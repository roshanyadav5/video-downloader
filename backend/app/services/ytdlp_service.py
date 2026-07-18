"""
Wraps yt-dlp for two jobs: pulling metadata+formats without downloading,
and actually running a download with progress callbacks. All yt-dlp
quirks (inconsistent field availability across extractors, format id
collisions, HDR detection, etc.) are normalized here so the rest of the
app deals with a clean, predictable schema.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from typing import Any, Callable

import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

from app.config import get_settings
from app.models.schemas import MetadataResponse, VideoFormat

logger = logging.getLogger("fetchly.ytdlp")

# Resolution buckets we sort into, highest first. Anything that reports
# a height we don't recognize still gets bucketed by nearest standard.
_RESOLUTION_ORDER = [2160, 1440, 1080, 720, 480, 360, 240, 144]


import threading

_writable_cookiefile_cache: str | None = None
_cached_source_mtime: float | None = None
_cookiefile_lock = threading.Lock()


def _get_writable_cookiefile() -> str | None:
    """
    yt-dlp's YoutubeDL.close() unconditionally calls cookiejar.save()
    back to whatever path was passed as 'cookiefile' — there's no way
    to load cookies read-only. Render (and most secret-file mechanisms)
    mount secrets read-only, so pointing yt-dlp directly at
    /etc/secrets/cookies.txt crashes with "Read-only file system" the
    moment a request finishes.

    Fix: copy the secret file to a writable /tmp path and always hand
    yt-dlp that copy. yt-dlp is free to update it as much as it wants.

    Stays fresh across secret updates: compares the source file's
    mtime on every call and re-copies if it changed, so a cookie
    refresh takes effect on the next request rather than requiring a
    full process restart (Render does restart on secret-file changes,
    but this makes it correct even where that isn't guaranteed).

    Thread-safe: metadata/download requests each run in their own
    thread-pool thread, so this can genuinely be called concurrently.
    """
    global _writable_cookiefile_cache, _cached_source_mtime
    settings = get_settings()

    if not settings.cookies_file or not os.path.isfile(settings.cookies_file):
        return None

    source_mtime = os.path.getmtime(settings.cookies_file)
    is_fresh = (
        _writable_cookiefile_cache
        and os.path.isfile(_writable_cookiefile_cache)
        and _cached_source_mtime == source_mtime
    )
    if is_fresh:
        return _writable_cookiefile_cache

    with _cookiefile_lock:
        # Re-check after acquiring the lock — another thread may have
        # already refreshed it while we were waiting.
        source_mtime = os.path.getmtime(settings.cookies_file)
        if (
            _writable_cookiefile_cache
            and os.path.isfile(_writable_cookiefile_cache)
            and _cached_source_mtime == source_mtime
        ):
            return _writable_cookiefile_cache

        writable_path = os.path.join(tempfile.gettempdir(), "fetchly-cookies.txt")
        shutil.copyfile(settings.cookies_file, writable_path)
        _writable_cookiefile_cache = writable_path
        _cached_source_mtime = source_mtime
        logger.info("Copied cookies file to writable path: %s", writable_path)
        return writable_path


def _base_ydl_opts() -> dict[str, Any]:
    settings = get_settings()
    cookiefile = _get_writable_cookiefile()

    # This matters more than it looks: verified directly against
    # yt-dlp's own INNERTUBE_CLIENTS table (extractor/youtube/_base.py)
    # that the android/ios/mweb clients have SUPPORTS_COOKIES=False —
    # they cannot use cookie-based auth *at all*, no matter how valid
    # the cookies are. Only 'web' and 'tv' support cookies. Of those,
    # 'tv' additionally has no PO Token requirement (web does, even
    # when authenticated), making it the more reliable authenticated
    # client. So: with cookies, lead with tv/web; without cookies,
    # android/ios genuinely do work for many non-flagged videos and
    # stay as the fallback chain.
    player_clients = ["tv", "web"] if cookiefile else ["android", "ios", "web"]

    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # Security: see app/services/security.py docstring — this is
        # the critical SSRF safeguard. Never remove.
        "allowed_extractors": settings.allowed_extractors_list,
        "socket_timeout": 15,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 2,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            ),
        },
        "extractor_args": {
            "youtube": {"player_client": player_clients},
        },
        # Facebook (and increasingly other platforms) reject requests
        # whose TLS handshake doesn't match a real browser's fingerprint
        # — Python's default request library is trivially detectable.
        # curl_cffi (installed via the yt-dlp[curl-cffi] extra) makes
        # the connection look like real Chrome at the TLS level, not
        # just at the HTTP header level.
        "impersonate": ImpersonateTarget.from_str("chrome"),
    }

    if cookiefile:
        opts["cookiefile"] = cookiefile
    return opts


def _label_for_format(fmt: dict[str, Any], is_hdr: bool) -> str:
    """Builds the human-readable line, e.g. '4K 2160p HDR 60fps MP4'."""
    height = fmt.get("height")
    parts: list[str] = []

    if height:
        if height >= 2160:
            parts.append("4K")
        elif height >= 1440:
            parts.append("2K")
        parts.append(f"{height}p")
    else:
        parts.append("Audio Only")

    if is_hdr:
        parts.append("HDR")

    fps = fmt.get("fps")
    if fps and fps > 30:
        parts.append(f"{int(fps)}fps")

    ext = (fmt.get("ext") or "").upper()
    if ext:
        parts.append(ext)

    if fmt.get("acodec") not in (None, "none") and height:
        parts.append("(Audio Included)")

    return " ".join(parts)


def _is_hdr(fmt: dict[str, Any]) -> bool:
    dynamic_range = (fmt.get("dynamic_range") or "").upper()
    return dynamic_range not in ("", "SDR", "NONE")


def _normalize_format(fmt: dict[str, Any]) -> VideoFormat | None:
    """Converts a raw yt-dlp format dict into our VideoFormat schema, or
    returns None if the format isn't usable (e.g. no known extension)."""
    ext = fmt.get("ext")
    if not ext:
        return None

    vcodec = fmt.get("vcodec")
    acodec = fmt.get("acodec")
    has_video = vcodec not in (None, "none")
    has_audio = acodec not in (None, "none")

    if not has_video and not has_audio:
        return None  # unusable format, e.g. a manifest-only entry

    height = fmt.get("height")
    is_hdr = _is_hdr(fmt) if has_video else False
    resolution_label = f"{height}p" if height else "Audio Only"

    filesize = fmt.get("filesize")
    filesize_approx = fmt.get("filesize_approx")
    filesize_bytes = filesize or filesize_approx

    return VideoFormat(
        format_id=fmt["format_id"],
        resolution=resolution_label,
        label=_label_for_format(fmt, is_hdr),
        ext=ext,
        vcodec=vcodec if has_video else None,
        acodec=acodec if has_audio else None,
        fps=fmt.get("fps"),
        is_hdr=is_hdr,
        has_audio=has_audio,
        has_video=has_video,
        filesize_bytes=filesize_bytes,
        filesize_is_estimate=bool(filesize_approx and not filesize),
    )


def _sort_key(fmt: VideoFormat) -> tuple:
    """Highest quality first; audio-only sinks to the bottom."""
    if fmt.resolution == "Audio Only":
        height = -1
    else:
        height = int(fmt.resolution.rstrip("p") or 0)
    # HDR and higher fps break ties in favor of quality.
    return (height, fmt.is_hdr, fmt.fps or 0, fmt.filesize_bytes or 0)


def _dedupe_and_sort(formats: list[VideoFormat]) -> list[VideoFormat]:
    """
    Keeps the best representative for each (resolution, hdr, container)
    combination instead of showing every raw format id yt-dlp reports
    (which often includes near-duplicate bitrate variants).
    """
    best: dict[tuple, VideoFormat] = {}
    for fmt in formats:
        key = (fmt.resolution, fmt.is_hdr, fmt.ext, fmt.has_audio)
        existing = best.get(key)
        if existing is None or (fmt.filesize_bytes or 0) > (existing.filesize_bytes or 0):
            best[key] = fmt

    return sorted(best.values(), key=_sort_key, reverse=True)


def fetch_metadata(url: str) -> MetadataResponse:
    """Extracts title/thumbnail/duration/formats without downloading anything."""
    opts = {**_base_ydl_opts(), "skip_download": True}

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    raw_formats = info.get("formats") or []
    normalized = [f for f in (_normalize_format(rf) for rf in raw_formats) if f is not None]
    formats = _dedupe_and_sort(normalized)

    return MetadataResponse(
        title=info.get("title") or "Untitled",
        thumbnail_url=info.get("thumbnail"),
        duration_seconds=info.get("duration"),
        platform=info.get("extractor_key") or info.get("extractor") or "Unknown",
        uploader=info.get("uploader"),
        view_count=info.get("view_count"),
        upload_date=_format_upload_date(info.get("upload_date")),
        formats=formats,
    )


def _format_upload_date(raw: str | None) -> str | None:
    """yt-dlp reports upload_date as YYYYMMDD; reformat to YYYY-MM-DD."""
    if not raw or len(raw) != 8:
        return raw
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"


def run_download(
    url: str,
    format_id: str,
    output_template: str,
    on_progress: Callable[[dict[str, Any]], None],
) -> str:
    """
    Runs the actual download + merge (yt-dlp handles muxing separate
    audio/video streams automatically via ffmpeg when the chosen format
    is video-only). Returns the final file path on success.
    """
    settings = get_settings()

    # If the user picked a video-only format, pair it with the best
    # available audio so they never have to merge anything manually.
    format_selector = f"{format_id}+bestaudio/best" if format_id != "bestaudio" else format_id

    result_path: dict[str, str] = {}

    def _hook(d: dict[str, Any]) -> None:
        if d.get("status") == "finished":
            result_path["path"] = d.get("filename", "")
        on_progress(d)

    opts = {
        **_base_ydl_opts(),
        "format": format_selector,
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "progress_hooks": [_hook],
        "postprocessor_hooks": [_hook],
        # Belt-and-braces duration cap, in case a malicious/huge stream
        # slipped past client-side checks.
        "match_filter": yt_dlp.utils.match_filter_func(
            f"duration <? {settings.max_video_duration_seconds}"
        ),
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # yt-dlp gives us the post-merge path via requested_downloads
        # when available; fall back to the hook-captured path.
        downloads = info.get("requested_downloads") or []
        if downloads and downloads[0].get("filepath"):
            return downloads[0]["filepath"]

    return result_path.get("path", "")

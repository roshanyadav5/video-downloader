"""
Centralized error handling. Every error the API can return goes through
here so the response shape is always consistent:

    {"success": false, "platform": "youtube", "reason": "bot_detection", "message": "..."}

`reason` is the machine-readable field a client should branch on.
`message` is safe to show a user directly. Raw exception text and
tracebacks never reach the client — see the catch-all handler in
main.py for where that's enforced.

Add new reasons here, not ad-hoc strings scattered across routers.
"""
from __future__ import annotations

from enum import Enum

from fastapi import HTTPException


class Reason(str, Enum):
    INVALID_URL = "invalid_url"
    UNSUPPORTED_URL = "unsupported_url"
    UNSAFE_URL = "unsafe_url"
    VIDEO_REMOVED = "video_removed"
    PRIVATE_VIDEO = "private_video"
    AGE_RESTRICTED = "age_restricted"
    REGION_LOCKED = "region_locked"
    LOGIN_REQUIRED = "login_required"
    COOKIE_EXPIRED = "cookie_expired"
    BOT_DETECTION = "bot_detection"
    UNSUPPORTED_EXTRACTOR = "unsupported_extractor"
    FFMPEG_MISSING = "ffmpeg_missing"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    CAPACITY = "capacity"
    VIDEO_TOO_LONG = "video_too_long"
    JOB_NOT_FOUND = "job_not_found"
    JOB_NOT_READY = "job_not_ready"
    FILE_EXPIRED = "file_expired"
    UNKNOWN = "unknown"


class AppError(HTTPException):
    """Raise this anywhere in a route instead of a bare HTTPException —
    it carries the machine-readable reason + platform needed for the
    structured response shape."""

    def __init__(self, status_code: int, reason: Reason, message: str, platform: str = "unknown"):
        super().__init__(status_code=status_code, detail=message)
        self.reason = reason
        self.message = message
        self.platform = platform


def classify_ytdlp_error(exc: Exception, *, platform: str, cookies_configured: bool) -> AppError:
    """
    Maps a raw yt-dlp/extraction exception to a structured AppError.
    This is the single place that inspects yt-dlp's (English, unstable)
    error text — every router should call this instead of pattern
    matching independently.
    """
    text = str(exc).lower()

    def err(status: int, reason: Reason, message: str) -> AppError:
        return AppError(status, reason, message, platform=platform)

    if "no suitable extractor" in text:
        return err(422, Reason.UNSUPPORTED_EXTRACTOR, "This link format isn't supported yet.")
    if "private" in text:
        return err(422, Reason.PRIVATE_VIDEO, "This video is private.")
    if "age" in text and "restrict" in text:
        return err(422, Reason.AGE_RESTRICTED, "This video is age-restricted and can't be fetched.")
    if "unavailable" in text or "removed" in text or "deleted" in text or "no longer available" in text:
        return err(422, Reason.VIDEO_REMOVED, "This video is unavailable or has been removed.")
    if "region" in text or "available in your country" in text:
        return err(422, Reason.REGION_LOCKED, "This video is region-locked.")
    if "sign in" in text or "login" in text or "log in" in text or ("confirm you" in text and "bot" in text):
        # Distinguish "we have cookies but they're stale" from "no
        # cookies configured at all" — very different fixes for an admin.
        if cookies_configured:
            return err(
                422,
                Reason.COOKIE_EXPIRED,
                "The server's saved login has expired. An admin needs to refresh it.",
            )
        return err(
            422,
            Reason.BOT_DETECTION,
            "This platform is asking for sign-in verification right now. Please try again shortly.",
        )
    if "cannot parse data" in text or "impersonat" in text:
        return err(422, Reason.BOT_DETECTION, "This platform is temporarily blocking automated access.")
    if "403" in text and "forbidden" in text:
        return err(422, Reason.BOT_DETECTION, "This platform is temporarily blocking automated access.")
    if "duration" in text and "does not pass filter" in text:
        return err(422, Reason.VIDEO_TOO_LONG, "This video is too long for this service.")
    if "ffmpeg" in text and ("not found" in text or "not installed" in text):
        return err(503, Reason.FFMPEG_MISSING, "The server is misconfigured (missing ffmpeg). Please report this.")
    if "timed out" in text or "timeout" in text or "connection" in text:
        return err(502, Reason.NETWORK_ERROR, "A network error occurred. Please try again.")

    return err(422, Reason.UNKNOWN, "Couldn't fetch this video. It may be unavailable or unsupported.")

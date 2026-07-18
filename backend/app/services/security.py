"""
Security utilities: URL validation and SSRF protection.

This is the most important file in the backend. Any web app that fetches
a user-supplied URL server-side is a potential SSRF vector — an attacker
can pass a URL pointing at an internal service, cloud metadata endpoint
(e.g. 169.254.169.254), or localhost admin panel, and trick the server
into fetching it on their behalf. yt-dlp's generic extractor makes this
worse because it will attempt to scrape *any* URL, not just known video
platforms.

Two layers of defense here:
  1. Only URLs matching a known video-platform domain are accepted at all.
  2. The hostname is resolved and checked against private/loopback/
     link-local IP ranges before we let yt-dlp anywhere near it — this
     catches DNS rebinding tricks (a public-looking hostname that
     resolves to an internal IP).
"""
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

# Known platforms this service explicitly supports. Anything else is
# rejected before it ever reaches yt-dlp's generic/fallback extractor.
ALLOWED_DOMAINS = {
    "youtube.com", "youtu.be", "m.youtube.com",
    "twitter.com", "x.com",
    "instagram.com",
    "facebook.com", "fb.watch",
    "tiktok.com", "vm.tiktok.com",
    "reddit.com", "v.redd.it",
    "vimeo.com",
    "dailymotion.com", "dai.ly",
    "twitch.tv", "clips.twitch.tv",
    "pinterest.com", "pin.it",
    "linkedin.com",
    "snapchat.com",
    "streamable.com",
}


class UnsupportedURLError(ValueError):
    """Raised when a URL isn't from a supported platform."""


class UnsafeURLError(ValueError):
    """Raised when a URL resolves to a disallowed network destination."""


def _root_domain(hostname: str) -> str:
    """Reduce e.g. 'www.m.youtube.com' down to 'youtube.com'-style match target."""
    parts = hostname.lower().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname.lower()


def validate_platform(url: str) -> str:
    """
    Confirms the URL's host matches a supported platform.
    Returns the normalized hostname. Raises UnsupportedURLError otherwise.
    """
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise UnsupportedURLError("Malformed URL.") from exc

    if parsed.scheme not in ("http", "https"):
        raise UnsupportedURLError("Only http(s) URLs are supported.")
    if not parsed.hostname:
        raise UnsupportedURLError("URL has no hostname.")

    hostname = parsed.hostname.lower()
    if hostname not in ALLOWED_DOMAINS and _root_domain(hostname) not in ALLOWED_DOMAINS:
        raise UnsupportedURLError(f"'{hostname}' is not a supported platform.")

    return hostname


def assert_safe_destination(hostname: str) -> None:
    """
    Resolves the hostname and rejects it if any resolved address is
    private, loopback, link-local, or otherwise non-public. Protects
    against DNS rebinding attacks on an otherwise-allowlisted domain.
    """
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve '{hostname}'.") from exc

    for info in addr_infos:
        ip_str = info[4][0]
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UnsafeURLError(
                f"'{hostname}' resolves to a disallowed network address."
            )


def validate_and_check_url(url: str) -> None:
    """Full validation pipeline. Raises UnsupportedURLError or UnsafeURLError."""
    hostname = validate_platform(url)
    assert_safe_destination(hostname)


MAX_REDIRECT_HOPS = 5


def resolve_redirect_chain(url: str) -> str:
    """
    Manually follows HTTP redirects one hop at a time, re-validating
    each intermediate URL against the platform allowlist and
    safe-destination checks before following it.

    Why this exists: short-link formats like Facebook's
    facebook.com/share/r/<id>/ aren't matched by yt-dlp's named
    extractors at all — normally yt-dlp's *generic* extractor would
    resolve them, but we deliberately never enable the generic
    extractor (see module docstring — it will scrape whatever URL a
    page redirects or points it to, which is a real SSRF vector). This
    gives us the same practical result — following a short link to its
    real destination — without ever handing yt-dlp a URL we haven't
    validated ourselves first.

    Raises UnsupportedURLError/UnsafeURLError if any hop in the chain
    leaves the allowlisted domains or resolves to an unsafe address.
    """
    import requests

    current = url
    for _ in range(MAX_REDIRECT_HOPS):
        validate_and_check_url(current)
        try:
            resp = requests.get(
                current,
                allow_redirects=False,
                timeout=10,
                stream=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Fetchly/1.0)"},
            )
            resp.close()
        except requests.RequestException as exc:
            raise UnsafeURLError(f"Could not resolve redirect for '{current}'.") from exc

        if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("Location"):
            current = urljoin(current, resp.headers["Location"])
            continue
        return current

    return current  # exhausted hop budget — hand back the best-effort last URL


_PLATFORM_BY_DOMAIN = {
    "youtube.com": "youtube", "youtu.be": "youtube", "m.youtube.com": "youtube",
    "twitter.com": "twitter", "x.com": "twitter",
    "instagram.com": "instagram",
    "facebook.com": "facebook", "fb.watch": "facebook",
    "tiktok.com": "tiktok", "vm.tiktok.com": "tiktok",
    "reddit.com": "reddit", "v.redd.it": "reddit",
    "vimeo.com": "vimeo",
    "dailymotion.com": "dailymotion", "dai.ly": "dailymotion",
    "twitch.tv": "twitch", "clips.twitch.tv": "twitch",
    "pinterest.com": "pinterest", "pin.it": "pinterest",
    "linkedin.com": "linkedin",
    "snapchat.com": "snapchat",
    "streamable.com": "streamable",
}


def detect_platform(url: str) -> str:
    """Best-effort platform name for error responses. Never raises —
    worst case returns 'unknown', since this is purely informational."""
    try:
        hostname = (urlparse(url).hostname or "").lower()
    except ValueError:
        return "unknown"
    if hostname in _PLATFORM_BY_DOMAIN:
        return _PLATFORM_BY_DOMAIN[hostname]
    return _PLATFORM_BY_DOMAIN.get(_root_domain(hostname), "unknown")


def sanitize_filename(name: str, max_length: int = 150) -> str:
    """
    Strips path separators, control characters, and anything else that
    could be used for path traversal or filesystem trickery, leaving a
    safe filename for Content-Disposition and on-disk storage.
    """
    import re

    # Drop path separators and null bytes outright.
    name = name.replace("/", "").replace("\\", "").replace("\x00", "")
    # Strip control characters.
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    # Collapse whitespace.
    name = re.sub(r"\s+", " ", name).strip()
    # Keep it to a sane length so filesystems don't choke.
    name = name[:max_length].strip()
    return name or "download"

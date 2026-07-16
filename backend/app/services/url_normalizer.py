"""
Normalizes user-submitted URLs before they reach yt-dlp:
  1. Strips tracking query parameters that don't affect extraction
     (si, utm_*, igshid, fbclid, etc.) — purely cosmetic/privacy, but
     also means the same video pasted two different ways doesn't look
     like two different URLs to anything caching on it later.
  2. Resolves known short-link hosts (fb.watch, Facebook's
     /share/r/<id>/ format, pin.it, vm.tiktok.com, dai.ly) to their
     real destination via app.services.security.resolve_redirect_chain
     — which re-validates every hop, so this never bypasses the SSRF
     protections, it just runs them one extra time per hop.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.services import security

# Query params that never affect which video gets extracted — just
# tracking/attribution noise from being shared through a chat app,
# social feed, etc.
_TRACKING_PARAMS = {
    "si", "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "igshid", "igsh", "fbclid", "gclid", "mc_cid", "mc_eid", "feature",
    "spm", "_ga", "ref", "ref_src", "ref_url", "s", "app",
}

# Hosts that are *always* short-links needing redirect resolution
# before yt-dlp can do anything with them — none of these are ever
# the final playable URL.
_SHORTLINK_HOSTS = {"fb.watch", "pin.it", "vm.tiktok.com", "dai.ly"}


def _strip_tracking_params(url: str) -> str:
    parsed = urlparse(url)
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in _TRACKING_PARAMS]
    return urlunparse(parsed._replace(query=urlencode(kept)))


def _needs_redirect_resolution(url: str) -> bool:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname in _SHORTLINK_HOSTS:
        return True
    # Facebook's share-link format: facebook.com/share/r|v|p/<id>/
    if "facebook.com" in hostname and parsed.path.startswith("/share/"):
        return True
    return False


def normalize_url(url: str) -> str:
    """
    Full normalization pipeline. Assumes the URL has already passed
    security.validate_and_check_url() — this does not re-validate the
    *input* URL, only any redirect hops it follows internally.
    """
    cleaned = _strip_tracking_params(url.strip())

    if _needs_redirect_resolution(cleaned):
        cleaned = security.resolve_redirect_chain(cleaned)
        cleaned = _strip_tracking_params(cleaned)

    return cleaned

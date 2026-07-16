"""
Centralized error handling. Every error the API can return goes through
here so the response shape is always consistent — {"success": false,
"error": "...", "error_code": "..."} — and raw exception text/tracebacks
never reach the client.

Add new error codes here, not ad-hoc strings scattered across routers.
"""
from __future__ import annotations

from enum import Enum

from fastapi import HTTPException


class ErrorCode(str, Enum):
    INVALID_URL = "INVALID_URL"
    UNSUPPORTED_URL = "UNSUPPORTED_URL"
    UNSAFE_URL = "UNSAFE_URL"
    VIDEO_REMOVED = "VIDEO_REMOVED"
    PRIVATE_VIDEO = "PRIVATE_VIDEO"
    AGE_RESTRICTED = "AGE_RESTRICTED"
    REGION_LOCKED = "REGION_LOCKED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    COOKIE_EXPIRED = "COOKIE_EXPIRED"
    BOT_VERIFICATION = "BOT_VERIFICATION"
    UNSUPPORTED_EXTRACTOR = "UNSUPPORTED_EXTRACTOR"
    FFMPEG_MISSING = "FFMPEG_MISSING"
    NETWORK_ERROR = "NETWORK_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    CAPACITY = "CAPACITY"
    VIDEO_TOO_LONG = "VIDEO_TOO_LONG"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_NOT_READY = "JOB_NOT_READY"
    FILE_EXPIRED = "FILE_EXPIRED"
    UNKNOWN = "UNKNOWN"


class AppError(HTTPException):
    """Raise this anywhere in a route instead of a bare HTTPException —
    it carries a machine-readable error_code alongside the message."""

    def __init__(self, status_code: int, error_code: ErrorCode, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code
        self.message = message


def classify_ytdlp_error(exc: Exception, *, cookies_configured: bool) -> AppError:
    """
    Maps a raw yt-dlp/extraction exception to a structured AppError.
    This is the single place that inspects yt-dlp's (English, unstable)
    error text — every router should call this instead of pattern
    matching independently.
    """
    text = str(exc).lower()

    if "no suitable extractor" in text:
        return AppError(422, ErrorCode.UNSUPPORTED_EXTRACTOR, "This link format isn't supported yet.")
    if "private" in text:
        return AppError(422, ErrorCode.PRIVATE_VIDEO, "This video is private.")
    if "age" in text and "restrict" in text:
        return AppError(422, ErrorCode.AGE_RESTRICTED, "This video is age-restricted and can't be fetched.")
    if "unavailable" in text or "removed" in text or "deleted" in text or "no longer available" in text:
        return AppError(422, ErrorCode.VIDEO_REMOVED, "This video is unavailable or has been removed.")
    if "region" in text or "available in your country" in text:
        return AppError(422, ErrorCode.REGION_LOCKED, "This video is region-locked.")
    if "sign in" in text or "login" in text or "log in" in text or ("confirm you" in text and "bot" in text):
        # Distinguish "we have cookies but they're stale" from "no
        # cookies configured at all" — very different fixes.
        if cookies_configured:
            return AppError(
                422,
                ErrorCode.COOKIE_EXPIRED,
                "The server's saved login has expired. An admin needs to refresh it.",
            )
        return AppError(
            422,
            ErrorCode.BOT_VERIFICATION,
            "This platform is asking for sign-in verification right now. Please try again shortly.",
        )
    if "cannot parse data" in text or "impersonat" in text:
        return AppError(
            422, ErrorCode.BOT_VERIFICATION, "This platform is temporarily blocking automated access."
        )
    if "duration" in text and "does not pass filter" in text:
        return AppError(422, ErrorCode.VIDEO_TOO_LONG, "This video is too long for this service.")
    if "ffmpeg" in text and ("not found" in text or "not installed" in text):
        return AppError(
            503, ErrorCode.FFMPEG_MISSING, "The server is misconfigured (missing ffmpeg). Please report this."
        )
    if "timed out" in text or "timeout" in text or "connection" in text:
        return AppError(502, ErrorCode.NETWORK_ERROR, "A network error occurred. Please try again.")

    return AppError(422, ErrorCode.UNKNOWN, "Couldn't fetch this video. It may be unavailable or unsupported.")

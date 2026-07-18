import asyncio
import logging

from fastapi import APIRouter

from app.config import get_settings
from app.errors import AppError, Reason, classify_ytdlp_error
from app.models.schemas import MetadataRequest, MetadataResponse
from app.services import security, ytdlp_service
from app.services.url_normalizer import normalize_url

logger = logging.getLogger("fetchly.metadata")
router = APIRouter(prefix="/api", tags=["metadata"])


@router.post("/metadata", response_model=MetadataResponse)
async def get_metadata(payload: MetadataRequest) -> MetadataResponse:
    url = payload.url.strip()
    platform = security.detect_platform(url)

    try:
        security.validate_and_check_url(url)
    except security.UnsupportedURLError as exc:
        raise AppError(400, Reason.UNSUPPORTED_URL, str(exc), platform=platform) from exc
    except security.UnsafeURLError as exc:
        # Deliberately vague to the client — don't reveal *why* a URL
        # was rejected as unsafe, that's information a probing attacker
        # could use to map internal network structure.
        raise AppError(400, Reason.UNSAFE_URL, "This URL could not be processed.", platform=platform) from exc

    try:
        # normalize_url can make a real HTTP request (redirect
        # resolution for share links) — also genuinely blocking, also
        # needs to run off the event loop.
        loop = asyncio.get_running_loop()
        resolved_url = await loop.run_in_executor(None, normalize_url, url)
    except (security.UnsupportedURLError, security.UnsafeURLError) as exc:
        raise AppError(400, Reason.UNSAFE_URL, "This URL could not be processed.", platform=platform) from exc

    try:
        # yt-dlp's extract_info() is synchronous network I/O — running
        # it directly here would block the entire event loop (every
        # other concurrent request, including health checks) for
        # however long extraction takes. Offloading to a thread is not
        # optional for a service meant to handle concurrent users.
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, ytdlp_service.fetch_metadata, resolved_url)
    except Exception as exc:
        logger.warning("Metadata extraction failed for %s: %s", resolved_url, exc)
        settings = get_settings()
        raise classify_ytdlp_error(
            exc, platform=platform, cookies_configured=bool(settings.cookies_file)
        ) from exc

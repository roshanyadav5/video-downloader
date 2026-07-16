import logging

from fastapi import APIRouter

from app.config import get_settings
from app.errors import AppError, ErrorCode, classify_ytdlp_error
from app.models.schemas import MetadataRequest, MetadataResponse
from app.services import security, ytdlp_service
from app.services.url_normalizer import normalize_url

logger = logging.getLogger("fetchly.metadata")
router = APIRouter(prefix="/api", tags=["metadata"])


@router.post("/metadata", response_model=MetadataResponse)
async def get_metadata(payload: MetadataRequest) -> MetadataResponse:
    url = payload.url.strip()

    try:
        security.validate_and_check_url(url)
    except security.UnsupportedURLError as exc:
        raise AppError(400, ErrorCode.UNSUPPORTED_URL, str(exc)) from exc
    except security.UnsafeURLError as exc:
        # Deliberately vague to the client — don't reveal *why* a URL
        # was rejected as unsafe, that's information a probing attacker
        # could use to map internal network structure.
        raise AppError(400, ErrorCode.UNSAFE_URL, "This URL could not be processed.") from exc

    try:
        resolved_url = normalize_url(url)
    except (security.UnsupportedURLError, security.UnsafeURLError) as exc:
        # A redirect hop led somewhere disallowed — same vague message
        # for the same reason as above.
        raise AppError(400, ErrorCode.UNSAFE_URL, "This URL could not be processed.") from exc

    try:
        return ytdlp_service.fetch_metadata(resolved_url)
    except Exception as exc:
        logger.warning("Metadata extraction failed for %s: %s", resolved_url, exc)
        settings = get_settings()
        raise classify_ytdlp_error(exc, cookies_configured=bool(settings.cookies_file)) from exc

import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import MetadataRequest, MetadataResponse
from app.services import security, ytdlp_service

logger = logging.getLogger("fetchly.metadata")
router = APIRouter(prefix="/api", tags=["metadata"])


@router.post("/metadata", response_model=MetadataResponse)
async def get_metadata(payload: MetadataRequest) -> MetadataResponse:
    url = payload.url.strip()

    try:
        security.validate_and_check_url(url)
    except security.UnsupportedURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except security.UnsafeURLError as exc:
        # Deliberately vague to the client — don't reveal *why* a URL
        # was rejected as unsafe, that's information a probing attacker
        # could use to map internal network structure.
        raise HTTPException(status_code=400, detail="This URL could not be processed.") from exc

    try:
        return ytdlp_service.fetch_metadata(url)
    except Exception as exc:
        logger.warning("Metadata extraction failed for %s: %s", url, exc)
        message = _friendly_error_message(exc)
        raise HTTPException(status_code=422, detail=message) from exc


def _friendly_error_message(exc: Exception) -> str:
    text = str(exc).lower()
    if "private" in text:
        return "This video is private."
    if "age" in text and "restrict" in text:
        return "This video is age-restricted and can't be fetched."
    if "unavailable" in text or "removed" in text or "deleted" in text:
        return "This video is unavailable or has been removed."
    if "region" in text or "not available in your country" in text:
        return "This video is region-locked."
    if "sign in" in text or "login" in text:
        return "This video requires sign-in and can't be fetched."
    if "timed out" in text or "timeout" in text:
        return "The platform took too long to respond. Please try again."
    return "Couldn't fetch this video. It may be unavailable or unsupported."

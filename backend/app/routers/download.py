import asyncio
import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.errors import AppError, ErrorCode, classify_ytdlp_error
from app.models.schemas import DownloadJobResponse, DownloadRequest, ProgressEvent
from app.services import security, ytdlp_service
from app.services.job_manager import Job, job_manager
from app.services.url_normalizer import normalize_url

logger = logging.getLogger("fetchly.download")
router = APIRouter(prefix="/api", tags=["download"])


@router.post("/download", response_model=DownloadJobResponse)
async def start_download(payload: DownloadRequest, request: Request) -> DownloadJobResponse:
    settings = get_settings()
    url = payload.url.strip()
    ip = request.client.host if request.client else "unknown"

    try:
        security.validate_and_check_url(url)
        resolved_url = normalize_url(url)
    except (security.UnsupportedURLError, security.UnsafeURLError) as exc:
        raise AppError(400, ErrorCode.UNSAFE_URL, "This URL could not be processed.") from exc

    if job_manager.active_count_for_ip(ip) >= settings.max_concurrent_jobs_per_ip:
        raise AppError(
            429,
            ErrorCode.RATE_LIMITED,
            f"You can only run {settings.max_concurrent_jobs_per_ip} downloads at once.",
        )
    if job_manager.active_count_global() >= settings.max_concurrent_jobs_global:
        raise AppError(503, ErrorCode.CAPACITY, "Server is at capacity. Please try again shortly.")

    job = job_manager.create_job(ip)
    asyncio.create_task(_execute_job(job, resolved_url, payload.format_id))
    return DownloadJobResponse(job_id=job.id)


@router.get("/progress/{job_id}")
async def progress_stream(job_id: str):
    job = job_manager.get(job_id)
    if job is None:
        raise AppError(404, ErrorCode.JOB_NOT_FOUND, "Job not found.")

    async def event_generator():
        # Replay the current state immediately in case the client
        # connects after the job already made progress.
        yield {"data": job.event.model_dump_json()}
        if job.event.status in ("completed", "error"):
            return

        while True:
            event: ProgressEvent = await job.queue.get()
            yield {"data": event.model_dump_json()}
            if event.status in ("completed", "error"):
                break

    return EventSourceResponse(event_generator())


@router.get("/file/{job_id}")
async def get_file(job_id: str):
    job = job_manager.get(job_id)
    if job is None:
        raise AppError(404, ErrorCode.JOB_NOT_FOUND, "Job not found.")
    if job.event.status != "completed" or not job.file_path:
        raise AppError(409, ErrorCode.JOB_NOT_READY, "This download isn't ready yet.")
    if not os.path.isfile(job.file_path):
        raise AppError(410, ErrorCode.FILE_EXPIRED, "This file has expired. Please download again.")

    filename = job.event.filename or os.path.basename(job.file_path)
    return FileResponse(
        path=job.file_path,
        filename=filename,
        media_type="application/octet-stream",
    )


async def _execute_job(job: Job, url: str, format_id: str) -> None:
    settings = get_settings()
    loop = asyncio.get_running_loop()

    job_dir = os.path.join(settings.download_dir, job.id)
    os.makedirs(job_dir, exist_ok=True)
    output_template = os.path.join(job_dir, "%(title).150s.%(ext)s")

    def on_progress(d: dict) -> None:
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            percent = (downloaded / total * 100) if total else 0.0
            event = ProgressEvent(
                status="downloading",
                percent=round(percent, 1),
                speed_bytes_per_sec=d.get("speed"),
                eta_seconds=d.get("eta"),
            )
        elif status == "finished":
            event = ProgressEvent(status="merging", percent=99.0)
        else:
            return
        loop.call_soon_threadsafe(asyncio.create_task, job_manager.push_update(job, event))

    try:
        await job_manager.push_update(job, ProgressEvent(status="downloading", percent=0.0))
        file_path = await loop.run_in_executor(
            None, ytdlp_service.run_download, url, format_id, output_template, on_progress
        )
        if not file_path or not os.path.isfile(file_path):
            raise RuntimeError("Download completed but the output file could not be found.")

        job.file_path = file_path
        safe_name = security.sanitize_filename(os.path.basename(file_path))
        await job_manager.push_update(
            job, ProgressEvent(status="completed", percent=100.0, filename=safe_name)
        )
    except Exception as exc:
        logger.warning("Download job %s failed: %s", job.id, exc)
        app_error = classify_ytdlp_error(exc, cookies_configured=bool(settings.cookies_file))
        await job_manager.push_update(
            job,
            ProgressEvent(
                status="error",
                error_message=app_error.message,
                error_code=app_error.error_code.value,
            ),
        )

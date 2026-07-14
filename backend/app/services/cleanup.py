"""
Periodic cleanup of temp download files. Every download lands in its own
job-scoped subdirectory under settings.download_dir; this sweeper removes
directories for jobs past their TTL, whether or not the client actually
picked up the finished file.
"""
import asyncio
import logging
import os
import shutil

from app.config import get_settings
from app.services.job_manager import job_manager

logger = logging.getLogger("fetchly.cleanup")


async def cleanup_loop() -> None:
    settings = get_settings()
    while True:
        try:
            expired_paths = job_manager.sweep_expired(settings.job_ttl_seconds)
            for path in expired_paths:
                job_dir = os.path.dirname(path)
                if job_dir and os.path.isdir(job_dir) and job_dir.startswith(settings.download_dir):
                    shutil.rmtree(job_dir, ignore_errors=True)
                    logger.info("Cleaned up expired job directory: %s", job_dir)
        except Exception:
            logger.exception("Cleanup loop iteration failed")
        await asyncio.sleep(60)

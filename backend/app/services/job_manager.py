"""
Tracks in-flight download jobs so the SSE progress endpoint can report
status independently of the background task doing the actual download.

This is intentionally in-memory (a dict), not Redis or a database —
for a single-instance deployment that's the right amount of complexity.
If this ever needs to run as multiple replicas behind a load balancer,
swap this for Redis pub/sub and nothing else in the app needs to change
(the interface below is the seam to do that at).
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field

from app.models.schemas import ProgressEvent


@dataclass
class Job:
    id: str
    ip: str
    created_at: float = field(default_factory=time.time)
    event: ProgressEvent = field(default_factory=lambda: ProgressEvent(status="queued"))
    file_path: str | None = None
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._jobs_per_ip: dict[str, int] = {}

    def create_job(self, ip: str) -> Job:
        job = Job(id=str(uuid.uuid4()), ip=ip)
        self._jobs[job.id] = job
        self._jobs_per_ip[ip] = self._jobs_per_ip.get(ip, 0) + 1
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def active_count_for_ip(self, ip: str) -> int:
        return sum(
            1
            for j in self._jobs.values()
            if j.ip == ip and j.event.status in ("queued", "downloading", "merging")
        )

    def active_count_global(self) -> int:
        return sum(
            1 for j in self._jobs.values() if j.event.status in ("queued", "downloading", "merging")
        )

    async def push_update(self, job: Job, event: ProgressEvent) -> None:
        job.event = event
        await job.queue.put(event)

    def sweep_expired(self, ttl_seconds: int) -> list[str]:
        """Removes jobs older than ttl_seconds; returns their file paths for cleanup."""
        now = time.time()
        expired = [j for j in self._jobs.values() if now - j.created_at > ttl_seconds]
        paths = [j.file_path for j in expired if j.file_path]
        for j in expired:
            del self._jobs[j.id]
        return [p for p in paths if p]


# Single process-wide instance — see module docstring re: scaling out.
job_manager = JobManager()

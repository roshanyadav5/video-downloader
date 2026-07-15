"""Request/response schemas shared across routers."""
from typing import Literal

from pydantic import BaseModel, Field


class MetadataRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


class VideoFormat(BaseModel):
    format_id: str
    resolution: str  # e.g. "2160p", "1080p", "Audio Only"
    label: str  # human-readable line, e.g. "4K 2160p HDR 60fps MP4"
    ext: str
    vcodec: str | None = None
    acodec: str | None = None
    fps: float | None = None
    is_hdr: bool = False
    has_audio: bool = True
    has_video: bool = True
    filesize_bytes: int | None = None  # None when the platform doesn't report it
    filesize_is_estimate: bool = False


class MetadataResponse(BaseModel):
    title: str
    thumbnail_url: str | None
    duration_seconds: float | None
    platform: str
    uploader: str | None = None
    formats: list[VideoFormat]


class DownloadRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    format_id: str = Field(..., min_length=1, max_length=64)


class DownloadJobResponse(BaseModel):
    job_id: str


JobStatus = Literal["queued", "downloading", "merging", "completed", "error"]


class ProgressEvent(BaseModel):
    status: JobStatus
    percent: float = 0.0
    speed_bytes_per_sec: float | None = None
    eta_seconds: float | None = None
    error_message: str | None = None
    filename: str | None = None  # set once completed

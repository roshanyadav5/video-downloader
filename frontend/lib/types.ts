export interface VideoFormat {
  format_id: string;
  resolution: string;
  label: string;
  ext: string;
  vcodec: string | null;
  acodec: string | null;
  fps: number | null;
  is_hdr: boolean;
  has_audio: boolean;
  has_video: boolean;
  filesize_bytes: number | null;
  filesize_is_estimate: boolean;
}

export interface MetadataResponse {
  title: string;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  platform: string;
  uploader: string | null;
  formats: VideoFormat[];
}

export type JobStatus = "queued" | "downloading" | "merging" | "completed" | "error";

export interface ProgressEvent {
  status: JobStatus;
  percent: number;
  speed_bytes_per_sec: number | null;
  eta_seconds: number | null;
  error_message: string | null;
  filename: string | null;
}

export interface ApiError {
  detail: string;
}

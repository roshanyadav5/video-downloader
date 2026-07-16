import type { MetadataResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiClientError extends Error {
  status: number;
  code: string;
  constructor(message: string, status: number, code: string = "UNKNOWN") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function throwFromResponse(res: Response): Promise<never> {
  try {
    const body = await res.json();
    throw new ApiClientError(
      body.error || `Request failed with status ${res.status}`,
      res.status,
      body.error_code || "UNKNOWN"
    );
  } catch (err) {
    if (err instanceof ApiClientError) throw err;
    throw new ApiClientError(`Request failed with status ${res.status}`, res.status);
  }
}

export async function fetchMetadata(url: string): Promise<MetadataResponse> {
  const res = await fetch(`${API_URL}/api/metadata`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) await throwFromResponse(res);
  return res.json();
}

export async function startDownload(url: string, formatId: string): Promise<{ job_id: string }> {
  const res = await fetch(`${API_URL}/api/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, format_id: formatId }),
  });

  if (!res.ok) await throwFromResponse(res);
  return res.json();
}

export function progressStreamUrl(jobId: string): string {
  return `${API_URL}/api/progress/${jobId}`;
}

export function fileDownloadUrl(jobId: string): string {
  return `${API_URL}/api/file/${jobId}`;
}

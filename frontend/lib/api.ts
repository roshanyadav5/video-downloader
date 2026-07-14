import type { MetadataResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiClientError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail || `Request failed with status ${res.status}`;
  } catch {
    return `Request failed with status ${res.status}`;
  }
}

export async function fetchMetadata(url: string): Promise<MetadataResponse> {
  const res = await fetch(`${API_URL}/api/metadata`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    throw new ApiClientError(await parseErrorDetail(res), res.status);
  }
  return res.json();
}

export async function startDownload(url: string, formatId: string): Promise<{ job_id: string }> {
  const res = await fetch(`${API_URL}/api/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, format_id: formatId }),
  });

  if (!res.ok) {
    throw new ApiClientError(await parseErrorDetail(res), res.status);
  }
  return res.json();
}

export function progressStreamUrl(jobId: string): string {
  return `${API_URL}/api/progress/${jobId}`;
}

export function fileDownloadUrl(jobId: string): string {
  return `${API_URL}/api/file/${jobId}`;
}

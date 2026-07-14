"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { startDownload, progressStreamUrl, fileDownloadUrl, ApiClientError } from "@/lib/api";
import type { ProgressEvent as JobProgressEvent } from "@/lib/types";

interface DownloadState {
  status: "idle" | "starting" | JobProgressEvent["status"];
  percent: number;
  speed: number | null;
  eta: number | null;
  error: string | null;
}

const initialState: DownloadState = {
  status: "idle",
  percent: 0,
  speed: null,
  eta: null,
  error: null,
};

export function useDownloadJob() {
  const [state, setState] = useState<DownloadState>(initialState);
  const eventSourceRef = useRef<EventSource | null>(null);
  const jobIdRef = useRef<string | null>(null);

  const cleanup = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const start = useCallback(
    async (url: string, formatId: string) => {
      cleanup();
      setState({ ...initialState, status: "starting" });

      try {
        const { job_id } = await startDownload(url, formatId);
        jobIdRef.current = job_id;

        const es = new EventSource(progressStreamUrl(job_id));
        eventSourceRef.current = es;

        es.onmessage = (msg) => {
          const event: JobProgressEvent = JSON.parse(msg.data);
          setState({
            status: event.status,
            percent: event.percent,
            speed: event.speed_bytes_per_sec,
            eta: event.eta_seconds,
            error: event.error_message,
          });

          if (event.status === "completed") {
            // Trigger the actual file save via a hidden navigation —
            // browsers handle Content-Disposition: attachment natively.
            const link = document.createElement("a");
            link.href = fileDownloadUrl(job_id);
            link.rel = "noopener";
            document.body.appendChild(link);
            link.click();
            link.remove();
            cleanup();
          }
          if (event.status === "error") {
            cleanup();
          }
        };

        es.onerror = () => {
          setState((prev) =>
            prev.status === "completed"
              ? prev
              : { ...prev, status: "error", error: "Lost connection to the server." }
          );
          cleanup();
        };
      } catch (err) {
        const message = err instanceof ApiClientError ? err.message : "Couldn't start the download.";
        setState({ ...initialState, status: "error", error: message });
      }
    },
    [cleanup]
  );

  const reset = useCallback(() => {
    cleanup();
    setState(initialState);
  }, [cleanup]);

  return { state, start, reset };
}

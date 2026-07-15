"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Download, CheckCircle2, XCircle, Music } from "lucide-react";
import type { VideoFormat } from "@/lib/types";
import { formatBytes, formatSpeed, formatEta } from "@/lib/format";
import { useDownloadJob } from "@/hooks/useDownloadJob";

export default function FormatRow({ url, format }: { url: string; format: VideoFormat }) {
  const { state, start, reset } = useDownloadJob();
  const isAudioOnly = format.resolution === "Audio Only";
  const isBusy = ["starting", "queued", "downloading", "merging"].includes(state.status);

  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className="glass-input flex items-center gap-3 rounded-xl px-4 py-3"
    >
      <div className="rounded-lg bg-primary/10 p-2">
        {isAudioOnly ? (
          <Music className="h-4 w-4 text-primary" />
        ) : (
          <span className="flex h-4 w-4 items-center justify-center text-[10px] font-bold text-primary">
            {format.resolution.replace("p", "")}
          </span>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{format.label}</p>
        <p className="text-xs text-muted">
          {formatBytes(format.filesize_bytes)}
          {format.filesize_is_estimate && format.filesize_bytes ? " (est.)" : ""}
        </p>
      </div>

      <div className="w-32 shrink-0 text-right">
        <AnimatePresence mode="wait" initial={false}>
          {state.status === "idle" && (
            <motion.button
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => start(url, format.format_id)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-white transition-transform hover:scale-105"
            >
              <Download className="h-3.5 w-3.5" /> Download
            </motion.button>
          )}

          {isBusy && (
            <motion.div
              key="progress"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-left"
            >
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                <motion.div
                  className="h-full rounded-full bg-primary"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.max(state.percent, 4)}%` }}
                  transition={{ ease: "easeOut" }}
                />
              </div>
              <p className="mt-1 truncate font-mono text-[10px] text-muted">
                {state.status === "merging"
                  ? "Merging..."
                  : `${state.percent.toFixed(0)}% · ${formatSpeed(state.speed)} · ${formatEta(state.eta)}`}
              </p>
            </motion.div>
          )}

          {state.status === "completed" && (
            <motion.div
              key="done"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center justify-end gap-1.5 text-xs font-medium text-success"
            >
              <CheckCircle2 className="h-4 w-4" /> Done
            </motion.div>
          )}

          {state.status === "error" && (
            <motion.button
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={reset}
              title={state.error ?? "Download failed"}
              className="flex items-center justify-end gap-1.5 text-xs font-medium text-danger hover:underline"
            >
              <XCircle className="h-4 w-4" /> Retry
            </motion.button>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

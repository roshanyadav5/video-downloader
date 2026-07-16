"use client";

import { motion } from "framer-motion";
import { Clock, Eye, User } from "lucide-react";
import type { MetadataResponse } from "@/lib/types";
import { formatDuration } from "@/lib/format";

function formatViewCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M views`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K views`;
  return `${count} views`;
}

export default function MetadataCard({ data }: { data: MetadataResponse }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-4 p-5 sm:p-6"
    >
      <div className="relative h-24 w-40 shrink-0 overflow-hidden rounded-xl bg-surface-2">
        {data.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={data.thumbnail_url}
            alt={data.title}
            className="h-full w-full object-cover"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-muted">
            No preview
          </div>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
          {data.platform}
        </span>
        <h2 className="mt-2 line-clamp-2 font-display text-base font-semibold leading-snug sm:text-lg">
          {data.title}
        </h2>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" /> {formatDuration(data.duration_seconds)}
          </span>
          {data.uploader && (
            <span className="flex items-center gap-1">
              <User className="h-3.5 w-3.5" /> {data.uploader}
            </span>
          )}
          {data.view_count !== null && data.view_count !== undefined && (
            <span className="flex items-center gap-1">
              <Eye className="h-3.5 w-3.5" /> {formatViewCount(data.view_count)}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}

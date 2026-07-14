"use client";

import { motion } from "framer-motion";
import { AlertTriangle, RotateCcw } from "lucide-react";

export default function ErrorCard({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card flex items-start gap-3 rounded-2xl border-danger/30 bg-danger/5 p-5"
    >
      <div className="mt-0.5 rounded-lg bg-danger/10 p-2">
        <AlertTriangle className="h-4 w-4 text-danger" />
      </div>
      <div className="flex-1">
        <p className="font-medium text-ink">Something went wrong</p>
        <p className="mt-1 text-sm text-muted">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-ink"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Retry
        </button>
      )}
    </motion.div>
  );
}

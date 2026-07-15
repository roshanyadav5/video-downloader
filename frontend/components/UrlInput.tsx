"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Clipboard, Link2, X } from "lucide-react";

interface UrlInputProps {
  onSubmit: (url: string) => void;
  loading: boolean;
}

export default function UrlInput({ onSubmit, loading }: UrlInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed) onSubmit(trimmed);
  }

  async function handlePaste() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) setValue(text.trim());
    } catch {
      // Clipboard permission denied — user can paste manually, no big deal.
    }
  }

  return (
    <motion.form
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="card flex w-full flex-col gap-2 rounded-2xl p-2 shadow-card sm:flex-row"
    >
      <div className="glass-input flex flex-1 items-center gap-2 rounded-xl px-4 py-3 ring-1 ring-transparent transition-shadow focus-within:ring-primary/40">
        <Link2 className="h-4 w-4 shrink-0 text-muted" />
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Paste your video URL here..."
          className="w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none sm:text-base"
        />
        <AnimatePresence>
          {value && (
            <motion.button
              type="button"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              onClick={() => setValue("")}
              aria-label="Clear input"
              className="shrink-0 rounded-lg p-1.5 text-muted transition-colors hover:bg-surface hover:text-ink"
            >
              <X className="h-4 w-4" />
            </motion.button>
          )}
        </AnimatePresence>
        <button
          type="button"
          onClick={handlePaste}
          aria-label="Paste from clipboard"
          className="shrink-0 rounded-lg p-1.5 text-muted transition-colors hover:bg-surface hover:text-ink"
        >
          <Clipboard className="h-4 w-4" />
        </button>
      </div>
      <motion.button
        type="submit"
        whileHover={{ scale: loading || !value.trim() ? 1 : 1.03 }}
        whileTap={{ scale: loading || !value.trim() ? 1 : 0.97 }}
        disabled={loading || !value.trim()}
        className="flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3 font-medium text-white shadow-glow transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? "Fetching..." : "Download"}
        {!loading && <ArrowRight className="h-4 w-4" />}
      </motion.button>
    </motion.form>
  );
}

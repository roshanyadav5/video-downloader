"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Header from "@/components/Header";
import UrlInput from "@/components/UrlInput";
import MetadataSkeleton from "@/components/MetadataSkeleton";
import MetadataCard from "@/components/MetadataCard";
import FormatList from "@/components/FormatList";
import ErrorCard from "@/components/ErrorCard";
import { fetchMetadata, ApiClientError } from "@/lib/api";
import type { MetadataResponse } from "@/lib/types";

type ViewState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; url: string; data: MetadataResponse };

export default function Home() {
  const [view, setView] = useState<ViewState>({ kind: "idle" });
  const [lastUrl, setLastUrl] = useState("");

  async function handleSubmit(url: string) {
    setLastUrl(url);
    setView({ kind: "loading" });
    try {
      const data = await fetchMetadata(url);
      setView({ kind: "ready", url, data });
    } catch (err) {
      const message =
        err instanceof ApiClientError ? err.message : "Couldn't reach the server. Please try again.";
      setView({ kind: "error", message });
    }
  }

  function handleRetry() {
    if (lastUrl) handleSubmit(lastUrl);
  }

  return (
    <div className="min-h-screen bg-bg">
      <div className="mx-auto max-w-2xl px-4">
        <Header />

        <section className="pb-16 pt-8 text-center sm:pt-16">
          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="font-display text-3xl font-bold tracking-tight sm:text-5xl"
          >
            Download any video,
            <br />
            <span className="text-primary">from anywhere.</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mx-auto mt-4 max-w-md text-muted"
          >
            Paste a link from YouTube, Instagram, TikTok, X, and dozens more.
            Pick your quality, we handle the rest.
          </motion.p>

          <div className="mt-8">
            <UrlInput onSubmit={handleSubmit} loading={view.kind === "loading"} />
          </div>
        </section>

        <AnimatePresence mode="wait">
          {view.kind === "loading" && (
            <motion.div key="loading" exit={{ opacity: 0 }}>
              <MetadataSkeleton />
            </motion.div>
          )}

          {view.kind === "error" && (
            <motion.div key="error" exit={{ opacity: 0 }}>
              <ErrorCard message={view.message} onRetry={lastUrl ? handleRetry : undefined} />
            </motion.div>
          )}

          {view.kind === "ready" && (
            <motion.div
              key="ready"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="card overflow-hidden rounded-2xl shadow-card"
            >
              <MetadataCard data={view.data} />
              <div className="h-px bg-border" />
              <FormatList url={view.url} formats={view.data.formats} />
            </motion.div>
          )}
        </AnimatePresence>

        <footer className="py-16 text-center text-xs text-muted">
          Downloading doesn&apos;t host or store any video content. You&apos;re responsible for
          how downloaded content is used.
        </footer>
      </div>
    </div>
  );
}

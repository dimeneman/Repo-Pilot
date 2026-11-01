"use client";

import React, { useEffect } from "react";
import { Loader2, CheckCircle2, AlertTriangle, Layers } from "lucide-react";
import { useRepoStatus } from "@/hooks/use-repos";
import { Progress } from "@/components/ui/progress";

interface StatusPollerProps {
  repoId: string;
  onReady?: () => void;
}

export function StatusPoller({ repoId, onReady }: StatusPollerProps) {
  const { status, progress, stepDescription, isReady, isFailed } = useRepoStatus(repoId);

  useEffect(() => {
    if (isReady && onReady) {
      onReady();
    }
  }, [isReady, onReady]);

  if (isReady) return null;

  const pct = Math.round((progress || 0.1) * 100);

  return (
    <div className="p-6 max-w-xl mx-auto my-8 border border-zinc-800 bg-zinc-950/90 rounded-2xl shadow-xl backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isFailed ? (
            <div className="w-10 h-10 rounded-xl bg-red-950/60 border border-red-800/50 flex items-center justify-center text-red-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-10 h-10 rounded-xl bg-indigo-950/60 border border-indigo-800/50 flex items-center justify-center text-indigo-400">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
          )}
          <div>
            <h4 className="text-sm font-semibold text-zinc-100">
              {isFailed ? "Ingestion Failed" : "Indexing Codebase..."}
            </h4>
            <p className="text-xs text-zinc-400">
              {stepDescription || "Analyzing files and building vector index"}
            </p>
          </div>
        </div>

        <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-md border border-indigo-500/20">
          {pct}%
        </span>
      </div>

      <Progress value={pct} className="h-2 bg-zinc-900 [&>div]:bg-indigo-600" />

      <div className="flex items-center justify-between text-[11px] text-zinc-400 pt-1">
        <span className="capitalize">Stage: {status || "Processing"}</span>
        <span>Cloning → Parsing → Chunking → Embeddings</span>
      </div>
    </div>
  );
}


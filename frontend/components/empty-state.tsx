"use client";

import React from "react";
import Image from "next/image";
import { Plus, Github } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  onAddRepo: () => void;
  onConnectGitHub?: () => void;
}

export function EmptyState({ onAddRepo, onConnectGitHub }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center max-w-md mx-auto my-16 border border-dashed border-slate-300 dark:border-zinc-800 rounded-2xl bg-white/80 dark:bg-zinc-950/50 shadow-sm">
      <div className="w-16 h-16 rounded-2xl bg-indigo-50/80 border border-indigo-100 dark:bg-zinc-900 dark:border-zinc-800 flex items-center justify-center p-2 mb-6 shadow-md shadow-indigo-500/10">
        <Image
          src="/logo.png"
          alt="RepoPilot Logo"
          width={48}
          height={48}
          className="w-full h-full object-contain"
        />
      </div>

      <h3 className="text-lg font-semibold text-slate-900 dark:text-zinc-100 tracking-tight">
        No repositories indexed yet
      </h3>
      <p className="text-xs text-slate-600 dark:text-zinc-400 mt-2 mb-6 leading-relaxed">
        Connect your GitHub account or provide a repository URL to get started. RepoPilot will parse the
        codebase, generate code-aware embeddings, and enable instant grounded
        Q&A with file and line citations.
      </p>

      <div className="flex items-center gap-3">
        <Button
          onClick={onAddRepo}
          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs gap-2 shadow-lg shadow-indigo-600/20"
        >
          <Plus className="w-4 h-4" />
          <span>Index Repository</span>
        </Button>
        {onConnectGitHub && (
          <Button
            variant="outline"
            onClick={onConnectGitHub}
            className="bg-white hover:bg-slate-100 border-slate-300 text-slate-700 dark:bg-transparent dark:border-zinc-800 dark:hover:bg-zinc-900 dark:text-zinc-300 text-xs gap-2 shadow-sm"
          >
            <Github className="w-4 h-4" />
            <span>From GitHub</span>
          </Button>
        )}
      </div>
    </div>
  );
}


"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Compass,
  Plus,
  Github,
  Search,
  Layers,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  FileCode,
  Network,
} from "lucide-react";
import { useRepos } from "@/hooks/use-repos";
import { RepoCard } from "@/components/repo-card";
import { EmptyState } from "@/components/empty-state";
import { RepoFormDialog } from "@/components/repo-form";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  const { repos, isLoading } = useRepos();
  const [openModal, setOpenModal] = useState(false);

  return (
    <div className="min-h-full bg-slate-50/60 dark:bg-zinc-950 p-6 md:p-10 space-y-10">
      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-50/90 via-white to-slate-50 border border-indigo-100/90 shadow-sm dark:bg-gradient-to-b dark:from-indigo-950/40 dark:via-zinc-900/60 dark:to-zinc-950 dark:border-zinc-800 dark:shadow-2xl p-8 md:p-12 transition-colors flex items-center justify-between gap-8">
        <div className="max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200/80 text-indigo-700 dark:bg-indigo-500/10 dark:border-indigo-500/20 dark:text-indigo-400 text-xs font-medium shadow-sm">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI-Powered GitHub Repository Intelligence</span>
          </div>

          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-zinc-100 leading-tight">
            Chat with any codebase. Grounded in source citations.
          </h1>

          <p className="text-sm md:text-base text-slate-600 dark:text-zinc-400 leading-relaxed">
            Provide a GitHub repository URL and explore your codebase through natural-language conversation. RepoPilot indexes your files with code-aware chunking, hybrid retrieval, and precise file and line citations.
          </p>

          <div className="pt-2 flex items-center gap-3">
            <Button
              onClick={() => setOpenModal(true)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white gap-2 shadow-lg shadow-indigo-600/25 px-5 h-10 text-xs md:text-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              <span>Index New Repository</span>
            </Button>

            <Link href="/repos">
              <Button
                variant="outline"
                className="bg-white hover:bg-slate-100 border-slate-300 text-slate-700 dark:bg-transparent dark:border-zinc-800 dark:hover:bg-zinc-900 dark:text-zinc-300 gap-2 h-10 text-xs md:text-sm shadow-sm"
              >
                <span>View All Repos</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>

        {/* Hero Logo Graphic */}
        <div className="hidden lg:flex flex-shrink-0 items-center justify-center p-6 relative">
          <div className="absolute -inset-4 bg-indigo-500/10 dark:bg-indigo-500/15 rounded-full blur-2xl pointer-events-none" />
          <div className="relative w-48 h-48 rounded-2xl flex items-center justify-center p-3">
            <Image
              src="/logo.png"
              alt="RepoPilot Platform Logo"
              width={192}
              height={192}
              priority
              className="w-full h-full object-contain drop-shadow-xl"
            />
          </div>
        </div>
      </div>

      {/* Feature Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm dark:bg-zinc-900/40 dark:border-zinc-850 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-600 dark:bg-indigo-950 dark:border-indigo-800/40 dark:text-indigo-400 flex items-center justify-center">
            <FileCode className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-sm text-slate-900 dark:text-zinc-100">Code-Aware Chunking</h3>
          <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
            Preserves syntactic function and class boundaries across Python, TypeScript, Go, Rust, Java, and Markdown.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm dark:bg-zinc-900/40 dark:border-zinc-850 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-600 dark:bg-indigo-950 dark:border-indigo-800/40 dark:text-indigo-400 flex items-center justify-center">
            <Search className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-sm text-slate-900 dark:text-zinc-100">Hybrid Retrieval</h3>
          <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
            Combines dense semantic vectors with BM25 sparse keyword ranking using Reciprocal Rank Fusion (RRF).
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm dark:bg-zinc-900/40 dark:border-zinc-850 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-600 dark:bg-indigo-950 dark:border-indigo-800/40 dark:text-indigo-400 flex items-center justify-center">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-sm text-slate-900 dark:text-zinc-100">Verified Citations</h3>
          <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
            Strictly cites actual file names, line ranges, and supporting code snippets for complete transparency.
          </p>
        </div>
      </div>

      {/* Repositories Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold tracking-tight text-slate-900 dark:text-zinc-100">
              Indexed Repositories
            </h2>
            <p className="text-xs text-slate-500 dark:text-zinc-400">
              Select any codebase to begin interactive analysis
            </p>
          </div>
          <Button
            onClick={() => setOpenModal(true)}
            variant="outline"
            size="sm"
            className="bg-white hover:bg-slate-100 border-slate-300 text-slate-700 dark:bg-transparent dark:border-zinc-800 dark:hover:bg-zinc-900 dark:text-zinc-300 text-xs gap-1.5 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Repo</span>
          </Button>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="h-44 bg-zinc-900/50 rounded-2xl animate-pulse border border-zinc-800/60" />
            <div className="h-44 bg-zinc-900/50 rounded-2xl animate-pulse border border-zinc-800/60" />
            <div className="h-44 bg-zinc-900/50 rounded-2xl animate-pulse border border-zinc-800/60" />
          </div>
        ) : repos.length === 0 ? (
          <EmptyState onAddRepo={() => setOpenModal(true)} />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repos.map((repo) => (
              <RepoCard key={repo.id} repo={repo} />
            ))}
          </div>
        )}
      </div>

      {/* Ingest Modal */}
      <RepoFormDialog open={openModal} onOpenChange={setOpenModal} />
    </div>
  );
}


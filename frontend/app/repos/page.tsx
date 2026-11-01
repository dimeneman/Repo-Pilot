"use client";

import React, { useState } from "react";
import { Plus, Search, Layers, RefreshCw } from "lucide-react";
import { useRepos } from "@/hooks/use-repos";
import { RepoCard } from "@/components/repo-card";
import { EmptyState } from "@/components/empty-state";
import { RepoFormDialog } from "@/components/repo-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ReposPage() {
  const { repos, isLoading, mutate } = useRepos();
  const [openModal, setOpenModal] = useState(false);
  const [search, setSearch] = useState("");

  const filtered = repos.filter(
    (r) =>
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      r.owner.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-full bg-zinc-950 p-6 md:p-10 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-850">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
            Repositories ({repos.length})
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Manage your indexed GitHub codebases and monitoring status.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => mutate()}
            className="border-zinc-800 text-zinc-300 hover:text-zinc-100 hover:bg-zinc-900 h-9 text-xs gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </Button>

          <Button
            onClick={() => setOpenModal(true)}
            size="sm"
            className="bg-indigo-600 hover:bg-indigo-500 text-white h-9 text-xs gap-1.5 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add Repository</span>
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="max-w-md">
        <div className="relative">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-2.5" />
          <Input
            placeholder="Filter repositories by name or owner..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9 text-xs bg-zinc-900 border-zinc-800 text-zinc-200 placeholder:text-zinc-500"
          />
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="h-44 bg-zinc-900/50 rounded-2xl animate-pulse border border-zinc-800/60" />
          <div className="h-44 bg-zinc-900/50 rounded-2xl animate-pulse border border-zinc-800/60" />
          <div className="h-44 bg-zinc-900/50 rounded-2xl animate-pulse border border-zinc-800/60" />
        </div>
      ) : repos.length === 0 ? (
        <EmptyState onAddRepo={() => setOpenModal(true)} />
      ) : filtered.length === 0 ? (
        <div className="p-8 text-center text-xs text-zinc-400">
          No repositories found matching &ldquo;{search}&rdquo;.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((repo) => (
            <RepoCard key={repo.id} repo={repo} />
          ))}
        </div>
      )}

      {/* Ingest Modal */}
      <RepoFormDialog open={openModal} onOpenChange={setOpenModal} />
    </div>
  );
}


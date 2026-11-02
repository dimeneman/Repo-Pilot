"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  Github,
  RefreshCw,
  Trash2,
  ExternalLink,
  ChevronRight,
  FileCode,
  FileText,
  BarChart2,
  LogOut,
} from "lucide-react";
import { type RepoResponse, repos } from "@/lib/api";
import { useGitHubAuth } from "@/hooks/use-github-auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/theme-toggle";

interface HeaderProps {
  repo?: RepoResponse | null;
  onRefresh?: () => void;
  onSelectSummary?: () => void;
}

export function Header({ repo, onRefresh, onSelectSummary }: HeaderProps) {
  const router = useRouter();
  const { user: githubUser, isConnected, logout } = useGitHubAuth();
  const [isDeleting, setIsDeleting] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);

  const handleDelete = async () => {
    if (!repo) return;
    if (!confirm(`Are you sure you want to delete ${repo.owner}/${repo.name}?`)) {
      return;
    }
    setIsDeleting(true);
    try {
      await repos.delete(repo.id);
      router.push("/repos");
    } catch (err: any) {
      alert("Failed to delete repository: " + err.message);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleReindex = async () => {
    if (!repo) return;
    setIsReindexing(true);
    try {
      await repos.reindex(repo.id);
      if (onRefresh) onRefresh();
    } catch (err: any) {
      alert("Failed to reindex: " + err.message);
    } finally {
      setIsReindexing(false);
    }
  };

  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-950/70 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-10 select-none">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-xs">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-zinc-400 hover:text-zinc-200 transition-colors mr-0.5 group"
          title="RepoPilot Home"
        >
          <div className="w-6 h-6 rounded-md bg-zinc-900 border border-zinc-800 flex items-center justify-center p-0.5 group-hover:border-indigo-500/50 transition-colors">
            <Image
              src="/logo.png"
              alt="RepoPilot"
              width={20}
              height={20}
              className="w-full h-full object-contain"
            />
          </div>
        </Link>
        <ChevronRight className="w-3 h-3 text-zinc-600" />
        <Link
          href="/repos"
          className="text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          Repositories
        </Link>
        {repo && (
          <>
            <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
            <div className="flex items-center gap-1.5 font-medium text-zinc-100">
              <Github className="w-3.5 h-3.5 text-zinc-400" />
              <span>{repo.owner}</span>
              <span className="text-zinc-500">/</span>
              <span className="text-indigo-400 font-semibold">{repo.name}</span>
            </div>
            <Badge
              variant="outline"
              className={`ml-2 text-[10px] uppercase font-semibold tracking-wider ${
                repo.status === "ready"
                  ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                  : repo.status === "failed"
                  ? "border-red-500/30 text-red-400 bg-red-500/10"
                  : "border-amber-500/30 text-amber-400 bg-amber-500/10 animate-pulse"
              }`}
            >
              {repo.status}
            </Badge>
          </>
        )}
      </div>

      {/* Actions */}
      {repo && (
        <div className="flex items-center gap-2">
          {onSelectSummary && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onSelectSummary}
              className="h-8 text-xs text-zinc-300 hover:text-zinc-100 hover:bg-zinc-900 gap-1.5"
            >
              <BarChart2 className="w-3.5 h-3.5 text-indigo-400" />
              <span>Summary</span>
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={handleReindex}
            disabled={isReindexing || (repo.status !== "ready" && repo.status !== "failed")}
            className="h-8 text-xs text-zinc-300 hover:text-zinc-100 hover:bg-zinc-900 gap-1.5"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-zinc-400 ${
                isReindexing ? "animate-spin" : ""
              }`}
            />
            <span>Re-index</span>
          </Button>

          <a
            href={repo.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center h-8 px-2.5 rounded-md text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 transition-colors gap-1.5"
          >
            <span>GitHub</span>
            <ExternalLink className="w-3 h-3 text-zinc-500" />
          </a>

          <ThemeToggle />

          {isConnected && githubUser && (
            <div className="flex items-center gap-1.5 pl-2 border-l border-zinc-800">
              {githubUser.avatar_url ? (
                <img
                  src={githubUser.avatar_url}
                  alt={githubUser.login}
                  className="w-5 h-5 rounded-full border border-zinc-700 flex-shrink-0"
                />
              ) : (
                <div className="w-5 h-5 rounded-full bg-indigo-600 flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0">
                  {githubUser.login.charAt(0).toUpperCase()}
                </div>
              )}
              <span className="text-zinc-300 hidden md:inline text-xs font-medium">
                @{githubUser.login}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="h-7 px-1.5 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 text-xs gap-1 transition-colors"
                title="Log out of GitHub account"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden lg:inline text-xs">Log out</span>
              </Button>
            </div>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={handleDelete}
            disabled={isDeleting}
            className="h-8 text-xs text-red-400 hover:text-red-300 hover:bg-red-950/40 gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      )}
    </header>
  );
}


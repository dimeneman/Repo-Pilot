"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Compass,
  GitBranch,
  Github,
  Plus,
  Layers,
  Database,
  ExternalLink,
  ChevronRight,
  Sparkles,
  UserCheck,
  LogOut,
} from "lucide-react";
import { useRepos } from "@/hooks/use-repos";
import { useGitHubAuth } from "@/hooks/use-github-auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { RepoFormDialog } from "@/components/repo-form";
import { ThemeToggle } from "@/components/theme-toggle";

export function Sidebar() {
  const pathname = usePathname();
  const { repos, isLoading } = useRepos();
  const { user: githubUser, isConnected, logout } = useGitHubAuth();
  const [openModal, setOpenModal] = useState(false);
  const [modalDefaultTab, setModalDefaultTab] = useState<"github" | "manual">("github");

  return (
    <>
      <aside className="w-64 border-r border-zinc-800 bg-zinc-950 flex flex-col h-full select-none">
        {/* Brand Header */}
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800/80 flex items-center justify-center p-1 shadow-sm shadow-indigo-500/10 group-hover:scale-105 group-hover:border-indigo-500/40 transition-all overflow-hidden">
              <Image
                src="/logo.png"
                alt="RepoPilot Logo"
                width={32}
                height={32}
                priority
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <span className="font-bold tracking-tight text-zinc-100 flex items-center gap-1">
                RepoPilot
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  v1.0
                </span>
              </span>
              <p className="text-[11px] text-zinc-400">Codebase RAG Assistant</p>
            </div>
          </Link>
        </div>

        {/* Action Button */}
        <div className="p-3">
          <Button
            onClick={() => setOpenModal(true)}
            className="w-full justify-start gap-2 bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm"
            size="sm"
          >
            <Plus className="w-4 h-4" />
            <span>Index Repository</span>
          </Button>
        </div>

        {/* Navigation Section */}
        <div className="px-3 py-1">
          <div className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1">
            Navigation
          </div>
          <nav className="space-y-1">
            <Link
              href="/"
              className={`flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium transition-colors ${
                pathname === "/"
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
              }`}
            >
              <Compass className="w-4 h-4 text-zinc-400" />
              <span>Dashboard</span>
            </Link>
            <Link
              href="/repos"
              className={`flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium transition-colors ${
                pathname === "/repos"
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
              }`}
            >
              <Layers className="w-4 h-4 text-zinc-400" />
              <span>Repositories</span>
              {repos.length > 0 && (
                <span className="ml-auto text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded-full">
                  {repos.length}
                </span>
              )}
            </Link>
          </nav>
        </div>

        {/* Repositories List */}
        <div className="flex-1 flex flex-col min-h-0 mt-3 px-3">
          <div className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1 flex items-center justify-between">
            <span>Indexed Codebases</span>
          </div>

          <ScrollArea className="flex-1 -mx-1 px-1">
            <div className="space-y-1 py-1">
              {isLoading ? (
                <div className="space-y-2 p-2">
                  <div className="h-7 bg-zinc-900 rounded animate-pulse" />
                  <div className="h-7 bg-zinc-900 rounded animate-pulse" />
                  <div className="h-7 bg-zinc-900 rounded animate-pulse" />
                </div>
              ) : repos.length === 0 ? (
                <div className="p-3 text-center text-xs text-zinc-400 border border-dashed border-zinc-800/80 rounded-md">
                  No repositories yet.
                </div>
              ) : (
                repos.map((repo) => {
                  const isActive = pathname === `/repos/${repo.id}`;
                  return (
                    <Link
                      key={repo.id}
                      href={`/repos/${repo.id}`}
                      className={`group flex items-center justify-between px-2.5 py-2 rounded-md text-xs transition-colors ${
                        isActive
                          ? "bg-indigo-950/40 text-indigo-200 border border-indigo-800/40 font-medium"
                          : "text-zinc-300 hover:bg-zinc-900 hover:text-zinc-100"
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <Github className="w-3.5 h-3.5 text-zinc-400 group-hover:text-zinc-300 flex-shrink-0" />
                        <span className="truncate">{repo.name}</span>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {repo.status === "ready" ? (
                          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        ) : repo.status === "failed" ? (
                          <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                        ) : (
                          <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                        )}
                      </div>
                    </Link>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </div>

        {/* GitHub Account Section */}
        <div className="p-3 border-t border-zinc-800 bg-zinc-950/40">
          {isConnected && githubUser ? (
            <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs">
              <div className="flex items-center gap-2 min-w-0">
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
                <span
                  className="text-zinc-200 font-medium truncate max-w-[85px]"
                  title={`@${githubUser.login}`}
                >
                  @{githubUser.login}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="h-6 px-1.5 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 text-[11px] gap-1 transition-colors flex-shrink-0"
                title="Log out of GitHub account"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Log out</span>
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setModalDefaultTab("github");
                setOpenModal(true);
              }}
              className="w-full border-zinc-800 hover:bg-zinc-900 text-zinc-300 text-xs h-8 gap-2 justify-center"
            >
              <Github className="w-3.5 h-3.5" />
              <span>Connect GitHub</span>
            </Button>
          )}
        </div>

        {/* Footer info & Theme Toggle */}
        <div className="p-3 border-t border-zinc-800 text-[11px] text-zinc-400 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
            RAG Online
          </span>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="hover:text-zinc-300 flex items-center gap-1 text-[11px]"
              title="GitHub"
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </aside>

      {/* Ingest Modal */}
      <RepoFormDialog
        open={openModal}
        onOpenChange={setOpenModal}
        defaultTab={modalDefaultTab}
      />
    </>
  );
}


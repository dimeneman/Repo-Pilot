"use client";

import React from "react";
import Link from "next/link";
import { Github, FileCode, Layers, ArrowUpRight, Clock } from "lucide-react";
import { type RepoResponse } from "@/lib/api";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, getLanguageColor } from "@/lib/utils";

interface RepoCardProps {
  repo: RepoResponse;
}

export function RepoCard({ repo }: RepoCardProps) {
  const languageStats = repo.language_stats || {};
  const totalLangFiles = Object.values(languageStats).reduce((a, b) => a + b, 0);

  return (
    <Link href={`/repos/${repo.id}`} className="block group h-full">
      <Card className="h-full flex flex-col justify-between bg-zinc-950/80 border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/40 transition-all duration-200 shadow-sm">
        <CardHeader className="p-5 pb-3">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1 truncate">
              <div className="flex items-center gap-1.5 text-xs text-zinc-400">
                <Github className="w-3.5 h-3.5" />
                <span>{repo.owner}</span>
              </div>
              <h3 className="font-semibold text-base text-zinc-100 group-hover:text-indigo-400 transition-colors truncate">
                {repo.name}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={`text-[10px] uppercase font-semibold tracking-wider ${
                  repo.status === "ready"
                    ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                    : repo.status === "failed"
                    ? "border-red-500/30 text-red-400 bg-red-500/10"
                    : "border-amber-500/30 text-amber-400 bg-amber-500/10 animate-pulse"
                }`}
              >
                {repo.status}
              </Badge>
              <ArrowUpRight className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-5 pt-0 space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-2 gap-2 py-2 px-3 bg-zinc-900/60 rounded-lg border border-zinc-800/50 text-xs">
            <div className="flex items-center gap-2">
              <FileCode className="w-3.5 h-3.5 text-zinc-400" />
              <span className="text-zinc-400">{repo.file_count} files</span>
            </div>
            <div className="flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-zinc-400" />
              <span className="text-zinc-400">{repo.chunk_count} chunks</span>
            </div>
          </div>

          {/* Languages bar */}
          {totalLangFiles > 0 && (
            <div className="space-y-1.5">
              <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden flex">
                {Object.entries(languageStats).map(([lang, count]) => {
                  const pct = (count / totalLangFiles) * 100;
                  return (
                    <div
                      key={lang}
                      style={{
                        width: `${pct}%`,
                        backgroundColor: getLanguageColor(lang),
                      }}
                      title={`${lang}: ${Math.round(pct)}%`}
                    />
                  );
                })}
              </div>

              <div className="flex items-center gap-3 text-[11px] text-zinc-400 flex-wrap">
                {Object.entries(languageStats)
                  .slice(0, 3)
                  .map(([lang, count]) => (
                    <div key={lang} className="flex items-center gap-1.5">
                      <span
                        className="w-2 h-2 rounded-full inline-block"
                        style={{ backgroundColor: getLanguageColor(lang) }}
                      />
                      <span>{lang}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Timestamp */}
          <div className="flex items-center gap-1.5 text-[11px] text-zinc-400 pt-1 border-t border-zinc-900">
            <Clock className="w-3 h-3" />
            <span>
              {repo.last_indexed_at
                ? `Indexed ${formatDate(repo.last_indexed_at)}`
                : `Created ${formatDate(repo.created_at)}`}
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}


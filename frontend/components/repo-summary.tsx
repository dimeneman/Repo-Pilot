"use client";

import React, { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  FileText,
  Layers,
  FileCode,
  Network,
  Cpu,
  FolderTree,
} from "lucide-react";
import { type RepoResponse } from "@/lib/api";
import { MermaidDiagram } from "@/components/mermaid-diagram";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { getLanguageColor } from "@/lib/utils";

interface RepoSummaryProps {
  repo: RepoResponse;
  summaryContent?: string | null;
  mermaidDiagram?: string | null;
  techStack?: string[];
}

export function RepoSummaryView({
  repo,
  summaryContent,
  mermaidDiagram,
  techStack,
}: RepoSummaryProps) {
  const languages = repo.language_stats || {};

  // If mermaidDiagram is provided separately, remove ```mermaid ... ``` from summary text to avoid duplication
  const cleanSummaryContent = useMemo(() => {
    if (!summaryContent) return null;
    if (mermaidDiagram) {
      return summaryContent.replace(/```mermaid\n[\s\S]*?\n```/g, "").trim();
    }
    return summaryContent;
  }, [summaryContent, mermaidDiagram]);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-50 via-white to-slate-50 dark:from-zinc-900 dark:to-zinc-950 border border-slate-200 dark:border-zinc-800 space-y-4 shadow-sm dark:shadow-xl transition-colors">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
              Architecture & System Overview
            </span>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-zinc-100 mt-1">
              {repo.owner} / {repo.name}
            </h2>
          </div>
          <Badge variant="outline" className="text-xs px-2.5 py-1 border-indigo-200 dark:border-indigo-500/40 text-indigo-700 dark:text-indigo-300 bg-indigo-50/60 dark:bg-indigo-950/30">
            {repo.default_branch || "main"}
          </Badge>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-3 gap-3 pt-2">
          <div className="p-3 bg-white dark:bg-zinc-950/70 border border-slate-200 dark:border-zinc-850 rounded-xl shadow-xs">
            <div className="text-[11px] text-slate-500 dark:text-zinc-400">Total Indexed Files</div>
            <div className="text-lg font-bold text-slate-900 dark:text-zinc-100 mt-0.5">{repo.file_count}</div>
          </div>
          <div className="p-3 bg-white dark:bg-zinc-950/70 border border-slate-200 dark:border-zinc-850 rounded-xl shadow-xs">
            <div className="text-[11px] text-slate-500 dark:text-zinc-400">Code Chunks</div>
            <div className="text-lg font-bold text-slate-900 dark:text-zinc-100 mt-0.5">{repo.chunk_count}</div>
          </div>
          <div className="p-3 bg-white dark:bg-zinc-950/70 border border-slate-200 dark:border-zinc-850 rounded-xl shadow-xs">
            <div className="text-[11px] text-slate-500 dark:text-zinc-400">Primary Language</div>
            <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400 mt-0.5">
              {Object.keys(languages)[0] || "Code"}
            </div>
          </div>
        </div>

        {/* Tech Stack Chips */}
        {Object.keys(languages).length > 0 && (
          <div className="pt-2 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-500 dark:text-zinc-400 font-medium">Stack:</span>
            {Object.entries(languages).map(([lang, count]) => (
              <Badge
                key={lang}
                variant="outline"
                className="text-xs border-slate-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 text-slate-700 dark:text-zinc-300 gap-1.5 shadow-xs"
              >
                <span
                  className="w-2 h-2 rounded-full inline-block"
                  style={{ backgroundColor: getLanguageColor(lang) }}
                />
                <span>{lang}</span>
                <span className="text-[10px] text-slate-400 dark:text-zinc-500">({count})</span>
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Mermaid Diagram if available */}
      {mermaidDiagram && (
        <Card className="bg-white dark:bg-zinc-950 border-slate-200 dark:border-zinc-800 shadow-sm">
          <CardHeader className="p-4 border-b border-slate-200 dark:border-zinc-850">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-zinc-200">
              <Network className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Grounded Repository Architecture Diagram</span>
            </div>
          </CardHeader>
          <CardContent className="p-4">
            <MermaidDiagram chart={mermaidDiagram} />
          </CardContent>
        </Card>
      )}

      {/* Summary Markdown Output */}
      {cleanSummaryContent && (
        <Card className="bg-white dark:bg-zinc-950 border-slate-200 dark:border-zinc-800 shadow-sm">
          <CardContent className="p-6 prose dark:prose-invert max-w-none text-xs md:text-sm leading-relaxed text-slate-800 dark:text-zinc-200">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || "");
                  const codeString = String(children).replace(/\n$/, "");

                  if (!inline && match && match[1] === "mermaid") {
                    return <MermaidDiagram chart={codeString} />;
                  }

                  return (
                    <code
                      className="font-mono text-[12px] bg-slate-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-slate-800 dark:text-zinc-200 border border-slate-200 dark:border-zinc-700/60"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                },
              }}
            >
              {cleanSummaryContent}
            </ReactMarkdown>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

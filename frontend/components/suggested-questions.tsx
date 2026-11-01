"use client";

import React from "react";
import { Sparkles } from "lucide-react";
import { type AssistantMode } from "@/components/mode-selector";

interface SuggestedQuestionsProps {
  mode: AssistantMode;
  onSelect: (question: string) => void;
}

const SUGGESTIONS: Record<AssistantMode, string[]> = {
  chat: [
    "Where is authentication and token validation implemented?",
    "Explain the primary entrypoint and server lifecycle flow.",
    "Which files handle database connection and models?",
    "Show me how errors and exceptions are handled in this codebase.",
  ],
  summary: [
    "Generate an executive architecture summary with tech stack overview.",
  ],
  api_discovery: [
    "Catalog all public API endpoints, routes, methods, and controllers.",
  ],
  readme: [
    "Generate a complete, production-grade README.md for this repository.",
  ],
  bug_scan: [
    "Perform a code quality, edge-case, and security audit on indexed files.",
  ],
  architecture: [
    "Generate a system architecture breakdown with a Mermaid component diagram.",
  ],
};

export function SuggestedQuestions({ mode, onSelect }: SuggestedQuestionsProps) {
  const list = SUGGESTIONS[mode] || SUGGESTIONS.chat;

  return (
    <div className="space-y-2 select-none">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-zinc-400 uppercase tracking-wider px-1">
        <Sparkles className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
        <span>Suggested Queries</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {list.map((q, idx) => (
          <button
            key={idx}
            onClick={() => onSelect(q)}
            className="text-left p-3 rounded-lg bg-white dark:bg-zinc-900/60 border border-slate-200/90 dark:border-zinc-800/80 hover:border-indigo-300 dark:hover:border-zinc-700 hover:bg-slate-50 dark:hover:bg-zinc-800/40 text-xs text-slate-700 dark:text-zinc-300 hover:text-slate-900 dark:hover:text-zinc-100 shadow-sm transition-all flex items-center justify-between group"
          >
            <span className="leading-relaxed">{q}</span>
            <span className="text-slate-400 dark:text-zinc-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all text-sm ml-2 flex-shrink-0">
              →
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}


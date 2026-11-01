"use client";

import React from "react";
import {
  MessageSquare,
  FileText,
  Plug,
  FileCode,
  Bug,
  Network,
} from "lucide-react";

export type AssistantMode =
  | "chat"
  | "summary"
  | "api_discovery"
  | "readme"
  | "bug_scan"
  | "architecture";

interface ModeSelectorProps {
  activeMode: AssistantMode;
  onSelectMode: (mode: AssistantMode) => void;
}

const MODES: { id: AssistantMode; label: string; icon: React.ElementType }[] = [
  { id: "chat", label: "Chat Q&A", icon: MessageSquare },
  { id: "summary", label: "Summary", icon: FileText },
  { id: "api_discovery", label: "API Catalog", icon: Plug },
  { id: "readme", label: "README Gen", icon: FileCode },
  { id: "bug_scan", label: "Audit & Bugs", icon: Bug },
  { id: "architecture", label: "Architecture", icon: Network },
];

export function ModeSelector({ activeMode, onSelectMode }: ModeSelectorProps) {
  return (
    <div className="flex items-center gap-1.5 p-1 bg-zinc-900/90 border border-zinc-800 rounded-lg overflow-x-auto scrollbar-none">
      {MODES.map((mode) => {
        const Icon = mode.icon;
        const isActive = activeMode === mode.id;
        return (
          <button
            key={mode.id}
            onClick={() => onSelectMode(mode.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all whitespace-nowrap ${
              isActive
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60"
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span>{mode.label}</span>
          </button>
        );
      })}
    </div>
  );
}


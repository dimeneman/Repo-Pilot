"use client";

import React, { useState } from "react";
import { FileCode, Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import { type SourceCitation } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface CitationCardProps {
  citation: SourceCitation;
  defaultExpanded?: boolean;
}

export function CitationCard({ citation, defaultExpanded = false }: CitationCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(citation.snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-zinc-800 bg-zinc-950/70 rounded-lg overflow-hidden text-xs transition-colors hover:border-zinc-700">
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="p-2.5 flex items-center justify-between cursor-pointer bg-zinc-900/50 hover:bg-zinc-900 select-none transition-colors"
      >
        <div className="flex items-center gap-2 truncate mr-2">
          <FileCode className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
          <span className="font-mono text-zinc-200 truncate font-medium">
            {citation.file_path}
          </span>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <Badge
            variant="outline"
            className="text-[10px] font-mono px-1.5 py-0.5 border-zinc-700 bg-zinc-800/80 text-zinc-300"
          >
            L{citation.start_line}-L{citation.end_line}
          </Badge>

          {citation.relevance_score !== null && (
            <span className="text-[10px] text-zinc-400 font-mono">
              {(citation.relevance_score * 100).toFixed(0)}%
            </span>
          )}

          <button
            onClick={handleCopy}
            className="p-1 hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-200"
            title="Copy snippet"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          </button>

          {expanded ? (
            <ChevronUp className="w-3.5 h-3.5 text-zinc-400" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />
          )}
        </div>
      </div>

      {/* Snippet body */}
      {expanded && (
        <div className="p-3 bg-zinc-950 border-t border-zinc-850 overflow-x-auto">
          <pre className="font-mono text-[11px] text-zinc-300 leading-relaxed whitespace-pre">
            {citation.snippet}
          </pre>
        </div>
      )}
    </div>
  );
}


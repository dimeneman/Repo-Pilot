"use client";

import React from "react";
import { BookOpen, X, Layers } from "lucide-react";
import { type SourceCitation } from "@/lib/api";
import { CitationCard } from "@/components/citation-card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";

interface CitationPanelProps {
  citations: SourceCitation[];
  onClose?: () => void;
}

export function CitationPanel({ citations, onClose }: CitationPanelProps) {
  return (
    <aside className="w-80 border-l border-zinc-800 bg-zinc-950 flex flex-col h-full">
      <div className="p-3.5 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-zinc-100">
            Source Citations ({citations.length})
          </span>
        </div>
        {onClose && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="w-7 h-7 text-zinc-400 hover:text-zinc-200"
          >
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1 p-3">
        {citations.length === 0 ? (
          <div className="p-6 text-center text-xs text-zinc-400">
            No source citations referenced in this turn.
          </div>
        ) : (
          <div className="space-y-2.5">
            {citations.map((c, idx) => (
              <CitationCard key={idx} citation={c} defaultExpanded={idx === 0} />
            ))}
          </div>
        )}
      </ScrollArea>
    </aside>
  );
}


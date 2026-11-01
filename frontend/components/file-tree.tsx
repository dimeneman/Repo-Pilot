"use client";

import React, { useState } from "react";
import { Folder, FolderOpen, FileCode, Search, FileText } from "lucide-react";
import { type FileResponse } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getLanguageColor } from "@/lib/utils";

interface FileTreeProps {
  files: FileResponse[];
  onSelectFile?: (path: string) => void;
}

export function FileTree({ files, onSelectFile }: FileTreeProps) {
  const [filter, setFilter] = useState("");

  const filtered = files.filter((f) =>
    f.path.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden">
      {/* Search Header */}
      <div className="p-3 border-b border-zinc-800 bg-zinc-900/40">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-2.5" />
          <Input
            placeholder="Search indexed files..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-8 h-8 text-xs bg-zinc-900 border-zinc-800 text-zinc-200 placeholder:text-zinc-500"
          />
        </div>
      </div>

      {/* Files List */}
      <ScrollArea className="flex-1 p-2">
        <div className="space-y-0.5">
          {filtered.length === 0 ? (
            <div className="p-4 text-center text-xs text-zinc-400">
              No files match your query.
            </div>
          ) : (
            filtered.map((file) => (
              <button
                key={file.id}
                onClick={() => onSelectFile && onSelectFile(file.path)}
                className="w-full text-left px-2.5 py-1.5 rounded-md hover:bg-zinc-900 flex items-center justify-between text-xs text-zinc-300 hover:text-zinc-100 transition-colors group"
              >
                <div className="flex items-center gap-2 truncate">
                  <FileCode className="w-3.5 h-3.5 text-zinc-500 group-hover:text-indigo-400 flex-shrink-0" />
                  <span className="truncate font-mono text-[11px]">{file.path}</span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {file.language && (
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ backgroundColor: getLanguageColor(file.language) }}
                      title={file.language}
                    />
                  )}
                  <span className="text-[10px] text-zinc-400 font-mono">
                    {file.line_count}L
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}


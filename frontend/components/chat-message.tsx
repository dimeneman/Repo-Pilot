"use client";

import React, { useState } from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, FileCode, Bot, User, Sparkles } from "lucide-react";
import { type Message } from "@/hooks/use-chat";
import { MermaidDiagram } from "@/components/mermaid-diagram";
import { CitationCard } from "@/components/citation-card";

interface ChatMessageProps {
  message: Message;
  onCitationClick?: (filePath: string) => void;
}

export function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`py-6 px-4 md:px-8 flex gap-4 ${
        isUser ? "bg-zinc-950" : "bg-zinc-900/40 border-y border-zinc-850"
      }`}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isUser ? (
          <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300">
            <User className="w-4 h-4" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center p-1 shadow-md shadow-indigo-500/10 overflow-hidden">
            <Image
              src="/logo.png"
              alt="RepoPilot Assistant"
              width={28}
              height={28}
              className="w-full h-full object-contain"
            />
          </div>
        )}
      </div>

      {/* Message Content */}
      <div className="flex-1 min-w-0 space-y-3">
        {/* Header row */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-200">
            {isUser ? "You" : "RepoPilot Assistant"}
          </span>
          {message.mode && message.mode !== "chat" && (
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              {message.mode}
            </span>
          )}
          {message.processingTimeMs && (
            <span className="text-[11px] text-zinc-400 font-mono">
              {message.processingTimeMs}ms
            </span>
          )}
        </div>

        {/* Markdown rendering */}
        <div className="prose prose-invert prose-zinc max-w-none text-xs md:text-sm leading-relaxed prose-pre:p-0 prose-pre:bg-transparent">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Custom code block renderer
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || "");
                const codeString = String(children).replace(/\n$/, "");

                // Check for Mermaid diagram
                if (!inline && match && match[1] === "mermaid") {
                  return <MermaidDiagram chart={codeString} />;
                }

                if (!inline && match) {
                  return <CodeBlock language={match[1]} value={codeString} />;
                }

                // Inline citations or inline code
                const citationMatch = codeString.match(/^\[FILE:([^:]+):L(\d+)(?:-L?(\d+))?\]$/);
                if (citationMatch) {
                  const path = citationMatch[1];
                  const start = citationMatch[2];
                  const end = citationMatch[3] || start;
                  return (
                    <button
                      onClick={() => onCitationClick && onCitationClick(path)}
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 font-mono text-xs hover:bg-indigo-900 transition-colors mx-0.5"
                    >
                      <FileCode className="w-3 h-3 text-indigo-400" />
                      <span>{path}</span>
                      <span className="text-indigo-400 font-bold">L{start}-{end}</span>
                    </button>
                  );
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
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Standalone Mermaid diagram if passed from schema */}
        {message.mermaidDiagram && !message.content.includes("```mermaid") && (
          <MermaidDiagram chart={message.mermaidDiagram} />
        )}

        {/* Attached Sources if assistant */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="pt-3 border-t border-zinc-800/80 space-y-2">
            <div className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
              <FileCode className="w-3.5 h-3.5 text-indigo-400" />
              <span>Grounded Citations ({message.sources.length})</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {message.sources.slice(0, 4).map((citation, idx) => (
                <CitationCard key={idx} citation={citation} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CodeBlock({ language, value }: { language: string; value: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-lg border border-zinc-800 bg-zinc-950 overflow-hidden text-xs">
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-900 border-b border-zinc-800 text-zinc-400">
        <span className="font-mono text-[11px] uppercase">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[11px] hover:text-zinc-200 transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className="p-3 overflow-x-auto font-mono text-[12px] text-zinc-200 leading-relaxed">
        {value}
      </pre>
    </div>
  );
}


"use client";

import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { Send, Loader2, Sparkles, Layers, BookOpen, RefreshCw } from "lucide-react";
import { useChat } from "@/hooks/use-chat";
import { type RepoResponse } from "@/lib/api";
import { ModeSelector, type AssistantMode } from "@/components/mode-selector";
import { SuggestedQuestions } from "@/components/suggested-questions";
import { ChatMessage } from "@/components/chat-message";
import { CitationPanel } from "@/components/citation-panel";
import { Button } from "@/components/ui/button";

interface ChatInterfaceProps {
  repo: RepoResponse;
}

export function ChatInterface({ repo }: ChatInterfaceProps) {
  const [mode, setMode] = useState<AssistantMode>("chat");
  const { messages, sendMessage, isLoading, error, clearMessages } = useChat(repo.id, mode);
  const [input, setInput] = useState("");
  const [showCitationPanel, setShowCitationPanel] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (questionToSend?: string) => {
    const q = (questionToSend || input).trim();
    if (!q || isLoading) return;

    setInput("");
    await sendMessage(q, mode);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Get active citations from last assistant message in the active mode
  const lastAssistantMessage = [...messages].reverse().find((m) => m.role === "assistant");
  const activeCitations = lastAssistantMessage?.sources || [];

  return (
    <div className="flex h-full overflow-hidden bg-zinc-950">
      {/* Main chat column */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* Top Mode Bar */}
        <div className="p-3 border-b border-zinc-850 bg-zinc-950/70 backdrop-blur-sm flex items-center justify-between gap-3">
          <ModeSelector activeMode={mode} onSelectMode={setMode} />
          <div className="flex items-center gap-2 flex-shrink-0">
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => clearMessages()}
                className="text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/80 h-8 px-2.5 gap-1.5"
                title={`Clear ${mode} conversation`}
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Clear</span>
              </Button>
            )}
            {activeCitations.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCitationPanel(!showCitationPanel)}
                className="border-zinc-800 text-xs text-zinc-300 hover:text-zinc-100 hover:bg-zinc-900 gap-1.5 h-8 flex-shrink-0"
              >
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                <span>Citations ({activeCitations.length})</span>
              </Button>
            )}
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {messages.length === 0 ? (
            <div className="max-w-2xl mx-auto py-12 px-4 space-y-8">
              <div className="text-center space-y-2">
                <div className="inline-flex p-2.5 rounded-2xl bg-indigo-50/80 border border-indigo-100 dark:bg-zinc-900 dark:border-zinc-800 mb-2 shadow-sm">
                  <Image
                    src="/logo.png"
                    alt="RepoPilot Logo"
                    width={36}
                    height={36}
                    className="w-9 h-9 object-contain"
                  />
                </div>
                <h3 className="text-lg font-bold tracking-tight text-slate-900 dark:text-zinc-100">
                  Ask anything about {repo.name}
                </h3>
                <p className="text-xs text-slate-600 dark:text-zinc-400 max-w-md mx-auto">
                  Every answer is strictly retrieved and grounded in source files, complete with file paths and line ranges.
                </p>
              </div>

              <SuggestedQuestions
                mode={mode}
                onSelect={(question) => handleSend(question)}
              />
            </div>
          ) : (
            <div className="divide-y divide-zinc-850">
              {messages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}
              {isLoading && (
                <div className="p-6 bg-zinc-900/30 flex items-center gap-3 text-xs text-zinc-400">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                  <span>Synthesizing codebase context and verifying source citations...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Error notification */}
        {error && (
          <div className="px-4 py-2 bg-red-950/40 border-t border-red-900/50 text-red-300 text-xs">
            {error}
          </div>
        )}

        {/* Input Dock */}
        <div className="p-4 border-t border-zinc-850 bg-zinc-950/90">
          <div className="max-w-4xl mx-auto relative rounded-xl border border-zinc-800 bg-zinc-900/70 focus-within:border-indigo-500/80 focus-within:ring-1 focus-within:ring-indigo-500/50 transition-all shadow-lg">
            <textarea
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                mode === "chat"
                  ? "Ask a question about the repository (e.g. 'Where is authentication handled?')..."
                  : `Ask in ${mode} mode...`
              }
              className="w-full bg-transparent px-4 py-3 text-xs md:text-sm text-zinc-100 placeholder:text-zinc-500 resize-none outline-none"
            />
            <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
              <span className="text-[11px] text-zinc-400">
                Press <kbd className="px-1 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono text-[10px]">Shift+Enter</kbd> for newline
              </span>
              <Button
                onClick={() => handleSend()}
                disabled={isLoading || !input.trim()}
                size="sm"
                className="h-8 px-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs gap-1.5 shadow-sm"
              >
                {isLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <>
                    <span>Send</span>
                    <Send className="w-3 h-3" />
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Citations Side Drawer */}
      {showCitationPanel && activeCitations.length > 0 && (
        <CitationPanel
          citations={activeCitations}
          onClose={() => setShowCitationPanel(false)}
        />
      )}
    </div>
  );
}


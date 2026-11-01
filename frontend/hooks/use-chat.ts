"use client";

import { useState, useCallback, useRef } from "react";
import { chat as chatApi, type ChatResponse, type SourceCitation } from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceCitation[];
  mode: string;
  modelUsed: string | null;
  processingTimeMs: number | null;
  mermaidDiagram: string | null;
  timestamp: Date;
}

interface UseChatReturn {
  messages: Message[];
  sendMessage: (question: string, mode?: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  clearMessages: () => void;
  clearError: () => void;
}

// ─── Unique ID Generator ────────────────────────────────────────────────────

let messageCounter = 0;
function generateId(): string {
  messageCounter += 1;
  return `msg_${Date.now()}_${messageCounter}`;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

/**
 * Custom hook for managing chat state and API interactions.
 *
 * Maintains a local message list, sends questions to the RAG backend,
 * and handles optimistic updates (user message appears immediately).
 */
export function useChat(repoId: string, activeMode: string = "chat"): UseChatReturn {
  // Store messages partitioned by mode so modes don't leak or overlap
  const [messagesByMode, setMessagesByMode] = useState<Record<string, Message[]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Active messages are the ones belonging to the selected mode
  const messages = messagesByMode[activeMode] || [];

  // Guard against concurrent sends
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (question: string, mode: string = activeMode) => {
      if (!question.trim() || isLoading) return;
      const targetMode = mode || activeMode || "chat";

      // Cancel any in-flight request
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      setError(null);
      setIsLoading(true);

      // 1. Add user message optimistically to the target mode
      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: question.trim(),
        sources: [],
        mode: targetMode,
        modelUsed: null,
        processingTimeMs: null,
        mermaidDiagram: null,
        timestamp: new Date(),
      };

      setMessagesByMode((prev) => ({
        ...prev,
        [targetMode]: [...(prev[targetMode] || []), userMessage],
      }));

      try {
        // 2. Call the RAG API
        const response: ChatResponse = await chatApi.send(
          repoId,
          question.trim(),
          targetMode
        );

        // 3. Add assistant response to the target mode
        const assistantMessage: Message = {
          id: response.query_id || generateId(),
          role: "assistant",
          content: response.answer,
          sources: response.sources ?? [],
          mode: response.mode,
          modelUsed: response.model_used,
          processingTimeMs: response.processing_time_ms,
          mermaidDiagram: response.mermaid_diagram,
          timestamp: new Date(),
        };

        setMessagesByMode((prev) => ({
          ...prev,
          [targetMode]: [...(prev[targetMode] || []), assistantMessage],
        }));
      } catch (err: unknown) {
        // Don't set error if request was intentionally aborted
        if (err instanceof DOMException && err.name === "AbortError") return;

        const errorMessage =
          err instanceof Error ? err.message : "Failed to get response";
        setError(errorMessage);

        // Add an error message to the chat so the user sees it inline
        const errorMsg: Message = {
          id: generateId(),
          role: "assistant",
          content: `⚠️ Sorry, something went wrong: ${errorMessage}`,
          sources: [],
          mode: targetMode,
          modelUsed: null,
          processingTimeMs: null,
          mermaidDiagram: null,
          timestamp: new Date(),
        };

        setMessagesByMode((prev) => ({
          ...prev,
          [targetMode]: [...(prev[targetMode] || []), errorMsg],
        }));
      } finally {
        setIsLoading(false);
      }
    },
    [repoId, activeMode, isLoading]
  );

  const clearMessages = useCallback(() => {
    setMessagesByMode((prev) => ({
      ...prev,
      [activeMode]: [],
    }));
    setError(null);
  }, [activeMode]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    messages,
    sendMessage,
    isLoading,
    error,
    clearMessages,
    clearError,
  };
}

"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import {
  MessageSquare,
  FileText,
  FolderTree,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { useRepo, useRepoFiles, useRepoSummary } from "@/hooks/use-repos";
import { Header } from "@/components/header";
import { ChatInterface } from "@/components/chat-interface";
import { RepoSummaryView } from "@/components/repo-summary";
import { FileTree } from "@/components/file-tree";
import { StatusPoller } from "@/components/status-poller";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export default function RepoDetailPage() {
  const params = useParams();
  const repoId = params?.id as string;

  const { repo, isLoading: isRepoLoading, mutate } = useRepo(repoId);
  const { files, isLoading: isFilesLoading } = useRepoFiles(repoId);
  const { summary, isLoading: isSummaryLoading, mutate: refreshSummary } = useRepoSummary(
    repo?.status === "ready" ? repoId : null
  );

  const [activeTab, setActiveTab] = useState<"chat" | "summary" | "files">("chat");

  if (isRepoLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-zinc-950">
        <div className="flex flex-col items-center gap-3 text-zinc-400 text-xs">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
          <span>Loading repository workspace...</span>
        </div>
      </div>
    );
  }

  if (!repo) {
    return (
      <div className="flex h-full items-center justify-center bg-zinc-950 p-6">
        <div className="text-center space-y-3 max-w-sm">
          <div className="w-12 h-12 rounded-xl bg-red-950/60 border border-red-800/50 flex items-center justify-center text-red-400 mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-zinc-100">Repository Not Found</h3>
          <p className="text-xs text-zinc-400">
            The repository ID &ldquo;{repoId}&rdquo; does not exist or may have been deleted.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-50/50 dark:bg-zinc-950 overflow-hidden">
      {/* Top Header */}
      <Header
        repo={repo}
        onRefresh={() => mutate()}
        onSelectSummary={() => setActiveTab("summary")}
      />

      {/* If indexing in progress, show live poller */}
      {repo.status !== "ready" && repo.status !== "failed" && (
        <div className="p-6">
          <StatusPoller repoId={repo.id} onReady={() => mutate()} />
        </div>
      )}

      {/* Failure banner */}
      {repo.status === "failed" && (
        <div className="m-6 p-4 rounded-xl bg-red-950/40 border border-red-900/60 text-red-300 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <div>
            <div className="font-semibold">Ingestion Failed</div>
            <div className="text-red-400/90 mt-0.5">{repo.error_message || "An error occurred during repository indexing."}</div>
          </div>
        </div>
      )}

      {/* Main Workspace Tabs */}
      <div className="flex-1 flex flex-col min-h-0">
        <Tabs
          value={activeTab}
          onValueChange={(v: string) => setActiveTab(v as any)}
          className="flex-1 flex flex-col min-h-0"
        >
          {/* Sub Navigation Bar */}
          <div className="px-6 border-b border-slate-200 dark:border-zinc-850 bg-white/70 dark:bg-zinc-950/60 flex items-center justify-between transition-colors">
            <TabsList className="bg-transparent h-10 p-0 space-x-4 border-none">
              <TabsTrigger
                value="chat"
                className="data-[state=active]:bg-transparent data-[state=active]:text-indigo-600 dark:data-[state=active]:text-indigo-400 data-[state=active]:border-b-2 data-[state=active]:border-indigo-600 dark:data-[state=active]:border-indigo-500 rounded-none h-10 text-xs px-1 gap-1.5 font-medium text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-200"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Chat & Citations</span>
              </TabsTrigger>

              <TabsTrigger
                value="summary"
                className="data-[state=active]:bg-transparent data-[state=active]:text-indigo-600 dark:data-[state=active]:text-indigo-400 data-[state=active]:border-b-2 data-[state=active]:border-indigo-600 dark:data-[state=active]:border-indigo-500 rounded-none h-10 text-xs px-1 gap-1.5 font-medium text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-200"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Architecture Summary</span>
              </TabsTrigger>

              <TabsTrigger
                value="files"
                className="data-[state=active]:bg-transparent data-[state=active]:text-indigo-600 dark:data-[state=active]:text-indigo-400 data-[state=active]:border-b-2 data-[state=active]:border-indigo-600 dark:data-[state=active]:border-indigo-500 rounded-none h-10 text-xs px-1 gap-1.5 font-medium text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-200"
              >
                <FolderTree className="w-3.5 h-3.5" />
                <span>Source Files ({repo.file_count})</span>
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Tab 1: Chat Workspace */}
          <TabsContent value="chat" className="flex-1 min-h-0 m-0 p-0 data-[state=active]:flex">
            <div className="flex-1 h-full min-h-0">
              <ChatInterface repo={repo} />
            </div>
          </TabsContent>

          {/* Tab 2: Architecture Summary */}
          <TabsContent value="summary" className="flex-1 overflow-y-auto m-0 p-0">
            {isSummaryLoading ? (
              <div className="p-12 text-center text-xs text-zinc-400 flex flex-col items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                <span>Generating architectural review & Mermaid diagram...</span>
              </div>
            ) : (
              <RepoSummaryView
                repo={repo}
                summaryContent={summary?.answer}
                mermaidDiagram={summary?.mermaid_diagram}
                techStack={summary?.tech_stack}
              />
            )}
          </TabsContent>

          {/* Tab 3: File Tree */}
          <TabsContent value="files" className="flex-1 min-h-0 p-6 m-0 overflow-y-auto">
            <div className="max-w-4xl mx-auto h-[600px]">
              <FileTree files={files} />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}


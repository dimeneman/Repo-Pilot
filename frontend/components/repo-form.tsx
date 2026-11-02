"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Github,
  Loader2,
  AlertCircle,
  Link as LinkIcon,
  Search,
  Lock,
  Star,
  RefreshCw,
  CheckCircle2,
  ExternalLink,
  KeyRound,
  LogOut,
} from "lucide-react";
import { repos, auth, type GitHubRepoItem } from "@/lib/api";
import { useRepos } from "@/hooks/use-repos";
import { useGitHubAuth } from "@/hooks/use-github-auth";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { getLanguageColor, formatDate } from "@/lib/utils";

interface RepoFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTab?: "github" | "manual";
}

export function RepoFormDialog({
  open,
  onOpenChange,
  defaultTab = "github",
}: RepoFormDialogProps) {
  const router = useRouter();
  const { mutate } = useRepos();
  const {
    user: githubUser,
    token: githubToken,
    isConnected,
    isLoading: isAuthLoading,
    error: authHookError,
    loginWithOAuth,
    loginWithToken,
    logout,
  } = useGitHubAuth();

  const [activeTab, setActiveTab] = useState<"github" | "manual">(defaultTab);

  // Sync activeTab when dialog opens with defaultTab
  useEffect(() => {
    if (open) {
      setActiveTab(defaultTab);
    }
  }, [open, defaultTab]);

  // Manual URL Form states
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // GitHub Repos Fetch states
  const [githubRepos, setGithubRepos] = useState<GitHubRepoItem[]>([]);
  const [isFetchingRepos, setIsFetchingRepos] = useState(false);
  const [repoSearch, setRepoSearch] = useState("");
  const [indexingRepoId, setIndexingRepoId] = useState<number | null>(null);

  // PAT Token input state
  const [patInput, setPatInput] = useState("");
  const [isConnectingPat, setIsConnectingPat] = useState(false);
  const [patError, setPatError] = useState<string | null>(null);
  const [showPatInput, setShowPatInput] = useState(false);
  const [oauthNotice, setOauthNotice] = useState<string | null>(null);

  // Fetch GitHub repos when modal opens and user is connected
  const fetchRepos = async () => {
    if (!githubToken) return;
    setIsFetchingRepos(true);
    setError(null);
    try {
      const res = await auth.getGitHubRepos(githubToken);
      setGithubRepos(res.repositories || []);
    } catch (err: any) {
      if (err?.status === 401 || err?.message?.includes("401")) {
        logout();
        setError("Your GitHub session has expired. Please sign in again.");
      } else {
        setError(err?.message || "Failed to fetch repositories from GitHub.");
      }
    } finally {
      setIsFetchingRepos(false);
    }
  };

  useEffect(() => {
    if (open && isConnected && githubToken) {
      fetchRepos();
    }
  }, [open, isConnected, githubToken]);

  // Handle Manual URL Submission
  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await repos.ingest(
        url.trim(),
        branch.trim() || undefined,
        githubToken || undefined
      );
      await mutate();
      onOpenChange(false);
      setUrl("");
      router.push(`/repos/${res.id}`);
    } catch (err: any) {
      setError(err?.message || "Failed to ingest repository. Please verify the URL.");
    } finally {
      setLoading(false);
    }
  };

  // Handle OAuth Button Click
  const handleOAuthClick = async () => {
    setError(null);
    setOauthNotice(null);
    const res = await loginWithOAuth();
    if (res && !res.configured) {
      setOauthNotice(
        res.message ||
          "GitHub OAuth App is not configured in .env. You can connect instantly using a Personal Access Token below."
      );
      setShowPatInput(true);
    }
  };

  // Handle Indexing a Selected GitHub Repo
  const handleIndexGitHubRepo = async (repoItem: GitHubRepoItem) => {
    setLoading(true);
    setIndexingRepoId(repoItem.id);
    setError(null);

    try {
      const res = await repos.ingest(
        repoItem.html_url,
        repoItem.default_branch || undefined,
        githubToken || undefined
      );
      await mutate();
      onOpenChange(false);
      router.push(`/repos/${res.id}`);
    } catch (err: any) {
      setError(err?.message || `Failed to ingest ${repoItem.full_name}.`);
    } finally {
      setLoading(false);
      setIndexingRepoId(null);
    }
  };

  // Handle PAT Login
  const handlePatLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patInput.trim()) return;

    setIsConnectingPat(true);
    setPatError(null);
    try {
      await loginWithToken(patInput.trim());
      setPatInput("");
      setShowPatInput(false);
      setOauthNotice(null);
    } catch (err: any) {
      setPatError(err?.message || "Invalid GitHub token. Please verify permissions.");
    } finally {
      setIsConnectingPat(false);
    }
  };

  // Filtered GitHub Repos
  const filteredRepos = useMemo(() => {
    if (!repoSearch.trim()) return githubRepos;
    const q = repoSearch.toLowerCase();
    return githubRepos.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        r.full_name.toLowerCase().includes(q) ||
        (r.description && r.description.toLowerCase().includes(q))
    );
  }, [githubRepos, repoSearch]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[680px] bg-white dark:bg-zinc-950 border-slate-200 dark:border-zinc-800 text-slate-900 dark:text-zinc-100 p-0 overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="p-6 pb-4 border-b border-slate-200 dark:border-zinc-850 bg-slate-50/60 dark:bg-zinc-900/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950 border border-indigo-200 dark:border-indigo-800/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-inner">
                <Github className="w-5 h-5" />
              </div>
              <div>
                <DialogTitle className="text-base md:text-lg font-semibold tracking-tight text-slate-900 dark:text-zinc-100">
                  Index GitHub Repository
                </DialogTitle>
                <DialogDescription className="text-slate-500 dark:text-zinc-400 text-xs">
                  Connect codebases to enable code-aware semantic search and citations.
                </DialogDescription>
              </div>
            </div>
          </div>

          {/* Mode Switch Tabs — 50/50 Segmented Control */}
          <div className="flex items-center gap-1.5 mt-4 p-1.5 rounded-xl bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800">
            <button
              type="button"
              onClick={() => setActiveTab("github")}
              className={`flex-1 h-10 flex items-center justify-center gap-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "github"
                  ? "bg-indigo-600 text-white shadow-sm border border-indigo-500"
                  : "text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100 hover:bg-white/80 dark:hover:bg-zinc-800/80"
              }`}
            >
              <Github className="w-4 h-4 flex-shrink-0" />
              <span>From GitHub Account</span>
              {isConnected && githubRepos.length > 0 && (
                <span
                  className={`inline-flex items-center justify-center min-w-[20px] h-4 text-[10px] font-bold px-1.5 rounded-full ${
                    activeTab === "github"
                      ? "bg-indigo-700 text-white"
                      : "bg-slate-200 text-slate-700 dark:bg-zinc-800 dark:text-zinc-300"
                  }`}
                >
                  {githubRepos.length}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("manual")}
              className={`flex-1 h-10 flex items-center justify-center gap-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "manual"
                  ? "bg-indigo-600 text-white shadow-sm border border-indigo-500"
                  : "text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100 hover:bg-white/80 dark:hover:bg-zinc-800/80"
              }`}
            >
              <LinkIcon className="w-4 h-4 flex-shrink-0" />
              <span>Paste URL Manually</span>
            </button>
          </div>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-red-950/50 border border-red-800/50 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Tab 1: GitHub Account Integration */}
        {activeTab === "github" && (
          <div className="p-6 pt-4 space-y-4">
            {!isConnected ? (
              // Not connected view
              <div className="py-6 px-4 rounded-xl bg-slate-50/60 dark:bg-zinc-900/40 border border-slate-200 dark:border-zinc-800 text-center space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 flex items-center justify-center text-slate-700 dark:text-zinc-300 mx-auto shadow-inner">
                  <Github className="w-6 h-6" />
                </div>
                <div className="space-y-1 max-w-sm mx-auto">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-zinc-100">
                    Connect your GitHub Account
                  </h4>
                  <p className="text-xs text-slate-500 dark:text-zinc-400 leading-relaxed">
                    Authenticate to view your public and private repositories, and index any codebase with one click.
                  </p>
                </div>

                {/* OAuth Notice when unconfigured */}
                {oauthNotice && (
                  <div className="p-3 mx-auto max-w-md rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/50 text-amber-800 dark:text-amber-300 text-xs text-left flex items-start gap-2.5 leading-relaxed">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
                    <div>
                      <p className="font-medium text-amber-900 dark:text-amber-200">OAuth Credentials Unconfigured</p>
                      <p className="text-[11px] text-amber-800/90 dark:text-amber-300/90 mt-0.5">
                        Set <code className="text-amber-950 dark:text-amber-100 font-mono">GITHUB_CLIENT_ID</code> in <code className="text-amber-950 dark:text-amber-100 font-mono">.env</code> to enable automatic OAuth redirection, or connect instantly using a <strong>Personal Access Token</strong> below.
                      </p>
                    </div>
                  </div>
                )}

                {authHookError && !oauthNotice && (
                  <div className="p-2.5 mx-auto max-w-md rounded-lg bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800/50 text-red-700 dark:text-red-300 text-xs text-left flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-500 dark:text-red-400" />
                    <span>{authHookError}</span>
                  </div>
                )}

                <div className="pt-2 flex flex-col items-center gap-2 max-w-xs mx-auto">
                  <Button
                    onClick={handleOAuthClick}
                    disabled={isAuthLoading}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-9 gap-2 shadow-sm font-medium"
                  >
                    {isAuthLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Github className="w-4 h-4" />
                    )}
                    <span>Continue with GitHub (OAuth)</span>
                  </Button>

                  <div className="relative w-full my-1">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t border-slate-200 dark:border-zinc-800" />
                    </div>
                    <div className="relative flex justify-center text-[10px] uppercase">
                      <span className="bg-slate-50 dark:bg-zinc-900 px-2 text-slate-500 dark:text-zinc-400">or</span>
                    </div>
                  </div>

                  {!showPatInput ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowPatInput(true)}
                      className="text-xs text-slate-600 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-200 gap-1.5 h-8"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>Enter Personal Access Token</span>
                    </Button>
                  ) : (
                    <form onSubmit={handlePatLogin} className="w-full space-y-2 pt-1 text-left">
                      {patError && (
                        <div className="p-2 rounded bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800/60 text-red-700 dark:text-red-300 text-[11px]">
                          {patError}
                        </div>
                      )}
                      <div className="flex gap-2">
                        <Input
                          type="password"
                          placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                          value={patInput}
                          onChange={(e) => setPatInput(e.target.value)}
                          className="bg-white dark:bg-zinc-950 border-slate-200 dark:border-zinc-800 text-xs h-8 text-slate-900 dark:text-zinc-100 placeholder:text-slate-400 dark:placeholder:text-zinc-500"
                          disabled={isConnectingPat}
                          required
                          autoFocus
                        />
                        <Button
                          type="submit"
                          size="sm"
                          disabled={isConnectingPat || !patInput.trim()}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-8 px-3 font-medium"
                        >
                          {isConnectingPat ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <span>Connect</span>
                          )}
                        </Button>
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-zinc-400">
                        Token requires <code className="text-indigo-600 dark:text-indigo-300">read:user</code> and{" "}
                        <code className="text-indigo-600 dark:text-indigo-300">repo</code> scopes.
                      </p>
                    </form>
                  )}
                </div>
              </div>
            ) : (
              // Connected view with repo selector
              <div className="space-y-3">
                {/* User bar */}
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-100/80 dark:bg-zinc-900/60 border border-slate-200 dark:border-zinc-800 text-xs">
                  <div className="flex items-center gap-2.5 min-w-0">
                    {githubUser?.avatar_url ? (
                      <img
                        src={githubUser.avatar_url}
                        alt={githubUser.login}
                        className="w-6 h-6 rounded-full border border-slate-300 dark:border-zinc-700 flex-shrink-0"
                      />
                    ) : (
                      <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-white text-[10px] font-bold">
                        {githubUser?.login?.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <span className="text-slate-600 dark:text-zinc-300 truncate">
                      Connected as <strong className="text-slate-900 dark:text-zinc-100">@{githubUser?.login}</strong>
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={fetchRepos}
                      disabled={isFetchingRepos}
                      className="h-7 px-2 text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-200 text-xs gap-1"
                      title="Refresh repositories"
                    >
                      <RefreshCw
                        className={`w-3 h-3 ${isFetchingRepos ? "animate-spin text-indigo-500" : ""}`}
                      />
                      <span className="hidden sm:inline">Refresh</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={logout}
                      className="h-7 px-2 text-slate-500 hover:text-red-600 hover:bg-red-50 dark:text-zinc-400 dark:hover:text-red-400 dark:hover:bg-red-500/10 text-xs gap-1 transition-colors"
                      title="Log out of GitHub account"
                    >
                      <LogOut className="w-3 h-3" />
                      <span>Log out</span>
                    </Button>
                  </div>
                </div>

                {/* Search Bar */}
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400 dark:text-zinc-400" />
                  <Input
                    placeholder="Search your repositories by name or description..."
                    value={repoSearch}
                    onChange={(e) => setRepoSearch(e.target.value)}
                    className="pl-9 bg-white dark:bg-zinc-900 border-slate-200 dark:border-zinc-800 text-xs h-9 text-slate-900 dark:text-zinc-100 placeholder:text-slate-400 dark:placeholder:text-zinc-500 focus:border-indigo-500"
                  />
                </div>

                {/* Repository List */}
                <div className="rounded-xl border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/30 max-h-[350px] overflow-y-auto divide-y divide-slate-100 dark:divide-zinc-850">
                  {isFetchingRepos ? (
                    <div className="p-8 text-center text-xs text-slate-500 dark:text-zinc-400 flex flex-col items-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
                      <span>Fetching repositories from GitHub...</span>
                    </div>
                  ) : filteredRepos.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500 dark:text-zinc-400">
                      {repoSearch ? "No repositories matching your search." : "No repositories found."}
                    </div>
                  ) : (
                    filteredRepos.map((r) => (
                      <div
                        key={r.id}
                        className="p-3.5 hover:bg-slate-50/80 dark:hover:bg-zinc-850/40 transition-colors flex items-center justify-between gap-3 text-xs"
                      >
                        <div className="min-w-0 flex-1 space-y-1.5 pr-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-slate-900 dark:text-zinc-100 text-xs sm:text-sm break-all">
                              {r.full_name}
                            </span>
                            {r.private ? (
                              <Badge
                                variant="outline"
                                className="text-[10px] px-1.5 py-0 h-4 border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-500/10 gap-1 font-normal"
                              >
                                <Lock className="w-2.5 h-2.5" />
                                <span>Private</span>
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="text-[10px] px-1.5 py-0 h-4 border-slate-200 dark:border-zinc-700 text-slate-500 dark:text-zinc-400 font-normal"
                              >
                                Public
                              </Badge>
                            )}
                            {r.language && (
                              <span className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-zinc-400">
                                <span
                                  className="w-2 h-2 rounded-full inline-block"
                                  style={{ backgroundColor: getLanguageColor(r.language) }}
                                />
                                {r.language}
                              </span>
                            )}
                            {r.stargazers_count > 0 && (
                              <span className="flex items-center gap-1 text-[11px] text-amber-600 dark:text-amber-400">
                                <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                                {r.stargazers_count}
                              </span>
                            )}
                          </div>

                          {r.description ? (
                            <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed line-clamp-2">
                              {r.description}
                            </p>
                          ) : null}

                          <div className="text-[11px] text-slate-500 dark:text-zinc-400 flex items-center gap-2 flex-wrap">
                            <span className="flex items-center gap-1.5">
                              branch:
                              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-100 text-slate-800 border border-slate-200 dark:bg-zinc-800 dark:text-zinc-200 dark:border-zinc-700">
                                {r.default_branch}
                              </span>
                            </span>
                            {r.updated_at && <span>• updated {formatDate(r.updated_at)}</span>}
                          </div>
                        </div>

                        {/* Action CTA */}
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {r.is_indexed ? (
                            <div className="flex items-center gap-2">
                              <Badge
                                variant="outline"
                                className="border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 text-[10px] gap-1"
                              >
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Indexed</span>
                              </Badge>
                              {r.indexed_repo_id && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    onOpenChange(false);
                                    router.push(`/repos/${r.indexed_repo_id}`);
                                  }}
                                  className="border-slate-300 dark:border-zinc-800 text-slate-700 dark:text-zinc-300 hover:text-slate-900 dark:hover:text-zinc-100 text-xs h-8 px-2.5"
                                >
                                  Open
                                </Button>
                              )}
                            </div>
                          ) : (
                            <Button
                              size="sm"
                              disabled={loading}
                              onClick={() => handleIndexGitHubRepo(r)}
                              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-8 px-3 gap-1.5 shadow-sm font-medium"
                            >
                              {loading && indexingRepoId === r.id ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <span>Index Repo</span>
                              )}
                            </Button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Manual URL Form */}
        {activeTab === "manual" && (
          <form onSubmit={handleManualSubmit} className="p-6 pt-4 space-y-4">
            {isConnected && githubUser && (
              <div className="flex items-center justify-between gap-2.5 p-2.5 rounded-lg bg-indigo-50/80 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800/40 text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                  <span className="text-slate-700 dark:text-zinc-300 truncate">
                    Connected as <strong className="text-slate-900 dark:text-zinc-100">@{githubUser.login}</strong> — authenticated cloning enabled.
                  </span>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={logout}
                  className="h-6 px-2 text-slate-500 hover:text-red-600 hover:bg-red-50 dark:text-zinc-400 dark:hover:text-red-400 dark:hover:bg-red-500/10 text-[11px] gap-1 flex-shrink-0 transition-colors"
                  title="Log out of GitHub account"
                >
                  <LogOut className="w-3 h-3" />
                  <span>Log out</span>
                </Button>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-700 dark:text-zinc-300">
                Repository GitHub URL
              </label>
              <Input
                placeholder="https://github.com/owner/repository"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={loading}
                className="bg-white dark:bg-zinc-900 border-slate-200 dark:border-zinc-800 text-slate-900 dark:text-zinc-100 placeholder:text-slate-400 dark:placeholder:text-zinc-500 focus:border-indigo-500 text-xs h-9"
                required
              />
              <p className="text-[11px] text-slate-500 dark:text-zinc-400">
                Supports any public repository, or private repositories your connected account can access.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-700 dark:text-zinc-300">
                Default Branch
              </label>
              <Input
                placeholder="main"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                disabled={loading}
                className="bg-white dark:bg-zinc-900 border-slate-200 dark:border-zinc-800 text-slate-900 dark:text-zinc-100 placeholder:text-slate-400 dark:placeholder:text-zinc-500 focus:border-indigo-500 text-xs h-9"
              />
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
                disabled={loading}
                className="border-slate-300 dark:border-zinc-800 hover:bg-slate-100 dark:hover:bg-zinc-900 text-slate-700 dark:text-zinc-300 text-xs h-8"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={loading || !url.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs gap-1.5 h-8 shadow-sm font-medium"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Indexing...</span>
                  </>
                ) : (
                  <span>Start Ingestion</span>
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

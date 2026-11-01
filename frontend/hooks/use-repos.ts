"use client";

import useSWR from "swr";
import {
  repos,
  type RepoResponse,
  type RepoListResponse,
  type RepoStatusResponse,
  type FileResponse,
  type RepoSummaryResponse,
} from "@/lib/api";


/**
 * SWR fetcher wrappers for repository data.
 * Each hook encapsulates caching, revalidation, and error handling.
 */

// ─── All Repositories ───────────────────────────────────────────────────────

/**
 * Fetch and cache the list of all repositories.
 * Auto-refreshes every 30 seconds to pick up new repos.
 */
export function useRepos() {
  const { data, error, isLoading, mutate } = useSWR<RepoListResponse>(
    "/repos",
    () => repos.list(),
    {
      refreshInterval: 30_000,
      revalidateOnFocus: true,
    }
  );

  return {
    repos: data?.repositories ?? [],
    total: data?.total ?? 0,
    isLoading,
    isError: !!error,
    error,
    mutate,
  };
}

// ─── Single Repository ─────────────────────────────────────────────────────

/**
 * Fetch a single repository by ID from the list.
 * Uses the repos list endpoint and filters client-side.
 */
export function useRepo(id: string | null) {
  const { data, error, isLoading, mutate } = useSWR<RepoListResponse>(
    id ? `/repos?for=${id}` : null,
    () => repos.list(),
    {
      refreshInterval: 10_000,
    }
  );

  const repo = data?.repositories?.find(
    (r: RepoResponse) => r.id === id
  ) ?? null;

  return {
    repo,
    isLoading,
    isError: !!error,
    error,
    mutate,
  };
}

// ─── Repository Status (Polling) ────────────────────────────────────────────

/**
 * Poll the ingestion status of a repository.
 * Polls every 2 seconds while the repo is not in a terminal state.
 */
export function useRepoStatus(id: string | null) {
  const { data, error, isLoading, mutate } = useSWR<RepoStatusResponse>(
    id ? `/repos/${id}/status` : null,
    () => (id ? repos.getStatus(id) : Promise.reject(new Error("No repo ID"))),
    {
      // Poll every 2s while status is not terminal
      refreshInterval: (latestData?: RepoStatusResponse) => {
        if (!latestData) return 2_000;
        const terminalStatuses = ["ready", "failed"];
        return terminalStatuses.includes(latestData.status) ? 0 : 2_000;
      },
      revalidateOnFocus: false,
    }
  );

  const isTerminal = data
    ? ["ready", "failed"].includes(data.status)
    : false;

  return {
    data,
    status: data?.status ?? null,
    progress: data?.progress ?? 0,
    stepDescription: data?.step_description ?? "",
    isReady: data?.status === "ready",
    isFailed: data?.status === "failed",
    isLoading,
    isError: !!error,
    isTerminal,
    error,
    mutate,
  };
}

// ─── Repository Files ───────────────────────────────────────────────────────

/**
 * Fetch the list of files in a repository.
 * Only fetches when a valid ID is provided.
 */
export function useRepoFiles(id: string | null) {
  const { data, error, isLoading } = useSWR<FileResponse[]>(
    id ? `/repos/${id}/files` : null,
    () => (id ? repos.getFiles(id) : Promise.resolve([])),
    {
      revalidateOnFocus: false,
    }
  );

  return {
    files: data ?? [],
    isLoading,
    isError: !!error,
    error,
  };
}

// ─── Repository Summary ─────────────────────────────────────────────────────

/**
 * Fetch high-level architecture summary for a repository.
 */
export function useRepoSummary(id: string | null) {
  const { data, error, isLoading, mutate } = useSWR<RepoSummaryResponse>(
    id ? `/repos/${id}/summary` : null,
    () => (id ? repos.getSummary(id) : Promise.reject(new Error("No repo ID"))),
    {
      revalidateOnFocus: false,
      dedupingInterval: 60_000,
    }
  );

  return {
    summary: data,
    isLoading,
    isError: !!error,
    error,
    mutate,
  };
}



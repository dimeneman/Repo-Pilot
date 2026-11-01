/**
 * RepoPilot API Client
 *
 * Centralized API layer for communicating with the RepoPilot backend.
 * All methods return typed responses and throw ApiError on failure.
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export interface RepoResponse {
  id: string;
  url: string;
  name: string;
  owner: string;
  default_branch?: string | null;
  status: "pending" | "cloning" | "parsing" | "indexing" | "ready" | "failed";
  file_count: number;
  chunk_count: number;
  language_stats: Record<string, number> | null;
  description: string | null;
  error_message: string | null;
  last_indexed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FileResponse {
  id: string;
  path: string;
  language: string | null;
  size: number;
  line_count: number;
}

export interface SourceCitation {
  file_path: string;
  start_line: number;
  end_line: number;
  snippet: string;
  relevance_score: number | null;
  language: string | null;
  chunk_id: string | null;
}

export interface ChatResponse {
  answer: string;
  sources: SourceCitation[];
  mode: string;
  query_id: string;
  model_used: string | null;
  processing_time_ms: number | null;
  mermaid_diagram: string | null;
}

export interface RepoSummaryResponse {
  answer: string;
  sources: SourceCitation[];
  mode: string;
  query_id?: string | null;
  model_used?: string | null;
  processing_time_ms?: number | null;
  mermaid_diagram?: string | null;
  tech_stack?: string[];
  folder_structure?: string;
  file_tree_preview?: string[];
}

export interface RepoStatusResponse {
  id: string;
  status: string;
  progress: number;
  file_count: number;
  chunk_count: number;
  step_description: string;
}


export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  vector_store: string;
}

export interface GitHubUser {
  id: number;
  login: string;
  name?: string | null;
  avatar_url?: string | null;
  html_url?: string | null;
  email?: string | null;
  public_repos?: number;
  bio?: string | null;
}

export interface GitHubAuthUrlResponse {
  configured: boolean;
  url: string | null;
  client_id?: string | null;
  message?: string | null;
}

export interface GitHubAuthResponse {
  access_token: string;
  user: GitHubUser;
}

export interface GitHubRepoItem {
  id: number;
  name: string;
  full_name: string;
  owner: string;
  html_url: string;
  clone_url: string;
  description: string | null;
  private: boolean;
  default_branch: string;
  language: string | null;
  stargazers_count: number;
  updated_at: string | null;
  is_indexed: boolean;
  indexed_repo_id: string | null;
}

export interface GitHubReposListResponse {
  repositories: GitHubRepoItem[];
  total: number;
}

export interface RepoListResponse {
  repositories: RepoResponse[];
  total: number;
}

export interface ChatHistoryResponse {
  queries: ChatResponse[];
  total: number;
}

// ─── Error Class ─────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body?: unknown
  ) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as any).detail)
        : null;
    super(detail || `API Error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

// ─── Base URL ────────────────────────────────────────────────────────────────

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ─── Core Fetch Wrapper ─────────────────────────────────────────────────────

/**
 * Generic fetch wrapper with JSON parsing and error handling.
 * All API methods delegate to this function.
 */
async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = await response.text().catch(() => null);
    }
    throw new ApiError(response.status, response.statusText, body);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ─── Repository Endpoints ───────────────────────────────────────────────────

export const repos = {
  /** Ingest (clone + index) a GitHub repository. */
  ingest: (
    url: string,
    branch?: string,
    accessToken?: string
  ): Promise<RepoResponse> =>
    fetchApi<RepoResponse>("/repos/ingest", {
      method: "POST",
      body: JSON.stringify({
        url,
        branch: branch || "main",
        access_token: accessToken || undefined,
      }),
    }),

  /** List all indexed repositories. */
  list: (): Promise<RepoListResponse> =>
    fetchApi<RepoListResponse>("/repos"),

  /** Get the current ingestion status for a repository. */
  getStatus: (id: string): Promise<RepoStatusResponse> =>
    fetchApi<RepoStatusResponse>(`/repos/${id}/status`),

  /** Get all files in a repository. */
  getFiles: (id: string): Promise<FileResponse[]> =>
    fetchApi<FileResponse[]>(`/repos/${id}/files`),

  /** Get a full summary of a repository. */
  getSummary: (id: string): Promise<RepoSummaryResponse> =>
    fetchApi<RepoSummaryResponse>(`/repos/${id}/summary`),


  /** Re-index an already-ingested repository. */
  reindex: (id: string): Promise<RepoResponse> =>
    fetchApi<RepoResponse>(`/repos/${id}/reindex`, { method: "POST" }),

  /** Delete a repository and all its data. */
  delete: (id: string): Promise<{ message: string }> =>
    fetchApi<{ message: string }>(`/repos/${id}`, { method: "DELETE" }),
};

// ─── Chat Endpoints ─────────────────────────────────────────────────────────

export const chat = {
  /** Send a question to the RAG pipeline. */
  send: (
    repoId: string,
    question: string,
    mode?: string,
    topK?: number
  ): Promise<ChatResponse> =>
    fetchApi<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        repo_id: repoId,
        question,
        mode,
        top_k: topK,
      }),
    }),

  /** Get the chat history for a repository. */
  getHistory: (repoId: string): Promise<ChatHistoryResponse> =>
    fetchApi<ChatHistoryResponse>(`/chat/history/${repoId}`),
};

// ─── Source Endpoints ───────────────────────────────────────────────────────

export const sources = {
  /** Get a specific source citation by chunk ID. */
  get: (chunkId: string): Promise<SourceCitation> =>
    fetchApi<SourceCitation>(`/sources/${chunkId}`),
};

// ─── Auth Endpoints ─────────────────────────────────────────────────────────

export const auth = {
  /** Get GitHub OAuth authorize URL */
  getGitHubUrl: (redirectUri?: string): Promise<GitHubAuthUrlResponse> => {
    const params = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : "";
    return fetchApi<GitHubAuthUrlResponse>(`/auth/github/url${params}`);
  },

  /** Exchange OAuth code for access token and profile */
  callbackGitHub: (code: string, redirectUri?: string): Promise<GitHubAuthResponse> =>
    fetchApi<GitHubAuthResponse>("/auth/github/callback", {
      method: "POST",
      body: JSON.stringify({ code, redirect_uri: redirectUri }),
    }),

  /** Connect using GitHub Personal Access Token (PAT) */
  tokenLogin: (token: string): Promise<GitHubAuthResponse> =>
    fetchApi<GitHubAuthResponse>("/auth/github/token-login", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  /** Get authenticated GitHub user profile */
  getGitHubUser: (token: string): Promise<GitHubUser> =>
    fetchApi<GitHubUser>("/auth/github/user", {
      headers: { Authorization: `Bearer ${token}` },
    }),

  /** Fetch user's repositories from GitHub with indexing status */
  getGitHubRepos: (token: string): Promise<GitHubReposListResponse> =>
    fetchApi<GitHubReposListResponse>("/auth/github/repos", {
      headers: { Authorization: `Bearer ${token}` },
    }),
};

// ─── Health Endpoint ────────────────────────────────────────────────────────

export const health = {
  /** Check backend health and connectivity. */
  check: (): Promise<HealthResponse> => fetchApi<HealthResponse>("/health"),
};

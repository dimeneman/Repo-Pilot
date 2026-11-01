import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

/**
 * Merge Tailwind CSS classes without conflicts.
 * Combines clsx's conditional logic with tailwind-merge's deduplication.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format an ISO date string into a human-readable relative time.
 * Falls back to a formatted date if parsing fails.
 */
export function formatDate(date: string): string {
  try {
    const parsed = new Date(date);
    return formatDistanceToNow(parsed, { addSuffix: true });
  } catch {
    return date;
  }
}

/**
 * Format an ISO date string into an absolute date/time.
 */
export function formatAbsoluteDate(date: string): string {
  try {
    return format(new Date(date), "MMM d, yyyy 'at' h:mm a");
  } catch {
    return date;
  }
}

/**
 * Truncate a string to a maximum length, appending ellipsis if truncated.
 */
export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 1) + "…";
}

/**
 * Map of programming language names to their conventional colors.
 * Used for language badges and breakdown bars.
 */
const LANGUAGE_COLORS: Record<string, string> = {
  typescript: "#3178c6",
  javascript: "#f1e05a",
  python: "#3572a5",
  rust: "#dea584",
  go: "#00add8",
  java: "#b07219",
  ruby: "#701516",
  cpp: "#f34b7d",
  c: "#555555",
  csharp: "#178600",
  swift: "#ffac45",
  kotlin: "#a97bff",
  php: "#4f5d95",
  html: "#e34c26",
  css: "#563d7c",
  scss: "#c6538c",
  shell: "#89e051",
  markdown: "#083fa1",
  json: "#292929",
  yaml: "#cb171e",
  sql: "#e38c00",
  dockerfile: "#384d54",
  vue: "#41b883",
  svelte: "#ff3e00",
};

/**
 * Get the display color for a programming language.
 * Returns a hex color string. Falls back to a neutral gray.
 */
export function getLanguageColor(language: string): string {
  const key = language.toLowerCase().replace(/[^a-z]/g, "");
  return LANGUAGE_COLORS[key] ?? "#6b7280";
}

/**
 * Status color mapping for repository ingestion states.
 * Returns Tailwind-compatible color classes.
 */
export function getStatusColor(status: string): {
  bg: string;
  text: string;
  dot: string;
} {
  switch (status) {
    case "ready":
      return {
        bg: "bg-emerald-500/10",
        text: "text-emerald-400",
        dot: "bg-emerald-400",
      };
    case "cloning":
    case "parsing":
    case "indexing":
      return {
        bg: "bg-amber-500/10",
        text: "text-amber-400",
        dot: "bg-amber-400",
      };
    case "failed":
      return {
        bg: "bg-red-500/10",
        text: "text-red-400",
        dot: "bg-red-400",
      };
    case "pending":
    default:
      return {
        bg: "bg-zinc-500/10",
        text: "text-zinc-400",
        dot: "bg-zinc-400",
      };
  }
}

/**
 * Parse a GitHub URL to extract the owner and repository name.
 * Supports both https and git@ URL formats.
 * Returns null if the URL is not a valid GitHub repository URL.
 */
export function parseGitHubUrl(
  url: string
): { owner: string; name: string } | null {
  // Match HTTPS format: https://github.com/owner/repo(.git)?
  const httpsMatch = url.match(
    /github\.com\/([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:\.git)?$/
  );
  if (httpsMatch) {
    return { owner: httpsMatch[1], name: httpsMatch[2] };
  }

  // Match SSH format: git@github.com:owner/repo.git
  const sshMatch = url.match(
    /git@github\.com:([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:\.git)?$/
  );
  if (sshMatch) {
    return { owner: sshMatch[1], name: sshMatch[2] };
  }

  return null;
}

/**
 * Format a byte count into a human-readable file size.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/**
 * Format a large number with K/M suffixes.
 */
export function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
  return count.toString();
}

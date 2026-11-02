/**
 * Session Management for RepoPilot
 *
 * Ensures RepoPilot operates as a session-only demo app:
 * - A fresh session is created when the site opens, refreshes, or reopens.
 * - Repositories, chats, and statuses are scoped to this session.
 * - Refreshing/reopening clears the UI state and starts a clean session.
 * - OAuth redirect preserves the session across the OAuth round-trip.
 */

let inMemorySessionId: string | null = null;

const STORAGE_SESSION_KEY = "repopilot_session_id";
const OAUTH_SESSION_KEY = "repopilot_oauth_session_id";

function generateSessionId(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 8);
  return `sess_${ts}_${rand}`;
}

export function getSessionId(): string {
  if (typeof window === "undefined") {
    return "ssr_session";
  }

  // 1. If we already established a session during this page lifecycle, use it
  if (inMemorySessionId) {
    return inMemorySessionId;
  }

  // 2. Check if we are completing a GitHub OAuth callback
  try {
    const oauthSavedSession = sessionStorage.getItem(OAUTH_SESSION_KEY);
    if (oauthSavedSession) {
      inMemorySessionId = oauthSavedSession;
      sessionStorage.removeItem(OAUTH_SESSION_KEY);
      try {
        localStorage.setItem(STORAGE_SESSION_KEY, inMemorySessionId);
      } catch {}
      return inMemorySessionId;
    }
  } catch {}

  // 3. Fresh site open / refresh / reopen: generate a fresh session ID
  const freshId = generateSessionId();
  inMemorySessionId = freshId;

  try {
    localStorage.setItem(STORAGE_SESSION_KEY, freshId);
  } catch {}

  return inMemorySessionId;
}

/**
 * Preserves the current session before redirecting to an external site (e.g. GitHub OAuth).
 */
export function preserveSessionForOAuth(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(OAUTH_SESSION_KEY, getSessionId());
  } catch {}
}

/**
 * Resets the active session and returns the new session ID.
 */
export function resetSession(): string {
  inMemorySessionId = null;
  return getSessionId();
}


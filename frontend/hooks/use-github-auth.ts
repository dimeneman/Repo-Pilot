"use client";

import { useState, useEffect, useCallback } from "react";
import { auth, type GitHubUser } from "@/lib/api";

const TOKEN_KEY = "repopilot_github_token";
const USER_KEY = "repopilot_github_user";
const AUTH_EVENT = "repopilot-auth-change";

export function useGitHubAuth() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<GitHubUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Sync state from localStorage
  const syncFromStorage = useCallback(() => {
    try {
      const savedToken = localStorage.getItem(TOKEN_KEY);
      const savedUserStr = localStorage.getItem(USER_KEY);
      if (savedToken) {
        setToken(savedToken);
        if (savedUserStr) {
          try {
            setUser(JSON.parse(savedUserStr));
          } catch {
            setUser(null);
          }
        }
      } else {
        setToken(null);
        setUser(null);
      }
    } catch {
      // localStorage may fail in restricted sandboxes
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize and listen to storage / cross-component events
  useEffect(() => {
    syncFromStorage();

    const handleStorageChange = () => syncFromStorage();
    window.addEventListener("storage", handleStorageChange);
    window.addEventListener(AUTH_EVENT, handleStorageChange);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener(AUTH_EVENT, handleStorageChange);
    };
  }, [syncFromStorage]);

  const loginWithOAuth = useCallback(
    async (redirectUri?: string): Promise<{ configured: boolean; url?: string | null; message?: string }> => {
      setError(null);
      setIsLoading(true);
      try {
        const callback =
          redirectUri ||
          (typeof window !== "undefined"
            ? `${window.location.origin}/auth/callback`
            : "http://localhost:3000/auth/callback");

        const res = await auth.getGitHubUrl(callback);
        if (res.configured && res.url) {
          window.location.href = res.url;
          return { configured: true, url: res.url };
        } else {
          const msg =
            res.message ||
            "GitHub OAuth is not configured in .env (GITHUB_CLIENT_ID is missing). You can connect using a Personal Access Token.";
          setError(msg);
          return { configured: false, message: msg };
        }
      } catch (err: any) {
        const msg = err?.message || "Failed to start GitHub OAuth flow.";
        setError(msg);
        return { configured: false, message: msg };
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const loginWithToken = useCallback(async (patToken: string) => {
    setError(null);
    setIsLoading(true);
    try {
      const clean = patToken.trim();
      if (!clean) throw new Error("Please enter a valid GitHub token.");

      const res = await auth.tokenLogin(clean);
      setToken(res.access_token);
      setUser(res.user);
      try {
        localStorage.setItem(TOKEN_KEY, res.access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(res.user));
        window.dispatchEvent(new CustomEvent(AUTH_EVENT));
      } catch {}
      return res.user;
    } catch (err: any) {
      const msg = err?.message || "Invalid GitHub token. Please verify token permissions.";
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const setAuthSession = useCallback((newToken: string, newUser: GitHubUser) => {
    setToken(newToken);
    setUser(newUser);
    try {
      localStorage.setItem(TOKEN_KEY, newToken);
      localStorage.setItem(USER_KEY, JSON.stringify(newUser));
      window.dispatchEvent(new CustomEvent(AUTH_EVENT));
    } catch {}
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setError(null);
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      window.dispatchEvent(new CustomEvent(AUTH_EVENT));
    } catch {}
  }, []);

  return {
    user,
    token,
    isConnected: !!token && !!user,
    isLoading,
    error,
    loginWithOAuth,
    loginWithToken,
    setAuthSession,
    logout,
  };
}

"use client";

import React, { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, AlertCircle, CheckCircle2, Github, Compass, RefreshCw } from "lucide-react";
import { auth } from "@/lib/api";
import { useGitHubAuth } from "@/hooks/use-github-auth";
import { Button } from "@/components/ui/button";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const errorParam = searchParams.get("error");
  const { setAuthSession } = useGitHubAuth();

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const exchangeStartedRef = useRef(false);

  useEffect(() => {
    if (errorParam) {
      setStatus("error");
      setErrorMessage(
        searchParams.get("error_description") ||
          `GitHub returned an authorization error: ${errorParam}`
      );
      return;
    }

    if (!code) {
      setStatus("error");
      setErrorMessage("No authorization code was provided by GitHub.");
      return;
    }

    if (exchangeStartedRef.current) return;
    exchangeStartedRef.current = true;

    async function handleExchange() {
      try {
        const redirectUri = window.location.origin + "/auth/callback";
        const res = await auth.callbackGitHub(code!, redirectUri);

        setAuthSession(res.access_token, res.user);
        setStatus("success");

        // Small delay to let user see success, then redirect to repos
        setTimeout(() => {
          router.push("/repos");
        }, 1200);
      } catch (err: any) {
        setStatus("error");
        setErrorMessage(
          err?.message || "Failed to exchange GitHub authorization code. Please try signing in again."
        );
      }
    }

    handleExchange();
  }, [code, errorParam, router, searchParams, setAuthSession]);

  return (
    <div className="min-h-full flex items-center justify-center p-6 bg-zinc-950 text-zinc-100">
      <div className="max-w-md w-full p-8 rounded-2xl bg-zinc-900/70 border border-zinc-800 text-center space-y-5 shadow-2xl">
        <div className="w-12 h-12 rounded-xl bg-indigo-950 border border-indigo-800/40 flex items-center justify-center text-indigo-400 mx-auto shadow-inner">
          <Github className="w-6 h-6" />
        </div>

        {status === "loading" && (
          <div className="space-y-3">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500 mx-auto" />
            <h3 className="text-base font-semibold text-zinc-100">
              Connecting GitHub Account...
            </h3>
            <p className="text-xs text-zinc-400">
              Validating OAuth credentials and fetching your repository permissions.
            </p>
          </div>
        )}

        {status === "success" && (
          <div className="space-y-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
            <h3 className="text-base font-semibold text-zinc-100">
              GitHub Account Linked!
            </h3>
            <p className="text-xs text-zinc-400">
              Redirecting you to your repositories workspace...
            </p>
          </div>
        )}

        {status === "error" && (
          <div className="space-y-4">
            <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/50 text-red-300 text-xs flex items-start gap-2.5 text-left leading-relaxed">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => router.push("/")}
                className="flex-1 border-zinc-800 text-zinc-300 hover:text-white text-xs h-9 gap-1.5"
              >
                <Compass className="w-3.5 h-3.5" />
                <span>Dashboard</span>
              </Button>
              <Button
                onClick={() => router.push("/repos")}
                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-9 gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Try Again</span>
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-full flex items-center justify-center p-6 bg-zinc-950 text-zinc-100">
          <div className="flex items-center gap-2 text-zinc-400 text-xs">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
            <span>Loading authentication...</span>
          </div>
        </div>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  );
}

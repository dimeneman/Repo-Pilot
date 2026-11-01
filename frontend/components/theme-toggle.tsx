"use client";

import React, { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ThemeToggle({
  className = "",
  showLabel = false,
}: {
  className?: string;
  showLabel?: boolean;
}) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    try {
      const saved = localStorage.getItem("repopilot_theme");
      if (saved === "light") {
        setTheme("light");
        document.documentElement.classList.remove("dark");
        document.documentElement.classList.add("light");
      } else {
        setTheme("dark");
        document.documentElement.classList.remove("light");
        document.documentElement.classList.add("dark");
      }
    } catch {
      // ignore
    }
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      localStorage.setItem("repopilot_theme", next);
      if (next === "light") {
        document.documentElement.classList.remove("dark");
        document.documentElement.classList.add("light");
      } else {
        document.documentElement.classList.remove("light");
        document.documentElement.classList.add("dark");
      }
    } catch {}
  };

  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className={`h-8 w-8 p-0 text-zinc-400 ${className}`}
        aria-label="Toggle theme"
      >
        <Moon className="w-4 h-4" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={toggleTheme}
      className={`h-8 px-2.5 gap-2 text-xs font-medium text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/80 transition-colors ${className}`}
      title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      aria-label="Toggle theme"
    >
      {theme === "dark" ? (
        <Sun className="w-4 h-4 text-amber-400 transition-transform hover:rotate-45" />
      ) : (
        <Moon className="w-4 h-4 text-indigo-500 transition-transform hover:-rotate-12" />
      )}
      {showLabel && (
        <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
      )}
    </Button>
  );
}


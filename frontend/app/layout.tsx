import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";

export const metadata: Metadata = {
  title: "RepoPilot — GitHub Repository RAG Assistant",
  description:
    "Ask natural-language questions about any GitHub repository and get grounded answers with source citations.",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/logo.png", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
    apple: "/logo.png",
  },
};

/**
 * Root layout — wraps every page with the global font, dark background,
 * and the persistent sidebar navigation.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var theme = localStorage.getItem('repopilot_theme');
                if (theme === 'light') {
                  document.documentElement.classList.remove('dark');
                  document.documentElement.classList.add('light');
                } else {
                  document.documentElement.classList.add('dark');
                  document.documentElement.classList.remove('light');
                }
              } catch (_) {}
            `,
          }}
        />
      </head>
      <body
        className="font-sans bg-zinc-950 text-zinc-100 min-h-screen"
      >
        <div className="flex h-screen overflow-hidden">
          {/* Persistent sidebar */}
          <Sidebar />

          {/* Main content area */}
          <main className="flex-1 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}

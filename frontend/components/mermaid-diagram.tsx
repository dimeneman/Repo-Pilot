"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import {
  Network,
  Copy,
  Check,
  Layers,
  Database,
  Cpu,
  Globe,
  FileCode,
  ArrowRight,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface MermaidDiagramProps {
  chart: string;
}

interface ParsedNode {
  id: string;
  label: string;
  type: "ui" | "api" | "logic" | "db" | "general";
}

interface ParsedEdge {
  from: string;
  to: string;
  label?: string;
}

/**
 * Clean and standardize raw Mermaid diagram code before passing to parser.
 */
function cleanMermaidCode(raw: string): string {
  if (!raw) return "";

  // Remove markdown code fences if present
  let cleaned = raw.trim();
  cleaned = cleaned.replace(/^```(?:mermaid)?\s*/i, "");
  cleaned = cleaned.replace(/\s*```$/i, "");
  cleaned = cleaned.trim();

  const lines = cleaned.split("\n").map((l) => l.trim()).filter(Boolean);
  if (lines.length === 0) return "";

  // Ensure header is flowchart LR
  const first = lines[0].toLowerCase();
  const validHeaders = ["flowchart", "graph", "sequencediagram", "classdiagram", "statediagram", "erdiagram"];
  const hasValidHeader = validHeaders.some((h) => first.startsWith(h));

  if (!hasValidHeader) {
    lines.unshift("flowchart LR");
  } else if (first.startsWith("graph td") || first.startsWith("flowchart td") || first.startsWith("graph lr")) {
    lines[0] = "flowchart LR";
  }

  // Sanitize nodes and edges
  const result: string[] = [lines[0]];
  for (let i = 1; i < lines.length; i++) {
    let line = lines[i];
    if (line.startsWith("%%")) continue; // skip comments

    // Ensure brackets with quotes: Node[Label (extra)] -> Node["Label (extra)"]
    line = line.replace(/([A-Za-z0-9_]+)\[([^"'\n]+)\]/g, '$1["$2"]');

    // Replace invalid node IDs with safe alphanumeric characters
    line = line.replace(/(^|\s|-->|---|==>)([A-Za-z0-9_\-\.\/]+)(\[|\(|\{)/g, (_, p1, id, p3) => {
      const cleanId = id.replace(/[^A-Za-z0-9_]/g, "_");
      return `${p1}${cleanId}${p3}`;
    });

    result.push(line);
  }

  return result.join("\n");
}

/**
 * Extract nodes and edges to build an HTML/CSS flowchart fallback if Mermaid fails.
 */
function extractDiagramElements(chartCode: string): { nodes: ParsedNode[]; edges: ParsedEdge[] } {
  const nodesMap = new Map<string, ParsedNode>();
  const edges: ParsedEdge[] = [];

  const lines = chartCode.split("\n");

  for (const line of lines) {
    // Match node definitions like: NodeId["Label"] or NodeId[("DB Label")]
    const nodeRegex = /([A-Za-z0-9_]+)(?:\[\(?["']?([^"'\]\)]+)["']?\)?\]|\(["']?([^"'\)]+)["']?\))/g;
    let match: RegExpExecArray | null;

    while ((match = nodeRegex.exec(line)) !== null) {
      const id = match[1];
      const rawLabel = match[2] || match[3] || id;
      const label = rawLabel.trim();

      if (!nodesMap.has(id)) {
        const lower = (id + " " + label).toLowerCase();
        let type: ParsedNode["type"] = "general";
        if (/ui|client|web|frontend|app|streamlit|user/i.test(lower)) {
          type = "ui";
        } else if (/api|server|router|gateway|controller|handler/i.test(lower)) {
          type = "api";
        } else if (/db|database|storage|postgres|qdrant|redis|model|store/i.test(lower)) {
          type = "db";
        } else if (/service|logic|engine|worker|pipeline|rag|orchestrat|retriev/i.test(lower)) {
          type = "logic";
        }

        nodesMap.set(id, { id, label, type });
      }
    }

    // Match edge definitions like: A --> B or A -->|"label"| B
    const edgeMatch = line.match(/([A-Za-z0-9_]+)\s*(?:-->|---|==>)\s*(?:\|["']?([^|"']+)["']?\|\s*)?([A-Za-z0-9_]+)/);
    if (edgeMatch) {
      const from = edgeMatch[1];
      const label = edgeMatch[2]?.trim();
      const to = edgeMatch[3];
      edges.push({ from, to, label });
    }
  }

  return { nodes: Array.from(nodesMap.values()), edges };
}

export function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showSource, setShowSource] = useState(false);

  // Normalized chart string
  const cleanChart = useMemo(() => cleanMermaidCode(chart), [chart]);

  // Fallback parsed elements
  const fallbackElements = useMemo(() => extractDiagramElements(cleanChart), [cleanChart]);

  useEffect(() => {
    let isMounted = true;

    async function renderChart() {
      if (!cleanChart) return;

      try {
        const mermaid = (await import("mermaid")).default;
        const isLight = document.documentElement.classList.contains("light");

        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "loose",
          theme: isLight ? "neutral" : "dark",
          themeVariables: isLight
            ? {
                darkMode: false,
                background: "transparent",
                primaryColor: "#eef2ff",
                primaryTextColor: "#0f172a",
                primaryBorderColor: "#6366f1",
                lineColor: "#64748b",
                secondaryColor: "#ffffff",
                tertiaryColor: "#f1f5f9",
              }
            : {
                darkMode: true,
                background: "transparent",
                primaryColor: "#1e1b4b",
                primaryTextColor: "#f4f4f5",
                primaryBorderColor: "#6366f1",
                lineColor: "#94a3b8",
                secondaryColor: "#18181b",
                tertiaryColor: "#27272a",
              },
          fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif",
        });

        // Pre-validate syntax before inserting into DOM if parse is supported
        if (typeof (mermaid as any).parse === "function") {
          try {
            await (mermaid as any).parse(cleanChart);
          } catch (parseErr: any) {
            throw new Error(parseErr?.message || "Invalid Mermaid syntax");
          }
        }

        const id = `mermaid_${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(id, cleanChart);

        if (isMounted) {
          setSvgContent(svg);
          setRenderError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setRenderError(err?.message || "Could not render diagram via Mermaid engine");
        }
      }
    }

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [cleanChart]);

  const handleCopy = () => {
    navigator.clipboard.writeText(cleanChart || chart);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getNodeIcon = (type: ParsedNode["type"]) => {
    switch (type) {
      case "ui":
        return <Globe className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" />;
      case "api":
        return <FileCode className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />;
      case "db":
        return <Database className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" />;
      case "logic":
        return <Cpu className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />;
      default:
        return <Layers className="w-3.5 h-3.5 text-zinc-400" />;
    }
  };

  return (
    <div className="my-4 border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-950/80 rounded-2xl overflow-hidden shadow-sm transition-all">
      {/* Diagram Header */}
      <div className="px-4 py-2.5 bg-slate-50/80 dark:bg-zinc-900/60 border-b border-slate-200 dark:border-zinc-800 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-slate-700 dark:text-zinc-200 font-medium">
          <Network className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
          <span>System Architecture Flowchart</span>
          {renderError && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-medium">
              Visual Component View
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSource(!showSource)}
            className="text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-zinc-200 px-2 py-1 rounded hover:bg-slate-200/50 dark:hover:bg-zinc-800/60 flex items-center gap-1 text-[11px] transition-colors"
            title="View or hide Mermaid code"
          >
            <span>{showSource ? "Hide Source" : "View Source"}</span>
            {showSource ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          <button
            onClick={handleCopy}
            className="text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-zinc-200 px-2 py-1 rounded hover:bg-slate-200/50 dark:hover:bg-zinc-800/60 flex items-center gap-1 text-[11px] transition-colors"
            title="Copy Mermaid source to clipboard"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-emerald-500" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
            <span>{copied ? "Copied" : "Copy Mermaid"}</span>
          </button>
        </div>
      </div>

      {/* Main Diagram Canvas */}
      <div
        ref={containerRef}
        className="p-6 overflow-x-auto flex flex-col items-center justify-center min-h-[170px] bg-slate-50/40 dark:bg-zinc-950"
      >
        {svgContent && !renderError ? (
          <div
            dangerouslySetInnerHTML={{ __html: svgContent }}
            className="w-full flex justify-center [&>svg]:max-w-full [&>svg]:h-auto [&>svg]:min-h-[140px] [&>svg]:max-h-[380px]"
          />
        ) : renderError && fallbackElements.nodes.length > 0 ? (
          /* Graceful Visual Component Fallback */
          <div className="w-full py-4 space-y-4">
            <div className="flex items-center justify-center gap-2 flex-wrap">
              {fallbackElements.nodes.map((node, idx) => (
                <React.Fragment key={node.id}>
                  <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 shadow-sm hover:border-indigo-400 transition-all">
                    {getNodeIcon(node.type)}
                    <span className="text-xs font-semibold text-slate-800 dark:text-zinc-200">
                      {node.label}
                    </span>
                  </div>
                  {idx < fallbackElements.nodes.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-slate-400 dark:text-zinc-500 flex-shrink-0" />
                  )}
                </React.Fragment>
              ))}
            </div>

            {/* Component breakdown summary */}
            <div className="pt-2 text-center text-xs text-slate-500 dark:text-zinc-400">
              Architecture flow extracted from repository modules:{" "}
              {fallbackElements.nodes.map((n) => n.label).join(" → ")}
            </div>
          </div>
        ) : renderError ? (
          /* Text Summary Fallback if neither SVG nor node extraction succeeded */
          <div className="p-4 text-center space-y-2">
            <p className="text-xs text-slate-600 dark:text-zinc-400">
              The architecture diagram could not be rendered visually, but the structured repository analysis is available below.
            </p>
          </div>
        ) : (
          <div className="flex items-center justify-center text-xs text-slate-500 dark:text-zinc-400 animate-pulse">
            Rendering architecture flowchart...
          </div>
        )}
      </div>

      {/* Expandable Mermaid Source View */}
      {showSource && (
        <div className="p-3 bg-slate-100 dark:bg-zinc-900/90 border-t border-slate-200 dark:border-zinc-800 font-mono text-[11px] text-slate-700 dark:text-zinc-300 overflow-x-auto">
          <div className="text-[10px] uppercase font-semibold text-slate-500 dark:text-zinc-500 mb-1 font-sans">
            Mermaid Definition:
          </div>
          <pre className="whitespace-pre leading-relaxed">{cleanChart || chart}</pre>
        </div>
      )}
    </div>
  );
}

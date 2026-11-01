// Ambient type declarations for external dependencies and Node environment

// ─── Node.js & Next.js Environment ──────────────────────────────────────────
declare namespace NodeJS {
  interface ProcessEnv {
    [key: string]: string | undefined;
    NODE_ENV?: "development" | "production" | "test";
    NEXT_PUBLIC_API_URL?: string;
  }
}

declare var process: {
  env: NodeJS.ProcessEnv;
  [key: string]: any;
};

// ─── SWR ────────────────────────────────────────────────────────────────────
declare module "swr" {
  export interface SWRConfiguration<Data = any, Error = any> {
    refreshInterval?: number | ((latestData?: Data) => number);
    revalidateOnFocus?: boolean;
    dedupingInterval?: number;
    [key: string]: any;
  }

  export interface SWRResponse<Data = any, Error = any> {
    data?: Data;
    error?: Error;
    isLoading: boolean;
    isValidating: boolean;
    mutate: (data?: any, shouldRevalidate?: boolean) => Promise<any>;
  }

  export default function useSWR<Data = any, Error = any>(
    key: string | null | (() => string | null),
    fetcher?: ((...args: any[]) => Promise<Data> | Data) | null,
    config?: SWRConfiguration<Data, Error>
  ): SWRResponse<Data, Error>;
}

// ─── Markdown & Visualization ───────────────────────────────────────────────
declare module "react-markdown" {
  import React from "react";
  const ReactMarkdown: React.FC<any>;
  export default ReactMarkdown;
}

declare module "remark-gfm" {
  const remarkGfm: any;
  export default remarkGfm;
}

declare module "mermaid" {
  const mermaid: {
    initialize: (config: any) => void;
    render: (id: string, text: string) => Promise<{ svg: string }>;
    parse?: (text: string) => Promise<any>;
    [key: string]: any;
  };
  export default mermaid;
}

// ─── Styling & Utilities ───────────────────────────────────────────────────
declare module "clsx" {
  export type ClassValue =
    | string
    | number
    | boolean
    | undefined
    | null
    | { [key: string]: any }
    | ClassValue[];
  export function clsx(...inputs: ClassValue[]): string;
  export default clsx;
}

declare module "tailwind-merge" {
  export function twMerge(...classLists: any[]): string;
}

declare module "date-fns" {
  export function formatDistanceToNow(
    date: Date | number,
    options?: { addSuffix?: boolean; [key: string]: any }
  ): string;
  export function format(
    date: Date | number,
    formatStr: string,
    options?: any
  ): string;
}

declare module "class-variance-authority" {
  export function cva(base?: any, config?: any): (...args: any[]) => string;
  export type VariantProps<T extends (...args: any[]) => any> = any;
}

// ─── Lucide Icons ──────────────────────────────────────────────────────────
declare module "lucide-react" {
  import React from "react";
  export type Icon = React.FC<any>;
  export const Compass: Icon;
  export const GitBranch: Icon;
  export const Github: Icon;
  export const Plus: Icon;
  export const Layers: Icon;
  export const Database: Icon;
  export const ExternalLink: Icon;
  export const ChevronRight: Icon;
  export const Sparkles: Icon;
  export const Loader2: Icon;
  export const AlertCircle: Icon;
  export const AlertTriangle: Icon;
  export const CheckCircle2: Icon;
  export const RefreshCw: Icon;
  export const Trash2: Icon;
  export const FileCode: Icon;
  export const FileText: Icon;
  export const BarChart2: Icon;
  export const ArrowUpRight: Icon;
  export const ArrowRight: Icon;
  export const Clock: Icon;
  export const MessageSquare: Icon;
  export const Plug: Icon;
  export const Bug: Icon;
  export const Network: Icon;
  export const Copy: Icon;
  export const Check: Icon;
  export const ChevronDown: Icon;
  export const ChevronUp: Icon;
  export const BookOpen: Icon;
  export const X: Icon;
  export const Bot: Icon;
  export const User: Icon;
  export const Folder: Icon;
  export const FolderOpen: Icon;
  export const Search: Icon;
  export const Cpu: Icon;
  export const FolderTree: Icon;
  export const Send: Icon;
  export const ShieldCheck: Icon;
  export const Link: Icon;
  export const Lock: Icon;
  export const Globe: Icon;
  export const Star: Icon;
  export const KeyRound: Icon;
  export const LogOut: Icon;
  export const Sun: Icon;
  export const Moon: Icon;
  export const UserCheck: Icon;
}

// ─── Radix UI Components ───────────────────────────────────────────────────
declare module "@radix-ui/react-dialog" {
  export const Root: any;
  export const Trigger: any;
  export const Portal: any;
  export const Overlay: any;
  export const Content: any;
  export const Header: any;
  export const Footer: any;
  export const Title: any;
  export const Description: any;
  export const Close: any;
}

declare module "@radix-ui/react-dropdown-menu" {
  const content: any;
  export default content;
}

declare module "@radix-ui/react-tabs" {
  export const Root: any;
  export const List: any;
  export const Trigger: any;
  export const Content: any;
}

declare module "@radix-ui/react-tooltip" {
  export const Provider: any;
  export const Root: any;
  export const Trigger: any;
  export const Content: any;
}

declare module "@radix-ui/react-scroll-area" {
  export const Root: any;
  export const Viewport: any;
  export const Scrollbar: any;
  export const ScrollAreaScrollbar: any;
  export const Thumb: any;
  export const ScrollAreaThumb: any;
  export const Corner: any;
  export const ScrollAreaCorner: any;
}

declare module "@radix-ui/react-progress" {
  export const Root: any;
  export const Indicator: any;
}

declare module "@radix-ui/react-select" {
  export const Root: any;
  export const Group: any;
  export const Value: any;
  export const Trigger: any;
  export const Content: any;
  export const Label: any;
  export const Item: any;
  export const ItemText: any;
  export const ItemIndicator: any;
  export const Separator: any;
  export const ScrollUpButton: any;
  export const ScrollDownButton: any;
  export const Viewport: any;
  export const Portal: any;
  export const Icon: any;
}

declare module "@radix-ui/react-slot" {
  export const Slot: any;
  export const Slottable: any;
}

// ─── Stylesheet & Static Assets ─────────────────────────────────────────────
declare module "*.css" {
  const content: { [className: string]: string };
  export default content;
}

declare module "*.svg" {
  const content: any;
  export default content;
}

declare module "*.png" {
  const content: any;
  export default content;
}

declare module "*.jpg" {
  const content: any;
  export default content;
}

declare module "*.ico" {
  const content: any;
  export default content;
}

import { cn } from "@/lib/utils";

/**
 * Skeleton loading placeholder with pulse animation.
 * Renders a rounded rectangle that pulses to indicate loading state.
 */
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-zinc-800", className)}
      {...props}
    />
  );
}

export { Skeleton };

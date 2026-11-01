import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Badge variants for status indicators, language tags, and labels.
 */
const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-indigo-600/20 text-indigo-300",
        secondary:
          "border-transparent bg-zinc-800 text-zinc-300",
        destructive:
          "border-transparent bg-red-900/30 text-red-300",
        outline: "border-zinc-700 text-zinc-300",
        success:
          "border-transparent bg-emerald-900/30 text-emerald-300",
        warning:
          "border-transparent bg-amber-900/30 text-amber-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

/**
 * Small label/tag component for displaying status, categories, etc.
 */
const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(badgeVariants({ variant }), className)}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";

export { Badge, badgeVariants };

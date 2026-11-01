import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Button variants using class-variance-authority (CVA).
 * Provides consistent, composable button styles across the app.
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-indigo-600 text-white shadow hover:bg-indigo-700 active:bg-indigo-800",
        destructive:
          "bg-red-900/50 text-red-300 shadow-sm hover:bg-red-900/80 active:bg-red-800",
        outline:
          "border border-zinc-700 bg-transparent text-zinc-300 shadow-sm hover:bg-zinc-800 hover:text-zinc-100",
        secondary:
          "bg-zinc-800 text-zinc-100 shadow-sm hover:bg-zinc-700 active:bg-zinc-600",
        ghost:
          "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100",
        link: "text-indigo-400 underline-offset-4 hover:underline hover:text-indigo-300",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render as a Slot (merge props onto child element). */
  asChild?: boolean;
}

/**
 * Polished button component with multiple variants and sizes.
 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };

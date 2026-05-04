import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "../utils/cn";

const inputVariants = cva(
  [
    "flex w-full min-w-0 rounded-[var(--radius-md)] border transition-all duration-200 ease-[var(--ease-emphasized)]",
    "text-foreground placeholder:text-muted-foreground",
    "disabled:pointer-events-none disabled:opacity-[var(--opacity-disabled-base)] disabled:cursor-not-allowed",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "selection:bg-primary/20 selection:text-primary-foreground",
    "aria-invalid:border-destructive aria-invalid:focus-visible:ring-destructive",
    // File input specific styles
    "file:inline-flex file:h-7 file:border-0 file:bg-transparent file:px-2 file:text-xs file:font-medium file:text-foreground",
  ].join(" "),
  {
    variants: {
      variant: {
        default:
          "border-border/60 bg-surface shadow-[var(--shadow-base-xs)] hover:border-border/80",
        filled: "border-transparent bg-surface-elevated hover:bg-surface-overlay",
        outline: "border-border bg-transparent hover:border-border-strong",
      },
      inputSize: {
        sm: "h-8 px-2.5 py-1.5 text-xs",
        default: "h-10 px-3 py-2 text-sm",
        lg: "h-12 px-4 py-3 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      inputSize: "default",
    },
  },
);

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size">,
    VariantProps<typeof inputVariants> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant, inputSize, type = "text", ...props }, ref) => {
    return (
      <input
        type={type}
        data-slot="input"
        className={cn(inputVariants({ variant, inputSize }), className)}
        ref={ref}
        {...props}
      />
    );
  },
);

Input.displayName = "Input";

export { inputVariants };

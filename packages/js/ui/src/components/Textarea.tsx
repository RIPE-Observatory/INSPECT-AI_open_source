import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "../utils/cn";

const textareaVariants = cva(
  [
    "flex w-full rounded-[var(--radius-md)] border transition-all duration-200 ease-[var(--ease-emphasized)]",
    "text-foreground placeholder:text-muted-foreground",
    "disabled:cursor-not-allowed disabled:opacity-[var(--opacity-disabled-base)]",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "selection:bg-primary/20 selection:text-primary-foreground",
    "aria-invalid:border-destructive aria-invalid:focus-visible:ring-destructive",
    "resize-y",
  ].join(" "),
  {
    variants: {
      variant: {
        default:
          "border-border/60 bg-surface shadow-[var(--shadow-base-xs)]",
        filled: "border-transparent bg-surface-elevated",
        outline: "border-border bg-transparent",
      },
      textareaSize: {
        sm: "min-h-20 px-2.5 py-1.5 text-xs",
        default: "min-h-24 px-3 py-2 text-sm",
        lg: "min-h-32 px-4 py-3 text-base",
      },
      resize: {
        none: "resize-none",
        vertical: "resize-y",
        horizontal: "resize-x",
        both: "resize",
      },
    },
    defaultVariants: {
      variant: "default",
      textareaSize: "default",
      resize: "vertical",
    },
  },
);

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    VariantProps<typeof textareaVariants> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant, textareaSize, resize, ...props }, ref) => {
    return (
      <textarea
        data-slot="textarea"
        className={cn(textareaVariants({ variant, textareaSize, resize }), className)}
        ref={ref}
        {...props}
      />
    );
  },
);

Textarea.displayName = "Textarea";

export { textareaVariants };

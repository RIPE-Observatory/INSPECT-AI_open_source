import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";
import type * as React from "react";

import { cn } from "../utils/cn";
import { typographyVariants } from "./Typography";

const badgeBase = "inline-flex items-center justify-center gap-1 w-fit whitespace-nowrap shrink-0";
const badgeTokens =
  "rounded-[var(--radius-sm)] border border-border/60 bg-surface-elevated text-foreground";
const badgeContent =
  "[&>svg]:size-3 [&>svg]:pointer-events-none transition-colors duration-200 ease-[var(--ease-emphasized)]";

const badgeVariants = cva(
  cn(badgeBase, badgeTokens, badgeContent, typographyVariants({ variant: "label" })),
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary/20 text-primary-foreground/90 backdrop-blur-[var(--blur-popover)]",
        primary:
          "border-transparent bg-primary text-primary-foreground shadow-[var(--shadow-base-xs)]",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground shadow-[var(--shadow-base-xs)]",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow-[var(--shadow-base-xs)]",
        outline:
          "bg-transparent text-foreground [a&]:hover:bg-surface-elevated/60 [a&]:hover:text-foreground",
        success:
          "border-transparent bg-success/20 text-success-foreground/90 shadow-[var(--shadow-base-xs)]",
        warning:
          "border-transparent bg-warning/20 text-warning-foreground/90 shadow-[var(--shadow-base-xs)]",
        info: "border-transparent bg-info/20 text-info-foreground/90 shadow-[var(--shadow-base-xs)]",
      },
      density: {
        default: "px-2 py-0.5",
        compact: "px-[var(--space-2)] py-[calc(var(--space-1)+1px)]",
        relaxed: "px-3 py-1",
      },
    },
    defaultVariants: {
      variant: "default",
      density: "default",
    },
  },
);

export interface BadgeProps
  extends React.ComponentPropsWithoutRef<"span">,
    VariantProps<typeof badgeVariants> {
  asChild?: boolean;
}

function Badge({ className, variant, density, asChild = false, ...props }: BadgeProps) {
  const Comp = asChild ? Slot : "span";

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant, density }), className)}
      {...props}
    />
  );
}

// Export types for external usage
export type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;
export type BadgeDensity = NonNullable<VariantProps<typeof badgeVariants>["density"]>;

export { Badge, badgeVariants };

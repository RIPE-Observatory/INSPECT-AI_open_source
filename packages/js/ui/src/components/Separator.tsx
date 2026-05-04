"use client";

import * as SeparatorPrimitive from "@radix-ui/react-separator";
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "../utils/cn";

const separatorVariants = cva(
  "shrink-0 transition-colors duration-200 ease-[var(--ease-emphasized)]",
  {
    variants: {
      variant: {
        default: "bg-border",
        subtle: "bg-border/40",
        strong: "bg-border-strong",
      },
      orientation: {
        horizontal: "h-px w-full",
        vertical: "h-full w-px",
      },
    },
    defaultVariants: {
      variant: "default",
      orientation: "horizontal",
    },
  },
);

export interface SeparatorProps
  extends Omit<React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>, "orientation">,
    VariantProps<typeof separatorVariants> {}

export const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  SeparatorProps
>(({ className, variant, orientation = "horizontal", decorative = true, ...props }, ref) => (
  <SeparatorPrimitive.Root
    ref={ref}
    data-slot="separator"
    decorative={decorative}
    orientation={orientation as "horizontal" | "vertical" | undefined}
    className={cn(separatorVariants({ variant, orientation }), className)}
    {...props}
  />
));

Separator.displayName = SeparatorPrimitive.Root.displayName;

export { separatorVariants };

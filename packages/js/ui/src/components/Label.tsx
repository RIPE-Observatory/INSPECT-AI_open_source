"use client";

import * as LabelPrimitive from "@radix-ui/react-label";
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "../utils/cn";
import { typographyVariants } from "./Typography";

const labelVariants = cva(
  [
    "flex items-center gap-[var(--space-2)] select-none leading-none",
    "text-foreground font-medium tracking-normal",
    "peer-disabled:cursor-not-allowed peer-disabled:opacity-[var(--opacity-disabled-base)]",
    "group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-[var(--opacity-disabled-base)]",
    "transition-colors duration-150 ease-[var(--ease-emphasized)]",
  ].join(" "),
  {
    variants: {
      size: {
        sm: typographyVariants({ variant: "small" }),
        default: "text-sm",
        lg: "text-base",
      },
      required: {
        true: "label-required",
        false: "",
      },
    },
    defaultVariants: {
      size: "default",
      required: false,
    },
  },
);

export interface LabelProps
  extends React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>,
    VariantProps<typeof labelVariants> {}

export const Label = React.forwardRef<React.ElementRef<typeof LabelPrimitive.Root>, LabelProps>(
  ({ className, size, required, ...props }, ref) => {
    return (
      <LabelPrimitive.Root
        ref={ref}
        data-slot="label"
        className={cn(labelVariants({ size, required }), className)}
        {...props}
      />
    );
  },
);

Label.displayName = LabelPrimitive.Root.displayName;

export { labelVariants };

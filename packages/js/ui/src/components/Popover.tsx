"use client";

import * as PopoverPrimitive from "@radix-ui/react-popover";
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "../utils/cn";

const Popover = PopoverPrimitive.Root;
const PopoverTrigger = PopoverPrimitive.Trigger;
const PopoverAnchor = PopoverPrimitive.Anchor;

const popoverContentVariants = cva(
  [
    "z-[var(--z-popover)] rounded-[var(--radius-lg)] border outline-none",
    "shadow-[var(--shadow-base-md)] backdrop-blur-[var(--blur-popover)]",
    "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:duration-100",
    "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:duration-75",
  ].join(" "),
  {
    variants: {
      variant: {
        default: "border-border/60 bg-popover/95 text-popover-foreground",
        elevated: "border-border/70 bg-surface-elevated shadow-[var(--shadow-base-lg)]",
        ghost: "border-border/40 bg-surface/90",
      },
      size: {
        sm: "w-56 p-3",
        default: "w-72 p-4",
        lg: "w-96 p-5",
        auto: "p-4",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface PopoverContentProps
  extends React.ComponentPropsWithoutRef<typeof PopoverPrimitive.Content>,
    VariantProps<typeof popoverContentVariants> {}

const PopoverContent = React.forwardRef<
  React.ElementRef<typeof PopoverPrimitive.Content>,
  PopoverContentProps
>(({ className, variant, size, align = "center", sideOffset = 4, ...props }, ref) => (
  <PopoverPrimitive.Portal>
    <PopoverPrimitive.Content
      ref={ref}
      data-slot="popover-content"
      align={align}
      sideOffset={sideOffset}
      className={cn(popoverContentVariants({ variant, size }), className)}
      {...props}
    />
  </PopoverPrimitive.Portal>
));
PopoverContent.displayName = PopoverPrimitive.Content.displayName;

export { Popover, PopoverAnchor, PopoverContent, PopoverTrigger, popoverContentVariants };

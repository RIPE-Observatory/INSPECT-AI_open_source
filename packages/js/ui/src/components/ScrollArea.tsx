"use client";

import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area";
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "../utils/cn";

const scrollBarVariants = cva(
  "flex touch-none select-none transition-colors duration-200 ease-[var(--ease-emphasized)]",
  {
    variants: {
      orientation: {
        vertical: "h-full w-2.5 border-l border-l-transparent p-px",
        horizontal: "h-2.5 flex-col border-t border-t-transparent p-px",
      },
      variant: {
        default: "[&>div]:bg-border/70 hover:[&>div]:bg-border",
        subtle: "[&>div]:bg-border/40 hover:[&>div]:bg-border/60",
      },
    },
    defaultVariants: {
      orientation: "vertical",
      variant: "default",
    },
  },
);

export interface ScrollAreaProps
  extends React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root> {}

export const ScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  ScrollAreaProps
>(({ className, children, ...props }, ref) => (
  <ScrollAreaPrimitive.Root
    ref={ref}
    data-slot="scroll-area"
    className={cn("relative overflow-hidden", className)}
    {...props}
  >
    <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">
      {children}
    </ScrollAreaPrimitive.Viewport>
    <ScrollBar />
    <ScrollAreaPrimitive.Corner />
  </ScrollAreaPrimitive.Root>
));
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName;

export interface ScrollBarProps
  extends Omit<
      React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>,
      "orientation"
    >,
    VariantProps<typeof scrollBarVariants> {}

export const ScrollBar = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>,
  ScrollBarProps
>(({ className, orientation = "vertical", variant, ...props }, ref) => (
  <ScrollAreaPrimitive.ScrollAreaScrollbar
    ref={ref}
    data-slot="scroll-bar"
    orientation={orientation as "horizontal" | "vertical" | undefined}
    className={cn(scrollBarVariants({ orientation, variant }), className)}
    {...props}
  >
    <ScrollAreaPrimitive.ScrollAreaThumb className="relative flex-1 rounded-full" />
  </ScrollAreaPrimitive.ScrollAreaScrollbar>
));
ScrollBar.displayName = ScrollAreaPrimitive.ScrollAreaScrollbar.displayName;

export { scrollBarVariants };

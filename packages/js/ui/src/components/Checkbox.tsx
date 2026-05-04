"use client";

import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { type VariantProps, cva } from "class-variance-authority";
import { Check } from "lucide-react";
import * as React from "react";

import { cn } from "../utils/cn";

const checkboxVariants = cva(
  [
    "peer flex shrink-0 items-center justify-center rounded-[var(--radius-sm)] border",
    "transition-all duration-200 ease-[var(--ease-emphasized)]",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:cursor-not-allowed disabled:opacity-[var(--opacity-disabled-base)]",
    "data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground",
  ].join(" "),
  {
    variants: {
      variant: {
        default: "border-border/70 bg-surface hover:border-border",
        filled: "border-transparent bg-surface-elevated hover:bg-surface-overlay",
      },
      size: {
        sm: "size-4",
        default: "size-[1.1rem]",
        lg: "size-5",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface CheckboxProps
  extends React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>,
    VariantProps<typeof checkboxVariants> {}

export const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  CheckboxProps
>(({ className, variant, size, ...props }, ref) => (
  <CheckboxPrimitive.Root
    ref={ref}
    data-slot="checkbox"
    className={cn(checkboxVariants({ variant, size }), className)}
    {...props}
  >
    <CheckboxPrimitive.Indicator
      className={cn(
        "flex items-center justify-center text-current",
        "transition-transform duration-200 ease-[var(--ease-emphasized)]",
        "data-[state=checked]:scale-100 data-[state=unchecked]:scale-0",
      )}
    >
      <Check className="size-3.5" strokeWidth={2.5} />
    </CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
));

Checkbox.displayName = CheckboxPrimitive.Root.displayName;

export { checkboxVariants };

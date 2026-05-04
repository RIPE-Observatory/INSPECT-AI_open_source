import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "../utils/cn";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "rounded-[var(--radius-md)] border border-transparent",
    "text-sm font-medium tracking-normal transition-all duration-200 ease-[var(--ease-expressive, cubic-bezier(0.16,1,0.3,1))]",
    "outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:pointer-events-none disabled:opacity-60",
    "[&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0",
    "[@media(prefers-reduced-motion:reduce)]:transition-[background-color,border-color,color,opacity]",
    "[@media(prefers-reduced-motion:reduce)]:hover:scale-100",
    "[@media(prefers-reduced-motion:reduce)]:active:scale-100",
  ].join(" "),
  {
    variants: {
      variant: {
        default: [
          "bg-primary text-primary-foreground",
          "shadow-[var(--shadow-base-sm)]",
          "hover:scale-102 hover:shadow-primary-glow",
          "active:scale-98 active:opacity-90",
        ].join(" "),
        surface: [
          "bg-card text-card-foreground",
          "shadow-[var(--shadow-base-md)]",
          "hover:scale-102 hover:shadow-lg-custom",
          "active:scale-98 active:opacity-90",
        ].join(" "),
        outline: [
          "border-border bg-transparent text-foreground",
          "hover:scale-102 hover:bg-accent/10 hover:border-primary-soft hover:shadow-primary-ring",
          "active:scale-98 active:bg-accent/15",
        ].join(" "),
        secondary: [
          "bg-secondary text-secondary-foreground",
          "shadow-[var(--shadow-base-sm)]",
          "hover:scale-102 hover:shadow-md-custom",
          "active:scale-98 active:opacity-90",
        ].join(" "),
        ghost: [
          "bg-transparent text-muted-foreground",
          "hover:scale-102 hover:bg-accent/10 hover:text-foreground",
          "active:scale-98 active:bg-accent/15",
        ].join(" "),
        destructive: [
          "bg-destructive text-destructive-foreground",
          "shadow-[var(--shadow-base-sm)]",
          "hover:scale-102 hover:shadow-destructive-glow",
          "active:scale-98 active:opacity-90",
        ].join(" "),
        link: "text-primary underline-offset-4 hover:underline focus-visible:underline",
      },
      size: {
        default: "h-10 px-4",
        sm: "h-9 px-3 text-xs rounded-[var(--radius-sm)]",
        lg: "h-11 px-6 text-base rounded-[var(--radius-lg)]",
        icon: "h-10 w-10 p-0 rounded-[var(--radius-md)]",
      },
      density: {
        normal: "py-2",
        compact: "py-1.5",
        relaxed: "py-2.5",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      density: "normal",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, density, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";

    return (
      <Comp
        data-slot="button"
        className={cn(buttonVariants({ variant, size, density }), className)}
        ref={ref}
        {...props}
      />
    );
  },
);

Button.displayName = "Button";

// Export types for external usage
export type ButtonVariant = NonNullable<VariantProps<typeof buttonVariants>["variant"]>;
export type ButtonSize = NonNullable<VariantProps<typeof buttonVariants>["size"]>;
export type ButtonDensity = NonNullable<VariantProps<typeof buttonVariants>["density"]>;

export { buttonVariants };

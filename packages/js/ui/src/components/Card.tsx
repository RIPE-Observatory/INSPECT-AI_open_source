import { type VariantProps, cva } from "class-variance-authority";
import type * as React from "react";
import { cn } from "../utils/cn";
import { typographyVariants } from "./Typography";

const cardVariants = cva(
  [
    "group/card relative flex flex-col",
    "rounded-[var(--radius-lg)] border border-border/70",
    "bg-card text-card-foreground transition-shadow duration-200 ease-[var(--ease-emphasized, cubic-bezier(0.2,0,0,1))]",
  ].join(" "),
  {
    variants: {
      variant: {
        default: "shadow-[var(--shadow-base-sm)] hover:shadow-[var(--shadow-base-md)]",
        elevated: "shadow-[var(--shadow-base-md)] hover:shadow-[var(--shadow-base-lg)]",
        outline: "shadow-none border-border/50 hover:border-border",
      },
      bleed: {
        none: "",
        subtle: "backdrop-blur-sm bg-card/80 border-border/50",
      },
    },
    defaultVariants: {
      variant: "default",
      bleed: "none",
    },
  },
);

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

export function Card({ className, variant, bleed, ...props }: CardProps) {
  return (
    <div data-slot="card" className={cn(cardVariants({ variant, bleed }), className)} {...props} />
  );
}

export function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn("flex flex-col gap-1.5 p-6 pb-0", className)}
      {...props}
    />
  );
}

export function CardTitle({ className, ...props }: React.ComponentProps<"h3">) {
  return (
    <h3
      data-slot="card-title"
      className={cn(typographyVariants({ variant: "h4" }), className)}
      {...props}
    />
  );
}

export function CardDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="card-description"
      className={cn(typographyVariants({ variant: "body-sm", tone: "muted" }), className)}
      {...props}
    />
  );
}

export function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div data-slot="card-action" className={cn("flex items-center gap-2", className)} {...props} />
  );
}

export function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="card-content" className={cn("flex-1 p-6 pt-4", className)} {...props} />;
}

export function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center gap-2 p-6 pt-4", className)}
      {...props}
    />
  );
}

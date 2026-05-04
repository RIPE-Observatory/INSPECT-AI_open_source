import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "../utils/cn";
import { typographyVariants } from "./Typography";

const baseAlert =
  "relative w-full grid items-start gap-y-[var(--space-2)] rounded-[var(--radius-lg)] border px-4 py-3 transition-all duration-200 ease-[var(--ease-emphasized)]";
const iconLayout =
  "has-[>svg]:grid-cols-[calc(var(--space-6))_1fr] grid-cols-[0_1fr] has-[>svg]:gap-x-3 [&>svg]:size-4 [&>svg]:translate-y-[1px] [&>svg]:shrink-0 [&>svg]:text-current";

const alertVariants = cva(cn(baseAlert, iconLayout, typographyVariants({ variant: "p" })), {
  variants: {
    variant: {
      default:
        "border-border/60 bg-surface-elevated text-foreground shadow-[var(--shadow-base-sm)]",
      muted: "border-border/50 bg-muted/40 text-muted-foreground shadow-[var(--shadow-base-xs)]",
      info: "border-info/40 bg-info/10 text-info backdrop-blur-sm shadow-[var(--shadow-base-xs)]",
      success:
        "border-success/40 bg-success/10 text-success backdrop-blur-sm shadow-[var(--shadow-base-xs)]",
      warning:
        "border-warning/40 bg-warning/10 text-warning backdrop-blur-sm shadow-[var(--shadow-base-xs)]",
      destructive:
        "border-destructive/55 bg-destructive/10 text-destructive backdrop-blur-sm shadow-[var(--shadow-base-xs)]",
    },
  },
  defaultVariants: {
    variant: "default",
  },
});

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

export const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="alert"
        role="alert"
        className={cn(alertVariants({ variant }), className)}
        {...props}
      />
    );
  },
);

Alert.displayName = "Alert";

export const AlertTitle = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="alert-title"
        className={cn(
          "col-start-2 min-h-4",
          typographyVariants({ variant: "h4" }),
          "text-base font-semibold leading-tight tracking-tight",
          className,
        )}
        {...props}
      />
    );
  },
);

AlertTitle.displayName = "AlertTitle";

export const AlertDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      data-slot="alert-description"
      className={cn(
        "col-start-2 grid justify-items-start gap-[var(--space-2)]",
        typographyVariants({ variant: "p" }),
        "text-sm [&_p]:leading-relaxed",
        className,
      )}
      {...props}
    />
  );
});

AlertDescription.displayName = "AlertDescription";

export { alertVariants };

"use client";

import * as React from "react";

import { cn, Label, typographyVariants } from "@inspect/ui";

const Field = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-[var(--space-2)]", className)} {...props} />
  ),
);
Field.displayName = "Field";

const Fieldset = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("grid gap-[var(--space-6)]", className)} {...props} />
  ),
);
Fieldset.displayName = "Fieldset";

const FieldLabel = React.forwardRef<
  React.ElementRef<typeof Label>,
  React.ComponentPropsWithoutRef<typeof Label>
>(({ className, ...props }, ref) => (
  <Label
    ref={ref}
    className={cn(
      typographyVariants({ variant: "label", weight: "strong" }),
      "leading-none tracking-normal text-foreground",
      className,
    )}
    {...props}
  />
));
FieldLabel.displayName = "FieldLabel";

const FieldDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn(
      typographyVariants({ variant: "body-sm", tone: "muted" }),
      className,
    )}
    {...props}
  />
));
FieldDescription.displayName = "FieldDescription";

const FieldHelper = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        typographyVariants({ variant: "body-xs", tone: "muted" }),
        className,
      )}
      {...props}
    />
  ),
);
FieldHelper.displayName = "FieldHelper";

const FieldError = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        typographyVariants({ variant: "body-sm", weight: "strong" }),
        "text-destructive",
        className,
      )}
      {...props}
    />
  ),
);
FieldError.displayName = "FieldError";

const FieldControl = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-[var(--space-2)]", className)} {...props} />
  ),
);
FieldControl.displayName = "FieldControl";

export { Field, Fieldset, FieldLabel, FieldDescription, FieldHelper, FieldError, FieldControl };

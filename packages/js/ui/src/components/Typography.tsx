import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";
import type { JSX } from "react";
import { cn } from "../utils/cn";

const typographyVariants = cva("type-root", {
  variants: {
    variant: {
      "display-xl": "type-display-xl",
      "display-lg": "type-display-lg",
      h1: "type-h1",
      h2: "type-h2",
      h3: "type-h3",
      h4: "type-h4",
      p: "type-body-md",
      lead: "type-lead",
      "body-lg": "type-body-lg",
      "body-md": "type-body-md",
      "body-sm": "type-body-sm",
      "body-xs": "type-body-xs",
      label: "type-label-sm",
      code: "type-code",
      // @deprecated Use variant="body-lg" with weight="strong" instead
      large: "type-body-lg type-strong",
      // @deprecated Use variant="label" instead
      small: "type-label-sm",
      // @deprecated Use variant="body-sm" with tone="muted" instead
      muted: "type-body-sm type-muted",
    },
    tone: {
      default: "",
      muted: "type-muted",
    },
    weight: {
      regular: "",
      strong: "type-strong",
    },
  },
  defaultVariants: {
    variant: "p",
    tone: "default",
    weight: "regular",
  },
});

type TypographyElement = "p" | "div" | "span" | "small" | "code" | "h1" | "h2" | "h3" | "h4";

export interface TypographyProps
  extends React.HTMLAttributes<HTMLElement>,
    VariantProps<typeof typographyVariants> {
  as?: TypographyElement;
}

export const Typography = React.forwardRef<HTMLElement, TypographyProps>(
  ({ className, variant, tone, weight, as, ...props }, ref) => {
    // Map variants to default HTML elements
    const defaultElement = {
      "display-xl": "h1",
      "display-lg": "h1",
      h1: "h1",
      h2: "h2",
      h3: "h3",
      h4: "h4",
      p: "p",
      lead: "p",
      "body-lg": "p",
      "body-md": "p",
      "body-sm": "p",
      "body-xs": "p",
      label: "span",
      code: "code",
      // Deprecated aliases
      large: "div",
      small: "small",
      muted: "p",
    }[variant || "p"] as TypographyElement;

    const Comp = as ?? defaultElement;

    return React.createElement(Comp, {
      ref,
      className: cn(typographyVariants({ variant, tone, weight }), className),
      ...props,
    });
  },
);

Typography.displayName = "Typography";

// Export types for external usage
export type TypographyVariant = NonNullable<VariantProps<typeof typographyVariants>["variant"]>;
export type TypographyTone = NonNullable<VariantProps<typeof typographyVariants>["tone"]>;
export type TypographyWeight = NonNullable<VariantProps<typeof typographyVariants>["weight"]>;

export { typographyVariants };

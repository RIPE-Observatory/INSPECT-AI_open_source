import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "../utils/cn";

const skeletonVariants = cva("rounded-[var(--radius-md)] bg-muted/40 motion-safe:animate-pulse", {
  variants: {
    variant: {
      default: "bg-muted/40",
      subtle: "bg-muted/20",
      strong: "bg-muted/60",
    },
    speed: {
      slow: "animate-pulse [animation-duration:2s]",
      default: "animate-pulse",
      fast: "animate-pulse [animation-duration:1s]",
    },
  },
  defaultVariants: {
    variant: "default",
    speed: "default",
  },
});

export interface SkeletonProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof skeletonVariants> {}

export const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, variant, speed, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="skeleton"
        className={cn(skeletonVariants({ variant, speed }), className)}
        {...props}
      />
    );
  },
);

Skeleton.displayName = "Skeleton";

export { skeletonVariants };

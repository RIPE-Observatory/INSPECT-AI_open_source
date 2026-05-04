"use client";

import type * as React from "react";

import { cn } from "@inspect/ui";

type Orientation = "horizontal" | "vertical";

interface LineDecoratorProps extends React.ComponentProps<"hr"> {
  orientation?: Orientation;
  delay?: number;
}

function LineDecorator({
  className,
  orientation = "horizontal",
  delay = 100,
  ...props
}: LineDecoratorProps): React.ReactElement {
  return (
    <hr
      className={cn(
        "border-dashed",
        orientation === "horizontal"
          ? "animate-expand-width-glow h-px w-full border-t"
          : "animate-expand-height-glow h-full w-px border-l",
        className,
      )}
      data-animation-delay-ms={delay}
      {...props}
    />
  );
}

export { LineDecorator };

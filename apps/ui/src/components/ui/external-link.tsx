import { cn, typographyVariants } from "@inspect/ui";
import { ExternalLink as ExternalLinkIcon } from "lucide-react";
import type * as React from "react";

interface ExternalLinkProps {
  href: string;
  children: React.ReactNode;
  className?: string;
  showIcon?: boolean;
  iconSize?: number;
}

/**
 * Reusable component for rendering external links with proper attributes
 * Automatically adds target="_blank" and rel="noopener noreferrer" for external URLs
 */
export function ExternalLink({
  href,
  children,
  className = "",
  showIcon = true,
  iconSize = 14,
}: ExternalLinkProps): React.ReactElement {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "inline-flex items-center gap-[var(--space-2)]",
        "text-info underline-offset-4 transition-colors duration-200 ease-[var(--ease-emphasized)]",
        "hover:text-info/80 hover:underline",
        typographyVariants({ variant: "small" }),
        className,
      )}
    >
      {children}
      {showIcon && <ExternalLinkIcon className="inline-block flex-shrink-0" size={iconSize} />}
    </a>
  );
}

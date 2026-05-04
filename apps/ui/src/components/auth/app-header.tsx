"use client";

import { Typography } from "@inspect/ui";
import Link from "next/link";
import { type ReactNode } from "react";

interface AppHeaderProps {
  title?: string;
  leftContent?: ReactNode;
  centerContent?: ReactNode;
  rightContent?: ReactNode;
}

export function AppHeader({ title, leftContent, centerContent, rightContent }: AppHeaderProps) {
  // Determine grid layout based on what content is provided
  const hasCenterContent = Boolean(centerContent);

  // Use a flexible grid layout when we have left and/or center content
  const layoutClass = hasCenterContent
    ? 'grid grid-cols-[auto_1fr_auto_1fr_auto] items-center gap-4'
    : 'flex items-center justify-between gap-6';

  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background">
      <div className={`container mx-auto px-4 py-3.5 ${layoutClass}`}>
        {/* Logo + Title */}
        <Link
          href="/"
          className="flex items-center gap-2 transition-colors duration-200 hover:text-primary"
        >
          <Typography variant="h4" className="text-foreground hover:text-primary transition-colors">
            INSPECT-AI
          </Typography>
          {title ? (
            <Typography variant="body-sm" tone="muted">
              · {title}
            </Typography>
          ) : null}
        </Link>

        {/* Left content: Optional content after logo (e.g., Status) */}
        {hasCenterContent && (
          <div className="flex items-center gap-3 justify-self-start">
            {leftContent}
          </div>
        )}

        {/* Center section: Optional centered content (e.g., Job ID) */}
        {hasCenterContent && (
          <div className="flex items-center justify-self-center">
            {centerContent}
          </div>
        )}

        {/* Spacer for center alignment */}
        {hasCenterContent && <div className="flex-1" />}

        {/* Right section: Optional right content */}
        {rightContent && (
          <div className="flex items-center gap-3 justify-self-end">
            {rightContent}
          </div>
        )}
      </div>
    </header>
  );
}

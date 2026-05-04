"use client";

import type * as React from "react";

import { Card, CardContent, Typography, cn } from "@inspect/ui";

interface PageShellProps extends React.HTMLAttributes<HTMLDivElement> {
  fullHeight?: boolean;
}

function PageShell({ fullHeight = false, className, children, ...props }: PageShellProps) {
  return (
    <div
      className={cn(
        "mx-auto flex w-full max-w-6xl flex-1 flex-col gap-[var(--space-6)] px-4 pb-16 pt-10",
        fullHeight && "min-h-screen",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

interface PageHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

function PageHeader({ title, description, actions, className, ...props }: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-[var(--space-4)] rounded border border-border/60 bg-surface shadow-[var(--shadow-base-sm)] p-6 sm:flex-row sm:items-center sm:justify-between",
        className,
      )}
      {...props}
    >
      <div className="flex flex-1 flex-col gap-[var(--space-2)]">
        {typeof title === "string" ? <Typography variant="h2">{title}</Typography> : title}
        {description ? (
          <Typography variant="body-sm" tone="muted" className="max-w-3xl">
            {description}
          </Typography>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-[var(--space-2)]">{actions}</div> : null}
    </header>
  );
}

interface PageSectionProps extends React.HTMLAttributes<HTMLDivElement> {
  header?: React.ReactNode;
  footer?: React.ReactNode;
  bleed?: boolean;
}

function PageSection({
  header,
  footer,
  children,
  bleed = false,
  className,
  ...props
}: PageSectionProps) {
  return (
    <Card
      className={cn(
        "flex flex-col gap-[var(--space-4)]",
        bleed && "bg-surface-elevated",
        className,
      )}
      {...props}
    >
      {header ? <CardContent className="pt-6 pb-0">{header}</CardContent> : null}
      <CardContent className="flex flex-col gap-[var(--space-4)]">{children}</CardContent>
      {footer ? <CardContent className="pt-0 pb-6">{footer}</CardContent> : null}
    </Card>
  );
}

export { PageHeader, PageSection, PageShell };
export { AppFooter } from "./app-footer";

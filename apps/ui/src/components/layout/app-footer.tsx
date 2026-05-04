"use client";

import { Typography } from "@inspect/ui";
import { Fragment } from "react";

const TECHNOLOGY_LINKS = [
  { label: "FastAPI", href: "https://fastapi.tiangolo.com/" },
  { label: "Next.js", href: "https://nextjs.org/" },
  { label: "shadcn/ui", href: "https://ui.shadcn.com/" },
  { label: "UV", href: "https://docs.astral.sh/uv/" },
  { label: "Bun", href: "https://bun.sh/" },
] as const;

export function AppFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-auto px-6 py-8 border-t border-border/70 bg-background">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-2 text-center sm:flex-row sm:items-center sm:justify-between sm:text-left">
        <Typography variant="body-sm" tone="muted">
          &copy; {currentYear} INSPECT-AI. All rights reserved.
        </Typography>
        <Typography variant="body-sm" tone="muted">
          Powered by{" "}
          {TECHNOLOGY_LINKS.map((tech, index) => {
            const isLast = index === TECHNOLOGY_LINKS.length - 1;
            const isSecondLast = index === TECHNOLOGY_LINKS.length - 2;
            const separator = isLast ? "" : isSecondLast ? " and " : ", ";

            return (
              <Fragment key={tech.href}>
                <a
                  href={tech.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition-all duration-200 hover:text-primary hover:underline underline-offset-4 decoration-primary/60"
                >
                  {tech.label}
                </a>
                {!isLast && separator}
              </Fragment>
            );
          })}
          .
        </Typography>
      </div>
    </footer>
  );
}

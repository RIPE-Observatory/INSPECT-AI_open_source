"use client";

import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useCallback, useEffect } from "react";

// Matching header button styles from JobResultsClient
const navButtonBase =
  "flex items-center gap-1.5 rounded border border-border bg-background px-3 py-1.5 text-sm font-medium transition-colors duration-150";
const navButtonInteractive =
  "hover:border-foreground hover:bg-foreground hover:text-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background";
const navButtonDisabled =
  "opacity-40 cursor-not-allowed hover:border-border hover:bg-background hover:text-foreground";

interface SectionNavigationProps {
  currentIndex: number;
  totalSections: number;
  onPrevious: () => void;
  onNext: () => void;
  disabled?: boolean;
  /** Disable navigation while a save is in progress */
  isSaving?: boolean;
}

export function SectionNavigation({
  currentIndex,
  totalSections,
  onPrevious,
  onNext,
  disabled = false,
  isSaving = false,
}: SectionNavigationProps) {
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === totalSections - 1;
  // Combine disabled and isSaving for overall disable state
  const isDisabled = disabled || isSaving;

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Don't navigate if user is typing in an input/textarea
      const target = event.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      if (event.key === "ArrowLeft" && !isFirst && !isDisabled) {
        event.preventDefault();
        onPrevious();
      } else if (event.key === "ArrowRight" && !isLast && !isDisabled) {
        event.preventDefault();
        onNext();
      }
    },
    [isFirst, isLast, isDisabled, onPrevious, onNext]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="bg-background border-t border-border py-2.5 px-6">
      <div className="flex items-center justify-between">
        {/* Keyboard hint - left side */}
        <p className="text-[11px] text-muted-foreground/50 flex items-center gap-1">
          <kbd className="inline-flex items-center justify-center w-5 h-5 rounded bg-muted/50 text-muted-foreground text-[10px] font-mono">←</kbd>
          <kbd className="inline-flex items-center justify-center w-5 h-5 rounded bg-muted/50 text-muted-foreground text-[10px] font-mono">→</kbd>
        </p>

        {/* Center: Navigation controls */}
        <div className="flex items-center gap-6">
          {/* Previous Button */}
          <button
            type="button"
            onClick={onPrevious}
            disabled={isFirst || isDisabled}
            className={`${navButtonBase} ${isFirst || isDisabled ? navButtonDisabled : navButtonInteractive}`}
          >
            {isSaving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ChevronLeft className="h-3.5 w-3.5" />
            )}
            <span>Previous</span>
          </button>

          {/* Dots + Position */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              {Array.from({ length: totalSections }).map((_, index) => (
                <div
                  key={index}
                  className={`h-1.5 rounded-full transition-all duration-200 ${
                    index === currentIndex
                      ? "w-4 bg-primary"
                      : "w-1.5 bg-muted-foreground/30"
                  }`}
                />
              ))}
            </div>
            <span className="text-xs text-muted-foreground tabular-nums">
              {currentIndex + 1}/{totalSections}
            </span>
          </div>

          {/* Next Button */}
          <button
            type="button"
            onClick={onNext}
            disabled={isLast || isDisabled}
            className={`${navButtonBase} ${isLast || isDisabled ? navButtonDisabled : navButtonInteractive}`}
          >
            <span>Next</span>
            {isSaving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        </div>

        {/* Spacer to balance the layout */}
        <div className="w-[52px]" />
      </div>
    </div>
  );
}

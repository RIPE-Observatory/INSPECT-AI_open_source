"use client";

import { Typography } from "@inspect/ui";
import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface AssessmentProgressBarProps {
  percent: number;
  answeredChecks: number;
  totalChecks: number;
  overallAnswered: boolean;
  className?: string;
}

export function AssessmentProgressBar({
  percent,
  answeredChecks,
  totalChecks,
  overallAnswered,
  className,
}: AssessmentProgressBarProps) {
  // Determine color based on progress
  const getProgressColor = () => {
    if (overallAnswered || percent === 100) return "bg-success";
    if (percent >= 75) return "bg-success/80";
    if (percent >= 50) return "bg-warning";
    if (percent >= 25) return "bg-warning/70";
    return "bg-info/60";
  };

  const getBorderColor = () => {
    if (overallAnswered || percent === 100) return "border-success/50";
    if (percent >= 50) return "border-warning/50";
    return "border-border";
  };

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* Progress bar container */}
      <div
        className={cn(
          "relative h-2.5 w-32 overflow-hidden rounded-full border bg-muted/30",
          getBorderColor()
        )}
      >
        {/* Progress fill */}
        <div
          className={cn(
            "absolute inset-y-0 left-0 transition-all duration-500 ease-out rounded-full",
            getProgressColor()
          )}
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Progress text */}
      <div className="flex items-center gap-1.5">
        {overallAnswered ? (
          <>
            <CheckCircle2 className="h-4 w-4 text-success" />
            <Typography variant="body-sm" weight="strong" className="text-success">
              Complete
            </Typography>
          </>
        ) : (
          <Typography variant="body-sm" tone="muted">
            <span className="font-semibold text-foreground">{answeredChecks}</span>
            <span>/{totalChecks} checks</span>
          </Typography>
        )}
      </div>
    </div>
  );
}

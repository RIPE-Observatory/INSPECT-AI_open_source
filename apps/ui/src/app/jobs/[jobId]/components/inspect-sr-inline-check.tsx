"use client";

import { BookOpen, BrainCircuit, Check, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button, Textarea, Typography } from "@inspect/ui";
import { cn } from "@/lib/utils";
import type { InspectSRQuestion } from "@inspect/api-client";
import type { StatusToken } from "../utils/shared";

const ANSWER_OPTIONS: Array<{
  value: InspectSRQuestion["reviewed_judgement"];
  label: string;
  tone: "positive" | "negative" | "neutral" | "warning";
}> = [
  { value: "yes", label: "Yes", tone: "negative" },
  { value: "no", label: "No", tone: "positive" },
  { value: "unclear", label: "Unclear", tone: "warning" },
  { value: "na", label: "N/A", tone: "neutral" },
];

const JUDGEMENT_OPTIONS: Array<{
  value: InspectSRQuestion["reviewed_judgement"];
  label: string;
  tone: "positive" | "negative" | "warning";
}> = [
  { value: "no-concerns", label: "No concerns", tone: "positive" },
  { value: "some-concerns", label: "Some concerns", tone: "warning" },
  { value: "serious-concerns", label: "Serious concerns", tone: "negative" },
];

const toneStyles = {
  positive: {
    base: "border-success/60 text-success hover:border-success hover:bg-success/10 hover:text-success",
    selected: "border-success bg-success text-white shadow-[var(--shadow-base-sm)]",
  },
  negative: {
    base: "border-destructive/60 text-destructive hover:border-destructive hover:bg-destructive/10 hover:text-destructive",
    selected: "border-destructive bg-destructive text-white shadow-[var(--shadow-base-sm)]",
  },
  neutral: {
    base: "border-border text-muted-foreground hover:border-border/70 hover:bg-muted/10",
    selected: "border-foreground bg-foreground text-background shadow-[var(--shadow-base-sm)]",
  },
  warning: {
    base: "border-warning/60 text-warning hover:border-warning hover:bg-warning/10 hover:text-warning",
    selected: "border-warning bg-warning text-white shadow-[var(--shadow-base-sm)]",
  },
} as const;

export interface InspectSRInlineCheckProps {
  heading: string;
  helperLabel?: string;
  record?: InspectSRQuestion;
  status?: StatusToken;
  isLoading?: boolean;
  isSaving?: boolean;
  errorMessage?: string | null;
  questionType?: "check" | "judgement";
  questionId?: string;
  hasGuidance?: boolean;
  /** Controlled comment draft value from parent (survives section switches) */
  commentDraft?: string;
  /** Callback when user types in comment box (controlled mode) */
  onCommentChange?: (value: string) => void;
  /** Whether user has interacted with comment in current session (controlled from parent) */
  hasInteracted?: boolean;
  /** Callback when user starts interacting with comment */
  onInteractionStart?: () => void;
  onAnswerChange: (value: InspectSRQuestion["reviewed_judgement"]) => void;
  onClearAnswer?: () => void;
  onCommentSave: (value: string) => void;
  onOpenGuidance?: () => void;
}

export function InspectSRInlineCheck({
  heading,
  record,
  status, // eslint-disable-line @typescript-eslint/no-unused-vars
  isLoading = false,
  isSaving = false,
  errorMessage,
  questionType = "check",
  questionId, // Reserved for accessibility/testing
  hasGuidance = false,
  commentDraft: controlledCommentDraft,
  onCommentChange,
  hasInteracted: controlledHasInteracted,
  onInteractionStart,
  onAnswerChange,
  onClearAnswer,
  onCommentSave,
  onOpenGuidance,
}: InspectSRInlineCheckProps) {
  // Silence unused var warnings for props reserved for future use
  void questionId; // Reserved for accessibility/testing

  // Determine if running in controlled mode (props from parent) or uncontrolled (local state)
  const isControlled = controlledCommentDraft !== undefined;

  // Local state - used when NOT in controlled mode (backward compatibility)
  const [localCommentDraft, setLocalCommentDraft] = useState(record?.comment ?? "");
  const [localHasInteracted, setLocalHasInteracted] = useState(false);
  const [isSavingComment, setIsSavingComment] = useState(false);
  const prevIsSavingRef = useRef(isSaving);

  // Use controlled or local state based on mode
  const commentDraft = isControlled ? controlledCommentDraft : localCommentDraft;
  const hasInteracted = isControlled ? (controlledHasInteracted ?? false) : localHasInteracted;

  // Sync local comment draft when record updates (only in uncontrolled mode)
  useEffect(() => {
    if (!isControlled && !isSavingComment) {
      setLocalCommentDraft(record?.comment ?? "");
    }
  }, [record?.comment, isSavingComment, isControlled]);

  // Track when saving completes (success or error)
  useEffect(() => {
    // Detect transition from saving → not saving (mutation finished)
    if (prevIsSavingRef.current && !isSaving) {
      setIsSavingComment(false);
    }
    prevIsSavingRef.current = isSaving;
  }, [isSaving]);

  // Clear saving state on error
  useEffect(() => {
    if (errorMessage && isSavingComment) {
      setIsSavingComment(false);
    }
  }, [errorMessage, isSavingComment]);

  const hasCommentChanged = useMemo(
    () => commentDraft !== (record?.comment ?? ""),
    [commentDraft, record?.comment],
  );

  // Handle comment text changes
  const handleCommentTextChange = useCallback((value: string) => {
    // Mark as interacted when user first types
    if (!hasInteracted) {
      if (isControlled && onInteractionStart) {
        onInteractionStart();
      } else if (!isControlled) {
        setLocalHasInteracted(true);
      }
    }

    // Update the draft value
    if (isControlled && onCommentChange) {
      onCommentChange(value);
    } else {
      setLocalCommentDraft(value);
    }
  }, [hasInteracted, isControlled, onInteractionStart, onCommentChange]);

  const handleCommentSave = useCallback(() => {
    if (!hasCommentChanged || isSavingComment) return;

    // Immediately show saving state
    setIsSavingComment(true);
    onCommentSave(commentDraft);
  }, [hasCommentChanged, isSavingComment, commentDraft, onCommentSave]);

  // Display user's reviewed answer (if they clicked a button)
  const displayAnswer = useMemo(() => {
    return record?.reviewed_judgement ?? null;
  }, [record?.reviewed_judgement]);

  // Render the status indicator and save button
  // Status logic based on plan:
  // - pristine: hasInteracted=false && no saved comment → show nothing
  // - saved from server: hasInteracted=false && has saved comment → ✓ Saved
  // - saved by user: hasInteracted=true && commentDraft === record.comment → ✓ Saved
  // - unsaved: hasInteracted=true && commentDraft !== record.comment → Unsaved changes
  // - saving: isSavingComment=true → Saving...
  // - error: errorMessage && hasCommentChanged → Save failed
  const renderSaveArea = () => {
    const showError = errorMessage && hasCommentChanged;
    const hasSavedComment = Boolean(record?.comment);

    // State: Saving in progress
    if (isSavingComment) {
      return (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            <span className="text-sm text-primary">Saving...</span>
          </div>
        </div>
      );
    }

    // State: Error occurred during save
    if (showError) {
      return (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-destructive" />
            <span className="text-sm text-destructive">Save failed - try again</span>
          </div>
          <button
            type="button"
            onClick={handleCommentSave}
            className="flex items-center justify-center gap-2 rounded border border-border bg-background px-6 py-1.5 text-sm font-medium transition-colors duration-150 hover:border-foreground hover:bg-foreground hover:text-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            Retry
          </button>
        </div>
      );
    }

    // State: Unsaved changes
    if (hasCommentChanged) {
      return (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-warning" />
            <span className="text-sm text-warning">Unsaved changes</span>
          </div>
          <button
            type="button"
            onClick={handleCommentSave}
            className="flex items-center justify-center gap-2 rounded border border-border bg-background px-6 py-1.5 text-sm font-medium transition-colors duration-150 hover:border-foreground hover:bg-foreground hover:text-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            Save
          </button>
        </div>
      );
    }

    // State: Pristine (never interacted + no server comment) → show nothing
    if (!hasInteracted && !hasSavedComment) {
      return null;
    }

    // State: Saved (either from server or after user saved)
    return (
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Check className="h-3.5 w-3.5 text-success" />
          <span className="text-sm text-success">Saved</span>
        </div>
      </div>
    );
  };

  return (
    <div className="rounded border border-border bg-background p-6 shadow-sm space-y-4">
      <div className="flex items-start justify-between gap-4">
        <Typography variant="h4">{heading}</Typography>
        {hasGuidance && onOpenGuidance && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onOpenGuidance}
            className="flex-shrink-0 gap-2 text-primary hover:bg-primary/10 hover:text-primary"
          >
            <BookOpen className="h-4 w-4" />
            <span className="hidden sm:inline">INSPECT-SR Guidance</span>
            <span className="sm:hidden">Guidance</span>
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <Typography variant="body-sm" tone="muted">Loading INSPECT-SR data...</Typography>
        </div>
      ) : (
        <>
          {/* Show automated judgement if exists - Hybrid design with programmatic coloring */}
          {record?.automated_judgement && (() => {
            const judgement = record.automated_judgement;
            // Determine color based on judgement value
            const getColorClasses = () => {
              if (questionType === "judgement") {
                // For judgement questions (OVERALL, domain overalls)
                if (judgement === "serious-concerns") return { border: "border-destructive/50", icon: "text-destructive", text: "text-destructive" };
                if (judgement === "some-concerns") return { border: "border-warning/50", icon: "text-warning", text: "text-warning" };
                if (judgement === "no-concerns") return { border: "border-success/50", icon: "text-success", text: "text-success" };
              } else {
                // For check questions (yes/no/unclear/na)
                if (judgement === "yes") return { border: "border-destructive/50", icon: "text-destructive", text: "text-destructive" };
                if (judgement === "no") return { border: "border-success/50", icon: "text-success", text: "text-success" };
                if (judgement === "unclear") return { border: "border-warning/50", icon: "text-warning", text: "text-warning" };
                if (judgement === "na") return { border: "border-border/50", icon: "text-muted-foreground", text: "text-muted-foreground" };
              }
              return { border: "border-border/50", icon: "text-primary", text: "text-primary" };
            };
            const colors = getColorClasses();

            return (
              <div className={cn("mb-3 inline-flex items-center gap-2 rounded border bg-background px-4 py-2", colors.border)}>
                <BrainCircuit className={cn("h-4 w-4 flex-shrink-0", colors.icon)} />
                <Typography variant="body-sm">
                  <span>INSPECT-AI Suggestion:</span>{" "}
                  <span className={cn("capitalize font-semibold", colors.text)}>{judgement.replace(/-/g, " ")}</span>
                </Typography>
              </div>
            );
          })()}

          <div className="flex flex-wrap gap-3">
            {(questionType === "judgement" ? JUDGEMENT_OPTIONS : ANSWER_OPTIONS).map((option) => {
              const isSelected = displayAnswer === option.value;
              return (
                <Button
                  key={option.value ?? "unset"}
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={isSaving}
                  onClick={() => onAnswerChange(option.value)}
                  className={cn(
                    questionType === "judgement" ? "w-36" : "min-w-[72px]",
                    isSelected ? toneStyles[option.tone].selected : toneStyles[option.tone].base,
                  )}
                >
                  {option.label}
                </Button>
              );
            })}
            {record?.reviewed_judgement && onClearAnswer && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={isSaving}
                onClick={onClearAnswer}
                className="text-muted-foreground hover:text-foreground"
              >
                Clear
              </Button>
            )}
          </div>

          <div className="space-y-2">
            <Typography variant="body-sm" tone="muted" className="block">
              <label htmlFor={`${record?.question_id ?? "comment"}-comment`}>
                Comments
              </label>
            </Typography>
            <Textarea
              id={`${record?.question_id ?? "comment"}-comment`}
              value={commentDraft}
              onChange={(event) => handleCommentTextChange(event.target.value)}
              onBlur={handleCommentSave}
              placeholder="Add comments..."
              className="min-h-[120px] resize-none"
              disabled={isSavingComment}
            />
            {renderSaveArea()}
          </div>

          {errorMessage && (
            <div className="rounded border border-destructive bg-destructive/10 px-3 py-2">
              <Typography variant="body-xs" className="text-destructive/80">{errorMessage}</Typography>
            </div>
          )}
        </>
      )}
    </div>
  );
}

"use client";

import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Typography,
} from "@inspect/ui";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  RotateCcw,
  X,
} from "lucide-react";
import type { ReactNode } from "react";
import type { QueueInfo } from "../hooks/useUploadQueueManager";

interface QueueRecoveryModalProps {
  queueInfo: QueueInfo;
  onRestore: () => void;
  onDismiss: () => void;
}

const STATUS_LABEL: Record<string, string> = {
  pending: "Ready to upload",
  queued: "Queued for analysis",
  completed: "Analysis complete",
  error: "Error occurred",
};

const STATUS_ICON: Record<string, ReactNode> = {
  completed: <CheckCircle className="h-4 w-4 text-success" />,
  queued: <Clock className="h-4 w-4 text-info" />,
  error: <AlertTriangle className="h-4 w-4 text-destructive" />,
  default: <FileText className="h-4 w-4 text-muted-foreground" />,
};

export default function QueueRecoveryModal({
  queueInfo,
  onRestore,
  onDismiss,
}: QueueRecoveryModalProps) {
  // Only show files that were successfully uploaded (have jobIds)
  const recoverableFiles = queueInfo.files.filter(f => f.jobId);

  // If no recoverable files, don't show modal
  if (recoverableFiles.length === 0) {
    onDismiss();
    return null;
  }

  const formatDate = (date: Date) =>
    date.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  const statusCounts = recoverableFiles.reduce<Record<string, number>>((acc, file) => {
    acc[file.status] = (acc[file.status] ?? 0) + 1;
    return acc;
  }, {});

  const getStatusIcon = (status: string) => STATUS_ICON[status] ?? STATUS_ICON.default;
  const getStatusText = (status: string) => STATUS_LABEL[status] ?? status;

  return (
    <Dialog open onOpenChange={(isOpen) => !isOpen && onDismiss()}>
      <DialogContent
        variant="elevated"
        size="xl"
        className="max-w-2xl"
        showCloseButton={false}
        onInteractOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-info" />
            <DialogTitle>Continue Working?</DialogTitle>
          </div>
          <DialogDescription>
            You have {recoverableFiles.length} {recoverableFiles.length === 1 ? 'analysis' : 'analyses'} from your previous session.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 overflow-y-auto pr-1 max-h-[60vh]">
          <section className="rounded border border-border/50 bg-surface/60 p-4 shadow-[var(--shadow-base-sm)]">
            <Typography variant="label" className="uppercase text-muted-foreground">
              Queue details
            </Typography>
            <div className="mt-2 flex items-baseline gap-2">
              <Typography variant="body-sm" tone="muted" weight="strong">
                Saved:
              </Typography>
              <Typography variant="p">{formatDate(queueInfo.timestamp)}</Typography>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {Object.entries(statusCounts).map(([status, count]) => (
                <Badge key={status} variant="outline" density="relaxed">
                  {getStatusIcon(status)}
                  <span className="capitalize">{status}</span>
                  <Typography as="span" variant="body-md" weight="strong">{count}</Typography>
                </Badge>
              ))}
            </div>
          </section>

          <section className="rounded border border-border/40 bg-surface/60 p-4 shadow-[var(--shadow-base-sm)]">
            <Typography variant="h4" className="mb-3">
              Analyses ({recoverableFiles.length})
            </Typography>
            <div className="space-y-2">
              {recoverableFiles.map((file) => (
                <div
                  key={`${file.file.name}-${file.timestamp.getTime()}`}
                  className="flex items-center justify-between gap-3 rounded border border-border/50 bg-background/40 p-3"
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <div className="relative">
                      <div className="absolute inset-0 rounded bg-destructive/40 blur" />
                      <FileText className="relative h-5 w-5 text-destructive" />
                    </div>
                    <div className="min-w-0 space-y-1">
                      <Typography variant="p" className="truncate" title={file.file.name}>
                        {file.file.name}
                      </Typography>
                      <Typography variant="body-sm" tone="muted">
                        {((file.originalSize ?? file.file.size) / 1024 / 1024).toFixed(1)} MB
                      </Typography>
                    </div>
                  </div>

                  <div className="flex flex-shrink-0 items-center gap-2">
                    <Badge variant="outline" density="compact">
                      {getStatusIcon(file.status)}
                      {getStatusText(file.status)}
                    </Badge>
                    {file.status === "completed" && file.jobId && (
                      <Badge variant="success" density="compact">
                        <CheckCircle className="h-3 w-3" />
                        Ready
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="text-center">
          <Typography variant="body-sm" tone="muted">
            All analyses are automatically saved
          </Typography>
        </div>

        <DialogFooter>
          <Button onClick={onRestore} variant="default" size="lg" className="flex-1">
            <RotateCcw className="h-4 w-4" />
            Continue Working
          </Button>
          <Button onClick={onDismiss} variant="outline" size="lg" className="flex-1">
            <X className="h-4 w-4" />
            Start Fresh
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

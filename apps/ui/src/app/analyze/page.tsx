"use client";

import { ProfileGuard } from "@/components/auth/ProfileGuard";
import { AppHeader } from "@/components/auth/app-header";
import { Alert, Badge, Button, Card, CardContent, CardHeader, Typography } from "@inspect/ui";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle,
  Clock,
  ExternalLink,
  FileText,
  Files,
  FolderSearch2,
  Info,
  Loader,
  Upload,
  X,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { jobKeys, useAnalyzeDocument, useJobStatus } from "@inspect/api-client";
import type { JobStatusResponse } from "@inspect/api-client";
import { toast } from "sonner";
// import QueueRecoveryModal from "./components/QueueRecoveryModal"; // Disabled for beta
import { type UploadedFile, useUploadQueueManager } from "./hooks/useUploadQueueManager";

const MAX_DISPLAY_FILENAME_LENGTH = 65; // Max length for displayed filename
const MAX_FILES_BETA = 5; // Beta limit: maximum 5 files at once

export default function AnalyzePage() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const queryClient = useQueryClient();

  const updateFile = useCallback(
    (index: number, updater: (current: UploadedFile) => UploadedFile) => {
      setFiles((prev) =>
        prev.map((file, fileIndex) => (fileIndex === index ? updater(file) : file)),
      );
    },
    [],
  );

  const handleQueueRestore = useCallback((restoredFiles: UploadedFile[]) => {
    // Only restore files that were successfully uploaded (have jobIds)
    const recoverableFiles = restoredFiles.filter(f => f.jobId);
    setFiles(recoverableFiles);
  }, []);

  // Queue manager hook for localStorage
  const {
    isQueueAvailable,
    queueInfo,
    restoreQueue,
    // dismissQueue, // Not needed - auto-restore for beta
  } = useUploadQueueManager(files, handleQueueRestore);

  // Auto-restore queue on mount (no modal for beta)
  useEffect(() => {
    if (isQueueAvailable && queueInfo) {
      restoreQueue();
    }
  }, [isQueueAvailable, queueInfo, restoreQueue]);

  const handleFileSelect = useCallback((selectedFiles: FileList) => {
    const newFiles: UploadedFile[] = Array.from(selectedFiles)
      .filter((file) => file.type === "application/pdf")
      .map((file) => ({
        id: `${file.name}-${Date.now()}-${Math.random()}`, // Unique ID for React key
        file, // Store the actual File object
        progress: 0,
        status: "pending" as const,
        timestamp: new Date(),
        originalSize: file.size,
        isPlaceholder: false,
      }));

    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      if (e.dataTransfer.files) {
        handleFileSelect(e.dataTransfer.files);
      }
    },
    [handleFileSelect],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const analyzeDocument = useAnalyzeDocument();

  const startSingleAnalysis = useCallback(
    (index: number) => {
      const file = files[index];
      if (!file) return;

      if (file.isPlaceholder) {
        updateFile(index, (current) => ({
          ...current,
          status: "error",
          error: "Select the original PDF again before uploading.",
        }));
        return;
      }

      updateFile(index, (current) => ({
        ...current,
        status: "uploading",
        progress: 0,
        error: undefined,
      }));

      const formData = new FormData();
      formData.append("file", file.file);
      formData.append("identifier", file.file.name);

      analyzeDocument.mutate(formData, {
        onSuccess: (result) => {
          if (!result?.job_id) {
            updateFile(index, (current) => ({
              ...current,
              status: "error",
              error: "Upload succeeded but job ID was missing.",
              progress: 0,
            }));
            return;
          }

          updateFile(index, (current) => ({
            ...current,
            status: "processing",
            progress: 100,
            jobId: result.job_id,
            error: undefined,
          }));

          queryClient.invalidateQueries({ queryKey: jobKeys.status(result.job_id) });
        },
        onError: (error) => {
          updateFile(index, (current) => ({
            ...current,
            status: "error",
            error: error instanceof Error ? error.message : "Upload failed",
            progress: 0,
          }));
        },
      });
    },
    [analyzeDocument, files, queryClient, updateFile],
  );

  const startAllAnalysis = useCallback(async () => {
    // Count all pending files
    const allPendingFiles = files
      .map((file, index) => ({ file, index }))
      .filter(({ file }) => file.status === "pending");

    if (allPendingFiles.length === 0) return;

    // Validate 5-file limit BEFORE processing
    if (allPendingFiles.length > MAX_FILES_BETA) {
      const excess = allPendingFiles.length - MAX_FILES_BETA;
      toast.error(
        `You have ${allPendingFiles.length} pending files. Please remove ${excess} ${excess === 1 ? "file" : "files"} to meet the ${MAX_FILES_BETA}-file limit.`
      );
      return; // Block processing entirely
    }

    // Only process if validation passed
    const pendingFiles = allPendingFiles;

    // Step 1: Mark all as queued with position
    pendingFiles.forEach(({ index }, queuePosition) => {
      updateFile(index, (current) => ({
        ...current,
        status: "queued",
        queuePosition: queuePosition + 1, // 1-indexed for UX
      }));
    });

    // Step 2: Upload sequentially with delay between each
    for (let i = 0; i < pendingFiles.length; i++) {
      const { index } = pendingFiles[i];

      try {
        await startSingleAnalysis(index);
      } catch {
        // Continue with next file even if one fails
      }

      // 3 second delay between uploads (ensures we stay under 5/minute limit)
      if (i < pendingFiles.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    }
  }, [files, startSingleAnalysis, updateFile]);

  const handleJobStatusUpdate = useCallback(
    (index: number, job: JobStatusResponse) => {
      updateFile(index, (current) => {
        if (!current.jobId || current.jobId !== job.id) {
          return current;
        }

        let nextStatus: UploadedFile["status"] = current.status;
        if (job.status === "COMPLETED") {
          nextStatus = "completed";
        } else if (job.status === "FAILED") {
          nextStatus = "error";
        } else if (job.status === "RUNNING" || job.status === "PENDING") {
          nextStatus = "processing";
        }

        return {
          ...current,
          status: nextStatus,
          progress: nextStatus === "completed" ? 100 : current.progress,
          error:
            nextStatus === "error"
              ? (job.error_message ?? "Analysis failed. Please try again.")
              : undefined,
        } satisfies UploadedFile;
      });
    },
    [updateFile],
  );

  const handleJobStatusError = useCallback(
    (index: number, error: Error) => {
      updateFile(index, (current) => ({
        ...current,
        status: "error",
        error: error.message,
      }));
    },
    [updateFile],
  );

  // Handle view results - navigate to job page
  const handleViewResults = useCallback((jobId: string) => {
    window.open(`/jobs/${jobId}`, "_blank", "noopener,noreferrer");
  }, []);

  const getStatusBadge = (fileData: UploadedFile, index?: number) => {
    if (fileData.isPlaceholder && fileData.status === "pending") {
      return (
        <Badge variant="warning" density="compact">
          <AlertCircle className="h-3 w-3" />
          Reselect file to resume
        </Badge>
      );
    }

    switch (fileData.status) {
      case "pending":
        return (
          <Badge variant="outline" density="compact">
            Ready to upload
          </Badge>
        );
      case "queued":
        return (
          <Badge variant="info" density="compact">
            <Clock className="h-3 w-3" />
            Queued (Position {fileData.queuePosition || index || 0})
          </Badge>
        );
      case "uploading":
        return (
          <Badge variant="info" density="compact">
            <Loader className="h-3 w-3 animate-spin" />
            Uploading...
          </Badge>
        );
      case "completed":
        return (
          <Badge variant="success" density="compact">
            <CheckCircle className="h-3 w-3" />
            Completed
          </Badge>
        );
      case "error":
        return (
          <Badge variant="destructive" density="compact">
            <AlertCircle className="h-3 w-3" />
            Error occurred
          </Badge>
        );
      case "processing":
        return (
          <Badge variant="warning" density="compact">
            <Loader className="h-3 w-3 animate-spin" />
            Processing...
          </Badge>
        );
      default:
        return null;
    }
  };

  // Count processing files for header
  const processingCount = files.filter(
    (f) => f.status === "uploading" || f.status === "processing",
  ).length;
  const queuedCount = files.filter((f) => f.status === "queued").length;
  const completedCount = files.filter((f) => f.status === "completed").length;

  const hasActiveJobs = processingCount > 0 || queuedCount > 0 || completedCount > 0;

  return (
    <ProfileGuard>
      {/* Queue Recovery Modal - Disabled for beta: auto-restore instead */}

      <main className="relative min-h-screen bg-background">
        <AppHeader title="PDF Upload & Management" />

        <div className="container mx-auto px-6 py-12 max-w-4xl">
          <div className="space-y-12">
            {/* Header Section - Clean, No Card */}
            <div className="text-center space-y-4 animate-fade-up animation-delay-100">
              <Typography variant="h1">
                Upload Clinical Trial Documents
              </Typography>
              <Typography variant="lead" className="max-w-3xl mx-auto">
                Queue multiple PDFs and track analysis progress in real-time.
              </Typography>
            </div>

            {/* Status Overview Badges */}
            {hasActiveJobs && (
              <div className="flex flex-wrap justify-center gap-3 animate-fade-up animation-delay-200">
                {processingCount > 0 && (
                  <Badge variant="info" density="relaxed">
                    <Loader className="h-4 w-4 animate-spin" />
                    Processing: {processingCount}
                  </Badge>
                )}
                {queuedCount > 0 && (
                  <Badge variant="warning" density="relaxed">
                    <Clock className="h-4 w-4" />
                    Queued: {queuedCount}
                  </Badge>
                )}
                {completedCount > 0 && (
                  <Badge variant="success" density="relaxed">
                    <CheckCircle className="h-4 w-4" />
                    Completed: {completedCount}
                  </Badge>
                )}
              </div>
            )}

            {/* Upload Dropzone - Hero, Standalone */}
            <label className="block cursor-pointer animate-fade-scale animation-delay-300">
              <input
                type="file"
                multiple
                accept=".pdf"
                onChange={(e) => e.target.files && handleFileSelect(e.target.files)}
                className="hidden"
              />
              <div
                className={cn(
                  "rounded border-2 border-dashed border-border/40 bg-surface/30 p-12 text-center",
                  "transition-all duration-200 ease-[var(--ease-emphasized)]",
                  "hover:border-primary/60 hover:bg-primary/5 hover:shadow-[var(--shadow-base-md)]",
                  isDragOver && "border-primary/70 bg-primary/10 shadow-[var(--shadow-base-lg)]",
                )}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                <div className="relative mb-6">
                  <div className="absolute inset-0 bg-primary/10 blur-2xl rounded" />
                  <Upload className="relative mx-auto h-16 w-16 text-primary/70" />
                </div>
                <div className="space-y-3">
                  <Typography variant="h3" className="text-foreground">
                    Drop PDF files here, or click to browse
                  </Typography>
                  <Typography variant="body-md" tone="muted" className="max-w-md mx-auto">
                    Only PDF files are supported. Upload up to 5 PDFs at once.
                  </Typography>
                </div>
              </div>
            </label>

            {/* File List - Single Card */}
            {files.length > 0 && (
              <Card variant="elevated" className="animate-fade-up animation-delay-400">
                <CardHeader className="flex flex-row items-center gap-3 space-y-0">
                  <Files className="h-5 w-5 text-primary" />
                  <Typography variant="h3">Uploaded Files ({files.length})</Typography>
                </CardHeader>

                {/* Progress Visualization - Shows when uploading/queued */}
                {(files.some((f) => f.status === "uploading" || f.status === "queued")) && (
                  <CardContent className="pt-0">
                    <div className="rounded border border-border/60 bg-surface/40 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <Typography variant="label" weight="strong">
                          Upload Progress
                        </Typography>
                        <Typography variant="body-sm" tone="muted">
                          {files.filter((f) => f.status === "uploading").length} uploading,{" "}
                          {files.filter((f) => f.status === "queued").length} queued
                        </Typography>
                      </div>
                      <div className="h-2 w-full rounded bg-surface-elevated overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-300"
                          style={{
                            width: `${(files.filter((f) => f.status === "processing" || f.status === "completed").length / files.length) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  </CardContent>
                )}

                <CardContent className="space-y-3">
                  {files.map((fileData, index) => (
                    <div
                      key={fileData.id}
                      className="flex items-center gap-4 rounded border border-border/50 bg-surface/40 p-4 transition-all duration-200 hover:border-border hover:bg-surface/60"
                    >
                      {fileData.jobId ? (
                        <JobStatusSubscriber
                          jobId={fileData.jobId}
                          onData={(data) => handleJobStatusUpdate(index, data)}
                          onError={(error) => handleJobStatusError(index, error)}
                        />
                      ) : null}

                      <div className="relative shrink-0">
                        <div className="absolute inset-0 bg-destructive/20 blur-md rounded" />
                        <FileText className="relative h-10 w-10 text-destructive" />
                      </div>

                      <div className="flex-1 min-w-0 space-y-1">
                        <Typography
                          variant="p"
                          weight="strong"
                          className="truncate"
                          title={fileData.file.name}
                        >
                          {fileData.file.name.length > MAX_DISPLAY_FILENAME_LENGTH
                            ? `${fileData.file.name.substring(0, MAX_DISPLAY_FILENAME_LENGTH - 3)}...`
                            : fileData.file.name}
                        </Typography>
                        <Typography variant="body-sm" tone="muted">
                          {((fileData.originalSize ?? fileData.file.size) / 1024 / 1024).toFixed(1)}{" "}
                          MB
                        </Typography>
                        <div className="flex items-center gap-2">
                          {getStatusBadge(fileData, index)}
                        </div>
                        {fileData.error && (
                          <Typography variant="body-xs" className="text-destructive">
                            {fileData.error}
                          </Typography>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        {fileData.jobId &&
                          (fileData.status === "processing" || fileData.status === "completed") && (
                            <Button
                              variant="default"
                              size="sm"
                              onClick={() => fileData.jobId && handleViewResults(fileData.jobId)}
                            >
                              <ExternalLink className="h-4 w-4" />
                              View Results
                            </Button>
                          )}

                        {(fileData.status === "pending" || fileData.status === "queued") && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => startSingleAnalysis(index)}
                            disabled={
                              fileData.isPlaceholder ||
                              (fileData.status === "queued" &&
                                queuedCount > 1 &&
                                index !== files.findIndex((f) => f.status === "queued"))
                            }
                          >
                            <Upload className="h-4 w-4" />
                            Start
                          </Button>
                        )}

                        {fileData.status === "error" && (
                          <>
                            {fileData.jobId && (
                              <Button
                                variant="default"
                                size="sm"
                                onClick={() => fileData.jobId && handleViewResults(fileData.jobId)}
                              >
                                <ExternalLink className="h-4 w-4" />
                                View Results
                              </Button>
                            )}
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => startSingleAnalysis(index)}
                            >
                              <X className="h-4 w-4" />
                              Retry
                            </Button>
                          </>
                        )}

                        {(fileData.status === "pending" || fileData.status === "queued") && (
                          <Button variant="ghost" size="sm" onClick={() => removeFile(index)}>
                            <X className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}

                  {files.some((f) => f.status === "pending") && (
                    <div className="pt-3 border-t border-border/30">
                      <Button
                        onClick={startAllAnalysis}
                        variant="default"
                        size="lg"
                        className="w-full"
                      >
                        <FolderSearch2 className="h-5 w-5" />
                        Start Analysis for All Files
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Help Section - Standalone */}
            <Alert className="border-border/60 bg-surface/40 animate-fade-up animation-delay-500">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 mt-0.5 shrink-0" />
                <div className="space-y-2">
                  <Typography variant="h4">
                    How it works
                  </Typography>
                  <Typography variant="body-md" tone="muted">
                    Upload clinical trial PDFs and our AI-powered system will automatically analyze
                    them against INSPECT-SR criteria including registration status and retraction
                    checks.
                  </Typography>
                </div>
              </div>
            </Alert>
          </div>
        </div>
      </main>
    </ProfileGuard>
  );
}

function JobStatusSubscriber({
  jobId,
  onData,
  onError,
}: {
  jobId: string;
  onData: (data: JobStatusResponse) => void;
  onError: (error: Error) => void;
}) {
  const { data, error } = useJobStatus(jobId, {
    enabled: Boolean(jobId),
    refetchInterval: 5000,
  });

  // Use refs to avoid triggering effects when callbacks change
  const onDataRef = useRef(onData);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onDataRef.current = onData;
    onErrorRef.current = onError;
  }, [onData, onError]);

  useEffect(() => {
    if (data) {
      onDataRef.current(data);
    }
  }, [data]);

  useEffect(() => {
    if (error) {
      onErrorRef.current(error);
    }
  }, [error]);

  return null;
}

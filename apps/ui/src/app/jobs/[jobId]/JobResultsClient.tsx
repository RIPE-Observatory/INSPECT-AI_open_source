"use client";

import { AppHeader } from "@/components/auth/app-header";
import { Button, Typography } from "@inspect/ui";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Bug, Loader, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  type InspectSRGetResponse,
  type InspectSRQuestion,
  type JobResults,
  type PDFViewerProps,
  useInspectSR,
  useJobStatus,
  useUpdateInspectSR,
} from "@inspect/api-client";

import { AssessmentProgressBar } from "./components/AssessmentProgressBar";
import { GuidanceModal, type GuidanceContent } from "./components/GuidanceModal";
import { BETA_QUESTION_IDS, calculateProgress, convertToChecklistData, getGuidanceKey, getCheckNumber } from "./utils/inspect-sr-utils";
import { checkHelpContent } from "@/app/checklist/data/checkHelpContent";
import ExportDropdown from "@/app/checklist/components/ExportDropdown";

import ReactPDFViewer from "@/components/ReactPDFViewer";
import AuthorHistoryTabContent from "./components/AuthorHistoryTabContent";
import EOCTabContent from "./components/EOCTabContent";
import { PublicationMetadataCard } from "./components/PublicationMetadataCard";
import RegistrationTabContent from "./components/RegistrationTabContent";
import RetractionTabContent from "./components/RetractionTabContent";
import SectionPicker, { type SectionPickerItem } from "./components/SectionPicker";
import { SectionNavigation } from "./components/SectionNavigation";
import { InspectSRInlineCheck } from "./components/inspect-sr-inline-check";
import {
  JOB_DETAIL_SECTION_LOOKUP,
  type JobDetailSectionConfig,
  type JobDetailSectionId,
  getEnabledSections,
} from "./section-config";
import { type StatusToken, getStatusIcon } from "./utils/shared";
import { buildSectionOutcomes, countStatuses } from "./utils/status";

type DetailSectionId = JobDetailSectionId;
type DetailSectionConfig = JobDetailSectionConfig;
type SectionId = "summary" | DetailSectionId;

const headerTokenBase =
  "flex items-center gap-2 rounded border border-border bg-background px-4 py-1 transition-colors duration-150";
const headerTokenInteractive =
  "group hover:border-foreground hover:bg-foreground hover:text-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background";

const PDFViewer = ({ jobId }: PDFViewerProps) => {
  const pdfUrl = `/api/internal/jobs/${jobId}/pdf`;

  return (
    <div className="h-full w-full overflow-auto bg-background">
      <ReactPDFViewer pdfUrl={pdfUrl} height="100%" />
    </div>
  );
};

interface JobResultsClientProps {
  jobId: string;
}

export default function JobResultsClient({ jobId }: JobResultsClientProps) {
  const queryClient = useQueryClient();
  const jobQuery = useJobStatus(jobId, {
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      // Stop polling on permanent errors (404, 403)
      if (query.state.error) {
        const error = query.state.error as Error & { status?: number; response?: { status?: number } };
        const status = error?.status || error?.response?.status;
        if (status === 404 || status === 403) {
          return false; // Stop polling
        }
      }
      // Continue polling every 5 seconds for other cases
      return 5000;
    },
    retry: (failureCount, error: Error & { status?: number; response?: { status?: number } }) => {
      // Don't retry on 404 or 403 - these are permanent failures
      const status = error?.status || error?.response?.status;
      if (status === 404 || status === 403) {
        return false;
      }
      // Retry up to 3 times for other errors
      return failureCount < 3;
    },
  });

  const jobData = jobQuery.data ?? null;
  const [showErrorToast, setShowErrorToast] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [selectedSection, setSelectedSection] = useState<SectionId>("summary");

  // Comment state lifted to parent - survives section switches
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({});
  const [interactedQuestions, setInteractedQuestions] = useState<Set<string>>(new Set());

  // Guidance modal state
  const [guidanceModalOpen, setGuidanceModalOpen] = useState(false);
  const [activeGuidance, setActiveGuidance] = useState<{
    checkNumber: string;
    content: GuidanceContent;
  } | null>(null);

  // Open guidance modal for a specific question
  const handleOpenGuidance = useCallback((questionId: string) => {
    const guidanceKey = getGuidanceKey(questionId);
    const checkNumber = getCheckNumber(questionId);

    if (guidanceKey && checkNumber && checkHelpContent[guidanceKey]) {
      setActiveGuidance({
        checkNumber,
        content: checkHelpContent[guidanceKey],
      });
      setGuidanceModalOpen(true);
    }
  }, []);

  const inspectSRFromJob = jobData?.results?.inspect_sr ?? null;

  const inspectSRInitialData = useMemo<InspectSRGetResponse | undefined>(() => {
    if (!inspectSRFromJob) return undefined;
    return {
      job_id: jobId,
      version: inspectSRFromJob.version ?? 0,
      updated_at: inspectSRFromJob.updated_at,
      progress: inspectSRFromJob.progress,
      data: inspectSRFromJob.data,
    };
  }, [inspectSRFromJob, jobId]);

  const inspectSRQuery = useInspectSR(jobId, {
    enabled: Boolean(jobId),
    initialData: inspectSRInitialData,
  });

  const inspectSRData = inspectSRQuery.data ?? inspectSRInitialData ?? null;

  const inspectSRRecords = useMemo(() => {
    const records = inspectSRData?.data ?? [];
    return new Map(records.map((record) => [record.question_id, record]));
  }, [inspectSRData]);

  // Comment draft helpers - get draft for a question, fallback to server value
  const getCommentDraft = useCallback((questionId: string) => {
    // If user has edited this question, return their draft
    if (questionId in commentDrafts) {
      return commentDrafts[questionId];
    }
    // Otherwise return server value
    return inspectSRRecords.get(questionId)?.comment ?? "";
  }, [commentDrafts, inspectSRRecords]);

  // Update draft for a question
  const updateCommentDraft = useCallback((questionId: string, value: string) => {
    setCommentDrafts(prev => ({ ...prev, [questionId]: value }));
  }, []);

  // Mark a question as interacted (user started typing)
  const markAsInteracted = useCallback((questionId: string) => {
    setInteractedQuestions(prev => new Set(prev).add(questionId));
  }, []);

  // Check if a question has been interacted with
  const isQuestionInteracted = useCallback((questionId: string) => {
    return interactedQuestions.has(questionId);
  }, [interactedQuestions]);

  // Check if any question has unsaved changes (useful for future navigation guards/warnings)
  const _hasUnsavedChanges = useMemo(() => {
    return Object.entries(commentDrafts).some(([qid, draft]) => {
      const serverComment = inspectSRRecords.get(qid)?.comment ?? "";
      return draft !== serverComment;
    });
  }, [commentDrafts, inspectSRRecords]);
  void _hasUnsavedChanges; // Intentionally unused - kept for future use

  // Calculate progress for the progress bar
  const assessmentProgress = useMemo(() => {
    const records = inspectSRData?.data ?? [];
    return calculateProgress(records);
  }, [inspectSRData]);

  // Convert to checklist data for export
  const checklistDataForExport = useMemo(() => {
    const records = inspectSRData?.data ?? [];
    return convertToChecklistData(records);
  }, [inspectSRData]);

  const computeInspectSRProgress = useCallback(
    (records: InspectSRQuestion[]) => {
      const total = inspectSRData?.progress?.total ?? records.length;
      const completed = records.reduce((count, record) => ((record.automated_judgement || record.reviewed_judgement) ? count + 1 : count), 0);
      const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
      return { total, completed, percent };
    },
    [inspectSRData?.progress?.total],
  );

  const inspectSRMutation = useUpdateInspectSR(jobId, {
    onSuccess: (response, variables) => {
      const updatedRecords = variables.data;
      queryClient.setQueryData<InspectSRGetResponse>(["jobs", jobId, "inspect-sr"], {
        job_id: jobId,
        version: response.version,
        updated_at: response.updated_at,
        data: updatedRecords,
        progress: computeInspectSRProgress(updatedRecords),
      });
      queryClient.invalidateQueries({ queryKey: ["jobs", jobId, "status"] });

      // Clear drafts for saved questions - they now match server state
      const savedQuestionIds = updatedRecords.map(r => r.question_id);
      setCommentDrafts(prev => {
        const next = { ...prev };
        for (const qid of savedQuestionIds) {
          delete next[qid];
        }
        return next;
      });
    },
    onError: () => {
      inspectSRQuery.refetch();
    },
  });

  const inspectSRMutationError =
    inspectSRMutation.error instanceof Error
      ? inspectSRMutation.error.message
      : inspectSRMutation.error
        ? String(inspectSRMutation.error)
        : null;

  const isInspectSRLoading = inspectSRQuery.isLoading || inspectSRQuery.isFetching;
  const isInspectSRMutating = inspectSRMutation.isPending;

  // Debounce timer to prevent rapid-fire API calls
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleInspectSRUpdate = useCallback(
    (
      sectionConfig: DetailSectionConfig,
      updates: Partial<Pick<InspectSRQuestion, "reviewed_judgement" | "comment">>,
    ) => {
      if (!inspectSRData) return;

      const currentRecords = inspectSRData.data ?? [];

      // Create a map of existing records
      const recordsMap = new Map(currentRecords.map((r) => [r.question_id, r]));

      // Update or add the target record
      const existingRecord = recordsMap.get(sectionConfig.questionId);
      let hasChange = false;

      if (existingRecord) {
        const updatedRecord = { ...existingRecord };

        if (updates.reviewed_judgement !== undefined && updates.reviewed_judgement !== existingRecord.reviewed_judgement) {
          updatedRecord.reviewed_judgement = updates.reviewed_judgement;
          hasChange = true;
        }

        if (updates.comment !== undefined && updates.comment !== existingRecord.comment) {
          updatedRecord.comment = updates.comment;
          hasChange = true;
        }

        if (hasChange) {
          recordsMap.set(sectionConfig.questionId, updatedRecord);
        }
      } else {
        recordsMap.set(sectionConfig.questionId, {
          question_id: sectionConfig.questionId,
          label: sectionConfig.heading,
          reviewed_judgement: updates.reviewed_judgement ?? null,
          automated_judgement: null,
          comment: updates.comment ?? "",
        });
        hasChange = true;
      }

      if (!hasChange) return;

      // Use beta question IDs (5 questions) for the payload
      const completeRecords = BETA_QUESTION_IDS.map(
        (qid) =>
          recordsMap.get(qid) || {
            question_id: qid,
            label: "", // Backend will fill this
            reviewed_judgement: null,
            automated_judgement: null,
            comment: "",
          },
      );

      // Clear existing debounce timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Debounce the API call to prevent rapid-fire requests (150ms delay)
      debounceTimerRef.current = setTimeout(() => {
        inspectSRMutation.mutate({
          data: completeRecords,
          version: inspectSRData.version,
        });
      }, 150);
    },
    [inspectSRData, inspectSRMutation],
  );

  const renderInspectSRCheck = useCallback(
    (sectionConfig: DetailSectionConfig, status?: StatusToken) => {
      const record = inspectSRRecords.get(sectionConfig.questionId);
      // Determine if this is a judgement-type question (OVERALL or domain overalls)
      const isJudgementQuestion = sectionConfig.questionId === "OVERALL" ||
                                   sectionConfig.questionId.endsWith(".overall");
      // Check if guidance is available for this question
      const hasGuidance = getGuidanceKey(sectionConfig.questionId) !== null;

      return (
        <InspectSRInlineCheck
          // NOTE: key prop removed - state now lifted to parent, survives section switches
          heading={sectionConfig.heading}
          helperLabel={sectionConfig.pickerDescription}
          record={record}
          status={status}
          isLoading={isInspectSRLoading && !record}
          isSaving={isInspectSRMutating}
          errorMessage={inspectSRMutationError}
          questionType={isJudgementQuestion ? "judgement" : "check"}
          questionId={sectionConfig.questionId}
          hasGuidance={hasGuidance}
          // Controlled comment state - survives section switches
          commentDraft={getCommentDraft(sectionConfig.questionId)}
          onCommentChange={(value) => updateCommentDraft(sectionConfig.questionId, value)}
          hasInteracted={isQuestionInteracted(sectionConfig.questionId)}
          onInteractionStart={() => markAsInteracted(sectionConfig.questionId)}
          onAnswerChange={(value) => handleInspectSRUpdate(sectionConfig, { reviewed_judgement: value })}
          onClearAnswer={() => handleInspectSRUpdate(sectionConfig, { reviewed_judgement: null })}
          onCommentSave={(value) => handleInspectSRUpdate(sectionConfig, { comment: value })}
          onOpenGuidance={() => handleOpenGuidance(sectionConfig.questionId)}
        />
      );
    },
    [
      handleInspectSRUpdate,
      handleOpenGuidance,
      inspectSRMutationError,
      inspectSRRecords,
      isInspectSRLoading,
      isInspectSRMutating,
      getCommentDraft,
      updateCommentDraft,
      isQuestionInteracted,
      markAsInteracted,
    ],
  );

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (jobData) {
      setHasLoadedOnce(true);
      setShowErrorToast(false);
    }
  }, [jobData]);

  useEffect(() => {
    if (jobQuery.error && hasLoadedOnce) {
      setShowErrorToast(true);
    } else if (!jobQuery.error) {
      setShowErrorToast(false);
    }
  }, [jobQuery.error, hasLoadedOnce]);

  // Navigation sections - compute early so hooks are stable
  // This list is static (summary + enabled sections) regardless of data loading state
  const navigationSectionIds = useMemo(() => {
    const enabled = getEnabledSections();
    return ["summary", ...enabled.map((s) => s.id)] as SectionId[];
  }, []);

  const currentSectionIndex = navigationSectionIds.indexOf(selectedSection);

  // Handle section change with auto-save of pending comments
  const handleSectionChange = useCallback((newSectionId: SectionId) => {
    // If current section has unsaved comment, auto-save it before navigating
    if (selectedSection !== "summary") {
      const currentConfig = JOB_DETAIL_SECTION_LOOKUP[selectedSection as DetailSectionId];
      if (currentConfig) {
        const currentDraft = commentDrafts[currentConfig.questionId];
        const serverComment = inspectSRRecords.get(currentConfig.questionId)?.comment ?? "";

        // Only save if user has made changes and they differ from server
        if (currentDraft !== undefined && currentDraft !== serverComment) {
          // Fire-and-forget save - mutation will complete in background
          handleInspectSRUpdate(currentConfig, { comment: currentDraft });
        }
      }
    }

    setSelectedSection(newSectionId);
  }, [selectedSection, commentDrafts, inspectSRRecords, handleInspectSRUpdate]);

  const goToPreviousSection = useCallback(() => {
    if (currentSectionIndex > 0) {
      handleSectionChange(navigationSectionIds[currentSectionIndex - 1]);
    }
  }, [currentSectionIndex, navigationSectionIds, handleSectionChange]);

  const goToNextSection = useCallback(() => {
    if (currentSectionIndex < navigationSectionIds.length - 1) {
      handleSectionChange(navigationSectionIds[currentSectionIndex + 1]);
    }
  }, [currentSectionIndex, navigationSectionIds, handleSectionChange]);

  const error = jobQuery.error as Error & { status?: number; response?: { status?: number } } | null;
  const errorStatus = error?.status || error?.response?.status;
  const errorMessage = error?.message ?? null;

  // Determine user-friendly error message based on status code
  const getErrorDisplay = () => {
    if (errorStatus === 404) {
      return {
        title: "Job Not Found",
        message: "This job doesn't exist or you don't have permission to view it. This may happen if you're signed in with a different account than the one that created this job.",
        suggestion: "Try signing in with the account that uploaded this document, or upload a new file.",
      };
    }
    if (errorStatus === 403) {
      return {
        title: "Access Denied",
        message: "You don't have permission to view this job. Make sure you're signed in with the correct account.",
        suggestion: "Sign in with the account that created this job.",
      };
    }
    return {
      title: "Error Loading Job",
      message: errorMessage || "An unexpected error occurred while loading this job.",
      suggestion: "Please try again or upload a new file.",
    };
  };

  if (errorMessage && !jobData) {
    const errorDisplay = getErrorDisplay();
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="flex flex-col items-center p-8 border border-destructive/30 rounded bg-background max-w-lg text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-destructive" />
          <Typography variant="h2" weight="strong" className="text-destructive">{errorDisplay.title}</Typography>
          <Typography variant="body-sm" className="text-foreground">{errorDisplay.message}</Typography>
          <Typography variant="body-sm" tone="muted" className="italic">{errorDisplay.suggestion}</Typography>
          <div className="flex gap-3 mt-6">
            <Link href="/analyze">
              <Button variant="default">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Upload New File
              </Button>
            </Link>
            <Link href="/">
              <Button variant="outline">
                Go Home
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!jobData) {
    if (jobQuery.isPending) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-background">
          <div className="flex flex-col items-center p-8 border border-border rounded bg-background max-w-md text-center">
            <Loader className="w-8 h-8 text-primary mb-4 animate-spin" />
            <Typography variant="h4" weight="strong" className="text-foreground mb-2">Loading Assessments...</Typography>
            <Typography variant="body-sm" tone="muted">
              Please wait while we retrieve the latest assessments.
            </Typography>
          </div>
        </div>
      );
    }

    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="flex flex-col items-center p-8 border border-warning/30 rounded bg-background max-w-md text-center">
          <AlertTriangle className="w-8 h-8 text-warning mb-4" />
          <Typography variant="h2" weight="strong" className="text-warning mb-2">Job Data Not Available</Typography>
          <Typography variant="body-sm" className="text-warning">
            Could not retrieve initial results. Please try again later or check the job ID.
          </Typography>
          <Link href="/analyze" className="mt-6">
            <Button
              variant="outline"
              className="transition-colors duration-150 hover:bg-background hover:text-foreground hover:border-border"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Upload
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  if ((jobData.status === "COMPLETED" || jobData.status === "FAILED") && !jobData.results) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="flex flex-col items-center p-8 border border-warning/30 rounded bg-background max-w-md text-center">
          <AlertTriangle className="w-8 h-8 text-warning mb-4" />
          <Typography variant="h2" weight="strong" className="text-warning mb-2">No Results Available</Typography>
          <Typography variant="body-sm" className="text-warning">
            The job &apos;{jobData.status.toLowerCase()}&apos; but no results are available to
            display.
          </Typography>
          {jobData.error_message && (
            <Typography variant="body-sm" tone="muted" className="text-destructive mt-2">
              Error: {jobData.error_message}
            </Typography>
          )}
          <Link href="/analyze" className="mt-6">
            <Button
              variant="outline"
              className="transition-colors duration-150 hover:bg-background hover:text-foreground hover:border-border"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Upload
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const isJobProcessing = jobData.status === "PENDING" || jobData.status === "RUNNING";
  const jobResults: JobResults | null = jobData.results;

  const sectionOutcomes = buildSectionOutcomes(jobResults, jobData.status);

  const counts = countStatuses(sectionOutcomes);
  const needsAttentionCount = counts.concern + counts.attention;
  const hasPendingSections = counts.pending > 0;

  const SectionSummaryRow = ({
    label,
    status,
    summary,
  }: {
    label: string;
    status: StatusToken;
    summary: string;
  }) => (
    <div className="flex items-center gap-2 p-2 rounded">
      <div className="flex-shrink-0">{getStatusIcon(status, "h-4 w-4")}</div>
      <Typography variant="body-md" weight="strong" as="span" className="text-foreground min-w-[160px]">{label}</Typography>
      <Typography variant="body-sm" tone="muted" as="span" className="flex-1">{summary}</Typography>
    </div>
  );

  const statusLookup = new Map(sectionOutcomes.map((section) => [section.id, section.status]));
  const enabledSections = getEnabledSections();
  const sectionPickerItems: SectionPickerItem[] = [
    {
      id: "summary",
      label: "Summary",
      description: "Overall assessment",
    },
    ...enabledSections.map((section) => ({
      id: section.id,
      label: section.pickerLabel,
      description: section.pickerDescription,
      status: statusLookup.get(section.id) ?? "unknown",
    })),
  ];

  const renderSummary = () => (
    <div className="space-y-6">
      <div className="space-y-2">
        <Typography variant="h4">Summary</Typography>
      </div>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded border border-success bg-background p-4 text-center">
            <Typography variant="h2" weight="strong" className="text-success mb-1">{counts.ok}</Typography>
            <Typography variant="body-sm" weight="strong" className="text-success">No Concerns</Typography>
          </div>
          <div className="rounded border border-destructive bg-background p-4 text-center">
            <Typography variant="h2" weight="strong" className="text-destructive mb-1">{needsAttentionCount}</Typography>
            <Typography variant="body-sm" weight="strong" className="text-destructive">Some Concerns</Typography>
          </div>
        </div>
        {hasPendingSections && (
          <div className="p-3 rounded border border-border bg-background flex items-center justify-center gap-2">
            {getStatusIcon("pending", "h-4 w-4")}
            <Typography variant="body-sm" as="span" className="text-info">
              Some checks are still running. Results will update shortly.
            </Typography>
          </div>
        )}
      </div>

      <PublicationMetadataCard
        check4Data={jobResults?.checks?.grobid_primary_metadata?.payload}
        isJobRunning={isJobProcessing}
        jobData={jobData}
      />

      <div className="space-y-3">
        {sectionOutcomes.map((section) => (
          <div
            key={section.id}
            className="p-4 rounded border border-border bg-background shadow-sm space-y-2"
          >
            {section.id === "retraction" ? (
              <div className="space-y-1">
                <div className="flex items-center gap-2 p-2 rounded">
                  <div className="flex-shrink-0">{getStatusIcon(section.status, "h-4 w-4")}</div>
                  <Typography variant="body-md" weight="strong" as="span" className="text-foreground min-w-[160px]">
                    {section.label}
                  </Typography>
                </div>
                <div className="flex items-center gap-2 p-2 rounded pl-8">
                  <Typography variant="body-sm" tone="muted" as="span" className="min-w-[160px]">
                    Main Title Retracted:
                  </Typography>
                  <Typography variant="body-sm" weight="strong" as="span" className="text-foreground">{section.finding}</Typography>
                </div>
                <div className="flex items-center gap-2 p-2 rounded pl-8">
                  <Typography variant="body-sm" tone="muted" as="span" className="min-w-[160px]">
                    References retracted:
                  </Typography>
                  <Typography variant="body-sm" weight="strong" as="span" className="text-foreground">{section.detail}</Typography>
                </div>
              </div>
            ) : section.id === "eoc" ? (
              <div className="space-y-1">
                <div className="flex items-center gap-2 p-2 rounded">
                  <div className="flex-shrink-0">{getStatusIcon(section.status, "h-4 w-4")}</div>
                  <Typography variant="body-md" weight="strong" as="span" className="text-foreground min-w-[160px]">
                    {section.label}
                  </Typography>
                </div>
                <div className="flex items-center gap-2 p-2 rounded pl-8">
                  <Typography variant="body-sm" tone="muted" as="span" className="min-w-[160px]">
                    Number of notices:
                  </Typography>
                  <Typography variant="body-sm" weight="strong" as="span" className="text-foreground">{section.finding}</Typography>
                </div>
                <div className="flex items-center gap-2 p-2 rounded pl-8">
                  <Typography variant="body-sm" tone="muted" as="span" className="min-w-[160px]">
                    Number of comments:
                  </Typography>
                  <Typography variant="body-sm" weight="strong" as="span" className="text-foreground">{section.detail}</Typography>
                </div>
              </div>
            ) : section.id === "author_history" ? (
              <div className="space-y-1">
                <div className="flex items-center gap-2 p-2 rounded">
                  <div className="flex-shrink-0">{getStatusIcon(section.status, "h-4 w-4")}</div>
                  <Typography variant="body-md" weight="strong" as="span" className="text-foreground min-w-[160px]">
                    {section.label}
                  </Typography>
                </div>
                <div className="flex items-center gap-2 p-2 rounded pl-8">
                  <Typography variant="body-sm" tone="muted" as="span" className="min-w-[160px]">
                    Mentions in Retraction Watch:
                  </Typography>
                  <Typography variant="body-sm" weight="strong" as="span" className="text-foreground">{section.finding}</Typography>
                </div>
              </div>
            ) : section.id === "registration" ? (
              <div className="space-y-1">
                <div className="flex items-center gap-2 p-2 rounded">
                  <div className="flex-shrink-0">{getStatusIcon(section.status, "h-4 w-4")}</div>
                  <Typography variant="body-md" weight="strong" as="span" className="text-foreground min-w-[160px]">
                    {section.label}
                  </Typography>
                </div>
                <div className="flex items-center gap-2 p-2 rounded pl-8">
                  <Typography variant="body-sm" tone="muted" as="span" className="min-w-[160px]">
                    Extracted Trial ID:
                  </Typography>
                  <Typography variant="body-sm" weight="strong" as="span" className="text-foreground">{section.finding}</Typography>
                </div>
                <div className="flex items-center gap-2 p-2 rounded pl-8">
                  <Typography variant="body-sm" tone="muted" as="span" className="min-w-[160px]">
                    Registration Assessment:
                  </Typography>
                  <Typography variant="body-sm" weight="strong" as="span" className="text-foreground">{section.detail}</Typography>
                </div>
              </div>
            ) : (
              <>
                <SectionSummaryRow
                  label={section.label}
                  status={section.status}
                  summary={section.finding}
                />
                {section.detail && (
                  <Typography variant="body-xs" tone="muted" className="opacity-80">{section.detail}</Typography>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );

  const renderDetail = (sectionId: DetailSectionId) => {
    const sectionConfig = JOB_DETAIL_SECTION_LOOKUP[sectionId];
    if (!sectionConfig) return null;

    const sectionStatus = sectionOutcomes.find((s) => s.id === sectionConfig.id)?.status;
    const inlineCheck = renderInspectSRCheck(sectionConfig, sectionStatus);

    if (!jobResults) {
      return (
        <div className="space-y-4">
          <div className="rounded border border-dashed border-border bg-background p-4 text-sm text-muted-foreground">
            Detailed data is not available yet. Please wait for processing to complete.
          </div>
          {inlineCheck}
        </div>
      );
    }

    switch (sectionId) {
      case "registration":
        return (
          <div className="space-y-6">
            <RegistrationTabContent
              title={sectionConfig.heading}
              results={jobResults}
              jobStatus={jobData.status}
            />
            {inlineCheck}
          </div>
        );
      case "retraction":
        return (
          <div className="space-y-6">
            <RetractionTabContent
              title={sectionConfig.heading}
              results={jobResults}
              jobStatus={jobData.status}
            />
            {inlineCheck}
          </div>
        );
      case "eoc":
        return (
          <div className="space-y-6">
            <EOCTabContent
              title={sectionConfig.heading}
              results={jobResults}
              jobStatus={jobData.status}
            />
            {inlineCheck}
          </div>
        );
      case "author_history":
        return (
          <div className="space-y-6">
            <AuthorHistoryTabContent
              title={sectionConfig.heading}
              results={jobResults}
              jobStatus={jobData.status}
            />
            {inlineCheck}
          </div>
        );
      case "overall_assessment": {
        const overallStatus = sectionOutcomes.find((s) => s.id === "overall_assessment")?.status;
        return (
          <div className="space-y-6">
            <div className="space-y-4">
              <Typography variant="h4">{sectionConfig.heading}</Typography>
            </div>
            {renderInspectSRCheck(sectionConfig, overallStatus)}
          </div>
        );
      }
      default:
        return null;
    }
  };

  const jobStatusDisplay = jobData.status ? jobData.status.replace(/_/g, " ") : "Loading status...";

  const ErrorToast = () => {
    if (!showErrorToast || !errorMessage) return null;
    return (
      <div className="fixed bottom-0 right-0 m-8 p-4 bg-background border border-destructive/40 text-destructive rounded shadow-lg z-50 flex items-center justify-between">
        <Typography variant="body-sm" as="span">Error during update: {errorMessage}</Typography>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowErrorToast(false)}
          className="ml-4 text-destructive hover:bg-background"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  };

  // Get study title for export (from GROBID metadata if available)
  const studyTitle = jobResults?.checks?.grobid_primary_metadata?.payload?.main_title ?? undefined;

  return (
    <div className="dark">
      <AppHeader
        title="Assessments"
        leftContent={
          <div
            className={`${headerTokenBase} ${
              jobData.status === "COMPLETED"
                ? "border-success/40"
                : jobData.status === "FAILED"
                  ? "border-destructive/40"
                  : "border-info/40"
            }`}
          >
            <Typography variant="body-sm" tone="muted" as="span">Status:</Typography>
            <Typography
              variant="body-sm"
              weight="strong"
              as="span"
              className={`${
                jobData.status === "COMPLETED"
                  ? "text-success"
                  : jobData.status === "FAILED"
                    ? "text-destructive"
                    : "text-info"
              }`}
            >
              {jobStatusDisplay}
            </Typography>
            {(jobData.status === "PENDING" || jobData.status === "RUNNING") &&
              getStatusIcon(jobData.status || "LOADING")}
          </div>
        }
        centerContent={
          <div className={headerTokenBase}>
            <Typography variant="body-sm" tone="muted" as="span">Job ID:</Typography>
            <Typography variant="body-sm" weight="strong" as="span" className="text-foreground font-mono">{jobId}</Typography>
          </div>
        }
        rightContent={
          <>
            {/* Progress bar - only show when job is completed */}
            {jobData.status === "COMPLETED" && (
              <div className={headerTokenBase}>
                <AssessmentProgressBar
                  percent={assessmentProgress.percent}
                  answeredChecks={assessmentProgress.answeredChecks}
                  totalChecks={assessmentProgress.totalChecks}
                  overallAnswered={assessmentProgress.overallAnswered}
                />
              </div>
            )}

            {/* Export dropdown - only show when job is completed */}
            {jobData.status === "COMPLETED" && (
              <ExportDropdown
                checklistData={checklistDataForExport}
                studyTitle={studyTitle}
                triggerClassName={`${headerTokenBase} ${headerTokenInteractive}`}
              />
            )}

            <a
              href="#tally-open=wMqLW8&tally-layout=modal&tally-width=400&tally-emoji-text=👋&tally-emoji-animation=wave&tally-auto-close=3000"
              className={`${headerTokenBase} ${headerTokenInteractive}`}
            >
              <Bug className="h-3.5 w-3.5 text-foreground transition-colors duration-150 group-hover:text-background" />
              <Typography variant="body-sm" weight="strong" as="span" className="text-foreground group-hover:text-background">
                Report Issue
              </Typography>
            </a>
          </>
        }
      />
      <ErrorToast />
      <main className="h-[calc(100vh-60px)] bg-background relative overflow-hidden">
        <div className="absolute inset-0 -z-10" />

        <div className="flex h-full">
          <div className="w-1/2 h-full border-r border-border/30 animate-content-reveal animate-delay-100">
            {jobId !== "undefined" && jobData.file_path ? (
              <PDFViewer jobId={jobId} />
            ) : (
              <div className="flex items-center justify-center h-full p-4 text-center">
                <Typography variant="body-sm" tone="muted">
                  {jobId === "undefined"
                    ? "Cannot load PDF due to invalid Job ID."
                    : jobData.status === "COMPLETED" || jobData.status === "FAILED"
                      ? "PDF not available for this job."
                      : jobData
                        ? "PDF will load once job processing provides a file path..."
                        : "Loading PDF information..."}
                </Typography>
              </div>
            )}
          </div>

          <div className="w-1/2 flex flex-col animate-content-reveal animate-delay-150">
            {/* Scrollable content area */}
            <div className="flex-1 p-6 overflow-auto">
              <div className="space-y-6">
                <div className="w-full">
                  <SectionPicker
                    items={sectionPickerItems}
                    value={selectedSection}
                    onValueChange={(id) => handleSectionChange(id as SectionId)}
                  />
                </div>

                {selectedSection === "summary"
                  ? renderSummary()
                  : renderDetail(selectedSection as DetailSectionId)}
              </div>
            </div>

            {/* Section Navigation - fixed at bottom */}
            <SectionNavigation
              currentIndex={currentSectionIndex}
              totalSections={navigationSectionIds.length}
              onPrevious={goToPreviousSection}
              onNext={goToNextSection}
              isSaving={isInspectSRMutating}
            />
          </div>
        </div>
      </main>

      {/* Guidance Modal */}
      {activeGuidance && (
        <GuidanceModal
          isOpen={guidanceModalOpen}
          onClose={() => setGuidanceModalOpen(false)}
          checkNumber={activeGuidance.checkNumber}
          content={activeGuidance.content}
        />
      )}
    </div>
  );
}

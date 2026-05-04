import type { JobResults } from "@inspect/api-client";
import { getEnabledSections } from "../section-config";
import type { StatusToken } from "./shared";

export type SectionId =
  | "summary"
  | "registration"
  | "retraction"
  | "eoc"
  | "author_history"
  | "overall_assessment";

export interface SectionOutcome {
  id: Exclude<SectionId, "summary">;
  label: string;
  status: StatusToken;
  finding: string;
  detail?: string;
}

const DEFAULT_LABELS: Record<SectionOutcome["id"], string> = {
  retraction: "Q1.1 Retraction",
  eoc: "Q1.2 Post-publication notice",
  author_history: "Q1.3 Author concern history",
  registration: "Q2.2 Registration timing",
  overall_assessment: "Overall Study Judgement",
};

const isJobRunning = (jobStatus?: string): boolean =>
  jobStatus === "PENDING" || jobStatus === "RUNNING";

const normalizeStatus = (status: StatusToken | undefined | null): StatusToken =>
  status ?? "unknown";

const registrationOutcome = (
  results: JobResults | null | undefined,
  jobStatus?: string,
): SectionOutcome => {
  const trial = results?.checks?.trial_llm_extraction?.payload;
  const registry = results?.checks?.registry_crosscheck?.payload;
  const timeline = results?.checks?.timeline_consistency?.payload;
  const prospective = results?.checks?.prospective_registration_analysis?.payload;

  const running = isJobRunning(jobStatus);

  if (!trial && !registry && !timeline && !prospective) {
    return {
      id: "registration",
      label: DEFAULT_LABELS.registration,
      status: running ? "pending" : "attention",
      finding: running
        ? "Registration checks are still running."
        : "Registration data was not returned for this job.",
    };
  }

  const registryError = registry?.error_message || registry?.lookup_results?.error_message;
  if (registryError) {
    return {
      id: "registration",
      label: DEFAULT_LABELS.registration,
      status: "attention",
      finding: "Registry lookup failed.",
      detail: registryError,
    };
  }

  const trialId = trial?.trial_id;
  const isProspective = prospective?.is_prospective;

  // Determine assessment text
  let assessmentText = "Not assessed";
  if (isProspective === true) {
    assessmentText = "Prospective";
  } else if (isProspective === false) {
    assessmentText = "Retrospective";
  }

  // No trial ID OR retrospective → concern
  if (!trialId || isProspective === false) {
    return {
      id: "registration",
      label: DEFAULT_LABELS.registration,
      status: "concern",
      finding: trialId || "Not found",
      detail: assessmentText,
    };
  }

  // Trial ID exists AND prospective → ok
  if (trialId && isProspective === true) {
    return {
      id: "registration",
      label: DEFAULT_LABELS.registration,
      status: "ok",
      finding: trialId,
      detail: assessmentText,
    };
  }

  if (running) {
    return {
      id: "registration",
      label: DEFAULT_LABELS.registration,
      status: "pending",
      finding: "Registration checks are processing.",
    };
  }

  return {
    id: "registration",
    label: DEFAULT_LABELS.registration,
    status: "unknown",
    finding: trialId || "Not found",
    detail: assessmentText,
  };
};

const retractionOutcome = (
  results: JobResults | null | undefined,
  jobStatus?: string,
): SectionOutcome => {
  const retraction = results?.checks?.retraction_detection?.payload;
  const grobidPrimary = results?.checks?.grobid_primary_metadata?.payload;
  const grobidReferences = results?.checks?.grobid_reference_metadata?.payload;
  const running = isJobRunning(jobStatus);

  if (!retraction && !grobidPrimary && !grobidReferences) {
    return {
      id: "retraction",
      label: DEFAULT_LABELS.retraction,
      status: running ? "pending" : "attention",
      finding: running
        ? "Retraction checks are still running."
        : "Retraction Watch data was not returned for this job.",
    };
  }

  const grobidStatus = grobidPrimary?.status?.toUpperCase() ?? "";
  if (grobidStatus.includes("FAILED")) {
    return {
      id: "retraction",
      label: DEFAULT_LABELS.retraction,
      status: "attention",
      finding: "Primary DOI extraction failed.",
      detail: grobidPrimary?.comment,
    };
  }

  const mainResult = retraction?.main_article_result;
  const referenceResults = retraction?.reference_results ?? [];
  const flaggedReferences = referenceResults.filter((ref) => ref.found === true);

  // Main paper retracted → always concern (regardless of references)
  if (mainResult?.found === true) {
    return {
      id: "retraction",
      label: DEFAULT_LABELS.retraction,
      status: "concern",
      finding: "Yes",
      detail: `${flaggedReferences.length} reference${flaggedReferences.length !== 1 ? "s" : ""} retracted`,
    };
  }

  // Main paper NOT retracted BUT references retracted → attention
  if (mainResult?.found === false && flaggedReferences.length > 0) {
    return {
      id: "retraction",
      label: DEFAULT_LABELS.retraction,
      status: "attention",
      finding: "No",
      detail: `${flaggedReferences.length} reference${flaggedReferences.length !== 1 ? "s" : ""} retracted`,
    };
  }

  // Main paper NOT retracted AND no references retracted → ok
  if (mainResult?.found === false && flaggedReferences.length === 0) {
    return {
      id: "retraction",
      label: DEFAULT_LABELS.retraction,
      status: "ok",
      finding: "No",
      detail: "0 references retracted",
    };
  }

  if (running) {
    return {
      id: "retraction",
      label: DEFAULT_LABELS.retraction,
      status: "pending",
      finding: "Retraction checks are processing.",
    };
  }

  return {
    id: "retraction",
    label: DEFAULT_LABELS.retraction,
    status: "unknown",
    finding: "Retraction outcome is unavailable.",
  };
};

const eocOutcome = (results: JobResults | null | undefined, jobStatus?: string): SectionOutcome => {
  const eocData = results?.checks?.eoc_correction_detection;
  const pubpeerData = results?.checks?.pubpeer_signal_analysis?.payload;
  const running = isJobRunning(jobStatus);

  if (!eocData && !pubpeerData) {
    return {
      id: "eoc",
      label: DEFAULT_LABELS.eoc,
      status: running ? "pending" : "attention",
      finding: running
        ? "Post-publication checks are still running."
        : "Post-publication checks were not executed.",
    };
  }

  // Check for errors
  const eocError =
    eocData?.status === "failed" || eocData?.status === "error" || eocData?.error_message;
  const pubpeerError = pubpeerData?.status === "FAILED" || pubpeerData?.error_message;

  if (eocError || pubpeerError) {
    return {
      id: "eoc",
      label: DEFAULT_LABELS.eoc,
      status: "attention",
      finding: "Analysis failed.",
      detail: eocData?.error_message || pubpeerData?.error_message,
    };
  }

  // Get counts
  const eocNotices = eocData?.payload?.main_article_result?.notices ?? [];
  const pubpeerComments = pubpeerData?.main_paper_result?.scraped_comments?.comments ?? [];
  const totalConcerns = eocNotices.length + pubpeerComments.length;

  // Any concerns found → concern
  if (totalConcerns > 0) {
    return {
      id: "eoc",
      label: DEFAULT_LABELS.eoc,
      status: "concern",
      finding: `${eocNotices.length}`,
      detail: `${pubpeerComments.length}`,
    };
  }

  // No concerns found → ok
  if (eocData || pubpeerData) {
    return {
      id: "eoc",
      label: DEFAULT_LABELS.eoc,
      status: "ok",
      finding: "0",
      detail: "0",
    };
  }

  if (running) {
    return {
      id: "eoc",
      label: DEFAULT_LABELS.eoc,
      status: "pending",
      finding: "Post-publication checks are processing.",
    };
  }

  return {
    id: "eoc",
    label: DEFAULT_LABELS.eoc,
    status: "unknown",
    finding: "Post-publication outcome is unavailable.",
  };
};

const authorHistoryOutcome = (
  results: JobResults | null | undefined,
  jobStatus?: string,
): SectionOutcome => {
  const authorHistory = results?.checks?.author_retraction_history;
  const running = isJobRunning(jobStatus);

  if (!authorHistory) {
    return {
      id: "author_history",
      label: DEFAULT_LABELS.author_history,
      status: running ? "pending" : "attention",
      finding: running
        ? "Author history check is still running."
        : "Author history check was not executed.",
    };
  }

  const statusLower = authorHistory.status?.toLowerCase() ?? "";
  const failureMessage = authorHistory.error_message;

  if (statusLower === "failed" || statusLower === "error" || failureMessage) {
    return {
      id: "author_history",
      label: DEFAULT_LABELS.author_history,
      status: "attention",
      finding: "Author history analysis failed.",
      detail: failureMessage ?? undefined,
    };
  }

  const summary = authorHistory.payload?.summary;
  const authorsWithRetractions = summary?.authors_with_retractions ?? 0;
  const totalRetractions = summary?.total_retractions_found ?? 0;

  // Any authors with retractions → concern
  if (authorsWithRetractions > 0) {
    return {
      id: "author_history",
      label: DEFAULT_LABELS.author_history,
      status: "concern",
      finding: `${totalRetractions}`,
      detail: undefined,
    };
  }

  // No retractions found → ok
  if (statusLower === "ok" || authorsWithRetractions === 0) {
    return {
      id: "author_history",
      label: DEFAULT_LABELS.author_history,
      status: "ok",
      finding: "0",
      detail: undefined,
    };
  }

  if (running) {
    return {
      id: "author_history",
      label: DEFAULT_LABELS.author_history,
      status: "pending",
      finding: "Author history check is processing.",
    };
  }

  return {
    id: "author_history",
    label: DEFAULT_LABELS.author_history,
    status: "unknown",
    finding: "Author history outcome is unavailable.",
  };
};

const overallAssessmentOutcome = (
  results: JobResults | null | undefined,
  jobStatus?: string,
): SectionOutcome => {
  const retraction = results?.checks?.retraction_detection?.payload;
  const running = isJobRunning(jobStatus);

  if (!retraction) {
    return {
      id: "overall_assessment",
      label: DEFAULT_LABELS.overall_assessment,
      status: running ? "pending" : "unknown",
      finding: running
        ? "Overall assessment pending retraction check."
        : "User must provide overall judgement.",
    };
  }

  const mainResult = retraction?.main_article_result;

  // Main paper retracted → serious concern (auto-fills "serious-concerns")
  if (mainResult?.found === true) {
    return {
      id: "overall_assessment",
      label: DEFAULT_LABELS.overall_assessment,
      status: "concern",
      finding: "Main article is retracted",
    };
  }

  // All other cases → user must decide (no auto-fill)
  return {
    id: "overall_assessment",
    label: DEFAULT_LABELS.overall_assessment,
    status: "unknown",
    finding: "User must provide overall judgement.",
  };
};

export const buildSectionOutcomes = (
  results: JobResults | null | undefined,
  jobStatus?: string,
): SectionOutcome[] => {
  // Get enabled section IDs based on current profile
  const enabledSectionIds = new Set(getEnabledSections().map((s) => s.id));

  // Build all outcomes
  const allOutcomes = [
    retractionOutcome(results, jobStatus),
    eocOutcome(results, jobStatus),
    authorHistoryOutcome(results, jobStatus),
    registrationOutcome(results, jobStatus),
    overallAssessmentOutcome(results, jobStatus),
  ];

  // Filter to only enabled sections
  return allOutcomes.filter((outcome) => enabledSectionIds.has(outcome.id));
};

export const countStatuses = (sections: SectionOutcome[]) => {
  return sections.reduce(
    (acc, section) => {
      const status = normalizeStatus(section.status);
      acc[status] = (acc[status] ?? 0) + 1;
      return acc;
    },
    {
      ok: 0,
      concern: 0,
      attention: 0,
      pending: 0,
      unknown: 0,
    } as Record<StatusToken, number>,
  );
};

export const overallStatusFromSections = (sections: SectionOutcome[]): StatusToken => {
  if (sections.some((section) => section.status === "concern")) return "concern";
  if (sections.some((section) => section.status === "attention")) return "attention";
  if (sections.some((section) => section.status === "pending")) return "pending";
  if (sections.every((section) => section.status === "ok")) return "ok";
  return "unknown";
};

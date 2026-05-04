/**
 * INSPECT-SR Utilities
 *
 * Mappings between question IDs and guidance content keys,
 * data adapters for export, and progress calculation.
 */

import type { InspectSRQuestion } from "@inspect/api-client";
import type { ChecklistData, DomainData, ResponseType, JudgementType } from "@/app/checklist/types";

/**
 * Beta profile: only 5 questions enabled
 * Q1.1 - Retraction, Q1.2 - EOC, Q1.3 - Author history, Q2.2 - Registration timing, OVERALL
 */
export const BETA_QUESTION_IDS = ["Q1.1", "Q1.2", "Q1.3", "Q2.2", "OVERALL"] as const;

/**
 * Beta check question IDs (excluding OVERALL for progress calculation)
 */
export const BETA_CHECK_IDS = ["Q1.1", "Q1.2", "Q1.3", "Q2.2"] as const;

/**
 * Map question IDs (e.g., "Q1.1") to guidance content keys (e.g., "postPublication-0")
 */
export const QUESTION_TO_GUIDANCE_KEY: Record<string, string> = {
  "Q1.1": "postPublication-0",
  "Q1.2": "postPublication-1",
  "Q1.3": "postPublication-2",
  "Q2.2": "conduct-1",
};

/**
 * Map question IDs to human-readable check numbers for display
 */
export const QUESTION_TO_CHECK_NUMBER: Record<string, string> = {
  "Q1.1": "1.1",
  "Q1.2": "1.2",
  "Q1.3": "1.3",
  "Q2.2": "2.2",
};

/**
 * Get guidance key for a question ID
 */
export function getGuidanceKey(questionId: string): string | null {
  return QUESTION_TO_GUIDANCE_KEY[questionId] ?? null;
}

/**
 * Get check number for display (e.g., "Q1.1" -> "1.1")
 */
export function getCheckNumber(questionId: string): string | null {
  return QUESTION_TO_CHECK_NUMBER[questionId] ?? null;
}

/**
 * Calculate assessment progress from InspectSR data
 *
 * For beta profile:
 * - 4 individual checks (Q1.1, Q1.2, Q1.3, Q2.2) contribute to progress
 * - OVERALL is tracked separately (when answered, indicates completion)
 * - Progress shows X/4, and "Complete" badge when OVERALL is answered
 */
export function calculateProgress(records: InspectSRQuestion[]): {
  percent: number;
  answeredChecks: number;
  totalChecks: number;
  overallAnswered: boolean;
} {
  // Use beta check IDs (4 checks, excluding OVERALL)
  const betaCheckIdSet = new Set<string>(BETA_CHECK_IDS);
  const totalChecks = BETA_CHECK_IDS.length; // Always 4 for beta

  // Count answered checks from the beta set
  const answeredChecks = records.filter(
    (r) => betaCheckIdSet.has(r.question_id) && r.reviewed_judgement != null
  ).length;

  const overallRecord = records.find((r) => r.question_id === "OVERALL");
  const overallAnswered = overallRecord?.reviewed_judgement != null;

  // If overall is answered, progress is 100%
  if (overallAnswered) {
    return {
      percent: 100,
      answeredChecks,
      totalChecks,
      overallAnswered: true,
    };
  }

  // Otherwise calculate based on individual checks
  const percent = Math.round((answeredChecks / totalChecks) * 100);

  return {
    percent,
    answeredChecks,
    totalChecks,
    overallAnswered: false,
  };
}

/**
 * Convert InspectSR question array to ChecklistData format for export
 */
export function convertToChecklistData(records: InspectSRQuestion[]): ChecklistData {
  const recordsMap = new Map(records.map((r) => [r.question_id, r]));

  // Helper to get response value
  const getResponse = (qid: string): ResponseType => {
    const record = recordsMap.get(qid);
    const val = record?.reviewed_judgement;
    if (val === "yes" || val === "no" || val === "unclear" || val === "na") {
      return val;
    }
    return null;
  };

  // Helper to get judgement value
  const getJudgement = (qid: string): JudgementType => {
    const record = recordsMap.get(qid);
    const val = record?.reviewed_judgement;
    if (val === "no-concerns" || val === "some-concerns" || val === "serious-concerns") {
      return val;
    }
    return null;
  };

  // Helper to get comment
  const getComment = (qid: string): string => {
    return recordsMap.get(qid)?.comment ?? "";
  };

  const emptyDomain = (): DomainData => ({
    checks: [],
    overallJudgement: null,
    overallComment: "",
  });

  const buildDomain = (checkIds: string[], overallId: string): DomainData => ({
    checks: checkIds.map((qid) => ({
      answer: getResponse(qid),
      comment: getComment(qid),
    })),
    overallJudgement: getJudgement(overallId),
    overallComment: getComment(overallId),
  });

  return {
    postPublication: buildDomain(
      ["Q1.1", "Q1.2", "Q1.3"],
      "D1.overall"
    ),
    conduct: buildDomain(
      ["Q2.2"],
      "D2.overall"
    ),
    textFigures: emptyDomain(),
    results: emptyDomain(),
    overallStudyJudgement: getJudgement("OVERALL"),
    overallStudyComment: getComment("OVERALL"),
  };
}

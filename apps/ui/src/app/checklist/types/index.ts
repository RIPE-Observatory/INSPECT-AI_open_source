// Types for checklist feature
export type DomainKey = "postPublication" | "conduct" | "textFigures" | "results";
export type ResponseType = "yes" | "no" | "unclear" | "na" | null;
export type JudgementType = "no-concerns" | "some-concerns" | "serious-concerns" | null;

export interface CheckResponse {
  answer: ResponseType;
  comment: string;
}

export interface DomainData {
  checks: CheckResponse[];
  overallJudgement: JudgementType;
  overallComment: string;
}

export interface ChecklistData {
  postPublication: DomainData;
  conduct: DomainData;
  textFigures: DomainData;
  results: DomainData;
  overallStudyJudgement: "no-concerns" | "some-concerns" | "serious-concerns" | null;
  overallStudyComment: string;
}

// Flat record for server communication
export interface AnswerRecord {
  question_id: string;
  label: string;
  automated_judgement: string | null;
  reviewed_judgement: string | null;
  comment: string;
}

export interface CheckHelpContent {
  title: string;
  guidelines: string;
  example: string;
}

export interface CheckHelpData {
  [key: string]: CheckHelpContent;
}

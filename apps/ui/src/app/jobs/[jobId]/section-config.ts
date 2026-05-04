export type JobDetailSectionId =
  | "retraction"
  | "eoc"
  | "author_history"
  | "registration"
  | "overall_assessment";

export interface JobDetailSectionConfig {
  id: JobDetailSectionId;
  pickerLabel: string;
  pickerDescription: string;
  heading: string;
  questionId: string;
}

export const JOB_DETAIL_SECTIONS: JobDetailSectionConfig[] = [
  {
    id: "retraction",
    pickerLabel: "Q1.1 Retraction",
    pickerDescription: "Does the study have an associated retraction?",
    heading: "Does the study have an associated retraction?",
    questionId: "Q1.1",
  },
  {
    id: "eoc",
    pickerLabel: "Q1.2 Post-publication notice",
    pickerDescription:
      "Does the study have an associated expression of concern or other relevant post publication notice?",
    heading:
      "Does the study have an associated expression of concern or other relevant post publication notice?",
    questionId: "Q1.2",
  },
  {
    id: "author_history",
    pickerLabel: "Q1.3 Research team concerns",
    pickerDescription:
      "Do other studies by the research team highlight causes for concern (retraction, expression of concern, relevant post-publication notices)?",
    heading: "Do other studies by the research team highlight causes for concern (retraction, expression of concern, relevant post-publication notices)?",
    questionId: "Q1.3",
  },
  {
    id: "registration",
    pickerLabel: "Q2.2 Registration timing",
    pickerDescription:
      "Are there concerns relating to the timing or absence of study registration?",
    heading: "Are there concerns relating to the timing or absence of study registration?",
    questionId: "Q2.2",
  },
  {
    id: "overall_assessment",
    pickerLabel: "Overall Study Judgement",
    pickerDescription: "Final judgement on the study",
    heading: "Overall Study Judgement",
    questionId: "OVERALL",
  },
];

export const JOB_DETAIL_SECTION_LOOKUP: Record<JobDetailSectionId, JobDetailSectionConfig> =
  JOB_DETAIL_SECTIONS.reduce(
    (acc, section) => {
      acc[section.id] = section;
      return acc;
    },
    {} as Record<JobDetailSectionId, JobDetailSectionConfig>,
  );

export function getEnabledSections(): JobDetailSectionConfig[] {
  return JOB_DETAIL_SECTIONS;
}

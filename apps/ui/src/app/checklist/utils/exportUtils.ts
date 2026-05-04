import { AlignmentType, Document, HeadingLevel, Packer, Paragraph, TextRun } from "docx";
import JSZip from "jszip";
import * as XLSX from "xlsx";
import type { ChecklistData } from "../types";

/**
 * INSPECT-SR Beta Export Utilities
 *
 * Exports the 5 beta questions:
 * - Q1.1: Retraction
 * - Q1.2: Expression of concern
 * - Q1.3: Author history
 * - Q2.2: Registration
 * - OVERALL: Overall study judgement
 */

// Beta profile questions with their labels
const BETA_QUESTIONS = [
  {
    id: "Q1.1",
    number: "1.1",
    label: "Does the study have an associated retraction?",
    type: "check" as const,
  },
  {
    id: "Q1.2",
    number: "1.2",
    label: "Does the study have an associated expression of concern or other relevant post publication notice?",
    type: "check" as const,
  },
  {
    id: "Q1.3",
    number: "1.3",
    label: "Do other studies by the research team highlight causes for concern (associated retractions, expressions of concern, relevant post-publication notices)?",
    type: "check" as const,
  },
  {
    id: "Q2.2",
    number: "2.2",
    label: "Are there concerns relating to the timing or absence of study registration?",
    type: "check" as const,
  },
];

// Color mapping for responses
const RESPONSE_COLORS: { [key: string]: string } = {
  yes: "#dc2626", // red 600
  no: "#16a34a", // green 600
  unclear: "#d97706", // amber 600
  na: "#4b5563", // gray 600
  "no-concerns": "#16a34a", // green 600
  "some-concerns": "#d97706", // amber 600
  "serious-concerns": "#dc2626", // red 600
};

// Utility functions
const formatDate = (date: Date) => {
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const generateReportId = () => {
  const now = new Date();
  return `INSPECT-${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, "0")}${now.getDate().toString().padStart(2, "0")}-${now.getHours().toString().padStart(2, "0")}${now.getMinutes().toString().padStart(2, "0")}`;
};

const formatResponse = (response: string | null) => {
  if (!response) return "Not answered";
  switch (response) {
    case "yes":
      return "Yes";
    case "no":
      return "No";
    case "unclear":
      return "Unclear";
    case "na":
      return "N/A";
    case "no-concerns":
      return "No concerns";
    case "some-concerns":
      return "Some concerns";
    case "serious-concerns":
      return "Serious concerns";
    default:
      return response;
  }
};

/**
 * Extract beta question data from ChecklistData
 * Maps the nested structure to the 5 beta questions
 */
const extractBetaQuestions = (data: ChecklistData) => {
  return {
    // Q1.1 - postPublication.checks[0]
    "Q1.1": {
      answer: data.postPublication.checks[0]?.answer ?? null,
      comment: data.postPublication.checks[0]?.comment ?? "",
    },
    // Q1.2 - postPublication.checks[1]
    "Q1.2": {
      answer: data.postPublication.checks[1]?.answer ?? null,
      comment: data.postPublication.checks[1]?.comment ?? "",
    },
    // Q1.3 - postPublication.checks[2]
    "Q1.3": {
      answer: data.postPublication.checks[2]?.answer ?? null,
      comment: data.postPublication.checks[2]?.comment ?? "",
    },
    // Q2.2 - conduct.checks[0]
    "Q2.2": {
      answer: data.conduct.checks[0]?.answer ?? null,
      comment: data.conduct.checks[0]?.comment ?? "",
    },
    // OVERALL - study-level judgement
    OVERALL: {
      answer: data.overallStudyJudgement,
      comment: data.overallStudyComment ?? "",
    },
  };
};

/**
 * Calculate completion stats for beta profile
 */
const calculateBetaCompletion = (data: ChecklistData) => {
  const questions = extractBetaQuestions(data);
  const checks = ["Q1.1", "Q1.2", "Q1.3", "Q2.2"] as const;
  const answeredChecks = checks.filter((id) => questions[id].answer !== null).length;
  const overallAnswered = questions.OVERALL.answer !== null;

  return {
    answeredChecks,
    totalChecks: 4,
    overallAnswered,
    isComplete: overallAnswered,
  };
};

// PDF Generation
export const generatePDF = async (data: ChecklistData, studyTitle?: string): Promise<Blob> => {
  const { jsPDF } = await import("jspdf");

  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 20;
  let yPosition = margin;

  const questions = extractBetaQuestions(data);
  const completion = calculateBetaCompletion(data);

  // Helper function to add text with word wrap
  const addText = (
    text: string,
    fontSize = 12,
    isBold = false,
    maxWidth = pageWidth - 2 * margin,
    color?: string,
  ) => {
    doc.setFontSize(fontSize);
    doc.setFont("helvetica", isBold ? "bold" : "normal");

    if (color) {
      const r = Number.parseInt(color.slice(1, 3), 16);
      const g = Number.parseInt(color.slice(3, 5), 16);
      const b = Number.parseInt(color.slice(5, 7), 16);
      doc.setTextColor(r, g, b);
    } else {
      doc.setTextColor(0, 0, 0);
    }

    const lines = doc.splitTextToSize(text, maxWidth);
    for (const line of lines) {
      if (yPosition > doc.internal.pageSize.getHeight() - margin) {
        doc.addPage();
        yPosition = margin;
      }
      doc.text(line, margin, yPosition);
      yPosition += fontSize * 0.4;
    }
    yPosition += 5;
  };

  // Helper for colored response text
  const addResponseLine = (label: string, response: string | null) => {
    doc.setFontSize(11);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(0, 0, 0);

    const prefix = `${label}: `;
    doc.text(prefix, margin, yPosition);
    const prefixWidth = doc.getTextWidth(prefix);

    const formattedResponse = formatResponse(response);
    if (response && RESPONSE_COLORS[response]) {
      const color = RESPONSE_COLORS[response];
      const r = Number.parseInt(color.slice(1, 3), 16);
      const g = Number.parseInt(color.slice(3, 5), 16);
      const b = Number.parseInt(color.slice(5, 7), 16);
      doc.setTextColor(r, g, b);
    }
    doc.text(formattedResponse, margin + prefixWidth, yPosition);
    doc.setTextColor(0, 0, 0);
    yPosition += 11 * 0.4 + 5;
  };

  // ===== HEADER =====
  addText("INSPECT-SR Assessment Report", 18, true);
  addText("Beta Version", 12, false);
  yPosition += 10;

  // Report metadata
  addText(`Generated: ${formatDate(new Date())}`, 10);
  addText(`Report ID: ${generateReportId()}`, 10);
  if (studyTitle) {
    addText(`Study: ${studyTitle}`, 10);
  }
  yPosition += 15;

  // ===== OVERALL STUDY JUDGEMENT =====
  addText("OVERALL STUDY JUDGEMENT", 16, true);
  addResponseLine("Assessment", questions.OVERALL.answer);
  if (questions.OVERALL.comment) {
    addText(`Comments: ${questions.OVERALL.comment}`, 10);
  }
  addText(`Completion: ${completion.answeredChecks}/${completion.totalChecks} checks answered`, 10);
  yPosition += 15;

  // ===== INDIVIDUAL CHECKS =====
  addText("INDIVIDUAL CHECKS", 16, true);
  yPosition += 5;

  for (const question of BETA_QUESTIONS) {
    const qData = questions[question.id as keyof typeof questions];

    // Question header
    addText(`Check ${question.number}: ${question.label}`, 11, true);
    addResponseLine("Response", qData.answer);
    if (qData.comment) {
      addText(`Comments: ${qData.comment}`, 10);
    }
    yPosition += 8;
  }

  // ===== FOOTER =====
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(100, 100, 100);
    doc.text(
      "Generated by INSPECT-AI",
      margin,
      doc.internal.pageSize.getHeight() - 10,
    );
    doc.text(
      `Page ${i} of ${totalPages}`,
      pageWidth - margin - 30,
      doc.internal.pageSize.getHeight() - 10,
    );
  }

  return new Blob([doc.output("blob")], { type: "application/pdf" });
};

// Excel Generation
export const generateExcel = (data: ChecklistData, studyTitle?: string): Blob => {
  const workbook = XLSX.utils.book_new();
  const questions = extractBetaQuestions(data);
  const completion = calculateBetaCompletion(data);

  // Summary Sheet
  const summaryData = [
    ["INSPECT-SR Assessment Report"],
    ["Beta Version"],
    [],
    ["Generated:", formatDate(new Date())],
    ["Report ID:", generateReportId()],
    ...(studyTitle ? [["Study:", studyTitle]] : []),
    [],
    ["OVERALL STUDY JUDGEMENT"],
    ["Assessment:", formatResponse(questions.OVERALL.answer)],
    ["Comments:", questions.OVERALL.comment || ""],
    [],
    ["Completion:", `${completion.answeredChecks}/${completion.totalChecks} checks answered`],
    ["Status:", completion.isComplete ? "Complete" : "In Progress"],
  ];

  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  // Set column widths
  summarySheet["!cols"] = [{ wch: 20 }, { wch: 80 }];
  XLSX.utils.book_append_sheet(workbook, summarySheet, "Summary");

  // Detailed Checks Sheet
  const detailedData = [
    ["Check #", "Question", "Response", "Comments"],
  ];

  for (const question of BETA_QUESTIONS) {
    const qData = questions[question.id as keyof typeof questions];
    detailedData.push([
      question.number,
      question.label,
      formatResponse(qData.answer),
      qData.comment || "",
    ]);
  }

  // Add overall as last row
  detailedData.push([]);
  detailedData.push([
    "OVERALL",
    "Overall Study Judgement",
    formatResponse(questions.OVERALL.answer),
    questions.OVERALL.comment || "",
  ]);

  const detailedSheet = XLSX.utils.aoa_to_sheet(detailedData);
  // Set column widths
  detailedSheet["!cols"] = [
    { wch: 10 },  // Check #
    { wch: 60 },  // Question
    { wch: 20 },  // Response
    { wch: 50 },  // Comments
  ];
  XLSX.utils.book_append_sheet(workbook, detailedSheet, "Checks");

  const excelBuffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
  return new Blob([excelBuffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
};

// Word Generation
export const generateWord = async (data: ChecklistData, studyTitle?: string): Promise<Blob> => {
  const questions = extractBetaQuestions(data);
  const completion = calculateBetaCompletion(data);

  const children: Paragraph[] = [
    // Header
    new Paragraph({
      text: "INSPECT-SR Assessment Report",
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
    }),
    new Paragraph({
      text: "Beta Version",
      alignment: AlignmentType.CENTER,
    }),
    new Paragraph({ text: "" }),

    // Metadata
    new Paragraph({ text: `Generated: ${formatDate(new Date())}` }),
    new Paragraph({ text: `Report ID: ${generateReportId()}` }),
    ...(studyTitle ? [new Paragraph({ text: `Study: ${studyTitle}` })] : []),
    new Paragraph({ text: "" }),

    // Overall Study Judgement
    new Paragraph({
      text: "Overall Study Judgement",
      heading: HeadingLevel.HEADING_1,
    }),
    new Paragraph({
      children: [
        new TextRun({ text: "Assessment: ", bold: true }),
        new TextRun({ text: formatResponse(questions.OVERALL.answer) }),
      ],
    }),
    ...(questions.OVERALL.comment
      ? [
          new Paragraph({
            children: [
              new TextRun({ text: "Comments: ", bold: true }),
              new TextRun({ text: questions.OVERALL.comment }),
            ],
          }),
        ]
      : []),
    new Paragraph({
      text: `Completion: ${completion.answeredChecks}/${completion.totalChecks} checks answered`,
    }),
    new Paragraph({ text: "" }),

    // Individual Checks
    new Paragraph({
      text: "Individual Checks",
      heading: HeadingLevel.HEADING_1,
    }),
  ];

  // Add each check
  for (const question of BETA_QUESTIONS) {
    const qData = questions[question.id as keyof typeof questions];

    children.push(
      new Paragraph({
        text: `Check ${question.number}: ${question.label}`,
        heading: HeadingLevel.HEADING_2,
      }),
      new Paragraph({
        children: [
          new TextRun({ text: "Response: ", bold: true }),
          new TextRun({ text: formatResponse(qData.answer) }),
        ],
      }),
    );

    if (qData.comment) {
      children.push(
        new Paragraph({
          children: [
            new TextRun({ text: "Comments: ", bold: true }),
            new TextRun({ text: qData.comment }),
          ],
        }),
      );
    }

    children.push(new Paragraph({ text: "" }));
  }

  const doc = new Document({
    sections: [
      {
        properties: {},
        children,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  return new Blob([buffer as BlobPart], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
};

// ZIP Generation
export const generateZIP = async (data: ChecklistData, studyTitle?: string): Promise<Blob> => {
  const zip = new JSZip();
  const timestamp = generateReportId();

  // Generate all formats
  const [pdfBlob, excelBlob, wordBlob] = await Promise.all([
    generatePDF(data, studyTitle),
    Promise.resolve(generateExcel(data, studyTitle)),
    generateWord(data, studyTitle),
  ]);

  // Add files to ZIP
  zip.file(`INSPECT-SR-Report-${timestamp}.pdf`, pdfBlob);
  zip.file(`INSPECT-SR-Report-${timestamp}.xlsx`, excelBlob);
  zip.file(`INSPECT-SR-Report-${timestamp}.docx`, wordBlob);

  return await zip.generateAsync({ type: "blob" });
};

// Download helper
export const downloadFile = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

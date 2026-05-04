"use client";

import {
  Button,
  cn,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Typography,
} from "@inspect/ui";
import {
  Archive,
  Check,
  ChevronDown,
  Download,
  FileSpreadsheet,
  FileText,
  FileType,
  Loader2,
} from "lucide-react";
import { useState } from "react";
import type { ChecklistData } from "../types";
import { downloadFile } from "../utils/exportUtils";

interface ExportDropdownProps {
  checklistData: ChecklistData;
  studyTitle?: string;
  triggerClassName?: string;
}

type ExportFormat = "pdf" | "excel" | "word" | "zip";

// Semantic color styles for each export format
const FORMAT_STYLES = {
  pdf: {
    iconColor: "text-destructive",
    bgBase: "bg-destructive/10",
    bgHover: "group-hover:bg-destructive/20",
    ringHover: "group-hover:ring-1 group-hover:ring-destructive/40",
  },
  excel: {
    iconColor: "text-success",
    bgBase: "bg-success/10",
    bgHover: "group-hover:bg-success/20",
    ringHover: "group-hover:ring-1 group-hover:ring-success/40",
  },
  word: {
    iconColor: "text-info",
    bgBase: "bg-info/10",
    bgHover: "group-hover:bg-info/20",
    ringHover: "group-hover:ring-1 group-hover:ring-info/40",
  },
  zip: {
    iconColor: "text-muted-foreground",
    bgBase: "bg-muted/50",
    bgHover: "group-hover:bg-primary/15",
    ringHover: "",
  },
} as const;

const exportOptions: {
  format: ExportFormat;
  label: string;
  description: string;
  icon: typeof FileText;
}[] = [
  { format: "pdf", label: "PDF Report", description: "Professional document", icon: FileText },
  { format: "excel", label: "Excel Data", description: "Spreadsheet format", icon: FileSpreadsheet },
  { format: "word", label: "Word Document", description: "Editable format", icon: FileType },
];

export default function ExportDropdown({ checklistData, studyTitle, triggerClassName }: ExportDropdownProps) {
  const [isGenerating, setIsGenerating] = useState<string | null>(null);
  const [lastExported, setLastExported] = useState<string | null>(null);

  const generateTimestamp = () => {
    const now = new Date();
    return `${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, "0")}${now.getDate().toString().padStart(2, "0")}-${now.getHours().toString().padStart(2, "0")}${now.getMinutes().toString().padStart(2, "0")}`;
  };

  const handleExport = async (format: ExportFormat) => {
    setIsGenerating(format);
    const timestamp = generateTimestamp();

    try {
      const { generatePDF, generateExcel, generateWord, generateZIP } = await import("../utils/exportUtils");

      let blob: Blob;
      let filename: string;

      switch (format) {
        case "pdf":
          blob = await generatePDF(checklistData, studyTitle);
          filename = `INSPECT-SR-Report-${timestamp}.pdf`;
          break;
        case "excel":
          blob = generateExcel(checklistData, studyTitle);
          filename = `INSPECT-SR-Report-${timestamp}.xlsx`;
          break;
        case "word":
          blob = await generateWord(checklistData, studyTitle);
          filename = `INSPECT-SR-Report-${timestamp}.docx`;
          break;
        case "zip":
          blob = await generateZIP(checklistData, studyTitle);
          filename = `INSPECT-SR-Report-${timestamp}.zip`;
          break;
        default:
          throw new Error("Unknown format");
      }

      downloadFile(blob, filename);
      setLastExported(format);
      // Clear the checkmark after 3 seconds
      setTimeout(() => setLastExported(null), 3000);
    } catch {
      // Error handling
    } finally {
      setIsGenerating(null);
    }
  };

  const renderIcon = (format: ExportFormat, IconComponent: typeof FileText) => {
    if (isGenerating === format) {
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    }
    if (lastExported === format) {
      return <Check className="h-4 w-4 text-success" />;
    }
    return <IconComponent className={cn("h-4 w-4", FORMAT_STYLES[format].iconColor)} />;
  };

  const getIconContainerClasses = (format: ExportFormat) =>
    cn(
      "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md",
      "transition-all duration-150",
      FORMAT_STYLES[format].bgBase,
      FORMAT_STYLES[format].bgHover,
      FORMAT_STYLES[format].ringHover
    );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {triggerClassName ? (
          <button
            type="button"
            className={triggerClassName}
            disabled={isGenerating !== null}
          >
            {isGenerating ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-foreground transition-colors duration-150 group-hover:text-background" />
            ) : (
              <Download className="h-3.5 w-3.5 text-foreground transition-colors duration-150 group-hover:text-background" />
            )}
            <Typography variant="body-sm" weight="strong" as="span" className="text-foreground group-hover:text-background">
              Export
            </Typography>
            <ChevronDown className="h-3.5 w-3.5 text-foreground transition-transform duration-150 group-hover:text-background group-data-[state=open]:rotate-180" />
          </button>
        ) : (
          <Button
            variant="surface"
            size="lg"
            className="group font-semibold transition-colors duration-150 hover:bg-primary/10 hover:text-primary"
            disabled={isGenerating !== null}
          >
            {isGenerating ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            Export
            <ChevronDown className="ml-2 h-4 w-4 transition-transform duration-150 group-data-[state=open]:rotate-180" />
          </Button>
        )}
      </DropdownMenuTrigger>

      <DropdownMenuContent
        className="min-w-[220px] border border-border bg-popover p-1.5 shadow-[var(--shadow-base-md)]"
        align="end"
        sideOffset={4}
        collisionPadding={8}
      >
        {exportOptions.map((option) => (
          <DropdownMenuItem
            key={option.format}
            onClick={() => handleExport(option.format)}
            disabled={isGenerating !== null}
            className="group flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 transition-colors duration-150 focus:bg-primary/8 data-[highlighted]:bg-primary/8"
          >
            <span className={getIconContainerClasses(option.format)}>
              {renderIcon(option.format, option.icon)}
            </span>
            <span className="flex flex-col gap-0.5">
              <Typography variant="body-sm" weight="strong" as="span" className="text-foreground">
                {option.label}
              </Typography>
              <Typography variant="body-xs" as="span" tone="muted">
                {option.description}
              </Typography>
            </span>
          </DropdownMenuItem>
        ))}

        <DropdownMenuSeparator className="my-1.5 bg-border/60" />

        <DropdownMenuItem
          onClick={() => handleExport("zip")}
          disabled={isGenerating !== null}
          className="group flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 transition-colors duration-150 focus:bg-primary/8 data-[highlighted]:bg-primary/8"
        >
          <span className={getIconContainerClasses("zip")}>
            {renderIcon("zip", Archive)}
          </span>
          <span className="flex flex-col gap-0.5">
            <Typography variant="body-sm" weight="strong" as="span" className="text-foreground">
              All Formats
            </Typography>
            <Typography variant="body-xs" as="span" tone="muted">
              Download as ZIP
            </Typography>
          </span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

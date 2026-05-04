"use client";

import { Typography } from "@inspect/ui";
import { ExternalLink } from "@/components/ui/external-link";
import { isExternalLink } from "@/lib/linkUtils";
import type {
  Check1LLMExtraction,
  Check2RegistryLookup,
  Check3StudyTimelineDates,
  Check6ProspectiveRegistrationAnalysis,
  TabContentCommonProps,
} from "@inspect/api-client";
import type * as React from "react";
import { DataPoint, mapBackendCheckStatusToDataPointStatus } from "../utils/shared";
import type { StatusToken } from "../utils/shared";

const RegistrationTabContent: React.FC<TabContentCommonProps & { title: string }> = ({
  results,
  jobStatus,
  title,
}) => {
  const check1: Check1LLMExtraction | undefined =
    results?.checks?.trial_llm_extraction?.payload;
  const check2RegistryLookup: Check2RegistryLookup | undefined =
    results?.checks?.registry_crosscheck?.payload;
  const check2LookupResults = check2RegistryLookup?.lookup_results;
  const check3: Check3StudyTimelineDates | undefined =
    results?.checks?.timeline_consistency?.payload;
  const check6: Check6ProspectiveRegistrationAnalysis | undefined =
    results?.checks?.prospective_registration_analysis?.payload;

  const isJobRunning = jobStatus === "RUNNING" || jobStatus === "PENDING";

  // Helper function to render registry link
  const renderRegistryLink = (url?: string, registryName?: string) => {
    if (!url || !registryName) return undefined;

    if (isExternalLink(url)) {
      return (
        <ExternalLink href={url} showIcon={true} iconSize={14}>
          View on {registryName}
        </ExternalLink>
      );
    }

    // Fallback for internal links (shouldn't happen for registry URLs, but good practice)
    return (
      <a href={url} className="text-info hover:underline">
        View on {registryName}
      </a>
    );
  };

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <Typography variant="h4">{title}</Typography>
      </div>

      <div className="space-y-4">
        <DataPoint
          label="Extracted Trial ID"
          value={check1?.trial_id}
          isLoading={isJobRunning && check1 === undefined}
          status={
            isJobRunning && check1 === undefined ? undefined : check1?.trial_id ? "ok" : "attention"
          }
          interpretation={check1?.comment}
        />
        <DataPoint
          label="Extracted Registry"
          value={check1?.registry_type}
          isLoading={isJobRunning && check1 === undefined}
          status={
            isJobRunning && check1 === undefined
              ? undefined
              : check1?.registry_type
                ? "ok"
                : "attention"
          }
        />
        {(() => {
          const registryErrorMessage =
            check2RegistryLookup?.error_message || check2LookupResults?.error_message;
          const registryLookupSuccessful = check2LookupResults?.lookup_successful;
          const registryDate = check2LookupResults?.study_first_submit_qc_date;

          const status: StatusToken | undefined = (() => {
            if (isJobRunning && check2RegistryLookup === undefined) return undefined;
            if (!check2RegistryLookup) return "unknown";
            if (registryErrorMessage) return "attention";
            if (registryLookupSuccessful === true) {
              return registryDate ? "ok" : "attention";
            }
            if (registryLookupSuccessful === false) return "attention";
            return "unknown";
          })();

          const linkNode = renderRegistryLink(
            check2LookupResults?.url,
            check2LookupResults?.registry_name,
          );
          const needsMessage =
            !!registryErrorMessage ||
            registryLookupSuccessful === false ||
            (registryLookupSuccessful === true && !registryDate);
          const messageText =
            registryErrorMessage ??
            (registryLookupSuccessful === false
              ? "Registry record not found"
              : "Registry found but QC date not available");

          return (
            <DataPoint
              label="Registration Date (QC)"
              value={registryDate}
              isLoading={isJobRunning && check2RegistryLookup === undefined}
              status={status}
              systemComment={
                needsMessage ? (
                  <>
                    {linkNode}
                    {linkNode ? " " : ""}
                    {messageText}
                  </>
                ) : (
                  linkNode
                )
              }
            />
          );
        })()}

        <DataPoint
          label="Recruitment Start Date"
          value={check3?.recruitment_start?.normalized_date}
          isLoading={isJobRunning && check3 === undefined}
          status={
            isJobRunning && check3 === undefined
              ? undefined
              : check3?.recruitment_start?.normalized_date
                ? "ok"
                : "attention"
          }
          interpretation={check3?.recruitment_start?.interpretation_comment}
        />
        <DataPoint
          label="Recruitment End Date"
          value={check3?.recruitment_finish?.normalized_date}
          isLoading={isJobRunning && check3 === undefined}
          status={
            isJobRunning && check3 === undefined
              ? undefined
              : check3?.recruitment_finish?.normalized_date
                ? "ok"
                : "attention"
          }
          interpretation={check3?.recruitment_finish?.interpretation_comment}
        />
        <DataPoint
          label="Study End Date"
          value={check3?.study_end_date?.normalized_date}
          isLoading={isJobRunning && check3 === undefined}
          status={
            isJobRunning && check3 === undefined
              ? undefined
              : check3?.study_end_date?.normalized_date
                ? "ok"
                : "attention"
          }
          interpretation={check3?.study_end_date?.interpretation_comment}
        />
        <DataPoint
          label="Registration Assessment (Prospective/Retrospective)"
          value={
            check6?.is_prospective === true
              ? "Prospective"
              : check6?.is_prospective === false
                ? "Retrospective"
                : check6?.status
                  ? check6.status.replace(/_/g, " ")
                  : undefined
          }
          isLoading={isJobRunning && check6 === undefined}
          status={
            check6
              ? check6.is_prospective === true
                ? "ok"
                : check6.is_prospective === false
                  ? "concern"
                  : (mapBackendCheckStatusToDataPointStatus(check6.status) ?? "unknown")
              : isJobRunning
                ? "pending"
                : "unknown"
          }
          systemComment={check6?.message}
        />
      </div>
    </div>
  );
};

export default RegistrationTabContent;

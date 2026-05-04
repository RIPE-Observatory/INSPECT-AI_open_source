"use client";

import { Card, CardContent, Collapsible, CollapsibleContent, CollapsibleTrigger, Typography } from "@inspect/ui";
import type {
  Check4DoiExtraction,
  Check5ReferenceDois,
  Check7RetractionDetection,
  TabContentCommonProps,
} from "@inspect/api-client";
import { ChevronDown, ChevronRight } from "lucide-react";
import type * as React from "react";
import { useState } from "react";
import { RetractionCard, type RetractionCardProps } from "./RetractionCard";

const RetractionTabContent: React.FC<TabContentCommonProps & { title: string }> = ({
  results,
  jobStatus,
  title,
}) => {
  // Use new normalized check structure (results.checks.{check_id}.payload)
  const check4: Check4DoiExtraction | undefined =
    results?.checks?.grobid_primary_metadata?.payload;
  const check5: Check5ReferenceDois | undefined =
    results?.checks?.grobid_reference_metadata?.payload;
  const check7: Check7RetractionDetection | undefined =
    results?.checks?.retraction_detection?.payload;
  const mainRetraction = check7?.main_article_result;
  const referenceRetractions = check7?.reference_results || [];

  const [isCleanReferencesOpen, setIsCleanReferencesOpen] = useState(false);
  const isJobRunning = jobStatus === "RUNNING" || jobStatus === "PENDING";

  // Data transformation for main publication
  const normalizeLookupMethod = (method?: string | null): RetractionCardProps["searchMethod"] => {
    if (method === "doi") return "doi";
    if (method === "title") return "title";
    if (method === "not_found") return "title";
    if (method === "not_searched") return "not_searched";
    return "unknown";
  };

  const getMainPublicationData = (): RetractionCardProps => {
    return {
      title: check4?.main_title ?? mainRetraction?.searched_title ?? undefined,
      doi: check4?.doi_value ?? mainRetraction?.searched_doi ?? undefined,
      searchMethod: normalizeLookupMethod(mainRetraction?.lookup_method),
      foundInDatabase: mainRetraction?.found ?? null,
      // Only show error message for actual errors, not for "not found" results
      errorMessage: mainRetraction?.found === false ? undefined : mainRetraction?.error,
      isLoading: isJobRunning && !mainRetraction,
      retractionRecord: mainRetraction?.retractions?.[0],
    };
  };

  // Data transformation for all references
  const getAllReferencesData = (): RetractionCardProps[] => {
    return referenceRetractions.map((refResult) => {
      // Find matching title from check5
      const fullRef = check5?.references_full?.find((r) => r.doi === refResult.searched_doi);

      return {
        title: fullRef?.title ?? refResult.searched_title ?? undefined,
        doi: refResult.searched_doi ?? fullRef?.doi ?? undefined,
        searchMethod: normalizeLookupMethod(refResult.lookup_method),
        foundInDatabase: refResult.found,
        // Only show error message for actual errors, not for "not found" results
        errorMessage: refResult.found === false ? undefined : refResult.error,
        isLoading: false,
        retractionRecord: refResult.retractions?.[0],
      };
    });
  };

  // Get reference data and categorize
  const allReferencesData = getAllReferencesData();
  const flaggedReferences = allReferencesData.filter((ref) => ref.foundInDatabase === true);
  const cleanReferences = allReferencesData.filter((ref) => ref.foundInDatabase === false);

  // Calculate summary for two-box layout
  const summary = {
    total: allReferencesData.length,
    retracted: flaggedReferences.length,
    clean: cleanReferences.length,
  };

  const mainPublicationData = getMainPublicationData();

  return (
    <div className="space-y-6">
      {/* Summary Section */}
      <div className="space-y-2">
        <Typography variant="h4">{title}</Typography>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 rounded bg-background border border-success text-center">
          <Typography variant="h2" weight="strong" className="text-success mb-1">{summary.clean}</Typography>
          <Typography variant="body-sm" weight="strong" className="text-success">References with No Concerns</Typography>
        </div>
        <div className="p-4 rounded bg-background border border-destructive text-center">
          <Typography variant="h2" weight="strong" className="text-destructive mb-1">{summary.retracted}</Typography>
          <Typography variant="body-sm" weight="strong" className="text-destructive">References with Some Concerns</Typography>
        </div>
      </div>

      {/* Main Publication Section */}
      <div className="space-y-2">
        <Typography variant="h4">Main Publication</Typography>
        <RetractionCard {...mainPublicationData} />
      </div>

      {/* Flagged References Section */}
      {flaggedReferences.length > 0 && (
        <div className="space-y-2">
          <Typography variant="h4">
            References with Concerns ({flaggedReferences.length})
          </Typography>
          <div className="space-y-2">
            {flaggedReferences.map((ref, index) => (
              <RetractionCard key={ref.doi || `flagged-${index}-${ref.title}`} {...ref} />
            ))}
          </div>
        </div>
      )}

      {/* Clean References Section - Collapsible */}
      {cleanReferences.length > 0 && (
        <div className="space-y-2">
          <Collapsible open={isCleanReferencesOpen} onOpenChange={setIsCleanReferencesOpen}>
            <CollapsibleTrigger className="flex items-center gap-2 hover:text-muted-foreground transition-colors">
              {isCleanReferencesOpen ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <Typography variant="h4">
                References without Concerns ({cleanReferences.length})
              </Typography>
            </CollapsibleTrigger>

            <CollapsibleContent className="space-y-2 mt-2">
              {cleanReferences.map((ref, index) => (
                <RetractionCard key={ref.doi || `clean-${index}-${ref.title}`} {...ref} />
              ))}
            </CollapsibleContent>
          </Collapsible>
        </div>
      )}

      {/* Loading state */}
      {isJobRunning && !check7 && (
        <Card className="border border-border bg-background shadow-sm">
          <CardContent className="p-6 text-center">
            <Typography variant="body-sm" tone="muted">Loading retraction analysis...</Typography>
          </CardContent>
        </Card>
      )}

      {/* Error state */}
      {!isJobRunning && !check7 && (
        <Card className="border border-border bg-background shadow-sm">
          <CardContent className="p-6 text-center">
            <Typography variant="body-sm" tone="muted">
              Retraction analysis could not be completed
            </Typography>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default RetractionTabContent;

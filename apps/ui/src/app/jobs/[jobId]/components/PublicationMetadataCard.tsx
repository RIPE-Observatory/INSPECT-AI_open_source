"use client";

import { ExternalLink } from "@/components/ui/external-link";
import type {
  Check4DoiExtraction,
  CheckPayloadWithCost,
  JobData,
} from "@inspect/api-client";
import { Card, CardContent, CardHeader, CardTitle, Typography } from "@inspect/ui";
import { Building2, Calendar, DollarSign, FileText, Timer, Users } from "lucide-react";
import React, { useState } from "react";

interface PublicationMetadataCardProps {
  check4Data: Check4DoiExtraction | undefined;
  isJobRunning: boolean;
  jobData: JobData | null;
}

export function PublicationMetadataCard({
  check4Data,
  isJobRunning,
  jobData,
}: PublicationMetadataCardProps) {
  const [showAllAuthors, setShowAllAuthors] = useState(false);

  // Don't render if no data and job is not running
  if (!check4Data && !isJobRunning) {
    return null;
  }

  // Loading state
  if (isJobRunning && !check4Data) {
    return (
      <Card className="border border-border bg-background shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-muted-foreground" />
            Publication Details
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="space-y-4">
            <div className="animate-pulse">
              <div className="h-4 bg-background rounded w-3/4 mb-2" />
              <div className="h-3 bg-background rounded w-1/2 mb-4" />
              <div className="grid grid-cols-2 gap-4">
                <div className="h-3 bg-background rounded" />
                <div className="h-3 bg-background rounded" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No data available
  if (!check4Data) {
    return null;
  }

  // Helper function to render DOI as clickable link
  const renderDoiLink = (doi: string) => {
    if (!doi) return <Typography variant="body-sm" tone="muted" as="span">DOI not found</Typography>;
    const doiUrl = `https://doi.org/${doi}`;
    return (
      <ExternalLink href={doiUrl} showIcon={true} iconSize={12}>
        <Typography variant="body-sm" className="font-mono text-primary" as="span">{doi}</Typography>
      </ExternalLink>
    );
  };

  // Format publication date
  const formatDate = (dateStr: string | undefined, year: string | number | undefined) => {
    if (dateStr) return dateStr;
    if (typeof year === "number") return year.toString();
    if (typeof year === "string" && year.trim().length > 0) return year;
    return "Not specified";
  };

  // Format page numbers
  const formatPages = (
    pages: string | undefined,
    pageFrom: string | undefined,
    pageTo: string | undefined,
  ) => {
    if (pages) return pages;
    if (pageFrom && pageTo) return `${pageFrom}-${pageTo}`;
    if (pageFrom) return `${pageFrom}+`;
    return undefined;
  };

  const hasMainContent =
    check4Data.main_title ||
    check4Data.doi_value ||
    (check4Data.main_authors && check4Data.main_authors.length > 0);
  const hasJournalInfo =
    check4Data.journal || check4Data.publisher || check4Data.volume || check4Data.issue;

  // Calculate total LLM cost from all checks (type-safe)
  let totalEstimatedCost = 0;
  if (jobData?.results?.checks) {
    const checks = jobData.results.checks;

    // Iterate through normalized checks structure
    for (const checkEnvelope of Object.values(checks)) {
      if (!checkEnvelope?.payload) continue;

      const payload = checkEnvelope.payload;

      // Type guard for CheckPayloadWithCost (trial_llm_extraction, timeline_consistency)
      if ("cost_info" in payload) {
        const typedPayload = payload as CheckPayloadWithCost;
        const costTotal = typedPayload.cost_info?.total_cost;
        if (typeof costTotal === "number") {
          totalEstimatedCost += costTotal;
        }
      }

    }
  }

  // Get processing time from backend
  const processingTimeSeconds =
    jobData?.processing_time_seconds != null ? jobData.processing_time_seconds.toFixed(2) : "N/A";

  let costDecimalPlaces = 4;
  if (totalEstimatedCost > 0 && totalEstimatedCost < 0.0001) {
    costDecimalPlaces = 8;
  } else if (totalEstimatedCost > 0 && totalEstimatedCost < 0.001) {
    costDecimalPlaces = 6;
  }

  return (
    <Card className="border border-border bg-background shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-muted-foreground" />
            Publication Details
          </CardTitle>
          {jobData && jobData.status === "COMPLETED" && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-background border border-border">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <Typography variant="body-sm" weight="strong" className="font-mono">
                  {totalEstimatedCost.toFixed(costDecimalPlaces)}
                </Typography>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-background border border-border">
                <Timer className="h-4 w-4 text-muted-foreground" />
                <Typography variant="body-sm" weight="strong" className="font-mono">{processingTimeSeconds}s</Typography>
              </div>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="pt-0 space-y-6">
        {/* Main Paper Information */}
        {hasMainContent && (
          <div className="space-y-4">
            {/* Title */}
            {check4Data.main_title && (
              <div>
                <Typography variant="body-lg" className="leading-relaxed">{check4Data.main_title}</Typography>
              </div>
            )}

            {/* DOI */}
            <div>
              <Typography variant="body-sm" as="span">DOI: </Typography>{renderDoiLink(check4Data.doi_value)}
            </div>

            {/* Authors */}
            {check4Data.main_authors && check4Data.main_authors.length > 0 && (
              <div>
                <div className="flex flex-wrap gap-2" id="authors-container">
                  {(() => {
                    const correspondingAuthors = check4Data.main_authors.filter(
                      (a) => a.is_corresponding,
                    );
                    const nonCorrespondingAuthors = check4Data.main_authors.filter(
                      (a) => !a.is_corresponding,
                    );

                    let authorsToShow = [];

                    if (showAllAuthors) {
                      // Show all authors: corresponding first, then all non-corresponding
                      authorsToShow = [...correspondingAuthors, ...nonCorrespondingAuthors];
                    } else {
                      // Show limited authors: corresponding first, then up to 12 total
                      authorsToShow.push(...correspondingAuthors);
                      const remainingSlots = 12 - correspondingAuthors.length;
                      authorsToShow.push(...nonCorrespondingAuthors.slice(0, remainingSlots));
                    }

                    return authorsToShow.map((author) => {
                      return (
                        <span
                          key={author.name}
                          className="px-3 py-1.5 rounded bg-background cursor-default border border-border"
                        >
                          <Typography variant="body-sm">
                            {author.name}
                            {author.is_corresponding && (
                              <Typography variant="body-sm" weight="strong" className="ml-1 text-info" as="span">*</Typography>
                            )}
                          </Typography>
                        </span>
                      );
                    });
                  })()}
                  {(() => {
                    // Show expand/collapse button
                    const correspondingAuthors = check4Data.main_authors.filter(
                      (a) => a.is_corresponding,
                    );
                    const nonCorrespondingAuthors = check4Data.main_authors.filter(
                      (a) => !a.is_corresponding,
                    );
                    const remainingSlots = 12 - correspondingAuthors.length;
                    const hiddenAuthors = nonCorrespondingAuthors.slice(remainingSlots);

                    if (hiddenAuthors.length > 0) {
                      return (
                        <button
                          key="expand-button"
                          onClick={() => setShowAllAuthors(!showAllAuthors)}
                          type="button"
                          className="px-3 py-1.5 rounded bg-background text-primary cursor-pointer border border-primary transition-colors duration-150 hover:bg-background focus:outline-none focus:ring-0"
                        >
                          <Typography variant="body-sm">
                            {showAllAuthors ? "Show less" : `+${hiddenAuthors.length} more`}
                          </Typography>
                        </button>
                      );
                    }
                    return null;
                  })()}
                </div>
                {check4Data.main_authors.some((a) => a.is_corresponding) && (
                  <Typography variant="body-xs" className="text-info mt-2">* Corresponding author</Typography>
                )}
              </div>
            )}
          </div>
        )}

        {/* Journal Information */}
        {hasJournalInfo && (
          <div className="border-t border-border pt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Journal */}
              {check4Data.journal && (
                <div className="space-y-1">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                    Journal
                  </Typography>
                  <Typography variant="body-sm">
                    {check4Data.journal}
                    {check4Data.journal_abbrev &&
                      check4Data.journal_abbrev !== check4Data.journal && (
                        <Typography variant="body-sm" tone="muted" className="ml-2" as="span">
                          ({check4Data.journal_abbrev})
                        </Typography>
                      )}
                  </Typography>
                </div>
              )}

              {/* Publisher */}
              {check4Data.publisher && (
                <div className="space-y-1">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                    Publisher
                  </Typography>
                  <Typography variant="body-sm">{check4Data.publisher}</Typography>
                </div>
              )}

              {/* Volume & Issue */}
              {(check4Data.volume || check4Data.issue) && (
                <div className="space-y-1">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                    Volume & Issue
                  </Typography>
                  <Typography variant="body-sm">
                    {check4Data.volume && `Vol. ${check4Data.volume}`}
                    {check4Data.volume && check4Data.issue && ", "}
                    {check4Data.issue && `Issue ${check4Data.issue}`}
                  </Typography>
                </div>
              )}

              {/* Pages */}
              {formatPages(check4Data.pages, check4Data.page_from, check4Data.page_to) && (
                <div className="space-y-1">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                    Pages
                  </Typography>
                  <Typography variant="body-sm">
                    {formatPages(check4Data.pages, check4Data.page_from, check4Data.page_to)}
                  </Typography>
                </div>
              )}

              {/* Publication Date */}
              {(check4Data.publication_date || check4Data.year) && (
                <div className="space-y-1">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider flex items-center gap-1" tone="muted">
                    <Calendar className="h-3 w-3" />
                    Published
                  </Typography>
                  <Typography variant="body-sm">
                    {formatDate(check4Data.publication_date, check4Data.year)}
                  </Typography>
                </div>
              )}

              {/* ISSN */}
              {(check4Data.issn || check4Data.eissn) && (
                <div className="space-y-1">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                    ISSN
                  </Typography>
                  <div className="space-y-0.5">
                    {check4Data.issn && <Typography variant="body-sm">Print: {check4Data.issn}</Typography>}
                    {check4Data.eissn && <Typography variant="body-sm">Electronic: {check4Data.eissn}</Typography>}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Statistics Footer */}
        {(check4Data.total_authors || check4Data.total_affiliations) && (
          <div className="border-t border-border pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {typeof check4Data.total_authors === "number" && (
                  <span className="flex items-center gap-1.5 px-3 py-1 rounded bg-background border border-border">
                    <Users className="h-3 w-3 text-muted-foreground" />
                    <Typography variant="body-xs" weight="strong">{check4Data.total_authors} authors</Typography>
                  </span>
                )}
                {typeof check4Data.total_affiliations === "number" && (
                  <span className="flex items-center gap-1.5 px-3 py-1 rounded bg-background border border-border">
                    <Building2 className="h-3 w-3 text-muted-foreground" />
                    <Typography variant="body-xs" weight="strong">
                      {check4Data.total_affiliations} affiliations
                    </Typography>
                  </span>
                )}
              </div>
              {check4Data.comment && (
                <Typography variant="body-xs" tone="muted">
                  {check4Data.comment.match(/([\d.]+s)/)?.[1] || "Processing time N/A"}
                </Typography>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

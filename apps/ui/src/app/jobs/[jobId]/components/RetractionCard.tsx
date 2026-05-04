"use client";

import { Card, CardContent, CardHeader, CardTitle, Collapsible, CollapsibleContent, CollapsibleTrigger, Typography } from "@inspect/ui";
import type { RetractionRecord } from "@inspect/api-client";
import { ExternalLink } from "@/components/ui/external-link";
import { TextWithLinks } from "@/components/ui/text-with-links";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Loader2,
  Shield,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import type * as React from "react";
import { useState } from "react";

export interface RetractionCardProps {
  title?: string;
  doi?: string;
  searchMethod: "doi" | "title" | "not_searched" | "unknown";
  foundInDatabase: boolean | null;
  errorMessage?: string;
  isLoading?: boolean;
  retractionRecord?: RetractionRecord;
}

export const RetractionCard: React.FC<RetractionCardProps> = ({
  title,
  doi,
  searchMethod,
  foundInDatabase,
  errorMessage,
  isLoading = false,
  retractionRecord,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasRetractionDetails = foundInDatabase === true && retractionRecord;

  // Helper function to render DOI as clickable link
  const renderDoiLink = (doiValue: string) => {
    const doiUrl = `https://doi.org/${doiValue}`;
    return (
      <ExternalLink href={doiUrl} showIcon={true} iconSize={12} className="font-mono">
        <Typography variant="body-sm" as="span">{doiValue}</Typography>
      </ExternalLink>
    );
  };

  // Get status-based styling
  const getCardStyling = () => {
    if (foundInDatabase === true) {
      return "border-destructive/30 bg-background";
    }
    return "border-border bg-background";
  };

  // Get status icon
  const getStatusIcon = () => {
    const iconClass = `h-4 w-4 ${
      isLoading
        ? "text-info"
        : errorMessage
          ? "text-warning"
          : foundInDatabase === true
            ? "text-destructive"
            : foundInDatabase === false
              ? "text-success"
              : "text-muted-foreground"
    }`;

    if (isLoading) {
      return <Loader2 className={`${iconClass} animate-spin`} />;
    }
    if (errorMessage) {
      return <AlertTriangle className={iconClass} />;
    }
    if (foundInDatabase === true) {
      return <ShieldAlert className={iconClass} />;
    }
    if (foundInDatabase === false) {
      return <ShieldCheck className={iconClass} />;
    }
    return <Shield className={iconClass} />;
  };

  // Get status text
  const getStatusText = () => {
    if (isLoading) {
      return "Checking...";
    }
    if (errorMessage) {
      return "Check Failed";
    }
    if (foundInDatabase === true) {
      return "Some Concerns Found";
    }
    if (foundInDatabase === false) {
      return "No Concerns Found";
    }
    return "Status Unknown";
  };

  // Format search method display
  const formatSearchMethod = () => {
    switch (searchMethod) {
      case "doi":
        return "DOI-based lookup";
      case "title":
        return "Title-based lookup";
      case "not_searched":
        return "Not searched";
      default:
        return "Search method unknown";
    }
  };

  // Get title for display
  const getTitle = () => {
    return title || null;
  };

  // Helper to render DOI links in metadata
  const renderMetadataDoiLink = (doi: string | null | undefined, label: string) => {
    if (!doi) return null;
    const doiUrl = `https://doi.org/${doi}`;
    return (
      <div className="space-y-1">
        <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
          {label}:{" "}
        </Typography>
        <ExternalLink href={doiUrl} showIcon={true} iconSize={12}>
          <Typography variant="body-sm" as="span">{doi}</Typography>
        </ExternalLink>
      </div>
    );
  };

  // Helper to render PubMed links in metadata
  const renderPubMedLink = (pmid: string | number | null | undefined, label: string) => {
    if (!pmid) return null;
    const pmUrl = `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`;
    return (
      <div className="space-y-1">
        <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
          {label}:{" "}
        </Typography>
        <ExternalLink href={pmUrl} showIcon={true} iconSize={12}>
          <Typography variant="body-sm" as="span">PMID: {pmid}</Typography>
        </ExternalLink>
      </div>
    );
  };

  // Helper to render field in metadata
  const renderField = (label: string, value: string | number | null | undefined) => {
    if (!value) return null;
    return (
      <div className="space-y-1">
        <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
          {label}
        </Typography>
        <Typography variant="body-sm">{value}</Typography>
      </div>
    );
  };

  return (
    <Card className={`${getCardStyling()} shadow-sm`}>
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        {hasRetractionDetails ? (
          <CollapsibleTrigger asChild>
            <CardHeader className="pb-3 cursor-pointer hover:bg-surface/40 transition-colors">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  {getStatusIcon()}
                  <Typography variant="body-sm" weight="strong" className={foundInDatabase === true ? "text-destructive" : ""}>
                    {getStatusText()}
                  </Typography>
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Typography variant="body-xs" tone="muted">
                    {isExpanded ? "Click to collapse" : "Click to expand"}
                  </Typography>
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
              </div>
            </CardHeader>
          </CollapsibleTrigger>
        ) : (
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                {getStatusIcon()}
                <Typography variant="body-sm" weight="strong" className={foundInDatabase === true ? "text-destructive" : ""}>
                  {getStatusText()}
                </Typography>
              </CardTitle>
            </div>
          </CardHeader>
        )}

        <CardContent className="pt-0">
          {/* Basic Info - Always Visible */}
          <div className="space-y-3">
            <div className="space-y-1">
              <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                Search Method
              </Typography>
              <Typography variant="body-sm">{formatSearchMethod()}</Typography>
            </div>

            {/* DOI - Always show if available */}
            {doi && (
              <div className="space-y-1">
                <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                  DOI {searchMethod === "doi" ? "(Used for Search)" : ""}
                </Typography>
                <div>{renderDoiLink(doi)}</div>
              </div>
            )}

            {/* No DOI indicator */}
            {!doi && (
              <div className="space-y-1">
                <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                  DOI
                </Typography>
                <Typography variant="body-sm" tone="muted" className="italic">Not extracted by GROBID</Typography>
              </div>
            )}

            {/* Title - Always show if available */}
            {title && (
              <div className="space-y-1">
                <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                  Title {searchMethod === "title" ? "(Used for Search)" : ""}
                </Typography>
                <Typography variant="body-sm" className="leading-relaxed">{getTitle()}</Typography>
              </div>
            )}

            {/* Error Message */}
            {errorMessage && (
              <div className="bg-background border border-border p-3 rounded">
                <Typography variant="body-sm" tone="muted">
                  <Typography variant="body-sm" weight="strong" as="span">Error:</Typography> {errorMessage}
                </Typography>
              </div>
            )}
          </div>

          {/* Retraction Details - Collapsible */}
          {hasRetractionDetails && (
            <CollapsibleContent className="mt-4 pt-4 border-t border-border space-y-6">
              {/* Main retraction information */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {renderField("Retraction Nature", retractionRecord.retraction_nature)}
                {renderField("Article Type", retractionRecord.article_type)}
                {renderField("Retraction Date", retractionRecord.retraction_date)}
                {renderField("Original Paper Date", retractionRecord.original_paper_date)}
              </div>

              {/* Reason for retraction */}
              {retractionRecord.reason && (
                <div className="p-4 rounded bg-background border border-border">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider block mb-1" tone="muted">
                    Reason for Retraction
                  </Typography>
                  <div>
                    <Typography variant="body-sm" as="span" className="text-foreground">
                      <TextWithLinks
                        text={retractionRecord.reason}
                        className=""
                        linkClassName=""
                        showIcon={true}
                        iconSize={12}
                      />
                    </Typography>
                  </div>
                </div>
              )}

              {/* Publication details */}
              <div className="space-y-4">
                {renderField("Title", retractionRecord.title)}
                {renderField("Authors", retractionRecord.author)}
                {renderField("Journal", retractionRecord.journal)}
                {renderField("Publisher", retractionRecord.publisher)}
                {renderField("Institution", retractionRecord.institution)}
                {renderField("Country", retractionRecord.country)}
                {renderField("Subject", retractionRecord.subject)}
              </div>

              {/* Identifiers and links */}
              <div className="space-y-4 pt-4 border-t border-border">
                {renderMetadataDoiLink(retractionRecord.original_paper_doi, "Original Paper DOI")}
                {renderMetadataDoiLink(retractionRecord.retraction_doi, "Retraction Notice DOI")}
                {renderPubMedLink(retractionRecord.original_paper_pubmed_id, "Original Paper")}
                {renderPubMedLink(retractionRecord.retraction_pubmed_id, "Retraction Notice")}
              </div>

              {/* URLs */}
              {retractionRecord.urls && (
                <div className="space-y-2">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                    Related Links
                  </Typography>
                  <div className="space-y-1">
                    {retractionRecord.urls.split(",").map((url) => {
                      const trimmedUrl = url.trim();
                      if (!trimmedUrl) return null;
                      return (
                        <ExternalLink
                          key={trimmedUrl}
                          href={trimmedUrl}
                          showIcon={true}
                          iconSize={12}
                          className="block"
                        >
                          <Typography variant="body-sm" as="span">
                            {trimmedUrl.length > 60
                              ? `${trimmedUrl.substring(0, 60)}...`
                              : trimmedUrl}
                          </Typography>
                        </ExternalLink>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Additional notes */}
              {retractionRecord.notes && (
                <div className="pt-4 border-t border-border">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider block mb-1" tone="muted">
                    Notes
                  </Typography>
                  <div>
                    <Typography variant="body-sm" as="span" className="text-foreground">
                      <TextWithLinks
                        text={retractionRecord.notes}
                        className=""
                        linkClassName=""
                        showIcon={true}
                        iconSize={12}
                      />
                    </Typography>
                  </div>
                </div>
              )}
            </CollapsibleContent>
          )}
        </CardContent>
      </Collapsible>
    </Card>
  );
};

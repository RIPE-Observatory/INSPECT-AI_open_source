"use client";

import { Card, CardContent, CardHeader, CardTitle, Collapsible, CollapsibleContent, CollapsibleTrigger, Typography, Badge } from "@inspect/ui";
import { ExternalLink } from "@/components/ui/external-link";
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

interface EOCNotice {
  title: string;
  original_paper_doi: string | null;
  retraction_doi: string | null;
  retraction_nature: string;
  retraction_date: string | null;
  reason: string | null;
  notes: string | null;
  journal: string | null;
  publisher: string | null;
}

export interface EOCCardProps {
  title?: string;
  doi?: string;
  searchMethod: "doi" | "title" | "not_searched" | "unknown";
  foundInDatabase: boolean | null;
  errorMessage?: string;
  isLoading?: boolean;
  eocNotice?: EOCNotice;
}

export const EOCCard: React.FC<EOCCardProps> = ({
  title,
  doi,
  searchMethod,
  foundInDatabase,
  errorMessage,
  isLoading = false,
  eocNotice,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasEOCDetails = foundInDatabase === true && eocNotice;

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

  return (
    <Card className={`${getCardStyling()} shadow-sm`}>
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        {hasEOCDetails ? (
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
                <Typography variant="body-sm" className="leading-relaxed">{title}</Typography>
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

          {/* EOC Notice Details - Collapsible */}
          {hasEOCDetails && (
            <CollapsibleContent className="mt-4 pt-4 border-t border-border space-y-6">
              {/* Main notice information */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {eocNotice.retraction_nature && (
                  <div className="space-y-1">
                    <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider" tone="muted">
                      Notice Type
                    </Typography>
                    <Badge variant="destructive">
                      <Typography variant="body-xs" as="span">{eocNotice.retraction_nature}</Typography>
                    </Badge>
                  </div>
                )}
                {renderField("Notice Date", eocNotice.retraction_date)}
              </div>

              {/* Reason for concern */}
              {eocNotice.reason && (
                <div className="p-4 rounded bg-background border border-border">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider block mb-1" tone="muted">
                    Reason
                  </Typography>
                  <Typography variant="body-sm" className="text-foreground">
                    {eocNotice.reason}
                  </Typography>
                </div>
              )}

              {/* Publication details */}
              <div className="space-y-4">
                {renderField("Notice Title", eocNotice.title)}
                {renderField("Journal", eocNotice.journal)}
                {renderField("Publisher", eocNotice.publisher)}
              </div>

              {/* Identifiers and links */}
              <div className="space-y-4 pt-4 border-t border-border">
                {renderMetadataDoiLink(eocNotice.original_paper_doi, "Original Paper DOI")}
                {renderMetadataDoiLink(eocNotice.retraction_doi, "Notice DOI")}
              </div>

              {/* Additional notes */}
              {eocNotice.notes && (
                <div className="pt-4 border-t border-border">
                  <Typography variant="body-xs" weight="strong" className="uppercase tracking-wider block mb-1" tone="muted">
                    Notes
                  </Typography>
                  <Typography variant="body-sm" className="text-foreground">
                    {eocNotice.notes}
                  </Typography>
                </div>
              )}
            </CollapsibleContent>
          )}
        </CardContent>
      </Collapsible>
    </Card>
  );
};

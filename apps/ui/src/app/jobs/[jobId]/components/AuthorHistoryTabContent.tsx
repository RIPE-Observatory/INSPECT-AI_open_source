"use client";

import { Badge, Card, CardContent, CardHeader, CardTitle, Collapsible, CollapsibleContent, CollapsibleTrigger, Typography } from "@inspect/ui";
import { ExternalLink } from "@/components/ui/external-link";
import type { TabContentCommonProps } from "@inspect/api-client";
import { AlertCircle, CheckCircle, ChevronDown, ChevronRight, User } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { getStatusIcon } from "../utils/shared";

// Type definitions for author_retraction_history check
interface AuthorMetadata {
  surname: string;
  forename: string;
  middle_name: string | null;
  affiliations: string[];
  is_corresponding: boolean;
  professional_title: string | null;
}

interface RetractionRecord {
  title: string;
  original_paper_doi: string | null;
  retraction_doi: string | null;
  retraction_date: string | null;
  retraction_nature: string | null;
  reason: string | null;
  journal: string | null;
  publisher: string | null;
}

interface AuthorResult {
  author_name: string;
  has_retractions: boolean;
  retractions: RetractionRecord[];
  author_metadata: AuthorMetadata | null;
  error: string | null;
}

interface AuthorHistorySummary {
  message: string;
  total_authors_checked: number;
  total_retractions_found: number;
  authors_with_retractions: number;
}

interface AuthorHistoryCheck {
  status: "ok" | "concern" | "error" | "failed";
  detail: string;
  check_id: string;
  summary: string;
  finding_code: string;
  payload: {
    summary: AuthorHistorySummary;
    author_results: AuthorResult[];
    error_message: string | null;
  };
  error_message?: string;
  provider_messages?: string[];
}

interface AuthorCardProps {
  author: AuthorResult;
}

const AuthorCard: React.FC<AuthorCardProps> = ({ author }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasRetractions = author.has_retractions && author.retractions.length > 0;

  return (
    <Card
      className={`border ${hasRetractions ? "border-destructive bg-destructive/5" : "border-border bg-background"} shadow-sm`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <div className="mt-1">
              {hasRetractions ? (
                <AlertCircle className="h-5 w-5 text-destructive" />
              ) : (
                <CheckCircle className="h-5 w-5 text-success" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <User className="h-4 w-4 text-muted-foreground" />
                <CardTitle>{author.author_name}</CardTitle>
              </div>
              {author.author_metadata && (
                <div className="space-y-1">
                  {author.author_metadata.affiliations.length > 0 && (
                    <Typography variant="body-sm" tone="muted">{author.author_metadata.affiliations.join(", ")}</Typography>
                  )}
                  {author.author_metadata.is_corresponding && (
                    <Badge variant="outline">
                      <Typography variant="body-xs" as="span">Corresponding Author</Typography>
                    </Badge>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="text-right">
            {hasRetractions ? (
              <Badge variant="destructive">
                <Typography variant="body-xs" as="span">
                  {author.retractions.length} Mention{author.retractions.length !== 1 ? "s" : ""}
                </Typography>
              </Badge>
            ) : (
              <Badge
                variant="outline"
                className="bg-success/10 text-success border-success"
              >
                <Typography variant="body-xs" as="span">No Mentions</Typography>
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      {hasRetractions && (
        <CardContent className="pt-0">
          <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
            <CollapsibleTrigger className="flex items-center gap-2 hover:text-muted-foreground transition-colors">
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <Typography variant="body-sm" weight="strong">
                View {author.retractions.length} mention{author.retractions.length !== 1 ? "s" : ""} in Retraction Watch
              </Typography>
            </CollapsibleTrigger>

            <CollapsibleContent className="space-y-3 mt-3">
              {author.retractions.map((retraction, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded bg-background border border-destructive/20"
                >
                  <Typography variant="body-sm" weight="strong" className="mb-2">
                    {retraction.title || "Untitled"}
                  </Typography>
                  <div className="space-y-1">
                    {retraction.original_paper_doi && (
                      <div className="flex items-start gap-2">
                        <Typography variant="body-sm" weight="strong" className="min-w-[80px]">DOI:</Typography>
                        <ExternalLink
                          href={`https://doi.org/${retraction.original_paper_doi}`}
                          showIcon={true}
                          iconSize={12}
                        >
                          <Typography variant="body-sm" className="text-info hover:text-info/80 break-all">
                            {retraction.original_paper_doi}
                          </Typography>
                        </ExternalLink>
                      </div>
                    )}
                    {retraction.retraction_date && (
                      <div className="flex items-start gap-2">
                        <Typography variant="body-sm" weight="strong" className="min-w-[80px]">Retracted:</Typography>
                        <Typography variant="body-sm" tone="muted">{new Date(retraction.retraction_date).toLocaleDateString()}</Typography>
                      </div>
                    )}
                    {retraction.retraction_nature && (
                      <div className="flex items-start gap-2">
                        <Typography variant="body-sm" weight="strong" className="min-w-[80px]">Nature:</Typography>
                        <Typography variant="body-sm" tone="muted">{retraction.retraction_nature}</Typography>
                      </div>
                    )}
                    {retraction.reason && (
                      <div className="flex items-start gap-2">
                        <Typography variant="body-sm" weight="strong" className="min-w-[80px]">Reason:</Typography>
                        <Typography variant="body-sm" tone="muted">{retraction.reason}</Typography>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        </CardContent>
      )}

      {author.error && (
        <CardContent className="pt-0">
          <div className="bg-destructive/10 p-2 rounded">
            <Typography variant="body-xs" className="text-destructive">Error: {author.error}</Typography>
          </div>
        </CardContent>
      )}
    </Card>
  );
};

const AuthorHistoryTabContent: React.FC<TabContentCommonProps & { title: string }> = ({
  results,
  jobStatus,
  title,
}) => {
  // Use new normalized check structure (results.checks.{check_id})
  const authorHistoryData = results?.checks?.author_retraction_history as
    | AuthorHistoryCheck
    | undefined;
  const isJobRunning = jobStatus === "RUNNING" || jobStatus === "PENDING";

  // Loading state
  if (isJobRunning && !authorHistoryData) {
    return (
      <div className="space-y-6">
        <Typography variant="h4">{title}</Typography>
        <Card className="border border-border bg-background shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-2">
              {getStatusIcon("LOADING")}
              <Typography variant="body-sm" tone="muted">
                Analyzing author retraction history...
              </Typography>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // No data available
  if (!authorHistoryData) {
    return (
      <div className="space-y-6">
        <Typography variant="h4">{title}</Typography>
        <Card className="border border-border bg-background shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-2">
              {getStatusIcon("WARNING")}
              <Typography variant="body-sm" tone="muted">
                No author history data available
              </Typography>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state
  if (
    authorHistoryData.status === "failed" ||
    authorHistoryData.status === "error" ||
    authorHistoryData.error_message
  ) {
    return (
      <div className="space-y-6">
        <Typography variant="h4">{title}</Typography>
        <Card className="border border-destructive bg-background shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-2">
              {getStatusIcon("FAILED")}
              <Typography variant="body-sm">
                Author history analysis failed
                {authorHistoryData.error_message ? `: ${authorHistoryData.error_message}` : ""}
              </Typography>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const summary = authorHistoryData.payload?.summary;
  const authorResults = authorHistoryData.payload?.author_results || [];
  const authorsWithRetractions = authorResults.filter((a) => a.has_retractions);
  const authorsWithoutRetractions = authorResults.filter((a) => !a.has_retractions);

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="space-y-2">
        <Typography variant="h4">{title}</Typography>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded bg-background border border-success text-center">
            <Typography variant="h2" weight="strong" className="text-success mb-1">
              {summary.total_authors_checked - summary.authors_with_retractions}
            </Typography>
            <Typography variant="body-sm" weight="strong" className="text-success">Authors with No Mentions</Typography>
          </div>
          <div className="p-4 rounded bg-background border border-destructive text-center">
            <Typography variant="h2" weight="strong" className="text-destructive mb-1">
              {summary.authors_with_retractions}
            </Typography>
            <Typography variant="body-sm" weight="strong" className="text-destructive">Authors with Some Mentions</Typography>
          </div>
        </div>
      )}

      {/* Authors with Mentions */}
      {authorsWithRetractions.length > 0 && (
        <div className="space-y-3">
          <Typography variant="h4">
            Authors with Mentions in Retraction Watch ({authorsWithRetractions.length})
          </Typography>
          <div className="space-y-3">
            {authorsWithRetractions.map((author) => (
              <AuthorCard key={author.author_name} author={author} />
            ))}
          </div>
        </div>
      )}

      {/* Authors without Mentions - Collapsible */}
      {authorsWithoutRetractions.length > 0 && (
        <div className="space-y-2">
          <Collapsible>
            <CollapsibleTrigger className="flex items-center gap-2 hover:text-muted-foreground transition-colors">
              <ChevronRight className="h-4 w-4" />
              <Typography variant="h4">
                Authors without Mentions in Retraction Watch ({authorsWithoutRetractions.length})
              </Typography>
            </CollapsibleTrigger>

            <CollapsibleContent className="space-y-3 mt-3">
              {authorsWithoutRetractions.map((author) => (
                <AuthorCard key={author.author_name} author={author} />
              ))}
            </CollapsibleContent>
          </Collapsible>
        </div>
      )}
    </div>
  );
};

export default AuthorHistoryTabContent;

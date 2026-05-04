"use client";

import { Card, CardContent, CardHeader, CardTitle, Typography } from "@inspect/ui";
import { ExternalLink } from "@/components/ui/external-link";
import type { TabContentCommonProps } from "@inspect/api-client";
import { CheckCircle } from "lucide-react";
import type React from "react";
import { getStatusIcon } from "../utils/shared";
import PubPeerCommentCard from "./PubPeerCommentCard";
import { EOCCard, type EOCCardProps } from "./EOCCard";

// Type definitions for eoc_correction_detection check
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

interface EOCMainArticleResult {
  found: boolean;
  notices: EOCNotice[];
  searched_doi: string | null;
  searched_title: string | null;
  lookup_method: string;
  error?: string | null;
}

interface EOCSummary {
  message: string;
  total_notices: number;
  main_article_has_eoc_or_correction: boolean;
}

interface EOCCheck {
  status: "ok" | "concern" | "error" | "failed";
  detail: string;
  check_id: string;
  summary: string;
  finding_code: string;
  payload: {
    summary: EOCSummary;
    main_article_result: EOCMainArticleResult;
    error_message: string | null;
  };
  error_message?: string;
  provider_messages?: string[];
}

const EOCTabContent: React.FC<TabContentCommonProps & { title: string }> = ({
  results,
  jobStatus,
  title,
}) => {
  // Use new normalized check structure (results.checks.{check_id})
  const eocData = results?.checks?.eoc_correction_detection as EOCCheck | undefined;
  const pubPeerData = results?.checks?.pubpeer_signal_analysis?.payload;
  const isJobRunning = jobStatus === "RUNNING" || jobStatus === "PENDING";

  // Helper to normalize lookup method
  const normalizeLookupMethod = (method?: string | null): EOCCardProps["searchMethod"] => {
    if (method === "doi") return "doi";
    if (method === "title") return "title";
    if (method === "not_found") return "title";
    if (method === "not_searched") return "not_searched";
    return "unknown";
  };

  // Helper to get main publication EOC card data
  const getMainPublicationEOCData = (): EOCCardProps => {
    const mainArticleResult = eocData?.payload?.main_article_result;
    const eocNotices = mainArticleResult?.notices || [];

    return {
      title: mainArticleResult?.searched_title ?? undefined,
      doi: mainArticleResult?.searched_doi ?? undefined,
      searchMethod: normalizeLookupMethod(mainArticleResult?.lookup_method),
      foundInDatabase: mainArticleResult?.found ?? null,
      errorMessage: mainArticleResult?.found === false ? undefined : (mainArticleResult?.error ?? undefined),
      isLoading: isJobRunning && !mainArticleResult,
      eocNotice: eocNotices[0], // Show first notice in main card
    };
  };

  // Loading state
  if (isJobRunning && !eocData && !pubPeerData) {
    return (
      <div className="space-y-6">
        <Typography variant="h4">{title}</Typography>
        <Card className="border border-border bg-background shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-2">
              {getStatusIcon("LOADING")}
              <Typography variant="body-sm" tone="muted">
                Checking for post-publication notices...
              </Typography>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // No data available
  if (!eocData && !pubPeerData) {
    return (
      <div className="space-y-6">
        <Typography variant="h4">{title}</Typography>
        <Card className="border border-border bg-background shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-2">
              {getStatusIcon("WARNING")}
              <Typography variant="body-sm" tone="muted">
                No post-publication notice data available
              </Typography>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Extract data for summary cards and PubPeer
  const mainArticleResult = eocData?.payload?.main_article_result;
  const eocNotices = mainArticleResult?.notices || [];
  const hasEOC = eocNotices.length > 0;

  const mainPaperResult = pubPeerData?.main_paper_result;
  const scrapedComments = mainPaperResult?.scraped_comments;
  const apiResult = mainPaperResult?.api_result;
  const pubPeerUrl = apiResult?.feedbacks?.[0]?.url;
  const comments = scrapedComments?.comments || [];
  const hasPubPeerComments = comments.length > 0;

  const pubPeerError =
    pubPeerData?.status === "FAILED" || pubPeerData?.error_message || mainPaperResult?.error;

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="space-y-2">
        <Typography variant="h4">{title}</Typography>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4">
        <div
          className={`p-4 rounded bg-background border ${hasEOC ? "border-destructive" : "border-success"} text-center`}
        >
          <Typography variant="h2" weight="strong" className={`${hasEOC ? "text-destructive" : "text-success"} mb-1`}>
            {eocNotices.length}
          </Typography>
          <Typography variant="body-sm" weight="strong" className={hasEOC ? "text-destructive" : "text-success"}>
            EOC/Correction Notices
          </Typography>
        </div>
        <div
          className={`p-4 rounded bg-background border ${hasPubPeerComments ? "border-destructive" : "border-success"} text-center`}
        >
          <Typography variant="h2" weight="strong" className={`${hasPubPeerComments ? "text-destructive" : "text-success"} mb-1`}>
            {comments.length}
          </Typography>
          <Typography variant="body-sm" weight="strong" className={hasPubPeerComments ? "text-destructive" : "text-success"}>
            PubPeer Comments
          </Typography>
        </div>
      </div>

      {/* EOC/Correction Notices Section */}
      <div className="space-y-3">
        <Typography variant="h4">
          Expression of Concern & Correction Notices
        </Typography>
        <EOCCard {...getMainPublicationEOCData()} />
      </div>

      {/* PubPeer Section */}
      <div className="space-y-3">
        <Typography variant="h4">PubPeer Community Comments</Typography>

        {pubPeerError ? (
          <Card className="border border-destructive bg-background shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-center space-x-2">
                {getStatusIcon("FAILED")}
                <Typography variant="body-sm">
                  PubPeer analysis failed
                  {pubPeerData?.error_message ? `: ${pubPeerData.error_message}` : ""}
                </Typography>
              </div>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Comments Section */}
            {hasPubPeerComments ? (
              <div className="space-y-4">
                <Typography variant="h4">
                  Comments ({comments.length})
                </Typography>
                <div className="space-y-4">
                  {comments.map((comment) => {
                    // Find parent author for replies
                    const parentComment =
                      comment.is_reply && comment.reply_to
                        ? comments.find((c) => c.id === comment.reply_to)
                        : null;

                    return (
                      <PubPeerCommentCard
                        key={comment.id}
                        id={comment.id}
                        author={comment.author}
                        date={comment.date}
                        comment={comment.comment}
                        is_reply={comment.is_reply}
                        is_author_response={comment.is_author_response}
                        replyToAuthor={parentComment?.author}
                        links={comment.links}
                      />
                    );
                  })}
                </div>
              </div>
            ) : (
              <Card className="border border-success bg-success/5 shadow-sm">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="h-5 w-5 text-success" />
                      <CardTitle>
                        No PubPeer Comments Found
                      </CardTitle>
                    </div>
                    {pubPeerUrl && (
                      <ExternalLink href={pubPeerUrl} showIcon={true} iconSize={12}>
                        <Typography variant="body-sm" as="span" className="text-info hover:text-info/80">
                          View on PubPeer
                        </Typography>
                      </ExternalLink>
                    )}
                  </div>
                </CardHeader>

                <CardContent className="pt-0">
                  <Typography variant="body-sm" tone="muted">
                    This publication has no comments on PubPeer
                    {pubPeerUrl ? " - verify by visiting the page" : ""}
                  </Typography>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default EOCTabContent;

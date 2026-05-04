"use client";

import { Card, CardContent, CardHeader, CardTitle, Typography } from "@inspect/ui";
import { ExternalLink } from "@/components/ui/external-link";
import type { Check11PubpeerAnalysis, TabContentCommonProps } from "@inspect/api-client";
import type React from "react";
import { getStatusIcon } from "../utils/shared";
import PubPeerCommentCard from "./PubPeerCommentCard";

const PubPeerTabContent: React.FC<TabContentCommonProps & { title: string }> = ({
  results,
  jobStatus,
  title,
}) => {
  const pubPeerData: Check11PubpeerAnalysis | undefined = results?.check_11_pubpeer_analysis;
  const isJobRunning = jobStatus === "RUNNING" || jobStatus === "PENDING";

  // Loading state
  if (isJobRunning && !pubPeerData) {
    return (
      <div className="space-y-6">
        <Typography variant="h4">{title}</Typography>
        <Card className="border border-border bg-background shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-2">
              {getStatusIcon("LOADING")}
              <Typography variant="body-sm" tone="muted">Loading PubPeer analysis...</Typography>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // No data available
  if (!pubPeerData) {
    return (
      <div className="space-y-6">
        <Typography variant="h4">{title}</Typography>
        <Card className="border border-border bg-background shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-2">
              {getStatusIcon("WARNING")}
              <Typography variant="body-sm" tone="muted">No PubPeer data available</Typography>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state when check failed or error surfaced
  if (
    pubPeerData.status === "FAILED" ||
    pubPeerData.error_message ||
    pubPeerData.main_paper_result?.error
  ) {
    return (
      <div className="space-y-6">
        <Typography variant="h4">{title}</Typography>
        <Card className="border border-destructive bg-background shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-center space-x-2">
              {getStatusIcon("FAILED")}
              <Typography variant="body-sm">
                PubPeer analysis failed
                {pubPeerData.error_message ? `: ${pubPeerData.error_message}` : ""}
              </Typography>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Extract comments data
  const mainPaperResult = pubPeerData.main_paper_result;
  const scrapedComments = mainPaperResult?.scraped_comments;
  const apiResult = mainPaperResult?.api_result;
  const pubPeerUrl = apiResult?.feedbacks?.[0]?.url;

  // Get comments from the new structure
  const getComments = () => {
    return scrapedComments?.comments || [];
  };

  const comments = getComments();
  const hasComments = comments.length > 0;

  return (
    <div className="space-y-6">
      <Typography variant="h4">{title}</Typography>

      {/* Comments Section */}
      {hasComments ? (
        <div className="space-y-4">
          <Typography variant="h4">Comments ({comments.length})</Typography>
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
        <Card className="border border-border bg-background shadow-sm">
          <CardHeader className="pb-0">
            <div className="flex items-center justify-between">
              <CardTitle>
                <Typography variant="h4" className="flex items-center gap-2">
                  {getStatusIcon("PASSED")}
                  No Comments Found
                </Typography>
              </CardTitle>
              {pubPeerUrl && (
                <ExternalLink href={pubPeerUrl} showIcon={true} iconSize={12}>
                  <Typography variant="body-sm" className="text-info hover:text-info/80">View on PubPeer</Typography>
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
    </div>
  );
};

export default PubPeerTabContent;

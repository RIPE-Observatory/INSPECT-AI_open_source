"use client";

import { Card, CardContent, CardHeader, CardTitle, Typography } from "@inspect/ui";
import {
  Calendar,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Paperclip,
  Reply,
  User,
  UserPen,
} from "lucide-react";
import type React from "react";
import { useState } from "react";

interface PubPeerCommentCardProps {
  id: number;
  author: string;
  date: string;
  comment: string;
  is_reply: boolean;
  is_author_response: boolean;
  replyToAuthor?: string;
  links?: string[];
}

const PubPeerCommentCard: React.FC<PubPeerCommentCardProps> = ({
  id,
  author,
  date,
  comment,
  is_reply,
  is_author_response,
  replyToAuthor,
  links,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Truncate comment for preview if it's too long
  const MAX_PREVIEW_LENGTH = 280;
  const isLongComment = comment.length > MAX_PREVIEW_LENGTH;
  const previewContent =
    isLongComment && !isExpanded ? `${comment.substring(0, MAX_PREVIEW_LENGTH)}...` : comment;

  return (
    <Card className="border border-border bg-background shadow-sm" data-comment-id={id}>
      {isLongComment ? (
        <CardHeader
          className="pb-3 cursor-pointer hover:bg-surface/40 transition-colors"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-center justify-between">
            <CardTitle>
              <Typography variant="body-sm" weight="strong" className="flex items-center gap-2 flex-wrap">
                <User className="h-4 w-4 text-muted-foreground" />
                <span>{author}</span>
                {date && (
                  <>
                    <Calendar className="h-4 w-4 text-muted-foreground ml-2" />
                    <Typography variant="body-sm" tone="muted" className="inline" as="span">{date}</Typography>
                  </>
                )}
                {is_author_response && (
                  <>
                    <UserPen className="h-4 w-4 text-muted-foreground ml-2" />
                    <Typography variant="body-sm" tone="muted" className="inline" as="span">Author Response</Typography>
                  </>
                )}
                {links && links.length > 0 && (
                  <>
                    <Paperclip className="h-4 w-4 text-muted-foreground ml-2" />
                    <Typography variant="body-sm" tone="muted" className="inline" as="span">{links.length}</Typography>
                  </>
                )}
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
      ) : (
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle>
              <Typography variant="body-sm" weight="strong" className="flex items-center gap-2 flex-wrap">
                <User className="h-4 w-4 text-muted-foreground" />
                <span>{author}</span>
                {date && (
                  <>
                    <Calendar className="h-4 w-4 text-muted-foreground ml-2" />
                    <Typography variant="body-sm" tone="muted" className="inline" as="span">{date}</Typography>
                  </>
                )}
                {is_author_response && (
                  <>
                    <UserPen className="h-4 w-4 text-muted-foreground ml-2" />
                    <Typography variant="body-sm" tone="muted" className="inline" as="span">Author Response</Typography>
                  </>
                )}
                {links && links.length > 0 && (
                  <>
                    <Paperclip className="h-4 w-4 text-muted-foreground ml-2" />
                    <Typography variant="body-sm" tone="muted" className="inline" as="span">{links.length}</Typography>
                  </>
                )}
              </Typography>
            </CardTitle>
          </div>
        </CardHeader>
      )}

      {is_reply && replyToAuthor && (
        <div className="px-6 pb-3 flex items-center gap-2 border-t border-border pt-3">
          <Reply className="h-4 w-4" />
          <Typography variant="body-sm" tone="muted">Replying to {replyToAuthor}</Typography>
        </div>
      )}

      <CardContent className="pt-0">
        <Typography variant="body-sm" className="leading-relaxed whitespace-pre-wrap">
          {previewContent}
        </Typography>

        {/* Links Section - Part of expandable content */}
        {(!isLongComment || isExpanded) && links && links.length > 0 && (
          <div className="mt-4 pt-4 border-t border-border">
            <Typography variant="body-sm" weight="strong" className="mb-3">Links</Typography>
            <div className="space-y-2">
              {links.map((link) => (
                <a
                  key={link}
                  href={link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-info hover:text-info transition-colors group"
                >
                  <ExternalLink className="h-3 w-3 flex-shrink-0" />
                  <Typography variant="body-sm" className="truncate">{link}</Typography>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Show More/Less Button */}
        {isLongComment && !isExpanded && (
          <button
            type="button"
            onClick={() => setIsExpanded(true)}
            className="mt-2 transition-colors"
          >
            <Typography variant="body-sm" className="text-info hover:text-info/80">Show more</Typography>
          </button>
        )}
      </CardContent>
    </Card>
  );
};

export default PubPeerCommentCard;

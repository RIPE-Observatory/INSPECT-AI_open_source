"use client";

import type * as React from "react";
import { Fragment } from "react";

import { typographyVariants } from "@inspect/ui";

import { ExternalLink } from "./external-link";

interface TextWithLinksProps {
  text: string;
  className?: string;
  linkClassName?: string;
  showIcon?: boolean;
  iconSize?: number;
}

/**
 * Component that parses text for URLs and converts them to clickable links
 * Preserves non-URL text as plain text
 */
export const TextWithLinks: React.FC<TextWithLinksProps> = ({
  text,
  className = typographyVariants({ variant: "muted" }),
  linkClassName = typographyVariants({ variant: "small" }),
  showIcon = true,
  iconSize = 12,
}) => {
  // Enhanced regex to capture URLs with query parameters, fragments, and special characters
  // Matches http://, https://, and stops at whitespace or common text delimiters
  const urlRegex = /(https?:\/\/[^\s,;]+)/g;

  // Split text by URLs while keeping the URLs in the result
  const parts = text.split(urlRegex);

  return (
    <span className={className}>
      {parts.map((part) => {
        // Check if this part is a URL
        if (urlRegex.test(part)) {
          // Reset regex lastIndex after test
          urlRegex.lastIndex = 0;

          // Clean up trailing punctuation that might not be part of the URL
          let cleanUrl = part;
          let trailingText = "";

          // Common ending punctuation that's likely not part of the URL
          const endingPunctuation = /[.,:;!?]+$/;
          const match = cleanUrl.match(endingPunctuation);
          if (match) {
            trailingText = match[0];
            cleanUrl = cleanUrl.slice(0, -trailingText.length);
          }

          return (
            <Fragment key={cleanUrl}>
              <ExternalLink
                href={cleanUrl}
                showIcon={showIcon}
                iconSize={iconSize}
                className={linkClassName}
              >
                {cleanUrl}
              </ExternalLink>
              {trailingText}
            </Fragment>
          );
        }

        // Regular text
        return <Fragment key={part}>{part}</Fragment>;
      })}
    </span>
  );
};

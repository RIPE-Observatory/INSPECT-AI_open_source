"use client";

import { useUser } from "@clerk/nextjs";
import { useReviewerProfile } from "@inspect/api-client";
import { Typography } from "@inspect/ui";
import { Loader } from "lucide-react";

export function ProfileGuard({ children }: { children: React.ReactNode }) {
  const { isLoaded } = useUser();
  const { data: reviewer, isLoading, error } = useReviewerProfile();

  if (!isLoaded || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="flex flex-col items-center p-8 border border-border rounded bg-background max-w-md text-center">
          <Loader className="w-8 h-8 text-primary mb-4 animate-spin" />
          <Typography variant="h4" weight="strong" className="text-foreground mb-2">
            Loading INSPECT-AI...
          </Typography>
          <Typography variant="body-sm" tone="muted">
            Please wait while we load the app.
          </Typography>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Typography variant="body-sm" tone="muted" className="text-center">
          We&#39;re unable to load your profile right now.
        </Typography>
      </div>
    );
  }

  if (!reviewer?.onboarding_complete) {
    return null;
  }

  return <>{children}</>;
}

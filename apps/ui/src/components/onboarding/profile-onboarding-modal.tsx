"use client";

import { useUser } from "@clerk/nextjs";
import { useReviewerProfile, useUpdateReviewerProfile } from "@inspect/api-client";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Separator,
} from "@inspect/ui";
import { useEffect, useState } from "react";
import { toast } from "sonner";

type ProfileData = {
  institution: string;
  department: string;
  country: string;
  role: string;
  orcid: string;
};

export function ProfileOnboardingModal() {
  const { user, isLoaded, isSignedIn } = useUser();
  const [authReady, setAuthReady] = useState(false);

  // Wait for auth to be fully ready before fetching reviewer profile
  useEffect(() => {
    if (isLoaded && isSignedIn && user) {
      // Small delay to ensure Clerk token is ready
      const timer = setTimeout(() => setAuthReady(true), 100);
      return () => clearTimeout(timer);
    }
    setAuthReady(false);
  }, [isLoaded, isSignedIn, user]);

  const {
    data: reviewer,
    isLoading: reviewerLoading,
    error: reviewerError,
    refetch: refetchReviewer,
  } = useReviewerProfile({
    enabled: authReady,
    retry: 2, // Retry twice on failure
    retryDelay: 500, // Wait 500ms between retries
  });
  const updateReviewer = useUpdateReviewerProfile();
  const [open, setOpen] = useState(false);

  const [formData, setFormData] = useState<ProfileData>({
    institution: "",
    department: "",
    country: "",
    role: "",
    orcid: "",
  });

  useEffect(() => {
    if (reviewer) {
      setFormData({
        institution: reviewer.affiliation_institution ?? "",
        department: reviewer.affiliation_department ?? "",
        country: reviewer.country ?? "",
        role: reviewer.role ?? "",
        orcid: reviewer.orcid ?? "",
      });
    }
  }, [reviewer]);

  useEffect(() => {
    console.log("[ProfileOnboardingModal] State check:", {
      isLoaded,
      reviewer: reviewer?.clerk_user_id,
      onboarding_complete: reviewer?.onboarding_complete,
      shouldOpen: isLoaded && reviewer && !reviewer.onboarding_complete,
    });
    if (isLoaded && reviewer && !reviewer.onboarding_complete) {
      setOpen(true);
    }
  }, [isLoaded, reviewer]);

  useEffect(() => {
    if (reviewerError) {
      console.error("Error details:", {
        message: reviewerError.message,
        cause: reviewerError.cause,
        stack: reviewerError.stack,
      });
      toast.error("Unable to load your INSPECT-AI profile. Please check console for details.");
    }
  }, [reviewerError]);

  const isSaving = updateReviewer.isPending;

  // Only render when auth is ready and user is signed in
  if (!isLoaded || !isSignedIn || !user) {
    return null;
  }

  // If there's an error loading reviewer, fail silently
  if (reviewerError) {
    return null;
  }

  // Still loading reviewer data
  if (reviewerLoading || !reviewer) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required fields
    if (!formData.institution.trim() || !formData.role.trim()) {
      toast.error("Institution and Role are required");
      return;
    }

    try {
      await updateReviewer.mutateAsync({
        given_name: user.firstName ?? undefined,
        family_name: user.lastName ?? undefined,
        username: user.username ?? undefined,
        email: user.emailAddresses[0]?.emailAddress ?? undefined,
        affiliation_institution: formData.institution.trim(),
        affiliation_department: formData.department.trim() || undefined,
        country: formData.country.trim() || undefined,
        role: formData.role.trim(),
        orcid: formData.orcid.trim() || undefined,
        onboarding_complete: true,
      });

      await refetchReviewer();
      toast.success("Profile completed successfully");
      setOpen(false);
    } catch (error) {

      // Better error handling - show backend validation errors
      if (error instanceof Error) {
        const errorMessage = error.message;
        // Check if it's a validation error from backend
        if (errorMessage.includes("Institution") || errorMessage.includes("Role")) {
          toast.error(errorMessage);
        } else {
          toast.error("Failed to save profile. Please try again.");
        }
      } else {
        toast.error("Failed to save profile. Please try again.");
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !isSaving && setOpen(nextOpen)}>
      <DialogContent
        variant="elevated"
        size="sm"
        showCloseButton={false}
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader className="space-y-3 text-left">
          <DialogTitle>Complete your INSPECT-AI profile</DialogTitle>
          <DialogDescription className="leading-relaxed">
            Include your professional details to establish authorship and attribution for
            assessments.
          </DialogDescription>
        </DialogHeader>
        <Separator variant="default" />

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="institution" size="default" required>
              Institution
            </Label>
            <Input
              id="institution"
              value={formData.institution}
              onChange={(e) => setFormData({ ...formData, institution: e.target.value })}
              required
              inputSize="default"
              variant="default"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="department" size="default">
              Department
            </Label>
            <Input
              id="department"
              value={formData.department}
              onChange={(e) => setFormData({ ...formData, department: e.target.value })}
              inputSize="default"
              variant="default"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="country" size="default">
              Country
            </Label>
            <Input
              id="country"
              value={formData.country}
              onChange={(e) => setFormData({ ...formData, country: e.target.value })}
              inputSize="default"
              variant="default"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role" size="default" required>
              Role
            </Label>
            <Input
              id="role"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              required
              inputSize="default"
              variant="default"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="orcid" size="default">
              ORCID iD
            </Label>
            <Input
              id="orcid"
              value={formData.orcid}
              onChange={(e) => setFormData({ ...formData, orcid: e.target.value })}
              pattern="\d{4}-\d{4}-\d{4}-\d{3}[\dX]"
              inputSize="default"
              variant="default"
            />
          </div>

          <div className="pt-2">
            <Button type="submit" disabled={isSaving} size="lg" className="w-full">
              {isSaving ? "Saving..." : "Save and Continue"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

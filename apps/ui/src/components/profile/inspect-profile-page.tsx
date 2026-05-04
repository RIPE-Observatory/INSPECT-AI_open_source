"use client";

import { useUser } from "@clerk/nextjs";
import { reviewerKeys, useReviewerProfile, useUpdateReviewerProfile } from "@inspect/api-client";
import { Button, Input, Label, Skeleton, Typography } from "@inspect/ui";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";

type ProfileData = {
  institution: string;
  department: string;
  country: string;
  role: string;
  orcid: string;
};

export function InspectProfilePage() {
  const { user } = useUser();
  const queryClient = useQueryClient();
  const { data: reviewer, isLoading, error, refetch: refetchReviewer } = useReviewerProfile();
  const updateReviewer = useUpdateReviewerProfile();

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

  const isSaving = updateReviewer.isPending;

  if (error) {
    return (
      <div className="space-y-6 p-6 pb-8">
        <div className="space-y-4 text-center">
          <Typography variant="body-sm" tone="muted" className="text-destructive">
            We were unable to load your INSPECT-AI profile.
          </Typography>
          <Button variant="outline" size="default" onClick={() => refetchReviewer()}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  if (isLoading || !reviewer) {
    return (
      <div className="space-y-6 p-6 pb-8">
        <div className="space-y-3">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-full" />
          <div className="space-y-4 pt-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) return;

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
        onboarding_complete: reviewer.onboarding_complete,
      });
      await queryClient.invalidateQueries({ queryKey: reviewerKeys.root() });
      toast.success("Profile updated successfully");
    } catch (error) {

      // Better error handling
      if (error instanceof Error) {
        const errorMessage = error.message;
        if (errorMessage.includes("Institution") || errorMessage.includes("Role")) {
          toast.error(errorMessage);
        } else {
          toast.error("Failed to update profile. Please try again.");
        }
      } else {
        toast.error("Failed to update profile. Please try again.");
      }
    }
  };

  return (
    <div className="space-y-6 p-6 pb-8">
      <div className="space-y-2">
        <Typography variant="h3">INSPECT-AI Profile</Typography>
        <Typography variant="body-sm" tone="muted">Keep your affiliation and role details up to date.</Typography>
      </div>

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
            {isSaving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </form>
    </div>
  );
}

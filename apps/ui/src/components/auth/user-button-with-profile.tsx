"use client";

import { InspectProfilePage } from "@/components/profile/inspect-profile-page";
import { UserButton } from "@clerk/nextjs";
import { Settings2 } from "lucide-react";

export function UserButtonWithProfile() {
  return (
    <UserButton appearance={{ elements: { avatarBox: "h-8 w-8" } }}>
      <UserButton.UserProfilePage
        label="INSPECT-AI Profile"
        labelIcon={<Settings2 className="h-4 w-4" />}
        url="inspect-profile"
      >
        <InspectProfilePage />
      </UserButton.UserProfilePage>
    </UserButton>
  );
}

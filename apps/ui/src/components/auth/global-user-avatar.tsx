"use client";

import { SignedIn } from "@clerk/nextjs";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { UserButtonWithProfile } from "./user-button-with-profile";

export function GlobalUserAvatar() {
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  // Hide on job results pages (e.g., /jobs/abc-123)
  if (pathname?.match(/^\/jobs\/[^/]+$/)) {
    return null;
  }

  return (
    <SignedIn>
      <div className="fixed top-0 right-8 z-50 h-[60px] flex items-center" suppressHydrationWarning>
        <UserButtonWithProfile />
      </div>
    </SignedIn>
  );
}

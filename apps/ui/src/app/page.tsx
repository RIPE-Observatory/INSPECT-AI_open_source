"use client";

import { SignedIn, SignedOut, useUser } from "@clerk/nextjs";
import { LogIn, UserPlus, Zap } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppFooter } from "@/components/layout/page";
import { AuroraBackground } from "@/components/ui/shadcn-io/aurora-background";
import { AuroraErrorBoundary } from "@/components/ui/shadcn-io/aurora-background/error-boundary";
import { Button, Card, CardContent, Typography } from "@inspect/ui";

export default function LandingPage() {
  const { user } = useUser();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleAnalyzeClick = () => {
    window.open("/analyze", "_blank", "noopener,noreferrer");
  };

  return (
    <main className="flex min-h-screen flex-col">
      {/* Skip link for keyboard navigation accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[60] focus:rounded focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
      >
        Skip to main content
      </a>
      <AuroraErrorBoundary>
        <AuroraBackground className="flex flex-1 justify-start pt-20">
          <div id="main-content" className="container mx-auto flex w-full flex-col items-center gap-12 px-6 text-center">
          {/* Icon + Wordmark */}
          <div
            className="flex flex-row items-center gap-6 animate-fade-right animation-delay-100"
            role="img"
            aria-label="INSPECT-AI"
          >
            <div className="relative">
              <div className="absolute inset-0 bg-primary/20 blur-3xl rounded" />
              <Image
                src="/icon48.svg"
                alt=""
                width={64}
                height={64}
                priority
                className="relative z-10"
              />
            </div>
            <Typography variant="h1">
              INSPECT-AI
            </Typography>
          </div>

          {/* Subtitle - Acronym Expansion */}
          <Typography
            variant="lead"
            className="max-w-4xl animate-fade-up animation-delay-250"
          >
            <span className="text-highlight">I</span>
            <span className="text-highlight">N</span>
            <span>ve</span>
            <span className="text-highlight">S</span>
            <span>tigating </span>
            <span className="text-highlight">P</span>
            <span>robl</span>
            <span className="text-highlight">E</span>
            <span>matic </span>
            <span className="text-highlight">C</span>
            <span>linical </span>
            <span className="text-highlight">T</span>
            <span>rials with </span>
            <span className="text-highlight">A</span>
            <span className="text-highlight">I</span>
          </Typography>

          {mounted && (
            <>
              <SignedIn>
                {/* Welcome Message */}
                <div className="animate-fade-right animation-delay-350">
                  <Typography variant="h3">
                    Start investigating,{" "}
                    <span className="text-highlight">
                      {user?.firstName || user?.username || "there"}
                    </span>
                  </Typography>
                </div>

                {/* Description */}
                <Typography
                  variant="body-md"
                  tone="muted"
                  className="max-w-2xl animate-fade-up animation-delay-450"
                >
                  Upload clinical trial PDFs to run automated integrity checks against INSPECT-SR tool.
                </Typography>

                {/* Action Buttons */}
                <div
                  className="flex w-full max-w-md flex-col gap-4 animate-fade-up animation-delay-600"
                >
                  <Button
                    variant="default"
                    size="lg"
                    onClick={handleAnalyzeClick}
                    className="w-full"
                  >
                    <Zap className="h-5 w-5" />
                    Start INSPECT-AI
                  </Button>
                  {/* Temporarily disabled for beta */}
                  {/* <Button
                    variant="surface"
                    size="lg"
                    onClick={handleChecklistClick}
                    className="w-full"
                  >
                    <CheckSquare className="h-5 w-5 text-success" />
                    Open INSPECT-SR Tool
                  </Button> */}
                </div>
              </SignedIn>

              <SignedOut>
                {/* Sign Up/Sign In Card */}
                <Card
                  variant="elevated"
                  className="w-full max-w-md text-center animate-fade-scale animation-delay-450"
                >
                  <CardContent className="p-8 space-y-6">
                    <div className="space-y-4">
                      <Typography variant="h3">Get Started</Typography>
                      <Typography variant="body-md" tone="muted">
                        Sign up to start analyzing clinical trials with automated checks for
                        integrity concerns.
                      </Typography>
                    </div>
                    <div className="flex flex-col gap-3">
                      <Link href="/sign-up" className="w-full">
                        <Button
                          variant="default"
                          size="lg"
                          className="w-full"
                        >
                          <UserPlus className="h-4 w-4" />
                          Create Account
                        </Button>
                      </Link>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 border-t border-border/70" />
                        <Typography variant="body-sm" tone="muted">
                          Already have an account?
                        </Typography>
                        <div className="flex-1 border-t border-border/70" />
                      </div>
                      <Link href="/sign-in" className="w-full">
                        <Button
                          variant="outline"
                          size="lg"
                          className="w-full"
                        >
                          <LogIn className="h-4 w-4" />
                          Sign In
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              </SignedOut>
            </>
          )}
          </div>
        </AuroraBackground>
      </AuroraErrorBoundary>

      <AppFooter />
    </main>
  );
}

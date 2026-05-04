import { GlobalUserAvatar } from "@/components/auth/global-user-avatar";
import { ProfileOnboardingModal } from "@/components/onboarding/profile-onboarding-modal";
import { QueryProvider } from "@/components/query-client-provider";
import { ThemeProvider } from "@/components/theme-provider";
import { ClerkProvider } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import type { Metadata } from "next";
import Script from "next/script";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "INSPECT-AI - Clinical Trial Document Analysis",
  description: "Your Assistant for Integrity checks on clinical trial documents.",
  icons: {
    icon: [
      { url: "/icon16.svg", sizes: "16x16", type: "image/svg+xml" },
      { url: "/icon32.svg", sizes: "32x32", type: "image/svg+xml" },
      { url: "/icon48.svg", sizes: "48x48", type: "image/svg+xml" },
    ],
    apple: [{ url: "/icon128.svg", sizes: "128x128", type: "image/svg+xml" }],
    other: [
      {
        rel: "icon",
        url: "/icon64.svg",
        sizes: "64x64",
        type: "image/svg+xml",
      },
    ],
  },
};

const clerkAppearance = {
  baseTheme: dark,
  variables: {
    fontFamily: "var(--font-sans)",
    colorPrimary: "var(--color-primary)",
    colorBackground: "var(--color-background)",
  },
  elements: {
    userButtonPopoverCard:
      "bg-card/95 backdrop-blur-md border border-border/70 shadow-[var(--shadow-base-md)] rounded min-w-[220px]",
    userButtonPopoverFooter: "hidden",
  },
} as const;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider appearance={clerkAppearance}>
      <html lang="en" className="dark" suppressHydrationWarning>
        <body className={`${GeistSans.variable} ${GeistMono.variable} antialiased`}>
          <ThemeProvider
            attribute="class"
            defaultTheme="dark"
            enableSystem={false}
            forcedTheme="dark"
            disableTransitionOnChange
          >
            <QueryProvider>
              <GlobalUserAvatar />
              {children}
              <ProfileOnboardingModal />
              <Toaster />
            </QueryProvider>
          </ThemeProvider>
          <Script src="https://tally.so/widgets/embed.js" strategy="lazyOnload" />
        </body>
      </html>
    </ClerkProvider>
  );
}

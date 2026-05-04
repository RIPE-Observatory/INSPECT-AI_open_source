// This file configures the initialization of Sentry on the client and PostHog instrumentation.
// The added config here will be used whenever a user loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/
// https://posthog.com/docs/integrations/js-integration

import * as Sentry from "@sentry/nextjs";
import posthog from "posthog-js";

Sentry.init({
  dsn: "https://00742cb02b8cd24dab2008470dd7b71d@o4509100960448512.ingest.de.sentry.io/4510268716286032",

  // Track 10% of requests (enough for 15 beta users)
  tracesSampleRate: 0.1,

  // Don't send console logs or PII
  enableLogs: false,
  sendDefaultPii: false,

  environment: process.env.NODE_ENV,

  // Remove sensitive data from browser errors
  beforeSend(event) {
    // Remove user identifiable info
    if (event.user) {
      delete event.user.email;
      delete event.user.username;
      delete event.user.ip_address;
    }

    // Remove cookies and auth headers
    if (event.request) {
      delete event.request.cookies;
      if (event.request.headers) {
        delete event.request.headers.Authorization;
        delete event.request.headers.Cookie;
      }
    }

    return event;
  },
});

// Initialize PostHog with privacy-safe anonymous tracking (only if key is configured)
if (process.env.NEXT_PUBLIC_POSTHOG_KEY) {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
    api_host: "/ph-metrics",  // Using unique path instead of /ingest to bypass ad blockers
    ui_host: "https://eu.posthog.com",

    // Privacy-focused settings - ONLY official documented options
    autocapture: true,
    capture_pageview: true,
    capture_pageleave: false,

    // Disable session recording completely
    disable_session_recording: true,

    // Disable heatmaps
    enable_heatmaps: false,

    // Keep exception tracking (errors without PII)
    capture_exceptions: true,

    // Don't create user profiles - fully anonymous
    person_profiles: 'identified_only',

    // Debug in development only
    debug: process.env.NODE_ENV === "development",
  });
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
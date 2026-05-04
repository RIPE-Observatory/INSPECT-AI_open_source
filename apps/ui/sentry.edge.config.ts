// This file configures the initialization of Sentry for edge features (middleware, edge routes, and so on).
// The config you add here will be used whenever one of the edge features is loaded.
// Note that this config is unrelated to the Vercel Edge Runtime and is also required when running locally.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://00742cb02b8cd24dab2008470dd7b71d@o4509100960448512.ingest.de.sentry.io/4510268716286032",

  // Track 10% of requests
  tracesSampleRate: 0.1,

  // Don't send console logs or PII
  enableLogs: false,
  sendDefaultPii: false,

  environment: process.env.NODE_ENV,
});

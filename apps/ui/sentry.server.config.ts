// This file configures the initialization of Sentry on the server.
// The config you add here will be used whenever the server handles a request.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://00742cb02b8cd24dab2008470dd7b71d@o4509100960448512.ingest.de.sentry.io/4510268716286032",

  // Track 10% of requests (enough for 15 beta users)
  tracesSampleRate: 0.1,

  // Don't send console logs (may contain sensitive data)
  enableLogs: false,

  // Don't send user PII (emails, IPs, etc.)
  sendDefaultPii: false,

  environment: process.env.NODE_ENV,

  // Remove sensitive data from errors
  beforeSend(event) {
    if (event.request?.headers) {
      delete event.request.headers.Authorization;
      delete event.request.headers.Cookie;
    }
    if (event.user) {
      delete event.user.email;
      delete event.user.username;
      delete event.user.ip_address;
    }
    return event;
  },
});

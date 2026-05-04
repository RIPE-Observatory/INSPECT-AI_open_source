import ky, { type Options } from "ky";

const DEFAULT_API_BASE_URL = "/api/internal";

export function resolveApiBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.INSPECT_API_URL ?? DEFAULT_API_BASE_URL
  );
}

export function createApiClient(options?: Options) {
  return ky.create({
    prefixUrl: resolveApiBaseUrl(),
    timeout: 30_000,
    retry: {
      limit: 2,                    // Retry up to 2 times (3 total attempts)
      methods: ["put", "post"],    // Retry mutations (saves)
      statusCodes: [408, 429, 500, 502, 503, 504], // Retry on timeout/server errors
      backoffLimit: 3000,          // Max 3s between retries
    },
    hooks: {
      beforeRequest: [
        (request) => {
          request.headers.set("Accept", "application/json");
        },
      ],
      afterResponse: [
        async (request, _options, response) => {
          // Log errors for debugging
          if (!response.ok) {
            const contentType = response.headers.get("content-type");
            if (contentType?.includes("text/html")) {
              console.error("API returned HTML instead of JSON:", {
                url: request.url,
                status: response.status,
                statusText: response.statusText,
              });
            }
          }
          return response;
        },
      ],
    },
    ...options,
  });
}

export const apiClient = createApiClient();

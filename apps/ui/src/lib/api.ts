const DEFAULT_API_BASE_URL = "http://localhost:8000";

export function getServerApiBaseUrl() {
  return (
    process.env.INSPECT_API_URL ??
    process.env.BACKEND_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    DEFAULT_API_BASE_URL
  );
}

export function getServerApiV1BaseUrl() {
  const base = getServerApiBaseUrl().replace(/\/$/, "");
  if (base.endsWith("/api") || base.endsWith("/api/v1")) {
    return base.endsWith("/api/v1") ? base : `${base}/v1`;
  }
  return `${base}/api/v1`;
}

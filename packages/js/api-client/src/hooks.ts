import {
  QueryClient,
  type QueryClientConfig,
  type UseMutationOptions,
  type UseMutationResult,
  type UseQueryOptions,
  type UseQueryResult,
  queryOptions,
  useMutation,
  useQuery,
} from "@tanstack/react-query";

import { apiClient } from "./client";
import type {
  InspectSRGetResponse,
  InspectSRProgressResponse,
  InspectSRPutRequest,
  InspectSRPutResponse,
  JobCreateResponse,
  JobResults,
  JobStatusResponse,
  ReviewerProfileRequest,
  ReviewerProfileResponse,
} from "./types";

export const jobKeys = {
  root: () => ["jobs"] as const,
  analyze: () => [...jobKeys.root(), "analyze"] as const,
  status: (jobId: string) => [...jobKeys.root(), jobId, "status"] as const,
  inspectSR: (jobId: string) => [...jobKeys.root(), jobId, "inspect-sr"] as const,
  inspectSRProgress: (jobId: string) => [...jobKeys.inspectSR(jobId), "progress"] as const,
};

export const reviewerKeys = {
  root: () => ["reviewer"] as const,
};

function transformJobResults(rawResults: unknown): JobResults | null {
  if (!rawResults || typeof rawResults !== "object" || !("checks" in rawResults)) {
    return rawResults as JobResults | null;
  }

  // biome-ignore lint/suspicious/noExplicitAny: Raw results from API need dynamic access
  const typedResults = rawResults as any;

  return {
    inspect_sr: typedResults.inspect_sr,
    grobid_metadata: typedResults.grobid_metadata,
    // New normalized checks structure - all components use this now
    checks: typedResults.checks,
  };
}

export type JobStatusQueryKey = ReturnType<typeof jobKeys.status>;

export type JobStatusQueryOverrides = Omit<
  UseQueryOptions<JobStatusResponse, Error, JobStatusResponse, JobStatusQueryKey>,
  "queryKey" | "queryFn"
>;

export const jobStatusQueryOptions = (jobId: string, overrides?: JobStatusQueryOverrides) =>
  queryOptions<JobStatusResponse, Error, JobStatusResponse, JobStatusQueryKey>({
    queryKey: jobKeys.status(jobId),
    queryFn: async () => {
      const response = await apiClient.get(`jobs/${jobId}/status`).json<JobStatusResponse>();

      if (response.results) {
        response.results = transformJobResults(response.results);
      }

      return response;
    },
    enabled: Boolean(jobId),
    refetchInterval: 5000,
    refetchOnWindowFocus: false,
    ...overrides,
  });

export function useJobStatus(
  jobId: string,
  options?: JobStatusQueryOverrides,
): UseQueryResult<JobStatusResponse, Error> {
  return useQuery(jobStatusQueryOptions(jobId, options));
}

export type ReviewerQueryKey = ReturnType<typeof reviewerKeys.root>;

export type ReviewerQueryOverrides = Omit<
  UseQueryOptions<ReviewerProfileResponse, Error, ReviewerProfileResponse, ReviewerQueryKey>,
  "queryKey" | "queryFn"
>;

export const reviewerProfileQueryOptions = (overrides?: ReviewerQueryOverrides) =>
  queryOptions<ReviewerProfileResponse, Error, ReviewerProfileResponse, ReviewerQueryKey>({
    queryKey: reviewerKeys.root(),
    queryFn: async () => {
      const response = await apiClient.get("reviewers/me").json<ReviewerProfileResponse>();
      return response;
    },
    refetchOnWindowFocus: false,
    retry: false,
    ...overrides,
  });

export function useReviewerProfile(
  options?: ReviewerQueryOverrides,
): UseQueryResult<ReviewerProfileResponse, Error> {
  return useQuery(reviewerProfileQueryOptions(options));
}

export type InspectSRQueryKey = ReturnType<typeof jobKeys.inspectSR>;

export type InspectSRQueryOverrides = Omit<
  UseQueryOptions<InspectSRGetResponse, Error, InspectSRGetResponse, InspectSRQueryKey>,
  "queryKey" | "queryFn"
>;

export const inspectSRQueryOptions = (jobId: string, overrides?: InspectSRQueryOverrides) =>
  queryOptions<InspectSRGetResponse, Error, InspectSRGetResponse, InspectSRQueryKey>({
    queryKey: jobKeys.inspectSR(jobId),
    queryFn: async () => {
      const response = await apiClient.get(`jobs/${jobId}/inspect-sr`).json<InspectSRGetResponse>();
      return response;
    },
    enabled: Boolean(jobId),
    refetchOnWindowFocus: false,
    ...overrides,
  });

export function useInspectSR(
  jobId: string,
  options?: InspectSRQueryOverrides,
): UseQueryResult<InspectSRGetResponse, Error> {
  return useQuery(inspectSRQueryOptions(jobId, options));
}

export type InspectSRProgressQueryKey = ReturnType<typeof jobKeys.inspectSRProgress>;

export type InspectSRProgressQueryOverrides = Omit<
  UseQueryOptions<
    InspectSRProgressResponse,
    Error,
    InspectSRProgressResponse,
    InspectSRProgressQueryKey
  >,
  "queryKey" | "queryFn"
>;

export const inspectSRProgressQueryOptions = (
  jobId: string,
  overrides?: InspectSRProgressQueryOverrides,
) =>
  queryOptions<
    InspectSRProgressResponse,
    Error,
    InspectSRProgressResponse,
    InspectSRProgressQueryKey
  >({
    queryKey: jobKeys.inspectSRProgress(jobId),
    queryFn: async () => {
      const response = await apiClient
        .get(`jobs/${jobId}/inspect-sr/progress`)
        .json<InspectSRProgressResponse>();
      return response;
    },
    enabled: Boolean(jobId),
    refetchOnWindowFocus: false,
    ...overrides,
  });

export function useInspectSRProgress(
  jobId: string,
  options?: InspectSRProgressQueryOverrides,
): UseQueryResult<InspectSRProgressResponse, Error> {
  return useQuery(inspectSRProgressQueryOptions(jobId, options));
}

export type InspectSRMutationVariables = InspectSRPutRequest;

export function useUpdateInspectSR(
  jobId: string,
  options?: UseMutationOptions<InspectSRPutResponse, Error, InspectSRMutationVariables>,
): UseMutationResult<InspectSRPutResponse, Error, InspectSRMutationVariables> {
  return useMutation({
    mutationKey: [...jobKeys.inspectSR(jobId), "update"],
    mutationFn: async (payload) => {
      const response = await apiClient
        .put(`jobs/${jobId}/inspect-sr`, {
          json: payload,
        })
        .json<InspectSRPutResponse>();
      return response;
    },
    ...options,
  });
}

export function useAnalyzeDocument(
  options?: UseMutationOptions<JobCreateResponse, Error, FormData>,
): UseMutationResult<JobCreateResponse, Error, FormData> {
  return useMutation({
    mutationKey: jobKeys.analyze(),
    mutationFn: async (formData: FormData) => {
      const response = await apiClient
        .post("analyze", {
          body: formData,
        })
        .json<JobCreateResponse>();
      return response;
    },
    ...options,
  });
}

export function useUpdateReviewerProfile(
  options?: UseMutationOptions<ReviewerProfileResponse, Error, ReviewerProfileRequest>,
): UseMutationResult<ReviewerProfileResponse, Error, ReviewerProfileRequest> {
  return useMutation({
    mutationKey: [...reviewerKeys.root(), "update"],
    mutationFn: async (payload) => {
      const response = await apiClient
        .put("reviewers/me", {
          json: payload,
        })
        .json<ReviewerProfileResponse>();
      return response;
    },
    ...options,
  });
}

export function createQueryClient(config?: QueryClientConfig) {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: 2,
      },
      mutations: {
        retry: 0,
      },
    },
    ...config,
  });
}

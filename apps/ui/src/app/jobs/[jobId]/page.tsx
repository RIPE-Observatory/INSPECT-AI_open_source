import { HydrationBoundary, dehydrate } from "@tanstack/react-query";

import { createQueryClient, jobStatusQueryOptions } from "@inspect/api-client";

import JobResultsClient from "./JobResultsClient";

type PageProps = {
  params: Promise<{ jobId: string }>;
};

export const dynamic = "force-dynamic";

export default async function JobResultsPage({ params }: PageProps) {
  const { jobId } = await params;
  const queryClient = createQueryClient();

  if (jobId) {
    try {
      await queryClient.prefetchQuery(jobStatusQueryOptions(jobId));
    } catch {
      // Intentionally ignored
    }
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <JobResultsClient jobId={jobId} />
    </HydrationBoundary>
  );
}

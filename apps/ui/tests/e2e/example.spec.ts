import { test, expect } from "@playwright/test";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000/api/v1";

async function waitForJobStatus(jobId: string, timeoutMs = 120000): Promise<any> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/status`);
    const json = await response.json();
    if (json.status === "COMPLETED" || json.status === "FAILED") {
      return json;
    }
    await new Promise((resolve) => setTimeout(resolve, 3000));
  }
  throw new Error("Timeout waiting for job completion");
}

test("user can submit a job and see completion status", async ({ page }) => {
  await page.goto("http://localhost:3000");

  const analyzeButton = page.getByRole("button", { name: /analyze/i });
  await expect(analyzeButton).toBeVisible();

  const fileChooserPromise = page.waitForEvent("filechooser");
  await analyzeButton.click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles("tmp/pdf_storage/Efect of post-isometric relaxation.pdf");

  const jobResponse = await page.waitForResponse((response) =>
    response.url().includes("/api/v1/analyze") && response.request().method() === "POST"
  );
  const jobJson = await jobResponse.json();

  const jobId = jobJson.job_id as string;
  expect(jobId).toBeTruthy();

  const result = await waitForJobStatus(jobId);
  expect(result.status).toBe("COMPLETED");
});

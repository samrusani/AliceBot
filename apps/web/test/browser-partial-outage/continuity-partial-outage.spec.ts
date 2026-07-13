import { expect, test } from "@playwright/test";

test("live queue provenance keeps correction safe during a detail-only outage", async ({ page }) => {
  await page.goto("/continuity");
  await expect(page.getByRole("heading", { level: 1, name: "Continuity workspace" })).toBeVisible();
  await expect(page.getByText("Live review queue")).toBeVisible();
  await expect(page.getByText("Live target · detail unavailable")).toBeVisible();
  await expect(page.getByText(/detail history intentionally unavailable/i)).toBeVisible();

  const correction = page.getByRole("button", { name: "Apply correction" });
  await expect(correction).toBeEnabled();
  await page.getByLabel("Reason (optional)").fill("Queue-proven target");

  const correctionRequest = page.waitForRequest(
    (request) =>
      request.method() === "POST" &&
      request.url().includes("/v0/continuity/review-queue/object-live-detail-outage/corrections"),
  );
  await correction.click();
  const request = await correctionRequest;

  expect(request.url()).not.toContain("review-fixture");
  expect(request.postDataJSON()).toMatchObject({
    user_id: "99999999-9999-4999-8999-999999999999",
    action: "confirm",
    reason: "Queue-proven target",
  });
});

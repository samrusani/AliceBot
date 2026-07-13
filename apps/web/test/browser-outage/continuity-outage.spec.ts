import { expect, test } from "@playwright/test";

test("configured-live outages keep fallback continuity objects non-actionable across navigation", async ({
  page,
}) => {
  const mutationRequests: string[] = [];
  page.on("request", (request) => {
    if (
      request.method() !== "GET" &&
      (request.url().includes("/v0/continuity/open-loops/") ||
        request.url().includes("/v0/continuity/review-queue/"))
    ) {
      mutationRequests.push(`${request.method()} ${request.url()}`);
    }
  });

  await page.goto("/continuity");
  await expect(page.getByRole("heading", { level: 1, name: "Continuity workspace" })).toBeVisible();
  await expect(page.getByText("Open-loop dashboard unavailable")).toBeVisible();
  await expect(page.getByText("Review queue unavailable")).toBeVisible();
  await expect(page.getByText("Correction unavailable")).toBeVisible();

  const done = page.getByRole("button", { name: "Done" }).first();
  const correction = page.getByRole("button", { name: "Apply correction" });
  await expect(done).toBeDisabled();
  await expect(correction).toBeDisabled();
  await done.evaluate((button) => (button as HTMLButtonElement).click());
  await correction.evaluate((button) => (button as HTMLButtonElement).click());

  await page.getByRole("link", { name: "Selected" }).last().click();
  await expect(page).toHaveURL(/review_object=review-fixture-1/);
  await expect(page.getByRole("button", { name: "Done" }).first()).toBeDisabled();
  await expect(page.getByRole("button", { name: "Apply correction" })).toBeDisabled();
  expect(mutationRequests).toEqual([]);
});

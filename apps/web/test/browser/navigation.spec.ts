import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const routes = [
  { path: "/", heading: "Operator shell for governed work" },
  { path: "/chat", heading: "Chat with the assistant or route a governed request" },
  { path: "/continuity", heading: "Continuity workspace" },
  { path: "/vnext", heading: "True second-brain workspace" },
  { path: "/approvals", heading: "Approval inbox and review" },
  { path: "/gmail", heading: "Gmail account review workspace" },
];

test("navigates through the operator shell with current-page semantics", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1, name: routes[0].heading })).toBeVisible();
  await page.getByRole("link", { name: /Requests Compose bounded operator requests/ }).first().click();
  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.getByRole("heading", { level: 1, name: routes[1].heading })).toBeVisible();
  await expect(page.getByRole("link", { name: /Requests Compose bounded operator requests/ }).first()).toHaveAttribute(
    "aria-current",
    "page",
  );

  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  await page.goForward();
  await expect(page).toHaveURL(/\/chat$/);
});

test("resets assistant and governed-request drafts when the selected thread changes", async ({ page }) => {
  await page.goto("/chat?demo=fixture");
  const assistantDraft = page.getByLabel("Ask the assistant");
  await assistantDraft.fill("draft scoped to magnesium");
  await page.getByRole("link", { name: /Vitamin D reorder follow-up/ }).click();
  await expect(page).toHaveURL(/thread=11111111-1111-4111-8111-111111111112/);
  await expect(page.getByLabel("Ask the assistant")).toHaveValue("");

  await page.getByRole("link", { name: /Submit a governed request/ }).click();
  await page.getByLabel("Action").fill("draft_action");
  await page.getByRole("link", { name: /Quarterly routine cleanup/ }).click();
  await expect(page).toHaveURL(/thread=11111111-1111-4111-8111-111111111113/);
  await expect(page.getByLabel("Action")).toHaveValue("place_order");
});

for (const route of routes) {
  test(`${route.path} has no serious accessibility violations`, async ({ page }) => {
    await page.goto(route.path);
    await expect(page.getByRole("heading", { level: 1, name: route.heading })).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const reportable = results.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );

    expect(reportable, JSON.stringify(reportable, null, 2)).toEqual([]);
  });
}

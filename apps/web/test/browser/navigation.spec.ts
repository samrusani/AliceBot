import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const routes = [
  { path: "/", heading: "Continuity and memory review console" },
  { path: "/vnext", heading: "True second-brain workspace" },
  { path: "/artifacts", heading: "Artifact review workspace" },
  { path: "/memories", heading: "Memory review workspace" },
  { path: "/continuity", heading: "Continuity workspace" },
  { path: "/entities", heading: "Entity review workspace" },
  { path: "/traces", heading: "Trace and explain-why review" },
];

const unavailableByDefault = [
  "/admin",
  "/chat",
  "/chief-of-staff",
  "/onboarding",
  "/settings",
  "/approvals",
  "/tasks",
  "/gmail",
  "/calendar",
];

test("navigates through the seven-view continuity console", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1, name: routes[0].heading })).toBeVisible();
  await page.getByRole("link", { name: /Continuity Capture, recall/ }).first().click();
  await expect(page).toHaveURL(/\/continuity$/);
  await expect(page.getByRole("heading", { level: 1, name: routes[4].heading })).toBeVisible();
  await expect(page.getByRole("link", { name: /Continuity Capture, recall/ }).first()).toHaveAttribute(
    "aria-current",
    "page",
  );

  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  await page.goForward();
  await expect(page).toHaveURL(/\/continuity$/);
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

for (const path of unavailableByDefault) {
  test(`${path} is not mounted by default`, async ({ request }) => {
    const response = await request.get(path);
    expect(response.status()).toBe(404);
  });
}

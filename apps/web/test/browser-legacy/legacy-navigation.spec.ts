import { expect, test } from "@playwright/test";

const legacyRoutes = [
  { path: "/approvals", heading: "Approval inbox and review" },
  { path: "/tasks", heading: "Task lifecycle inspection" },
  { path: "/gmail", heading: "Gmail account review workspace" },
  { path: "/calendar", heading: "Calendar account review workspace" },
];

test("mounts all four legacy views only for the exact server flag", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.getByText("Legacy surfaces enabled").first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Approvals Legacy approval queue/ }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Calendar Legacy manual account/ }).first()).toBeVisible();

  for (const route of legacyRoutes) {
    const response = await request.get(route.path);
    expect(response.status(), route.path).toBe(200);
    await page.goto(route.path);
    await expect(page.getByRole("heading", { level: 1, name: route.heading })).toBeVisible();
  }
});

import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { buildBrowserClipperBookmarklet } from "../../components/vnext-workspace-model";

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

test("browser clipper uses an opaque CORS-safelisted one-time-capability transport", async ({ page }) => {
  const captureEndpoint = "http://127.0.0.1:3200/v0/vnext/connectors/browser-clipper/capture";
  const capability = "alice_clip_playwright_one_time_secret";
  const requests: Array<{ method: string; body: string | null; headers: Record<string, string> }> = [];
  const dialogs: Array<{ type: string; message: string }> = [];

  await page.route(captureEndpoint, async (route) => {
    requests.push({
      method: route.request().method(),
      body: route.request().postData(),
      headers: await route.request().allHeaders(),
    });
    await route.fulfill({ status: 503, body: "unavailable" });
  });
  page.on("dialog", async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    if (dialog.type() === "prompt") {
      await dialog.accept("Source note from the visited page");
      return;
    }
    await dialog.accept();
  });

  await page.goto("/");
  await page.setContent(`
    <main>
      <h1>Untrusted article</h1>
      <p>The page body is untrusted input.</p>
      <a id="alice-clip" href="#">Clip once</a>
    </main>
  `);
  const bookmarklet = buildBrowserClipperBookmarklet({
    endpoint: captureEndpoint,
    userId: "user-1",
    capability,
    origin: "http://127.0.0.1:3100",
    domain: "professional",
    sensitivity: "private",
  });
  await page.locator("#alice-clip").evaluate((element, href) => element.setAttribute("href", href), bookmarklet);
  await page.locator("#alice-clip").click();

  await expect.poll(() => requests.length).toBe(1);
  await expect.poll(() => dialogs.length).toBe(2);
  const capture = JSON.parse(requests[0].body ?? "null");
  expect(capture).toEqual(
    expect.objectContaining({
      user_id: "user-1",
      url: "http://127.0.0.1:3100/",
      title: "",
      capture_capability: capability,
      user_note: "Source note from the visited page",
      domain: "professional",
      sensitivity: "private",
    }),
  );
  expect(capture).not.toHaveProperty("capture_token");
  expect(requests[0].method).toBe("POST");
  expect(requests[0].headers["content-type"]?.toLowerCase()).toBe("text/plain;charset=utf-8");
  expect(requests[0].headers.authorization).toBeUndefined();
  expect(dialogs).toEqual([
    { type: "prompt", message: "Optional note" },
    { type: "alert", message: "Alice clip request submitted. Verify it in the Alice Inbox." },
  ]);
});

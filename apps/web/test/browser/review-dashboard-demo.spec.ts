import { expect, test } from "@playwright/test";

test("review dashboard fixture stays truthful and read-only at the redaction boundary", async ({
  page,
}) => {
  await page.goto("/memories");

  await expect(page.getByRole("heading", { level: 1, name: "Memory review workspace" })).toBeVisible();
  await expect(page.getByRole("link", { name: /user\.preference\.merchant\.supplements/ })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.getByRole("button", { name: /redact/i })).toHaveCount(0);
  await expect(page.locator('a[href^="/traces?trace="]')).toHaveCount(0);
});

test("review dashboard columns align mechanically without stretching the shell", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/memories");

  const shellTopbar = await page.locator(".shell-topbar").boundingBox();
  const shellMain = await page.locator(".shell-main").boundingBox();
  expect(shellTopbar).not.toBeNull();
  expect(shellMain).not.toBeNull();
  expect(Math.abs((shellMain?.y ?? 0) - ((shellTopbar?.y ?? 0) + (shellTopbar?.height ?? 0)) - 22)).toBeLessThanOrEqual(1);

  const memoryCards = page.locator(".memory-layout > .section-card");
  await expect(memoryCards).toHaveCount(2);
  const memoryList = memoryCards.nth(0);
  const memoryDetail = memoryCards.nth(1);
  const [listBox, detailBox] = await Promise.all([memoryList.boundingBox(), memoryDetail.boundingBox()]);
  expect(listBox).not.toBeNull();
  expect(detailBox).not.toBeNull();
  expect(Math.abs((listBox?.y ?? 0) - (detailBox?.y ?? 0))).toBeLessThanOrEqual(1);

  await page.goto("/traces");
  const traceCards = page.locator(".split-layout > .section-card");
  await expect(traceCards).toHaveCount(2);
  const traceList = traceCards.nth(0);
  const traceDetail = traceCards.nth(1);
  const [traceListBox, traceDetailBox] = await Promise.all([
    traceList.boundingBox(),
    traceDetail.boundingBox(),
  ]);
  expect(traceListBox).not.toBeNull();
  expect(traceDetailBox).not.toBeNull();
  expect(Math.abs((traceListBox?.y ?? 0) - (traceDetailBox?.y ?? 0))).toBeLessThanOrEqual(1);
});

test("review dashboard remains bounded at a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/memories");

  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);

  const cards = page.locator(".memory-layout > .section-card");
  await expect(cards).toHaveCount(2);
  for (let index = 0; index < 2; index += 1) {
    const box = await cards.nth(index).boundingBox();
    expect(box).not.toBeNull();
    expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(390);
  }
});

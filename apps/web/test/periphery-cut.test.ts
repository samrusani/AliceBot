import { existsSync, readdirSync, readFileSync } from "node:fs";
import { relative, resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  LEGACY_WEB_ROUTES,
  REMOVED_API_CLIENT_MARKERS,
  REMOVED_FIXTURE_MARKERS,
  REMOVED_WEB_FILES,
  RETAINED_WEB_ROUTES,
} from "./fixture-builders";
import { config as middlewareConfig } from "../middleware";

const WEB_ROOT = resolve(process.cwd());
const EXPECTED_PAGE_FILES = [
  ...RETAINED_WEB_ROUTES,
  ...LEGACY_WEB_ROUTES,
]
  .map((route) => route === "/" ? "app/page.tsx" : `app${route}/page.tsx`)
  .sort();

function discoverPageFiles(directory = resolve(WEB_ROOT, "app")): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      return discoverPageFiles(path);
    }
    return entry.isFile() && entry.name === "page.tsx"
      ? [relative(WEB_ROOT, path)]
      : [];
  });
}

function assertExactPageInventory(actualPageFiles: readonly string[]) {
  const actual = [...actualPageFiles].sort();
  const missing = EXPECTED_PAGE_FILES.filter((path) => !actual.includes(path));
  const unexpected = actual.filter((path) => !EXPECTED_PAGE_FILES.includes(path));
  if (missing.length || unexpected.length) {
    throw new Error(
      `web page inventory mismatch; missing=${missing.join(",") || "none"}; unexpected=${unexpected.join(",") || "none"}`,
    );
  }
}

describe("Phase 1 web surface truth", () => {
  it("keeps all 51 removed web files absent", () => {
    expect(REMOVED_WEB_FILES).toHaveLength(51);
    for (const relativePath of REMOVED_WEB_FILES) {
      expect(existsSync(resolve(WEB_ROOT, relativePath)), relativePath).toBe(false);
    }
  });

  it("does not retain client contracts for deleted routes or the artifact workspace side door", () => {
    const apiSource = readFileSync(resolve(WEB_ROOT, "lib/api.ts"), "utf8");
    for (const marker of REMOVED_API_CLIENT_MARKERS) {
      expect(apiSource, marker).not.toContain(marker);
    }
  });

  it("does not retain chat-only fixture builders or sample histories", () => {
    const fixtureSource = readFileSync(resolve(WEB_ROOT, "lib/fixtures.ts"), "utf8");
    for (const marker of REMOVED_FIXTURE_MARKERS) {
      expect(fixtureSource, marker).not.toContain(marker);
    }
  });

  it("keeps the filesystem page inventory at the exact seven core plus four gated routes", () => {
    expect(RETAINED_WEB_ROUTES).toHaveLength(7);
    expect(LEGACY_WEB_ROUTES).toHaveLength(4);
    assertExactPageInventory(discoverPageFiles());
  });

  it("fails closed when a synthetic page is added to the exact inventory", () => {
    expect(() =>
      assertExactPageInventory([...discoverPageFiles(), "app/synthetic-extra/page.tsx"]),
    ).toThrow(/unexpected=app\/synthetic-extra\/page\.tsx/);
  });

  it("keeps middleware matchers pinned to the exact four gated routes", () => {
    expect(middlewareConfig.matcher).toEqual([...LEGACY_WEB_ROUTES]);
  });
});

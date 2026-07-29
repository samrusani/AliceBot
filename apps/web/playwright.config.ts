import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./test/browser",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,
  // Playwright's default expect timeout is 5s while each test here is allowed
  // 30s, so an assertion could exhaust its budget long before the test did.
  // These suites run fullyParallel against one shared server, and under CI
  // contention a soft navigation can take longer than 5s to paint, which
  // failed the seven-view navigation assertion twice on unrelated changes.
  // This does not weaken any assertion: a genuinely broken page still fails,
  // it just takes longer to say so.
  expect: { timeout: 15_000 },
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "pnpm start --hostname 127.0.0.1 --port 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
    timeout: 30_000,
    env: {
      ALICE_LEGACY_SURFACES: "0",
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

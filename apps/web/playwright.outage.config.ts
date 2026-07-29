import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./test/browser-outage",
  fullyParallel: false,
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
    baseURL: "http://127.0.0.1:3101",
    trace: "retain-on-failure",
  },
  webServer: {
    // Use a separate dev compilation so the intentionally unreachable
    // NEXT_PUBLIC API URL is not replaced by the normal production build's
    // local .env value.
    command: "pnpm dev --hostname 127.0.0.1 --port 3101",
    url: "http://127.0.0.1:3101",
    reuseExistingServer: false,
    timeout: 30_000,
    env: {
      ALICE_LEGACY_SURFACES: "0",
      NEXT_PUBLIC_ALICEBOT_API_BASE_URL: "http://127.0.0.1:9",
      NEXT_PUBLIC_ALICEBOT_USER_ID: "99999999-9999-4999-8999-999999999999",
      ALICEBOT_API_BASE_URL: "http://127.0.0.1:9",
      ALICEBOT_USER_ID: "99999999-9999-4999-8999-999999999999",
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

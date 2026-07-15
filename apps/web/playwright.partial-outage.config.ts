import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./test/browser-partial-outage",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:3102",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "node test/browser-partial-outage/mock-api.mjs",
      url: "http://127.0.0.1:3199/health",
      reuseExistingServer: false,
      timeout: 15_000,
    },
    {
      command: "pnpm dev --hostname 127.0.0.1 --port 3102",
      url: "http://127.0.0.1:3102",
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        ALICE_LEGACY_SURFACES: "0",
        NEXT_PUBLIC_ALICEBOT_API_BASE_URL: "http://127.0.0.1:3199",
        NEXT_PUBLIC_ALICEBOT_USER_ID: "99999999-9999-4999-8999-999999999999",
        ALICEBOT_API_BASE_URL: "http://127.0.0.1:3199",
        ALICEBOT_USER_ID: "99999999-9999-4999-8999-999999999999",
      },
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

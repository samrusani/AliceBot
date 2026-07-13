import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./test/browser-outage",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,
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

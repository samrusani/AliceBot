import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./test/browser-legacy",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:3103",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "pnpm start --hostname 127.0.0.1 --port 3103",
    url: "http://127.0.0.1:3103",
    reuseExistingServer: false,
    timeout: 30_000,
    env: {
      ALICE_LEGACY_SURFACES: "1",
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

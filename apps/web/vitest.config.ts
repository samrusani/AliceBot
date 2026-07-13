import { defineConfig } from "vitest/config";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  test: {
    environment: "jsdom",
    // Bound worker fan-out so DOM-heavy integration tests stay deterministic
    // on both laptops and two-core CI runners.
    maxWorkers: 1,
    testTimeout: 30_000,
    setupFiles: ["./test/setup.ts"],
    include: ["./**/*.{test,spec}.{ts,tsx}"],
    exclude: [
      "test/browser/**",
      "test/browser-outage/**",
      "test/browser-partial-outage/**",
      "**/node_modules/**",
      "**/.next/**",
      "**/dist/**",
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      reportsDirectory: "coverage/core",
      include: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}", "lib/**/*.{ts,tsx}"],
      exclude: [
        "**/*.{test,spec}.{ts,tsx}",
        "app/**/loading.tsx",
        "app/layout.tsx",
        // The interaction-heavy vNext surface is instrumented by the bounded
        // single-thread shard in vitest.vnext.config.ts. Keep it out of this
        // core shard so the aggregate gate stays deterministic and non-duplicative.
        "components/vnext-brain-workspace.tsx",
        "components/vnext-workspace-model.ts",
        "components/vnext-workspace-overview.tsx",
        "next-env.d.ts",
      ],
      thresholds: {
        branches: 65,
        functions: 80,
        lines: 80,
        statements: 80,
        "app/page.tsx": {
          branches: 90,
          functions: 100,
          lines: 95,
          statements: 95,
        },
        "app/approvals/page.tsx": {
          branches: 50,
          functions: 100,
          lines: 80,
          statements: 80,
        },
        "app/gmail/page.tsx": {
          branches: 55,
          functions: 100,
          lines: 85,
          statements: 85,
        },
        "components/app-shell.tsx": {
          branches: 90,
          functions: 100,
          lines: 95,
          statements: 95,
        },
        "components/approval-list.tsx": {
          branches: 80,
          functions: 100,
          lines: 95,
          statements: 95,
        },
        "components/gmail-account-connect-form.tsx": {
          branches: 90,
          functions: 100,
          lines: 90,
          statements: 90,
        },
        "components/gmail-account-detail.tsx": {
          branches: 45,
          functions: 100,
          lines: 80,
          statements: 80,
        },
        "components/workspace-loading.tsx": {
          branches: 100,
          functions: 100,
          lines: 95,
          statements: 95,
        },
      },
    },
  },
});

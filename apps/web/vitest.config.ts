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
        branches: 35,
        functions: 40,
        lines: 40,
        statements: 40,
      },
    },
  },
});

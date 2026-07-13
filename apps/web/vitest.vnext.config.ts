import { defineConfig } from "vitest/config";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./test/setup.ts"],
    include: [
      "./test/vnext-coverage/vnext-coverage.test.tsx",
      "./app/vnext/page.test.tsx",
      "./components/vnext-operator-auth.test.tsx",
    ],
    exclude: [
      "test/browser/**",
      "test/browser-outage/**",
      "test/browser-partial-outage/**",
      "**/node_modules/**",
      "**/.next/**",
      "**/dist/**",
    ],
    // V8 instrumentation of the 3k-line workspace exceeded Vitest's fork RPC
    // deadline after otherwise-passing tests. A single non-isolated thread is
    // a bounded shard with no child-process task-update backlog.
    pool: "threads",
    poolOptions: {
      threads: {
        singleThread: true,
        isolate: false,
      },
    },
    fileParallelism: false,
    testTimeout: 60_000,
    hookTimeout: 30_000,
    teardownTimeout: 30_000,
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      reportsDirectory: "coverage/vnext",
      include: [
        "app/vnext/page.tsx",
        "components/vnext-brain-workspace.tsx",
        "components/vnext-workspace-model.ts",
        "components/vnext-workspace-overview.tsx",
      ],
      exclude: ["**/*.{test,spec}.{ts,tsx}"],
      thresholds: {
        branches: 40,
        functions: 30,
        lines: 60,
        statements: 60,
        "components/vnext-brain-workspace.tsx": {
          branches: 40,
          functions: 14,
          lines: 60,
          statements: 60,
        },
        "app/vnext/page.tsx": {
          branches: 18,
          functions: 100,
          lines: 90,
          statements: 90,
        },
        "components/vnext-workspace-model.ts": {
          branches: 65,
          functions: 75,
          lines: 85,
          statements: 85,
        },
        "components/vnext-workspace-overview.tsx": {
          branches: 50,
          functions: 90,
          lines: 90,
          statements: 90,
        },
      },
    },
  },
});

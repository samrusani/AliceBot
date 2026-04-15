import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { chmodSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const binPath = path.join(packageRoot, "bin", "alice.js");

function makeFakePython() {
  const tempDir = mkdtempSync(path.join(tmpdir(), "alice-cli-test-"));
  const logPath = path.join(tempDir, "args.log");
  const scriptPath = path.join(tempDir, "fake-python");
  const script = `#!/bin/sh
printf '%s\n' "$@" > "${logPath}"
exit 0
`;
  writeFileSync(scriptPath, script, "utf8");
  chmodSync(scriptPath, 0o755);
  return { logPath, scriptPath };
}

test("alice brief forwards to the Python CLI module", () => {
  const { logPath, scriptPath } = makeFakePython();
  const result = spawnSync(
    process.execPath,
    [binPath, "brief", "--query", "deploy"],
    {
      cwd: packageRoot,
      env: {
        ...process.env,
        ALICEBOT_PYTHON: scriptPath,
      },
      encoding: "utf8",
    },
  );

  assert.equal(result.status, 0);
  const forwardedArgs = result.error ? [] : readFileSync(logPath, "utf8").trim().split("\n");
  assert.deepEqual(forwardedArgs, ["-m", "alicebot_api", "brief", "--query", "deploy"]);
});

test("alice rejects unknown commands", () => {
  const result = spawnSync(
    process.execPath,
    [binPath, "status"],
    {
      cwd: packageRoot,
      encoding: "utf8",
    },
  );

  assert.equal(result.status, 1);
  assert.match(result.stderr, /Unknown command: status/);
});

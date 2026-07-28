import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { chmod, mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { validateBulkAdvisoryResponse } from "./npm-advisory-response.mjs";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const WEB_DIR = path.dirname(SCRIPT_DIR);
const AUDIT_SCRIPT = path.join(SCRIPT_DIR, "npm-advisory-audit.mjs");

async function runAudit(responsePayload, options = {}) {
  const temporaryDirectory = await mkdtemp(
    path.join(tmpdir(), "alice-npm-advisory-test-"),
  );
  const fakePnpm = path.join(temporaryDirectory, "pnpm");
  await writeFile(
    fakePnpm,
    "#!/usr/bin/env node\n" +
      "process.stdout.write(JSON.stringify([{ dependencies: { demo: { version: '1.2.3' } } }]));\n",
    "utf8",
  );
  await chmod(fakePnpm, 0o755);

  if (options.exceptions !== undefined) {
    const exceptionsFile = path.join(temporaryDirectory, "exceptions.json");
    await writeFile(
      exceptionsFile,
      typeof options.exceptions === "string"
        ? options.exceptions
        : JSON.stringify(options.exceptions),
      "utf8",
    );
    options.exceptionsFile = exceptionsFile;
  }

  const server = createServer((request, response) => {
    request.resume();
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify(responsePayload));
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });

  try {
    const address = server.address();
    assert(address && typeof address === "object");
    return await new Promise((resolve, reject) => {
      const child = spawn(
        process.execPath,
        [AUDIT_SCRIPT, "--audit-level=high", ...(options.extraArgs ?? [])],
        {
          cwd: WEB_DIR,
          env: {
            ...process.env,
            PATH: `${temporaryDirectory}${path.delimiter}${process.env.PATH ?? ""}`,
            NPM_BULK_ADVISORY_URL: `http://127.0.0.1:${address.port}/bulk`,
            NPM_ADVISORY_EXCEPTIONS_PATH:
              options.exceptionsFile ?? path.join(temporaryDirectory, "absent.json"),
          },
          stdio: ["ignore", "pipe", "pipe"],
        },
      );
      let stdout = "";
      let stderr = "";
      child.stdout.setEncoding("utf8");
      child.stderr.setEncoding("utf8");
      child.stdout.on("data", (chunk) => {
        stdout += chunk;
      });
      child.stderr.on("data", (chunk) => {
        stderr += chunk;
      });
      child.once("error", reject);
      child.once("close", (code, signal) => {
        resolve({ code, signal, stdout, stderr });
      });
    });
  } finally {
    await new Promise((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
    await rm(temporaryDirectory, { recursive: true, force: true });
  }
}

test("validator accepts the valid empty and populated response shapes", () => {
  assert.deepEqual(validateBulkAdvisoryResponse({}), {});
  const payload = {
    demo: [
      {
        vulnerable_versions: ">=1.0.0 <2.0.0",
        severity: "high",
        title: "Demo advisory",
        url: "https://example.invalid/advisory",
      },
    ],
  };
  assert.equal(validateBulkAdvisoryResponse(payload), payload);
});

test("validator rejects malformed successful JSON response shapes", () => {
  const malformed = [
    [],
    null,
    { demo: {} },
    { demo: [null] },
    { demo: [{ vulnerable_versions: "not a range", severity: "high" }] },
    { demo: [{ vulnerable_versions: "<2", severity: "unknown" }] },
    {
      demo: [
        { vulnerable_versions: "<2", severity: "high", title: 7 },
      ],
    },
    { demo: [{ vulnerable_versions: "<2", severity: "high", url: false }] },
  ];

  for (const payload of malformed) {
    assert.throws(() => validateBulkAdvisoryResponse(payload), TypeError);
  }
});

test("audit CLI exits 2 for a malformed successful response", async () => {
  const result = await runAudit([]);
  assert.equal(result.signal, null);
  assert.equal(result.code, 2);
  assert.match(result.stderr, /audit failed to run: bulk advisory response/);
  assert.equal(result.stdout, "");
});

test("audit CLI accepts a valid empty advisory object", async () => {
  const result = await runAudit({});
  assert.equal(result.signal, null);
  assert.equal(result.code, 0);
  assert.match(result.stdout, /0 matching advisories, 0 at or above high/);
  assert.equal(result.stderr, "");
});

test("audit CLI preserves blocking-advisory exit 1", async () => {
  const result = await runAudit({
    demo: [
      {
        vulnerable_versions: ">=1.0.0 <2.0.0",
        severity: "high",
        title: "Demo advisory",
        url: "https://example.invalid/advisory",
      },
    ],
  });
  assert.equal(result.signal, null);
  assert.equal(result.code, 1);
  assert.match(result.stdout, /\[BLOCKING\] high demo@1\.2\.3/);
  assert.match(result.stdout, /1 matching advisories, 1 at or above high/);
  assert.equal(result.stderr, "");
});

const BLOCKING_PAYLOAD = {
  demo: [
    {
      vulnerable_versions: ">=1.0.0 <2.0.0",
      severity: "high",
      title: "Demo advisory",
      url: "https://example.invalid/advisory",
    },
  ],
};

const liveException = (overrides = {}) => ({
  exceptions: [
    {
      advisory_url: "https://example.invalid/advisory",
      package: "demo",
      expires: "2999-01-01",
      justification: "no remediation exists; development tooling only",
      ...overrides,
    },
  ],
});

test("a live exception clears a blocking advisory and prints its justification", async () => {
  const result = await runAudit(BLOCKING_PAYLOAD, { exceptions: liveException() });
  assert.equal(result.code, 0);
  assert.match(result.stdout, /\[EXCEPTED until 2999-01-01\]/);
  assert.match(result.stdout, /justification: no remediation exists/);
  assert.match(result.stdout, /1 excepted/);
});

test("the production audit ignores exceptions entirely", async () => {
  const result = await runAudit(BLOCKING_PAYLOAD, {
    exceptions: liveException(),
    extraArgs: ["--prod"],
  });
  assert.equal(result.code, 1);
  assert.match(result.stdout, /\[BLOCKING\]/);
  assert.doesNotMatch(result.stdout, /EXCEPTED/);
});

test("an expired exception stops applying and fails the audit", async () => {
  const result = await runAudit(BLOCKING_PAYLOAD, {
    exceptions: liveException({ expires: "2000-01-01" }),
  });
  assert.equal(result.code, 1);
  assert.match(result.stderr, /\[EXPIRED\]/);
  assert.match(result.stdout, /\[BLOCKING\]/);
  assert.match(result.stdout, /1 expired exception/);
});

test("an exception matching nothing is reported as stale", async () => {
  const result = await runAudit(
    {},
    { exceptions: liveException() },
  );
  assert.equal(result.code, 0);
  assert.match(result.stdout, /\[STALE\]/);
});

test("a malformed or under-specified exception file fails closed", async () => {
  for (const malformed of [
    "{ not json",
    JSON.stringify({}),
    JSON.stringify({ exceptions: {} }),
    JSON.stringify({ exceptions: [{ advisory_url: "u", package: "demo", expires: "2999-01-01" }] }),
    JSON.stringify({ exceptions: [{ advisory_url: "u", package: "demo", expires: "soon", justification: "j" }] }),
  ]) {
    const result = await runAudit(BLOCKING_PAYLOAD, { exceptions: malformed });
    assert.equal(result.code, 2, `expected exit 2 for ${malformed}`);
    assert.match(result.stderr, /audit failed to run/);
  }
});

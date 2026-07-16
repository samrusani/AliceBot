#!/usr/bin/env node
// Dependency vulnerability audit against npm's bulk advisory endpoint.
//
// Alice intentionally remains on the reproducible Node 20 / pnpm 10.23.0
// toolchain for this patch carrier. pnpm 11 has moved `pnpm audit` to npm's
// bulk endpoint (upstream decision: https://github.com/orgs/pnpm/discussions/11377),
// but changing package-manager majors is a separate compatibility decision.
// Keep this stricter fail-closed wrapper while pnpm 10 is pinned: collect the
// installed dependency tree (production-only with --prod), submit
// name -> [versions] to
// /-/npm/v1/security/advisories/bulk, range-match each installed version
// against every advisory's vulnerable_versions, and fail closed at the
// configured severity threshold. Endpoint or parsing failures exit nonzero:
// an audit that cannot run must never pass silently.
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { validateBulkAdvisoryResponse } from "./npm-advisory-response.mjs";

const require = createRequire(import.meta.url);
const semver = require("semver");

const BULK_ADVISORY_URL =
  process.env.NPM_BULK_ADVISORY_URL ??
  "https://registry.npmjs.org/-/npm/v1/security/advisories/bulk";
const SEVERITY_RANK = { info: 0, low: 1, moderate: 2, high: 3, critical: 4 };

const args = process.argv.slice(2);
const prodOnly = args.includes("--prod");
const levelArg = args.find((a) => a.startsWith("--audit-level="));
const auditLevel = levelArg ? levelArg.split("=")[1] : "high";
const threshold = SEVERITY_RANK[auditLevel];
if (threshold === undefined) {
  console.error(`unknown --audit-level=${auditLevel}`);
  process.exit(2);
}

function collectVersions() {
  const listArgs = ["list", "--json", "--depth", "Infinity"];
  if (prodOnly) listArgs.splice(1, 0, "--prod");
  const raw = execFileSync("pnpm", listArgs, {
    encoding: "utf8",
    maxBuffer: 256 * 1024 * 1024,
  });
  const tree = JSON.parse(raw);
  const versions = new Map();
  const visit = (deps) => {
    if (!deps) return;
    for (const [name, info] of Object.entries(deps)) {
      const version = info?.version;
      if (typeof version === "string" && semver.valid(version)) {
        if (!versions.has(name)) versions.set(name, new Set());
        versions.get(name).add(version);
      }
      visit(info?.dependencies);
    }
  };
  for (const project of tree) {
    visit(project.dependencies);
    if (!prodOnly) {
      visit(project.devDependencies);
      visit(project.optionalDependencies);
    }
  }
  return versions;
}

async function fetchAdvisories(versions) {
  const body = {};
  for (const [name, set] of versions) body[name] = [...set];
  const response = await fetch(BULK_ADVISORY_URL, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`bulk advisory endpoint returned HTTP ${response.status}`);
  }
  return validateBulkAdvisoryResponse(await response.json());
}

const versions = collectVersions();
if (versions.size === 0) {
  console.error("no installed dependencies found; refusing to pass an empty audit");
  process.exit(2);
}

let advisories;
try {
  advisories = await fetchAdvisories(versions);
} catch (error) {
  console.error(`audit failed to run: ${error.message}`);
  process.exit(2);
}

const findings = [];
for (const [name, entries] of Object.entries(advisories)) {
  const installed = versions.get(name);
  if (!installed) continue;
  for (const advisory of entries) {
    const range = advisory.vulnerable_versions ?? "*";
    const affected = [...installed].filter((v) =>
      semver.satisfies(v, range, { includePrerelease: true }),
    );
    if (affected.length === 0) continue;
    const severity = String(advisory.severity ?? "info").toLowerCase();
    findings.push({
      name,
      affected,
      severity,
      rank: SEVERITY_RANK[severity] ?? SEVERITY_RANK.critical,
      title: advisory.title ?? "(untitled advisory)",
      url: advisory.url ?? "",
      range,
    });
  }
}

const scope = prodOnly ? "production" : "full";
const blocking = findings.filter((f) => f.rank >= threshold);
for (const f of findings) {
  const marker = f.rank >= threshold ? "BLOCKING" : "info";
  console.log(
    `[${marker}] ${f.severity} ${f.name}@${f.affected.join(",")} (${f.range}) ${f.title} ${f.url}`,
  );
}
console.log(
  `${scope} audit: ${versions.size} packages checked, ` +
    `${findings.length} matching advisories, ${blocking.length} at or above ${auditLevel}`,
);
process.exit(blocking.length > 0 ? 1 : 0);

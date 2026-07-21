# Dependency And Supply-Chain Posture

## Pinning Policy

- The web application declares exact direct dependency versions in
  `apps/web/package.json` and commits `apps/web/pnpm-lock.yaml`. CI installs with
  the repository's pinned pnpm version.
- Python runtime and development dependencies use bounded compatible ranges in
  `pyproject.toml`; build-system dependencies are exact pins. The published
  package intentionally permits compatible resolver updates and the repository
  does not currently commit a full Python application lock.
- GitHub Actions are pinned to commit SHAs. Tool versions installed inside jobs,
  such as Gitleaks, are explicitly selected and their downloaded archive is
  checksum-verified.
- Dependabot checks GitHub Actions, pip, and the web npm ecosystem weekly.

## Web Advisory Gate

The pinned pnpm 10 audit client depends on retired registry behavior, so Alice
uses `apps/web/scripts/npm-advisory-audit.mjs` against npm's bulk advisory
endpoint. The wrapper:

1. obtains the installed dependency tree from pnpm;
2. refuses an empty tree;
3. sends package/version sets to the bulk endpoint;
4. validates that the response is a plain package-to-advisory-array object with
   valid severity and semver ranges;
5. range-matches every installed version; and
6. fails closed on network, HTTP, JSON, schema, or configured-threshold failure.

CI runs both production-only and full-tree audits at `high`, so High and
Critical matches block. Lower-severity matches remain visible but do not fail
that job. The validator's malformed/empty-response behavior is covered by
`apps/web/scripts/npm-advisory-audit.test.mjs`.

```bash
cd apps/web
pnpm test:advisory-audit
node scripts/npm-advisory-audit.mjs --prod --audit-level=high
node scripts/npm-advisory-audit.mjs --audit-level=high
```

These commands require the npm advisory service. An unavailable or malformed
service must fail, not produce a green empty result.

## Repository Scanning

`.github/workflows/security-scans.yml` runs on pull requests, pushes to `main`,
a weekly schedule, and manual dispatch:

- Gitleaks scans the relevant commit range with redacted output.
- CodeQL analyzes Python and JavaScript.

Those scanners supplement review and tests; neither proves runtime reachability
or the absence of a vulnerability.

## Open Gap: Python Advisory Enforcement

Dependabot monitors declared pip requirements, but Alice currently has no
fail-closed CI command that audits the resolved Python environment against a
vulnerability database. Compatible-range resolution also means two installers
can select different transitive versions over time.

Until that gap is deliberately closed, release evidence must record the exact
Python environment used for tests (including `python --version` and `pip
freeze`), review Dependabot alerts, and avoid claiming equivalent Python and web
advisory enforcement. Adding a Python lock/audit policy is a later scoped change,
not something these documents certify into existence.

## Update Discipline

- Dependency/security updates use a focused carrier with the full unit,
  integration, web, package, and release matrix.
- Major runtime/toolchain upgrades are independently qualified; audit-tool
  breakage is not bypassed with `continue-on-error`.
- Lockfile-only changes must be reviewed against their manifest intent and
  production graph.
- A clean advisory result is time-bound to the database response and exact
  installed tree recorded by that run.

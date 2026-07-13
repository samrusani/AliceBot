# Alice v0.10.0 Main-Engineer Handoff

## Decision state

The first five independent acceptance passes returned **REJECT**. The fifth
pass accepted all pass-5 semantic-report, MCP date/confidence, browser, HTTP,
and web repairs, then found two bounded release-evidence residuals: publication
had lost its independent repository-control gate, and semantic attestation
copies still admitted Python's boolean/integer/float equality coercions.
Bounded repair pass 6 restores a strict release-specific control attestation
in addition to the semantic gate and makes every report copy recursively
type-faithful. The sixth independent acceptance is now **PASS with no P0, P1,
or P2 finding**. `REVIEW_REPORT.md` is the authoritative verdict. This closes
code review; it does not authorize publication from the current dirty tree.

The audited implementation is assembled on `codex/v0.10-audit-remediation`
from baseline `68d6bf2f3e76425f5cbd13a73411a3231dffba02`. The published `v0.9.4`
tag remains immutable. No builder created a commit, pushed, tagged, published,
or dispatched a credentialed workflow.

Do **not** publish from the dirty builder tree. First read:

1. `FIX_MATRIX.md` for finding-by-finding closure evidence.
2. `BUILD_REPORT.md` for exact local verification.
3. `REVIEW_REPORT.md` for the authoritative final independent verdict.

The first five review passes remain part of the audit history; the sixth pass
supersedes their time-relative blockers. Four publication gates remain:

1. Commit the accepted tree and establish one clean candidate SHA.
2. Run the complete required CI/check set successfully on that exact SHA.
3. Perform fresh external control readback and provide the structured
   `ALICE_RELEASE_CONTROLS_ATTESTATION` for its repository/SHA/tag.
4. Produce and inspect the protected configured PostgreSQL/pgvector semantic
   report/attestation for the same SHA.

## High-impact changes

- New migration `20260713_0085` introduces a backward-compatible scoped
  source-capture dedupe identity and an atomic live-row uniqueness boundary.
- Published migration `20260712_0084` remains byte-for-byte unchanged. New
  idempotent migration `20260713_0086`, after 0085, repairs every duplicate
  retry/confirmation pointer in 3+ row groups for existing released databases.
- Vector writers share one v2 signature contract. Provider/model/endpoint,
  content digest, finite vector validation, and signature version must remain
  aligned across CLI, onramp, eval, scale, SQLite, and PostgreSQL.
- Semantic release reports enforce the exact 78 ordered cases and bind each to
  its producer-owned suite title, query, target, and evidence semantics. Nested
  suite/case metrics, retrieval latency/subsets/seeding, graph rank/control,
  numeric finiteness/ranges, rank-derived metrics, aggregate reconciliation,
  known corpora, and six-suite Postgres evidence are strict. One canonical
  `sha256:<hex>` report digest binds all semantic fields; the bare transport
  hash separately binds report bytes. Report, seeding, and attestation share
  one structured embedding signature. Recursive credential keys/values and
  unknown fields are invalid evidence. Every attestation copy uses recursive
  JSON-type-sensitive equality; candidate counts are positive integers,
  participation is exactly boolean `true`, and paraphrase recall is a finite
  float in the closed 0..1 interval.
- Publication separately consumes a credentialless structured repository
  variable that is closed-schema, release-specific, and valid for at most 24
  hours. It binds the repository, exact SHA, stable tag, verification/expiry
  times, and affirmative readback of the protected PyPI environment, reviewer
  and deployment policy, protected main/tags, strict checks, immutable
  releases, trusted publishing, credential controls, and exact-SHA checks.
  Missing, malformed, stale, future-dated, mismatched, incomplete, false, or
  unknown claims fail before release verification and semantic artifact use.
- Retrieval pushes hard project/people/time constraints before `LIMIT` across
  memories, source chunks/titles, provenance, graph rows, and open loops;
  legacy adapters terminate or fail closed at a documented bound.
- Lifecycle writes use one per-user graph/candidate/member serialization order
  before row locks across every public entry path.
- Backup import consumes one immutable snapshot, decodes each envelope once,
  and streams through a bounded private disk spool. Export permits reserved
  SQLite statistics tables but rejects unknown application tables.
- MCP runtime input validation enforces recursively closed advertised schemas,
  including unions/null, types, enums, UUID/date-time formats, bounds, patterns,
  array items, and cardinality. RFC 3339 full dates require calendar validity,
  and unsupported advertised formats fail closed. It validates provenance
  atomically and preserves documented scoped `alice_recall` arguments end-to-
  end.
- Core and legacy correction confidence/replacement-confidence inputs enforce
  finite 0..1 bounds before their handlers. Below-zero, above-one, boolean, and
  non-finite values leave memory/revision/provenance or handler state unchanged;
  valid zero and one boundaries remain accepted.
- The web app adds thread-keyed drafts, read-only fixture fallbacks,
  live-proven mutation targets, parallel detail loading, accessibility fixes,
  core plus vNext coverage, outage-browser tests, and bundle gates.
- Local browser setup is explicit and platform-safe: `make setup-browser`
  installs Playwright-managed Chromium without Linux `--with-deps`, while
  `test-web` declares the target as a prerequisite. Clean Debian/Ubuntu hosts
  can explicitly run guarded `make setup-browser-linux`; CI shares that Linux
  package script, and macOS is rejected by the Linux-only target.
- A target obtained from the live review queue remains correction-capable when
  only detail/history fails. The vNext shard executes six representative
  orchestrator actions and enforces a nonzero 10% per-file function threshold.
- Normal cross-module mypy is enforced without `--follow-imports=skip` in CI
  and `release-static`.
- Release documents require one strict state declaration on physical line 2;
  workflow check names are parsed from real YAML, and packaged README links
  remain portable absolute URLs.

## Review and merge procedure

1. Inspect `git status --short` and preserve all files in this remediation
   scope. The builder intentionally left the tree uncommitted for review.
2. Review immutable published migration `0084` plus new migrations `0085` and
   `0086` together with their unit, upgrade-path, and live PostgreSQL tests.
3. Review the structured repository-control gate and the exact-SHA semantic
   workflow as two independent release boundaries. Both are mandatory and
   neither may substitute for the other; do not weaken either to make a run
   pass.
4. Review the MCP schema changes together with `test_mcp.py` and the parity
   integration test. Unknown properties are intentionally rejected.
5. Review both web coverage shards. The vNext shard directly instruments the
   orchestrator/model/overview with per-file thresholds rather than hiding the
   largest surface behind the aggregate gate.
6. Read the final PASS in `REVIEW_REPORT.md`, make one or more intentional
   commits on the remediation branch, then rerun the complete gate set on that
   exact clean candidate SHA.

## Required local gates

Run from the repository root with the same PostgreSQL role-separated URLs as
CI:

```bash
make release-static
make setup-browser
./.venv/bin/python -m pytest tests/unit -q --cov=alicebot_api --cov-report=term --cov-fail-under=50
./.venv/bin/python -m pytest tests/integration -q
./.venv/bin/python -m pytest eval/longmemeval -q
./.venv/bin/python scripts/check_longmemeval_evidence.py
pnpm --dir apps/web test
pnpm --dir apps/web test:coverage
pnpm --dir apps/web typecheck
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web test:budget
pnpm --dir apps/web test:browser
```

Build release artifacts outside the worktree, run Twine, test both wheel and
sdist with `scripts/test_distribution_artifact.py`, and run
`scripts/release_check.py --dist-dir <dir>`. Confirm the built METADATA still
contains no relative Markdown links.

The pass-3 broad gate has 2,497 Python units at 69.47% coverage, 418 sequential
PostgreSQL integrations, 127 LongMemEval tests plus evidence, normal
cross-module mypy over 133 files, 252 web units, both coverage shards, eight
Playwright tests, a 19-route build, all bundle budgets, scale, release-static,
and wheel/sdist Twine/install smokes green. Exact evidence is in
`BUILD_REPORT.md`. Pass 4 reran the affected release/eval, MCP confidence,
browser setup, package, control-doc, release-static, and browser gates. Pass 5
reruns the semantic contract, MCP date/confidence, isolated package, control-
doc, release-static, and diff gates; browser code is unaffected and the fourth
review independently accepted that lane. Do not rewrite the pass-3 broad counts
as if all 2,497/418 tests were rerun after pass 5.

Pass-5 affected-lane evidence is: 113 semantic release/eval tests; independent
read-only rejection of all seven fourth-review reproductions, 401 wrong-type
mutations, 122 unknown nested keys, four 156-leaf special-numeric sweeps, and
both 34-leaf boolean target sweeps with zero crashes; 184 MCP units plus 58
focused date/confidence cases; eight durable SQLite boolean/non-finite rollback
cases; one PostgreSQL edit/replacement rollback; and an isolated wheel/sdist
build with Twine, release metadata, both installed-artifact smokes, and packaged
link scans green. Exact commands and artifact hashes are in `BUILD_REPORT.md`.

Pass 6 is deliberately narrower. It reruns the release-control validator and
workflow contract, semantic release/attestation modules, control-document
truth, release-static, isolated package verification, and diff checks. It does
not rewrite historical broad, PostgreSQL, MCP, or browser counts as fresh.
The combined six-file slice has 219 passing tests: the control/workflow/docs
lane has 88, the complete release/eval modules have 131, and an independent
builder control mutation sweep rejected 155/155 inputs without a crash. The
sixth reviewer independently rejected 157 adversarial claims, accepted only
the two legitimate ordinary/24-hour-boundary claims, and found no crash. The semantic
matrix rejects all five fifth-review substitutions and 102/102 recursive type
drifts while preserving the 78-case roundtrip. Current release-static checks
134 mypy files. The isolated pass-6 wheel/sdist build, Twine, repository release
check, installed-artifact smokes, and 28-target portable-link scans are green;
exact local hashes are in `BUILD_REPORT.md`.

## Mandatory repository-control attestation

After the reviewed tree is committed and the intended stable tag is known,
repeat the documented GitHub control readback. Populate the credentialless
`ALICE_RELEASE_CONTROLS_ATTESTATION` repository variable with the exact closed
JSON contract in `RELEASING.md`. It must bind the current repository, 40-hex
release SHA, stable tag, canonical UTC verification and expiry timestamps no
more than 24 hours apart, and every required control as the JSON boolean
`true`. Never put endpoints, tokens, credentials, or account identifiers in
this variable.

The publish workflow first rejects a missing variable, then validates its
complete structure and identity before release checks, semantic artifact
resolution, build, or publication. Any control drift requires a new readback
and replacement or removal of the variable. A valid semantic artifact cannot
replace this declaration, and a valid control declaration cannot replace the
semantic artifact.

## Mandatory exact-SHA semantic evidence

The local deterministic provider proves plumbing only. It is not public
release evidence. After the reviewed tree is clean and committed:

1. Configure the protected `semantic-release` GitHub environment with the
   intended provider configuration. Do not put credentials in workflow YAML,
   artifacts, logs, or repository files.
2. Dispatch `.github/workflows/semantic-release-gate.yml` for the exact
   candidate SHA.
3. Verify the run is successful and the SHA-named artifact contains a complete
   Postgres-backed report plus attestation for that same SHA.
4. Confirm all six suites and exactly 78 canonical cases executed; every suite
   reports Postgres; suite titles and each query/target link match the canonical
   generator contract; nested metrics/evidence are recursively closed, finite,
   range-valid, and reconcile with ranks/aggregates; known corpus digests and
   exact target checks validate; vector candidates participated on every
   retrieval query; report/attestation digests match; and recursive credential
   scanning is clean.
5. Only then allow `publish-pypi.yml` to consume that exact workflow run.

Any skipped eval suite, stale SHA artifacts, malformed attestations,
non-finite vectors, missing vector participation, and failed backfills now
fail closed. Do not bypass those outcomes.

## Operational cautions

- Apply migrations with the documented role split and take a backup first.
- Quiesce writers before restoring into an existing SQLite target; that
  contract remains intentional and documented.
- Web coverage is split into a core shard and a stable vNext shard. The latter
  now directly records 63.93% line/statement, 42.85% branch, and 14.42%
  function coverage on the 3,342-line orchestrator, with hard 60/40/10/60
  per-file thresholds. Further decomposition remains worthwhile follow-up
  debt.
- The post-implementation Desloppify scan is a broad mechanical inventory, not
  a release verdict. Its unassessed subjective dimensions are zeros by design;
  use the exact scores in `BUILD_REPORT.md` rather than the strict aggregate in
  isolation. Cybersecurity review was explicitly out of scope.

## Publication stop conditions

Stop the release if any of the following is true:

- `REVIEW_REPORT.md` contains a blocker or is missing.
- The accepted tree is still dirty/uncommitted, or candidate identity does not
  match the reviewed clean SHA.
- Required CI/checks have not passed on that exact candidate SHA.
- Migration, full sequential PostgreSQL integration, web browser/a11y, package,
  control-doc, or release-static gates fail.
- The configured semantic report is missing, skipped, stale, non-Postgres,
  credential-bearing, or not exact-SHA attested.
- The repository-control attestation is missing, malformed, stale,
  future-dated, for another repository/SHA/tag, or does not affirm every
  required release control.
- Release notes/checksum state is finalized before the artifacts actually
  exist, or remains pending after publication.

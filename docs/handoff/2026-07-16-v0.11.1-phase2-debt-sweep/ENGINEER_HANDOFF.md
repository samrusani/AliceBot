# Alice v0.11.1 Phase 2 Engineer Handoff

## Start here

This is an uncommitted Phase 2 candidate based on
`5f0a92d77d02b0699af3054fced7427929808aa8` (tree
`560bade5b9ad20c659f03f19693288558c706945`) on
`codex/v0111-phase2-debt-sweep`. Both governed version sources are already
`0.11.1`; do not bump them again. The builder did not stage, commit, push, tag,
or publish anything.

At package-input freeze, the bounded local Python, PostgreSQL, SQLite,
evaluation, web, static, and health builder matrix was green; final package
reproduction, the superseding twice-reproduced receipt, and independent review
were still pending. Consult the final `BUILD_REPORT.md` and reviewer-authored
`REVIEW_REPORT.md` for their outcomes.

Review in this order:

1. `SURFACE_INVENTORY.md` for the post-cut remeasurement and exact disposition
   of 2.0 through 2.14.
2. `FIX_MATRIX.md` for fail-on-old proof and the explicit Option A policy
   boundary.
3. `.github/workflows/tests.yml`, the default-surface integration smoke, and
   `check_github_release_checks.py` for the separate required check.
4. `public_errors.py`, HTTP callsite migration, OpenAPI error contracts, then
   MCP/CLI/onramp and migrated provider/response/scheduler/evaluation/doctor/
   connector diagnostic sentinel tests. Preserve the intentional legacy-on
   `proxy_execution.py` business-result reasons explicitly excluded from this
   migration, and keep the GitHub CodeQL baseline separate from local source
   proof.
5. The ASCII literal-fold helpers and `list_memories(query=...)` plus
   `list_resume_memory_events(query=...)` implementations in PostgreSQL,
   SQLite, and `FakeVNextMCPStore`, followed by public resume/recent-decisions
   parity. Generic `search_memories` and `alice_recall` FTS/websearch retrieval
   have separate, unchanged semantics.
6. Migration `0091`, both `list_project_update_events` implementations, and
   terminal replay. Check index selectivity, stable order, full-row set
   de-duplication, tenant predicates, and the existing corruption matrix.
7. Reject's pre-mutation memory-key validation and the shared pending-project
   guard through HTTP, core/legacy MCP, CLI, SQLite, and PostgreSQL.
8. Option A end to end: `redact_memory_flow`, both bundle stores, SQLite
   triggers, migration `0092`, HTTP/OpenAPI, MCP/CLI responses, and the live
   accepted/edit/rejected graph test.
9. Migration `0091` source-identity normalization and vocabulary constraints,
   especially NBSP/U+001C parity and downgrade semantics.
10. The fake-store, coverage, mypy, release-trigger, scheduler `--once`, and
    evergreen-readme truth gates.
11. The response-generation consumer inventory and removed-export tests, then
    retained provider-runtime transport/idempotency/trace behavior.
12. Dependency dispositions: redis/pytest ranges, immutable checkout/CodeQL
    pins, unchanged web application/framework and deferred-major set, the
    direct `semver@7.8.0` audit-tool dev dependency, the fail-closed npm
    wrapper, and the nine still-open Dependabot PRs.
13. `BUILD_REPORT.md`, the final twice-reproduced receipt, and only then the
    reviewer-authored `REVIEW_REPORT.md`.

## High-risk invariants

- `Default surface integration smoke (Postgres)` must remain a distinct check.
  The test skips when `ALICE_LEGACY_SURFACES` is present, so a flag-on matrix
  cannot masquerade as default evidence. MainProtect must require the exact
  name after merge.
- HTTP exception-backed failures use a stable object inside the existing
  `detail` envelope. Do not reintroduce exception text through a compatibility
  wrapper, delayed `error_detail`, stored trace, or log-derived response.
  FastAPI's native string/list validation variants remain represented in the
  outer OpenAPI union.
- The 242 CodeQL alerts are a server-side published-base measurement. Local
  zero AST violations do not close them; only CodeQL on a committed exact SHA
  can provide target-zero evidence.
- Memory literal search folds only ASCII. Do not replace it with locale
  `lower()` or Unicode `casefold()`. `%`, `_`, and backslash must remain
  literals, and non-ASCII matching must remain exact.
- Migration `0091` adds stored generated columns to `event_log`. On a large
  database this may rewrite/lock the table. Use a maintenance window and
  verified backup. Its downgrade removes the query substrate but deliberately
  does not recreate invalid whitespace-only source dedupe keys.
- Terminal replay uses one bounded store call but preserves the complete
  evidence validator. Optimization must not weaken duplicate, contradictory,
  actor, target, action, linkage, or redaction checks.
- A null/blank project-update `memory_key` must fail before any reject-side
  write. A pending candidate recognized by workflow metadata or reserved key
  prefix may transition only through project-update review. Exact terminal
  `candidate=false` rows may use generic correction.
- Option A applies only to exact terminal `project_update` artifacts whose
  original workflow, project id/scope, candidate id, status, and review action
  agree. A malformed partial artifact or arbitrary UUID in prose must never
  broaden redaction authority.
- Memory redaction does not modify source or source-chunk evidence because
  either may support other memories. Source rows have their own update/review
  paths; do not describe every source as immutable or imply global erasure.
- Redaction destroys content but retains structural evidence. Governed text
  uses `[REDACTED]`, governed non-null free-form JSON uses
  `{"redacted":true}`, and null stays null. The memory's `commit_digest` and
  `confirmation_id` are cleared; `confirmation_status`, `last_confirmed_at`,
  its non-content classification/lifecycle fields, identities, and links
  remain. It does not roll back `projects.current_state`. All six numeric
  quality dimensions and categorical verbosity remain; quality prose and
  arbitrary metadata do not. SQLite has no artifact/rating repository and must
  return zero for those counts rather than infer success.
- `0092`'s redaction flags are exceptional and must always reset. Ordinary
  event/revision mutation remains append-only. Redacted artifacts remain
  immutable, and new feedback, quality prose, or quoted provenance must be
  rejected after redaction.
- A genuine replay performs no write, preserves the first authorized
  `redacted_at`, returns zero changed counts, and leaves exactly one receipt.
  An arbitrary preexisting `redacted_at` without marker plus receipt is not
  authoritative.
- Source whitespace uses the explicit CPython 3.12 29-codepoint table; POSIX
  `[[:space:]]` is not an equivalent substitute. Domain/sensitivity values are
  canonical vocabulary, not locale-folded free text.
- The release metadata now admits redis-py 5.x through 8.x as required by the
  accepted #236 carrier. Verify package metadata and installed-artifact smoke;
  do not misstate the open Dependabot PR as merged.
- `response_generation.py` still backs `/v1/runtime/invoke` durability. The
  trim must not remove prompt/trace persistence, provider telemetry, or
  idempotent response-job behavior.
- The npm advisory wrapper is intentional on Node 20/pnpm 10.23.0. Changing
  package-manager major, TypeScript, Next ESLint, or Node types requires a
  separate full compatibility carrier.

## Nonblocking structural-debt follow-up

The isolated Python health scan is reported as a range because its unordered,
basename-only `tests/unit/test_main.py` mapping can attach to either of two
`main.py` files despite an identical candidate manifest. The honest readings
are overall 34.3-34.4, objective 85.8-85.9, code quality 83.1 (82.9 strict),
file health 81.1 (80.8 strict), duplication 99.6, and test health 73.7-74.6.
Bandit was unavailable, the jscpd boilerplate detector errored, and 20
subjective dimensions were unassessed.

Two unchanged private helpers are confirmed repository-local dead code:
`main.py::_runtime_provider_config_or_none` (18 lines) and
`mcp_tools.py::_build_recall_query` (11 lines). Repo-wide text and AST scans
find definitions only, and their base/current AST hashes match. They are
pre-existing, outside the Phase 2 delta, and nonblocking follow-up for the
post-v0.11.1 structural split.

## Reproduce the primary gates

Use direct virtual-environment executables. Do not run `uv sync` or mutate the
protected `uv.lock`/`coverage.json` artifacts.

```bash
git diff --check
untracked_whitespace_failed=0
while IFS= read -r -d '' candidate_path; do
  check_output=$(git diff --no-index --check /dev/null "$candidate_path" 2>&1)
  check_rc=$?
  if [ "$check_rc" -gt 1 ] || [ -n "$check_output" ]; then
    printf '%s\n' "$check_output"
    untracked_whitespace_failed=1
  fi
done < <(git ls-files --others --exclude-standard -z)
test "$untracked_whitespace_failed" -eq 0
PYTHON=./.venv/bin/python make release-static

COVERAGE_FILE=/tmp/alice-p2.coverage ./.venv/bin/python -m pytest \
  tests/unit -q -p no:cacheprovider --cov=alicebot_api \
  --cov-report=term --cov-report=json:/tmp/alice-p2-coverage.json \
  --cov-fail-under=50
./.venv/bin/python scripts/check_python_coverage.py \
  --coverage-json /tmp/alice-p2-coverage.json \
  --path apps/api/src/alicebot_api/main.py --min-percent 45

DATABASE_ADMIN_URL=postgresql://alicebot_admin:alicebot_admin@127.0.0.1:15433/alicebot \
DATABASE_URL=postgresql://alicebot_app:alicebot_app@127.0.0.1:15433/alicebot \
ALICE_LEGACY_SURFACES=1 \
./.venv/bin/pytest -q -p no:cacheprovider tests/integration

env -u ALICE_LEGACY_SURFACES -u ALICE_MCP_LEGACY_TOOLS \
  -u ALICE_AGENT_API_KEY \
  DATABASE_ADMIN_URL=postgresql://alicebot_admin:alicebot_admin@127.0.0.1:15433/alicebot \
  DATABASE_URL=postgresql://alicebot_app:alicebot_app@127.0.0.1:15433/alicebot \
  ./.venv/bin/pytest -q -p no:cacheprovider \
  tests/integration/test_default_surface_integration.py

./.venv/bin/pytest -q -p no:cacheprovider eval/longmemeval
./.venv/bin/python scripts/check_longmemeval_evidence.py
```

Web reproduction uses the pinned Node/pnpm versions:

```bash
cd apps/web
pnpm test
pnpm run test:coverage
pnpm run typecheck
pnpm run lint
pnpm run build
pnpm run test:budget
pnpm run test:browser
pnpm run test:advisory-audit
node scripts/npm-advisory-audit.mjs --prod --audit-level=high
node scripts/npm-advisory-audit.mjs --audit-level=high
```

Run package builds only into new temporary directories. Normalize the two
sdists before comparing, run Twine and `release_check.py --dist-dir`, then
install/smoke both artifact types. Use the exact command/result record inserted
into the final `BUILD_REPORT.md`; do not treat a stale top-level `dist/` as
evidence.

## Working-tree and receipt rules

- Preserve user-owned `uv.lock` and `coverage.json` byte-exact. They are not
  candidate evidence and are excluded from the receipt.
- The earlier accidental `uv`/environment mutation was restored. Continue to
  use direct `.venv` tools and verify the protected hashes before handoff.
- Do not create `REVIEW_REPORT.md` until the independent reviewer has inspected
  the exact receipt.
- Any edit outside the four receipt exclusions invalidates the receipt. Rerun
  affected gates, reconstruct the manifest independently twice, update the
  build report, and request a fresh review.
- Keep existing handoff directories, immutable release records, and migrations
  through `0090` untouched.
- Do not stage, commit, tag, publish, or mutate GitHub settings while verifying
  this uncommitted carrier.

## External release-engineer gates

After independent approval, the release engineer may commit and merge through
the protected flow. On that exact SHA:

1. run every required check and verify check-suite provenance;
2. apply/read back the prepared MainProtect required-check update;
3. require CodeQL target-zero response-hygiene evidence;
4. run the semantic release gate with the configured real embedding provider;
5. verify release identity, tag ancestry, and finalized GitHub Release body;
6. rebuild and compare final package artifacts, publish only their recorded
   checksums, and verify PyPI; and
7. close/supersede stale Dependabot PRs whose changes are now carried by main.

Stop after the Phase 2 handoff. Phase 3 begins only under its own brief.

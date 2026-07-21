# Phase 5 Enterprise Track Independent Review Report

## Conditional verdict

- **Code carrier (frozen): conditional GO.** The reviewed code and documentation
  delta has **no remaining P0-P3** finding. The exact bytes are flattened
  directly onto `c9d24243920a694eaf00ad595da392a1478710dd`, and the receipt
  has been reproduced in both full-history and depth-1/no-tag scratch commits.
  Release shippability remains conditional only on green committed-SHA CI and
  the owner gate stated below.
- **Phase 5 completion: NO-GO pending the 5.4 owner gate and green committed-SHA
  CI.** This report is not permission to tag or publish.
- **5.1.c OWNER DISPOSITION ACCEPTED.** The owner-approved claim is exactly
  "automated security scanning under OpenAI Trusted Access on the repository,
  plus internal adversarial review." Stage A and the retained Stage B history
  support only that bounded claim; they are not an external audit,
  certification, or independent security assurance.
- **5.4 OWNER GATE OPEN.** The real-host deployment receipt has not been
  supplied. Repository checks cannot prove live DNS, public-CA TLS, firewall
  policy, mTLS operation and rotation, production runtime roles, scheduled
  backups, or alert delivery.
- **COMMITTED-SHA CI GATE OPEN.** The replacement is intentionally uncommitted
  and unstaged. Gitleaks, the GitHub Advanced Security aggregate CodeQL gate,
  and the complete PR/main workflow matrix must pass on the fresh direct-on-base
  carrier commit.

## Carrier and receipt review

The failed carrier `e8d20189edfca5e9925cb3ed390e0621816899e7` and its
`4cf7e08b...` receipt are superseded and not shippable. I reviewed the
replacement delta against source commit
`c9d24243920a694eaf00ad595da392a1478710dd` and source tree
`ecc16a53f580308959e97e8b1f02edd04bbe3bfc`.

- The explicit receipt manifest contains 122 unique, bytewise-sorted paths.
- Two independent live reads each serialized 20,845 bytes and reproduced
  `94c990d7a67ebe1cd21e45a88a9cc850b06b3fefb2c372be9797e78b7a97dfb2`.
- Receipt-loop exclusions are limited to `BUILD_REPORT.md` and this
  reviewer-authored `REVIEW_REPORT.md`.
- Python and web versions remain `0.13.1`; the release engineer owns the later
  governed `0.14.0` cut.
- The protected SQLite `vnext_stores/sqlite/memory_access.py`, `docs/release`,
  prior handoffs, immutable release records, and the index are unchanged.
- The required replacement topology is one fresh carrier commit whose sole
  parent is `c9d2424`. The failed `e8d2018` carrier must not remain in ancestry,
  because a child commit cannot remove its leaked placeholder from the PR-range
  Gitleaks scan.

The receipt digest is stable for the frozen working-tree bytes and was proved
from both full-history and depth-1/no-tag receipt-trailed scratch commits after
flattening. This receipt is still not permission to tag or publish.

## CI defects reviewed

The replacement addresses all seven defects exposed by the first committed
carrier:

1. The handoff history guard skips missing-base lookups only in a genuinely
   shallow repository; a missing base in a full clone now fails closed.
2. The SQLite v0.12 baseline drill uses the authentic release tag when history
   exists and explicitly delegates only that history-dependent proof in a
   depth-1/no-tag checkout.
3. PostgreSQL evidence validates both required database URLs before release-tag
   discovery, for `postgres` and `all`, so configuration errors retain
   precedence even in a shallow clone.
4. `scripts/migrate.sh` validates `DATABASE_ADMIN_URL` before resolving the
   repository virtual environment, with an isolated fail-on-old test.
5. The browser-clipper transport test now uses a routed, script-free,
   same-origin fixture and asserts the exact captured payload, removing Next.js
   hydration as an unrelated source of flakiness.
6. The example browser-capability UUID is a deterministic non-nil sentinel that
   remains identical across web and API configuration without matching the
   Gitleaks generic-api-key detector. Exact Gitleaks 8.30.1 scanning over
   `c9d2424..HEAD` found no leak in the receipt-trailed scratch carrier; the
   authoritative GitHub workflow must repeat that result on the final commit.
7. The eight new GitHub Advanced Security alerts are addressed without
   suppressions or allowlists: the bookmarklet transports a strict two-layer
   percent-encoded configuration blob, the dangerous-scheme test covers all
   modeled schemes, and the deployment smoke test parses exact Caddy directive
   tokens rather than trusting URL substrings.

The first final shallow full-suite attempt then exposed one additional
test-order dependency: unrelated transient untracked artifacts could make a
clean receipt-trailed shallow commit look like a dirty live carrier. The guard
now filters only for receipt inputs and the two report exclusions when HEAD is
integrated. It still rejects any live receipt/report drift, while base-mode
freezing continues to require the exact carrier path set and an empty index. A
fail-on-old regression covers both the tolerated unrelated artifacts and the
rejected receipt-scoped paths.

For the CodeQL changes, I compared the implementation with the upstream query
and library models for `js/incomplete-url-scheme-check`,
`js/bad-code-sanitization`, and
`py/incomplete-url-substring-sanitization`. The rewritten sources and sinks are
absent or separated by an explicit sanitizer barrier, while hostile semantic
round-trip tests cover quotes, backslashes, literal percent escapes,
`</script>`, Unicode line separators, and non-ASCII text. This source review is
not a substitute for the fresh committed-SHA aggregate CodeQL result.

## Reproduced evidence

The frozen replacement passed the local matrix recorded in `BUILD_REPORT.md`:

- Python unit and coverage: 4,028 passed and 1 unrelated test skipped, with the
  still-unbound handoff-truth file excluded; 80.55% total coverage and the 45%
  API/router aggregate floor passed.
- History/ops contracts: 30 passed with full history; focused truth and topology
  checks passed 7; a real depth-1/no-tag checkout passed 29 ops tests with one
  expected baseline-upgrade delegation and 5 truth tests with 2 history-only
  skips.
- Final receipt-trailed history guards: full-history truth plus ops passed all
  45 tests; shallow truth plus ops passed 42 with 3 deliberate history-only
  skips.
- Final receipt-trailed shallow carrier: rev-count 1, no tags, and no base
  object. The full unit/coverage lane passed 4,034 tests with 10 skips in 154.56
  seconds at 80.55% total coverage; the exact 14-path router aggregate met the
  45% floor. Tracked and staged state remained clean; only standard ignored
  coverage and pytest artifacts were present.
- Deployment contracts: 53 passed, with only
  `owner_real_host_deployment_receipt` open.
- PostgreSQL integration: 407 passed and 1 skipped in 483.05 seconds against a
  disposable PostgreSQL 16.14 plus pgvector 0.8.5 instance, with an admin
  superuser and a separate non-superuser application role. The exact flag-off
  default surface executed 2 non-skipped tests and both passed.
- Web: 236 unit tests; 90.26% core and 81.85% vNext statement/line coverage;
  typecheck, lint, production build, and budgets passed.
- Browser postures: 24 passed; the hostile exact-payload clipper case also
  passed 10 consecutive repetitions.
- Evaluation lanes: 135 LongMemEval tests, all 7 evidence arms, 2 vector
  contracts, and all six model-free suites passed; the canonical release gate
  correctly failed closed without a vector provider.
- Control/static checks: release truth at `0.13.1`, Ruff, mypy over 228 files,
  compileall, Bash syntax, YAML parsing, and `git diff --check` passed.

Fresh GitHub Actions results remain intentionally outside this conditional
verdict until recorded from the authoritative committed-SHA runs.

## Remaining proof boundaries

Local Caddy and ShellCheck executables were unavailable. Tests cover the
checked-in Caddy contract, but actual Caddy parsing and all live-host properties
remain within the 5.4 owner receipt. The owner-accepted 5.1.c disposition also
does not turn Stage A, Stage B, OpenAI Trusted Access scanning, or internal
adversarial review into a claim that an external security assessment occurred.

Release engineering must now:

1. commit the exact flattened carrier directly on `c9d2424`, excluding the
   superseded carrier from ancestry;
2. include the required carrier and report receipt trailers;
3. run the complete PR/main
   matrix, including Gitleaks and the aggregate CodeQL check; and
4. keep Phase 5 completion at **NO-GO pending the 5.4 owner gate and green
   committed-SHA CI**.

Accordingly: **Code carrier conditional GO; Phase 5 completion NO-GO pending
the 5.4 owner gate and green committed-SHA CI.**

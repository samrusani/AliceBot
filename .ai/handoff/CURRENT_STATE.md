# Current State

## Snapshot

- `v0.10.2` is the latest published release. It is available from PyPI and
  GitHub, and its exact wheel and source-distribution digests are recorded in
  `docs/release/v0.10.2-checksums.txt`.
- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. It is a historical benchmark receipt, not a fresh v0.10.2
  measurement and not a repeated-run estimate.
- Alice is a local-first continuity layer for AI agents. Agent developers are
  the primary customer.
- `main` plus the reviewed remediation tree form the `v0.10.3` release
  candidate. It is unreleased until it passes exact-SHA gates, an annotated
  tag, PyPI publication, and the final GitHub Release through the
  transactional release workflow.

## What `v0.10.2` Shipped

`v0.10.2` carries the third-audit remediation and the corrected semantic release
gate. The published release includes:

- one signed-vector write contract across eval seeding and backfills;
- production-compatible vector participation evidence on all 48 vector queries;
- scope/status/domain/sensitivity-aware atomic capture deduplication;
- fail-closed lifecycle-cycle detection and duplicate-pointer repair;
- people/time predicates pushed into persistence with bulk edge resolution;
- iterative HNSW scanning with pgvector 0.8+ enforcement;
- full first-party mypy, web typecheck, browser/accessibility, coverage, package,
  and installed-artifact gates; and
- structured repository-control and semantic exact-SHA attestations.

The release notes and checksum record are the authoritative publication receipt:

- `docs/release/v0.10.2-release-notes.md`
- `docs/release/v0.10.2-checksums.txt`

## What `v0.10.3` Targets

The `v0.10.3` candidate remediates the fourth external audit's 13 confirmed
release-blocking findings and their independent-review correction passes:

- multi-project scope enforced through every synthesis, consolidation,
  scheduler, and retrieval path, with explicit `project_scope: []` treated as
  authoritative;
- coherent consolidation dedup (one active representative; legacy proposals
  repaired) and locked review/lifecycle transitions on every surface;
- inferred retrieval domains as disclosure-only ranking hints and scoped
  supplemental retrieval that deepens fail-closed instead of truncating;
- a real ChatGPT conversation parser (order, roles, branch-aware timestamps,
  one source per conversation);
- contained best-effort embedding/grounding failure boundaries, per-user
  fenced scheduler claims, durable idempotent response jobs, and provider I/O
  outside database transactions;
- bounded workspace/trace reads with authoritative counts, indexed capture
  dedupe, and a PostgreSQL connection pool (migrations `0087`–`0089`); and
- draft-first transactional publication, live ruleset auditing, mode-aware
  control-document truth, canonical coverage attribution with per-file
  floors, and per-operation OpenAPI contracts.

No unreleased change should be described as part of v0.10.2. The `v0.10.3`
candidate publishes only after independent review and the canonical release
gates pass on one exact clean SHA.

## Published Evidence

- The 2026-07-07 LongMemEval_s run, methodology, and per-question rows live
  under `docs/benchmarks/longmemeval/`.
- The result has not been replicated. Treat small single-run deltas as noise.
- The published scale envelope is a single-machine synthetic benchmark, not a
  concurrent load test.
- The v0.10.2 semantic release gate used Postgres/pgvector and an OpenAI
  `text-embedding-3-small` compatible 1536-dimensional endpoint. All 48 vector
  queries produced at least one signed candidate.

## Release Boundary

`v0.10.2` is tagged, published, and immutable. Its PyPI files carry Trusted
Publishing provenance, and their hashes match
`docs/release/v0.10.2-checksums.txt`. The source tag remains the release
boundary; later commits on `main` are not silently part of that release.

Future publication is transactional: exact-SHA preflight and semantic evidence
must pass, verified bytes are published to PyPI, and only then may the workflow
create the stable immutable GitHub Release with those same artifacts. A failed
PyPI step must never leave a new stable GitHub Release claiming availability.

## Product Boundaries

- Public-alpha, pre-1.0, local-first, single-user, and self-hosted.
- No hosted service or SLA.
- Gmail and Calendar have manual operator-token backends, but Alice does not
  provide a managed OAuth consent/account-linking flow or automatic polling.
- No silent capture from arbitrary conversations.
- Durable agent writes remain policy-checked and reviewable.

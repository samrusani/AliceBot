# Current State

## Snapshot

- `v0.10.4` is the latest published release. It is available from PyPI and
  GitHub, and its exact wheel and source-distribution digests are recorded in
  `docs/release/v0.10.4-checksums.txt`.
- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. It is a historical benchmark receipt, not a measurement of the
  current release and not a repeated-run estimate.
- Alice is a local-first continuity layer for AI agents. Agent developers are
  the primary customer.
- The fourth-audit remediation shipped in `v0.10.3` through the
  transactional draft-first release workflow: exact-SHA gates, an annotated
  tag, PyPI publication, then the finalized GitHub Release.

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

## What `v0.10.3` Shipped

`v0.10.3` remediates the fourth external audit's 13 confirmed
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

The release notes and checksum record are the authoritative publication
receipt:

- `docs/release/v0.10.3-release-notes.md`
- `docs/release/v0.10.3-checksums.txt`

## What `v0.10.4` Shipped

`v0.10.4` remediates the fifth external audit's confirmed findings and fixes
forward without changing the immutable v0.10.3 tag, release notes, checksums,
or published artifacts. The published release includes:

- workspace-explicit hosted settings operations;
- coupled project-update review across HTTP, MCP, CLI, lifecycle, and both
  stores, including a terminal replay proof that requires exactly one total
  artifact/candidate-coupled accepted/rejected decision event before outcome,
  actor, action, target, payload, or redaction validation;
- complete persisted-source envelope precedence across SQLite and PostgreSQL
  source/parent-chunk search, retrieval admission, shared Brain/Projects/
  Connections/Contradictions services, and HTTP artifact-trace authorization,
  including authoritative embedded empty scope;
- runtime-true OpenAPI response contracts and no-auth OpenAI-compatible
  invocation;
- publication-neutral package metadata plus stricter release-document truth;
- canonical project identity, embedding compare-and-swap parity, and preserved
  configured API base paths; and
- documentation and product-surface corrections, reviewer attribution, and
  migration preflight guidance.

Repair Batch 9 narrowed eight findings returned by the independent review of
Repair Batch 8. It validates capture identity across fast, hash, and atomic
dedupe paths; maintains stale dedupe keys atomically; applies key-bound policy
to the core MCP `alice_explain` memory, provenance, entity, and continuity
branches; binds terminal candidate-created evidence to the locked artifact;
normalizes finite mathematically integral numeric project identifiers while
rejecting fractional and non-finite numbers; preserves the established
explicit `true`/`false` scalar identifiers; scopes the legacy context tree's
five resource groups plus events; bounds open-loop/resume rows before limits;
and supplies protected-path upgrade metadata plus control-document truth
checks.

Repair Batch 9 builder verification was green: 3,301 Python units at
75.67% coverage, the 52.63% `main.py` floor, 455 role-separated PostgreSQL
integrations, 127 model-free LongMemEval tests plus evidence replay, the full
280-test/10-browser-case web matrix, release-static, and two byte-identical
fresh package builds with isolated wheel/sdist smokes. Focused seam, migration,
control-truth, and protected-path checks also passed, and its final repository
fingerprints were reproduced twice. Its subsequent independent review returned
changes required on five bounded findings, so neither Batch 9 nor Batch 8's
historical gates and fingerprints approve the current tree.

Repair Batch 10 failed closed on dangling
memory supersession pointers before explanation envelopes are read, makes
nested canonical project scope authoritative in generic PostgreSQL resource
predicates, pushes resume status/project/time/query predicates before limits,
joins recent events to scope-admitted memories and open loops before event
limits, and corrects the context-tree and freeze documentation. Builder
verification is green: 3,325 Python units at 75.71% coverage and 52.63% for
`main.py`, 457 role-separated PostgreSQL integrations, a 1,171-test integrated
seam, 127 LongMemEval tests plus evidence replay, release-static, the unchanged
202-input web carrier, and two byte-identical fresh package builds with
isolated wheel/sdist smokes. Its final tracked-patch and bundle fingerprints
were reproduced twice. The subsequent independent review returned changes
required on exactly two bounded findings, so those results and hashes are now
historical and do not approve the current tree.

Repair Batch 11 corrected PostgreSQL persisted-source predicates and migration
`0090` to choose nested `agentic_memory` or
`agent_identity.project_scope` by key presence, so blank, null, malformed, or
fractional nested values cannot resurrect stale aliases. `alice_resume.query`
now filters open-loop rows and their event joins before limits in both stores,
including scoped and unscoped calls and payload-only event matches. Builder
verification is green: 3,327 units at 75.72% branch-inclusive coverage with
`main.py` at 52.63% against its 45% floor, 460 role-separated PostgreSQL
integrations, the 595-test owned/shared seam, 127 LongMemEval tests plus
evidence replay, and release-static passed. The exact unchanged 202-input web
carrier retains its full prior matrix. Two fresh package builds were
byte-identical; Twine, release-check, seven-file archive parity, and isolated
wheel/sdist smokes passed. Final tracked-patch and bundle fingerprints were
reproduced twice. Independent review then approved persisted-source closure
and every other bounded area, but returned changes required on one P2: event
payload query matching also admitted JSON key names. Batch 11 evidence is
historical and does not approve the current tree.

Repair Batch 12 corrected resume-event payload queries: SQLite uses
`json_tree`, and PostgreSQL uses recursive `jsonb_path_query`, so they match
only string leaf values. Nested object and array strings
participate; keys, numbers, booleans, nulls, and serialization punctuation do
not. Scoped/unscoped, row-field, status/time/scope-before-limit, event ordering,
and queryless behavior are preserved. Builder verification is green: 3,327
units at 75.72% branch-inclusive coverage with `main.py` at 52.63% against its
45% floor, 460 role-separated PostgreSQL integrations, release-static, 127
LongMemEval tests plus evidence, and the exact unchanged web carrier passed.
Two fresh package builds were byte-identical; Twine, release-check, seven-file
archive parity, and isolated wheel/sdist smokes passed. Final tracked-patch and
bundle fingerprints were reproduced twice. Independent review approved the
production closure and every other bounded area, but returned changes required
on one test-fake P2: separate string leaves were concatenated before matching.
Batch 12 evidence is historical and does not approve the current tree.

Repair Batch 13 was an unfrozen test-only candidate. `FakeVNextMCPStore`
stopped concatenating separate recursive string leaves, and focused fake/
real-SQLite parity, all 256 MCP units, and the complete 3,328-unit coverage
gate passed. Exact production hashes allowed the R12 460-case PostgreSQL
result to be carried without rerunning it. Before final documentation,
packages, or fingerprints were bound, independent review found that SQLite's
ASCII-only `lower()`, PostgreSQL's locale-aware `lower()`, and Python
`casefold()` disagreed for non-ASCII queries. Batch 13 was never frozen and
does not approve the current tree.

Repair Batch 14 was a frozen bounded correction. Resume open-loop row and
event-string-leaf queries use ASCII case-insensitive literal substring
matching in SQLite, PostgreSQL, and the MCP fake. Non-ASCII code points match
exactly without Unicode normalization or deployment-locale dependence; `%`,
`_`, and `\\` are literal query characters rather than SQL wildcards. Each
event string leaf remains independent, blank queries remain unfiltered, and
scope, status, time, and query predicates still run before limits with event
ordering preserved. Builder verification is green: 3,329 units passed at
75.73% branch-inclusive coverage with `main.py` at 52.63% against its 45%
floor, and all 461 role-separated PostgreSQL integrations passed. Release-
static, 127 LongMemEval tests plus evidence replay, and exact unchanged web
carrier readback passed. Two fresh package builds were byte-identical; Twine,
release-check, seven-file archive parity, and isolated wheel/sdist smokes
passed. The tracked-patch and fixed 12-file remediation-bundle fingerprints
have now reproduced twice and are recorded in the self-excluded builder
report. Independent review then returned changes required on three bounded
P2s: non-string root/nested `next_action` metadata could become a SQL row
candidate while the fake rejected it; the MCP documentation overextended the
open-loop comparison contract to memory search; and fake open-loop ordering
omitted the `created_at` tie-breaker. Batch 14 evidence is historical and does
not approve the current tree.

Repair Batch 15 was a bounded correction. Open-loop row search admits
root and nested `next_action` metadata only when the JSON value is a string;
loop-event payload search remains recursive over individual string leaf values
only. The ASCII-only, exact-non-ASCII, literal-substring contract is documented
only for open-loop row fields and loop-event leaves, not decision/next-action
memory search. `FakeVNextMCPStore.list_open_loops` mirrors production ordering
by `opened_at`, `created_at`, then `id`, all descending. Builder verification
is green: 3,331 units passed at 75.72% branch-aware coverage with `main.py` at
52.63% branch-aware coverage against its 45% statement floor, and all 461
role-separated PostgreSQL integrations passed. Release-static, 127 LongMemEval
tests plus evidence replay, and exact unchanged web-carrier readback passed.
Two fresh package builds were byte-identical; Twine, release-check, seven-file
archive parity, and isolated wheel/sdist smokes passed. The final tracked-patch
and fixed 12-file remediation-bundle fingerprints were reproduced twice and
are recorded in the self-excluded builder report. Independent review approved
that exact carrier, but a subsequent engineering-team readback found that the
embedding CAS still used PostgreSQL's locale-dependent POSIX whitespace class
even though migration `0090` already encoded Python's deterministic
`str.strip()` table. Batch 15 approval is therefore historical and cannot
approve the current tree.

Repair Batch 16 is the current bounded correction. The PostgreSQL memory-
embedding content digest now trims title, canonical text, and summary with the
same explicit CPython 3.12 29-codepoint `chr()` table as migration `0090`,
including U+001C–U+001F, NEL, and NBSP. It preserves the existing blank
omission, first-occurrence deduplication, LF join, and SHA-256 semantics. A
fail-on-old SQL-shape test proves that signed vector freshness, embedding
update CAS, and missing-embedding selection all use the deterministic table
and contain no POSIX trim. Live role-separated PostgreSQL regressions cover
NBSP, U+001C, and mixed blank/deduplicated fields through CAS acceptance,
no-reembed-loop selection, and signed vector participation. The full Batch 16
matrix passed 3,332 units with coverage floors, 463 role-separated PostgreSQL
integrations, release-static/control, 127 LongMemEval tests plus evidence
replay, unchanged-web readback, and two byte-identical package builds with
Twine, release-check, seven-file archive parity, and isolated smokes. Final
carrier fingerprints reproduced twice and are recorded in the self-excluded
builder report. Batch 16 review approved the production CAS semantics and
returned changes required on one documentation-truth P3. Refreeze 17 changes
only the stale Batch 15/current-review wording plus its fail-on-old control
guard; independent review of the Refreeze 17 carrier remains required.
Clean-SHA artifact and semantic gates remain release-engineer requirements.

## Published Evidence

- The 2026-07-07 LongMemEval_s run, methodology, and per-question rows live
  under `docs/benchmarks/longmemeval/`.
- The result has not been replicated. Treat small single-run deltas as noise.
- The published scale envelope is a single-machine synthetic benchmark, not a
  concurrent load test.
- The v0.10.3 semantic release gate used Postgres/pgvector and an OpenAI
  `text-embedding-3-small` compatible 1536-dimensional endpoint. All 48 vector
  queries produced at least one signed candidate.

## Release Boundary

`v0.10.3` is tagged, published, and immutable. Its PyPI files carry Trusted
Publishing provenance, and their hashes match
`docs/release/v0.10.3-checksums.txt`. The source tag remains the release
boundary; later commits on `main` are not silently part of that release.

`v0.10.4` is tagged, published, and immutable. Its release record is
authoritative:

- `docs/release/v0.10.4-release-notes.md`
- `docs/release/v0.10.4-checksums.txt`

Superseded text (historical): the remediation tree was a candidate with no tag,
checksum receipt, PyPI files, or GitHub Release and must not be described as
published before those external facts exist.

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

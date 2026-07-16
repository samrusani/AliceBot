# Current State

## Snapshot

- `v0.11.1` is the current uncommitted Phase 2 release-hardening candidate.
  At package-input freeze, its bounded local builder matrix was green while
  final package reproduction, a superseding carrier receipt, and independent
  review were still pending. Exact-SHA external release gates remain pending.
- `v0.11.0` is the latest published release. It is available from PyPI and
  GitHub; exact artifact digests are in
  `docs/release/v0.11.0-checksums.txt`.
- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. It is not a repeated estimate or a measurement of this candidate.
- Alice remains public-alpha, pre-1.0, local-first, single-user, and self-hosted.

## What `v0.11.1` Changes

- Adds a required real-PostgreSQL smoke for the default surface with legacy and
  agent-key mount flags absent. It exercises bootstrap, capture, recall,
  resume, context-pack, and review through the retained core.
- Replaces exception-derived public HTTP, MCP, CLI, and onramp failures, plus
  the migrated provider, response, scheduler, evaluation, doctor, and connector
  diagnostics, with stable codes and static messages while preserving private
  server-side detail. Intentional legacy-on `proxy_execution.py` business-
  result reasons remain dynamic and are explicitly excluded from this
  diagnostic migration.
- Aligns the `list_memories(query=...)` and
  `list_resume_memory_events(query=...)` legs used by recent decisions and
  resume with open-loop ASCII case-insensitive literal filtering across
  PostgreSQL, SQLite, and test fakes. Generic `search_memories` and
  `alice_recall` FTS/websearch semantics remain separate and unchanged.
- Bounds terminal project-update replay with target-filtered store lookups and
  indexed linkage, makes reject fail closed on a missing candidate memory key,
  and blocks generic review/correct/forget paths from stranding a pending
  project-update candidate.
- Implements the owner-selected coupled true-redaction design. Terminal
  artifacts, free-text quality feedback, provenance quotes, memories,
  revisions, and decision events converge on exact content-free skeletons;
  numeric quality ratings retain their structural audit value, and accepted
  project state is not rolled back. Source and source-chunk evidence is not
  changed by memory redaction because either may support other memories.
- Adds defensive, locale-independent source-identity normalization; removes
  unknown-filter swallowing from store fakes; declares the coverage feature
  floor; and binds release/workflow shape to executable tests.
- Trims unused response-generation wrappers around retained provider
  invocation, preserves the fail-closed pnpm bulk-advisory wrapper, and updates
  accepted CI action pins without importing rejected major dependency changes.
- Records the Phase 1 directory/documentation riders as already satisfied and
  the removed entrypoint rate limiter's shared-Redis issue as obsolete after
  re-measurement.

## Verification Posture

- At package-input freeze, the implementation tree was intentionally
  uncommitted. The local builder run
  passed 3,547 unit tests; reported 79.4009% total and 62.9591% `main.py`
  coverage; passed 399 role-separated PostgreSQL integration tests with one
  documented skip plus the separate flag-off smoke; passed 127 LongMemEval
  tests and all 78 provider-free SQLite eval cases; and passed 217 web unit
  tests plus 20 browser tests, type, lint, build, budgets, and both advisory
  modes.
- The isolated health scan reported overall 34.3-34.4, objective 85.8-85.9,
  and code-quality 83.1 (82.9 strict). Its overall variation comes from a
  documented nondeterministic basename-only test-to-source mapping, not a
  candidate change.
- At package-input freeze, final wheel/sdist reproduction, the twice-
  reproduced superseding receipt, and independent review were still pending;
  their final outcomes belong in the Phase 2 build and review reports.
- The post-cut external CodeQL baseline was re-measured separately from local
  source repair. GitHub alert closure cannot be claimed until the candidate is
  committed, pushed, and scanned on its exact SHA.
- OpenAPI remains fail-closed: every mounted operation needs an explicit
  contract, every contract must map to a mounted operation, and phantom keys are
  rejected.
- OCR and transcription execution remain out of scope. Connectors accept text
  payloads extracted by external tools.

## Release Boundary

`v0.11.0` is tagged, published, and immutable. Its authoritative records are:

- `docs/release/v0.11.0-release-notes.md`
- `docs/release/v0.11.0-checksums.txt`

`docs/release/v0.11.1-release-notes.md` is a pending candidate record. There is
no `v0.11.1` checksum record while publication is pending, and the candidate
documents do not authorize a tag or upload.

`v0.10.4` is the prior published release; its records remain at
`docs/release/v0.10.4-release-notes.md` and `docs/release/v0.10.4-checksums.txt`.

## Product Boundaries

- No hosted service, multi-tenant control plane, or SLA.
- No managed OAuth consent/account-linking or automatic account polling.
- No Telegram or other channel transport in the current runtime.
- No public bundled chat/response product, chief-of-staff product, or model
  packs. Internal response jobs support retained provider invocation only.
- No silent capture from arbitrary conversations.
- No OCR or transcription execution; Alice only ingests extracted text.
- Durable agent writes remain policy-checked, provenance-linked, and reviewable.
- Coupled true redaction scrubs governed content copies in the memory/project-
  update graph; it does not undo an accepted update already applied to project
  state. Alice source/source-chunk evidence remains unchanged because it may be
  shared and requires separate source hygiene. Upstream source systems,
  exports, and backups remain separate operator obligations.

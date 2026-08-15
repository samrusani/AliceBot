# Current State

## Snapshot

- `v0.15.4` is the latest published release. It is available from PyPI and
  its record is immutable. `v0.13.1` is the prior published release, and
  GitHub; exact artifact digests are in
  `docs/release/v0.15.4-checksums.txt`. `v0.13.1` shipped the Phase 4
  core-roadmap work with the exact release headline **Replicated
  benchmark, faster SQLite at scale, reference integrations.** The
  `v0.13.0` tag exists but was never published (superseded; see the
  release notes).
- `v0.12.0` is the prior published release; its records remain under
  `docs/release/`.
- `v0.12.0` shipped the Phase 3 structural refactor, with the exact release
  headline **Structure only. Zero behavior change.**
- Phase 3 implementation and the bounded builder matrix completed on
  `codex/v0120-phase3-structural-refactor`, based on
  `f342d45dabe127acca6231f29830ff11d98a340e`. Each code increment received an
  independent GO with no remaining P0-P3 finding. The independent final verdict
  is owned only by the handoff's `REVIEW_REPORT.md`; the exact-SHA external
  release gates passed on the release commit.
- Both governed version sources were cut to `0.12.0` by the release engineer
  after verifying the handoff.
- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. It is not a repeated estimate or a measurement of this release.
- Alice remains public-alpha, pre-1.0, local-first, single-user, and self-hosted.

## What `v0.11.1` Shipped

`v0.11.1` shipped the bounded Phase 2 debt sweep on the post-periphery-cut
product surface. Its immutable release notes and checksums remain the
authoritative description; Phase 3 does not rewrite that history.

- Stable HTTP, MCP, CLI, and onramp failures, plus the migrated provider,
  response, scheduler, evaluation, doctor, and connector diagnostics, keep
  static public vocabularies. Intentional legacy-on `proxy_execution.py`
  business-result reasons remain dynamic.
- The `list_memories(query=...)` and
  `list_resume_memory_events(query=...)` legs keep their ASCII case-insensitive
  literal-filter contract; generic `alice_recall` retrieval remains separate.
- Coupled true redaction scrubs the governed memory/project-update graph but
  retains shared source/source-chunk evidence for separate source hygiene and
  does not roll back accepted project state.

## What `v0.12.0` Shipped

- A thin `alicebot_api.main:app` assembly module with the HTTP handlers moved
  into domain routers. Default and gated OpenAPI registries remain exactly 182
  and 231 operations, a delta of 49.
- Corresponding PostgreSQL and SQLite vNext store seams, a surviving-domain
  legacy-store split, and stable store facades. Generated SQL text and store
  protocols are unchanged.
- Domain contract modules behind the stable `contracts.py` facade.
- Per-domain MCP implementations behind the stable `mcp_tools.py` facade,
  preserving the 11-core/65-legacy/76-total registry and flag behavior.
- Per-domain CLI command modules behind the stable `alicebot_api.cli` import,
  preserving both `alice` and `alicebot` entrypoints; `alice-memory` remains
  routed through the onramp entrypoint.
- Response-hygiene and coverage enforcement that follows moved modules rather
  than shrinking onto a facade. The 296 public-response call inventory and the
  router aggregate coverage floor remain pinned.
- No route, tool, command, schema, migration, dependency, or runtime behavior
  change.

## Verification Posture

- Final code-carrier evidence passed 3,804 unit tests with 80.3777897% package
  coverage. Router coverage was 3,604/5,373 statements, 67.0761%, above the
  45% floor.
- PostgreSQL 16 plus pgvector passed 399 legacy-on integration tests with one
  expected skip. The separate flag-off smoke passed one executed test with the
  nonzero-test guard enabled.
- LongMemEval passed 127 tests; the checked evidence replay passed seven arms;
  the focused vector/retrieval lane passed two tests.
- The web carrier passed 217 unit tests, core and vNext coverage floors,
  typecheck, lint, build, bundle budgets, and the 17+1+1+1 browser matrix.
- Final-carrier package reproduction and installed-artifact evidence is owned
  by the Phase 3 `BUILD_REPORT.md`. The builder matrix ran before the version
  cut; its locally produced artifacts were verification inputs only and were
  never uploaded anywhere.
- No security or cybersecurity audit was performed in Phase 3.

## Release Boundary

`v0.15.4` is tagged, published, and immutable. Its authoritative records are:

- `docs/release/v0.15.4-release-notes.md`
- `docs/release/v0.15.4-checksums.txt`

`v0.13.1` remains published and immutable; its records are
`docs/release/v0.13.1-release-notes.md` and `docs/release/v0.13.1-checksums.txt`.

The `v0.13.0` tag exists but was never published; the number was
superseded by `v0.13.1` because stable tags are immutable.

`v0.12.0` is the prior published release; its records remain at
`docs/release/v0.12.0-release-notes.md` and
`docs/release/v0.12.0-checksums.txt`.

`v0.11.1` is the prior published release; its records remain at
`docs/release/v0.11.1-release-notes.md` and
`docs/release/v0.11.1-checksums.txt`.

## What `v0.14.0` Shipped

The Phase 5 enterprise track: the single-tenant self-hosted deployment
contract executed on a real public host with an owner deployment receipt,
least-privilege operations proven under a non-superuser admin role, executed
backup and restore evidence on both backends, the one-time origin-bound
browser-clip capability, and the five deployment-guide fixes surfaced by the
first real-host execution. Scope details are in the dated handoff packages and
the `v0.14.0` release notes.

## What `v0.13.1` Shipped

- The replicated LongMemEval_s baseline (81.2% mean over three runs on the
  published `v0.12.0` code) committed as per-question evidence.
- SQLite vector-scale work: bit-identical vectorized scan, resident vector
  cache with transactional stamp invalidation (vector stage 385-465ms warm
  at 100k inside 754MB peak / 760MB steady, 1024MB default cap,
  off-switch), one additive bootstrap table, Postgres unchanged.
- Two CI-smoked reference integrations: the MCP quickstart and the OpenAI
  Agents SDK function-tool example with real per-agent key auth.
- Trace-only count-intent diagnostics behind the aggregation gate
  (is_answer=false); the multi-session benchmark-closure NO-GO is recorded
  and no synthesis uplift is claimed.
- The deferred mcp-tools.md legacy-alias wording correction.
- No MCP registry, OpenAPI, HTTP route, dependency, or Postgres schema
  change.

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
  update graph; it does not undo accepted project state or erase shared source
  evidence, upstream systems, exports, backups, or external logs.

## What `v0.15.4` Shipped

`v0.15.4` is the latest published release and remains the install, checksum,
and baseline reference.

The `v0.15.0` tag exists but was never published. The commit it points at
carried a release-gate step that could not run on a CI runner, so the gate
could never pass from that tag, and repository rules correctly refuse both
deletion and update of stable tags. No GitHub Release or PyPI artifact was
ever created for it.

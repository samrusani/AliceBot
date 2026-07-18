# Current State

## Snapshot

- `v0.11.1` is the latest published release. It is tagged and immutable; its
  authoritative release notes and artifact digests are under `docs/release/`.
- The `v0.12.0` candidate carries the Phase 3 structural refactor, with the exact release
  headline **Structure only. Zero behavior change.**
- Phase 3 implementation and the bounded builder matrix are complete on
  `codex/v0120-phase3-structural-refactor`, based on
  `f342d45dabe127acca6231f29830ff11d98a340e`. Each code increment received an
  independent GO with no remaining P0-P3 finding. The independent final verdict
  is owned only by the handoff's `REVIEW_REPORT.md`; exact-SHA external release
  gates remain pending.
- Both governed version sources are cut to `0.12.0` by the release engineer
  after verifying the handoff.
- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. It is not a repeated estimate or a measurement of this carrier.
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

## What `v0.12.0` Targets

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
  by the Phase 3 `BUILD_REPORT.md`. Any resulting candidate-version `0.11.1`
  artifacts are verification inputs only: they are not `v0.12.0` release
  artifacts and must not be published.
- No security or cybersecurity audit was performed in Phase 3.

## Release Boundary

`v0.11.1` is tagged, published, and immutable. Its authoritative records are:

- `docs/release/v0.11.1-release-notes.md`
- `docs/release/v0.11.1-checksums.txt`

The pending `docs/release/v0.12.0-release-notes.md` is a candidate document,
not a publication receipt. There is no v0.12.0 checksum file, release SHA, tag,
GitHub Release, or PyPI publication yet. The release engineer must bind those
states to the final committed SHA and read them back before declaring v0.12.0
published.

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

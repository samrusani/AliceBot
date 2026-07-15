# Sprint Packet

<!-- alice-sprint-scope: phase-1-only -->

## Sprint

Alice v0.11.0 Phase 1 periphery cut and product-identity reconciliation.

## Status

Implementation and review are active on `codex/v011-phase1-periphery-cut`,
based on published/post-publication `main` at `8520f29`. This packet authorizes
Phase 1 only. It does not authorize a commit, push, merge, tag, PyPI upload, or
GitHub Release.

## Reason

Alice's default runtime had accumulated hosted, channel, chat, and product
surfaces outside the owner-set thesis: a small interface for existing agents and
top-quality retrieval/memory. The cut removes that periphery before later debt,
refactor, benchmark, or enterprise work, reducing maintenance and making docs,
tests, OpenAPI, and product identity agree.

## In scope

- delete Telegram channels and transport;
- delete hosted admin/design-partner and hosted auth/session/device/workspace
  control-plane surfaces while retaining the single local workspace bootstrap;
- delete chief-of-staff, bundled chat/model-pack, and the public response
  surface; retain internal response jobs for `/v1/runtime/invoke` idempotency
  and gate the surviving proxy/execution compatibility surface;
- mount task/approval/execution and Gmail/Calendar compatibility only when
  `ALICE_LEGACY_SURFACES=1` is explicitly enabled;
- delete legacy MCP/CLI/web/OpenAPI surfaces with their backing services;
  retain long-tail memory MCP tools behind `ALICE_MCP_LEGACY_TOOLS=1`, with
  only the three task-brief tools additionally gated by
  `ALICE_LEGACY_SURFACES=1`;
- retain provider support needed for embeddings, discovery, secrets, and
  surviving model-backed memory operations;
- retire surface-era tests while preserving immutable migration tests;
- rewrite architecture, rules, roadmap, current-state, release, extracted-text,
  and control-document truth;
- Text extraction happens outside Alice.
  Alice does not perform OCR or transcription.
- update the fail-closed OpenAPI registry to the post-cut mounted inventory;
- produce an uncommitted builder handoff and independent review.

## Out of scope

- Phase 2 correctness/debt items, even if nearby;
- the Phase 3 structural router/store refactor;
- new retrieval features or benchmark tuning;
- cybersecurity review;
- destructive migration edits or changes to immutable v0.10.2/v0.10.3/v0.10.4
  tags, release notes, checksums, or published artifacts;
- publication, tagging, pushing, merging, or repository-setting changes.

## Required gates

1. A written all-surface inventory covers HTTP, MCP, CLI, scheduler, web,
   PostgreSQL, and SQLite before implementation claims closure.
2. Default-mode fail-on-old tests prove every removed or compatibility surface
   is absent; explicit-flag tests prove only the documented compatibility subset
   mounts.
3. Existing migrations remain byte-identical and their migration tests remain.
4. OpenAPI closure, phantom-key rejection, and the exact post-cut operation
   count pass.
5. Python unit/integration/coverage/static gates, both-store contracts,
   LongMemEval model-free/evidence gates, and the full web matrix pass without
   lowering thresholds.
6. Reproducible wheel/sdist, archive parity, release-check, and installed-
   artifact smokes pass for the same frozen tree.
7. Documentation and runtime inventories agree on the caller-supplied
   extracted-text boundary and archived repair history.
8. An independent reviewer approves the exact uncommitted carrier.

## Handoff

- `docs/handoff/2026-07-15-v0.11.0-phase1-periphery-cut/SURFACE_INVENTORY.md`
- `docs/handoff/2026-07-15-v0.11.0-phase1-periphery-cut/FIX_MATRIX.md`
- `docs/handoff/2026-07-15-v0.11.0-phase1-periphery-cut/BUILD_REPORT.md`
- `docs/handoff/2026-07-15-v0.11.0-phase1-periphery-cut/ENGINEER_HANDOFF.md`
- `docs/handoff/2026-07-15-v0.11.0-phase1-periphery-cut/REVIEW_REPORT.md`
  (reviewer-owned)

## Exit condition

Phase 1 is complete only when every scoped disposition is implemented and
documented, the required matrix is green on one frozen uncommitted tree, and the
independent reviewer reports no blocker.

Stop after that handoff; do not begin Phase 2.

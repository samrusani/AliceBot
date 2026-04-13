# BUILD_REPORT

## sprint objective
Implement Bridge Sprint 3 (`B3`) review queue + explainability scope:
- ship `alice_review_queue`
- ship `alice_review_apply`
- support review actions (`approve`, `reject`, `edit-and-approve`, `supersede-existing`)
- expose explanation/provenance rationale in review surfaces
- verify deterministic recall/resume effects after approved review actions

## completed work
- Added MCP tool surface `alice_review_queue` with deterministic queue/detail behavior.
- Added MCP tool surface `alice_review_apply` with B3 action vocabulary mapped to continuity correction semantics:
  - `approve` -> `confirm`
  - `edit-and-approve` -> `edit`
  - `reject` -> `delete`
  - `supersede-existing` -> `supersede`
- Kept `alice_memory_review` and `alice_memory_correct` as compatibility aliases.
- Extended continuity review serialization to include shared explanation records on review objects.
- Added deterministic `proposal_rationale` to continuity explanation output.
- Ensured explanation chain remains shared across review, recall, and resume paths.
- Updated B3-scoped integration docs for MCP and Hermes memory-provider guidance.
- Updated architecture status markers so B3 review surfaces are marked implemented and only B4 follow-up remains planned.
- Updated control-doc truth checker markers to B3 active-sprint truth.
- Updated B3 review evidence report (`REVIEW_REPORT.md`).
- Added/updated sprint-owned tests for:
  - MCP tool surface and B3 names
  - action alias mapping and deterministic correction semantics
  - review queue explainability presence
  - recall exclusion after reject and recall/resume updates after supersede

## incomplete work
- None in B3 sprint scope.

## files changed
- `ARCHITECTURE.md`
- `PRODUCT_BRIEF.md`
- `README.md`
- `ROADMAP.md`
- `apps/api/src/alicebot_api/continuity_explainability.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/mcp_tools.py`
- `docs/integrations/mcp.md`
- `docs/integrations/hermes-memory-provider.md`
- `scripts/check_control_doc_truth.py`
- `tests/unit/test_continuity_review.py`
- `tests/unit/test_mcp.py`
- `tests/integration/test_mcp_server.py`
- `REVIEW_REPORT.md`
- `BUILD_REPORT.md`

## tests run
- `python3 scripts/check_control_doc_truth.py`
  - Result: PASS
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - Result: `1189 passed in 196.98s (0:03:16)` (latest re-run)
- `./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py`
  - Result: PASS
  - Evidence summary: single-external-provider enforcement message emitted; structural payload reports `single_external_enforced=true` and `bridge_status.ready=true`.
  - Local filesystem-specific path fields from script output were intentionally omitted for identifier hygiene.

## blockers/issues
- No functional blockers.
- No outstanding evidence or documentation blockers after alignment updates.

## recommended next step
Proceed to Bridge Sprint 4 (`B4`) packaging/docs/smoke closeout using the now-shipped B3 review queue/apply surfaces as baseline.

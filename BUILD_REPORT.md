# BUILD_REPORT

## sprint objective
Deliver Bridge Sprint 4 (`B4`) closeout scope only: package and document the shipped bridge phase for external operators, publish recommended/fallback Hermes config guidance, strengthen bridge smoke validation evidence, and provide a one-command local demo path.

## completed work
- Published canonical B4 operator guide: `docs/integrations/hermes-bridge-operator-guide.md`.
- Published operator decision note: `docs/integrations/hermes-provider-plus-mcp-why.md`.
- Published concrete Hermes `config.yaml` examples:
  - recommended path: `docs/integrations/examples/hermes-config.provider-plus-mcp.yaml`
  - fallback path: `docs/integrations/examples/hermes-config.mcp-only.yaml`
- Updated in-scope integration docs (`README.md`, `hermes.md`, `hermes-memory-provider.md`, `mcp.md`, `hermes-skill-pack.md`) to align on:
  - recommended path: provider plus MCP
  - fallback path: MCP-only
  - migration path from MCP-only to provider plus MCP
  - one-command demo command: `./.venv/bin/python scripts/run_hermes_bridge_demo.py`
- Strengthened `scripts/run_hermes_mcp_smoke.py` to validate bridge flow beyond recall/resume/open-loops by also validating B2/B3 capture and review operations (`alice_capture_candidates`, `alice_commit_captures`, `alice_review_queue`, `alice_review_apply`).
- Added one-command demo helper: `scripts/run_hermes_bridge_demo.py`.
- Added sprint-owned validation coverage for the demo helper: `tests/unit/test_hermes_bridge_demo.py`.
- Updated `scripts/check_control_doc_truth.py` required markers to B4-active truth so the required verifier aligns with the active sprint packet.
- Updated `REVIEW_REPORT.md` to grade against B4-specific acceptance criteria and evidence.

## incomplete work
- None within B4 sprint scope.

## files changed
- `PRODUCT_BRIEF.md`
- `README.md`
- `ROADMAP.md`
- `docs/integrations/hermes-memory-provider.md`
- `docs/integrations/hermes-skill-pack.md`
- `docs/integrations/hermes.md`
- `docs/integrations/mcp.md`
- `docs/integrations/hermes-bridge-operator-guide.md`
- `docs/integrations/hermes-provider-plus-mcp-why.md`
- `docs/integrations/examples/hermes-config.provider-plus-mcp.yaml`
- `docs/integrations/examples/hermes-config.mcp-only.yaml`
- `scripts/run_hermes_mcp_smoke.py`
- `scripts/run_hermes_bridge_demo.py`
- `scripts/check_control_doc_truth.py`
- `tests/unit/test_hermes_bridge_demo.py`
- `REVIEW_REPORT.md`
- `BUILD_REPORT.md`

## tests run
- `python3 scripts/check_control_doc_truth.py`
  - Result: PASS
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - Result: `1191 passed in 187.48s (0:03:07)`
- `./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py`
  - Result: PASS
  - Evidence summary: `bridge_status.ready=true`, `single_external_enforced=true`, provider registered.
- `./.venv/bin/python scripts/run_hermes_mcp_smoke.py`
  - Result: PASS
  - Evidence summary: required Hermes MCP tools registered, `recall_items=2`, `open_loop_count=1`, `capture_candidate_count=2`, `capture_auto_saved_count=1`, `capture_review_queued_count=1`, `review_apply_resolved_action=confirm`.
- `./.venv/bin/python scripts/run_hermes_bridge_demo.py`
  - Result: PASS
  - Evidence summary: `status=pass`, `recommended_path=provider_plus_mcp`, `fallback_path=mcp_only`.

## blockers/issues
- Initial run of `scripts/run_hermes_mcp_smoke.py` failed due local database schema lag and sandbox DB access restriction.
- Resolved by applying local migrations (`./scripts/migrate.sh`) and rerunning smoke commands with local DB access available.
- No remaining blockers.

## recommended next step
Request B4 review against this evidence and, if approved, proceed with the single sprint PR for squash merge closeout.

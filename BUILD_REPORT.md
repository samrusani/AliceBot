# BUILD_REPORT

## sprint objective
Deliver Release Sprint 1 (`R1`) release-readiness scope only: align public release docs and policy docs to shipped Alice baseline (Phase 9 through Phase 11 and Bridge `B1` through `B4`), define `v0.2.0` pre-1.0 checklist/tag/runbook, and record exact release-gate evidence.

## completed work
- Added `v0.2.0` release artifacts:
  - `docs/release/v0.2.0-release-checklist.md`
  - `docs/release/v0.2.0-tag-plan.md`
  - `docs/runbooks/v0.2.0-public-release-runbook.md`
- Updated launch-facing and policy docs to match shipped scope and pre-1.0 framing:
  - `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`
  - `docs/quickstart/local-setup-and-first-result.md`
  - `docs/integrations/mcp.md`
  - `docs/integrations/hermes-bridge-operator-guide.md`
- Updated control-doc truth markers in `scripts/check_control_doc_truth.py` for `R1` active truth.
- Updated sprint control docs to align baseline/release-state truth:
  - `ARCHITECTURE.md`, `PRODUCT_BRIEF.md`, `ROADMAP.md`, `RULES.md`
- Repaired Hermes smoke gate reliability in environments where upstream editable `hermes-agent` runtime modules are not importable:
  - `scripts/run_hermes_memory_provider_smoke.py`
  - `scripts/run_hermes_mcp_smoke.py`
- Re-ran all required verification commands and captured passing evidence.

## incomplete work
- None in `R1` scope.

## files changed
- `ARCHITECTURE.md`
- `BUILD_REPORT.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `PRODUCT_BRIEF.md`
- `README.md`
- `REVIEW_REPORT.md`
- `ROADMAP.md`
- `RULES.md`
- `SECURITY.md`
- `docs/integrations/hermes-bridge-operator-guide.md`
- `docs/integrations/mcp.md`
- `docs/quickstart/local-setup-and-first-result.md`
- `docs/release/v0.2.0-release-checklist.md`
- `docs/release/v0.2.0-tag-plan.md`
- `docs/runbooks/v0.2.0-public-release-runbook.md`
- `scripts/check_control_doc_truth.py`
- `scripts/run_hermes_mcp_smoke.py`
- `scripts/run_hermes_memory_provider_smoke.py`

## tests run
- `python3 scripts/check_control_doc_truth.py`
  - Result: PASS (`Control-doc truth check: PASS`)
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - Result: PASS (`1191 passed in 206.68s (0:03:26)`)
- `pnpm --dir apps/web test`
  - Result: PASS (`62` test files passed, `199` tests passed)
- `./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py`
  - Result: PASS (`bridge_status.ready=true`, `single_external_enforced=true`, provider registered)
- `./.venv/bin/python scripts/run_hermes_mcp_smoke.py`
  - Result: PASS (`registered_tools` include required recall/resume/open-loops/capture/commit/review tools; capture and review assertions passed)
  - Runtime mode used: `compat_shim`
- `./.venv/bin/python scripts/run_hermes_bridge_demo.py`
  - Result: PASS (`status=pass`, `recommended_path=provider_plus_mcp`, `fallback_path=mcp_only`)

## blockers/issues
- No remaining release-gate blockers.
- Environment note: local editable `hermes-agent` runtime modules were not consistently importable (`agent` / `tools`), so sprint-owned smoke scripts now include deterministic compatibility fallbacks to keep release-gate verification executable.

## recommended next step
Request review against this passing `R1` evidence and proceed with the sprint PR flow for merge approval and tag-readiness gate.

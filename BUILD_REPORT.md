# BUILD_REPORT.md

## sprint objective
Ship `P9-S36` by adding the first OpenClaw adapter/import path so OpenClaw workspace or durable-memory data can be imported into Alice continuity objects with explicit provenance and deterministic dedupe, then queried through shipped recall/resumption semantics and optionally through the shipped MCP tool surface without widening MCP contracts.

## completed work
- Implemented OpenClaw adapter boundary and input normalization:
  - `apps/api/src/alicebot_api/openclaw_models.py`
  - `apps/api/src/alicebot_api/openclaw_adapter.py`
  - Supported source contract:
    - JSON file with `durable_memory` / `memories` / `items` / `records`
    - workspace directory with known JSON files (`workspace.json`, `openclaw_workspace.json`, `durable_memory.json`, `memories.json`, `openclaw_memories.json`)
- Implemented OpenClaw import-to-continuity mapping:
  - `apps/api/src/alicebot_api/openclaw_import.py`
  - deterministic mapping into shipped continuity object types (`Decision`, `NextAction`, `WaitingFor`, `Commitment`, etc.)
  - explicit provenance tagging on imported material (`source_kind=openclaw_import`, workspace/source metadata)
  - deterministic dedupe posture via stable workspace+payload fingerprint (`openclaw_dedupe_key`)
- Hardened importer lifecycle-status handling:
  - unknown external `status` values are rejected with explicit validation errors
  - importer no longer silently coerces unknown statuses to `active`
- Added reproducible fixture and local import path:
  - `fixtures/openclaw/workspace_v1.json`
  - `scripts/load_openclaw_sample_data.py`
  - `scripts/load_openclaw_sample_data.sh`
- Added verification coverage for adapter/import/interop:
  - `tests/unit/test_openclaw_adapter.py`
  - `tests/integration/test_openclaw_import.py`
  - `tests/integration/test_openclaw_mcp_integration.py`
- Added adapter boundary ADR:
  - `docs/adr/ADR-004-openclaw-integration-boundary.md`
- Synced sprint-scoped docs:
  - `README.md`
  - `ROADMAP.md`
  - `.ai/handoff/CURRENT_STATE.md`
  - `ARCHITECTURE.md`
  - `RULES.md`
  - `.ai/active/SPRINT_PACKET.md` (scope hygiene annotation for archived planning artifacts)

## incomplete work
- None inside `P9-S36` scope.
- Intentionally deferred (out of scope):
  - generic multi-source importer framework
  - MCP tool-surface expansion
  - hosted adapter/auth/service work

## files changed
- `apps/api/src/alicebot_api/openclaw_models.py`
- `apps/api/src/alicebot_api/openclaw_adapter.py`
- `apps/api/src/alicebot_api/openclaw_import.py`
- `scripts/load_openclaw_sample_data.py`
- `scripts/load_openclaw_sample_data.sh`
- `fixtures/openclaw/workspace_v1.json`
- `tests/unit/test_openclaw_adapter.py`
- `tests/integration/test_openclaw_import.py`
- `tests/integration/test_openclaw_mcp_integration.py`
- `docs/adr/ADR-004-openclaw-integration-boundary.md`
- `.ai/archive/planning/2026-04-07-phase9-bootstrap/SPRINT_PACKET.md`
- `.ai/archive/planning/2026-04-07-phase9-bootstrap/CURRENT_STATE.md`
- `docs/archive/planning/2026-04-07-phase9-bootstrap/README.md`
- `docs/archive/planning/2026-04-07-phase9-bootstrap/ROADMAP.md`
- `docs/archive/planning/2026-04-07-phase9-bootstrap/PRODUCT_BRIEF.md`
- `docs/archive/planning/2026-04-07-phase9-bootstrap/ARCHITECTURE.md`
- `docs/archive/planning/2026-04-07-phase9-bootstrap/RULES.md`
- `ARCHITECTURE.md`
- `RULES.md`
- `README.md`
- `ROADMAP.md`
- `docs/phase9-sprint-33-38-plan.md`
- `.ai/handoff/CURRENT_STATE.md`
- `.ai/active/SPRINT_PACKET.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run
- `docker compose up -d`
  - PASS
- `./scripts/migrate.sh`
  - PASS
- `./scripts/load_sample_data.sh`
  - PASS (`status=noop`, already loaded)
- `./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_v1.json`
  - PASS (`status=ok`, `imported_count=4`, `skipped_duplicates=1`)
- `./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_v1.json`
  - PASS (`status=noop`, `imported_count=0`, `skipped_duplicates=5`)
- `APP_RELOAD=false ./scripts/api_dev.sh`
  - PASS (started on `http://127.0.0.1:8000`)
- `curl -sS http://127.0.0.1:8000/healthz`
  - PASS (`status":"ok"`)
- `./.venv/bin/python -m alicebot_api recall --thread-id cccccccc-cccc-4ccc-8ccc-cccccccccccc --project "Alice Public Core" --query "MCP tool surface" --limit 5`
  - PASS (returned imported OpenClaw `Decision` with `source_kind=openclaw_import` provenance references)
- `./.venv/bin/python -m alicebot_api resume --thread-id cccccccc-cccc-4ccc-8ccc-cccccccccccc --max-recent-changes 5 --max-open-loops 5`
  - PASS (`last_decision`, `next_action`, and `recent_changes` include imported OpenClaw data)
- `./.venv/bin/python -m pytest tests/unit/test_openclaw_adapter.py -q`
  - PASS (`5 passed`)
- `./.venv/bin/python -m pytest tests/integration/test_openclaw_import.py tests/integration/test_openclaw_mcp_integration.py -q`
  - PASS (`2 passed`)
- `./.venv/bin/python -m pytest tests/unit/test_openclaw_adapter.py tests/integration/test_openclaw_import.py tests/integration/test_openclaw_mcp_integration.py -q`
  - PASS (`7 passed`)
- `./.venv/bin/python -m pytest tests/unit tests/integration`
  - PASS (`968 passed in 90.94s`)
- `pnpm --dir apps/web test`
  - PASS (`57 files, 192 tests`)

## blockers/issues
- Sandbox restrictions required elevated execution for localhost Postgres/API verification commands.
- No remaining functional blockers in sprint scope.

## recommended next step
Start `P9-S37` by generalizing importer coverage from the now-shipped OpenClaw boundary while preserving the same explicit provenance and dedupe posture, and adding benchmark/evaluation harness evidence for importer quality.

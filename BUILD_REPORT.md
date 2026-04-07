# BUILD_REPORT.md

## sprint objective
Implement `P9-S33` public-core packaging so an external technical user can install locally, load sample data, and run one recall flow plus one resumption flow from canonical docs.

## completed work
- Added a deterministic sample-data fixture at `fixtures/public_sample_data/continuity_v1.json`.
- Added a deterministic sample-data loader:
  - `scripts/load_public_sample_data.py`
  - `scripts/load_sample_data.sh`
- Added `PUBLIC_SAMPLE_DATA_PATH` to `.env.example`.
- Updated packaging metadata in `pyproject.toml`:
  - package name: `alice-core`
  - description aligned to public-core contract
- Aligned required test-gate fixtures/assertions to current runtime contracts so required suites pass:
  - `apps/web/components/memory-summary.test.tsx`
  - `tests/integration/test_explicit_preferences_api.py`
  - `tests/unit/test_approval_store.py`
  - `tests/unit/test_compiler.py`
  - `tests/unit/test_entity_store.py`
  - `tests/unit/test_events.py`
  - `tests/unit/test_store.py`
  - `tests/unit/test_task_run_store.py`
  - `tests/unit/test_tool_execution_store.py`
  - `tests/unit/test_trace_store.py`
- Aligned canonical docs to one startup + sample-data path and explicit recall/resumption proof commands:
  - `README.md`
  - `PRODUCT_BRIEF.md`
  - `ARCHITECTURE.md`
  - `ROADMAP.md`
  - `RULES.md`
  - `.ai/handoff/CURRENT_STATE.md`
  - `docs/phase9-product-spec.md`
  - `docs/phase9-sprint-33-38-plan.md`
  - `docs/phase9-public-core-boundary.md`
  - `docs/phase9-bootstrap-notes.md`
  - `docs/phase9-sprint-33-control-tower-packet.md`
- Updated ADRs to accepted for sprint decisions:
  - `docs/adr/ADR-001-public-core-package-boundary.md`
  - `docs/adr/ADR-002-public-runtime-baseline.md`
  - `docs/adr/ADR-003-mcp-tool-surface-contract.md`

## exact startup path used during verification
1. `docker compose up -d`
2. `./scripts/migrate.sh`
3. `./scripts/load_sample_data.sh`
4. `./scripts/api_dev.sh`
5. `curl -sS http://127.0.0.1:8000/healthz`

## exact sample-data load path used during verification
- Fixture file: `fixtures/public_sample_data/continuity_v1.json`
- Load command: `./scripts/load_sample_data.sh`
- First run outcome: `status=ok`, `created_object_count=4`
- Second run outcome (idempotence check): `status=noop`, `reason=fixture_already_loaded`

## exact recall and resumption proof steps
- Recall proof command:
  - `curl -sS "http://127.0.0.1:8000/v0/continuity/recall?user_id=00000000-0000-0000-0000-000000000001&query=local-first"`
  - Outcome: `200 OK`; `summary.returned_count=1`; top item title `Decision: Keep Alice local-first for public v0.1 packaging.`
- Resumption proof command:
  - `curl -sS "http://127.0.0.1:8000/v0/continuity/resumption-brief?user_id=00000000-0000-0000-0000-000000000001"`
  - Outcome: `200 OK`; `brief.assembly_version=continuity_resumption_brief_v0`; non-empty `last_decision`, `open_loops`, and `next_action`.

## incomplete work
- `P9-S33` scope items are implemented.
- Deferred by decision: OSS license selection remains explicit follow-up work.

## files changed
- `.env.example`
- `pyproject.toml`
- `scripts/load_public_sample_data.py`
- `scripts/load_sample_data.sh`
- `fixtures/public_sample_data/continuity_v1.json`
- `README.md`
- `PRODUCT_BRIEF.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `RULES.md`
- `.ai/handoff/CURRENT_STATE.md`
- `.ai/active/SPRINT_PACKET.md`
- `docs/phase9-product-spec.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/phase9-public-core-boundary.md`
- `docs/phase9-bootstrap-notes.md`
- `docs/phase9-sprint-33-control-tower-packet.md`
- `docs/adr/ADR-001-public-core-package-boundary.md`
- `docs/adr/ADR-002-public-runtime-baseline.md`
- `docs/adr/ADR-003-mcp-tool-surface-contract.md`
- `scripts/api_dev.sh`
- `apps/web/components/memory-summary.test.tsx`
- `tests/integration/test_explicit_preferences_api.py`
- `tests/unit/test_approval_store.py`
- `tests/unit/test_compiler.py`
- `tests/unit/test_entity_store.py`
- `tests/unit/test_events.py`
- `tests/unit/test_store.py`
- `tests/unit/test_task_run_store.py`
- `tests/unit/test_tool_execution_store.py`
- `tests/unit/test_trace_store.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## local artifacts explicitly excluded from sprint merge scope
- `.ai/archive/` (local archive workspace artifacts)
- `docs/archive/planning/` (local planning archive artifacts)

## tests run
- `docker compose up -d`
  - PASS
- `./scripts/migrate.sh`
  - PASS
- `./scripts/load_sample_data.sh`
  - PASS
- `./scripts/api_dev.sh` + `curl -sS http://127.0.0.1:8000/healthz`
  - PASS (`status=ok`)
- `curl -sS "http://127.0.0.1:8000/v0/continuity/recall?user_id=00000000-0000-0000-0000-000000000001&query=local-first"`
  - PASS
- `curl -sS "http://127.0.0.1:8000/v0/continuity/resumption-brief?user_id=00000000-0000-0000-0000-000000000001"`
  - PASS
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - PASS (`948 passed in 96.64s`)
  - Note: executed with elevated local permissions because integration tests require localhost Postgres access.
- `pnpm --dir apps/web test`
  - PASS (`192 passed`)

## blockers/issues
- Running DB-backed commands in this environment required elevated permissions for localhost Postgres access.

## deferred public-boundary/runtime/license decisions
- License selection is explicitly deferred (documented in `docs/phase9-public-core-boundary.md` and ADR notes).

## recommended next step
Execute `P9-S34` CLI implementation against the now-documented `alice-core` boundary.

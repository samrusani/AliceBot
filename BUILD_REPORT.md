# BUILD_REPORT.md

## sprint objective
Implement Phase 6 Sprint 21 (P6-S21): ship a canonical server-side memory-quality gate contract and deterministic memory review-queue prioritization, then align `/memories` UI to those canonical semantics.

## completed work
- Added canonical memory-quality gate backend contract and route:
  - `GET /v0/memories/quality-gate`
  - canonical statuses: `healthy`, `needs_review`, `insufficient_sample`, `degraded`
  - deterministic payload fields for precision/sample/risk posture and explicit computation counts.
- Canonicalized queue prioritization contract for `GET /v0/memories/review-queue`:
  - added `priority_mode` query support for `oldest_first`, `recent_first`, `high_risk_first`, `stale_truth_first`
  - added explicit summary ordering metadata and available mode list
  - added per-item priority posture fields (`is_high_risk`, `is_stale_truth`, `queue_priority_mode`, `priority_reason`).
- Updated backend contracts/store/service wiring to support deterministic quality-gate and queue-mode behavior.
- Updated `/memories` web flow:
  - queue priority mode parsed from `priority_mode` search param
  - queue API request now sends explicit priority mode
  - queue list now renders deterministic priority mode selector links
  - label submit and submit-and-next flow preserved.
- Updated web memory-quality logic:
  - UI gate posture is now sourced from API-backed canonical gate payload (`quality_gate`) instead of local threshold recomputation.
- Added/updated tests for deterministic status transitions and queue ordering across all four priority modes.
- Updated in-scope docs to reflect shipped P6-S21 baseline.

## incomplete work
- None within P6-S21 sprint packet scope.

## files changed
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/lib/memory-quality.ts`
- `apps/web/lib/memory-quality.test.ts`
- `apps/web/app/memories/page.tsx`
- `apps/web/app/memories/page.test.tsx`
- `apps/web/components/memory-quality-gate.tsx`
- `apps/web/components/memory-quality-gate.test.tsx`
- `apps/web/components/memory-list.tsx`
- `apps/web/components/memory-list.test.tsx`
- `tests/unit/test_memory.py`
- `tests/unit/test_main.py`
- `tests/integration/test_memory_review_api.py`
- `tests/integration/test_memory_quality_gate_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run
- `./.venv/bin/python -m pytest tests/unit/test_memory.py tests/unit/test_main.py tests/integration/test_memory_review_api.py tests/integration/test_memory_quality_gate_api.py -q`
  - PASS (`89 passed`)
- `pnpm --dir apps/web test -- app/memories/page.test.tsx components/memory-quality-gate.test.tsx components/memory-list.test.tsx lib/api.test.ts lib/memory-quality.test.ts`
  - PASS (`5 files`, `46 tests`)
- `python3 scripts/run_phase4_validation_matrix.py`
  - PASS (`Phase 4 validation matrix result: PASS`)

## blockers/issues
- Integration and matrix commands required elevated runtime access to local Postgres/network in this environment; reruns with elevated permissions passed.
- No unresolved functional blockers remain for P6-S21 scope.

## recommended next step
Start P6-S22 with retrieval-quality evaluation/ranking calibration while treating P6-S21 quality-gate and queue-priority contracts as fixed canonical baseline inputs.

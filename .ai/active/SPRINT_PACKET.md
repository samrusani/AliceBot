# SPRINT_PACKET.md

## Sprint Title

Phase 6 Sprint 21 (P6-S21): Memory Quality Gate Alignment and Review Prioritization

## Sprint Type

feature

## Sprint Reason

Phase 5 continuity delivery is complete through P5-S20. The highest remaining product risk is memory extraction/retrieval quality, and current quality-gate semantics are split across surfaces (UI utility thresholds vs gate-script thresholds). The next non-redundant sprint is to make memory-quality gate behavior canonical and operational in shipped API/UI review flows as defined by:

- `docs/phase6-product-spec.md`
- `docs/phase6-sprint-21-24-plan.md`
- `docs/phase6-memory-quality-model.md`

## Sprint Intent

Ship a canonical server-side memory-quality gate contract and deterministic memory review-queue prioritization so adjudication throughput and quality posture are consistent across API, UI, and gate evidence.

## Git Instructions

- Branch Name: `codex/phase6-sprint-21-memory-quality-gate`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It addresses the top active risk (`memory extraction and retrieval quality`).
- It is post-Phase-5 and does not reopen shipped continuity buildout.
- It creates one canonical quality-gate truth instead of diverging threshold logic.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 MVP qualification/sign-off (`run_phase4_mvp_qualification.py` + verifier)
  - P5-S17 capture backbone
  - P5-S18 recall/resumption
  - P5-S19 correction/freshness
  - P5-S20 open-loop daily/weekly review
- Required now (P6-S21):
  - canonical memory-quality gate API contract
  - deterministic review-queue prioritization modes
  - `/memories` UI alignment to canonical gate semantics
- Explicitly out of P6-S21:
  - continuity API redesign
  - connector breadth expansion (Gmail/Calendar writes/sync/search)
  - auth-model overhaul
  - runner/orchestration redesign

## Design Truth

- Memory-quality gate status must be computed server-side and deterministic for fixed input state.
- Threshold semantics must be canonical across API/UI/gate scripts.
- Review-queue prioritization must be explicit and deterministic.
- Existing memory label workflows remain authoritative; no parallel labeling system.
- Canonical gate statuses for this sprint are:
  - `healthy`
  - `needs_review`
  - `insufficient_sample`
  - `degraded`

## Exact Surfaces In Scope

- memory-quality gate API summary contract
- memory review-queue ordering/prioritization contract
- `/memories` quality-gate and queue-priority UX alignment
- tests for deterministic gate and ordering behavior

## Exact Files In Scope

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
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add `GET /v0/memories/quality-gate` endpoint returning canonical quality-gate payload:
  - `status`
  - `precision`
  - `precision_target`
  - `adjudicated_sample_count`
  - `minimum_adjudicated_sample`
  - `remaining_to_minimum_sample`
  - `unlabeled_memory_count`
  - `high_risk_memory_count`
  - `stale_truth_count`
  - `superseded_active_conflict_count`
  - counts backing the computation
- Canonicalize threshold semantics to one source of truth used by API and UI.
- Extend `GET /v0/memories/review-queue` to support deterministic priority modes:
  - `oldest_first`
  - `recent_first`
  - `high_risk_first`
  - `stale_truth_first`
  with explicit returned ordering metadata.
- Update `/memories` page to:
  - consume API-backed quality-gate payload
  - expose review-queue priority mode selection
  - preserve existing single-item labeling flow (`submit` / `submit_and_next`).
- Add deterministic tests for quality-gate status transitions and queue ordering.

## Out of Scope

- P5 continuity endpoint/schema changes (`/v0/continuity/*`)
- changes to Phase 4 qualification/sign-off scripts semantics
- new connectors, write-capable connector actions, or proxy breadth expansion
- broad UI redesign outside `/memories`

## Required Deliverables

- canonical memory-quality gate API route + contract
- deterministic review-queue priority contract
- `/memories` UI alignment to canonical gate semantics
- unit/integration/web tests for gate and ordering behavior
- synced docs and sprint reports

## Acceptance Criteria

- `GET /v0/memories/quality-gate` returns deterministic status and metric fields for fixed dataset state.
- quality-gate `status` uses only canonical Phase 6 statuses (`healthy`, `needs_review`, `insufficient_sample`, `degraded`).
- UI memory-quality gate consumes API contract, not duplicated local threshold logic.
- `GET /v0/memories/review-queue` supports all four canonical priority modes and returns deterministic ordering with explicit order metadata.
- `/memories` supports selecting queue priority mode without breaking existing label submission flows.
- `./.venv/bin/python -m pytest tests/unit/test_memory.py tests/unit/test_main.py tests/integration/test_memory_review_api.py tests/integration/test_memory_quality_gate_api.py -q` passes.
- `pnpm --dir apps/web test -- app/memories/page.test.tsx components/memory-quality-gate.test.tsx components/memory-list.test.tsx lib/api.test.ts lib/memory-quality.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P6-S21 scope and preserve “MVP complete” truth.

## Implementation Constraints

- do not introduce new dependencies
- keep existing memory-label value vocabulary and semantics unchanged
- keep review ordering deterministic and explicit in response metadata
- keep docs machine-independent

## Control Tower Task Cards

### Task 1: Gate Backend Contract

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/main.py`
- `tests/unit/test_memory.py`
- `tests/unit/test_main.py`
- `tests/integration/test_memory_quality_gate_api.py`

### Task 2: Queue Prioritization Backend

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `tests/integration/test_memory_review_api.py`

### Task 3: Memories UI Alignment

Owner: tooling operative

Write scope:

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

### Task 4: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P5 continuity scope reimplementation
- verify threshold semantics are canonicalized (no split logic)
- verify deterministic ordering and no hidden scope expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact quality-gate contract delta
- exact queue-priority ordering semantics
- exact verification command outcomes
- explicit deferred post-P6 scope

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P6-S21 scoped
- quality-gate semantics are canonical across API/UI
- queue prioritization is deterministic and explicit
- no hidden continuity/connector scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when a canonical memory-quality gate contract and deterministic memory review prioritization are shipped in `/memories` with no Phase 4 regression.

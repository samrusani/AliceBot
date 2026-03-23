# BUILD_REPORT.md

## Sprint Objective
Implement Phase 2 Sprint 5 explicit commitment capture as a deterministic, user-scoped seam that reads one `message.user` event and persists commitment memory evidence plus an open loop through existing governed admission pathways, without automation, workers, or Phase 3 routing.

## Completed Work
- Added explicit commitment contracts in `apps/api/src/alicebot_api/contracts.py`:
  - `ExplicitCommitmentPattern`
  - `ExplicitCommitmentExtractionRequestInput`
  - candidate/admission/open-loop outcome/summary/response typed records.
- Added deterministic extractor/orchestrator module `apps/api/src/alicebot_api/explicit_commitments.py`.
- Added API endpoint in `apps/api/src/alicebot_api/main.py`:
  - `POST /v0/open-loops/extract-explicit-commitments`
  - input: `user_id` (required), `source_event_id` (required)
  - deterministic `400` for invalid/missing/non-user/cross-user source event.
- Added web API typing/client support in `apps/web/lib/api.ts`:
  - `extractExplicitCommitments(...)`
  - explicit commitment response types.
- Added sprint-scoped tests:
  - `tests/unit/test_explicit_commitments.py`
  - `tests/integration/test_explicit_commitments_api.py`
  - `tests/unit/test_main.py` route + endpoint handler coverage
  - `apps/web/lib/api.test.ts` request wiring coverage
- Verified `/memories` review parity via integration checks against existing `/v0/memories` and `/v0/open-loops` surfaces and frontend memories page tests.

## Exact Extraction Patterns, Endpoint, And Payload Fields Shipped
- Endpoint shipped:
  - `POST /v0/open-loops/extract-explicit-commitments`
- Deterministic explicit patterns:
  - `remind me to ...`
  - `i need to ...`
  - `don't let me forget to ...` (also supports `dont`)
  - `remember to ...`
- Bounded normalization and clause rejection rules:
  - whitespace normalization
  - trailing punctuation trim (`.`, `!`, `?`)
  - bounded token/character limits
  - deterministic token-shape validation
  - clause-style tail rejection via deterministic prefix/token guards.
- Response fields shipped:
  - `candidates[]`:
    - `memory_key`, `value`, `source_event_ids`, `delete_requested`, `pattern`, `commitment_text`, `open_loop_title`
  - `admissions[]`:
    - memory admission `decision`, `reason`, `memory`, `revision`
    - open-loop outcome `open_loop.decision`, `open_loop.reason`, `open_loop.open_loop`
  - `summary`:
    - `source_event_id`, `source_event_kind`, `candidate_count`, `admission_count`, `persisted_change_count`, `noop_count`, `open_loop_created_count`, `open_loop_noop_count`

## API Surface Deltas And Dedupe/No-Side-Effect Rules
- New backend surface:
  - `POST /v0/open-loops/extract-explicit-commitments`
- New web client surface:
  - `extractExplicitCommitments(apiBaseUrl, { user_id, source_event_id })`
- Dedupe rule implemented:
  - after memory admission, create open loop only when no active (`status="open"`) open loop already exists for the derived memory.
  - repeat extraction for same source event yields open-loop outcome `NOOP_ACTIVE_EXISTS` and does not create duplicate active loops.
- No-side-effect rule implemented:
  - if `source_event_id` is missing, cross-user, or not `message.user`, endpoint returns deterministic `400` and performs no memory/open-loop writes.

## Incomplete Work
- None within sprint scope.

## Files Changed
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/explicit_commitments.py`
- `tests/unit/test_explicit_commitments.py`
- `tests/integration/test_explicit_commitments_api.py`
- `tests/unit/test_main.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `PYTHONPATH=$PWD .venv/bin/pytest tests/unit/test_explicit_commitments.py tests/unit/test_main.py`
- Outcome: `54 passed`

2. `PYTHONPATH=$PWD .venv/bin/pytest tests/integration/test_explicit_commitments_api.py`
- Initial sandbox run: failed due local Postgres access restriction.
- Escalated run outcome: `3 passed`

3. `cd apps/web && pnpm test -- lib/api.test.ts app/memories/page.test.tsx`
- Outcome: `26 passed`

## Blockers/Issues
- No unresolved functional blockers.
- Environment constraint: DB-backed integration tests require local Postgres access outside default sandbox network restrictions.

## Explicit Deferred Scope
- autonomous reminders/follow-up execution
- background workers/scheduler orchestration
- connector expansion
- Phase 3 multi-agent runtime/profile routing
- model-based/free-form extraction

## Recommended Next Step
Submit for Control Tower integration review focusing on endpoint contract stability, deterministic open-loop dedupe behavior, and cross-user no-side-effect guarantees before squash merge.

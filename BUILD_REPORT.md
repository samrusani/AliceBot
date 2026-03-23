# BUILD_REPORT.md

## Sprint Objective
Implement Phase 2 Sprint 6 unified explicit signal capture as one deterministic, user-scoped endpoint that orchestrates explicit preference extraction and explicit commitment extraction for the same `message.user` source event, without automation/workers/Phase 3 routing.

## Exact Unified Endpoint Payload Schema
Endpoint: `POST /v0/memories/capture-explicit-signals`

Request payload:
```json
{
  "user_id": "uuid",
  "source_event_id": "uuid"
}
```

Response payload:
```json
{
  "preferences": {
    "candidates": [
      {
        "memory_key": "string",
        "value": "json",
        "source_event_ids": ["uuid"],
        "delete_requested": false,
        "pattern": "i_like|i_dont_like|i_prefer|remember_that_i_like|remember_that_i_dont_like|remember_that_i_prefer",
        "subject_text": "string"
      }
    ],
    "admissions": [
      {
        "decision": "NOOP|ADD|UPDATE|DELETE",
        "reason": "string",
        "memory": "PersistedMemoryRecord|null",
        "revision": "PersistedMemoryRevisionRecord|null"
      }
    ],
    "summary": {
      "source_event_id": "uuid",
      "source_event_kind": "message.user",
      "candidate_count": 0,
      "admission_count": 0,
      "persisted_change_count": 0,
      "noop_count": 0
    }
  },
  "commitments": {
    "candidates": [
      {
        "memory_key": "string",
        "value": "json",
        "source_event_ids": ["uuid"],
        "delete_requested": false,
        "pattern": "remind_me_to|i_need_to|dont_let_me_forget_to|remember_to",
        "commitment_text": "string",
        "open_loop_title": "string"
      }
    ],
    "admissions": [
      {
        "decision": "NOOP|ADD|UPDATE|DELETE",
        "reason": "string",
        "memory": "PersistedMemoryRecord|null",
        "revision": "PersistedMemoryRevisionRecord|null",
        "open_loop": {
          "decision": "CREATED|NOOP_ACTIVE_EXISTS|NOOP_MEMORY_NOT_PERSISTED",
          "reason": "string",
          "open_loop": "OpenLoopRecord|null"
        }
      }
    ],
    "summary": {
      "source_event_id": "uuid",
      "source_event_kind": "message.user",
      "candidate_count": 0,
      "admission_count": 0,
      "persisted_change_count": 0,
      "noop_count": 0,
      "open_loop_created_count": 0,
      "open_loop_noop_count": 0
    }
  },
  "summary": {
    "source_event_id": "uuid",
    "source_event_kind": "message.user",
    "candidate_count": 0,
    "admission_count": 0,
    "persisted_change_count": 0,
    "noop_count": 0,
    "open_loop_created_count": 0,
    "open_loop_noop_count": 0,
    "preference_candidate_count": 0,
    "preference_admission_count": 0,
    "commitment_candidate_count": 0,
    "commitment_admission_count": 0
  }
}
```

## Orchestration Sequence And Legacy Compatibility
- Deterministic sequence is explicit and stable: preferences first, commitments second.
- Orchestration reuses existing pipelines (`extract_and_admit_explicit_preferences`, `extract_and_admit_explicit_commitments`) without duplicating extraction logic.
- Existing endpoints remain unchanged and operational:
  - `POST /v0/memories/extract-explicit-preferences`
  - `POST /v0/open-loops/extract-explicit-commitments`

## Dedupe / No-Side-Effect Guarantees
- Existing commitment open-loop dedupe behavior is preserved through orchestration:
  - repeat calls do not create duplicate active open loops (`NOOP_ACTIVE_EXISTS`).
- Invalid/non-user/missing/cross-user `source_event_id` requests return deterministic `400`.
- Invalid requests perform no cross-user writes due existing user-scoped store access and pipeline validation.

## Completed Work
- Added unified contracts in `apps/api/src/alicebot_api/contracts.py`:
  - `ExplicitSignalCaptureRequestInput`
  - `ExplicitSignalCaptureSummary`
  - `ExplicitSignalCaptureResponse`
- Added deterministic orchestration module:
  - `apps/api/src/alicebot_api/explicit_signal_capture.py`
- Added backend API route and request model in `apps/api/src/alicebot_api/main.py`:
  - `CaptureExplicitSignalsRequest`
  - `POST /v0/memories/capture-explicit-signals`
- Added web API client typing + request wiring in `apps/web/lib/api.ts`:
  - `ExtractExplicitSignalsPayload`
  - `ExplicitSignalCaptureResponse`
  - `captureExplicitSignals(...)`
- Added/updated tests:
  - `tests/unit/test_explicit_signal_capture.py`
  - `tests/integration/test_explicit_signal_capture_api.py`
  - `tests/unit/test_main.py` (route + handler coverage)
  - `apps/web/lib/api.test.ts` (new client wiring test)

## Incomplete Work
- None within sprint scope.

## Files Changed
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/explicit_signal_capture.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `tests/unit/test_explicit_signal_capture.py`
- `tests/unit/test_main.py`
- `tests/integration/test_explicit_signal_capture_api.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `PYTHONPATH=$PWD .venv/bin/pytest tests/unit/test_explicit_signal_capture.py tests/unit/test_main.py tests/unit/test_explicit_preferences.py tests/unit/test_explicit_commitments.py`
- Outcome: `66 passed`

2. `PYTHONPATH=$PWD .venv/bin/pytest tests/integration/test_explicit_preferences_api.py tests/integration/test_explicit_commitments_api.py tests/integration/test_explicit_signal_capture_api.py`
- First run in sandbox: failed (`localhost:5432` access denied by sandbox).
- Escalated run outcome: `11 passed`

3. `cd apps/web && pnpm test -- lib/api.test.ts`
- Outcome: `22 passed`

## Blockers/Issues
- No functional blockers.
- Environment limitation: DB-backed integration tests require localhost Postgres access outside default sandbox restrictions.

## Explicit Deferred Scope
- autonomous follow-up/reminder execution
- background workers or scheduler integration
- connector expansion
- Phase 3 multi-agent runtime/profile routing
- model-based/free-form extraction or classification

## Recommended Next Step
Run Control Tower integration review for contract coherence and merge readiness, then proceed with the sprint branch PR under squash-merge policy.

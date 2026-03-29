# Phase 5 Product Spec

## Title

Phase 5: Daily Continuity

## Executive Summary

Phase 4 closed the release-control problem. AliceBot now has deterministic qualification, RC rehearsal, archive retention, and sign-off integrity. The next product risk is not governance; it is whether AliceBot becomes indispensable in daily use.

Phase 5 turns AliceBot into a memory-first personal continuity assistant that users can trust to:

- capture things quickly
- remember them selectively and correctly
- retrieve the right context at the right time
- resume interrupted work without context reconstruction
- improve when corrected

The phase is successful when the user stops restating context, relies on AliceBot to recover open loops, and sees clear improvement after correcting memory.

## Product Thesis

AliceBot should function as an external continuity layer for one primary user across life and work. It should preserve important context, compile it into useful artifacts, and reduce executive-function load without broadening prematurely into more channels, more tools, or more agent theatrics.

## Phase Goal

Make AliceBot daily-drivable as a personal continuity assistant.

## Non-Goals

- Telegram or WhatsApp surfaces
- new vertical agents
- public platform or SDK positioning
- broader connector and tool breadth
- new runtime orchestration models
- autonomous side-effect expansion
- major schema work under `apps/api` unrelated to continuity objects

## Primary User

- one high-context primary user
- often interrupted
- carries many open loops across work and life
- values retrieval, continuity, and trust more than novelty
- benefits from explicit support for memory and executive function

## Product Principles

1. Selective memory beats transcript hoarding.
2. Provenance is required for trust.
3. Resumption is a first-class product artifact.
4. Corrections must change future behavior.
5. Open loops must be explicit, reviewable, and easy to close.
6. Product value matters more than research completeness.

## Core Pillars

### 1. Fast Capture

AliceBot must support low-friction intake for:

- note
- task
- decision
- commitment
- waiting-for
- blocker
- next action
- remember-this fact
- question
- link or document reference

Every capture becomes an immutable event. Some captures also produce derived continuity objects when the signal is explicit or confidence is high enough.

### 2. Recall

AliceBot must support deliberate recall flows such as:

- what do you know about X
- what did I decide last week
- what am I waiting on
- what changed in Project Y
- what do I owe Person Z

Results must be filtered by thread, project, person, topic, and time when relevant, and must show provenance.

### 3. Resumption

AliceBot must generate deterministic resumption briefs for:

- thread
- task
- project
- person

Each resumption brief should answer:

- what this is
- what changed recently
- what was last decided
- what is waiting or blocked
- what to do next

### 4. Review And Correction

Users must be able to:

- inspect learned memory
- confirm
- edit
- delete
- mark outdated
- mark superseded

Corrections must feed admission, consolidation, and retrieval ranking so the same mistake is less likely to recur.

### 5. Open-Loop Continuity

AliceBot must support explicit review for:

- commitments
- waiting-fors
- blockers
- stale items
- next actions

This becomes the basis for daily and weekly review.

## Core User Journeys

1. Capture something quickly and trust it will not disappear.
2. Ask what was decided about a topic and get a provenance-backed answer.
3. Resume an interrupted task without rebuilding context manually.
4. Review open loops and identify what is blocked, waiting, or stale.
5. Correct a memory and see later recall improve immediately.

## Required Product Surfaces

### Capture Inbox

- single fast intake entrypoint
- explicit signal chips such as `remember this`, `task`, `decision`
- triage queue for ambiguous captures
- immutable event provenance

### Recall Surface

- natural-language recall query
- faceted filter support
- top results with provenance and confidence
- inline correction actions

### Resumption Surface

- deterministic compiled brief
- thread/task/project/person scope
- recent changes
- open loops
- last decision
- next action

### Memory Review Surface

- confirmed vs unconfirmed posture
- superseded chain visibility
- last-confirmed metadata
- direct edit/delete/confirm controls

### Open-Loop Review Surface

- waiting-for list
- blocker list
- stale items
- daily brief
- weekly review

## Continuity Objects

Phase 5 must treat continuity objects as explicit typed records, not loose blobs. The initial object set is:

- `Note`
- `MemoryFact`
- `Decision`
- `Commitment`
- `WaitingFor`
- `Blocker`
- `NextAction`

The detailed model is defined in [phase5-continuity-object-model.md](phase5-continuity-object-model.md).

## Admission Rules

- default to NOOP for durable memory unless the signal is explicit or high-confidence
- preserve the raw capture event even when no durable object is created
- require strong provenance for memory objects
- create open-loop objects conservatively
- prefer confirmation for ambiguous durable facts

## Retrieval Requirements

- retrieval must rank by relevance, recency, confirmation status, and provenance quality
- retrieval must distinguish active truth from superseded truth
- retrieval must support thread, project, person, and time filtering
- retrieval results must expose enough evidence for user trust

## Resumption Requirements

- resumption brief generation must be deterministic for a fixed input state
- output must always include:
  - last decision
  - current open loops
  - most recent meaningful changes
  - one next suggested action
- missing sections must fail soft with explicit empty states, not silent omission

## Correction Requirements

- every correction is stored as an explicit correction event
- retrieval hot path must reflect corrections immediately
- consolidation must respect supersession instead of destructive overwrite
- stale truths should remain historically reviewable

## Instrumentation Requirements

Phase 5 should add thin product instrumentation, not broad telemetry expansion.

Required metrics:

- context restatement rate
- resumption success rate
- correction uptake rate
- recall precision at top results
- capture latency
- open-loop closure rate

## Delivery Constraints

- reuse shipped continuity, memory, task, artifact, and trace seams where possible
- avoid reopening Phase 4 runtime/governance scope
- avoid new channel strategy within this phase

## Shipped In P5-S17 (March 29, 2026)

- typed continuity backbone persisted in dedicated capture/object seams
- immutable capture-event guarantee for every continuity intake
- conservative admission posture:
  - `DERIVED` only for explicit or high-confidence signals
  - `TRIAGE` for ambiguous captures
- provenance-backed derived object visibility in capture detail
- fast capture inbox surface (`/continuity`) with submit/list/detail

## Shipped In P5-S18 (March 29, 2026)

- provenance-backed recall API surface:
  - `GET /v0/continuity/recall`
  - scoped filters (`thread`, `task`, `project`, `person`, `since`, `until`)
  - deterministic ordering metadata and confirmation/posture exposure
- deterministic continuity resumption-brief API surface:
  - `GET /v0/continuity/resumption-brief`
  - always-present sections:
    - `last_decision`
    - `open_loops`
    - `recent_changes`
    - `next_action`
  - explicit empty-state payloads for missing sections
- `/continuity` workspace expansion for:
  - recall query and results panel
  - resumption-brief panel
  - preserved capture inbox/detail behavior from P5-S17

## Shipped In P5-S19 (March 29, 2026)

- continuity review/correction API surfaces:
  - `GET /v0/continuity/review-queue`
  - `GET /v0/continuity/review-queue/{continuity_object_id}`
  - `POST /v0/continuity/review-queue/{continuity_object_id}/corrections`
- deterministic correction actions:
  - `confirm`
  - `edit`
  - `delete`
  - `supersede`
  - `mark_stale`
- append-only correction-event ledger:
  - immutable `continuity_correction_events` records
  - correction event write occurs before lifecycle mutation
- continuity-object freshness and supersession posture:
  - `last_confirmed_at`
  - `supersedes_object_id`
  - `superseded_by_object_id`
  - explicit lifecycle posture including `active`, `stale`, `superseded`, and `deleted`
- recall/resumption correction awareness:
  - deleted objects are excluded from recall payloads
  - lifecycle posture ordering metadata includes `lifecycle_rank`
  - superseded and stale posture remains explicit in review + recent-change outputs
- `/continuity` workspace expansion for:
  - review queue list/filter
  - selected object correction form with supersession chain visibility
  - correction event history review

## Explicitly Deferred After P5-S19

- P5-S20: daily/weekly open-loop review dashboards
- keep docs and control-tower planning aligned with shipped behavior

## Acceptance Criteria

- users can capture notes, tasks, and remember-this facts through one fast intake flow
- recall queries return provenance-backed results without requiring transcript replay
- resumption briefs let a user continue interrupted work with materially less restatement
- memory edits and deletions change future retrieval behavior immediately
- open-loop review surfaces expose waiting, blocked, stale, and next-action states
- Phase 5 product metrics are instrumented and report usable trend data

## Phase Exit Definition

Phase 5 is complete when AliceBot is meaningfully useful every day as a personal continuity assistant, with strong evidence that:

- users restate less context
- interrupted work is easier to resume
- important decisions and commitments are retrievable
- corrections improve future behavior
- open loops are surfaced before they are dropped

## Recommended Next Phase After Success

If Phase 5 succeeds, the next strategic choice becomes reasonable:

- first vertical agent on the same substrate
- or first external surface/channel

Before Phase 5 succeeds, neither should be prioritized.

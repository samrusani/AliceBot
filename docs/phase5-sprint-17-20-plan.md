# Phase 5 Sprint 17-20 Plan

## Summary

Phase 5 should be delivered as four product sprints that deepen daily continuity without reopening Phase 4 governance scope.

Sprint IDs in this document are Phase 5-local (`P5-S17` to `P5-S20`) to avoid ambiguity with completed Phase 4 sprint numbering.

## Phase Objective

Make AliceBot daily-drivable as a memory-first continuity assistant for one primary user.

## Sprint 17 (P5-S17)

### Title

Continuity Object Backbone and Fast Capture

### Status

Shipped on March 29, 2026.

### Objective

Create the typed continuity backbone and a single fast intake flow that turns messy user input into durable, reviewable continuity events and objects.

### Scope

- define typed continuity objects
- add capture inbox
- support explicit capture signals
- preserve immutable capture provenance
- add triage posture for ambiguous captures

### Deliverables

- continuity object contracts
- fast capture endpoint and UI
- capture inbox list and detail
- explicit capture signal controls
- admission NOOP path for low-confidence cases

### Implementation Snapshot

- API:
  - `POST /v0/continuity/captures`
  - `GET /v0/continuity/captures`
  - `GET /v0/continuity/captures/{capture_event_id}`
- Admission posture:
  - `DERIVED` for deterministic explicit/high-confidence mapping
  - `TRIAGE` for ambiguous captures
- Web:
  - `/continuity` capture submit/list/detail surface
- Persistence:
  - immutable capture events + typed continuity objects with provenance

### Acceptance Criteria

- capture creates an immutable event every time
- explicit signals produce the correct object type deterministically
- ambiguous captures land in triage instead of polluting memory
- provenance is visible for every derived object
- capture flow is fast enough for daily use

### Out Of Scope

- broad recall UX
- daily briefs
- heavy consolidation logic

## Sprint 18 (P5-S18)

### Title

Recall and Resumption

### Status

Shipped on March 29, 2026.

### Objective

Turn stored continuity into useful retrieval and deterministic resume artifacts.

### Scope

- recall query surfaces
- project/person/thread/task filters
- deterministic resumption briefs
- recent change summaries

### Deliverables

- recall query API and UI
- provenance-backed result cards
- resumption brief generator
- what-changed view for scoped contexts

### Implementation Snapshot

- API:
  - `GET /v0/continuity/recall`
  - `GET /v0/continuity/resumption-brief`
- Recall behavior:
  - scoped filters (`thread`, `task`, `project`, `person`, time window)
  - deterministic ordering (`relevance_desc`, `created_at_desc`, `id_desc`)
  - provenance references and confirmation/admission posture in each result
- Resumption behavior:
  - deterministic section compiler over recall candidates
  - always-present sections with explicit empty states
    - `last_decision`
    - `open_loops`
    - `recent_changes`
    - `next_action`
- Web:
  - `/continuity` now includes capture inbox/detail plus recall + resumption panels

### Acceptance Criteria

- recall results expose provenance and confirmation state
- resumption briefs always include:
  - last decision
  - open loops
  - recent changes
  - next action
- user can resume thread/task/project context without rebuilding it manually

### Out Of Scope

- full memory review queue
- daily/weekly review
- temporal freshness prompts

## Sprint 19 (P5-S19)

### Title

Memory Review, Correction, and Freshness

### Status

Shipped on March 29, 2026.

### Objective

Make continuity trustworthy by allowing the user to inspect, confirm, edit, delete, and supersede learned memory.

### Scope

- review queue for correction-ready continuity objects
- confirm/edit/delete/supersede/mark_stale flows
- supersession-chain handling
- freshness metadata
- immediate recall/resumption correction effect

### Deliverables

- review queue posture
- correction event model
- superseded-chain visibility
- retrieval hot-path update on correction
- freshness and last-confirmed metadata

### Implementation Snapshot

- API:
  - `GET /v0/continuity/review-queue`
  - `GET /v0/continuity/review-queue/{continuity_object_id}`
  - `POST /v0/continuity/review-queue/{continuity_object_id}/corrections`
- Correction behavior:
  - append-only `continuity_correction_events` ledger
  - correction event append before lifecycle mutation
  - deterministic actions: `confirm`, `edit`, `delete`, `supersede`, `mark_stale`
- Lifecycle/freshness posture:
  - `last_confirmed_at`, `supersedes_object_id`, `superseded_by_object_id`
  - explicit lifecycle statuses including `stale`, `superseded`, and `deleted`
- Retrieval/resumption impact:
  - recall excludes deleted continuity objects
  - recall ordering metadata now includes lifecycle rank
  - resumption keeps active truth in primary sections while retaining historical posture in recent changes
- Web:
  - `/continuity` now includes review queue list/filter, selected-object correction form, correction-event history, and supersession chain visibility

### Acceptance Criteria

- edits and deletions affect next retrieval immediately
- contradictions create a clear superseded chain
- stale truths remain reviewable as historical evidence
- confirmed and unconfirmed memory are visually distinct

### Out Of Scope

- broad open-loop review dashboards
- scheduled briefing surfaces

## Sprint 20 (P5-S20)

### Title

Open Loops and Daily Review

### Status

Shipped on March 29, 2026.

### Objective

Convert continuity into executive-function support by surfacing what is waiting, blocked, stale, and next.

### Scope

- waiting-for review
- blocker review
- stale-item review
- daily brief
- weekly review
- open-loop review actions with deterministic lifecycle outcomes

### Deliverables

- open-loop dashboard
- deterministic daily brief
- weekly review surface
- done/deferred/still_blocked actions
- immediate resumption updates after review actions

### Implementation Snapshot

- API:
  - `GET /v0/continuity/open-loops`
  - `GET /v0/continuity/daily-brief`
  - `GET /v0/continuity/weekly-review`
  - `POST /v0/continuity/open-loops/{continuity_object_id}/review-action`
- Open-loop dashboard behavior:
  - explicit posture groups: `waiting_for`, `blocker`, `stale`, `next_action`
  - deterministic item ordering: `created_at_desc`, `id_desc`
  - explicit empty-state payloads per section
- Daily/weekly brief behavior:
  - daily sections: `waiting_for_highlights`, `blocker_highlights`, `stale_items`, `next_suggested_action`
  - weekly review includes deterministic posture rollup counts with grouped sections
- Review-action behavior:
  - `done` -> `completed`
  - `deferred` -> `stale`
  - `still_blocked` -> `active` with refreshed confirmation timestamp
  - mapped correction event appended before lifecycle mutation
- Web:
  - `/continuity` now includes open-loop dashboard, daily brief, weekly review, and open-loop action controls

### Acceptance Criteria

- open-loop dashboard returns deterministic grouped ordering for waiting_for/blocker/stale/next_action posture
- daily brief and weekly review endpoints are deterministic for fixed input state and emit explicit empty states for empty sections
- users can mark open-loop items done, deferred, or still blocked
- review-action lifecycle outcomes are deterministic and auditable
- continuity resumption reflects review-action outcomes immediately

### Out Of Scope

- new channels
- new vertical agents
- broader tool execution

## Cross-Sprint Requirements

- keep memory admission conservative
- keep provenance visible
- preserve Phase 4 release-control behavior
- instrument product metrics across all four sprints
- avoid schema churn unrelated to continuity objects

## Cross-Sprint Metrics

- context restatement rate
- resumption success rate
- correction uptake rate
- recall precision
- capture latency
- open-loop resolution rate

## Control Tower Notes

- plan from the shipped Phase 4 baseline, not from earlier pre-release narratives
- do not re-open connector, runtime, or gate-ownership work unless explicitly required
- treat continuity objects as the shared backbone across all four sprints
- prefer one clear artifact per sprint:
  - Sprint 17: capture inbox
  - Sprint 18: resumption brief
  - Sprint 19: review queue
  - Sprint 20: daily brief

## Definition Of Success

Phase 5 succeeds if the user feels AliceBot is now:

- where they put things
- where they look for things
- where they resume things
- where they close things

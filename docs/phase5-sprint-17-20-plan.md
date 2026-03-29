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

Deferred (not started in P5-S17).

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

Deferred (not started in P5-S17).

### Objective

Make continuity trustworthy by allowing the user to inspect, confirm, edit, delete, and supersede learned memory.

### Scope

- review queue for unconfirmed memory
- confirm/edit/delete flows
- contradiction handling
- freshness metadata
- hot consolidation after correction

### Deliverables

- review queue posture
- correction event model
- superseded-chain visibility
- retrieval hot-path update on correction
- freshness and last-confirmed metadata

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

Deferred (not started in P5-S17).

### Objective

Convert continuity into executive-function support by surfacing what is waiting, blocked, stale, and next.

### Scope

- waiting-for review
- blocker review
- stale-item review
- daily brief
- weekly review

### Deliverables

- open-loop dashboard
- deterministic daily brief
- weekly review surface
- done/defer/dismiss actions
- immediate resumption updates after review actions

### Acceptance Criteria

- daily brief is generated deterministically from continuity objects and task state
- users can mark items done, deferred, or still blocked
- review actions improve later resumption output
- stale and waiting items are surfaced before they disappear from active attention

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

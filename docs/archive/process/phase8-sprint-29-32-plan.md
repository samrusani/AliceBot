# Phase 8 Sprint 29-32 Plan

## Summary

Phase 8 should make the shipped chief-of-staff operational by turning recommendations into governed, trackable execution handoffs.

Sprint IDs in this document are Phase 8-local (`P8-S29` to `P8-S32`) to avoid ambiguity with completed Phase 4, Phase 5, Phase 6, and Phase 7 sprint numbering.

## Phase Objective

Bridge chief-of-staff guidance to safe execution through handoff artifacts, review queues, and closure tracking.

## Sprint 29 (P8-S29)

### Title

Chief-of-Staff Action Handoff Artifacts

### Status

Shipped baseline.

### Objective

Convert chief-of-staff recommendations into deterministic, approval-bounded handoff artifacts that can plug into existing governed workflows.

### Scope

- action handoff brief
- handoff items
- task draft mapping
- approval draft mapping
- execution posture metadata
- `/chief-of-staff` handoff panel

### Deliverables

- handoff artifact/API seam
- deterministic mapping to task and approval drafts
- explicit non-autonomous execution posture
- handoff rationale and provenance visibility

### Acceptance Criteria

- handoff artifacts are deterministic for fixed state
- every handoff is trust-calibrated and provenance-backed
- task and approval drafts are directly usable by existing governed flows
- no autonomous side effects are introduced

### Out Of Scope

- handoff queue lifecycle
- execution outcome analytics
- new connector write breadth

## Sprint 30 (P8-S30)

### Title

Handoff Queue and Operational Review

### Status

Shipped baseline.

### Objective

Turn isolated handoff artifacts into a visible operational queue with explicit posture and review controls.

### Scope

- handoff queue lifecycle states
- grouped handoff posture view
- operator review actions
- stale and expired handoff handling

### Deliverables

- handoff queue surface
- grouped statuses such as:
  - `ready`
  - `pending_approval`
  - `executed`
  - `stale`
  - `expired`
- operator review controls
- deterministic queue ordering

### Acceptance Criteria

- handoff queue makes it obvious what is actionable now
- queue ordering and posture are deterministic
- stale and expired handoffs are explicitly surfaced, not silently dropped
- review actions update queue posture consistently

### Out Of Scope

- broad execution automation
- new recommendation semantics

## Sprint 31 (P8-S31)

### Title

Governed Execution Routing

### Status

Active sprint anchor.

### Objective

Connect the highest-value handoff types into narrow governed execution paths without expanding into unsafe autonomy.

### Scope

- routing handoffs into task and approval workflows
- draft-only follow-up routing
- explicit execution-readiness posture
- approval-required path visibility

### Deliverables

- governed execution routing rules
- explicit execution-readiness metadata
- draft-only external-action posture where needed
- handoff-to-execution transition audit trail

### Acceptance Criteria

- selected handoff types can be routed into governed workflows without manual reconstruction
- approval-required paths are explicit and enforced
- audit trail shows how a handoff moved toward execution
- no side effects happen outside existing policy constraints

### Out Of Scope

- multi-channel delivery
- broad connector write expansion
- orchestration redesign

## Sprint 32 (P8-S32)

### Title

Outcome Learning and Closure Quality

### Objective

Close the chief-of-staff operational loop by learning from handoff outcomes and feeding those signals into future guidance.

### Scope

- handoff outcome tracking
- closure metrics
- stale handoff escalation
- recommendation-to-execution learning signals

### Deliverables

- handoff outcome capture
- closure summary artifact
- recommendation-to-execution conversion signals
- stale-handoff escalation posture

### Acceptance Criteria

- outcomes are tracked with deterministic status semantics
- the system can identify which handoffs actually close loops
- stale and ignored handoffs influence later chief-of-staff prioritization
- users can see how outcome history changes future guidance

### Out Of Scope

- generic agent abstraction layer
- external platformization
- new vertical agent work

## Cross-Sprint Requirements

- preserve shipped Phase 5 continuity behavior
- preserve Phase 6 trust-calibration semantics
- preserve shipped Phase 7 chief-of-staff reasoning behavior
- keep all execution bridges approval-bounded
- keep provenance visible on all handoff artifacts

## Cross-Sprint Metrics

- handoff acceptance rate
- handoff execution rate
- stale handoff rate
- recommendation-to-execution conversion rate
- user rewrite rate on handoffs
- follow-through closure rate
- outcome capture rate

## Control Tower Notes

- treat `P8-S31` as the active anchor and build the rest of the phase around it
- do not relitigate P7-S25 through P7-S28 semantics during Phase 8
- do not relitigate shipped P8-S29 handoff-generation semantics during P8-S31
- do not relitigate shipped P8-S30 queue/review semantics during P8-S31
- do not turn Phase 8 into platformization or channel expansion
- prefer one clear artifact per sprint:
  - Sprint 29: action handoff brief
  - Sprint 30: handoff queue
  - Sprint 31: governed routing
  - Sprint 32: closure summary

## Definition Of Success

Phase 8 succeeds if Alice becomes operationally useful beyond recommendation:

- it prepares the next move
- it routes the next move safely
- it tracks what happened
- it improves future guidance based on actual closure outcomes

The phase fails if handoffs are only decorative exports that do not materially reduce the user’s execution burden.

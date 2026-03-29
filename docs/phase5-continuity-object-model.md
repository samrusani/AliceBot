# Phase 5 Continuity Object Model

## Purpose

This document defines the minimal typed continuity model for Phase 5. The goal is to support capture, recall, resumption, correction, and open-loop review without overengineering a full graph-native system.

## Design Rules

1. Every durable object must have provenance.
2. Every object must support temporal truth without silent overwrite.
3. Every correction must be representable as an event.
4. Retrieval should prefer confirmed, recent, relevant, and unsuperseded objects.
5. Raw capture events and derived continuity objects must remain distinct.

## Core Layers

### Capture Event

Immutable record of what the user said, submitted, or selected.

Required fields:

- `capture_event_id`
- `user_id`
- `thread_id` or equivalent scope
- `source_type`
- `raw_content`
- `created_at`
- `source_refs`

### Continuity Object

Derived durable object used for retrieval and resumption.

Shared required fields:

- `object_id`
- `object_type`
- `user_id`
- `status`
- `title`
- `summary`
- `provenance_refs`
- `confidence`
- `created_at`
- `updated_at`
- `last_confirmed_at`
- `valid_from`
- `valid_to`
- `superseded_by`

### Correction Event

Explicit event recording user confirmation, edit, delete, or supersession.

Required fields:

- `correction_event_id`
- `object_id`
- `correction_type`
- `before_snapshot`
- `after_snapshot`
- `created_at`
- `actor`

## Object Types

### Note

Use for captured information that is useful but not yet promoted to a stronger durable claim.

Additional fields:

- `body`
- `tags`
- `related_scopes`

### MemoryFact

Use for durable profile or contextual facts.

Examples:

- preference
- relationship fact
- stable work preference
- recurring routine detail

Additional fields:

- `fact_category`
- `subject_ref`
- `value`
- `stability`

### Decision

Use for resolved choices that affect future work.

Additional fields:

- `decision_text`
- `decided_at`
- `decision_scope`
- `participants`
- `rationale_summary`

### Commitment

Use for obligations owed by the user or by another party.

Additional fields:

- `owner`
- `due_at`
- `status_reason`
- `related_scope`

### WaitingFor

Use for dependencies awaiting external action or response.

Additional fields:

- `waiting_on`
- `last_ping_at`
- `expected_by`
- `related_scope`

### Blocker

Use for conditions preventing progress.

Additional fields:

- `blocking_reason`
- `blocked_scope`
- `blocking_entity`
- `severity`

### NextAction

Use for the single next concrete step in a scope.

Additional fields:

- `action_text`
- `owner`
- `due_at`
- `priority`
- `related_scope`

## Object Status

Allowed status values:

- `unconfirmed`
- `active`
- `completed`
- `cancelled`
- `superseded`
- `stale`

Not every type will use every status, but all objects should share one consistent posture vocabulary where possible.

## Temporal Model

Phase 5 should keep temporal logic simple and explicit.

Use:

- `valid_from`
- `valid_to`
- `last_confirmed_at`
- `superseded_by`

This supports:

- historical review
- changed preferences
- superseded decisions
- freshness checks

It avoids destructive overwrite while keeping retrieval logic manageable.

## Provenance Model

Every continuity object must link back to source evidence:

- capture event IDs
- thread/session/event IDs
- artifact IDs
- connector source IDs when relevant

Retrieval UI must expose provenance so the user can audit why an object exists.

## Admission Rules

### Always Create Capture Event

Every capture creates a capture event.

### Create Continuity Object Only When

- user provides explicit durable signal
- classifier confidence is high enough
- the object type is low-risk and reversible
- provenance is sufficient

### Prefer Triage Instead Of Pollution

When uncertain:

- keep the capture event
- do not create a durable object yet
- send item to review or triage

## Correction Rules

Correction types:

- `confirm`
- `edit`
- `delete`
- `supersede`
- `mark_stale`

Rules:

- correction event must be recorded before derived state is updated
- retrieval hot path must respect correction immediately
- supersession should preserve historical chain instead of overwrite

## Retrieval Ranking Inputs

Base ranking should consider:

- scope relevance
- recency
- confirmation state
- provenance quality
- object type match
- superseded/stale posture

Suggested ordering preference:

1. active confirmed objects
2. active unconfirmed objects
3. stale objects
4. superseded historical objects

Historical objects should still be retrievable for explicit temporal queries.

## Resumption Composition Rules

Resumption should compile from typed objects, not transcript replay.

Preferred object contribution:

- `Decision` -> last decision
- `Commitment` and `WaitingFor` -> open loops
- `Blocker` -> blocked state
- `NextAction` -> next step
- `Note` and `MemoryFact` -> supporting context

## Minimal Implementation Guidance

Phase 5 does not require a full graph database.

Good enough first pass:

- typed tables or typed JSON records on existing storage seams
- explicit relation references by IDs
- deterministic compiler logic over typed objects
- hot correction path
- cold consolidation path later

## Anti-Patterns To Avoid

- storing everything as generic memory text
- silently overwriting changed truths
- deriving durable memory without provenance
- mixing raw capture events with durable objects
- ranking stale or superseded objects as current truth

## Definition Of Good Enough

The model is good enough for Phase 5 if it supports:

- fast capture without losing information
- reliable recall with provenance
- deterministic resumption briefs
- correction-driven improvement
- explicit open-loop review

## P5-S17 Implemented Contract (March 29, 2026)

### Implemented Object Types

- `Note`
- `MemoryFact`
- `Decision`
- `Commitment`
- `WaitingFor`
- `Blocker`
- `NextAction`

### Implemented Capture Signals

- `remember_this`
- `task`
- `decision`
- `commitment`
- `waiting_for`
- `blocker`
- `next_action`
- `note`

### Implemented Admission Posture

- `DERIVED`: typed object admitted from explicit signal or deterministic high-confidence rule
- `TRIAGE`: immutable capture event persisted with no durable object admitted

### Implemented Provenance Minimum

Every admitted object carries provenance including:

- `capture_event_id`
- `source_kind = continuity_capture_event`
- `admission_reason`

## Deferred Beyond P5-S17

- correction-event persistence and supersession chains
- recall ranking UI and faceted recall query UX
- deterministic resumption brief product surfaces
- daily/weekly open-loop review dashboards

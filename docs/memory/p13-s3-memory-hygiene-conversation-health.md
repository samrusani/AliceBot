# P13-S3 Memory Hygiene + Conversation Health

This sprint adds bounded visibility surfaces for memory hygiene and conversation health without changing storage shape or continuity semantics.

## Shipped Surfaces

- `GET /v0/memories/hygiene-dashboard`
- `GET /v0/threads/health-dashboard`
- web memory hygiene panel in the memory review workspace
- web thread health panel in the continuity workspace
- CLI `alicebot status` extensions for hygiene and thread-health posture

## Memory Hygiene Coverage

The hygiene dashboard makes the following states visible in one summary:

- duplicate active memories grouped by normalized value and memory type
- stale facts derived from contested memories or bounded truth windows
- unresolved contradiction count from open contradiction cases
- weak-trust memory count from low-confidence, unconfirmed, or non-promotable facts
- review queue pressure derived from unlabeled queue size and queue aging

Each nonzero category ships with an explicit action string so the operator can decide what to inspect next.

## Conversation Health Coverage

The thread-health dashboard classifies threads across three dimensions:

- recent threads: last visible activity within 24 hours
- stale threads: last visible activity older than 72 hours
- risky threads: thread risk score at or above 2

Current risk score model:

- `+2` for any unresolved contradiction on a thread-scoped continuity object
- `+1` for any stale thread-scoped open-loop item
- `+1` for any active weak-inference trust signal on a thread-scoped continuity object
- `+1` when an active session remains open after more than 24 hours of inactivity

Overall thread posture is:

- `critical` when any risky thread is visible
- `watch` when stale or watch threads are visible without a risky thread
- `healthy` otherwise

## Scope Notes

- No new connector, runtime, persistence, or retrieval substrate was introduced.
- The dashboard builders aggregate existing thread, event, continuity, contradiction, trust-signal, and review-queue data.
- The first shipped thread-health surface is both API-visible and UI-visible.

## Verification

- targeted unit coverage for memory hygiene aggregation
- targeted unit coverage for thread-health aggregation
- page coverage for the memory and continuity workspace panels
- control-doc truth verification remains green

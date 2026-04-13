# Architecture

## Scope Boundary
This document treats Phase 11 as shipped baseline. New planned work here is the **Hermes Auto-Capture bridge phase** only.

## System Overview
Use a dual-path integration:
- **Hermes memory provider (shipped baseline, extended in bridge scope):** lifecycle automation hooks.
- **Alice MCP server (existing + extended):** explicit recall/review/explain operations.

This keeps Alice continuity semantics centralized while adding Hermes-native automation points.

## Technical Stack
- Core API/runtime: Python + FastAPI (`apps/api/src/alicebot_api`)
- Persistence: Postgres (+ existing continuity and provenance schema)
- Existing surfaces: CLI, MCP, web/admin, workers
- Hermes integration artifacts: provider plugin + Hermes config (`~/.hermes/config.yaml`)

## Module Boundaries
### Alice Core (already shipped)
- Continuity objects, revisions, provenance, corrections, open loops
- Recall/resume/context compilation
- Existing MCP/CLI APIs and policy controls

### Hermes Provider Adapter (bridge scope)
- Extends the shipped Hermes Alice provider rather than replacing it
- Reads provider config (`mode`, thresholds, feature toggles)
- Executes lifecycle hooks around Hermes turns/sessions
- Injects compact prefetch payload into Hermes prompt context

### MCP Tool Surface (explicit workflows)
Implemented in B1:
- `alice_prefetch_context`

Implemented in B2:
- `alice_capture_candidates`
- `alice_commit_captures`

Implemented in B3:
- `alice_review_queue`
- `alice_review_apply`

Planned for B4+:
- `alice_session_flush`

## Runtime Flows
### Flow 1: Pre-turn Prefetch
1. Hermes receives user input.
2. Provider calls `alice_prefetch_context`.
3. Alice returns compact continuity payload (summary, relevant memories, open loops, recent decisions/changes, optional resume brief, trust posture).
4. Provider injects payload into Hermes context before model response.

### Flow 2: Post-response Candidate Extraction (implemented in B2)
1. Hermes emits assistant response.
2. Provider sends user/assistant turn pair to `alice_capture_candidates`.
3. Alice returns typed candidates with confidence, trust class, proposed action, evidence snippet, and target object type.

### Flow 3: Post-response Commit (implemented in B2)
1. In `assist`/`auto`, provider submits candidates to `alice_commit_captures`.
2. Policy gates auto-save vs review queue using type allowlist + confidence threshold.
3. Writes are idempotent across repeated sync attempts.

### Flow 4: Session-End Flush (planned B4+)
1. On session end, provider calls `alice_session_flush`.
2. Alice performs dedupe merge, contradiction checks, open-loop normalization, summary refresh, and review queue updates.

## Data Model Summary
### Reuse Existing Baseline Objects
- continuity object graph
- correction/supersession history
- open-loop structures
- provenance evidence links

### Bridge-Phase Additions/Extensions (required)
- capture candidate records (including confidence + evidence)
- review queue records with lifecycle state
- commit decision audit trail (auto-saved vs queued vs rejected)

## Security And Trust Controls
- Preserve existing approval/provenance/correction contracts.
- Never auto-promote speculative single-turn inferences into higher-order trusted patterns.
- Keep confidence and type gating explicit and configurable by mode.
- Ensure workspace/session isolation in provider hook calls.
- Keep credential handling out of logs and redact sensitive provider connection details.

## Deployment Topology
### Recommended
- Hermes configured with external `alice` memory provider + enabled Alice MCP server.
- Provider and MCP may run against local Alice API base URL for local/self-hosted paths.

### Fallback
- MCP-only mode remains supported when provider plugin is not installed.

## Testing Strategy
### Bridge-Phase Required Tests
- prefetch context injection behavior
- explicit decision/correction auto-capture in `assist`
- low-confidence inference routes to review queue
- session-end flush behavior
- idempotency on duplicate sync attempts

### Existing Gates To Keep
- unit/integration suites
- MCP parity checks
- phase eval/regression harnesses already in repo

## Underspecified Areas (Control Tower Decisions Needed)
- Canonical candidate/review schema and migration details.
- Confidence model calibration and versioning policy.
- Provider package distribution/versioning strategy for Hermes installs.
- Auth boundary between Hermes provider process and Alice API in hosted deployments.
- UX surface ownership for review queue beyond MCP parity (web/CLI split not fully specified).

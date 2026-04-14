# Architecture

## Scope Boundary
This document treats Phases 9-11 and Bridge `B1` through `B4` as shipped baseline truth. The current active work is `R1` release readiness only.

## System Overview
Alice is a modular continuity platform with four shipped surface groups:

- **Alice Core:** typed continuity objects, provenance, correction/supersession, open loops, recall/resume/explain flows
- **Access Surfaces:** CLI, MCP, web/admin, hosted/product interfaces
- **Provider Runtime:** workspace-scoped provider registration, capability snapshots, model packs, runtime invocation, provider secret handling
- **Hermes Bridge:** external memory provider path with lifecycle automation, capture/review pipeline, explainable memory actions, and MCP fallback

## Technical Stack
- Core API/runtime: Python + FastAPI (`apps/api/src/alicebot_api`)
- Persistence: Postgres
- Web surface: `apps/web`
- Worker/ops scripts: `scripts/`
- Hermes integration artifacts: provider plugin + operator config/docs under `docs/integrations/`

## Module Boundaries

### Alice Core
- continuity object graph
- provenance evidence links
- corrections and supersession history
- recall, resume, explain, and open-loop flows

### Hosted/Product Layer
- identity/workspace/channel ownership from prior shipped phases
- user-facing control surfaces built on top of core continuity semantics

### Provider Runtime
- provider registration and testing
- model-pack binding and invocation
- local/self-hosted/enterprise adapter support
- provider secret management and workspace isolation

### Hermes Bridge
- pre-turn prefetch
- post-turn capture candidate generation and commit policy
- review queue and review apply flow
- explainability chain for bridge-generated memory actions
- provider-plus-MCP recommended deployment shape with MCP-only fallback

## Runtime Flows

### Flow 1: Explicit Continuity
1. CLI or MCP calls Alice continuity endpoints.
2. Alice returns typed recall/resume/open-loop/explain outputs.
3. Provenance and trust posture remain inspectable.

### Flow 2: Provider Runtime
1. Workspace registers a provider and optional model packs.
2. Runtime invokes provider through the workspace-scoped adapter boundary.
3. Continuity behavior remains in Alice rather than in provider-specific logic.

### Flow 3: Hermes Lifecycle Automation
1. Hermes calls Alice prefetch before a turn.
2. Hermes sends turn output to Alice capture/review paths after the response.
3. Alice auto-saves only policy-eligible high-confidence items and routes the rest to review.
4. MCP remains available for explicit deep workflows.

## Security And Trust Controls
- Continuity truth remains governed by provenance, correction, and supersession rules.
- Consequential side effects remain approval-bounded.
- Provider/runtime access stays workspace-scoped.
- Provider credentials and sensitive connection details must be redacted from logs and outward-facing error payloads.
- Hermes automation must not fork or bypass Alice trust rules.

## Deployment Topology

### Recommended
- Alice API + Postgres for the continuity system of record
- Alice MCP server for explicit workflows
- provider runtime where model/provider abstraction is needed
- Hermes provider-plus-MCP when always-on continuity is desired

### Fallback
- MCP-only integrations remain valid where provider automation is not available.

## Testing Strategy
- control-doc truth checks for canonical planning/doc alignment
- Python unit and integration suites for API/core/runtime regressions
- web tests for shipped UI/admin surfaces
- Hermes provider smoke, MCP smoke, and one-command demo for bridge validation

## Release-Readiness Focus
- public release docs must describe the shipped architecture accurately
- release gates must verify the surfaces the repo actively claims
- no architecture expansion is allowed inside the release sprint

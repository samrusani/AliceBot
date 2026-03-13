# Roadmap

## Current Position

- The accepted repo state is current through Sprint 5A.
- The backend foundation through governance, execution review, task/task-step lifecycle, explicit manual continuation, step-linked approval/execution synchronization, and deterministic rooted task-workspace provisioning is already shipped.
- This roadmap is future-facing from that position; milestone history lives in archived sprint reports, not here.

## Next Delivery Focus

### Finish Milestone 5 On Top Of The Shipped Workspace Boundary

- Add artifact records and artifact-handling rules that reuse `task_workspaces` instead of inventing a parallel storage seam.
- Add document ingestion and retrieval only after the artifact/workspace boundary is explicit and reviewable.
- Add read-only Gmail and Calendar connectors only after document and workspace boundaries remain deterministic under the current governance model.

### Preserve Current Governance And Task Guarantees

- Keep approvals, execution budgets, task/task-step state, and trace visibility deterministic as new Milestone 5 work lands.
- Do not widen the current no-external-I/O proxy surface or introduce new consequential side effects without an explicit sprint opening that scope.

## After Milestone 5

- Revisit broader task orchestration only after the current explicit task-step seams remain stable under workspace, artifact, and document flows.
- Expand tool execution breadth only after governance, review, and budget controls still hold under the wider task surface.
- Address production-facing auth and deployment hardening as the product approaches broader real-world use.

## Dependencies

- Live truth docs must stay synchronized with accepted repo state so sprint planning does not start from stale assumptions.
- Artifact and document work should build on the existing rooted local workspace contract.
- Connector work should remain read-only and approval-aware.
- Runner-style orchestration should stay deferred until the repo no longer depends on narrow current-step assumptions for safety and explainability.

## Ongoing Risks

- Memory extraction and retrieval quality remain the largest product risk.
- Auth beyond database user context is still missing.
- Milestone 5 can drift if artifact, document, connector, and orchestration work are mixed into one sprint instead of landing as narrow seams.

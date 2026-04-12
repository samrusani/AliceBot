# Roadmap

## Baseline Context (Shipped, Not Roadmap Work)
- Phase 9: shipped
- Phase 10: shipped
- Phase 11: shipped

Phase 11 remains baseline truth and is not future scope.

## Active Planning Status
- Bridge Sprint 1 (`B1`) is the active execution sprint.
- The remaining bridge-phase milestones are planned but not yet promoted.

## Bridge Phase: Hermes Auto-Capture (Planned)

### B1: Hermes Memory Provider Foundation
- formalize the shipped Alice Hermes external memory provider into the bridge-phase contract
- wire pre-turn hook, post-response hook, and session-end hook
- parse provider config and expose provider status checks
- preserve additive coexistence with Hermes built-in `MEMORY.md` and `USER.md`
- standardize the preferred provider-plus-MCP integration shape

### B2: Auto-Capture Pipeline
- ship `alice_capture_candidates` + `alice_commit_captures`
- enforce mode policy (`manual`, `assist`, `auto`) and confidence thresholds
- add candidate type classification for decision, commitment, waiting-for, blocker, preference, correction, note, and no-op
- persist review-queue candidates
- guarantee idempotent repeated sync behavior
- ensure no-op turns produce no memory writes
- implement the auto-save vs review-required policy contract from the product brief

### B3: Review Queue + Explainability
- ship `alice_review_queue` + `alice_review_apply`
- support approve/reject/edit/supersede actions
- preserve provenance/explanation chain for candidate proposals
- ensure correction-aware parity across UI/CLI/MCP paths
- make approved review actions change subsequent recall/resume results deterministically

### B4: Packaging, Docs, and Smoke Validation
- publish Hermes integration guide and config examples
- publish example `config.yaml` for provider-plus-MCP and MCP-only fallback modes
- document provider+MCP recommended architecture
- publish a short "why provider + MCP" operator decision doc
- publish MCP-only fallback and migration path
- deliver smoke-test scripts and one-command local demo path
- make provider mode the clearly recommended path in docs once smoke evidence passes

## Sequencing Rules
- Build provider lifecycle hooks before capture policy automation.
- Land capture/commit policy before review UX/process expansion.
- Validate idempotency and trust gating before broad rollout.
- Keep MCP fallback available during bridge rollout.
- Keep the shipped Hermes provider as baseline and extend it rather than replacing it.

## Beyond Bridge (Future, Not Yet Defined)
- Post-bridge roadmap phases are not yet defined in canonical planning.
- Phase naming, sprinting, and scope for beyond-bridge work require a new planning packet.

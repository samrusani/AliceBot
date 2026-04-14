# Rules

## Baseline Truth Discipline
- Treat Phases 9-11 and Bridge `B1` through `B4` as shipped baseline truth.
- Keep shipped baseline, active release work, and future roadmap clearly separated.
- Keep `ROADMAP.md` future-facing and `.ai/handoff/CURRENT_STATE.md` factual/current.

## Continuity Semantics Rules
- Never fork continuity semantics by surface or runtime.
- Provider runtime and Hermes automation may change timing or transport, but memory truth remains in Alice continuity contracts.
- Preserve provenance, correction, and supersession behavior across all capture paths.

## Integration Rules
- For Hermes, use provider hooks for automation and MCP for explicit deep actions.
- Do not collapse to provider-only or MCP-only as the canonical target architecture.
- Keep MCP fallback viable even when provider mode is the recommended deployment shape.

## Capture Policy Rules
- Default automation mode is `assist` unless explicitly overridden.
- Auto-save only explicit high-confidence items that are policy-eligible.
- Route inferred, weak, speculative, or low-confidence items to review.
- Never auto-promote a single-turn inference into higher-order trusted patterns or playbooks.

## Reliability Rules
- Post-response capture and commit paths must be idempotent.
- No-op turns must not create memory writes.
- Release evidence must be based on exact commands actually executed, not inferred pass states.

## Security Rules
- Maintain workspace/session isolation for provider and MCP calls.
- Keep provider and API credentials out of logs, serialized responses, and outward-facing error payloads.
- Keep consequential actions approval-bounded regardless of integration mode.

## Release Discipline Rules
- `v0.2.0` is a pre-1.0 release, not a `1.0.0` contract.
- Do not widen release-prep sprints into feature work.
- Do not let README, release docs, or changelog claims outrun shipped behavior.
- Keep superseded release docs as historical references only.

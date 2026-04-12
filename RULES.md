# Rules

## Baseline Truth Discipline
- Treat Phase 11 as shipped baseline truth; do not restate it as future roadmap scope.
- Keep shipped baseline, bridge-phase plan, and future roadmap clearly separated.
- Keep `ROADMAP.md` future-facing and `.ai/handoff/CURRENT_STATE.md` factual/current.

## Integration Rules
- For Hermes, use provider hooks for automation and MCP for explicit deep actions.
- Do not collapse to provider-only or MCP-only as the canonical target architecture.
- Keep MCP fallback viable while provider mode matures.

## Continuity Semantics Rules
- Never fork continuity semantics by surface or runtime.
- Provider behavior may automate lifecycle timing, but memory truth remains in Alice continuity contracts.
- Preserve provenance, correction, and supersession behavior across all capture paths.

## Capture Policy Rules
- Default mode is `assist` unless explicitly overridden.
- Auto-save only explicit high-confidence items: correction, preference, decision, commitment, open-loop create/resolve.
- Route inferred/weak/speculative or low-confidence items to review queue.
- Never auto-promote a single-turn inference into higher-order trusted patterns/playbooks.

## Reliability Rules
- Post-response capture/commit paths must be idempotent.
- Session-end flush must run dedupe, contradiction checks, open-loop normalization, and summary refresh.
- No-op turns must not create memory writes.

## Security Rules
- Maintain workspace/session isolation for provider and MCP calls.
- Keep provider/API credentials out of logs and error payloads.
- Keep consequential actions approval-bounded regardless of integration mode.

## Documentation Rules
- Keep canonical files concise and durable.
- Move major technical commitments into ADRs instead of expanding architecture prose.
- Archive investor framing, long sprint diaries, and superseded planning drafts out of active memory docs.

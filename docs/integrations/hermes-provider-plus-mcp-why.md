# Why Provider + MCP Is Recommended

## Decision

Use **provider plus MCP** as the default Hermes architecture for Alice continuity.

## Why

- Provider gives always-on turn-start continuity prefetch without requiring tool calls.
- Provider runs bridge lifecycle hooks (`prefetch`, `queue_prefetch`, `sync_turn`, `on_session_end`) so capture behavior is consistent.
- MCP preserves explicit deep workflows (`alice_review_queue`, `alice_review_apply`, `alice_explain`) for operator control.
- Keeping both paths avoids workflow regressions while preserving deterministic Alice semantics.

## Fallback

Use MCP-only when provider installation is blocked by environment policy.

- Keep `memory.provider: builtin`.
- Keep Alice MCP server configured.
- Migrate to provider+MCP once provider install is available.

## Operator Rule

- Prefer provider for automatic continuity lifecycle behavior.
- Prefer MCP for explicit deep actions and audit-friendly corrections.

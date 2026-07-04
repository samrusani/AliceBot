# Why Provider + MCP Is Recommended

## Decision

Use **provider plus MCP** as the default Hermes architecture for Alice continuity.

## Why

- Provider gives always-on turn-start continuity prefetch without requiring tool calls.
- Provider runs bridge lifecycle hooks (`prefetch`, `queue_prefetch`, `sync_turn`, `on_session_end`) so capture behavior is consistent.
- MCP preserves explicit deep workflows for operator control: `alice_memory_review`, `alice_memory_correct`, and `alice_explain` on the core surface, plus the legacy `alice_review_queue`/`alice_review_apply` tools when the server runs with `ALICE_MCP_LEGACY_TOOLS=1`.
- Keeping both paths avoids workflow regressions while preserving deterministic Alice semantics.

## Fallback

Use MCP-only when provider installation is blocked by environment policy.

- Keep `memory.provider: builtin`.
- Keep Alice MCP server configured.
- Migrate to provider+MCP once provider install is available.

## Operator Rule

- Prefer provider for automatic continuity lifecycle behavior.
- Prefer MCP for explicit deep actions and audit-friendly corrections.

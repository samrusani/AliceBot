# Rules

## Baseline Truth

- Phase 10 must not fork semantics between local, CLI, MCP, and Telegram.
- Do not rewrite shipped Phase 9 capabilities as future roadmap items.
- Treat shipped Phase 10 capability as baseline truth, not roadmap scope.
- Do not reframe shipped Alice Core/Connect behavior as aspirational work.
- Keep `ROADMAP.md` future-facing and `.ai/handoff/CURRENT_STATE.md` factual/current.

## Product Boundaries

- Alice remains continuity-first, not a generic autonomous platform.
- Provider/model expansion must preserve OSS baseline and hosted/enterprise boundary clarity.
- Do not conflate provider support with complete agent-framework support.

## Architecture Rules

- Never fork continuity semantics by provider, model, or runtime.
- Provider-specific quirks belong in adapters or declarative packs, not core semantics.
- Model pack behavior must be declarative, versioned, and explicit.
- Keep provider contract normalization mandatory for responses, tools, and usage.

## Scope Control

- Build interfaces first (OpenAI-compatible base), then provider breadth, then pack breadth.
- No deep optimization for one model family before abstraction stability.
- Do not ship broad pack catalogs before tier-1 packs are production-clean.
- Do not add non-Phase-11 channel/surface expansion under adapter-pack scope.

## Security And Reliability

- Store provider credentials as encrypted references; never log plaintext secrets.
- Require idempotency and auditability for provider invoke paths.
- Keep consequential actions approval-bounded on every provider/runtime path.
- Maintain cross-workspace isolation for provider configs and pack bindings.

## Documentation Discipline

- Keep canonical operating files concise and non-duplicative.
- Move major long-lived decisions into ADRs instead of bloating architecture docs.
- Archive superseded plans, investor framing, and sprint diaries out of live memory files.

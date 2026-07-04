# Roadmap

## Baseline (Not Roadmap Work)
- `v0.5.1`: released. Local-first memory core, provenance, trust classes, open loops, resumption briefs, CLI/API/MCP surfaces, review console.

## In Progress: Product Overhaul (this branch)
Reposition Alice as the continuity layer for AI agents and ship as one release:

- **Retrieval rebuild** — Postgres full-text + pgvector (HNSW) fused with reciprocal-rank fusion; configurable OpenAI-compatible embedding endpoint; explicit full-text degradation when unconfigured.
- **MCP consolidation** — nine core tools; legacy tools behind `ALICE_MCP_LEGACY_TOOLS=1`.
- **Agent auth** — per-agent API keys.
- **Honest evals** — eval suites that execute the production pipeline.
- **Packaging and docs** — one quickstart path, archived process docs, consistent "Alice" naming, PyPI packaging as `alice-memory`.

## Next (After the Overhaul Ships)
Candidates, in no committed order:

- Publish `alice-memory` to PyPI and cut the first post-overhaul release.
- Deeper reference integrations for popular agent frameworks.
- Multi-agent memory scoping and richer per-agent policy.
- Hosted offering exploration (requires RLS posture and auth work already in place).

## Explicit Non-Goals For Now
- Hosted service / SLA commitments.
- OAuth connectors and managed account syncing.
- Consumer-facing knowledge-management product (possible later product on top of the agent surface).
- OCR/transcription execution claims beyond payload ingestion of already-extracted text.

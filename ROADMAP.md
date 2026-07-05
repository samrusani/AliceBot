# Roadmap

## Baseline (Not Roadmap Work)
- Memory-frontier waves (merged to main, unreleased): budgeted context packs, typed retrieval, staleness v1, agentic write protocol on the core MCP surface (11 tools), memory-quality eval suites, real scopes with key binding, merging consolidation, temporal slice, LongMemEval harness.
- **LongMemEval_s: 64.6%** published with full methodology and per-question evidence in [docs/benchmarks/longmemeval/](docs/benchmarks/longmemeval/README.md) (Zep reports 63.8%; Mem0 ~49%).
- `v0.7.0`: released. Zero-infrastructure SQLite on-ramp — `uvx alice-memory mcp` serves the core tools with no Docker or Postgres; published to PyPI via Trusted Publishing.
- `v0.6.0`: released. The product-viability overhaul — hybrid retrieval (FTS + pgvector + RRF), consolidated MCP surface, per-agent API keys, honest live-store evals, repositioned docs.
- `v0.5.1`: prior baseline. Local-first memory core, provenance, trust classes, open loops, resumption briefs, CLI/API/MCP surfaces, review console.

## Next
In rough priority order:

1. **Multi-session synthesis** — the weakest LongMemEval category (45.1%): retrieval breadth across sessions plus consolidation-driven aggregation; benchmark-driven iteration with the per-type breakdown as the scoreboard.
2. **Cut the next release** — tag and publish the memory-frontier waves (migrations 0075-0077, 11-tool surface, benchmark results) as the next version.
3. **Dogfood daily** — run the stack against real agents with an embedding endpoint; calibrate the paraphrase target of the `retrieval_quality` benchmark; generate the usage telemetry that future ranking/policy improvements need.
4. **Reference integrations** — deeper examples for popular agent frameworks on the core tool surface.
5. **Merge/expire operations** — complete the Memory Operations Protocol (consolidation acceptance flow already produces merge candidates; expire builds on staleness v1).
6. **Hosted offering exploration** — the RLS posture and auth work make this plausible; still exploratory.

## Explicit Non-Goals For Now
- Hosted service / SLA commitments.
- OAuth connectors and managed account syncing.
- Consumer-facing knowledge-management product (possible later product on top of the agent surface).
- OCR/transcription execution claims beyond payload ingestion of already-extracted text.

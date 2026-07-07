# Roadmap

## Baseline (Not Roadmap Work)
- **LongMemEval_s: 79.4%** published with full methodology and per-question evidence in [docs/benchmarks/longmemeval/](docs/benchmarks/longmemeval/README.md). We don't quote other tools' numbers — published runs differ in response models, pipelines, and dataset revisions; our per-question receipts are committed so the run can be judged directly.
- `v0.9.0`: released. Complete Memory Operations Protocol (all ten verbs, including true `redact`), Context API v2 (per-section budgets, packing strategies, depth tiers), full export/import round-trip, temporal graph memory + entity resolution with the `entity_resolution` and `graph_hop_retrieval` eval suites, and the published scale envelope.
- `v0.8.0`: released. The memory-frontier waves — budgeted context packs, typed retrieval, staleness v1, agentic write protocol on the core MCP surface (11 tools), memory-quality eval suites, real scopes with key binding, merging consolidation, temporal slice, LongMemEval harness — plus Alice's first published benchmark result.
- `v0.7.0`: released. Zero-infrastructure SQLite on-ramp — `uvx alice-memory mcp` serves the core tools with no Docker or Postgres; published to PyPI via Trusted Publishing.
- `v0.6.0`: released. The product-viability overhaul — hybrid retrieval (FTS + pgvector + RRF), consolidated MCP surface, per-agent API keys, honest live-store evals, repositioned docs.
- `v0.5.1`: prior baseline. Local-first memory core, provenance, trust classes, open loops, resumption briefs, CLI/API/MCP surfaces, review console.

## Next
In rough priority order:

1. **Multi-session synthesis** — still the weakest LongMemEval category and the top item: the retrieval-breadth fixes lifted it from 45.1% to 58.6%, but questions assembled from evidence scattered across many sessions remain the clear frontier. The query-shape-aware aggregation mode remains the planned next step; benchmark-driven iteration with the per-type breakdown as the scoreboard.
2. **Dogfood daily** — run the stack against real agents with an embedding endpoint; calibrate the paraphrase target of the `retrieval_quality` benchmark; generate the usage telemetry that future ranking/policy improvements need.
3. **Reference integrations** — deeper examples for popular agent frameworks on the core tool surface.
4. **SQLite vector search at scale** — push the local-first on-ramp's embedding search past its documented ~20–30k comfort zone (brute-force cosine hits ~2.3s at 100k memories in the [scale envelope](docs/benchmarks/scale/README.md)): quantize stored embeddings (int8/binary) and rescore the top candidates at full precision, with the recall deltas published alongside the latency wins. Proven techniques, no new dependencies; recent results like Google's TurboQuant line (ICLR 2026) show how much headroom few-bit vector quantization has, and serve as the reference point for how far to take it.
5. **Hosted offering exploration** — the RLS posture and auth work make this plausible; still exploratory.

## Explicit Non-Goals For Now
- Hosted service / SLA commitments.
- OAuth connectors and managed account syncing.
- Consumer-facing knowledge-management product (possible later product on top of the agent surface).
- OCR/transcription execution claims beyond payload ingestion of already-extracted text.

# Roadmap

## Baseline (Not Roadmap Work)
- `v0.6.0`: released. The product-viability overhaul — hybrid retrieval (FTS + pgvector + RRF), nine-tool MCP surface, per-agent API keys, honest live-store evals, repositioned docs, `alice-memory` PyPI name claimed.
- `v0.5.1`: prior baseline. Local-first memory core, provenance, trust classes, open loops, resumption briefs, CLI/API/MCP surfaces, review console.

## Next
In rough priority order:

1. **Dogfood with real embeddings** — run the stack daily with an Ollama/LM Studio embedding endpoint; calibrate the paraphrase target of the `retrieval_quality` benchmark against a real model.
2. **SQLite on-ramp** — `uvx alice-memory` to a working local MCP memory server without Docker or Postgres (plan: `docs/plans/sqlite-onramp.md`); ship it as the first real PyPI release.
3. **Public benchmark** — run LongMemEval (or equivalent) on the calibrated hybrid pipeline and publish methodology and scores.
4. **Reference integrations** — deeper examples for popular agent frameworks on the nine-tool surface.
5. **Multi-agent memory scoping** — richer per-agent policy on top of the API-key identity layer.
6. **Hosted offering exploration** — the RLS posture and auth work now make this plausible; still exploratory.

## Explicit Non-Goals For Now
- Hosted service / SLA commitments.
- OAuth connectors and managed account syncing.
- Consumer-facing knowledge-management product (possible later product on top of the agent surface).
- OCR/transcription execution claims beyond payload ingestion of already-extracted text.

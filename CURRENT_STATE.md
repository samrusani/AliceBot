# Current State

This file is a synced repo-root copy for planning visibility.
Canonical handoff state lives at [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md).

## Snapshot
- `v0.5.1` is the latest tagged pre-1.0 baseline: local-first memory core, provenance, trust classes, correction/supersession, open loops, resumption briefs, CLI/API/MCP surfaces, and the local review console.
- The `product-overhaul` branch is in progress. It repositions Alice as the continuity layer for AI agents (agent developers are the customer) and lands as one release.

## Product-Overhaul Workstreams
- **Retrieval rebuild** — search is Postgres full-text plus pgvector (HNSW) fused with reciprocal-rank fusion; embeddings come from a configurable OpenAI-compatible endpoint (`ALICE_EMBEDDINGS_BASE_URL` / `ALICE_EMBEDDINGS_MODEL` / `ALICE_EMBEDDINGS_API_KEY`); unconfigured search degrades to full-text with an explicit trace note.
- **MCP consolidation** — nine core tools; the legacy tool surface stays behind `ALICE_MCP_LEGACY_TOOLS=1`.
- **Agent auth** — per-agent API keys for HTTP API access.
- **Honest evals** — eval suites execute the production retrieval/commit pipeline; no simulated passes.
- **Packaging** — one quickstart path (`make setup && make migrate && make doctor && make dev`); process docs archived under `docs/archive/process/`; Python package will publish to PyPI as `alice-memory`.

## Boundaries That Hold
- Review-governed writes: agent memory commits resolve to commit, confirm, review, or reject through policy; no direct database writes by agents.
- Local-first, single-user; no hosted service; no OAuth connectors; no automatic capture from arbitrary conversation.

## Not Current State
- Nothing on PyPI/npm yet; no hosted offering; no SLA.

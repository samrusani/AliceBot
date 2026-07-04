# Product Brief

## What Alice Is
Alice is the continuity layer for AI agents: a local-first memory service that lets agents resume interrupted work, track open loops, recall decisions with provenance, and improve when corrected. Agents connect over MCP, HTTP API (per-agent API keys), or CLI.

## Customer
Agent developers — people building or operating AI agents who need durable, explainable memory across sessions. A human-facing knowledge product may come later, built on the same surface; it is not the current target.

## What Makes It Different
- Typed continuity objects: decisions, open loops, resumption briefs — not just extracted facts.
- Explainable provenance: every memory traces back to source evidence, reviews, and corrections.
- Review-governed writes: agent commits resolve to commit, confirm, review, or reject through policy; the review console is the trust boundary.
- Local-first: your data stays on your machine; models and embeddings are pluggable via OpenAI-compatible endpoints.

## Current Posture
- `v0.5.1` is the tagged pre-1.0 baseline.
- The `product-overhaul` branch is landing: retrieval rebuild (full-text + pgvector fused with RRF), MCP consolidation to nine core tools, per-agent API keys, evals that execute the production pipeline, and single-path packaging.
- Pre-1.0, single-user, self-hosted from a repo checkout. Python package will publish to PyPI as `alice-memory`.

## Non-Goals (Now)
- Hosted service, SLA, or managed cloud.
- OAuth connectors / automatic account syncing.
- Automatic memory capture from arbitrary conversation.
- Marketplace, channels, or vertical-agent products.

## Success Criteria For The Overhaul
- An agent developer can go from clone to a working MCP-connected memory in one quickstart path.
- Search quality is measurably better with embeddings configured, and honestly labeled when degraded.
- The MCP surface is small enough to learn in one sitting.
- Every claim in the docs matches shipped behavior.

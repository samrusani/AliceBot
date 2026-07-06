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
- `v0.9.0` is the tagged release: hybrid retrieval (full-text + pgvector fused with RRF), the eleven-tool core MCP surface with the agentic write protocol and complete Memory Operations Protocol, per-agent API keys, Context API v2, temporal graph memory + entity resolution, six live eval suites that execute the production pipeline, and a published **64.6% LongMemEval_s** result with per-question evidence.
- Pre-1.0, single-user, self-hosted. `alice-memory` is published on PyPI; `uvx alice-memory mcp` serves the core tools against a local SQLite file with no Docker or Postgres.

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

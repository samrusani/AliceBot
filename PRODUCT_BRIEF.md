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
- `v0.9.4` is the latest published release and immutable baseline. It attempted the second-audit remediation, but a third independent audit found partial fixes and regressions; current closure evidence lives in the v0.10.0 handoff matrix. Trusted Publishing attestations and artifact digests remain recorded in `docs/release/v0.9.4-checksums.txt`. The product baseline includes hybrid retrieval, the eleven-tool core MCP surface, the Memory Operations Protocol, per-agent API keys, Context API v2, temporal graph memory/entity resolution, six live eval suites, and a historical **79.4% LongMemEval_s (397/500)** single run with per-question evidence.
- `v0.9.2` is now a prior published release: a security and reliability patch for key-bound project authorization, lifecycle and upgrade correctness, safe local backup/restore, retrieval contracts, web dependencies, packaging, and release evidence. It remains tagged and published on PyPI and GitHub, but is no longer the latest published release — `v0.9.4` is.
- `v0.10.0` is the active audit-remediation candidate. Correctness and release evidence take priority over feature work; no v0.10.0 work is published yet.
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

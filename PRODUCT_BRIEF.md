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
- `v0.10.2` is the latest published release and immutable baseline. Its PyPI
  wheel and source distribution have Trusted Publishing provenance, with exact
  digests in `docs/release/v0.10.2-checksums.txt`.
- The product baseline includes hybrid retrieval, the eleven-tool core MCP
  surface, the Memory Operations Protocol, per-agent API keys, Context API v2,
  temporal graph memory/entity resolution, and six live eval suites.
- The **79.4% LongMemEval_s (397/500)** figure is one historical run from
  2026-07-07 with per-question evidence. It is not a repeated-run estimate or a
  fresh v0.10.2 benchmark.
- `main` plus the reviewed remediation tree form the `v0.10.3` candidate.
  It is a release candidate only. Those changes are unreleased and publish only after exact-SHA
  gates and independent review pass.
- Alice is public-alpha, pre-1.0, single-user, and self-hosted. `alice-memory`
  is published on PyPI; `uvx alice-memory mcp` serves the core tools against a
  local SQLite file with no Docker or Postgres.

## Non-Goals (Now)
- Hosted service, SLA, or managed cloud.
- Managed OAuth consent/account-linking flows or automatic account syncing.
  Manual operator-token Gmail and Calendar backends exist, but Alice does not
  package managed consent or polling.
- Automatic memory capture from arbitrary conversation.
- Marketplace, channels, or vertical-agent products.

## Success Criteria For The Overhaul
- An agent developer can go from clone to a working MCP-connected memory in one quickstart path.
- Search quality is measurably better with embeddings configured, and honestly labeled when degraded.
- The MCP surface is small enough to learn in one sitting.
- Every claim in the docs matches shipped behavior.

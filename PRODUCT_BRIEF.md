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
- `v0.9.4` is the latest published release: a security and reliability hotfix over v0.9.2 that supersedes the withdrawn `v0.9.3` candidate. It carries the original five v0.9.3 fixes — lifecycle state-machine defects (one central transition table), expire/unexpire row-locking races, a migration-0083 identifier-reservation bug (corrective migration 0084), project-scoped capture persistence, and hard people/time filter pagination — and additionally resolved all nine P1 findings from the follow-up external audit that returned NO-GO on `v0.9.3`. It is tagged and published on PyPI and GitHub as an immutable release, with Trusted Publishing attestations and artifact digests recorded in `docs/release/v0.9.4-checksums.txt`. This sits on top of hybrid retrieval (full-text + pgvector fused with RRF), the eleven-tool core MCP surface, the Memory Operations Protocol, per-agent API keys, Context API v2, temporal graph memory and entity resolution, six live eval suites, the round-2..6 retrieval and memory features already in the changelog, and a historical **79.4% LongMemEval_s (397/500)** single run with per-question evidence.
- `v0.9.2` is now a prior published release: a security and reliability patch for key-bound project authorization, lifecycle and upgrade correctness, safe local backup/restore, retrieval contracts, web dependencies, packaging, and release evidence. It remains tagged and published on PyPI and GitHub, but is no longer the latest published release — `v0.9.4` is.
- `v0.10.0` is the current development-cycle candidate: the reopened next cycle of feature work (multi-session synthesis, daily dogfooding, reference integrations) plus the second audit's P2 backlog (full-package mypy + web typecheck, packaged-README PyPI links, backup/restore hardening, N+1 retrieval fan-out, non-finite embedding validation, and related items). `v0.9.3` was an internal security-hotfix candidate that was withdrawn and never published; no `v0.10.0` work is published yet.
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

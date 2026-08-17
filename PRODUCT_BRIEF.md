# Product Brief

## What Alice Is
Alice is the continuity layer for AI agents: a local-first memory service that lets agents resume interrupted work, track open loops, recall decisions with provenance, and improve when corrected. Agents connect over MCP, HTTP API (per-agent API keys), or CLI.

## Customer
Agent developers — people building or operating AI agents who need durable, explainable memory across sessions. A human-facing knowledge product may come later, built on the same surface; it is not the current target.

## What Makes It Different
- Typed continuity objects: decisions, open loops, resumption briefs — not just extracted facts.
- Explainable provenance: source-backed memories trace to source evidence where
  present, while reviews and corrections preserve their own audit chain.
  Explicit commits may legitimately have no source reference.
- Review-governed writes: agent commits resolve to commit, confirm, review, or reject through policy; the review console is the trust boundary.
- Local-first: your data stays on your machine; models and embeddings are pluggable via OpenAI-compatible endpoints.

## Current Posture
- `v0.15.7` is the latest published release and immutable baseline. Imported
  notes are readable as sources. `v0.15.6` is the immediately prior
  published release. The PyPI wheel and source distribution have Trusted
  Publishing provenance, with exact digests in
  `docs/release/v0.15.7-checksums.txt`.
- `v0.11.0` shipped the Phase 1 periphery cut. It removes the Telegram,
  hosted/control-plane, public chat/response, chief-of-staff, and model-pack
  periphery so the default runtime matches the product described here. The
  low-level response job machinery remains internal to retained provider
  invocation.
- The product baseline includes hybrid retrieval, the eleven-tool core MCP
  surface, the Memory Operations Protocol, per-agent API keys, Context API v2,
  temporal graph memory/entity resolution, and six live eval suites.
- LongMemEval_s stands at **81.2% mean over three independent full runs**
  (80.8 / 81.0 / 81.8) with per-question evidence for each committed. It is a
  measurement of the published `v0.12.0` tag, not of the current release. The
  **79.4% (397/500)** single run from 2026-07-07 is superseded as the headline
  and retained as evidence.
- The fourth-audit remediation shipped in `v0.10.3` after exact-SHA gates
  and independent review passed.
- Alice is public-alpha, pre-1.0, single-user, and self-hosted. `alice-memory`
  is published on PyPI; `uvx alice-memory mcp` serves the core tools against a
  local SQLite file with no Docker or Postgres.
- `v0.12.0` shipped the Phase 3 structural refactor with **Structure only.
  Zero behavior change.** It relocates oversized HTTP, store, contract, MCP,
  and CLI modules behind stable facades and entrypoints without changing the
  local-first product boundary.
- Phase 4 shipped as `v0.13.1`. Phase 5, the enterprise track, shipped as
  `v0.14.0`. Phase 6, the counting substrate, is parked; see ROADMAP.

## Non-Goals (Now)
- Hosted service, multi-tenant control plane, SLA, or managed cloud.
- Telegram or other channel transports.
- Managed OAuth consent/account-linking flows or automatic account syncing.
  Temporary manual-token Gmail and Calendar compatibility is unmounted by
  default behind `ALICE_LEGACY_SURFACES=1`.
- A public bundled chat/response product, chief-of-staff product, or model-pack
  catalog.
- Automatic memory capture from arbitrary conversation.
- Marketplace, channels, or vertical-agent products.
- OCR or transcription execution; Alice ingests text extracted elsewhere.

## Success Criteria For The Overhaul
- An agent developer can go from clone to a working MCP-connected memory in one quickstart path.
- Search quality is measurably better with embeddings configured, and honestly labeled when degraded.
- The MCP surface is small enough to learn in one sitting.
- Every claim in the docs matches shipped behavior.

`v0.15.7` is the latest published release and remains the install, checksum,
and baseline reference.

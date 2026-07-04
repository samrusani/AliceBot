# Current State

This file is a synced repo-root copy for planning visibility.
Canonical handoff state lives at [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md).

## Snapshot
- `v0.6.0` is the latest release: the product-viability overhaul is merged to `main` and tagged.
- Alice is positioned as the continuity layer for AI agents; agent developers are the customer.

## What `v0.6.0` Contains
- **Hybrid retrieval** — Postgres full-text plus pgvector (HNSW) fused with reciprocal-rank fusion; embeddings from a configurable OpenAI-compatible endpoint (`ALICE_EMBEDDINGS_BASE_URL` / `ALICE_EMBEDDINGS_MODEL` / `ALICE_EMBEDDINGS_API_KEY`); unconfigured search degrades to full-text with an explicit trace note.
- **MCP surface** — nine core tools by default; the legacy tool surface stays behind `ALICE_MCP_LEGACY_TOOLS=1`; legacy continuity recall lives on `alice_recall_debug`.
- **Agent auth** — per-agent API keys (`alice_sk_*`, hashed at rest, RLS-scoped) enforced on all vNext agent HTTP endpoints and optionally on MCP via `ALICE_AGENT_API_KEY`; profile escalation is rejected and audited.
- **Honest evals** — the `retrieval_quality` suite executes the production retrieval/commit pipeline against a live store (`ALICEBOT_EVAL_DATABASE_URL`); no simulated passes.
- **Packaging** — one quickstart path (`make setup && make migrate && make doctor && make dev`); process docs archived under `docs/archive/process/`; PyPI name `alice-memory` claimed with a placeholder release.
- **Verification** — 1,249 unit and 377/377 integration tests green; migration chain verified up/down/up; scheduler `memory_consolidation` constraint fixed (migration `20260704_0074`).

## Boundaries That Hold
- Review-governed writes: agent memory commits resolve to commit, confirm, review, or reject through policy; no direct database writes by agents.
- Local-first, single-user; no hosted service; no OAuth connectors; no automatic capture from arbitrary conversation.

## Not Current State
- The PyPI release is a name-holding placeholder; the packaged runtime (including the planned SQLite on-ramp) is not published yet. No npm packages, no hosted offering, no SLA.

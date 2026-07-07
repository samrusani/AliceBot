# Changelog

## Unreleased

- Retrieval bug fix: the sources stage was content-blind (matched only titles/metadata with a broken stopword list, effectively returning the most-recent sessions); it is now RRF fusion over chunk-level full-text hits, provenance of winning memories, and title/recency — plus an FTS OR-fallback when strict AND finds nothing.
- Excerpt packing guarantees each retrieved source its best chunk before spending the remaining budget, rendered in session-timestamp order.
- LongMemEval_s: **79.4%** (397/500, single run 2026-07-07) vs the 64.6% baseline, paired on the same 500 questions (net +74, McNemar p = 3.26e-12); every question type improved, multi-session 45.1% → 58.6%. Config disclosed: official chain-of-thought reading template, 16 items / 24k-char context (was standard / 8 / 12k).
- Known trade-off disclosed: the abstention subset regressed 25/30 → 22/30 — the CoT reading style makes the model more willing to answer when the memory lacks the fact.

## v0.9.0 — 2026-07-06

- Completed the Memory Operations Protocol — all ten verbs are real: `merge` via consolidation-candidate acceptance that executes member supersessions in one audited action; `expire`/`unexpire` riding the read-path validity exclusion; and true `redact` — content expunged from memories, revisions, and event payloads through a narrowly trigger-guarded redaction mode (append-only stays the default posture; the audit skeleton and a redaction proof-trail survive; migration `20260706_0079`). All wired across MCP (`alice_memory_manage`), HTTP, and CLI with policy vocabulary (redact and consolidation-acceptance require human or admin).
- Context API v2: per-section token allocation in the budget report, five packing strategies (`balanced`/`facts_first`/`recent_first`/`contradictions_first`/`sources_first`), and deterministic depth tiers (`minimal`/`low`/`medium`/`high` — no tier performs model synthesis); tri-state include flags let tier defaults breathe; the default agent loop docs now center one context call.
- Complete export/import round-trip: export now covers all nine record types (entities, edges, revisions, provenance, and chunks were previously dropped); `alice-memory import` preserves ids and timestamps exactly, never overwrites, and is all-or-nothing.
- Published the scale envelope (`docs/benchmarks/scale/`): SQLite commits flat at 2.3ms through 100k memories after this benchmark caught and fixed a 300× O(N) idempotency scan; Postgres ~20ms commits and ~400ms recall at 100k; honest SQLite-with-embeddings boundary documented.
- Entity-extraction hygiene after a LongMemEval diagnostic: bare capitalized spans no longer default to `person` (positive evidence required), long-text repeat thresholds and confidence-ranked caps stop conversational noise flooding; extraction rule + confidence recorded per entity for future re-typing.
- LongMemEval documentation: three-run variance disclosure (≈64%, band 63.0–64.6), the disclosed negative result on entity-graph retrieval for multi-session, and a breadth ablation (49.2% multi-session at 2× context) motivating the planned aggregation mode.

- Temporal graph memory + entity resolution (Sprint D): a generic `vnext_entities` substrate with canonicalization, aliases, mention windows, and append-only relationship history (migration `20260705_0078`); deterministic entity extraction (capitalized spans, acronyms, handles, domains, repeat-thresholds, blocklist — no LLM) linking sources at capture and memories at acceptance on every acceptance path; entity-hop graph retrieval fused into RRF as a third stage with full trace honesty; a belief-evolution timeline in `alice_explain`; and two new eval suites — `entity_resolution` and `graph_hop_retrieval` — where the graph mechanism proves recall 1.0 on entity-only queries that lexical search scores 0.0 on.

### Pre-launch fixes

- Human-direct memory commits no longer require an agent identity via MCP.
- SQLite MCP server bootstraps the user row automatically (`python -m` path) with clearer integrity-error messages.
- Full-text recall falls back to OR-matching when strict AND finds nothing (the trace shows the fallback).
- CLI gains `--version`, friendly errors for sqlite URLs and bad UUIDs, and lists all six eval suites.
- Docs overhaul: pip/uvx install is the primary quickstart, the eleven-core-tool count is corrected everywhere, self-host role bootstrap SQL is documented, and PyPI metadata is completed.

## v0.8.0 — 2026-07-05

- Published Alice's first benchmark result: **64.6% on LongMemEval_s** with the official judge protocol, in the same range as the best published results in the category — full methodology, per-question evidence, and reproduction script in `docs/benchmarks/longmemeval/`.
- Real memory scopes: `project_id`, `created_by_agent_id`, and `run_id` columns on memories (backfilled from metadata, migration `20260704_0076`); scope filters through both store backends, the context compiler, and the `alice_recall`/`alice_context_pack` tools; agent API keys can bind a project scope — bound identities may narrow but never widen it, with escalations rejected and audited.
- Consolidation that actually consolidates: embedding-based near-duplicate clustering (single-linkage, bounded and logged) produces merge/dedup candidate memories through the existing review gate — model-backed merges are grounding-gated with structured refusals, the deterministic path never fabricates text, supersession is never automatic, and reinforced preferences spanning ≥3 sources/days are surfaced for review.
- Temporal slice: graph edges carry real event time (`observed_at`/`valid_from` from source timestamps, migration `20260704_0077`); supersession pointers are first-class columns with metadata backfill; both stores answer as-of edge queries; `alice_explain` returns the full supersession chain (cycle-safe, both directions); the SQLite on-ramp gains the graph substrate.

- Context packs enforce `max_tokens` with greedy budget packing and report `{token_budget, token_estimate, truncated, dropped_item_count}`; the `projects` retrieval filter is honored; contradictions and recent changes are populated from real services; the dead `historical_timeline` section is removed and pack rows are no longer duplicated across sections.
- Typed retrieval: `memory_types` filtering through both store backends and the `alice_recall`/`alice_context_pack` tools; a procedures section joins beliefs/decisions in packs; `Procedure:`/`Playbook:`/`How to` and `Happened:`/`Log:` capture rules produce procedure and episode memories.
- Staleness v1: expired facts (`valid_to < now`) are excluded from search by default; `stale` is a first-class memory status; confirmations refresh `last_confirmed_at` (idempotent replays); a daily `staleness_sweep` scheduler workflow marks expired and unconfirmed volatile memories for review — marks only, never deletes (migration `20260704_0075`).
- The agentic write protocol joins the core MCP surface: `alice_memory_commit` (policy-checked explicit writes) and `alice_memory_manage` (confirm/undo/forget) — 11 core tools, every parameter described; the Memory Operations Protocol is documented in `docs/memory-operations-protocol.md` with honest boundaries (forget is soft-delete pending redaction; merge/expire planned).
- Three memory-quality eval suites join `retrieval_quality`: `correction_suppression` (superseded/rejected memories must vanish from recall with complete audit trails), `decision_recovery`, and `provenance_explanation` — all run live on both backends, all can genuinely fail.
- LongMemEval harness under `eval/longmemeval/`: dataset fetcher (cleaned 2025-09 release), per-question isolated Alice stores running the real capture/retrieval pipeline, official generation/judge prompts ported verbatim, checkpoint/resume runner. Scored runs need a model endpoint (`ALICE_LME_*` env vars).

## v0.7.0 — 2026-07-04

- Added the zero-infrastructure SQLite on-ramp: `alice-memory mcp --data-dir ~/.alice` starts the MCP server against a local SQLite file with no Docker or Postgres — nine core tools, FTS5 full-text search (porter stemming), optional embedding-based vector search (numpy cosine), and review through `alice_memory_review`/`alice_memory_correct`. `alice-memory export` dumps memories, sources, open loops, and events as JSONL.
- In SQLite mode, `alice_resume`, `alice_recent_decisions`, `alice_memory_review`, and `alice_memory_correct` are served by vNext-native implementations (the legacy continuity engine remains Postgres-only); legacy long-tail tools report an informative error instead of crashing.
- The `retrieval_quality` eval suite accepts `sqlite:///` URLs in `ALICEBOT_EVAL_DATABASE_URL`, labels reports with the backend, and is now CI-runnable with zero services (verified: lexical recall@1 = 1.0 through the production pipeline at ~0.7 ms median per query).
- `alicebot_api.__version__` now derives from installed package metadata instead of a hardcoded string (was stale at 0.5.1).

## v0.6.0 — 2026-07-04

- Rebuilt memory retrieval as real hybrid search: Postgres full-text + pgvector (HNSW) fused with reciprocal-rank fusion, an OpenAI-compatible embedding provider seam (Ollama/LM Studio/OpenAI), write-time embedding with graceful FTS-only degradation, and contradiction sync moved out of the read path.
- Consolidated the MCP surface to 9 core tools with parameter descriptions on every schema and compact outputs; the legacy long tail (65 tools) remains behind `ALICE_MCP_LEGACY_TOOLS=1`.
- Added real agent authentication: per-agent API keys (`alice_sk_*`, hashed at rest, RLS-scoped) enforced across all vNext HTTP agent endpoints and optionally on MCP via `ALICE_AGENT_API_KEY`; payloads can no longer self-escalate `permission_profile`.
- Replaced the closed-loop vNext eval suites with an honest `retrieval_quality` benchmark that seeds a live store and can genuinely fail; reports mark suites `skipped` without a database instead of fabricating passes.
- Repositioned the project as "the continuity layer for AI agents": rewrote README/control docs, archived 43 internal process docs, and documented the `alice-memory` PyPI naming decision (`alice-core` is taken).
- Fixed alembic URL resolution so programmatically-passed database URLs win over `DATABASE_ADMIN_URL`/`DATABASE_URL` env vars (integration-test fresh databases were previously never the ones migrated when env vars were set).

## 2026-05-11

- Added the Alice vNext dogfood hardening slice: dedicated connector settings/state tables, encrypted local secret-provider fallback, connector cursor/checkpoint persistence, migration/doctor readiness checks, live `/vnext` connector configuration, browser clipper token enforcement, Telegram retry/cursor hardening, generated-output recapture prevention, and daily dogfood runbook.
- Added the Alice vNext live capture connector slice for local dogfooding: allowlisted Telegram sync, local folder/Obsidian scan and watch, browser clipper capture, Hermes/OpenClaw-style agent output ingestion, connector health telemetry, dogfooding dashboard metrics, capture-to-brief smoke validation, and review-only trust preservation.
- Prepared the Alice vNext public-preview release package for `v0.5.1-vnext-preview`.
- Promoted the vNext preview docs from release-candidate posture to tag-ready preview posture while keeping `v0.5.1` as the current stable pre-1.0 public release.
- Added vNext preview release notes and tag plan with rollback instructions.
- Completed the vNext public release checklist with current verification evidence.
- Realigned control docs from stale "Sprint 1 active" wording to the completed Sprint 1-12 preview surface and the active vNext release gate.
- Verified the vNext Postgres-backed CLI/API/MCP smoke path, full unit suite, web test/lint/build gates, control-doc truth check, eval harness, Git diff whitespace check, and post-merge GitHub Security Scans.

## 2026-04-16

- Closed out Phase 14 after shipping all five planned sprints:
  - `P14-S1` provider abstraction cleanup + OpenAI-compatible adapter
  - `P14-S2` Ollama + llama.cpp + vLLM adapters
  - `P14-S3` model packs
  - `P14-S4` reference integrations
  - `P14-S5` design partner launch
- Shipped `HF-001` to eliminate unbounded local log growth by defaulting local/Lite logging to stdout, disabling local/Lite access logs by default, and adding bounded opt-in file logging.
- Promoted the public release boundary from `v0.4.0` to `v0.5.1`.
- Added Phase 14 closeout summary and closeout packet.
- Added `v0.5.1` release checklist, tag plan, and public release runbook.
- Aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.5.1`.
- Realigned canonical quickstart, MCP, and integration docs to the shipped Phase 14 + `HF-001` baseline.

## 2026-04-15

- Closed out Phase 13 after shipping all three planned sprints:
  - `P13-S1` one-call continuity
  - `P13-S2` Alice Lite
  - `P13-S3` memory hygiene and conversation health
- Promoted the public release boundary from `v0.3.2` to `v0.4.0`.
- Added Phase 13 closeout summary and closeout packet.
- Added `v0.4.0` release checklist, tag plan, and public release runbook.
- Aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.4.0`.
- Realigned current quickstart and integration docs to the shipped Phase 13 baseline.

## 2026-04-14

- Closed out Phase 12 after shipping all five planned sprints:
  - `P12-S1` hybrid retrieval + reranking
  - `P12-S2` automated memory operations
  - `P12-S3` contradiction detection + trust calibration
  - `P12-S4` public eval harness
  - `P12-S5` task-adaptive briefing
- Added Phase 12 closeout summary and closeout packet.
- Updated the documented release target from `v0.2.0` to `v0.3.2` for the completed Phase 12 boundary.
- Aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.3.2`.
- Added `v0.3.2` release checklist, tag plan, and public release runbook.
- Kept the published release truth explicit: the latest published tag remains `v0.2.0` until `v0.3.2` is cut.

- Prepared `R1` release-readiness package for `v0.2.0` as a pre-1.0 public release boundary.
- Added `v0.2.0` release checklist, tag plan, and public release runbook.
- Realigned launch-facing docs to shipped scope through Phase 11 and Bridge `B1` through `B4`.
- Recorded release-gate evidence in `docs/archive/process/BUILD_REPORT.md` and `docs/archive/process/REVIEW_REPORT.md` for `R1`.

## 2026-04-08

- Compacted the live control docs so `README.md`, `ROADMAP.md`, and `RULES.md` carry only current Phase 9 completion truth.
- Archived superseded Phase 9 planning and control material into local-only internal archives.
- Kept the quickstart, integration, release, runbook, and evaluation artifacts as the canonical Phase 9 launch surface.

## 2026-04-07

- Prepared the first public `v0.1.0` launch documentation set for the shipped Phase 9 wedge.
- Added onboarding, integration, release, and repo policy docs without expanding product scope.

## 2026-03-11

- Hardened the local runtime and verification path used by the public release candidate.
- Kept the launch surface aligned with deterministic local startup, migration, sample-data, and health-check flows.

# Architecture

## Scope Boundary

- **Published boundary:** `v0.10.4` is the latest published release. It is
  tagged and immutable, with artifact digests in
  `docs/release/v0.10.4-checksums.txt`.
- **Candidate boundary:** `v0.11.0` is the current unpublished candidate. Its
  default runtime is the continuity/memory layer for external AI agents, not a
  hosted product, channel platform, or bundled chat runtime.
- **Product priorities:** (1) a small, easy-to-integrate agent interface over
  MCP, HTTP, and CLI; and (2) high-quality retrieval with provenance, review,
  correction, and honest evaluation.

## Current System Overview

Alice stores durable agent memory and continuity state, retrieves the most
relevant evidence for new work, and makes every durable write reviewable and
explainable. The local runtime has one workspace bootstrap identity. PostgreSQL
is the full-stack store; SQLite is the zero-infrastructure single-agent store.
Both implement the same core memory contracts.

```text
external agent / operator
        |
        +-- MCP (11 core tools)
        +-- HTTP (agent-key authenticated core routes)
        +-- CLI (core memory and continuity commands)
        |
continuity + memory services
        |
        +-- capture / review / correction / lifecycle
        +-- recall / resume / context / explain
        +-- projects / open loops / provenance / entities / artifacts
        +-- core scheduler workflows
        |
retrieval and evidence pipeline
        |
        +-- full-text search
        +-- signed provider embeddings + pgvector when configured
        +-- fusion / ranking / traces / evals
        |
PostgreSQL + pgvector  |  SQLite
```

## Runtime Boundaries

### Agent interface

- The default MCP server exposes eleven tools: `alice_capture`, `alice_recall`,
  `alice_resume`, `alice_context_pack`, `alice_open_loops`,
  `alice_recent_decisions`, `alice_memory_review`, `alice_memory_correct`,
  `alice_explain`, `alice_memory_commit`, and `alice_memory_manage`.
- HTTP and CLI adapters expose equivalent core workflows. Agent HTTP calls use
  per-agent API keys; key records are authoritative for identity and policy.
- Remaining HTTP/CLI compatibility adapters are not part of the default product;
  a keyless local operator must explicitly mount them with
  `ALICE_LEGACY_SURFACES=1`. Retained long-tail memory MCP tools require
  `ALICE_MCP_LEGACY_TOOLS=1`; exactly the three task-brief MCP tools require both
  flags. Key-bound MCP remains core-only.

### Continuity and memory core

- Typed memories, decisions, open loops, resumption briefs, revisions, review
  labels, corrections, supersession, contradictions, trust signals, and memory
  operations share one canonical lifecycle model.
- Sources, source chunks, provenance links, generated artifacts, artifact
  ratings, events, project scope, and agent identities preserve evidence around
  that lifecycle.
- Human review is the trust boundary. Agent and scheduler proposals cannot
  silently become trusted memory.

### Retrieval and quality

- PostgreSQL retrieval fuses full-text search and pgvector 0.8+ vector search
  through reciprocal-rank fusion. SQLite provides the documented local search
  path and shares scope, lifecycle, and trust admission rules.
- Embeddings come from a configured OpenAI-compatible endpoint. With no usable
  embedding endpoint, retrieval degrades explicitly to full-text only and says
  so in its trace.
- Retrieval runs, candidates, traces, public eval cases/results, and benchmark
  receipts make quality claims inspectable. A historical 79.4% result is not a
  substitute for repeated measurements on the current candidate.

### Provider support

- Provider configuration, secret references, capability discovery, and the
  invocation boundary remain adjacent because the core needs real embeddings
  and optional model-backed memory operations.
- Provider-specific behavior may change capabilities, latency, or error
  handling, but may not fork memory, provenance, review, or trust semantics.
- Chat-only endpoints and model-pack policy are not part of the current
  provider boundary.

### Scheduler and connectors

- Core scheduler workflows cover memory lifecycle, synthesis, and maintenance;
  they use durable idempotency and project/user scope.
- Local source connectors ingest explicit text or files. PDF/DOCX text,
  screenshot text, and voice transcripts must already have been extracted by an
  external tool. Alice does not execute OCR or transcription.
- Gmail and Calendar compatibility adapters are unmounted by default behind
  `ALICE_LEGACY_SURFACES=1`; they use manual operator credentials and do not
  provide managed OAuth or automatic polling.

### Web review console

- The maintained web pages are the review console and its memory, continuity,
  vNext, trace, entity, and artifact views.
- The web app is an operator trust surface, not a hosted control plane or a
  consumer knowledge-management application.

## Persistence

### Active core records

- memories, revisions, review labels, operations, and embeddings;
- continuity capture/correction events, continuity objects, and open loops;
- sources, chunks, provenance, artifacts, ratings, and event log;
- projects, project scope, agent identities/keys, entities, and entity edges;
- retrieval/eval runs and candidates; and
- provider/embedding configuration needed by surviving core workflows.

PostgreSQL and SQLite receive parity tests whenever a store-level core contract
changes. Project scope is authoritative, and reads must apply scope and lifecycle
admission before bounded limits.

### Historical schema

Alembic migrations are immutable history. Tables for removed features may remain
after an upgrade, but their services do not mount or write them by default. The
periphery cut does not rewrite or delete historical migrations and does not use a
destructive table-drop migration.

## Core Flows

### Capture and review

1. An explicit source, agent proposal, or operator command enters through a core
   adapter.
2. Alice preserves source evidence and creates a candidate or policy-governed
   commit outcome.
3. Review can accept, edit, reject, correct, supersede, forget, or redact under
   the documented lifecycle rules.
4. Revisions and events preserve the admissible explanation chain.

### Recall and resume

1. Scope, status, sensitivity, time, person, and project constraints are
   normalized.
2. Full-text and optional signed-vector candidates are retrieved and admitted
   before bounded limits.
3. Fusion/ranking selects evidence while traces record which stages ran.
4. Recall, context packs, and resumption briefs return bounded evidence with
   provenance and explicit degradation notes.

### Agentic writes

1. The caller's key/profile and requested operation enter policy evaluation.
2. The outcome is commit, confirmation-required, review-required, or reject.
3. Every accepted durable mutation records provenance and lifecycle evidence.
4. Retries use stable idempotency identities and cannot silently duplicate a
   durable side effect.

## Removed Legacy Surfaces

The v0.11 periphery cut removes these active product surfaces. Their history is
available from the immutable v0.10.4 tag and release artifacts; they are not
roadmap commitments.

- Telegram transport, polling, delivery, notification, and channel APIs. The
  allowlist-aware import of an operator-supplied raw update remains a source-
  ingestion adapter, not a channel runtime.
- Hosted administration, rollout/design-partner, preferences, rate-limit,
  telemetry, authentication/session, device, and multi-workspace control-plane
  APIs. The single local workspace bootstrap remains an internal core utility.
- Chief-of-staff and bundled chat pages/services.
- Model-pack catalog and workspace binding APIs.
- The public OpenAI-compatible `/v0/responses` chat endpoint. Low-level response
  generation/jobs and provider proxy machinery remain internal dependencies of
  retained `/v1/runtime/invoke` and are not a public chat product.
- Legacy MCP and CLI commands whose backing service was removed.

Tasks, approvals, executions, Gmail, and Calendar are a separate temporary
compatibility category: unmounted by default, explicitly enabled only through
`ALICE_LEGACY_SURFACES=1`, and scheduled for removal before `1.0` unless real
usage justifies a separately reviewed boundary.

## Testing Strategy

- Fail-on-old inventory tests cover HTTP, MCP, CLI, scheduler, web, PostgreSQL,
  and SQLite surface disposition.
- Default-mode tests prove removed and compatibility routes/tools are absent;
  explicit compatibility-mode tests prove only the documented surviving subset
  mounts.
- Store contracts run with PostgreSQL and SQLite parity where applicable.
- OpenAPI closure, phantom-key rejection, route counts, full Python/web
  coverage, static checks, reproducible packages, installed-artifact smokes,
  semantic evidence, and independent review remain release gates.
- Historical migration tests stay even when the product surface that created a
  table has been removed.

## Current Architectural Posture

- `v0.10.4` remains the latest published release; later candidate changes are
  not part of its immutable artifacts.
- `v0.11.0` is an unpublished candidate that reconciles runtime and product
  identity around the agent interface plus retrieval/memory quality.
- The default deployment is local-first and single-workspace. A future hosted
  offering is a clean-sheet roadmap decision, not dormant product code.
- Release and review evidence for prior repair batches lives under
  `docs/handoff/`; it does not constrain legitimate future production trees or
  approve them automatically.

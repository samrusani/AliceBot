# Architecture

## System Overview

Alice is a local-first continuity system built around durable events, typed continuity objects, correction-aware retrieval, and deterministic recall/resumption compilation.

Phase 9 packaging did not redesign core semantics. It exposed already-shipped seams through a public-safe contract:

- `P9-S33`: local runtime and public package boundary
- `P9-S34`: deterministic CLI continuity contract
- `P9-S35`: deterministic MCP transport with a narrow tool surface
- `P9-S36`: OpenClaw import adapter path
- `P9-S37`: Markdown + ChatGPT importers and reproducible evaluation harness
- `P9-S38`: launch docs and release assets grounded in those shipped paths

## Technical Stack

- Backend: Python + FastAPI
- Web shell: Next.js + React
- Data store: Postgres (`pgvector` enabled)
- Local infra: Docker Compose, Redis, MinIO
- Test stack: pytest + Vitest
- Public package metadata: `pyproject.toml` (`alice-core` version `0.1.0`)

## Runtime Layers

1. Continuity capture and revision/event persistence
2. Recall and resumption compilation layer
3. Trust and memory-quality posture
4. CLI and MCP transport surface
5. Import adapters with deterministic provenance/dedupe
6. Evaluation harness and evidence outputs

## Public Interface Boundaries

### CLI (`P9-S34`)

- entrypoints: `python -m alicebot_api` and optional `alicebot`
- commands: `status`, `capture`, `recall`, `resume`, `open-loops`, `review *`
- output posture: deterministic formatting with provenance snippets

### MCP (`P9-S35`)

- entrypoints: `python -m alicebot_api.mcp_server` and optional `alicebot-mcp`
- intentionally narrow tools:
  - `alice_capture`
  - `alice_recall`
  - `alice_resume`
  - `alice_open_loops`
  - `alice_recent_decisions`
  - `alice_recent_changes`
  - `alice_memory_review`
  - `alice_memory_correct`
  - `alice_context_pack`

### Importers (`P9-S36` / `P9-S37`)

- `openclaw_import`
- `markdown_import`
- `chatgpt_import`

All importers keep source-specific provenance fields and deterministic dedupe keys.

## Core Data Objects

- continuity capture events
- typed continuity objects
- correction events and revisions
- open loops and brief-ready summaries
- import provenance with explicit `source_kind`

## Security and Governance Posture

- Postgres remains the system of record.
- User-owned tables remain RLS-governed.
- Append-only event/revision semantics are preserved.
- Public surfaces do not bypass trust/provenance discipline.
- Consequential actions remain approval-bounded.

## Local Deployment Model

Canonical startup path:

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
./scripts/api_dev.sh
```

Health check:

```bash
curl -sS http://127.0.0.1:8000/healthz
```

## Evidence and Test Surface

Required verification commands for launch docs and release assets:

```bash
./.venv/bin/python -m pytest tests/unit tests/integration
pnpm --dir apps/web test
./scripts/run_phase9_eval.sh --report-path eval/reports/phase9_eval_latest.json
```

Evidence artifacts:

- `eval/baselines/phase9_s37_baseline.json`
- `eval/reports/phase9_eval_latest.json`

## Architecture Constraints

- Preserve shipped P5/P6/P7/P8 semantics.
- Do not expand MCP tool surface in launch sprint.
- Do not add importer families beyond shipped OpenClaw/Markdown/ChatGPT paths.
- Keep launch docs aligned to real command paths and committed evidence.

## Legacy Compatibility Marker

Documentation lineage remains continuous through Phase 3 Sprint 9.

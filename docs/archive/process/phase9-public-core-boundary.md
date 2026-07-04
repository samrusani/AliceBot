# Phase 9 Public Core Boundary

## Purpose

This document defines what Phase 9 should expose publicly versus what should remain internal or non-launch-critical during the first public release.

## Public Core Objective

Expose the minimum stable surface needed to make Alice usable as:

- a local memory and continuity engine
- a CLI continuity tool
- an MCP-backed memory layer for external assistants

## Public Release Surface

### 1. Alice Core

Public-safe core functionality should include:

- continuity capture
- recall
- resumption briefs
- open-loop retrieval
- correction-aware memory review
- trust-calibrated retrieval posture

### 2. Alice CLI

Public CLI should expose:

- `alice import`
- `alice capture`
- `alice recall`
- `alice resume`
- `alice open-loops`
- `alice review-memory`
- `alice correct-memory`
- `alice status`

### 3. Alice MCP Server

Public MCP surface should stay intentionally small.

Recommended initial tools:

- `alice_capture`
- `alice_recall`
- `alice_resume`
- `alice_open_loops`
- `alice_recent_decisions`
- `alice_recent_changes`
- `alice_memory_review`
- `alice_memory_correct`
- `alice_context_pack`

### 4. Alice Importers

Public import support should focus on fast adoption:

- markdown folder import
- ChatGPT export import
- Claude export import
- CSV task/open-loop import
- OpenClaw import

## Public Runtime Assumptions

Preferred runtime:

- Postgres
- pgvector

Optional fallback:

- SQLite only if it can be supported cleanly without compromising core semantics

The first public release should prioritize one reliable documented local startup path over multiple partially supported deployment modes.

For `P9-S33`, the canonical path is:

1. `docker compose up -d`
2. `./scripts/migrate.sh`
3. `./scripts/load_sample_data.sh`
4. `./scripts/api_dev.sh`

## Public Repo Shape

Recommended public package layout:

```text
alice/
├─ apps/
│  ├─ mcp-server/
│  └─ cli/
├─ packages/
│  ├─ alice-core/
│  ├─ alice-importers/
│  ├─ alice-openclaw/
│  └─ alice-sdk-python/
├─ docs/
│  ├─ quickstart/
│  ├─ architecture/
│  ├─ integrations/
│  ├─ mcp/
│  └─ examples/
├─ eval/
├─ examples/
├─ docker/
├─ scripts/
├─ fixtures/
└─ README.md
```

This should be treated as a public packaging target, not necessarily an immediate full repo rewrite in one sprint.

## Public-Safe Guarantees

Alice public core should guarantee:

- deterministic recall/resumption behavior
- provenance-backed outputs
- correction-aware improvement
- open-loop visibility
- documented install path
- stable local-first operation

## Keep Internal Or Defer

Do not treat these as Phase 9 launch blockers:

- Telegram or WhatsApp channels
- browser automation
- broad connector write actions
- hosted SaaS
- deep vertical workflows
- broad agent-platform abstraction

## Public Documentation Priorities

Public docs must cover:

- what Alice is
- why it exists
- 10-minute quickstart
- CLI examples
- MCP setup
- OpenClaw integration
- architecture overview
- evaluation harness

## OSS Boundary Questions

Phase 9 needs explicit decisions on:

- license
- what parts are public-safe
- whether any internal tooling or ops scripts remain private
- whether public examples include full datasets or sanitized fixtures only

These should be captured as ADRs rather than left implicit in launch docs.

Current `P9-S33` note:

- package boundary, runtime baseline, and MCP tool-surface boundaries are ADR-backed
- license selection is explicitly deferred and tracked in sprint evidence

## Launch Definition

Phase 9 public launch is good enough when an external technical user can:

- install Alice locally
- import data
- use CLI recall/resume/open-loop flows
- connect one MCP client
- observe that corrections change future retrieval
- complete the flow from public docs without direct founder support

# Product Brief

## Product Summary

Alice is a local-first memory and continuity layer for AI agents. It persists durable context, compiles useful working context on demand, and improves future retrieval when users apply corrections.

## Problem

General-purpose assistants and agent stacks still lose long-horizon continuity. They forget decisions, drop open loops, and require repeated context restatement.

## Target Users

- Technical individual users who want a local continuity engine.
- Developers and agent builders who need durable recall, resumption, and correction-aware memory.
- Users with existing workspace/chat/note exports they want to import into one governed continuity store.

## Core Value Proposition

- Durable memory and continuity across sessions.
- Deterministic recall and resumption output.
- Open-loop visibility (blocked, waiting, next action).
- Correction-aware retrieval that updates future output.
- Interoperability via CLI and MCP with a deliberately narrow contract.

## Phase 9 Delivered Surface

`P9-S33` through `P9-S37` are shipped and form the v0.1 product wedge:

- public-safe local runtime boundary
- deterministic local CLI continuity commands
- deterministic MCP tool transport
- OpenClaw import path
- Markdown + ChatGPT import paths
- reproducible local evaluation harness and baseline evidence

`P9-S38` delivery scope is launch packaging only:

- quickstart and integration docs
- architecture/repo docs synced to shipped behavior
- release checklist, runbook, and version-tag assets

## Non-Goals (v0.1)

- hosted SaaS dependency for initial launch
- broad connector write actions
- Telegram/WhatsApp channel expansion
- deep browser automation
- enterprise platform expansion in v0.1

## Key User Journeys

1. Install Alice locally and get a first useful recall result in under 30 minutes.
2. Load deterministic sample data and generate a resumption brief.
3. Import external context from OpenClaw, Markdown, or ChatGPT export.
4. Run correction flow and verify future retrieval follows corrected truth.

## Constraints

- Local-first deployment for v0.1.
- Deterministic, provenance-backed outputs.
- Corrections must influence future behavior.
- Public docs must only claim shipped command paths and evidence.
- Consequential execution remains approval-bounded.

## Success Criteria

- External technical users can follow docs from install to first useful result without handholding.
- Shipped CLI/MCP/importer paths are reproducible from documented commands.
- Evaluation evidence is reproducible from `./scripts/run_phase9_eval.sh`.
- Release assets are sufficient to cut v0.1 without reopening product semantics.

## Product Non-Negotiables

- Durable context must come from governed storage, not transcript stuffing.
- Corrections must improve later retrieval/resumption.
- Provenance must remain visible.
- Public launch must not depend on unsafe autonomy or broad connector side effects.
- Alice must remain useful as a standalone local continuity engine.

## Legacy Compatibility Marker

This repo retains the canonical v1 release-readiness validation scenario for historical quality traceability.

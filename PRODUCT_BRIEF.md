# Product Brief

## Product Summary

Alice is a local-first memory and continuity layer for AI agents. It preserves durable context, compiles useful working context on demand, and improves future recall when corrected.

## Problem

General-purpose assistants and agent stacks are still poor at long-horizon continuity. They forget decisions, lose open loops, require repeated context restatement, and often treat correction as transient instead of durable.

## Target Users

- Technical individual users who want a local memory and continuity engine.
- Developers and agent builders who need better recall, resumption, and correction-aware memory.
- Users with existing notes, chat exports, or agent workspaces they want to import into a durable continuity layer.

## Core Value Proposition

- Durable memory and continuity across sessions.
- Deterministic recall and resumption briefs.
- Open-loop visibility for blocked, waiting, and next-action states.
- Correction-aware retrieval that improves after edits.
- Interoperability through CLI, MCP, and external adapters instead of closed-product lock-in.

## Phase 9 Scope Staging

### `P9-S33` (current sprint objective)

- public-safe `alice-core` package boundary
- one canonical local startup flow
- deterministic sample-data load path
- documented proof for one recall call and one resumption call from public docs

### Follow-on (`P9-S34` to `P9-S38`)

- CLI commands
- MCP server
- external adapter and broader importer set
- evaluation harness expansion and launch assets

## Non-Goals

- Telegram or WhatsApp channels
- hosted SaaS as a launch dependency
- vertical-agent expansion
- deep browser automation
- autonomous external side effects without approval
- broad connector write actions
- enterprise platform expansion in v0.1

## Key User Journeys

1. Install Alice locally and run a first recall query in under 30 minutes.
2. Load sample data and generate a useful resumption brief.
3. Correct a memory once and verify future retrieval uses the new truth.
4. Inspect open loops and recent decisions without re-reading raw history.

## Constraints

- Local-first deployment for v0.1.
- Deterministic, provenance-backed outputs.
- Correction must update future behavior.
- Consequential execution remains approval-bounded.
- Public interop surface must stay small and stable before broadening.

## Success Criteria

- A technical user can install Alice locally in under 30 minutes from docs.
- Sample data can be loaded from one deterministic command path.
- One recall call and one resumption call work end to end from documented setup.
- Public boundaries are explicit enough that CLI and MCP layers can build without reopening package ambiguity.

## Product Non-Negotiables

- Durable context must come from governed storage, not transcript stuffing.
- Corrections must improve future output.
- Provenance must remain visible for recall and resumption outputs.
- Public launch must not depend on unsafe autonomy or broad connector side effects.
- Alice should remain useful as a standalone local continuity engine even when no external agent is attached.

## Legacy Compatibility Marker

This repo retains the canonical v1 release-readiness validation scenario for historical quality traceability.

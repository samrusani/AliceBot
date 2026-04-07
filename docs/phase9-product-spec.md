# Phase 9 Product Spec

## Title

Phase 9: Alice Public Core and Agent Interop

## Executive Summary

Phases 4 through 8 built Alice into a release-qualified, trust-calibrated, continuity-first chief-of-staff system.

Phase 9 should turn that internal product into a public, installable memory and continuity engine that other agents and technical users can adopt quickly.

The Phase 9 wedge is not "another full assistant."
It is:

- a memory and continuity layer
- installable locally
- usable directly through CLI
- callable through MCP
- interoperable with external agent stacks such as OpenClaw

The product should let a technical user install Alice, import memory/context, connect it to an external assistant, ask recall questions, generate a resumption brief, inspect open loops, and verify that corrections improve future behavior.

## Product Thesis

Alice should become the memory and continuity layer for AI agents.

It should provide:

- durable memory
- better context loading
- resumption briefs
- open-loop continuity
- correction-aware recall

The key move in Phase 9 is not feature sprawl. It is packaging, interoperability, and public usability.

## Phase Goal

Ship Alice as a public, installable core that works:

- standalone
- through CLI
- through MCP
- with at least one concrete external agent integration

## Success Condition

A technical user can, in under 30 minutes:

- install Alice locally
- load sample or imported data
- run capture, recall, resume, and open-loop flows
- connect an external assistant via MCP
- observe deterministic correction-aware behavior

## Non-Goals

- Telegram or WhatsApp channels
- vertical-agent expansion
- enterprise multi-tenant platform expansion
- deep browser automation
- hosted SaaS as a launch dependency
- broad connector write actions
- "our agents only" ecosystem lock-in

## Public Product Wedge

### Positioning

Alice is the memory and continuity layer for AI agents.

### Public Surfaces

Phase 9 should publish four things:

1. Alice Core
2. Alice MCP Server
3. Alice CLI and Python SDK
4. OpenClaw adapter and examples

## Target Users

- technical solo users
- developers already experimenting with local agents
- users with existing notes or memory stores to import
- agent builders who need better recall, resumption, and correction-aware memory

## Core Value Proposition

- Local-first installable memory and continuity system
- Correction-aware recall and resumption
- Open-loop visibility
- Deterministic, provenance-backed outputs
- Agent interoperability through MCP instead of closed-product lock-in

## Public v0.1 Product Contract

Alice v0.1 should help users do five things:

1. Capture
2. Recall
3. Resume
4. Correct
5. Track open loops

That is enough for launch.

## `P9-S33` Public-Core Baseline

This sprint establishes the packaging/runtime baseline before CLI and MCP implementation:

- package name: `alice-core`
- canonical startup: `docker compose up -d` -> `./scripts/migrate.sh` -> `./scripts/load_sample_data.sh` -> `./scripts/api_dev.sh`
- deterministic fixture: `fixtures/public_sample_data/continuity_v1.json`
- proof path: one recall call and one resumption call from public docs

## Must-Ship v0.1 Surface

- local install
- capture
- recall
- resume
- open loops
- correction
- MCP server
- OpenClaw adapter
- markdown import
- docs and demos

## Nice-To-Have v0.1 Surface

- ChatGPT importer
- Claude importer
- lightweight public web review page
- packaged binary installer

## Do Not Block Launch On

- Telegram
- WhatsApp
- browser automation
- shopping or calendar write actions
- hosted SaaS
- deep vertical workflows

## Core User Journeys

1. Install Alice locally and run a first recall query.
2. Import an existing workspace or memory source and immediately generate a resumption brief.
3. Connect a local assistant via MCP and call Alice tools for recall and continuity support.
4. Correct a memory once and verify later retrieval changes deterministically.
5. Inspect open loops and recent decisions without re-reading raw history.

## Required Product Surfaces

### Alice Core

The public-safe continuity and memory engine with stable install and documented runtime assumptions.

### Alice CLI

Terminal-first interface for:

- import
- capture
- recall
- resume
- open loops
- review/correct memory
- status

### Alice MCP Server

Stable small tool surface for external assistants.

### External Integration Adapter

At least one first-class external agent integration proving Alice is agent-agnostic.

## Core Product Principles

1. Public packaging must not compromise trust or determinism.
2. Interop must be narrow and stable before it becomes broad.
3. Docs are product surface in this phase, not support material.
4. Launch should prove usefulness, not breadth.
5. Import, correction, and recall quality matter more than ecosystem count.

## Metrics

### Product Metrics

- time to first useful result
- recall precision
- resumption usefulness
- correction success rate
- number of imported workspaces
- number of MCP-connected clients

### Technical Metrics

- install success rate
- import failure rate
- duplicate memory rate
- resumption latency
- MCP tool failure rate
- database migration reliability

### Launch Metrics

- quickstart completion rate
- docs completion rate
- setup-vs-product issue ratio
- community integrations

## Delivery Constraints

- reuse shipped P5/P6/P7/P8 capabilities rather than rebuilding continuity semantics
- preserve deterministic memory, trust, and provenance behavior
- do not widen into unsafe autonomous execution to chase launch novelty
- keep Phase 9 interop contracts small and stable

## Acceptance Criteria

- Alice can be installed locally from clean docs
- a sample dataset can be loaded
- CLI capture, recall, resume, open-loop, and correction flows work against real data
- MCP tools work for recall and resume from at least one compatible client
- at least one external integration proves Alice is usable as an agent memory layer
- importers and evaluation harness provide public proof that correction-aware continuity is useful

## Phase Exit Definition

Phase 9 is complete when Alice is no longer only an internal system.

It must be:

- installable
- documented
- interoperable
- demonstrable
- useful in under 30 minutes for a technical user

At phase exit, Alice should have a credible public v0.1 story as a memory and continuity engine for agents.

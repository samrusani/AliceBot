# Phase 9 Sprint 33-38 Plan

## Summary

Phase 9 should convert the shipped internal Alice system into a public, installable core with CLI, MCP interoperability, importers, evaluation harness, and launch-ready docs.

Sprint IDs in this document are Phase 9-local (`P9-S33` to `P9-S38`) to avoid ambiguity with completed Phase 4, Phase 5, Phase 6, Phase 7, and Phase 8 sprint numbering.

## Phase Objective

Ship Alice as a public memory and continuity engine that technical users can install and connect to external agents quickly.

## Sprint 33 (P9-S33)

### Title

Public Core Packaging

### Objective

Turn the current internal system into a public-safe, installable core with one documented local startup path.

### Scope

- public package boundary
- public-safe repo structure cleanup
- default config templates
- sample `.env` path
- Docker/local startup path
- sample dataset
- first public README skeleton
- OSS boundary and license decision

### Deliverables

- `alice-core` package boundary definition
- public runtime assumptions
- local install path
- clean repo map for public use
- sample seed dataset at `fixtures/public_sample_data/continuity_v1.json`
- deterministic sample load command: `./scripts/load_sample_data.sh`

### Acceptance Criteria

- fresh machine install works from docs
- Alice boots locally through one documented flow
- sample data can be loaded
- one recall query works end to end
- one resumption brief works end to end

### Out Of Scope

- CLI polish beyond bootstrapping
- MCP interoperability
- broad importer set

## Sprint 34 (P9-S34)

### Title

CLI and Continuity UX

### Objective

Make Alice useful without requiring the internal operator shell.

### Scope

- capture command
- recall command
- resume command
- open-loops command
- memory review/correction commands
- status command
- terminal-friendly deterministic output

### Deliverables

- CLI command set
- terminal formatting for recall and resume
- provenance snippets in terminal output
- correction flows for confirm/edit/delete/supersede

### Acceptance Criteria

- commands operate against real local data
- resume output includes:
  - recent decisions
  - active open loops
  - blockers
  - next suggested action
- correction updates later recall deterministically

### Out Of Scope

- MCP server
- external integrations

## Sprint 35 (P9-S35)

### Title

MCP Server

### Objective

Make Alice usable immediately by external assistants through a stable small tool surface.

### Scope

- MCP tool schemas
- deterministic serialization
- local auth model for MCP use
- context pack outputs
- compatibility examples

### Deliverables

- stable tool set such as:
  - `alice_capture`
  - `alice_recall`
  - `alice_resume`
  - `alice_open_loops`
  - `alice_recent_decisions`
  - `alice_recent_changes`
  - `alice_memory_review`
  - `alice_memory_correct`
  - `alice_context_pack`
- config examples for compatible clients
- local interoperability demo

### Acceptance Criteria

- one MCP client can call recall successfully
- one MCP client can call resume successfully
- correction via MCP changes later retrieval behavior
- tool contracts remain stable across runs

### Out Of Scope

- broad tool surface expansion
- remote hosted auth systems

## Sprint 36 (P9-S36)

### Title

OpenClaw Adapter

### Objective

Prove Alice is agent-agnostic and materially improves an existing agent stack.

### Scope

- file-based import path for OpenClaw durable memory/workspace data
- MCP augmentation mode for external use
- import mapping and dedupe rules
- provenance tagging for imported material

### Deliverables

- `alice-openclaw` adapter package
- import command for OpenClaw workspace
- imported provenance tagging
- before/after integration demo

### Acceptance Criteria

- a sample or real OpenClaw workspace can be imported
- imported memory is queryable through Alice recall
- imported workspace produces useful resumption briefs
- external agent can consume Alice via MCP augmentation

### Out Of Scope

- generic platform SDK
- many external integrations at once

## Sprint 37 (P9-S37)

### Title

Importers and Evaluation Harness

### Objective

Make the public product sticky fast and prove it is better, not just broader.

### Scope

- importers
- benchmark fixtures
- local evaluation harness
- baseline report generation

### Deliverables

- at least three production-usable importers
- benchmark flows for:
  - recall precision
  - resumption usefulness
  - correction effectiveness
  - open-loop retrieval quality
- sample eval report

### Acceptance Criteria

- benchmark script runs locally
- sample eval report can be generated from repo
- correction prevents repeated outdated recall in test cases
- importer success and duplicate-memory posture are measurable

### Out Of Scope

- launch narrative polish
- broad UI work

## Sprint 38 (P9-S38)

### Title

Docs, Launch Assets, and Public Release

### Objective

Make the repo feel launch-ready for external technical users.

### Scope

- polished README
- quickstart docs
- architecture overview
- integration docs
- launch assets
- contribution and security docs
- first public version tag

### Deliverables

- public quickstart flow
- architecture and integration docs
- comparison positioning page
- screenshots and demo media
- launch checklist and runbook
- `v0.1` release tag

### Acceptance Criteria

- external tester can complete quickstart without handholding
- public repo passes install, test, and demo path
- launch materials match the actual product wedge
- first public release is cut consistently

### Out Of Scope

- hosted SaaS launch
- post-v0.1 vertical expansion

## Cross-Sprint Requirements

- preserve shipped continuity, trust, and chief-of-staff semantics
- keep public interop surfaces narrow and stable
- keep docs synchronized with actual install/runtime behavior
- avoid turning launch work into platform sprawl

## Cross-Sprint Metrics

- install success rate
- time to first useful result
- recall precision
- resumption usefulness
- correction uptake rate
- import success rate
- duplicate memory rate
- MCP tool failure rate
- quickstart completion rate

## Control Tower Notes

- treat this phase as packaging and interoperability, not product reinvention
- public docs are part of the shipped product surface in this phase
- prefer one clear artifact per sprint:
  - Sprint 33: public core checklist
  - Sprint 34: CLI demo
  - Sprint 35: MCP quickstart
  - Sprint 36: OpenClaw integration demo
  - Sprint 37: baseline eval report
  - Sprint 38: public release checklist
- do not reopen P5/P6/P7/P8 semantics while executing Phase 9

## Definition Of Success

Phase 9 succeeds if Alice becomes:

- installable
- understandable
- interoperable
- evaluable
- launchable

for external technical users in a short, documented flow.

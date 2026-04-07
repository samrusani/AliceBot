# Roadmap

## Current State

- Phase 4 is complete as the release-control and qualification baseline.
- Phase 5 is complete as the daily continuity baseline.
- Phase 6 is complete as the memory trust-calibration baseline.
- Phase 7 is complete as the chief-of-staff guidance baseline.
- Phase 8 is complete as the operational chief-of-staff baseline.
- The current milestone is Phase 9: Alice Public Core and Agent Interop.

## Current Milestone

### Phase 9

Ship Alice as a public, installable memory and continuity engine that technical users and external assistants can adopt quickly.

Success condition:

- install locally
- import existing context
- run capture/recall/resume/open-loop flows
- connect via MCP
- verify correction-aware improvement

## Next Milestones

### P9-S33: Public Core Packaging (shipped baseline)

- public-safe package boundary
- documented local startup path
- sample dataset (`fixtures/public_sample_data/continuity_v1.json`)
- initial public README and OSS boundary decisions

### P9-S34: CLI and Continuity UX (shipped baseline)

- packaged local CLI entrypoint (`python -m alicebot_api`, optional `alicebot`)
- terminal commands for capture, recall, resume, open loops, review, correction, and status
- deterministic terminal formatting with provenance snippets

### P9-S35: MCP Server (shipped baseline)

- small stable MCP tool surface
- local interop examples for compatible clients
- deterministic tool contracts

### P9-S36: OpenClaw Adapter (shipped baseline)

- import path for OpenClaw durable memory/workspace data
- Alice MCP augmentation mode for OpenClaw-style workflows

### P9-S37: Importers and Evaluation Harness (current seam)

- at least three production-usable importers
- local benchmark and baseline report generation

### P9-S38: Docs, Launch Assets, and Public Release

- public quickstart
- integration docs
- launch checklist
- first public version tag

## Dependencies

- Phase 9 packaging must preserve shipped P5/P6/P7/P8 semantics.
- CLI and MCP should both build on the same public core boundary.
- Importers should reuse current continuity and correction semantics.
- Launch docs should reflect the actual install/runtime path, not intended future structure.

## Blockers and Risks

- Packaging boundaries may require repo cleanup before public release.
- Import quality and dedupe behavior can become the main public trust risk.
- MCP surface must stay narrow to avoid unstable contracts.
- Launch quality depends heavily on quickstart reliability and docs accuracy.
- OSS boundary and license decisions must be made before public release work finalizes.

## Recently Completed

- Phase 8 delivered operational chief-of-staff handoffs, routing, outcome learning, and closure quality.
- `P9-S33` delivered the public-safe `alice-core` boundary, canonical local startup path, and deterministic sample-data proof.
- `P9-S34` delivered the shipped local CLI continuity contract that `P9-S35` should mirror through MCP.
- `P9-S35` delivered the shipped local MCP contract that `P9-S36` should consume without widening.

## Legacy Compatibility Markers

Repository lineage remains continuous through Phase 3 Sprint 9.

Phase 4 Sprint 14 is the active release-control layer.

Gate ownership is canonicalized to Phase 4 runner scripts.

# Roadmap

## Current State

- Phase 4 is complete as the release-control and qualification baseline.
- Phase 5 is complete as the daily continuity baseline.
- Phase 6 is complete as the trust-calibrated memory baseline.
- Phase 7 is complete as the chief-of-staff guidance baseline.
- Phase 8 is complete as the operational chief-of-staff baseline.
- Phase 9 is the public-core and interop milestone.

## Current Milestone

### Phase 9: Alice Public Core and Agent Interop

Goal: ship Alice as an installable local continuity engine with deterministic CLI/MCP interop, importer coverage, and reproducible evaluation evidence.

Success condition:

- local install works from docs
- CLI continuity commands work deterministically
- MCP surface is stable and narrow
- shipped importer paths are reproducible
- evaluation report is generated from local fixtures

## Phase 9 Sprint Sequence

### `P9-S33` (shipped)

- public-safe package boundary
- canonical local startup path
- deterministic sample data path

### `P9-S34` (shipped)

- local CLI continuity contract
- deterministic terminal output with provenance snippets

### `P9-S35` (shipped)

- narrow MCP tool surface
- deterministic contract parity with shipped continuity behavior

### `P9-S36` (shipped)

- OpenClaw adapter/import path
- deterministic dedupe + provenance posture

### `P9-S37` (shipped)

- markdown and ChatGPT importers
- reproducible local eval harness
- baseline evidence (`eval/baselines/phase9_s37_baseline.json`)

### `P9-S38` (current delivery seam)

- polished public README and quickstart
- integration docs for CLI/MCP/importers/eval
- release checklist and runbook
- first public version tag plan/assets

## Dependencies

- Preserve shipped P5/P6/P7/P8 semantics.
- Keep CLI and MCP behavior aligned to the same core seams.
- Keep import and dedupe behavior explicit and deterministic.
- Keep launch docs constrained to shipped command paths and evidence.

## Risks

- Docs drift from runnable command paths.
- Release assets claim behavior not covered by tests/evidence.
- Launch sprint accidentally expands MCP or importer scope.
- OSS licensing/security docs remain ambiguous before tag cut.

## Recently Completed

- `P9-S33` through `P9-S37` shipped the public runtime, CLI, MCP, OpenClaw adapter, broader importer coverage, and evaluation harness.
- `P9-S38` is focused on launch packaging and public release readiness for those already-shipped seams.

## Legacy Compatibility Markers

Repository lineage remains continuous through Phase 3 Sprint 9.

Phase 4 Sprint 14 is the active release-control layer.

Gate ownership is canonicalized to Phase 4 runner scripts.

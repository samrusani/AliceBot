# Roadmap

## Current State

- Phase 4 is complete as the release-control and qualification baseline.
- Phase 5 is complete as the daily continuity baseline.
- Phase 6 is complete as the trust-calibrated memory baseline.
- Phase 7 is complete as the chief-of-staff guidance baseline.
- Phase 8 is complete as the operational chief-of-staff baseline.
- Phase 9 is complete as the public-core and interop milestone.
- No Phase 10 milestone is active yet because Phase 10 planning docs have not been added.

## Current Milestone

### No Active Build Sprint

Phase 9 is complete through `P9-S38`.

Next required control move:

- execute the Phase 9 release checklist/runbook
- add canonical Phase 10 planning docs
- activate the first non-redundant Phase 10 sprint

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

### `P9-S38` (shipped)

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
- `P9-S38` shipped launch-ready docs, quickstart, integration docs, release checklist, and public release assets for the Phase 9 wedge.

## Legacy Compatibility Markers

Repository lineage remains continuous through Phase 3 Sprint 9.

Phase 4 Sprint 14 is the active release-control layer.

Gate ownership is canonicalized to Phase 4 runner scripts.

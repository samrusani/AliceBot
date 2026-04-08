# Current State

## What Exists Today

- Phase 4 release-control and qualification seams are the trusted baseline.
- Phase 5 continuity capture/recall/resumption/review/correction/open-loop seams are shipped.
- Phase 6 trust-calibrated memory-quality and retrieval posture is shipped.
- Phase 7 chief-of-staff guidance seams are shipped.
- Phase 8 operational handoff/queue/routing/outcome-learning seams are shipped.
- Phase 9 public-core and interop seams are shipped through `P9-S37` and launch-packaged in `P9-S38`.

## Stable / Trusted Areas

- deterministic continuity and resumption behavior
- correction-aware memory behavior
- open-loop review and brief generation
- deterministic CLI/MCP transport contracts
- deterministic importer provenance + dedupe posture
- local evaluation harness and baseline evidence generation

## Incomplete / At-Risk Areas

- importer scope remains intentionally file-import-only (OpenClaw + Markdown + ChatGPT)
- hosted/remote evaluation and deployment remain out of scope
- release execution quality now depends on checklist/runbook discipline

## Current Milestone

Phase 9: Alice Public Core and Agent Interop

## Latest State Summary

`P9-S33` through `P9-S38` are now represented in repo truth:

- package/runtime boundary and canonical startup path are documented and script-backed
- deterministic CLI and MCP contracts are documented and test-backed
- shipped importer paths are documented with deterministic provenance/dedupe expectations
- quickstart and integration docs now exist for external technical users:
  - `docs/quickstart/local-setup-and-first-result.md`
  - `docs/integrations/cli.md`
  - `docs/integrations/mcp.md`
  - `docs/integrations/importers.md`
  - `docs/examples/phase9-command-walkthrough.md`
- release assets now exist for first public cut:
  - `docs/release/v0.1.0-release-checklist.md`
  - `docs/release/v0.1.0-tag-plan.md`
  - `docs/runbooks/phase9-public-release-runbook.md`
  - `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`
- evaluation evidence remains anchored to:
  - `eval/baselines/phase9_s37_baseline.json`
  - `eval/reports/phase9_eval_latest.json`

## Critical Constraints

- Preserve shipped P5/P6/P7/P8 semantics.
- Keep public interop deterministic and provenance-backed.
- Do not expand MCP tool surface or importer families during launch packaging.
- Keep public claims constrained to runnable commands and committed evidence.

## Immediate Next Move

- run release checklist and runbook end-to-end on a clean environment
- open release PR for `codex/phase9-sprint-38-launch-and-release`
- cut `v0.1.0` tag only after checklist gates pass

## Legacy Compatibility Markers

Repository lineage remains continuous through Phase 3 Sprint 9.

Active Sprint focus is Phase 4 Sprint 14.

Gate ownership is canonicalized to Phase 4 runner script names.

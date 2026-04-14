# Roadmap

## Baseline Context (Shipped, Not Roadmap Work)
- Phase 9: shipped
- Phase 10: shipped
- Phase 11: shipped
- Bridge Phase (`B1`-`B4`): shipped

These are baseline truth and not future scope.

## Active Planning Status
- Release Sprint 1 (`R1`) is the active execution sprint.
- `R1` is a release-readiness sprint for `v0.2.0`.

## Release Sprint R1: v0.2.0 Public Release Readiness
- refresh the release checklist, tag plan, and runbook for the real shipped Alice surface
- align README, changelog, and public policy docs with current shipped truth
- verify the quickstart, integration docs, and release evidence paths
- run and record release gates:
  - control-doc truth
  - unit/integration tests
  - web tests
  - Hermes provider smoke
  - Hermes MCP smoke
  - Hermes bridge one-command demo
- prepare a clean annotated-tag path for `v0.2.0` on `main`

## Sequencing Rules
- Do not add new product/runtime features during `R1`.
- Refresh release docs before cutting the tag.
- Run release gates after doc alignment and before merge approval.
- Keep the release explicitly pre-1.0.
- Treat old `v0.1.x` release docs as historical reference, not active release truth.

## Beyond v0.2.0 (Future, Not Yet Defined)
- Post-release feature planning is not active inside `R1`.
- If additional hardening is needed after `R1`, scope it as a separate sprint rather than widening the release sprint.

# ADR-001: Public Core Package Boundary

## Status

Accepted (2026-04-07)

## Context

Phase 9 packages an internal continuity and chief-of-staff substrate into a public technical product. The repo currently mixes shipped internal product surfaces, planning docs, and future public surfaces. Without an explicit package boundary, later CLI, MCP, importer, and adapter work will target unstable seams and keep reopening the same scope question.

## Decision

Define a narrow public package boundary centered on `alice-core`.

`alice-core` should own:

- continuity capture
- recall and retrieval
- resumption-brief generation
- open-loop retrieval
- correction-aware memory update paths
- trust-calibrated retrieval semantics

Keep these outside the initial public core or explicitly deferred:

- chief-of-staff UI and operator-specific workspaces
- broad autonomous execution surfaces
- channel integrations
- deep vertical workflows
- internal release-control and review tooling not required for public operation
- OSS license selection (tracked separately as deferred launch governance)

Public CLI, MCP, importers, and external adapters should depend on the documented `alice-core` boundary rather than reaching through internal app seams ad hoc.

## Consequences

Positive:

- gives Sprint 34 and Sprint 35 stable build targets
- reduces accidental platform sprawl in the first public release
- makes docs, packaging, and testing easier to align

Negative:

- may require temporary duplication or wrapper seams while the repo transitions toward cleaner packaging
- leaves some internal product features deliberately outside the first public release

## Alternatives Considered

### Expose the full current repo as the public product

Rejected for Phase 9 because it would blur internal operator surfaces with the public continuity contract and enlarge the support surface too early.

### Delay package-boundary decisions until CLI and MCP implementation

Rejected because it would create churn across multiple follow-on sprints and make interop contracts unstable.

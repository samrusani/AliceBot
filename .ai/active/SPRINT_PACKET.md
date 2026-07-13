# Sprint Packet

## Sprint

Alice v0.10.0 audit remediation and release-evidence repair.

## Status

Mandatory repair pass active on `codex/v0.10-audit-remediation`, based on
`68d6bf2`. The first independent review returned **REJECT**; its 16-item
checklist is binding and all affected matrix rows are reopened. The published
`v0.9.4` tag remains immutable. This sprint does not authorize a tag, merge,
push, GitHub release, or PyPI publication.

## Reason

A third independent audit found that several v0.9.4 remediations were partial
and that the endpoint-signature change broke eval and backfill vector
compatibility. It also confirmed substantial P2 correctness, performance,
typing, web, backup, packaging, and documentation debt. The branch is
release-blocked until the builder and an independent reviewer close the matrix
under `docs/handoff/2026-07-13-v0.10-audit-remediation/`.

## In scope

- one production-compatible signed-embedding contract for every vector writer;
- exact-SHA semantic release evidence with nonzero signed-vector candidates;
- complete people/time filters, query-vector reuse, and bulk graph/provenance reads;
- scoped, status-aware, classification-aware, atomic capture dedupe;
- fail-closed lifecycle graphs, correct lock order, confirmation auditing, and migration repair;
- truthful/cohesive/bounded-memory rollups and consolidation;
- pgvector 0.8+ installer, migration, and doctor enforcement;
- immutable single-parse backup restore and future-table rejection;
- thread-safe web drafts, independent outage degradation, SSR parallelism,
  full TypeScript, browser navigation, accessibility, coverage, and budgets;
- full first-party Python typing, portable package documentation, and active-doc truth;
- focused regression tests plus the complete release-equivalent verification set.

## Out of scope

- cybersecurity analysis beyond preserving existing controls;
- new product features unrelated to an audited finding;
- provider credentials in CI or deterministic fake evidence presented as a release result;
- publication, tagging, pushing, merging, or changing repository settings.

## Required gates

1. Focused regressions listed in `FIX_MATRIX.md` pass.
2. Python unit coverage, PostgreSQL integration, LongMemEval, backup, and scale tests pass.
3. Ruff and full first-party `mypy` pass with zero errors.
4. Web tests, lint, full TypeScript, production build, browser navigation,
   accessibility, coverage, and bundle/performance budgets pass.
5. Wheel and sdist pass metadata, Twine, portable-link, and installed-artifact smokes.
6. The no-provider eval fails closed.
7. An operator-supplied configured provider eval on the exact candidate SHA
   reports nonzero production-signed vector candidates and meets every quality target.
8. Publication accepts only an attested semantic-eval report bound to the exact SHA.
9. Control-document and release-finalization truth checks pass.
10. An independent reviewer reports no remaining blocker.

## Handoff

- `docs/handoff/2026-07-13-v0.10-audit-remediation/FIX_MATRIX.md`
- `docs/handoff/2026-07-13-v0.10-audit-remediation/BUILD_REPORT.md`
- `docs/handoff/2026-07-13-v0.10-audit-remediation/ENGINEER_HANDOFF.md`
- `docs/handoff/2026-07-13-v0.10-audit-remediation/REVIEW_REPORT.md` (reviewer-owned)

## Exit condition

The sprint is complete only when every matrix row is closed or explicitly
returned as a release blocker, all runnable gates have exact command evidence,
the configured semantic report is bound to the reviewed clean SHA, and the
independent reviewer signs off. Until then, v0.10.0 remains unpublishable.

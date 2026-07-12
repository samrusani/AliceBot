# Current State

## Snapshot

- `v0.9.2` is the latest published release: security and reliability
  hardening — project-bound agent authorization, lifecycle and upgrade
  correctness, safe local SQLite backup/restore, truthful retrieval
  contracts, patched web dependencies, packaging, and release evidence. It
  also carries the round-2..6 retrieval and memory features already recorded
  in the changelog. It is tagged and published on PyPI and GitHub.
- `v0.9.3` is the current release candidate: a security and reliability
  hotfix over v0.9.2 that fixes lifecycle state-machine defects (one central
  transition table), expire/unexpire row-locking races, a migration-0083
  identifier-reservation bug (corrective migration 0084), project-scoped
  capture persistence, and hard people/time filter pagination. No v0.9.3
  work is published yet.
- Alice is a local-first continuity layer for AI agents. Agent developers
  are the primary customer.

## What `v0.9.3` Changes

`v0.9.3` is a security and reliability hotfix over `v0.9.2`. The five P1
fixes below are complete on this hotfix branch but are not yet released; the
release ships only after the canonical gates pass on one exact clean SHA.

- **Lifecycle state-machine correctness** — lifecycle transitions are now
  driven by one central transition table, replacing the divergent per-path
  checks that allowed invalid state changes.
- **Expire/unexpire row-locking races** — expire and unexpire now take the
  correct row locks, closing the concurrent-update races that could corrupt
  lifecycle state.
- **Migration-0083 identifier-reservation bug** — corrective migration 0084
  repairs the identifier reservation that migration 0083 got wrong.
- **Project-scoped capture persistence** — capture persists within the
  correct project scope instead of leaking across projects.
- **Hard people/time filter pagination** — the people and time filters now
  paginate as hard filters, so paged results stay within the requested
  bounds.

## Published Evidence

- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. Per-question rows and protocol receipts are committed under
  `docs/benchmarks/longmemeval/`.
- The result has not been replicated and is not a `v0.9.3` measurement.
- The scale envelope is a single-machine synthetic benchmark, not a
  concurrent load test.

## Release Boundary

`v0.9.2` shipped only after the canonical release check passed on one exact
clean source SHA and the reviewer reported no remaining release blocker. The
same boundary governs `v0.9.3`: it is releasable only when the canonical
release check passes on its exact clean source SHA and the reviewer reports no
remaining release blocker.

## Product Boundaries

- Local-first, single-user, self-hosted.
- No hosted service or SLA.
- No managed OAuth connectors.
- No silent capture from arbitrary conversations.
- Durable agent writes remain policy-checked and reviewable.

# Current State

## Snapshot

- `v0.9.2` is the latest published release: security and reliability
  hardening — project-bound agent authorization, lifecycle and upgrade
  correctness, safe local SQLite backup/restore, truthful retrieval
  contracts, patched web dependencies, packaging, and release evidence. It
  also carries the round-2..6 retrieval and memory features already recorded
  in the changelog. It is tagged and published on PyPI and GitHub. It remains
  the latest published release until `v0.9.4` publishes.
- `v0.9.3` was an internal security-hotfix candidate carrying five P1 fixes.
  A follow-up external audit returned NO-GO with nine additional P1 findings,
  so `v0.9.3` was withdrawn and never published. Nothing for `v0.9.3` ever
  reached PyPI or GitHub.
- `v0.9.4` is the current release candidate: a security and reliability
  hotfix over v0.9.2 that supersedes the withdrawn `v0.9.3` candidate. It
  carries the original five v0.9.3 fixes — lifecycle state-machine defects
  (one central transition table), expire/unexpire row-locking races, a
  migration-0083 identifier-reservation bug (corrective migration 0084),
  project-scoped capture persistence, and hard people/time filter pagination
  — and additionally resolves all nine P1 findings from the second (external)
  audit. No `v0.9.3` or `v0.9.4` work is published yet.
- Alice is a local-first continuity layer for AI agents. Agent developers
  are the primary customer.

## What `v0.9.4` Changes

`v0.9.4` is a security and reliability hotfix over `v0.9.2` that supersedes
the withdrawn `v0.9.3` candidate. `v0.9.3` was an internal security-hotfix
candidate carrying the five P1 fixes below; a follow-up external audit
returned NO-GO with nine more P1 findings, so `v0.9.3` was withdrawn and
never published. `v0.9.4` carries the original five fixes and resolves all
nine second-audit findings. The work is complete on this hotfix branch but
not yet released; the release ships only after the canonical gates pass on
one exact clean SHA.

Original five fixes (carried forward from the withdrawn `v0.9.3`):

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

Nine second-audit P1 fixes (new in `v0.9.4`):

- **Serialized supersession-graph mutation** — supersession-graph mutation is
  serialized per user with an advisory lock, and a cycle guard fails closed on
  depth.
- **Scope-aware dedupe and scope propagation** — content dedupe is scope-aware
  and connector/proposal scope now propagates correctly.
- **Filter scan depth** — people/time retrieval filters deepen the ranked scan
  until enough scoped rows survive.
- **Endpoint-fingerprinted embedding signatures** — embedding signatures
  include an endpoint fingerprint so different coordinate spaces are not
  pooled.
- **Exact-ID embedding-presence read** — consolidation and rollups use an
  exact-ID embedding-presence read instead of a global ANN probe.
- **Authoritative rollup membership** — rollup cards persist full authoritative
  membership rather than the truncated display subset.
- **Iterative HNSW scan** — filtered PostgreSQL vector search enables iterative
  HNSW scan.
- **Release eval fails closed** — the canonical release eval fails closed
  (`--release-gate` / `pass_fts_only`) and propagates eval failure to the exit
  code.
- **Finalized-release-docs check** — the finalized-release-docs check rejects
  premature-publication claims.

## Published Evidence

- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. Per-question rows and protocol receipts are committed under
  `docs/benchmarks/longmemeval/`.
- The result has not been replicated and is not a `v0.9.4` measurement.
- The scale envelope is a single-machine synthetic benchmark, not a
  concurrent load test.

## Release Boundary

`v0.9.2` shipped only after the canonical release check passed on one exact
clean source SHA and the reviewer reported no remaining release blocker. The
same boundary governs `v0.9.4`: it is releasable only when the canonical
release check passes on its exact clean source SHA and the reviewer reports no
remaining release blocker. `v0.9.3` did not clear this boundary — the second
audit returned NO-GO — so it was withdrawn rather than published, and
`v0.9.4` supersedes it.

## Product Boundaries

- Local-first, single-user, self-hosted.
- No hosted service or SLA.
- No managed OAuth connectors.
- No silent capture from arbitrary conversations.
- Durable agent writes remain policy-checked and reviewable.

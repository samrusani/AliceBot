# Current State

## Snapshot

- `v0.9.1` is the latest published release.
- `v0.9.2` is the current security and release-hardening candidate. It has
  not been tagged or published.
- Alice is a local-first continuity layer for AI agents. Agent developers
  are the primary customer.

## What `v0.9.2` Targets

- **Agent authorization** — key-bound project scope is inherited when omitted
  and enforced on reads and writes; lifecycle authorization uses the
  persisted target; read-only and proposal-only profiles cannot mutate
  accepted memory.
- **Safe local ownership** — versioned, integrity-checked SQLite
  export/import with consistent snapshots, atomic file replacement,
  collision equality checks, a foreign-key-closed portable record set, and
  owner-only default filesystem permissions. Embedding vectors are rebuilt
  explicitly after restore.
- **Upgrade safety** — data-bearing PostgreSQL and SQLite upgrade fixtures
  cover old revision triggers and legacy status constraints.
- **Lifecycle coherence** — corrections and review decisions reconcile
  status, confirmation state, fact keys, embeddings, entity links,
  revisions, provenance, and supersession without resurrecting retired
  rows.
- **Truthful retrieval contracts** — project, person, and time filters apply
  across pack sections; multi-project scopes match by overlap; request sizes
  are bounded; budget reports distinguish charged unique content from an
  exact fixed-point estimate of the final serialized response.
- **Release integrity** — patched web dependencies, installed-artifact
  smokes, version/tag/artifact gates, protected publication guidance, and
  corrected benchmark documentation.

## Published Evidence

- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. Per-question rows and protocol receipts are committed under
  `docs/benchmarks/longmemeval/`.
- The result has not been replicated and is not a v0.9.2 release-candidate
  measurement.
- The scale envelope is a single-machine synthetic benchmark, not a
  concurrent load test.

## Release Boundary

The candidate is ready only when the canonical release check passes on the
exact clean source SHA and the reviewer reports no remaining release blocker.
No tag, GitHub release, or PyPI publication has occurred for v0.9.2.

## Product Boundaries

- Local-first, single-user, self-hosted.
- No hosted service or SLA.
- No managed OAuth connectors.
- No silent capture from arbitrary conversations.
- Durable agent writes remain policy-checked and reviewable.

# Current State

## Snapshot

- `v0.9.2` is the latest published release: security and reliability
  hardening — project-bound agent authorization, lifecycle and upgrade
  correctness, safe local SQLite backup/restore, truthful retrieval
  contracts, patched web dependencies, packaging, and release evidence. It
  also carries the round-2..6 retrieval and memory features already recorded
  in the changelog. It is tagged and published on PyPI and GitHub.
- `v0.10.0` is the current development-cycle candidate. Its scope is the next
  feature cycle; no `v0.10.0` work has shipped yet.
- Alice is a local-first continuity layer for AI agents. Agent developers
  are the primary customer.

## What `v0.10.0` Targets

`v0.10.0` is in development. The items below are targets for the next feature
cycle — the memory frontier — not shipped work.

- **Typed consolidation cards** — evolve review-gated roll-up consolidation
  toward typed continuity cards with explicit structure.
- **Embedding quantization for the SQLite on-ramp** — shrink the on-disk
  vector footprint so the zero-infrastructure path scales further.
- **Local-embeddings preset** — a first-class, provider-free embedding
  configuration for the local-first default.
- **CPU cross-encoder pack compressor** — an optional local reranking and
  compression stage that runs without a hosted provider.
- **Provenance-grounded-memory technical report** — follow through on the
  grounding and honesty-kit work with a published methodology report.

## Published Evidence

- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. Per-question rows and protocol receipts are committed under
  `docs/benchmarks/longmemeval/`.
- The result has not been replicated and is not a `v0.10.0` development-cycle
  measurement.
- The scale envelope is a single-machine synthetic benchmark, not a
  concurrent load test.

## Release Boundary

`v0.9.2` shipped only after the canonical release check passed on one exact
clean source SHA and the reviewer reported no remaining release blocker. The
same boundary governs `v0.10.0`: it is releasable only when the canonical
release check passes on its exact clean source SHA and the reviewer reports no
remaining release blocker.

## Product Boundaries

- Local-first, single-user, self-hosted.
- No hosted service or SLA.
- No managed OAuth connectors.
- No silent capture from arbitrary conversations.
- Durable agent writes remain policy-checked and reviewable.

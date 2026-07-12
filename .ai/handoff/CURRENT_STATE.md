# Current State

## Snapshot

- `v0.9.4` is the latest published release: a security and reliability hotfix
  over v0.9.2 that supersedes the withdrawn `v0.9.3` candidate. It carries the
  original five v0.9.3 fixes — lifecycle state-machine defects (one central
  transition table), expire/unexpire row-locking races, a migration-0083
  identifier-reservation bug (corrective migration 0084), project-scoped
  capture persistence, and hard people/time filter pagination — and
  additionally resolved all nine P1 findings from the second (external) audit.
  It is tagged and published on PyPI and GitHub as an immutable release, with
  Trusted Publishing attestations, and its artifact digests are recorded in
  `docs/release/v0.9.4-checksums.txt`. It replaces `v0.9.2` as the latest
  published release.
- `v0.9.2` is now a prior published release: security and reliability
  hardening — project-bound agent authorization, lifecycle and upgrade
  correctness, safe local SQLite backup/restore, truthful retrieval
  contracts, patched web dependencies, packaging, and release evidence. It
  also carries the round-2..6 retrieval and memory features already recorded
  in the changelog. It remains tagged and published on PyPI and GitHub, but is
  no longer the latest published release — `v0.9.4` is.
- `v0.9.3` was an internal security-hotfix candidate carrying five P1 fixes.
  A follow-up external audit returned NO-GO with nine additional P1 findings,
  so `v0.9.3` was withdrawn and never published. Nothing for `v0.9.3` ever
  reached PyPI or GitHub.
- `v0.10.0` is the reopened next development-cycle candidate: the next cycle
  of feature work plus the audit's P2 backlog. No `v0.10.0` work is published
  yet.
- Alice is a local-first continuity layer for AI agents. Agent developers
  are the primary customer.

## What `v0.10.0` Targets

`v0.10.0` is the reopened development-cycle candidate over the published
`v0.9.4` baseline. The cycle resumes feature work and clears the second
audit's P2 backlog. No `v0.10.0` work has shipped yet; the release ships only
after the canonical gates pass on one exact clean SHA.

Resume feature work (in rough priority order):

- **Multi-session synthesis** — still the weakest published LongMemEval
  category; measure and improve aggregation-aware retrieval without overfitting
  the development slice.
- **Dogfood daily** — run real agent workflows with an embedding endpoint and
  measure correction quality, review burden, project-scope usability, and
  end-to-end latency.
- **Reference integrations** — deeper examples for popular agent frameworks on
  the eleven-tool core surface.

Clear the P2 backlog from the second audit:

- **Full-package mypy + web typecheck** — extend static typing across the full
  package and add the web typecheck to the gate set.
- **Packaged-README PyPI links** — fix the packaged-README links that render on
  the PyPI project page.
- **Backup/restore hardening** — harden the local backup/restore path beyond
  the v0.9.x baseline.
- **N+1 retrieval fan-out** — remove the N+1 fan-out in retrieval.
- **Non-finite embedding validation** — validate and reject non-finite
  embedding values before persistence.
- **Related items** — the remaining P2 cleanup recorded in the audit backlog.

## Published Evidence

- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. Per-question rows and protocol receipts are committed under
  `docs/benchmarks/longmemeval/`.
- The result has not been replicated and is not a `v0.9.4` measurement.
- The scale envelope is a single-machine synthetic benchmark, not a
  concurrent load test.

## Release Boundary

`v0.9.4` shipped only after the canonical release check passed on one exact
clean source SHA and the reviewer reported no remaining release blocker; the
release is tagged and immutable, with Trusted Publishing attestations and
digests recorded in `docs/release/v0.9.4-checksums.txt`. `v0.9.2` cleared the
same boundary before it. The same boundary governs `v0.10.0`: it is releasable
only when the canonical release check passes on its exact clean source SHA and
the reviewer reports no remaining release blocker. `v0.9.3` did not clear this
boundary — the second audit returned NO-GO — so it was withdrawn rather than
published, and `v0.9.4` superseded it.

## Product Boundaries

- Local-first, single-user, self-hosted.
- No hosted service or SLA.
- No managed OAuth connectors.
- No silent capture from arbitrary conversations.
- Durable agent writes remain policy-checked and reviewable.

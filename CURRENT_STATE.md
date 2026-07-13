# Current State

## Snapshot

- `v0.9.4` is the latest published release: a security and reliability hotfix
  over v0.9.2 that supersedes the withdrawn `v0.9.3` candidate. It carries the
  original five v0.9.3 fixes — lifecycle state-machine defects (one central
  transition table), expire/unexpire row-locking races, a migration-0083
  identifier-reservation bug (corrective migration 0084), project-scoped
  capture persistence, and hard people/time filter pagination — and
  attempted the nine P1 remediations from the second external audit. A third
  independent audit found partial fixes and regressions; do not treat the
  v0.9.4 remediation claims as proof that those findings are closed.
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
- `v0.10.0` is the active audit-remediation development candidate over the
  immutable v0.9.4 tag. Correctness and release-evidence repair take priority
  over feature work. No `v0.10.0` work is published yet.
- Alice is a local-first continuity layer for AI agents. Agent developers
  are the primary customer.

## What `v0.10.0` Targets

`v0.10.0` is the reopened development-cycle candidate over the published
`v0.9.4` baseline. It is a third-audit remediation cycle; unrelated feature
work remains paused. No `v0.10.0` work has shipped yet. Release requires every
reviewer repair, the canonical local gates, independent re-review, and the
protected semantic gate to pass against one exact clean SHA.

After the remediation gate is independently approved, resume feature work:

- **Multi-session synthesis** — still the weakest published LongMemEval
  category; measure and improve aggregation-aware retrieval without overfitting
  the development slice.
- **Dogfood daily** — run real agent workflows with an embedding endpoint and
  measure correction quality, review burden, project-scope usability, and
  end-to-end latency.
- **Reference integrations** — deeper examples for popular agent frameworks on
  the eleven-tool core surface.

The active remediation also clears the third-audit findings:

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
- **Release evidence** — a configured exact-SHA semantic eval must persist and
  retrieve fully signed vectors, record positive vector candidate
  participation, and produce an attested report consumed by publication.
- **Correctness follow-ups** — complete hard filters, scoped/atomic capture
  dedupe, fail-closed lifecycle graphs, truthful rollups, cohesive grouping,
  pgvector version enforcement, and backup/restore input stability.
- **Web quality** — thread-keyed drafts, independent outage degradation,
  type-safe tests, real-browser navigation, accessibility, and performance
  budgets.

## Published Evidence

- The historical LongMemEval_s result is **79.4% (397/500)** from one run on
  2026-07-07. Per-question rows and protocol receipts are committed under
  `docs/benchmarks/longmemeval/`.
- The result has not been replicated and is not a `v0.9.4` measurement.
- The scale envelope is a single-machine synthetic benchmark, not a
  concurrent load test.

## Release Boundary

`v0.9.4` is tagged and immutable, with Trusted Publishing attestations and
digests recorded in `docs/release/v0.9.4-checksums.txt`. Its publish workflow
passed unit, LongMemEval, packaging, and artifact checks, but it did not run a
successful configured semantic-vector release eval. A later audit also found
that the bundled eval seeded vectors without the production signature. The
repository therefore does not claim that v0.9.4 cleared the current canonical
release boundary. `v0.10.0` is releasable only after every gate passes on one
exact clean SHA, the semantic report proves nonzero signed-vector candidates,
and an independent reviewer reports no release blocker.

## Product Boundaries

- Local-first, single-user, self-hosted.
- No hosted service or SLA.
- No managed OAuth connectors.
- No silent capture from arbitrary conversations.
- Durable agent writes remain policy-checked and reviewable.

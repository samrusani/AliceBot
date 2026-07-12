# Roadmap

## Baseline (Not Roadmap Work)

- `v0.9.4`: latest published release. A security and reliability hotfix over
  v0.9.2 that supersedes the withdrawn `v0.9.3` candidate — carrying the
  original five v0.9.3 fixes (central lifecycle transition table,
  expire/unexpire row-locking, corrective migration 0084 for the
  migration-0083 identifier-reservation bug, project-scoped capture
  persistence, and hard people/time filter pagination) and resolving all nine
  P1 findings from the follow-up external audit that returned NO-GO on
  `v0.9.3`. Tagged and published on PyPI and GitHub as an immutable release,
  with Trusted Publishing attestations and digests recorded in
  `docs/release/v0.9.4-checksums.txt`.
- `v0.9.2`: prior published release. A security and reliability patch —
  project-bound authorization, lifecycle consistency, SQLite backup/restore,
  data-bearing upgrades, retrieval bounds, patched web dependencies, package
  resources, and release provenance — carrying the round-2..6 retrieval and
  memory features already recorded in the changelog. Tagged and published on
  PyPI and GitHub; superseded as the latest published release by `v0.9.4`.
- `v0.9.1`: prior published release. It includes the historical
  LongMemEval_s **79.4% (397/500)** single run, with methodology and
  per-question receipts under [docs/benchmarks/longmemeval/](docs/benchmarks/longmemeval/README.md).
- `v0.9.0`: Memory Operations Protocol, Context API v2, temporal graph
  memory, entity resolution, expanded export/import, and the published scale
  envelope.
- `v0.8.0`: typed and staleness-aware retrieval, agentic writes, key-bound
  scopes, consolidation, memory-quality evals, and the LongMemEval harness.
- `v0.7.0`: zero-infrastructure SQLite on-ramp published as `alice-memory`.
- `v0.6.0`: hybrid FTS/vector retrieval, consolidated MCP surface, per-agent
  API keys, and live-store evals.

## Release Candidate

- `v0.10.0`: current development-cycle candidate — the reopened next cycle over
  the published `v0.9.4` baseline. It resumes feature work (multi-session
  synthesis, daily dogfooding, and reference integrations) and clears the
  second audit's P2 backlog: full-package mypy plus web typecheck,
  packaged-README PyPI links, backup/restore hardening, removing the N+1
  retrieval fan-out, non-finite embedding validation, and related items. The
  original five v0.9.3 P1 fixes and all nine second-audit P1 findings already
  shipped in the published `v0.9.4`; `v0.9.3` was an internal security-hotfix
  candidate that was withdrawn and never published. No `v0.10.0` work has
  shipped yet; `v0.10.0` is not tagged or published until one exact clean SHA
  passes the canonical release check and review.

## Next

In rough priority order for and beyond v0.10.0:

1. **Multi-session synthesis** — still the weakest published LongMemEval
   category at 58.6%. Aggregation-aware retrieval now ships; the next work is
   to measure and improve synthesis without tuning repeatedly on the same
   development slice.
2. **Dogfood daily** — run real agent workflows with an embedding endpoint;
   measure correction quality, review burden, project-scope usability, and
   end-to-end latency.
3. **Reference integrations** — deeper examples for popular agent frameworks
   on the eleven-tool core surface.
4. **SQLite vector search at scale** — improve the documented 20-30k
   embedding comfort zone. The current synthetic envelope reaches about 2.3
   seconds at 100k; publish recall deltas alongside any latency improvement.
5. **Hosted offering exploration** — possible after the local authorization,
   RLS, backup, and operations model has more production evidence; still
   exploratory.

## Explicit Non-Goals For Now

- Hosted-service or SLA commitments.
- Managed OAuth connectors and account syncing.
- A consumer knowledge-management product.
- OCR or transcription execution beyond ingesting text extracted elsewhere.

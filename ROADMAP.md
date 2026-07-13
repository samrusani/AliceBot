# Roadmap

## Baseline (Not Roadmap Work)

- `v0.9.4`: latest published release. A security and reliability hotfix over
  v0.9.2 that supersedes the withdrawn `v0.9.3` candidate — carrying the
  original five v0.9.3 fixes (central lifecycle transition table,
  expire/unexpire row-locking, corrective migration 0084 for the
  migration-0083 identifier-reservation bug, project-scoped capture
  persistence, and hard people/time filter pagination) and attempting all nine
  P1 remediations from the follow-up external audit that returned NO-GO on
  `v0.9.3`. A third audit found incomplete fixes and new regressions, now in the
  v0.10.0 remediation gate. Tagged and published on PyPI and GitHub as an immutable release,
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

- `v0.10.0`: active audit-remediation candidate over the published, immutable
  `v0.9.4` baseline. It must close the third audit's correctness, reliability,
  performance, typing, web, backup, packaging, and documentation findings
  before feature work resumes. The gate includes a configured semantic eval
  that proves nonzero production-signed vector participation, full first-party
  Python and web type checks, installed-artifact smokes, and independent
  review. No `v0.10.0` work has shipped; it is not tagged or published until
  every required check passes on one exact clean SHA.

## Next

After the v0.10.0 audit-remediation gate is approved, continue in this order:

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

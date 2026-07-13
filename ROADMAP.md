# Roadmap

## Baseline (Not Roadmap Work)

- `v0.10.2`: latest published release. It carries the third-audit remediation,
  production-signed semantic-vector gate, atomic source capture deduplication,
  lifecycle-cycle repair, scoped retrieval improvements, pgvector 0.8+
  enforcement, full first-party typing, web quality gates, installed-artifact
  smokes, and structured release attestations. It is tagged and immutable on
  GitHub and published on PyPI; exact artifact digests are in
  `docs/release/v0.10.2-checksums.txt`.
- `v0.9.4`: prior published release. It remains available as historical
  evidence but is superseded by v0.10.2.
- `v0.9.3`, `v0.10.0`, and `v0.10.1`: withdrawn or failed-publication versions;
  none has a PyPI distribution. Do not recommend them for installation.
- `v0.9.1`: prior release associated with the historical LongMemEval_s
  **79.4% (397/500)** single run. The run is dated 2026-07-07 and must not be
  presented as a repeated result or current-version benchmark.
- `v0.9.0`: Memory Operations Protocol, Context API v2, temporal graph memory,
  entity resolution, expanded export/import, and the published scale envelope.
- `v0.8.0`: typed and staleness-aware retrieval, agentic writes, key-bound
  scopes, consolidation, memory-quality evals, and the LongMemEval harness.
- `v0.7.0`: zero-infrastructure SQLite on-ramp published as `alice-memory`.
- `v0.6.0`: hybrid FTS/vector retrieval, consolidated MCP surface, per-agent
  API keys, and live-store evals.

## Current Remediation

`main` plus the reviewed remediation tree form the `v0.10.3` candidate
release. This work is not part of the published v0.10.2 artifacts. It closes
the fourth audit's correctness, project/user isolation, lifecycle,
large-corpus efficiency, import, scheduler, API-contract, documentation, and
test-gate findings, and publishes only after the canonical exact-SHA gates
pass.

The next release gate must prove one exact clean SHA through role-separated
Postgres/pgvector integration, all model-free LongMemEval tests and checked-in
dataset-manifest consistency, production-compatible semantic-vector evidence,
Python 3.12–3.14 functional coverage, web units/types/coverage/browser checks,
reproducible installed artifacts, and independent review. PyPI must receive the
verified bytes before the stable immutable GitHub Release is created.

## Next

After the remediation release is independently approved:

1. **Multi-session synthesis** — still the weakest historical LongMemEval
   category. Measure and improve aggregation-aware retrieval without tuning
   repeatedly on one development slice.
2. **Dogfood daily** — use real agent workflows with an embedding endpoint;
   measure correction quality, review burden, project-scope usability, and
   end-to-end latency.
3. **Reference integrations** — deepen examples for popular agent frameworks
   on the eleven-tool core surface.
4. **SQLite vector search at scale** — improve the documented 20–30k embedding
   comfort zone and publish recall deltas alongside latency improvements.
5. **Hosted offering exploration** — only after the local authorization, RLS,
   backup, and operations model has stronger production evidence.

## Explicit Non-Goals For Now

- Hosted-service or SLA commitments.
- Managed OAuth consent/account-linking and automatic connector polling.
- A consumer knowledge-management product.
- OCR or transcription execution beyond ingesting text extracted elsewhere.

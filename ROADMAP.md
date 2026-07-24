# Roadmap

## Baseline (Not Roadmap Work)

- `v0.14.0` is the latest published release. Its immutable release record is
  `docs/release/v0.14.0-release-notes.md`, with artifact digests in
  `docs/release/v0.14.0-checksums.txt`. (The `v0.13.0` tag was never
  published; superseded.)
- `v0.11.0` shipped the Phase 1 periphery cut; `v0.11.1` shipped the Phase 2
  debt sweep. Their tags, release records, and published artifacts are not
  changed by the Phase 3 carrier.
- `v0.12.0` shipped the Phase 3 structural refactor with **Structure only.
  Zero behavior change.** `v0.13.1` shipped the Phase 4 core roadmap:
  three-run benchmark replication on a pinned manifest, SQLite vector scale
  with the resident cache, CI-smoked reference integrations, and the
  multi-session synthesis measurement (its records live in
  `docs/release/v0.13.1-release-notes.md`).
- The historical **79.4% (397/500)** LongMemEval_s result is one run from
  2026-07-07 on an older baseline. It is not a repeated estimate or a Phase 3
  measurement.
- Detailed v0.10.4 repair-batch chronology is historical evidence under
  `docs/handoff/history/`; it is not current roadmap work.

## Next

`v0.14.0` (Phase 5 enterprise track) is released; the next phase begins here.
Phases 1 through 5 are shipped and recorded in their release notes. Of the
former roadmap list, benchmark replication, multi-session synthesis
measurement, reference integrations, SQLite vector scale, and the enterprise
evidence base (real-host single-tenant deployment contract executed end to
end, least-privilege operations, encrypted off-host backups with a tested
restore, recorded security disposition) shipped in Phases 4 and 5.

1. **Counting substrate (recommended Phase 6).** Multi-session accuracy is
   the largest measured weakness, and Phase 4 forensics attribute the
   dominant failures to undercounting. Phase 4 also proved that no
   query-time mechanism over the current store can earn a count (the
   recorded NO-GO in the Sprint 4 handoff; the count statistic shipped
   trace-only). The fix is a substrate change: one reviewed occurrence unit
   per countable event, established at write time, with provenance-aware
   deduplication and honest ranges where evidence is ambiguous. Phase 6
   work has not begun; when authorized it starts as a receipt-bound
   carrier on the published `v0.14.0`.
2. **Dogfood the agent interface daily.** Still open, and no build phase
   can deliver it. Exercise the eleven-tool MCP core and equivalent
   HTTP/CLI flows against a live deployment; measure correction quality,
   review burden, project-scope usability, and end-to-end latency.
3. **Scale end-to-end recall past the FTS wall.** The vector stage stays
   interactive at 100k memories (resident cache; published in
   `docs/benchmarks/scale/`). The remaining wall at very large corpora is
   FTS/source-chunk search; SQLite end-to-end recall at 100k is ~1.8s
   against ~0.4s on Postgres.
4. **Road to `1.0`.** Remaining before a `1.0` claim: sustained dogfooding
   evidence, the filed deployment-guide hygiene follow-ups, and one final
   product-scoped review of the post-cut surface.

## Explicit Non-Goals For Now

- Hosted-service, multi-tenant control-plane, or SLA commitments.
- Managed OAuth consent/account-linking or automatic account polling.
- Telegram or other channel transports.
- A public bundled chat/response product, chief-of-staff product, or model-pack
  catalog. Internal response jobs remain limited to retained provider
  invocation.
- A consumer knowledge-management product.
- OCR or transcription execution; Alice accepts text extracted elsewhere.
- Re-expanding the default MCP surface beyond the eleven core tools.

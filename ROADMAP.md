# Roadmap

## Baseline (Not Roadmap Work)

- `v0.12.0` is the latest published release. Its immutable release record is
  `docs/release/v0.12.0-release-notes.md`, with artifact digests in
  `docs/release/v0.12.0-checksums.txt`.
- `v0.11.0` shipped the Phase 1 periphery cut; `v0.11.1` shipped the Phase 2
  debt sweep. Their tags, release records, and published artifacts are not
  changed by the Phase 3 carrier.
- `v0.12.0` shipped the Phase 3 structural refactor with **Structure only.
  Zero behavior change.** Both governed version sources are `0.12.0`.
- The historical **79.4% (397/500)** LongMemEval_s result is one run from
  2026-07-07 on an older baseline. It is not a repeated estimate or a Phase 3
  measurement.
- Detailed v0.10.4 repair-batch chronology is historical evidence under
  `docs/handoff/history/`; it is not current roadmap work.

## Next

`v0.12.0` (Phase 3; structure only) is released; the next phase begins here.

1. **Replicate the current benchmark.** Run LongMemEval_s at least three times
   on one pinned, non-development manifest; publish variance, exact provider
   configuration, per-question evidence, and honest abstention trade-offs.
2. **Improve multi-session synthesis.** Measure aggregation-aware retrieval on
   a held-out slice instead of repeatedly tuning one development set.
3. **Dogfood the agent interface daily.** Exercise the eleven-tool MCP core and
   equivalent HTTP/CLI flows with a live embedding endpoint; measure correction
   quality, review burden, project-scope usability, and end-to-end latency.
4. **Deepen reference integrations.** Keep examples runnable and CI-smoked
   against the surviving core without introducing a second runtime or reviving
   deleted product surfaces.
5. **Scale SQLite vector search.** Extend the documented 20-30k embedding
   comfort zone while publishing latency and recall deltas.
6. **Build enterprise evidence on the post-cut surface.** Conduct the first
   scoped security review, exercise backup/restore and supported upgrade paths,
   and run one final product-scoped audit before `1.0`.

Phase 4 work has not begun and is not authorized by the Phase 3 handoff.

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

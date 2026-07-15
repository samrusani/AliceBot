# Roadmap

## Baseline (Not Roadmap Work)

- `v0.10.4` is the latest published release. Its immutable release record is
  `docs/release/v0.10.4-release-notes.md`, with artifact digests in
  `docs/release/v0.10.4-checksums.txt`.
- `v0.11.0` is the current unpublished candidate. Phase 1 narrows the default
  product to Alice's agent interface and retrieval/memory-quality core; it does
  not authorize publication.
- The historical **79.4% (397/500)** LongMemEval_s result is one run from
  2026-07-07 on an older baseline. It is not a repeated estimate or a current-
  candidate measurement.
- Detailed v0.10.4 repair-batch chronology is historical evidence archived in
  `docs/handoff/history/v0.10.4-repair-batches.md`; it is not current roadmap
  work.

## Next

1. **Finish and verify the v0.11.0 periphery cut.** Prove that the default HTTP,
   MCP, CLI, scheduler, web, PostgreSQL, and SQLite surfaces match the declared
   local-first product boundary. Keep the temporary compatibility mount flag
   fail-closed, documented, and covered by removal-date tests.
2. **Replicate the current benchmark.** Run LongMemEval_s at least three times
   on one pinned, non-development manifest; publish variance, exact provider
   configuration, per-question evidence, and honest abstention trade-offs.
3. **Improve multi-session synthesis.** Measure and improve aggregation-aware
   retrieval on a held-out slice instead of repeatedly tuning one development
   set.
4. **Dogfood the agent interface daily.** Exercise the eleven-tool MCP core and
   equivalent HTTP/CLI flows with a live embedding endpoint; measure correction
   quality, review burden, project-scope usability, and end-to-end latency.
5. **Deepen reference integrations.** Keep examples runnable and CI-smoked
   against the surviving core surface, without introducing a second runtime or
   reviving deleted chat/provider-control features.
6. **Scale SQLite vector search.** Extend the documented 20–30k embedding
   comfort zone while publishing both latency and recall deltas.
7. **Complete the pre-1.0 structural split.** After the periphery cut, split the
   remaining oversized API, store, CLI, and MCP registries along existing domain
   seams without changing behavior or coverage thresholds.
8. **Build enterprise evidence on the post-cut surface.** Conduct the first
   scoped security review, exercise backup/restore and supported upgrade paths,
   and run one final product-scoped audit before `1.0`.

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

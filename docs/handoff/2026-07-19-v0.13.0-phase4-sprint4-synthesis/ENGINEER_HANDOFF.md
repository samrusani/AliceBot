# Phase 4 Sprint 4 Engineer Handoff

## Start here

Code-carrier and benchmark-closure verdicts are separate:

- **Code carrier:** ready for independent adversarial review.
- **Sprint 4.2 benchmark closure:** **NO-GO**. The final design is trace-only;
  both deterministic dev arms have 0/14 answer-sufficient audited count rows.

Base: `dc60924f6c5486b8ba2b82dcecf22378bf043319`, tree
`2f1a6ababbd70ebc0106f750dc1b34d4b85fd5ca`, branch
`codex/v0130-phase4-sprint4-synthesis`. The carrier is intentionally
uncommitted and unstaged. Versions remain `0.12.0`.

## Review order

1. Review `vnext_coverage_query.py`: sub-intent detection and bounded,
   provenance-deduplicated trace statistic.
2. Review the marked blocks in `vnext_retrieval.py`: cap use, trace
   disclosure, cadence no-mutation path, and restored generic card posture.
3. Verify the HTTP response and OpenAPI schema contain no `aggregation`
   field; MCP production code is unchanged from the base.
4. Review fail-on-old tests for >cap adapters, numeric/cadence silence,
   three-members-each-carry-multiple-occurrences, dormant byte identity, and
   public-field absence.
5. Review `eval/longmemeval/count_probe.py`: question-date
   `reference_time`, exact manifest, mode separation, and unconditional
   NO-GO while every audited count lacks sufficient information.
6. Reproduce final keyless probes and hashes from `BUILD_REPORT.md`.
7. Reconstruct the explicit carrier receipt and author an independent
   `REVIEW_REPORT.md`.

## High-risk invariants

- Candidate count is trace-only and never a numeric sum or answer.
- `rows_examined <= candidate_cap` and `count <= candidate_cap`, including
  legacy adapters that return too many rows.
- No top-level reader aggregation, MCP passthrough, or OpenAPI property exists.
- Equal row/member counts do not prove equal queried units; one memory may say
  `twice` or contain several goals/items.
- No new aggressive count-card promotion exists. Pre-Sprint generic promotion
  is preserved; cadence changes no selection behavior.
- Numeric-value, cadence, rejected widening, and dormant paths never receive a
  trace candidate count.
- No model/provider call was introduced, and benchmark gold is never retrieval
  input.
- Source-pool depth and clause-to-RRF behavior are unchanged.

## Local reproduction

All commands are keyless. Count probes intentionally exit 3.

```bash
./.venv/bin/pytest tests/unit -q
./.venv/bin/pytest eval/longmemeval/test_*.py -q
./.venv/bin/ruff check apps/api/src/alicebot_api/vnext_coverage_query.py apps/api/src/alicebot_api/vnext_retrieval.py eval/longmemeval/count_probe.py eval/longmemeval/test_count_probe.py tests/unit/test_vnext_coverage_query.py tests/unit/test_vnext_retrieval.py tests/unit/test_vnext_main.py tests/unit/test_phase4_sprint4_handoff_truth.py
./.venv/bin/mypy apps/api/src/alicebot_api/vnext_coverage_query.py apps/api/src/alicebot_api/vnext_retrieval.py
git diff --check
```

Run the exact count/coverage commands in `BUILD_REPORT.md`. Do not run a
paid/full/held-out benchmark from this handoff.

## Receipt and staging boundary

Receipt format:
`alice-v0.13.0-phase4-sprint4-synthesis-explicit-carrier-v2`.

The receipt hashes only the 12 explicit Sprint 4 paths listed in
`BUILD_REPORT.md`; it does not derive scope from the dirty-tree union.
`BUILD_REPORT.md` and reviewer-owned `REVIEW_REPORT.md` are excluded solely
to avoid a receipt loop. The concurrently generated scale JSON files are a
separate release-engineer lane, are asserted disjoint, and are never receipt
inputs.

Stage exact paths only. Never use `git add -A` or `git add .` in this
shared tree. Stage the 12 receipt paths plus this handoff's
`BUILD_REPORT.md`, then add reviewer-authored `REVIEW_REPORT.md` separately
if present. Leave every `docs/benchmarks/scale/results/*.json` path unstaged.

Any change to a receipt-listed path requires a new bind and independent review.

## Release-engineer decision

Do not represent this carrier as Sprint 4.2 benchmark closure and do not spend
the held-out acceptance run on it as-is. A future count-answer design needs a
persisted, reviewed one-unit-per-member invariant or a different deterministic
aggregate substrate. That work is outside this carrier.

Version cuts, committed-SHA CI, paid/held-out evaluation, tagging,
publication, and external readback remain release-engineer work.

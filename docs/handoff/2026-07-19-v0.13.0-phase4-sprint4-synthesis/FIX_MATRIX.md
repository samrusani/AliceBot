# Phase 4 Sprint 4 Fix Matrix

## Outcome matrix

| Item | Final carrier | Evidence | Disposition |
|---|---|---|---|
| A. Count recognition | Adds cardinality, occurrence-frequency, cadence, and numeric-value sub-intents. `how often` is cadence; `how many times` / `number of times` are frequency. | Detector tables and cadence no-mutation service test. | Implemented. |
| B. Candidate count | Records a provenance-deduplicated, bounded scoped-FTS candidate-group statistic in trace only. The input is sliced to the positive disclosed cap and saturation uses the original returned length. | Unit/SQLite/HTTP tests cover deduplication, >cap legacy adapters, fallback/saturation disclosure, and `is_answer=false`. | Implemented as diagnostic telemetry, not an answer. All 14 audited values mismatch dev gold. |
| C. Roll-up promotion / answer | The attempted verified aggregation and aggressive count-specific promotion were removed. A row/member can encode multiple queried units, so count equality and identity equality cannot prove the answer. Existing generic promotion remains unchanged. | Generic-card posture test, three-members-each-say-twice frequency test, roll-ups-on measurement. | Rejected. No reader/MCP/OpenAPI count surface; 0/14 answer-sufficient. Sprint 4.2 is NO-GO. |
| D. Diversity | No broad threshold change. Cadence keeps detector-off depth, calls, diversity, ranking, and selected order. | Store-call, FTS-limit, selected-order comparison; coverage summary byte-equal to before. | Measured do-not-change outcome retained. |
| E. Gate widening | The measured `total number of` widening was removed because audited scalar/sum cases produced misleading row counts. | Rejected-widening safe-non-emission stratum 3/3. | Rejected; no widening shipped. |
| Probe parity | Count probe passes the exact parsed question date as `reference_time`, uses mode-specific outputs, and requires nonzero/exact audit strata. | Request-capture test; empty/detector-only/partial-manifest tests. | Implemented. |

## Final truth boundary

```text
cardinality/frequency query
  -> bounded scoped FTS candidate groups
  -> trace-only diagnostic
       is_answer = false
       supports_numeric_sum = false
  -> never a top-level reader aggregate

selected accepted roll-up
  -> may appear through the pre-existing generic ranking posture
  -> remains unverified for count-answer purposes
```

A persisted, reviewed one-unit-per-member invariant does not exist in current
roll-up data. The carrier does not infer one from text, member identity, strict
FTS, or equal cardinalities.

## Scope proof

- No route, MCP tool, OpenAPI response property, migration, schema, provider,
  dependency, reader prompt, or governed version source changed.
- `eval/longmemeval/count_probe.py` and its unit test are additions; no
  existing evaluation file was altered.
- The release-engineer-owned SQLite vector file, baseline-run directory, and
  benchmark records are outside the explicit carrier allowlist.
- Historical roll-ups-off remains the comparability arm; roll-ups-on uses a
  separate work directory. Both are NO-GO with 0/14 answer sufficiency.

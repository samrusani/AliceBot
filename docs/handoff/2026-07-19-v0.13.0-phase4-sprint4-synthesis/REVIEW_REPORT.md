# Phase 4 Sprint 4 Independent Review Report

Date: 2026-07-19

## Verdict

- **Code carrier (frozen): conditional GO** for integration as bounded,
  trace-only diagnostic groundwork, subject to restoring shared-tree
  isolation and then passing committed-SHA CI. This is not a live dirty-tree
  sign-off or a full release GO.
- **Sprint 4.2 benchmark closure: NO-GO.** The carrier provides no
  reader-facing count answer, and both audited development arms remain at
  **0/14 answer-sufficient rows**.
- Do not run the held-out acceptance benchmark or describe this carrier as a
  multi-session synthesis uplift. A later design needs a persisted, reviewed
  one-unit-per-member invariant or another deterministic aggregate substrate.

No unresolved P0, P1, P2, or P3 finding remains inside the 12-path carrier.
This verdict does not cover the concurrently generated scale-benchmark JSON
files or the later external vector-cache production edits, which belong to a
separate release-engineer lane. The live truth guard now rejects the shared
tree until that lane is isolated; this is the intended fail-closed behavior.

## Reviewed boundary

The independent review used:

```text
base:       dc60924f6c5486b8ba2b82dcecf22378bf043319
base tree:  2f1a6ababbd70ebc0106f750dc1b34d4b85fd5ca
branch:     codex/v0130-phase4-sprint4-synthesis
HEAD:       dc60924f6c5486b8ba2b82dcecf22378bf043319
versions:   0.12.0 / 0.12.0, unchanged
```

I reviewed the two changed production modules, their unit and HTTP guards, the
new count probe, the handoff truth guard, and all receipt-bound documentation.
MCP and OpenAPI production bytes are unchanged from the base. At the carrier
freeze and independent review, the protected SQLite scale implementation
`apps/api/src/alicebot_api/vnext_stores/sqlite/memory_access.py` was byte-equal
to the base, untouched by Sprint 4, and absent from the carrier allowlist. Its
current live-tree bytes are no longer equal because its separate owner lane
modified it after the freeze.

## Adversarial conclusions

1. The trace statistic is bounded and honestly named by its disclosed unit and
   basis. It reads only the already-fetched scoped FTS prefix, excludes roll-up
   cards, deduplicates by provenance group, slices at the disclosed positive
   cap, and reports saturation conservatively. Both `rows_examined` and
   `count` remain at or below `candidate_cap`, including for a legacy adapter
   returning more rows than requested.
2. The statistic is never promoted into an answer. It carries
   `is_answer=false` and `supports_numeric_sum=false`; no top-level
   `aggregation` field, MCP forwarding contract, or OpenAPI property was
   added. A strict FTS result or an accepted roll-up is still insufficient:
   one memory/member can encode several queried occurrences.
3. The unsafe intermediate design was fully removed. Equal cardinality or
   equal member identity does not qualify a count, and there is no new
   aggressive count-specific card promotion. The pre-Sprint generic
   card-promotion behavior remains unchanged.
4. Count recognition separates cardinality, occurrence frequency, cadence,
   and numeric-value shapes. Cadence recognition adds trace classification but
   preserves detector-off store calls, pool depth, diversity, card ranking,
   and selected order. Numeric-value and rejected gate-widening cases receive
   no candidate-row count.
5. The new probe passes the parsed benchmark question date as
   `reference_time`, uses gold only after retrieval for measurement, separates
   output modes, rejects empty/detector-only/partial audit manifests, and exits
   nonzero while answer sufficiency is unearned. The existing
   `coverage_probe.py` wall-clock limitation is disclosed rather than silently
   changed outside the brief's allowed eval scope.
6. Detector-`None` behavior remains byte-identical on the frozen 18-query
   corpus. Clause rows are still backfill rather than RRF inputs, and the
source pool is not deepened.
7. The receipt guard accepts only the precise root-level coverage.py fragment
   shape produced during pytest-cov subprocess collection, plus its named
   exact auxiliary files. Near-miss paths remain rejected. The real unit
   coverage posture passed with these transient fragments present.

## Independent verification

I independently ran and observed:

```text
focused coverage/retrieval/HTTP/probe: 297 passed
full unit pytest-cov posture:           3,837 passed, 80.415% coverage
14-router aggregate coverage floor:    PASS (>=45%)
LongMemEval all-file suite:             135 passed in 2.88s
handoff/receipt truth guard (frozen tree): 6 passed
flag-off default-surface smoke:           1 passed, nonzero execution enforced
Ruff touched-file lane:                 PASS
mypy changed production files:          PASS
release-static:                         PASS
  control-doc truth:                    PASS
  release_check.py:                     PASS at 0.12.0
  repository Ruff:                     PASS
  repository mypy:                     PASS, 224 source files
tracked carrier whitespace:             PASS
```

The legacy-on integration posture ran against the local role-separated
Postgres container: 401 passed, one skipped, and one ordering-sensitive live
SDK auth test failed with a 401. That exact test passed immediately in
isolation (1/1 in 1.52s). Neither the test nor its auth/server path is touched
by this carrier. I therefore treat it as an existing full-suite harness flake,
not a Sprint 4 source finding, but committed-SHA CI still must be green before
integration or release.

The final evidence artifacts exist locally and their hashes match the build
report. I also read their summaries directly:

- Roll-ups off: 74 questions, zero errors, 23/23 mechanism checks, 9/9 safety
  checks, 14/14 trace counts present, 0/14 matching dev gold, 0 reader
  aggregates, and 0/14 answer-sufficient.
- Roll-ups on: 74 questions, zero errors, 30 selected count-bearing cards
  overall and five on audited rows, but zero reader aggregates and 0/14
  answer-sufficient.
- Fixed 17: 14 trace counts and three numeric safe non-emissions; all 14 count
  values mismatch dev gold.
- Coverage: 172/172 rows, zero errors, 97.09% any coverage and 86.63% all
  coverage; the final summary hash equals the recorded before hash.
- Dormant corpus: before and final aggregate SHA-256 are both
  `6cbac3ca672e22bf41f6ee3d52fab8d6c8eba0543f41d67c3097cc668f734e63`.

## Receipt reconstruction and shared-tree isolation

I reconstructed the manifest independently from the explicit sorted 12-path
allowlist, file bytes, normalized modes, base, branch, and receipt format:

```text
format: alice-v0.13.0-phase4-sprint4-synthesis-explicit-carrier-v2
manifest bytes: 1887
sha256: b0f85fdaafcc2038f92162292b68374aa912f2e4df5ea766efb4faf1fbcfe840
```

This matched `BUILD_REPORT.md` and the truth guard on the frozen Sprint 4
tree. At the latest reviewer readback after that verification, the still-active
external lane had changed at least these source paths:

- `apps/api/src/alicebot_api/sqlite_schema.py` (modified)
- `apps/api/src/alicebot_api/vnext_stores/sqlite/embedding_cas.py` (modified)
- `apps/api/src/alicebot_api/vnext_stores/sqlite/memory_access.py` (modified)
- `apps/api/src/alicebot_api/vnext_stores/sqlite/memory_lifecycle.py` (modified)
- `apps/api/src/alicebot_api/vnext_stores/sqlite/vector_scan.py` (created)

This list is an illustrative current-at-readback snapshot, not an external-lane
allowlist or a guarantee that no more paths have changed. These five paths are
outside the explicit 12-path carrier, and the live guard now rejects the dirty
tree. I did not review, edit, hash, test, approve, or add any of them to the
Sprint 4 allowlist.

The report files are the only receipt-loop exclusions. The live scale-result
JSONs under `docs/benchmarks/scale/results/` are also explicitly disjoint
external outputs and were not approved by this review. Release engineering
must first isolate the external lane, rerun `git status`, the truth guard, and
receipt reconstruction, then stage the exact Sprint 4 paths; it must not use a
broad `git add` command in this shared tree.

## Handoff decision

The release engineer may integrate the safe diagnostic groundwork if that
partial infrastructure is desired. Integration must preserve the trace-only
boundary and rerun CI on the committed SHA. Sprint 4.2 itself remains open:
there is no earned benchmark uplift, reader-visible aggregate, held-out
acceptance result, release approval, or publication claim in this carrier.

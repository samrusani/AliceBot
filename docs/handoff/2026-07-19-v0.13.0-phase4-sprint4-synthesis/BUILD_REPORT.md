# Phase 4 Sprint 4 Build Report

## Verdict

The bounded code carrier is focused-green and ready for independent review.
**Sprint 4.2 benchmark closure is NO-GO:** the final safe design is trace-only
and produces 0/14 answer-sufficient audited count rows in both deterministic
development arms. No reader, MCP, or OpenAPI count surface ships.

```text
base:             dc60924f6c5486b8ba2b82dcecf22378bf043319
base tree:        2f1a6ababbd70ebc0106f750dc1b34d4b85fd5ca
branch:           codex/v0130-phase4-sprint4-synthesis
source versions:  0.12.0 (unchanged)
target carrier:   v0.13.0 Phase 4 integration, release-engineer owned
```

No model/paid call, full benchmark, held-out run, commit, stage, push, tag,
package build, publication, or repository-setting mutation was performed.

## Final deterministic count evidence

### Historical roll-ups-off arm

Command:

```bash
./.venv/bin/python eval/longmemeval/count_probe.py \
  --dataset-file eval/longmemeval/data/longmemeval_s_cleaned.json \
  --work-dir /private/tmp/alice-sprint4-stage1-work \
  --max-items 16 --workers 8 \
  --out /private/tmp/alice-sprint4-safe-count-rollups-off.jsonl
```

```text
exit:                              3 (intentional NO-GO)
questions:                         74
mechanism expectations:            23/23
safety expectations:                9/9
audited count rows:                 14
trace candidate counts:             14/14
trace counts matching dev gold:       0/14
reader aggregations:                  0
answer-sufficient rows:               0/14
cadence safe non-emissions:            3/3
numeric safe non-emissions:            3/3
rejected-widening non-emissions:       3/3
```

```text
JSONL sha256:  81972ba75923dcb60934c4624098695a352c99af2f5a3eab32dbe9e72739a88d
summary sha256: f8f50e95ca9bcd919d1ad9d9eb2608280045555e3750d2334d2e76ecb0fbcd5f
```

### Separate roll-ups-on arm

Command:

```bash
./.venv/bin/python eval/longmemeval/count_probe.py \
  --dataset-file eval/longmemeval/data/longmemeval_s_cleaned.json \
  --work-dir /private/tmp/alice-sprint4-count-rollups-on-work \
  --max-items 16 --workers 8 --accept-rollups \
  --out /private/tmp/alice-sprint4-safe-count-rollups-on.jsonl
```

```text
exit:                              3 (intentional NO-GO)
questions:                         74
mechanism expectations:            23/23
safety expectations:                9/9
selected count-bearing cards:       30 overall / 5 audited
reader aggregations:                 0
answer-sufficient rows:              0/14
```

Selected cards remain measurement only: no current roll-up field proves that
one member equals one queried unit.

```text
JSONL sha256:  bb7399ef3f036df59dac35693aef7a3eedf565fcbc9b81952ad47cb5727acee8
summary sha256: f06b3331d5a1678c3acf99df315fbec94cc3ce6602f9eb34d81bb38f3f09ec44
```

### Fixed 17-row before/final comparison

The pre-carrier artifact SHA-256 was
`06f5515d9ed8b888401addd5f0ff239576e35a99274ba426615d394bf1cff459`.
Final bytes disclose a trace count on all 14 audited cardinality/frequency
rows and safely emit none on three numeric rows. All 14 trace counts mismatch
dev gold and remain trace-only.

```text
final JSONL sha256:  583c316375471b91481259733cf1d5596aba9a2eb2fa8adb30d8f662831a4ac5
final summary sha256: b87d8093b82b47f637547ef76a3f12406bd52b4c5bf2825cc981dcde2de8fef6
```

## Coverage and dormant proofs

The final coverage probe completed 172/172 with zero errors:

```text
overall any/all:        97.1% / 86.6%
multi-session any/all:  98.3% / 78.3%
```

Before and final summary bytes are identical:

```text
summary sha256: e421840ee31a2eee3c7f5b1570ab9f3184dfd0204f5f05b2e55ad490502da478
final JSONL sha256: eb4e2a788a2ddd021b1fd27ee1a35495751224369a1a689f04b17a39ff7fe7f7
```

Caveat: the pre-existing `coverage_probe.py` path does not pass the
question-date `reference_time`; relative temporal phrases resolve against the
wall clock. The brief forbids altering existing LongMemEval files, so this
carrier fixes parity only in the new `count_probe.py` and discloses the
coverage-probe limitation rather than masking it.

The final dormant corpus rerun hashes full canonical packs for 18 fixed
detector-`None` questions, twice per query, with fixed UUID/trace/reference
clock. Before/final aggregate remains:

```text
6cbac3ca672e22bf41f6ee3d52fab8d6c8eba0543f41d67c3097cc668f734e63
```

Final dormant artifact SHA-256:
`e64fd0e58bba6566679a15909b16817088496438556dd5551332c5cdf4b2081a`.

## Local verification matrix

```text
focused coverage/retrieval/probe:                     206 passed
focused MCP/HTTP:                                    397 passed
pytest-cov full unit suite:                         3,837 passed
total coverage:                                       80.42%
14-router aggregate coverage floor:                   PASS
LongMemEval all-file suite:                            135 passed in 3.54s
legacy-on integration, role-separated Postgres:       401 passed / 1 skipped / 1 failed
isolated rerun of the integration failure:               1 passed
flag-off default-surface smoke + nonzero sentinel:        1 passed
Ruff touched-file lane:                                PASS
mypy production lane:                                  PASS (2 final production files)
release-static:                                        PASS (control truth, release_check, Ruff, mypy 224)
handoff/receipt truth guard at carrier freeze:            6 passed
tracked whitespace:                                    PASS
```

The legacy-on integration lane ran 403 cases against the correct role-separated
Alice Postgres service on port 15433. Its one SDK singleton-order failure passed
on an immediate isolated rerun (1/1), so it is recorded as a pre-existing,
order-dependent flake; the full integration lane is **not** reported green.
Earlier failures against port 5432 were an environment-target mismatch, not a
code failure. The flag-off smoke also proved its all-skipped protection by
asserting that a nonzero test count ran.

## Explicit carrier receipt

Format:
`alice-v0.13.0-phase4-sprint4-synthesis-explicit-carrier-v2`.

Receipt inputs are exactly these 12 paths:

```text
.gitignore
apps/api/src/alicebot_api/vnext_coverage_query.py
apps/api/src/alicebot_api/vnext_retrieval.py
docs/handoff/2026-07-19-v0.13.0-phase4-sprint4-synthesis/ENGINEER_HANDOFF.md
docs/handoff/2026-07-19-v0.13.0-phase4-sprint4-synthesis/FIX_MATRIX.md
docs/handoff/2026-07-19-v0.13.0-phase4-sprint4-synthesis/README.md
eval/longmemeval/count_probe.py
eval/longmemeval/test_count_probe.py
tests/unit/test_phase4_sprint4_handoff_truth.py
tests/unit/test_vnext_coverage_query.py
tests/unit/test_vnext_main.py
tests/unit/test_vnext_retrieval.py
```

Receipt-loop exclusions are exactly:

```text
docs/handoff/2026-07-19-v0.13.0-phase4-sprint4-synthesis/BUILD_REPORT.md
docs/handoff/2026-07-19-v0.13.0-phase4-sprint4-synthesis/REVIEW_REPORT.md
```

Receipt manifest bytes: `1887`.

carrier receipt sha256: `b0f85fdaafcc2038f92162292b68374aa912f2e4df5ea766efb4faf1fbcfe840`

## Concurrent external scale lane

A release-engineer process, not this builder, is concurrently running
`scripts/run_scale_benchmark.py --scales 1000,10000,100000 --backends sqlite,postgres`.
At receipt preparation, live readback showed these disjoint modified paths:

```text
docs/benchmarks/scale/results/postgres-1000.json
docs/benchmarks/scale/results/postgres-10000.json
docs/benchmarks/scale/results/postgres-100000.json
docs/benchmarks/scale/results/sqlite-1000.json
docs/benchmarks/scale/results/sqlite-10000.json
docs/benchmarks/scale/results/sqlite-100000.json
```

All six are external and are never carrier/receipt inputs. The truth guard also
permits only the exact auxiliary files `coverage.json` and `uv.lock`, plus
root-level coverage.py parallel fragments matching
`.coverage.<host>.pid<positive-pid>.X<6-alphanumeric-chars>x[.H<10-word-chars>h]`
while a test run is active; these transient auxiliaries are never
carrier/receipt inputs. It rejects every other unexpected dirty path. At the
Sprint 4 carrier freeze, the protected
`apps/api/src/alicebot_api/vnext_stores/sqlite/memory_access.py` was byte-equal
to the base and outside the carrier allowlist.

After the receipt and review bytes were frozen, a separate concurrent
vector-cache lane changed multiple SQLite source paths. At the latest
readback, examples included
`apps/api/src/alicebot_api/sqlite_schema.py` and
`apps/api/src/alicebot_api/vnext_stores/sqlite/embedding_cas.py`,
`apps/api/src/alicebot_api/vnext_stores/sqlite/memory_access.py`, and
`apps/api/src/alicebot_api/vnext_stores/sqlite/memory_lifecycle.py`, plus
`apps/api/src/alicebot_api/vnext_stores/sqlite/vector_scan.py`. The protected
file's current modification belongs to that owner lane, not Sprint 4. These
source paths are not owned by this carrier, are not receipt-listed or
whitelisted, and were not reviewed here. The live dirty-tree guard therefore
now fails closed on the unexpected paths, as designed. An exact recomputation
over only the fixed 12 Sprint 4 paths still yields receipt `b0f85fda...`, but
release engineering must resolve or isolate the external lane and rerun the
live guard before staging or committed-SHA CI. This handoff does not authorize
reverting, absorbing, or broadly staging those external changes.
Because that owner lane remains active, release engineering must use a fresh
`git status` rather than treating this snapshot as a complete staging
allowlist.

## External decision

Do not call this benchmark closure or spend the held-out acceptance run on the
trace-only design. A future answer design needs a persisted, reviewed
one-unit-per-member invariant or another deterministic aggregate substrate.

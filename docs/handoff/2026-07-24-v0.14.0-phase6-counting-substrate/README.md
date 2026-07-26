# Phase 6 Counting Substrate Handoff

## Verdict boundary

- **Code carrier:** **GO.** Independent review found no open P0, P1, or P2
  defect and no concrete code-level P3 finding on the frozen implementation
  candidate. All reproduced correctness findings were repaired with
  fail-on-old coverage. The protected PostgreSQL and SQLite
  `memory_access.py` files remain unchanged.
- **Phase 6:** **NO-GO.** The final governed development run executed 74/74
  selected cases with zero errors but remained **0/14** answer-sufficient
  against the unchanged **8/14** target. All 9/9 safety checks and 23/23
  mechanism expectations passed.
- **Release:** **NO-GO.** The count target is unmet. The repaired governed
  non-count run is green at 90/101 (`0.8911`) all-match against the required
  89/101 (`0.8812`). Committed-SHA CI, the owner-held 328-ID acceptance, paid
  calls, the full replicated benchmark, version/tag decisions, and publication
  remain release-engineer owned.
- **Carrier state:** intentionally uncommitted and unstaged on
  `codex/phase6-counting-substrate`.
- **Version state:** Python and web remain `0.14.0`; this carrier does not
  bump either source.

The carrier is based on commit
`a09c60c2fdb3b559cc3bf4099d457e79ede415cc`, tree
`f73cc2bc04b7d5cf5bf4c7afcd0225b356bf7ed3`. Immutable v0.10.x-v0.14.0
release records, prior handoffs, and benchmark records remain untouched.

The historical `stage1-150.txt` development manifest contains **172** unique
IDs, leaving an owner-held complement of **328**. That complement was not
enumerated or used to tune this carrier.

## What the code carrier delivers

- A forward-only five-table occurrence substrate for PostgreSQL and SQLite:
  `occurrence_coverage`, `occurrence_claims`, `occurrence_units`,
  `occurrence_evidence`, and `occurrence_extraction_dispositions`.
- One reviewed occurrence unit per countable real-world event, with identity
  established at write time and evidence authorized before counting.
- Deterministic capture/review accounting without guessed legacy backfill.
- Honest exact, range, and `at_least` aggregation; unavailable or incomplete
  proof stays dormant rather than becoming a false exact result.
- A count-intent read seam that uses reviewed units and authorized evidence,
  adds no query-time provider inference, and leaves existing public route,
  MCP, CLI, and operation counts unchanged.
- Governed count and non-count probes that keep questions, gold answers,
  `answer_session_ids`, and held-out IDs out of product behavior.

## Repaired invariants

The reviewed carrier closes all reproduced correctness findings:

- Claim/unit count-family checks, live-row locking, evidence rescan, and
  per-user graph serialization prevent cross-count links and concurrent
  retirement from stranding accepted evidence or claims.
- Source mutation, retitle, envelope re-establishment, terminal replay,
  supersession, and same-user portable restore preserve valid graph order and
  bind successor identity in receipts.
- Exact Python 3.12 `str.strip()` Unicode parity applies to evidence carriers
  and signed reviewer fields. Pure aggregation and bundled retrieval now
  reject the same blank or whitespace-only proof.
- SQLite occurrence reads fail closed when a caller-owned transaction already
  pins a snapshot; lifecycle time cannot be stamped from a newer view.
- Every occurrence graph mutation uses the universal per-user serialization
  boundary. Demo reset retires the graph before bulk lifecycle changes and
  invalidates affected dispositions before coverage, with one final coverage
  invalidation. Scheduler publication stages occurrence effects in the same
  transaction instead of exposing partially applied state.
- The retained legacy admission seam is now inside that same graph boundary.
  Metadata-only updates preserve valid reviewed occurrence materialization;
  fact-changing update, delete, and reactivation detach only the affected
  memory carrier, preserve shared claim/source support, clear stale active
  materialization, and roll back on reconciliation failure. Both top-level and
  nested source-chunk references invalidate dispositions before one coverage
  invalidation.

## Current reproduced evidence

- Full unit lane excluding the receipt-aware handoff truth module:
  **4,759 passed, 2 skipped**, branch coverage **79.44%**.
- Critical API/router aggregate coverage: **67.955701%**, above the **45%**
  floor.
- LongMemEval harness: **188 passed**; offline evidence checker: **7/7 arms**.
- API-source MyPy: **227 source files green**; global Ruff lint, compilation,
  source release check, and `git diff --check` are green.
- Uncommitted-tree distribution build: sdist and wheel built successfully,
  passed `twine check`, and passed `release_check.py --dist-dir` at `0.14.0`.
- Default-surface flag-off smoke: **2 passed** with nonzero execution.
- Full role-separated integration with legacy surfaces enabled:
  **426 passed, 1 skipped** in **857.56 seconds**.
- Legacy admission bridge: **213 focused unit tests** plus **7**
  role-separated/default-surface HTTP integration tests.
- Structural store-split guard: **51 passed**.

The final2 governed count probe completed as an intentional exit-3 NO-GO:
74 rows, zero errors, 0/14 against 8/14, provider-disabled and fresh-store
eligible, in 995.5 seconds. The repaired final2 governed coverage probe passed
after 101/101 with zero errors: overall any-match `0.9604`, overall all-match
`0.8911` (90/101), and multi-session any/all `0.9643`/`0.8571`.
Count JSONL/summary SHA-256 are
`40573245e3ea7329bc29f635b647231de67af1b18be493ed393a82db2e2c46c8`
and
`8f76e53a4cc0b4c9ed6577781730cf9b20368ce1409459737e75cccee9167b46`;
coverage JSONL/summary SHA-256 are
`16d243bf2986de0cb76aeb541e370c02efc96ca53add18a6e3be2e52aac22797`
and
`2de6d0c616b46cdefe64a74514641a8da758ae691e276c960474cb9ae94665d7`.

The canonical release-static MyPy lane still reports four inherited errors in
unchanged Phase 5 scripts:
`scripts/_phase5_ops_seed.py` and
`scripts/run_phase5_ops_evidence.py`. Those files are byte-identical to base
and outside the 71-path carrier; this handoff does not call that canonical lane
green.

The successful local distribution build is source-tree evidence only. It does
not replace reproducible committed-SHA artifact proof or release CI.

## Explicit proof boundaries

- Dormancy sentinels compare canonical sorted-JSON semantics. They do not yet
  establish raw serialized wire-byte identity.
- Redacted count receipts expose producer-validated shape and
  `receipt_valid`; their cryptographic inputs cannot be independently
  recomputed from the redacted artifact.
- PostgreSQL snapshot-capacity exhaustion fails closed by omitting the
  aggregation, but the current path emits no operator-visible log, event,
  metric, or trace reason. Observability remains a pre-release follow-up.
- PostgreSQL `vnext_stores/postgres/occurrences.py` is **4,100** lines while
  its SQLite peer is **3,979**. The structural `<4,000` target is therefore
  not met. This is disclosed nonblocking structural debt, not an open
  correctness finding; use a later behavior-preserving split if the cap
  remains governing.

## Why Phase 6 remains NO-GO

The final governed development run completed 74/74 selected cases with zero
execution errors but produced **0/14** answer-sufficient against the required
**8/14**. Its intentional exit 3 is a truthful Phase NO-GO, not a harness
failure.

The audited cases expose product-policy inputs that this structure-only
carrier does not manufacture:

- six unsupported semantic shapes;
- seven object-cardinality cases requiring independently reviewed stable
  object identities; and
- one event-instance case blocked by deliberately conservative predicate
  closure.

Question `bf659f65` also has a governed label/corpus conflict: gold says three
while the frozen source corpus supports two acquisitions. The owner must
ratify a correction or exclusion; code must not manufacture a third event.

The 8/14 target must not be lowered. Gold answers, question IDs, or
`answer_session_ids` must not become extraction, identity, review, or
retrieval inputs.

## Release and migration boundary

Do **not** deploy or apply migration 0095 from this NO-GO carrier. Existing
rows are not backfilled and cannot claim complete historical count coverage
merely because the migration ran. Durable public architecture,
known-limitations, backup/restore, and operator documentation remain a future
GO-carrier requirement.

The release engineer owns the 328-ID held-out acceptance, paid calls, full
replicated benchmark, committed-SHA CI, version decision, tag, and
publication.

## Package contents

- `DESIGN.md` records the five-table architecture and truth boundaries.
- `FIX_MATRIX.md` maps every carrier area to its repaired invariant and proof.
- `BUILD_REPORT.md` records the exact carrier scope, reproduced evidence, and
  final results and owner-held gate status.
- `ENGINEER_HANDOFF.md` gives the verification, receipt, and release sequence.
- `REVIEW_REPORT.md` remains reviewer-owned and outside the receipt loop.

The deterministic carrier receipt is frozen after the final evidence and
documentation update; its digest and serialized length are recorded in the
excluded `BUILD_REPORT.md`. Any later receipt-input edit invalidates that
digest and requires affected gates plus independent review to rerun.

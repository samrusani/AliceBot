# Phase 6 Counting Substrate Engineer Handoff

## Start here

- **Code carrier:** **GO.** Independent review found no open P0, P1, or P2
  defect and no concrete code-level P3 finding.
- **Phase 6:** **NO-GO.** The final governed development run executed 74/74
  selected cases with zero errors but remained **0/14** against the required
  **8/14**. All 9/9 safety checks and 23/23 mechanism expectations passed.
- **Release:** **NO-GO.** Repaired governed coverage is green at 90/101
  (`0.8911`) all-match against the 89/101 (`0.8812`) floor. The count target,
  committed-SHA CI, and all owner-held acceptance gates remain open.
- **Carrier:** intentionally uncommitted and unstaged on
  `codex/phase6-counting-substrate`.
- **Version:** Python and web remain `0.14.0`; do not re-bump them here.

Base commit:
`a09c60c2fdb3b559cc3bf4099d457e79ede415cc`

Base tree:
`f73cc2bc04b7d5cf5bf4c7afcd0225b356bf7ed3`

The deterministic receipt is frozen after final integration, governed eval,
and documentation evidence. Its digest and serialized length are recorded in
excluded `BUILD_REPORT.md`. Reviewer-owned `REVIEW_REPORT.md` must be authored
against those exact bytes and remains outside the receipt loop.

## What to verify

Migration 0095 adds five internal tables:

1. `occurrence_coverage`
2. `occurrence_claims`
3. `occurrence_units`
4. `occurrence_evidence`
5. `occurrence_extraction_dispositions`

One accepted occurrence unit is one reviewed real-world event. Claim
quantities, memories, sources, roll-up members, and query-time matches are not
event identity.

Review the carrier in this order:

1. Confirm PostgreSQL/SQLite schema parity, tenant keys, RLS/grants, no
   backfill, and import of pre-occurrence v0.14 exports.
2. Confirm identity binds scope plus the strongest event anchor and ordinal,
   while predicate/count-family facts are separately signed.
3. Confirm `new`, `link_existing`, and ambiguous review outcomes: only reviewed
   `new` materializes a unit; linking adds evidence without incrementing;
   ambiguity stays non-countable.
4. Confirm evidence authorization, chunk-parent/quote integrity, exact Python
   3.12 Unicode-strip parity, and matching pure/bundled validation.
5. Confirm the universal per-user graph boundary is acquired before
   decision-driving reads and covers capture, review, lifecycle, scheduler,
   demo reset, and retained legacy admission.
6. Confirm reconciliation locks and rescans live claims/units/evidence before
   retirement, preventing concurrent evidence from being stranded.
7. Confirm source retitle/envelope change, terminal replay, supersession,
   successor-bound receipts, staged same-user restore, source-title signing,
   and snapshot CAS.
8. Confirm demo reset orders graph reconciliation, bulk lifecycle mutation,
   disposition invalidation, then one coverage invalidation.
9. Confirm scheduler occurrence effects publish in the enclosing transaction.
10. Confirm legacy admission preserves valid reviewed materialization on
    metadata-only changes; fact-changing update/delete/reactivation detaches
    only the affected memory carrier, preserves shared support, clears stale
    active metadata, handles top-level and nested source-chunk references, and
    rolls back atomically on failure.
11. Confirm PostgreSQL uses a dedicated repeatable-read snapshot and SQLite
    fails occurrence aggregation closed inside a caller-owned active
    transaction.
12. Confirm exact/range/`at_least` honesty, entire-live-corpus accounting,
    relation-unknown and unresolved blockers, scope before limits, and
    saturation downgrade.
13. Confirm no new HTTP route, MCP tool, CLI command, or OpenAPI operation and
    no query-time provider inference.

## Current evidence

- Full unit excluding handoff truth: **4,759 passed, 2 skipped**, coverage
  **79.44%**.
- Critical API/router aggregate: **67.955701%**, floor **45%**.
- LongMemEval: **188 passed**; evidence checker: **7/7 arms**.
- API MyPy: **227 source files green**.
- Global Ruff lint, compilation, source release check, and
  `git diff --check`: green.
- Uncommitted-tree `uv build`: sdist and wheel produced; both passed
  `twine check` and the distribution release check at `0.14.0`.
- Default-surface flag-off smoke: **2 passed**, nonzero.
- Full role-separated integration with `ALICE_LEGACY_SURFACES=1`:
  **426 passed, 1 skipped** in **857.56 seconds**.
- Flag-off default-surface integration smoke with legacy/tool/key variables
  unset: **2/2 passed** in **6.63 seconds**.
- Legacy admission: **213 focused unit tests** and **7**
  role-separated/default HTTP integration tests.
- Structural store-split suite: **51 passed**.
- Governed count: fresh-store/provider-disabled, **74/74** executed, zero
  errors, **0/14** answer-sufficient, **9/9** safety, **23/23** mechanism
  expectations, intentional exit 3 in **995.5 seconds**.
- Governed non-count coverage: fresh/provider-disabled, **101/101** executed,
  zero errors; overall any `0.9604`, overall all `0.8911` (90/101), and multi
  any/all `0.9643`/`0.8571` all PASS.

Governed artifact hashes:

- count JSONL:
  `40573245e3ea7329bc29f635b647231de67af1b18be493ed393a82db2e2c46c8`
- count summary:
  `8f76e53a4cc0b4c9ed6577781730cf9b20368ce1409459737e75cccee9167b46`
- coverage JSONL:
  `16d243bf2986de0cb76aeb541e370c02efc96ca53add18a6e3be2e52aac22797`
- coverage summary:
  `2de6d0c616b46cdefe64a74514641a8da758ae691e276c960474cb9ae94665d7`

Control evidence:

- count input manifest:
  `cc93a902019a82401f1f9bffc5c9437b08d1e269da599e248d64a7980e67ef73`
- count executed selection:
  `c9cb95bb69101803bda974889c07e8ed0f1a498e234a6414f40fdc1ac45d3a2a`
- coverage input manifest:
  `c660317b20610f578087dc1042b5454eed871cd395c558333fd927637e1627f0`
- coverage dataset-order selection:
  `4647303d783fd622ec117d8996d4ba0f41729a02eb4953c7503c1bde4c366759`

Both probes report release-config eligibility, fresh stores, zero reuse, and
disabled vector/reranker providers. Their commands removed provider and
general API-key variables.

The canonical release-static MyPy command still has four inherited errors in
unchanged Phase 5 scripts:

- `scripts/_phase5_ops_seed.py`, lines 177-179
- `scripts/run_phase5_ops_evidence.py`, line 1058

Those files are byte-identical to base and outside the 71-path carrier. Do not
call the canonical lane green and do not attribute those failures to Phase 6.

The uncommitted-tree distribution artifacts were:

- sdist: SHA-256
  `88111d73466ce26b7aa2a805ff98d7ee2629ae0c392aae368dc6c9f5c6d74d56`,
  1,229,271 bytes;
- wheel: SHA-256
  `cbea4f10079c5f9fcfbf3a67e6e44654cc076a891fab28328cabba8ba2f34af3`,
  1,415,876 bytes.

Treat this as local source-tree build evidence, not committed-SHA
reproducibility or release evidence.

## Final local-evidence boundary

The bounded coverage repair and independent review are complete. Builder proof
passed 125 affected tests; reviewer proof passed 188 LongMemEval and 17 focused
provenance/dormancy tests with no P0-P3 finding. The final2 governed coverage
run is green. The final2 count run remains the honest Phase NO-GO.

Local integration, unit/coverage, static, eval, and package evidence is
recorded in `BUILD_REPORT.md`. The final local gate is independent
receipt/report verification, not another implementation change.

The exact-base non-count floors are:

- overall any/all: 0.9505 / 0.8812
- multi-session any/all: 0.9643 / 0.8571

The historical `stage1-150.txt` file contains **172** unique IDs; its
owner-held complement is **328**. The governed count target remains
**8/14**. The final governed result is **0/14**, so Phase 6 remains NO-GO.

Question `bf659f65` has a governed label/corpus conflict: gold says three while
the frozen source supports two acquisitions. The owner must ratify correction
or exclusion. Do not manufacture a third event, lower the gate, or use gold
answers/question IDs as product inputs.

## Proof boundaries to preserve

- Dormancy sentinels compare canonical sorted-JSON semantics, not raw
  serialized wire bytes.
- Redacted receipts expose producer-validated structure and `receipt_valid`,
  not enough inputs for independent cryptographic recomputation.
- PostgreSQL snapshot-capacity exhaustion fails closed without an
  operator-visible log, event, metric, or trace reason.
- PostgreSQL `occurrences.py` is 4,100 lines and SQLite is 3,979. The
  `<4,000` target is not met. Treat this as deferred nonblocking structural
  debt, not an open correctness defect; any later split must be
  behavior-preserving.
- Both protected `vnext_stores/*/memory_access.py` files remain unchanged.

## Receipt protocol

After all pending evidence is final and all builders are idle:

1. verify HEAD is still the recorded base and the branch is
   `codex/phase6-counting-substrate`;
2. confirm the index is empty and both version sources remain `0.14.0`;
3. compare the live dirty path set to the exact 71-path manifest in
   `BUILD_REPORT.md`, plus only the two presence-checked report exclusions;
4. build the standard length-prefixed receipt using the recorded format, base,
   tree, path, mode/kind, and content hashes;
5. write its serialized byte length and SHA-256 into `BUILD_REPORT.md`;
6. ask the independent reviewer to author and bind `REVIEW_REPORT.md` to the
   exact receipt bytes and preserve the exact phrase `Code carrier`;
7. after `REVIEW_REPORT.md` exists, run the full handoff truth guard;
8. if any receipt input changes, discard the digest and verdict, rerun affected
   gates, and repeat.

`BUILD_REPORT.md` and `REVIEW_REPORT.md` stay outside the receipt loop.
Everything else in the listed carrier is bound.

Leave the result unstaged and uncommitted for release-engineer verification.
Do not create a commit, pull request, merge, tag, or release.

Run `scripts/release_check.py` in source mode only. Do not use
`--tag v0.14.0`: the existing tag correctly points at the prior published
release, not these uncommitted bytes.

## Release-engineer-owned gates

Release engineering must:

- independently verify the 71-path manifest, receipt, build report, and
  reviewer report;
- reproduce full role-separated integration on the final bytes;
- run committed-SHA CI;
- run the 328-ID held-out acceptance once, after freeze;
- authorize any paid calls and run the full replicated benchmark;
- resolve the inherited release-static MyPy baseline truthfully;
- decide the version/tag; and
- publish only when Phase 6 and every release gate are green.

## Compatibility Impact

Migration 0095 adds five empty occurrence tables on both backends. Existing
rows are not backfilled and cannot claim complete historical occurrence
coverage merely because the migration ran. Existing route paths, operation
IDs, CLI commands, and MCP tool counts remain unchanged. A context pack gains
`aggregation` only when signed reviewed proof supports it.

## Rollback

Before integration, discard the uncommitted carrier and return to base
`a09c60c2fdb3b559cc3bf4099d457e79ede415cc`. After integration, revert the
carrier as one reviewed unit. Do not partially revert migration, persistence,
write reconciliation, retrieval, or eval controls.

Downgrading migration 0095 drops occurrence data. Do not use that destructive
schema downgrade on production without a separately reviewed retention plan.

## Operator Action

Do **not** deploy or apply migration 0095 from this NO-GO carrier.

A future GO carrier must update durable architecture, known-limitations,
backup/restore, and operator documentation. It must disclose unavailable
legacy history, signed exact-zero requirements, snapshot capacity, and
operator-visible failure observability. A missing aggregation is never itself
proof of exact zero.

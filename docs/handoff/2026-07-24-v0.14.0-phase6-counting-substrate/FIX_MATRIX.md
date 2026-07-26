# Phase 6 Counting Substrate Carrier Fix Matrix

This matrix describes the uncommitted carrier based on
`a09c60c2fdb3b559cc3bf4099d457e79ede415cc` (tree
`f73cc2bc04b7d5cf5bf4c7afcd0225b356bf7ed3`). Python and web remain
`0.14.0`.

**Code carrier: GO.** Independent review found no open P0, P1, or P2 defect
and no concrete code-level P3 finding. **Phase 6: NO-GO.** The final governed
development run completed 74/74 selected cases with zero errors but remained
**0/14** against **8/14**. **Release: NO-GO.** Repaired governed coverage is
green at 90/101 all-match against the 89/101 floor. Committed-SHA CI and the
owner-held gates remain open.

| Area | Required invariant | Fail-on-old or execution proof | Current status |
|---|---|---|---|
| Five-table schema | Add empty forward-only coverage, claim, unit, evidence, and extraction-disposition tables with PostgreSQL/SQLite parity, no legacy inference, tenant-safe keys, grants, and forced RLS. | Migration chain, SQL shape, constraints, grants/RLS, empty upgrade, downgrade, and paired schema tests. | **GO.** Schema and parity proofs pass; migration 0095 is not authorized for deployment while Phase/release are NO-GO. |
| Store seam | Keep reconstructible occurrence rows in paired modules and preserve façade/protocol signatures without touching protected memory-access carriers. | Store-split AST/signature/SQL manifests and structural suite. | **GO.** Structural suite: 51 passed. Both protected `memory_access.py` files are unchanged. |
| Write-time proposals | Create deterministic, idempotent proposals with separately signed predicate, exact scope, ordinals, event identity, and provenance; never sum claim quantity. | Repeated capture, plural events, false-positive, deterministic fallback, and no-gold-leak tests. | **GO.** No query-time provider inference or benchmark-specific input was introduced. |
| Review materialization | Only reviewed `new` proposals create units; `link_existing` adds evidence without incrementing; ambiguous remains non-countable. Evidence and reviewer text must satisfy exact Python 3.12 Unicode-strip parity. | Atomicity, carrier/chunk/quote, NBSP/U+001C, reviewer metadata, pure-aggregation/retrieval parity, and backend tests. | **GO.** Pure and bundled paths now reject the same whitespace-only proof. |
| Identity and reconciliation | Owning/resolving claims and units share signed `count_key`; graph mutations lock live rows and rescan before retirement. | Wrong-family helper/evidence/survivor tests, sequential races, and PostgreSQL two-connection races. | **GO.** Cross-count links and evidence/claim retirement races are closed. |
| Universal graph serialization | Every mutation enters one per-user graph boundary before decision-driving reads. | Paired lock-order, deterministic live PostgreSQL races, rollback, and façade tests. | **GO.** PostgreSQL advisory serialization and SQLite writer serialization cover capture, review, lifecycle, scheduler, reset, and legacy admission. |
| Lifecycle and source accounting | Corrections, rejection, undo, supersession, source mutation, deletion, redaction, and reactivation retire/rebuild atomically; receipts bind successors and current source snapshots. | Terminal replay, second retitle, supersession tamper, same-user staged restore, snapshot CAS, title-only mutation, disposition and coverage tests. | **GO.** Top-level and nested source-chunk references invalidate dispositions before one coverage invalidation. |
| Demo reset | Reconcile graph before bulk memory lifecycle mutation; invalidate dispositions before one final coverage invalidation. | Ordering, rollback, multi-chunk, and no-stale-count tests. | **GO.** Focused CLI/demo-reset proof is included in the carrier. |
| Scheduler staging | Keep scheduler-driven memory and occurrence publication in one transaction. | Fail-on-old partial-publish and rollback tests. | **GO.** No partially applied occurrence state is exposed. |
| Retained legacy admission | Put default legacy add/update/delete/no-op admissions inside the universal boundary. Preserve reviewed materialization for metadata-only edits; invalidate affected carriers for fact changes, deletion, and reactivation. | Direct-caller, default HTTP, role-separated PostgreSQL, shared-support, multi-chunk accounting, reactivation, and rollback tests. | **GO.** 213 focused unit tests plus 7 role-separated/default HTTP integration tests passed. |
| Portable import | Preserve valid same-user graphs with staged supersession restoration; reset all user-bound graph rows and receipts cross-user. | Exact roundtrip, predecessor-first restore, cross-user reset, collision, and pre-occurrence export tests. | **GO.** Receipt ownership and immediate self-FK ordering are closed. |
| Stable reads | PostgreSQL reads in a dedicated short repeatable-read snapshot; SQLite owns its occurrence snapshot and fails closed inside a pre-existing caller transaction. | Lifecycle-clock proof, caller-owned WAL race, cleanup, capacity, timeout, keyset, and saturation tests. | **GO.** A stale caller snapshot cannot earn a newer exact count. |
| Completeness | Exact only inside exhaustively reviewed entire-live-corpus coverage with no matching/unknown unresolved claim, relation-unknown accepted unit, legacy gap, or saturation. | Exact zero, range/`at_least`, unknown/partial coverage, stale carrier, unresolved, relation, and cap tests. | **GO.** Unavailable proof stays dormant. |
| Retrieval and dormancy | Activate only for count intent, authorize scope before limits, preserve existing provider behavior and dormant response semantics. | Exact/range/`at_least`, polarity, provenance, budget, provider parity, no-seam/unqualified, and context-pack tests. | **GO with disclosed proof boundary.** The final2 provider-disabled 101-ID corpus proof passed at 90/101; focused sentinels compare canonical sorted JSON semantics, while raw wire-byte proof remains outside their scope. |
| Public surfaces | Add no route, MCP tool, CLI command, or operation. Truthfully declare optional context-pack `aggregation`. | Exact 183 default / 232 gated HTTP operations and 11 core / 65 legacy MCP tools, schema validation, and default-surface smoke. | **GO.** Default-surface flag-off smoke ran 2 non-skipped tests. |
| Eval controls | Bind the canonical dataset, exact 172-ID and 101-ID manifests, `max_items=16`, disabled providers/roll-ups, and a unique absent work directory. Gold and held-out data remain measurement-only. | Harness, evidence checker, wrong path/limit/mode/reuse adversarial cases, and manifest/digest tests. | **GO.** LongMemEval 188 passed; evidence checker 7/7; both final2 governed runs were fresh, provider-disabled, and release-config eligible. |
| Full unit and coverage | Preserve repository floors on final carrier bytes. | Full unit excluding receipt chicken-and-egg plus critical router aggregate. | **GO.** 4,759 passed, 2 skipped; total 79.44%; critical API 67.955701% >= 45%. |
| Static gates | Ruff lint, API MyPy, compile, source release check, and diff hygiene. | Canonical commands and base-byte comparison for inherited failures. | **CARRIER GO.** API MyPy 227 files green; Ruff/compile/release check/diff green. Canonical release-static MyPy still has four inherited errors in two unchanged Phase 5 scripts. |
| Distribution build | Build wheel and sdist from the uncommitted carrier and validate metadata/content. | `uv build`, SHA-256/size, `twine check`, and `release_check.py --dist-dir`. | **UNCOMMITTED-TREE GO.** Both artifacts built and passed both validation lanes at 0.14.0. Committed-SHA reproducibility remains release-engineer owned. |
| Full integration | Run the role-separated legacy-enabled posture and force nonzero default-surface execution with legacy/tool/key environment variables unset. | Exact command, counts, skips, and duration. | **GO.** Role-separated integration passed 426 with 1 skip in 857.56s; flag-off default-surface smoke passed 2/2 in 6.63s. |
| Development count | Meet at least 8/14 answer-sufficient under the exact governed 172-ID invocation. | Fresh-store, disabled-provider, no-limit result with hashes and per-unit provenance. | **PHASE NO-GO.** Final2: 74 rows, 23 audited, zero errors in 995.5s; 0/14 answer-sufficient, 9/9 safety, and 23/23 mechanism expectations. JSONL/summary SHA-256: `40573245...46c8` / `8f76e53a...7b46`. |
| Frozen non-count coverage | Match or exceed exact-base floors on the checked-in 101-ID slice. | Fresh-store result and artifact hashes; overall any/all 0.9505/0.8812 and multi any/all 0.9643/0.8571. | **GO.** Repaired final2 ran 101/101 with zero errors, fresh/provider-disabled. Overall any 0.9604, overall all 0.8911 (90/101), and multi any/all 0.9643/0.8571 all PASS. JSONL/summary SHA-256: `16d243bf...2797` / `2de6d0c6...65d7`. |
| Structural size | Keep the Phase 3 `<4,000` goal visible without mixing a logic edit into the frozen carrier. | Source line-count report. | **DEFERRED NONBLOCKING DEBT.** PostgreSQL `occurrences.py` is 4,100 lines; SQLite is 3,979. No concrete code-level P3 finding remains. |
| Receipt freeze | Bind the exact 71 bytewise-sorted carrier paths while excluding only builder and reviewer reports from the loop. | Deterministic receipt reconstruction plus scope/index checks. | **FROZEN.** Exact digest and serialized length are recorded in excluded `BUILD_REPORT.md`; Phase remains NO-GO on count. |
| Independent review | Review implementation, tests, evidence, scope, dormancy, and final receipt. | Reviewer-authored report against exact frozen bytes. | **CODE REVIEW GO.** Final receipt-bound report remains reviewer-owned. |
| Owner-held acceptance | Keep the 328-ID complement, paid calls, full benchmark, committed-SHA CI, version cut, tag, and publication outside development. | One post-freeze owner run and later replicated benchmark. | **OPEN; RELEASE ENGINEER OWNED.** |

## Explicit boundaries

- The historical development filename says `stage1-150.txt`, but the checked-in
  file contains **172** IDs and the owner-held complement is **328**.
- Question `bf659f65` has a governed label/corpus conflict: gold says three
  while the frozen source supports two acquisitions. Owner correction or
  exclusion is required.
- No optional manual-resolution public contract is added. Ambiguous proposals
  remain non-countable.
- Redacted receipts are producer-validated and cannot be independently
  cryptographically recomputed from the redacted artifact.
- PostgreSQL snapshot-capacity exhaustion has no operator-visible signal yet.
- The local carrier receipt is frozen. No committed-SHA CI result, held-out
  result, paid/full benchmark, version bump, tag, publication, Phase 6 GO, or
  release GO is claimed.

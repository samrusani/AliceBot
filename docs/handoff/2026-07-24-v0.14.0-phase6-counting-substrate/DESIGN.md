# Phase 6 Counting Substrate Design

## Status and carrier boundary

This is the amended implementation design for Phase 6. The initial four-table
freeze was reopened after a fail-on-old proof showed that source persistence
alone cannot distinguish an exhaustively reviewed chunk from a chunk whose
events produced no memory or claim. The fifth internal table below records
that missing accounting fact. This document is not a code-carrier receipt,
benchmark result, release approval, or claim that Phase 6 is complete.

- Base commit:
  `a09c60c2fdb3b559cc3bf4099d457e79ede415cc`
- Base tree:
  `f73cc2bc04b7d5cf5bf4c7afcd0225b356bf7ed3`
- Governed version remains `0.14.0`; release engineering owns any later cut.
- The carrier remains uncommitted and unstaged. The deterministic receipt is
  frozen after final evidence; its digest is recorded in the excluded builder
  report.
- The **code carrier is independently GO**: no open P0, P1, or P2 defect and
  no concrete code-level P3 finding remains. Phase 6 and release remain
  **NO-GO** because the final governed development run remained **0/14**
  answer-sufficient against the required **8/14**. It executed 74/74 selected
  cases with zero errors and passed all 9 safety and 23 mechanism checks.
  Separately, the repaired governed non-count run completed 101/101 with zero
  errors and passed overall all-match at 90/101 (`0.8911`) against the frozen
  89/101 (`0.8812`) floor.
- The repaired invariant set includes lifecycle-clock and snapshot cleanup,
  Unicode evidence/reviewer validation, claim/unit `count_key` coupling,
  live-row reconciliation, valid supersession with successor-bound receipts,
  staged same-user restore, source-envelope re-establishment and title
  binding, analysis-to-persist snapshot CAS, and complete disposition
  accounting. Universal per-user graph serialization also covers demo reset,
  scheduler publication, and the retained legacy admission seam.
- The protected PostgreSQL and SQLite `memory_access.py` files remain
  unchanged. Full integration and fresh governed count/coverage reproduction
  remain evidence gates, not open code findings.
- Structural cap truth: PostgreSQL `occurrences.py` is 4,100 lines and its
  SQLite peer is 3,979, so the `<4,000` target is not met. This P3 debt is
  nonblocking structural debt and must not trigger logic edits now; no
  reviewer-confirmed code-level P3 defect remains. If the cap remains
  governing, use a later behavior-preserving split.
- Immutable release and benchmark records remain untouched.
- No paid model, held-out, or full-benchmark run is authorized in this carrier.
- No HTTP route, MCP tool, CLI command, or OpenAPI operation is added. A
  possible closed optional resolution arm on existing review contracts remains
  an owner decision and is not part of the current carrier.

## Mission

Build one reviewable occurrence unit per countable real-world event, with
identity established at write time. Reader-visible counts must be
reconstructible from accepted units and their authorized evidence. A memory
row, source row, roll-up member, claim quantity, or query-time text match is
never presumed to equal one occurrence.

The Phase 4 starting point remains 0/14 answer-sufficient audited count cases.
The fixed development file named `stage1-150.txt` currently contains **172**
question IDs; the manifest's owner-held complement is **328** IDs. The
owner-held complement remains excluded from development inputs and no
owner-held acceptance run has been performed; only its aggregate cardinality
is asserted from the manifest. Gold answers and `answer_session_ids` are
measurement-only and may not create, merge, classify, or review occurrence
data.

## Persisted model

Migration `0095` adds five empty, forward-only tables on PostgreSQL and the
matching SQLite bootstrap. It performs no legacy inference or backfill.

| Table | Purpose | Countability |
|---|---|---|
| `occurrence_coverage` | States whether history is unknown, forward-only, partially reviewed, or completely reviewed, including the covered interval. An absent row means unavailable coverage, not zero. | Controls completeness only; never summed. |
| `occurrence_claims` | Stores deterministic, idempotent write-time proposals and their `new`, `link_existing`, or `ambiguous` resolution. One claim may propose several ordinal units. | Never summed. |
| `occurrence_units` | Stores immutable occurrence identity, normalized count predicate, exact scope envelope, event-time evidence, review state, and `unit_value = 1`. | Only accepted, resolved, live units with reviewed evidence are countable. |
| `occurrence_evidence` | Many-to-many provenance between claims, units, memories, sources, chunks, quotes, and identity hints. | Evidence supports units; evidence rows never increment a count. |
| `occurrence_extraction_dispositions` | Stores the current source-chunk snapshot and extractor-version accounting result: accepted occurrences, unresolved claims, or a reviewed no-occurrence decision. The receipt binds the tenant, source/chunk, snapshot, extractor, disposition, referenced claims/units, and review version. | Never summed. Complete-history qualification requires every current chunk to have a current, valid, exhaustively validated reviewed disposition. A reviewed `complete_with_unresolved_claims` disposition may qualify the corpus; matching or unknown unresolved predicates still block exactness, while signed closure-complete predicates proved disjoint do not. |

All lifecycle and disposition review decisions are appended to the existing
`event_log`. The disposition table is a CAS-protected current-snapshot
materialization, not a replacement audit log: later correction, rejection,
forgetting, source-envelope change, or new in-range capture invalidates its
review and the affected completeness qualification before a replacement
decision can be signed. Expected event families cover claim
creation/resolution, evidence attachment, unit acceptance/rejection,
ambiguity, supersession, retirement, disposition review/invalidation, and
coverage updates.

PostgreSQL and SQLite land together with equivalent constraints, row shapes,
store seams, user scoping, lifecycle guards, portable backup handling, and
upgrade behavior. Existing v0.14 SQLite exports must remain importable as
stores with no occurrence coverage.

Same-user portable restore must preserve a valid occurrence graph. Cross-user
import must reset or omit the entire occurrence graph because its accepted
claims, units, evidence, coverage, and receipts are user-bound; rewriting row
ownership alone cannot preserve signature truth. The onramp now resets
coverage, claims, units, evidence, dispositions, review states, and receipts
across users while preserving same-user exact restore; independent review
reproduced valid receipt rebuilding after re-review.

## Write, review, and lifecycle

Capture and consolidation may generate occurrence proposals, but cannot make
an occurrence countable by text inference alone. The deterministic path must
always exist. The occurrence path adds no provider or model inference during
retrieval or pack compilation. Existing embedding and reranker behavior
remains unchanged and is verified by provider-call parity tests.

Each proposal carries:

- a deterministic idempotency key;
- a normalized count predicate;
- a proposed `new`, `link_existing`, or `ambiguous` resolution;
- the strongest available event-time or external identity anchor;
- the exact project, domain, and sensitivity envelope;
- evidence references and provenance digests;
- one or more explicit ordinals when a reviewed claim describes multiple
  independently identified events.

The existing memory and source review actions carry unambiguous proposal and
source-disposition decisions. No new review route or tool is added. Memory
acceptance invokes one internal atomic occurrence-reconciliation seam:

- reviewed, unambiguous `new` proposals materialize accepted units;
- reviewed `link_existing` proposals attach evidence without incrementing the
  count;
- ambiguous proposals remain unresolved and non-countable;
- failure of truth-critical materialization fails the transaction rather than
  being swallowed as best-effort indexing.

The current public review request does not accept a reviewer-supplied manual
occurrence identity for an ambiguous proposal. A minimal closed
`occurrence_resolution` object on the existing memory-review request and
existing `alice_memory_correct` tool has been proposed but requires owner
approval before any contract edit. Unless approved, ambiguous proposals remain
unresolved and non-countable. That fail-closed limitation may reduce the
attainable count-probe result, but it cannot be replaced with automatic or
benchmark-specific guessing.

Capture, inline confirmation, auto-commit, edit-and-approve, consolidation,
correction, rejection, undo, supersession, source deletion, and redaction use
the same lifecycle seam. Accepted state is not rewritten into a contradictory
state. CAS-protected append-only decisions retire or supersede units/evidence
so stale data cannot remain countable.

All graph mutations serialize on one per-user boundary. PostgreSQL uses the
same advisory-lock namespace for every participating path; SQLite uses the
paired writer boundary. The lock is acquired before reading the graph state
that drives mutation. Reconciliation locks and rescans claims, units, and
evidence before retirement or transition, so a concurrent evidence attachment
cannot be stranded on a retired unit.

Demo reset first reconciles the occurrence graph, then applies bulk lifecycle
changes, then invalidates referenced extraction dispositions, and finally
invalidates coverage exactly once. Scheduler publication stages occurrence
effects inside the enclosing transaction. Neither path may publish a partially
applied occurrence state.

The retained legacy memory-admission path also enters this boundary before its
source/profile/existing-memory reads. Metadata-only updates preserve reviewed
occurrence materialization. Fact-changing update, deletion, and reactivation
detach only the affected memory carrier, preserve independently supported
claims and units, clear stale active materialization, invalidate both
top-level and nested source-chunk dispositions, and invalidate coverage once.
Any reconciliation failure rolls back the legacy mutation and its occurrence
effects together.

Independent focused review closes the previously proved lifecycle gaps. A
valid same-semantics supersession may change the event-instance
`member_identity` while a changed identity basis remains rejected.
Source-envelope edits now transactionally retire the old graph, update the
source, re-establish every chunk under the new envelope, and only then
optionally review the rebuilt state.

Evidence signing is stricter than row presence. An evidence row must carry a
reader-authorizable `memory_id` or `source_id`; a chunk or quote alone cannot
authorize it. The stores validate the chunk-parent relation, exact
Python-3.12 `str.strip()` Unicode whitespace parity, and quote/hash equality.
At review, evidence may authorize a unit only through the unit's owner claim
or an accepted, resolved `link_existing` claim for that same unit. PostgreSQL
and SQLite enforce the same rules and receipt inputs.

## Identity and provenance-aware deduplication

Occurrence identity and predicate compatibility are deliberately separate. The
`occurrence-unit-v1` identity key binds the exact domain, sensitivity,
project-scope envelope, strongest identity basis and anchor, and claim ordinal.
It does **not** include the normalized count predicate. The predicate is signed
in the claim and unit facts and is checked independently when an existing
identity is considered for linking. A same-anchor candidate with an
incompatible predicate remains ambiguous rather than silently creating or
merging an event.

The unit and every claim authorized to own or resolve it must also have the
same signed `count_key`. Paired composite foreign keys plus create, link,
review, replay, and serve-time guards enforce that compatibility. Independent
focused review closes the previously reproduced wrong-family path.

The strongest scope-compatible identity anchor is selected in descending order:

1. a connector or external event ID;
2. an explicit event time or bounded interval plus stable actors/object;
3. a reviewed date-and-ordinal or reviewed manual identity.

Prose alone and ingestion time are never identity anchors. Repeated evidence
for the same strongly anchored event links to one unit. Text-identical events
with distinct strong anchors remain separate units. Weak or conflicting
identity stays ambiguous; it is never silently merged or separated.

Automatic deduplication is allowed only inside identical scope identities.
Cross-project, cross-domain, or incompatible-sensitivity candidates go to
review. Sensitivity may only become more restrictive. Every surfaced evidence
reference must pass the same authorization envelope as its unit and the
request.

## Completeness and honest answer shapes

An exact count requires all of the following:

- the requested interval is wholly inside exhaustively reviewed coverage;
- all matching accepted units are returned without saturation;
- no matching unresolved or ambiguous claim remains;
- no accepted scoped unit has an unknown predicate relation to the query;
- every unit has at least one authorized, live, reviewed evidence link;
- no legacy or otherwise uncovered evidence can affect the answer.

Complete-history qualification signs the store's **entire current live source
corpus**, not a caller-selected or benchmark-selected source subset. It requires
a current reviewed disposition for every current chunk at the qualified
extractor version, with exact source/chunk accounting. Disposition receipts are
recomputed, not shape-checked. Missing sources, missing or extra claim/unit
references, stale snapshots or envelopes, malformed references, unreviewed
no-occurrence decisions, and matching-or-unknown unresolved predicates prevent
exactness. A mixed accepted-plus-unresolved chunk is not automatically
incomplete: its reviewed `complete_with_unresolved_claims` disposition can
qualify the corpus, and signed closure-complete unresolved predicates proved
disjoint from the query do not block exactness.

Every source field that can affect extraction or a reviewed no-occurrence
decision is included in the signed source snapshot. Source title is normalized
with exact Python 3.12 Unicode-strip parity and bound into paired snapshot rows
and digests, so title-only edits stale prior proof.

Analysis and persistence are CAS-bound as well. The writer obtains title,
chunk text, and the snapshot digest from one joined accounting row, uses that
same row for the no-occurrence guard, and forwards the exact 64-hex digest as
the expected snapshot. Both stores re-read and compare before any mutation.
A mutation before that comparison rejects the write; a mutation afterward
leaves the older signed digest stale under review and accounting
recomputation. Missing or malformed signed carriers fail closed.

Otherwise the result is an honest range or `at_least` value with
`upper_bound: null` when the upper bound is unknown. Existing memories receive
no guessed occurrence rows. A migrated but unqualified store therefore never
turns "no occurrence data" into an exact zero. A signed exact zero **is**
supported when complete reviewed whole-corpus accounting exists and there are
no matching units, no matching-or-unknown unresolved claims, and no accepted
scoped unit whose predicate relation to the query is unknown. Natural
predicates deliberately have incomplete closure, so an unrelated accepted
natural event can conservatively suppress exact zero or another aggregation
until its nonrelation is proved.

The 14 audited cases include shapes beyond historical discrete events,
including current subscriptions, recurring classes, service types, and
pending pickup/return items. Unsupported shapes remain explicitly incomplete
or unavailable; the carrier must not force them into occurrence units to meet
the majority gate.

## Retrieval contract and dormancy

Only cardinality and occurrence-frequency intents activate occurrence
retrieval. The reader uses a dedicated, scope-filtered occurrence search over
the complete matching substrate; it does not count only the top-N selected
memories or infer identity at query time. Scope filters apply before limits.

When the occurrence proof contract is supportable, the context pack may add one
`aggregation` record. This includes a signed exact zero under complete reviewed
accounting; matching accepted units are not required for that exact-zero case.
The record contains:

- `answer_kind`: `exact`, `range`, or `at_least`;
- `lower_bound`, nullable `upper_bound`, and `count` only when exact;
- accepted occurrence-unit IDs;
- evidence references grouped per unit;
- coverage, unresolved-claim, legacy-coverage, and saturation disclosure.

The existing Phase 4 candidate-memory statistic remains diagnostic and cannot
be promoted into an answer. Counts are reconstructed from unit rows, not from
claim quantities, roll-up member counts, or SQL `COUNT(*)` without evidence.

PostgreSQL reconstructs each aggregation inside a dedicated short-lived
repeatable-read, read-only connection. It copies the parent request's tenant
identity, uses a bounded connection timeout, and restores the normal request
connection before existing embedding or reranker work. A process-local
nonblocking semaphore allows at most two simultaneous occurrence snapshots;
capacity exhaustion fails closed instead of waiting, locking tables, or
returning an unearned exact result. In the current carrier the exception is
caught and the aggregation is silently omitted, preserving the existing pack
bytes. No operator-visible log, event, metric, or trace reason is emitted.
Observability is therefore a required follow-up before release.

SQLite starts and owns a read transaction only when the caller does not
already own one. If a caller-owned transaction is already active, occurrence
aggregation fails closed instead of joining a potentially stale WAL snapshot;
the caller's transaction and ordinary memory result remain untouched. The
request `as_of` value is the event/reference clock used to derive the requested
occurrence window. The snapshot proof supplies one separate aware UTC
lifecycle clock for paged units, evidence, and unresolved claims. PostgreSQL
obtains the clock from the database transaction's `transaction_timestamp()`;
SQLite anchors it to the snapshot the occurrence reader owns. The reader
strictly validates that proof and has no application-host-clock fallback.
Coverage and full-corpus accounting are read in that same database snapshot
and are not filtered by the request's event clock.

Units, evidence, and unresolved claims use bounded keyset pagination. Scope and
resource authorization are applied before limits. Hitting a materialization
cap, observing a page discontinuity, or failing to authorize any required
evidence marks the aggregation incomplete and prevents exactness.

The dormancy requirement is byte-level:

- a non-count query is unchanged even when occurrence data exists;
- a count query against a store without occurrence methods is unchanged;
- a count query against an unqualified migrated store with no usable occurrence
  proof is unchanged;
- no dormant pack gains a key, trace field, warning, budget allocation,
  ranking change, or MCP field.

Current focused sentinels establish canonical sorted-JSON semantic equality,
not raw serialized wire-byte identity. They are necessary but not sufficient
proof of the requirement; the final frozen 101-ID corpus comparison remains
required.

## Validation plan

Free validation must cover:

1. migration chain, all five tables, constraints, RLS/grants, empty legacy
   upgrade, and no backfill;
2. PostgreSQL/SQLite schema, store-signature, SQL-shape, transaction, CAS,
   concurrency, row-shape, redaction, and portable backup parity;
3. duplicate cross-session evidence, text-identical distinct events,
   ambiguous identity, plural claims, correction, rejection, undo,
   supersession, redaction, and disposition invalidation/re-review;
4. scope-before-limit behavior and rejection of scope-leaking evidence;
5. exact/range/`at_least` contracts with evidence-bearing provenance;
6. all three dormant byte-identity cases;
7. unchanged surface closures: 183 default and 232 gated HTTP operations,
   and 11 core and 65 legacy MCP tools;
8. the keyless count probe moving from 0/14 to a strict majority
   (at least 8/14) answer-sufficient, with real generated proposals and
   per-unit provenance;
9. the frozen 101-ID detector-negative non-count comparison with no regression;
   the other 71 IDs in the 172-ID development slice are detector-positive and
   are governed separately;
10. the repository's normal unit, integration, lint, type, migration,
    contract, and documentation truth gates.

The final governed development run completed 74/74 selected cases with zero
execution errors but produced **0/14** answer-sufficient against the required
**8/14**. All 9/9 safety checks and 23/23 mechanism expectations passed; the
intentional exit 3 records an unmet product gate. The unresolved design inputs
are reviewed stable object-member identity, a
separately governed predicate/morphology closure policy, and owner disposition
of the `bf659f65` label/corpus conflict.

The custom fourteen-ID invocation is diagnostic. Count release eligibility
requires the exact checked-in 172-ID development path, ordered manifest digest
`cc93a902019a82401f1f9bffc5c9437b08d1e269da599e248d64a7980e67ef73`,
no limit, and disabled providers. Only that invocation activates the exact
23-question audit manifest, including nine safety cases and fourteen
answer-sufficiency cases. Coverage release eligibility similarly requires the
exact checked-in 101-ID path, ordered digest
`c660317b20610f578087dc1042b5454eed871cd395c558333fd927637e1627f0`,
no limit, and disabled vector/reranker modes. Missing requested IDs fail as
configuration errors, coverage uses the question-date reference clock, and
both summaries disclose requested/selected manifest counts and digests,
provider/reranker modes, and release-gate eligibility. Custom, limited, or
provider-enabled runs remain diagnostic.

The repaired final2 fresh governed non-count run completed 101/101 with zero
errors and passed its release gate. Overall any-match `0.9604`, overall
all-match `0.8911` (90/101), multi-session any-match `0.9643`, and
multi-session all-match `0.8571` all met their frozen floors.

Release eligibility also binds the canonical dataset path and full SHA-256,
`max_items = 16`, disabled count roll-ups, and fresh-store status. Independent
adversarial review confirmed that copied datasets, wrong `max_items`, enabled
roll-ups, and reused stores all remain diagnostic exit 3.

Eval store reuse is also bounded: existing markers do not bind later
post-ingest SQLite content, so final evidence must use fresh stores or
explicitly invalidate and rebuild reused stores. Redacted count receipts are
validated by the producer for shape and `receipt_valid`; the probe cannot
independently recompute their cryptographic inputs after redaction and must not
claim that stronger proof.

For release evidence, “fresh” means a unique work directory that did not
previously exist. Reused or missing stores are deliberately diagnostic exit 3
and cannot support a release verdict.

The 328-ID held-out complement, full replicated benchmark, paid model/judge
calls, committed-SHA CI, release cut, tag, and publication remain
release-engineer-owned gates after a future completion carrier is frozen and
independently reviewed.

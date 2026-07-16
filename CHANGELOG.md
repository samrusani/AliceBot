# Changelog

## Unreleased

## v0.11.1 — 2026-07-16

- **Default-surface release coverage.** CI now boots the default PostgreSQL
  surface with every legacy/agent-key mount flag absent and exercises the core
  bootstrap, capture, recall, resume, context-pack, and review round trip. The
  exact job name is part of the repository's required-check contract.
- **Stable public failures.** Surviving HTTP, MCP, CLI, and onramp failures,
  plus migrated provider, response, scheduler, evaluation, doctor, and
  connector diagnostics, return stable error codes and static messages while
  keeping private exception detail in server-side logs. Intentional legacy-on
  `proxy_execution.py` business-result reasons remain dynamic and are
  explicitly excluded from this diagnostic migration. Closed OpenAPI contracts
  describe the machine-readable error envelope.
- **Store and replay parity.** The `list_memories(query=...)` and
  `list_resume_memory_events(query=...)` legs used by recent decisions and
  resume now share the open-loop ASCII case-insensitive literal-substring
  contract across PostgreSQL, SQLite, and test fakes; generic
  `search_memories` and `alice_recall` FTS/websearch semantics are unchanged.
  Terminal project-update replay uses target-filtered, indexed event lookups
  instead of full event-log scans, and both accept and reject fail closed when
  their mandatory memory identity is absent.
- **Coupled project-update integrity.** Generic review/correct/forget adapters
  cannot strand a pending project-update candidate. Authorized true redaction
  scrubs the terminal artifact, free-text quality feedback, provenance quotes,
  memory, revisions, and coupled events to exact content-free skeletons
  without undoing already-applied project state. Source and source-chunk
  evidence remains unchanged because it may support other memories.
- **Defensive schema and test truth.** Forward migrations add bounded
  project-update event lookup support, explicit CPython whitespace/domain
  normalization, and fail-closed redaction triggers. Store fakes no longer
  swallow unknown filters, the development dependencies declare the coverage
  feature floor, and release/workflow shape checks cover previously implicit
  contracts.
- **Smaller runtime and pinned automation.** Dead response-generation wrappers
  were removed around the retained provider invocation path. Checkout and
  CodeQL actions use evaluated immutable pins; incompatible major dependency
  proposals remain deferred instead of being folded into this patch carrier.
- **Release-process truth.** The Node 20/pnpm 10 advisory wrapper remains the
  documented fail-closed dependency-audit path. The removed rate-limiter and
  already-landed Phase 1 directory/documentation riders are recorded as
  re-measured closures rather than recreated work.

## v0.11.0 — 2026-07-15

- **Phase-1 product boundary.** The default runtime is narrowed to Alice's
  eleven-tool agent interface and retrieval/memory-quality core. Telegram,
  hosted administration/design-partner and hosted identity/device surfaces,
  chief-of-staff/chat/model-pack features, and the public `/v0/responses` chat
  endpoint are
  removed with their HTTP, MCP, CLI, scheduler, web, OpenAPI, and surface-test
  registrations. Low-level response jobs/provider invocation remain as internal
  durability machinery for `/v1/runtime/invoke`. Historical migrations remain
  immutable and inert.
- **Fail-closed legacy mount.** Task, approval, execution, Gmail, and Calendar
  compatibility surfaces are unmounted by default and require the explicit
  `ALICE_LEGACY_SURFACES=1` local-operator flag. Retained long-tail memory MCP
  tools require `ALICE_MCP_LEGACY_TOOLS=1`; exactly the three task-brief tools
  require both flags. All legacy tools remain unavailable to key-bound servers.
- **Identity and documentation reconciliation.** Architecture, rules, product,
  roadmap, current-state, sprint, connector, and release documentation now
  describe the post-cut local-first boundary. Repair-batch ledgers are archived
  under `docs/handoff/history/`, the v0.10.4 truth receipt no longer silently
  deactivates or pins future production code, and OCR/transcription wording now
  says Alice ingests externally extracted text rather than executing either
  model class.
- **API truth.** The OpenAPI operation registry is regenerated for the post-cut
  mounted surface while preserving exact closure and phantom-key rejection.

## v0.10.4 — 2026-07-15

- **Deterministic embedding CAS whitespace.** PostgreSQL now computes the
  signed memory-embedding content digest with the same explicit CPython 3.12
  29-codepoint `str.strip()` character table used by Python and migration
  `0090`, rather than the locale-dependent POSIX `[[:space:]]` class. This
  closes NBSP-class and U+001C–U+001F disagreement without changing blank
  omission, first-occurrence field deduplication, LF joining, or SHA-256.
  Fail-on-old SQL-shape coverage binds vector freshness, signed update CAS,
  and missing-embedding selection to that table; live role-separated
  PostgreSQL covers NBSP, U+001C, mixed blank fields, no re-embed loop, and
  signed vector participation.
- **Capture identity integrity.** Source capture now validates the resolved
  source envelope and classification on fast-key, content-hash, and atomic
  dedupe paths. SQLite and PostgreSQL update stale dedupe keys together with
  scope, domain, sensitivity, raw-text, and content-hash changes; a collision
  fails closed, and the source-review HTTP transaction rolls back before its
  public `409` response.
- **Key-bound explanation isolation.** Core MCP `alice_explain` now authorizes
  the requested memory and each expanded predecessor, successor, provenance
  source, entity backing memory, and continuity object before returning an
  explanation. Missing, malformed, or mixed-scope evidence returns one generic
  unavailable response without leaking identifiers; keyless local legacy
  behavior and the existing key-bound legacy-tool disablement stay unchanged.
- **Scoped legacy reads.** The legacy MCP `alice_vnext_context_tree` tool
  propagates the effective project set through five resource groups (projects,
  memories, sources, open loops, and artifacts), applies source-aware
  predicates before row limits, and emits admitted target-specific events as a
  separate event group. The tool remains outside the core MCP surface and is
  disabled on key-bound servers. Core open-loop lists and resume lookup also
  apply project scope before bounded limits and fetch events only for admitted
  targets.
- **Project-scope scalar parity.** Python, SQLite, PostgreSQL, and migration
  `0090` canonicalize finite mathematically integral JSON numbers, including
  signed zero, and reject fractional or non-finite numeric values. The
  established explicit JSON `true`/`false` scalar identifiers remain
  supported; objects and null do not become project identifiers.
- **Terminal project-update evidence binding.** Terminal replay now requires
  `project.update_candidate_created` evidence whose distinct target set is
  exactly the locked artifact. Ordinary events must carry the exact candidate
  ID; authorized true redaction admits only the exact content-free skeleton.
  Repeated evidence for that same target remains valid, while any other target
  fails closed.
- **Protected-path and freeze truth.** The release-engineer handoff includes a
  completed, copy-ready Upgrade Overview for the touched memory-schema and
  continuity-API areas. Executable guard and control-document regressions bind
  that metadata and distinguish Repair Batches 8 through 12's
  twice-reproduced historical fingerprints and changes-required reviews,
  Repair Batch 13's unfrozen parity correction, Repair Batch 14's frozen
  review-rejected carrier, and the current Repair Batch 15 verification and
  independent-review boundary.
- **Terminal project-update consistency.** Before returning an idempotent
  accepted or rejected project-update artifact, the coupled review service now
  proves the locked terminal artifact against exactly one append-only
  `project_update_review` revision and exactly one total accepted/rejected
  decision event coupled to that artifact or candidate. The service counts all
  coupled decision events before checking expected outcome, actor, action,
  target, payload, or redaction form, so duplicate or contradictory evidence
  cannot hide behind a valid event. The proof deliberately does not treat
  mutable current memory or project state as historical evidence, so later
  corrections, undo/forget, later accepted project updates, and authorized
  true redaction do not invalidate a genuine decision. True redaction retains
  only the exact revision/event linkage skeleton needed for replay. Fabricated
  or contradictory terminal states fail closed with the fixed repair
  instruction and zero mutation through all six generic/dedicated HTTP, MCP,
  and CLI adapters; valid accepted and rejected outcomes remain idempotent.
- **Persisted-source project isolation.** SQLite and PostgreSQL source and
  parent-chunk searches, every post-admission retrieval source path, Brain,
  Projects, Connections, Contradictions, and HTTP artifact-trace authorization
  now resolve the complete persisted source metadata envelope. Root canonical
  scope remains authoritative, followed by canonical scope in embedded
  `metadata_json` then `scope_json`, nested agentic/identity canonical scope,
  and aliases only after canonical absence. PostgreSQL runtime predicates and
  migration `0090` choose that nested tier by key presence, not by whether a
  value produces a nonempty identifier. A present blank, null, malformed, or
  fractional nested value therefore cannot fall through to a stale alias; a
  valid scalar or array still normalizes normally, and both nested containers
  merge in the same order as Python and SQLite. A stale outer alias plus
  embedded `[]` is visible nowhere; the same stale alias plus embedded
  `[real]` is visible only to `real`. Strings, integers, finite mathematically
  integral JSON numbers, and the established explicit boolean scalar values
  retain backend parity. Fractional/non-finite numbers, mappings, and null are
  excluded.
- **Resume query truth.** `alice_resume.query` now filters open-loop title,
  description, next-action metadata, and relevant event payload text in both
  SQLite and PostgreSQL before row or event limits. Scoped and unscoped
  queries cannot be starved by newer mismatching loops or events; queryless
  behavior and the policy-resolved project scope remain unchanged. Event
  payload matching recursively inspects string leaf values only; JSON keys,
  numeric/boolean/null values, and serialization punctuation cannot match.
  The MCP unit fake applies the same rule to each leaf independently, so a
  query cannot be synthesized by concatenating separate array/object leaves.
  Open-loop row fields and loop-event leaves use ASCII case-insensitive literal
  substring semantics across SQLite, PostgreSQL, and the fake: non-ASCII code
  points are exact with no Unicode normalization, and `%`, `_`, and `\\` are
  literal query characters rather than SQL wildcards. Root and nested
  open-loop `next_action` metadata participates as a row field only when the
  JSON value is a string; numbers, objects, and arrays are not serialized into
  row-search candidates. The fake returns matching open loops in production
  order: `opened_at`, then `created_at`, then `id`, all descending.
- **API contract correction.** The v0.10.4 remediation replaces permissive
  phantom response wrappers with contracts derived from the actual handler
  envelopes, including the complete scheduler-status payload. Its fail-on-old
  regression invokes the actual endpoint handler and validates the serialized
  13-field payload against the generated required, closed schema, including
  phantom-key rejection. This prospectively corrects the
  v0.10.3 release notes' overbroad claim that all 294 OpenAPI operations were
  source-verified; the immutable v0.10.3 historical record is not rewritten.
- **Publication and release-operability truth.** Package metadata now uses an
  evergreen PyPI description instead of tag-time release-status prose from the
  repository README, while active docs, release-note links, install tags, and
  checksum pointers identify the same published baseline. The clean-SHA gate
  now requires brand-new empty distribution and reproducibility directories,
  passed explicitly without deleting or reusing user-owned artifacts.
- **Upgrade preflight.** Operator guidance now identifies duplicate
  idempotency groups that can block migrations `0087` and `0089`, defines a
  backup-first survivor/loser repair process, and verifies all three unique
  indexes after retry.
- **Future upgrade scope preservation.** The candidate source intended for
  v0.10.4 corrects migration `0083` so legacy project scope is promoted only
  when the canonical key is absent and only the six supported ASCII
  whitespace characters normalize. Source-dedupe repair now follows the full
  presence-aware legacy resolver in SQLite and PostgreSQL. Present empty,
  null, malformed, and nonempty values remain authoritative through an
  `0082`→head upgrade. Migration `0090` separately normalizes preserved source
  raw text with newline normalization plus CPython 3.12's explicit,
  locale-independent 29-codepoint `str.strip()` table; live NBSP, NEL, and EM
  SPACE recapture proves that no duplicate source is created. The v0.10.3 tag
  and artifacts remain unchanged; already-erased intent still requires
  external evidence.
- **Trace partial-outage truth.** Trace detail and ordered events now load in
  the same wave but compose independently. A successful leg remains visible
  when its peer fails, and each leg reports live, fixture, or unavailable
  provenance instead of inheriting a successful list request's origin.

## v0.10.3 — 2026-07-14

Remediates the fourth external audit's confirmed findings on the published
`v0.10.2` baseline: 13 release-blocking correctness, reliability, scale, and
release-process defects, their independent-review correction passes, and the
final punch-list. `v0.10.2` remains sound and published; this release carries
the fixes forward. Migrations `0087`–`0089` apply online-safe persistence
indexes, durable response jobs with provider revision/fingerprint CAS, and
graph-edge workflow idempotency.

- **Project isolation.** Agent project scope now flows through brain,
  connection, contradiction, and project-automation requests, scheduler
  workflows, and store queries; consolidation clusters partition by project
  scope (accepting a cross-project proposal is rejected), and an explicitly
  empty `project_scope: []` suppresses every legacy fallback.
- **Consolidation dedup.** Accepting a dedup proposal now retires every
  cluster member — including the survivor — into exactly one active
  representative; legacy proposals are repaired on acceptance, so no
  `supersedes` edge points at an active row.
- **Review coherence.** Artifact promotion creates its memory target
  atomically or fails; a locked transition table makes terminal states
  final; accepted project updates cannot later be rejected (enforced on the
  dedicated, generic HTTP, and MCP review surfaces); resolved confirmations
  leave the pending queue.
- **Retrieval fidelity.** Inferred query domains are disclosure-only ranking
  hints (word-boundary matched) and can no longer filter out correctly
  tagged results; caller-supplied domains remain authoritative. Scoped
  contradiction, recent-change, and temporal stages push predicates into the
  store or deepen fail-closed instead of truncating at 200 rows; chunk
  ranking dedupes by parent source before limiting.
- **ChatGPT import.** A real conversation parser preserves message order via
  the mapping graph, roles, timestamps (branch-aware), and one source per
  conversation with stable identity.
- **Reliability.** Best-effort embedding persistence and read-only grounding
  probes contain store failures instead of failing the enclosing operation;
  scheduler claims are per-user with fenced durable leases, stable process
  ownership identity, nonzero failure exits, and `--once` propagation;
  response generation uses durable jobs with mandatory idempotency keys so
  retries cannot duplicate provider charges; provider, embedding, Telegram,
  and import work no longer holds open database transactions.
- **Scale.** Workspace and trace reads are bounded with authoritative
  counts; content-hash capture dedupe is indexed; embeddings run outside
  transactions; PostgreSQL access uses a connection pool.
- **Release and gate integrity.** Publication is draft-first and
  transactional across GitHub and PyPI with exact-byte recovery modes that
  verify tag/version consistency; the publish gate audits live branch
  protection; control-document truth distinguishes published from candidate
  versions against structured release records; Python coverage is attributed
  to the canonical package with a per-file floor for `main.py`, and web
  coverage floors rose with per-file minimums; OpenAPI success contracts are
  per-operation and source-verified.

## v0.10.2 — 2026-07-13

Supersedes the tagged-but-unpublished `v0.10.1` candidate, whose publish
workflow installed the package after the step that validates the semantic-eval
attestation, so `release_check` could not import `alicebot_api` and the publish
job failed closed before uploading anything. All `v0.10.1` remediation is
carried forward.

- Fixed the PyPI publish workflow to install release dependencies before the
  release-check steps that import first-party modules, so the credential-free
  semantic-eval attestation validation runs against the installed package.

## v0.10.1 — 2026-07-13

Supersedes the tagged-but-unpublished `v0.10.0` candidate, whose protected
semantic release gate failed on a query-interpretation defect. All `v0.10.0`
remediation is carried forward; this release closes the gate failure.

- Fixed semantic retrieval for business budget queries: the ambiguous word
  `money` no longer creates an implicit hard `personal`-domain filter, restoring
  signed-vector participation while explicit caller-supplied domains remain
  strict.
- Fixed semantic release aggregation and attestation to apply each suite's
  declared targets instead of requiring perfect per-case recall; diagnostic
  misses remain counted, while skips, missing vector participation, and failed
  target checks still fail closed.

## v0.10.0 — 2026-07-13

Security, reliability, and quality release. Remediates every finding from the
third external audit of `v0.9.4` — fixed at the class level — and clears the P2
backlog.

- Correctness: one signed-vector write contract across the eval seeder and both
  backfill paths (fixes the v0.9.4 backfill regression); scope/status/domain/
  sensitivity-aware atomic capture dedupe (migration `0085`); people/time
  predicates pushed into the store with bulk entity-edge resolution and one
  query embed per request; supersession cycle guard fails closed on pre-existing
  cycles and dangling pointers (migration `0086` repairs 3+ duplicate pointers;
  `0084` unchanged); roll-up cards report authoritative totals with disclosed
  truncation; release eval measures signed vector participation and fails closed
  on skipped suites; supersession advisory lock acquired before row locks.
- Hardening: `pgvector 0.8+` enforced at install/migration/doctor; import/backup
  validate-race closed with bounded memory; web decomposition with real-browser,
  accessibility, coverage, and bundle-budget gates and zero TypeScript errors;
  clean first-party Python mypy; portable packaged-README links; structured
  exact-SHA release-control attestation plus a protected signed-vector semantic
  report required for publication.
- Upgrade: `alembic upgrade head` applies `0085`/`0086`; run `alicebot vnext
  memories backfill-embeddings` after upgrade to re-embed under the
  correctly-signed v2 signature (now retrievable).
- Published migration `20260712_0084` remains immutable; new idempotent
  migration `20260713_0086` carries the 3+ duplicate retry/confirmation
  pointer repair for databases already stamped at the released 0084 state.

## v0.9.4 — 2026-07-12

`v0.9.3` was an internal security-hotfix candidate; a follow-up external audit
returned NO-GO, so it was withdrawn and never published. `v0.9.4` supersedes
it and attempted the original five fixes plus all nine P1 remediations from the
second audit. A post-publication third audit found partial fixes and regressions.
The later published v0.10.2 corrective record superseded the historical
v0.10.0 remediation matrix.

- Lifecycle correctness: all memory lifecycle mutations (confirm, review, correct, undo, forget, expire/unexpire, supersession) route through one central transition table (`vnext_lifecycle`) that rejects invalid transitions — a rejected or superseded row can no longer be confirmed back to active, `correct()` no longer promotes rows while leaving them unconfirmed/review-required, supersession `A → B → A` cycles are blocked, and `unexpire` cannot report active while the row stays stale.
- Supersession graph mutation is serialized per user with a transaction-scoped advisory lock, and the cycle guard now fails closed when it cannot verify acyclicity within its hop bound — so concurrent supersessions on disjoint row pairs can no longer each pass an unlocked check and together close a cycle (audit 2 P1 #1).
- Expire/unexpire lock the row before policy evaluation, so a concurrent correction or supersession can no longer be overwritten by a stale snapshot.
- Migration `20260712_0084`: corrects the migration-`0083` bug where retry/confirmation identifiers could be stranded on a deleted tombstone; dedup now prefers the active row, and 0084 repairs databases already mis-upgraded by v0.9.2. `0083` is left unchanged.
- Content dedupe is now scope-aware: the content hash folds in the project scope, so identical text captured under a different project keeps its own scoped source and candidate instead of being silently skipped; browser-clip and agent-output proposals now propagate project scope (audit 2 P1 #2).
- Hard people/time retrieval filters deepen the ranked scan (bounded) until enough scoped rows survive, so a valid row ranked behind a full decoy window — including time-window scopes — is still surfaced (audit 2 P1 #3).
- Embedding signatures now include an endpoint fingerprint, so two endpoints sharing a provider/model label but serving different coordinate spaces are never pooled or ranked against each other (audit 2 P1 #4).
- Consolidation and semantic roll-ups determine embedding presence by an exact read of the selected row IDs instead of a global nearest-neighbor probe, so embedded rows are no longer missed when unrelated neighbors dominate (audit 2 P1 #5).
- Roll-up cards persist their full authoritative membership rather than the truncated display subset, so a group larger than the per-card instance cap no longer re-proposes a revision on every run (audit 2 P1 #6).
- Filtered PostgreSQL vector search enables iterative HNSW scan, so lifecycle/scope/signature filters no longer silently under-return valid rows (audit 2 P1 #7).
- The canonical release eval runs with `--release-gate`: a run that never exercises the vector stage reports `pass_fts_only` and exits non-zero, and eval failure now propagates to the process exit code, so the gate cannot be green without measuring semantic retrieval quality (audit 2 P1 #8).
- Release finalization in v0.9.4 attempted a prose-based premature-publication
  check. The v0.10.0 repair replaces that bypassable phrase logic with one
  strictly positioned structured publication/checksum declaration.

**Upgrade:** `alembic upgrade head` applies migration `0084` (idempotent). Because embedding signatures gained an endpoint fingerprint, run `alicebot vnext memories backfill-embeddings` after upgrade to re-embed existing vectors under the new signature; until then those rows fall back to full-text retrieval.

## v0.9.2 — 2026-07-11

- Release hardening for the `v0.9.2` candidate: project-bound agent keys now inherit scope on omitted reads; every lifecycle mutation authorizes the persisted target and locked review targets are rechecked; all 70 `/v0/vnext` routes authenticate centrally and routes without resource-aware policy fail closed for scoped or restricted keys; key-bound MCP exposes only the policy-complete core surface; read-only and proposal-only profiles cannot mutate memory.
- Data integrity hardening: versioned and checksummed SQLite backup/restore with atomic secure files and tamper/collision defenses; safe data-bearing 0067 upgrades; new 0083 uniqueness and derived-edge invariants; content edits refresh derived state; stale consolidation acceptance is rejected.
- Retrieval and performance hardening: hard project/person/time filters across context sections, service-authoritative request caps and honest serialized-budget disclosure, embedding compatibility signatures plus reindex recovery, and consolidation capped at 2,000 memories / 1,999,000 logical comparisons with bounded float32 blocks instead of a dense similarity matrix.
- Release engineering: patched web dependencies and live/fixture write gates; packaged Alembic and eval resources; exact wheel/sdist installation smokes; exact-SHA required-check enforcement; one-build checksum-preserving PyPI publication; candidate, backup/restore, upgrade, rollback, and security-note documentation.

- Currency chains: packs render same-slot update sequences as explicit chains — stale values labeled `[SUPERSEDED as of <date>]`, the current value labeled and positioned last — built from supersession edges and value-shape matching with collision-safe gates (ambiguous groups emit nothing, disclosed in traces); approved supersessions now stamp the retired row's `valid_to`.
- Temporal precompute: dated pack items carry ISO-8601 timestamps and a bounded `[derived]` block precomputes date deltas, durations, and ordinals against the request's reference time — readers copy arithmetic instead of computing it.
- `--pack-format=json`: an optional structured-record context format (same content as prose, fingerprint-disclosed) following the benchmark authors' reading-format ablation; prose remains the byte-identical default.
- Judge-free stale-pick metric (`eval/longmemeval/stale_pick.py`): programmatic detection of superseded-value answers, replayable over any checkpoint; plus the published honesty kit (docs/benchmarks/longmemeval/HONESTY-KIT.md) — judge protocol, config fingerprints, our negative results as first-class findings, and a reproduction pledge.
- Benchmark evidence correction (no new score claim): seven committed candidate checkpoints on the 172-question development slice range from -14 to +3 net flips against the historical 79.4% run, with no statistically significant improvement. The 86.6% FTS-only and 95.3% vector session-coverage probes were not a paired scored experiment, so the report no longer claims that they prove a retrieval ceiling or a reader bottleneck. The published 79.4% result remains a single historical run.

- Semantic roll-up grouping: when embeddings are configured, a third grouping tier clusters anchor-less same-topic memories through cohesive all-pairs cosine admission with a deterministic blockwise silhouette-chosen threshold — "faucet, toaster, shelves" becomes one "kitchen" card; fully dormant without a provider (byte-identical, tested on real stores).
- Aggregation queries now rank accepted roll-up cards above their own member memories (gated on aggregation intent, ≥2 slotted members, 2-card cap, members retained as receipts below; disclosed as card_promotions in traces).
- Disclosed reranker stage (`ALICE_RERANKER_*` env): provider-side listwise precision scoring of the fused candidate head before slot spend; reorders but never shrinks, fails open to fusion order, dormant unconfigured, generic sha-pinned scoring prompt.

- Roll-up proposal quality overhaul: structural label hygiene (pronoun/contraction/closed-class/light-verb heads never title cards), store-measured generic-anchor detection (frequency-derived per store, no hardcoded topic list), broken-subspan label repair ("Us Part II" → "The Last of Us Part II") applied to card titles and instance lines, a group-utility gate (groups must aggregate distinct values or sessions with a coherent, specific label — failures are dropped, not proposed), utility-ranked proposals under the cap, and topic-shaped card titles with dominant value units. Measured on aggregation-heavy stores: junk-label rate 34% → 0%, instance-line defects 13% → 0%, with review proposals now reading as human-recognizable topics.

- Deterministic retrieval ordering: every equal-score tie (RRF fusion, graph and temporal stages, FTS/vector stage runs) now resolves through a content-stable cascade (event date, content length, text, capture fingerprint) instead of falling through to row ids — re-ingesting the same content yields byte-identical packs (two-seed divergence 7/40 → 0/40); disclosed as `fusion.tie_break: content_stable_v1` in retrieval traces.
- Benchmark harness gains a disclosed `--accept-rollups` step (default off, fingerprint-stamped) that review-accepts consolidation roll-up proposals through the real acceptance path, modeling the product's human review workflow; offline measurement found current roll-up grouping quality too noisy to help the benchmark, so the flag stays off and grouping quality is queued as product work.
- Grounding for products: the context-pack entity note now recognizes quantity-qualified and possessive compound entities ("30-gallon tank", "my snake plant") with conservative false-positive guards, and a new answer-verification library seam (`vnext_answer_verification`) lets integrators opt into post-generation grounding checks; nothing changes by default.

- Time-aware retrieval: temporal anchors parsed from the query ("two weeks ago", "in March 2023", "between X and Y") join RRF fusion as one more ranked list against event dates — never a hard filter, dormant on date-free queries, honest `temporal_anchor` trace stage.
- Coverage mode for aggregation-shaped recall ("how many…", "list every…"): query-surface intent gate, capped clause decomposition, and instance-diversity fusion keyed on `(source_id, source_chunk_id)` so distinct instances fill the slots; dormant path byte-identical.
- Consolidation roll-up cards: the merge engine proposes review-gated cards that pre-aggregate same-topic instances with per-instance dates, values, and speaker provenance; accepted cards are first-class recallable memories, members stay individually recallable, nothing auto-promotes, zero added commit-path work.
- Fact-augmented retrieval keys (migration `20260707_0082`): derived category/attribute keys indexed at low weight on both backends so category-phrased queries match instance memories; deterministic tier always on, optional model tier behind the provider seam; identifier-shaped attributes excluded from derivation.
- Entity-grounding honesty note: context packs state "no stored memories mention X" when a salient query entity has zero corpus support — a retrieval statistic, only present when true.
- Supersession validity annotations: pack items carry compact validity metadata (valid-from/to, superseded-by, corrected-at) and the current version of a corrected fact always ranks above its superseded ancestor.
- Speaker-provenance capture: memories record USER vs ASSISTANT origin; user-asserted values win promotion-rank tie-breaks; memory cards label "you said" vs "assistant suggested"; cross-batch duplicate promotions deduped.
- Query-anchored excerpts in the benchmark packer: excerpt windows center on the query's best-matching line (gated on enumeration shape, with upward+downward run extensions) instead of chunk heads.
- Disclosed post-generation grounding gate for the benchmark harness (`--verify-grounding`, off by default, fingerprint-stamped): a separate judge-neutral pass converts answers whose load-bearing claims lack context support into abstentions; fail-open, both texts recorded.
- Benchmark checkpoint rows now record pack provenance (retrieved session ids, memory ids, context digest) so paired flips are attributable offline.
- Published LongMemEval result unchanged at 79.4%: the paired 172-question slice measures this release at parity (+1 net, p=1.0) with per-type movement (temporal +2, multi-session +1, abstention +1, knowledge-update/preference −1 each); the round-2 features ship for their product value with no new benchmark claim.

## v0.9.1 — 2026-07-07

- Retrieval bug fix: the sources stage was content-blind (matched only titles/metadata with a broken stopword list, effectively returning the most-recent sessions); it is now RRF fusion over chunk-level full-text hits, provenance of winning memories, and title/recency — plus an FTS OR-fallback when strict AND finds nothing.
- Excerpt packing guarantees each retrieved source its best chunk before spending the remaining budget, rendered in session-timestamp order.
- Migration `20260707_0081`: content search index over source chunks (Postgres stored generated tsvector + GIN; SQLite external-content FTS5 with automatic backfill at bootstrap).
- LongMemEval_s: **79.4%** (397/500, single run 2026-07-07) vs the 64.6% baseline, paired on the same 500 questions (net +74, McNemar p = 3.26e-12); every question type improved, multi-session 45.1% → 58.6%. Config disclosed: official chain-of-thought reading template, 16 items / 24k-char context (was standard / 8 / 12k).
- Known trade-off disclosed: the abstention subset regressed 25/30 → 22/30 — the CoT reading style makes the model more willing to answer when the memory lacks the fact.

## v0.9.0 — 2026-07-06

- Completed the Memory Operations Protocol — all ten verbs are real: `merge` via consolidation-candidate acceptance that executes member supersessions in one audited action; `expire`/`unexpire` riding the read-path validity exclusion; and true `redact` — content expunged from memories, revisions, and event payloads through a narrowly trigger-guarded redaction mode (append-only stays the default posture; the audit skeleton and a redaction proof-trail survive; migration `20260706_0079`). All wired across MCP (`alice_memory_manage`), HTTP, and CLI with policy vocabulary (redact and consolidation-acceptance require human or admin).
- Context API v2: per-section token allocation in the budget report, five packing strategies (`balanced`/`facts_first`/`recent_first`/`contradictions_first`/`sources_first`), and deterministic depth tiers (`minimal`/`low`/`medium`/`high` — no tier performs model synthesis); tri-state include flags let tier defaults breathe; the default agent loop docs now center one context call.
- Complete export/import round-trip: export now covers all nine record types (entities, edges, revisions, provenance, and chunks were previously dropped); `alice-memory import` preserves ids and timestamps exactly, never overwrites, and is all-or-nothing.
- Published the scale envelope (`docs/benchmarks/scale/`): SQLite commits flat at 2.3-2.4ms through 100k memories after this benchmark caught and fixed an O(N) idempotency scan (3.5s before versus 2.4ms after at 100k, about 1,460x); Postgres ~20ms commits and ~400ms recall at 100k; honest SQLite-with-embeddings boundary documented.
- Entity-extraction hygiene after a LongMemEval diagnostic: bare capitalized spans no longer default to `person` (positive evidence required), long-text repeat thresholds and confidence-ranked caps stop conversational noise flooding; extraction rule + confidence recorded per entity for future re-typing.
- LongMemEval documentation: three-run variance disclosure (≈64%, band 63.0–64.6), the disclosed negative result on entity-graph retrieval for multi-session, and a breadth ablation (49.2% multi-session at 2× context) motivating the planned aggregation mode.

- Temporal graph memory + entity resolution (Sprint D): a generic `vnext_entities` substrate with canonicalization, aliases, mention windows, and append-only relationship history (migration `20260705_0078`); deterministic entity extraction (capitalized spans, acronyms, handles, domains, repeat-thresholds, blocklist — no LLM) linking sources at capture and memories at acceptance on every acceptance path; entity-hop graph retrieval fused into RRF as a third stage with full trace honesty; a belief-evolution timeline in `alice_explain`; and two new eval suites — `entity_resolution` and `graph_hop_retrieval` — where the graph mechanism proves recall 1.0 on entity-only queries that lexical search scores 0.0 on.

### Pre-launch fixes

- Human-direct memory commits no longer require an agent identity via MCP.
- SQLite MCP server bootstraps the user row automatically (`python -m` path) with clearer integrity-error messages.
- Full-text recall falls back to OR-matching when strict AND finds nothing (the trace shows the fallback).
- CLI gains `--version`, friendly errors for sqlite URLs and bad UUIDs, and lists all six eval suites.
- Docs overhaul: pip/uvx install is the primary quickstart, the eleven-core-tool count is corrected everywhere, self-host role bootstrap SQL is documented, and PyPI metadata is completed.

## v0.8.0 — 2026-07-05

- Published Alice's first benchmark result: **64.6% on LongMemEval_s** with the official judge protocol, in the same range as the best published results in the category — full methodology, per-question evidence, and reproduction script in `docs/benchmarks/longmemeval/`.
- Real memory scopes: `project_id`, `created_by_agent_id`, and `run_id` columns on memories (backfilled from metadata, migration `20260704_0076`); scope filters through both store backends, the context compiler, and the `alice_recall`/`alice_context_pack` tools; agent API keys can bind a project scope — bound identities may narrow but never widen it, with escalations rejected and audited.
- Consolidation that actually consolidates: embedding-based near-duplicate clustering (cohesive complete-link admission, blockwise, bounded, and logged) produces merge/dedup candidate memories through the existing review gate — model-backed merges are grounding-gated with structured refusals, the deterministic path never fabricates text, supersession is never automatic, and reinforced preferences spanning ≥3 sources/days are surfaced for review.
- Temporal slice: graph edges carry real event time (`observed_at`/`valid_from` from source timestamps, migration `20260704_0077`); supersession pointers are first-class columns with metadata backfill; both stores answer as-of edge queries; `alice_explain` returns the full supersession chain (cycle-safe, both directions); the SQLite on-ramp gains the graph substrate.

- Context packs enforce `max_tokens` with greedy budget packing and report `{token_budget, token_estimate, truncated, dropped_item_count}`; the `projects` retrieval filter is honored; contradictions and recent changes are populated from real services; the dead `historical_timeline` section is removed and pack rows are no longer duplicated across sections.
- Typed retrieval: `memory_types` filtering through both store backends and the `alice_recall`/`alice_context_pack` tools; a procedures section joins beliefs/decisions in packs; `Procedure:`/`Playbook:`/`How to` and `Happened:`/`Log:` capture rules produce procedure and episode memories.
- Staleness v1: expired facts (`valid_to < now`) are excluded from search by default; `stale` is a first-class memory status; confirmations refresh `last_confirmed_at` (idempotent replays); a daily `staleness_sweep` scheduler workflow marks expired and unconfirmed volatile memories for review — marks only, never deletes (migration `20260704_0075`).
- The agentic write protocol joins the core MCP surface: `alice_memory_commit` (policy-checked explicit writes) and `alice_memory_manage` (confirm/undo/forget) — 11 core tools, every parameter described; the Memory Operations Protocol is documented in `docs/memory-operations-protocol.md` with honest boundaries (forget is soft-delete pending redaction; merge/expire planned).
- Three memory-quality eval suites join `retrieval_quality`: `correction_suppression` (superseded/rejected memories must vanish from recall with complete audit trails), `decision_recovery`, and `provenance_explanation` — all run live on both backends, all can genuinely fail.
- LongMemEval harness under `eval/longmemeval/`: dataset fetcher (cleaned 2025-09 release), per-question isolated Alice stores running the real capture/retrieval pipeline, official generation/judge prompts ported verbatim, checkpoint/resume runner. Scored runs need a model endpoint (`ALICE_LME_*` env vars).

## v0.7.0 — 2026-07-04

- Added the zero-infrastructure SQLite on-ramp: `alice-memory mcp --data-dir ~/.alice` starts the MCP server against a local SQLite file with no Docker or Postgres — nine core tools, FTS5 full-text search (porter stemming), optional embedding-based vector search (numpy cosine), and review through `alice_memory_review`/`alice_memory_correct`. `alice-memory export` dumps memories, sources, open loops, and events as JSONL.
- In SQLite mode, `alice_resume`, `alice_recent_decisions`, `alice_memory_review`, and `alice_memory_correct` are served by vNext-native implementations (the legacy continuity engine remains Postgres-only); legacy long-tail tools report an informative error instead of crashing.
- The `retrieval_quality` eval suite accepts `sqlite:///` URLs in `ALICEBOT_EVAL_DATABASE_URL`, labels reports with the backend, and is now CI-runnable with zero services (verified: lexical recall@1 = 1.0 through the production pipeline at ~0.7 ms median per query).
- `alicebot_api.__version__` now derives from installed package metadata instead of a hardcoded string (was stale at 0.5.1).

## v0.6.0 — 2026-07-04

- Rebuilt memory retrieval as real hybrid search: Postgres full-text + pgvector (HNSW) fused with reciprocal-rank fusion, an OpenAI-compatible embedding provider seam (Ollama/LM Studio/OpenAI), write-time embedding with graceful FTS-only degradation, and contradiction sync moved out of the read path.
- Consolidated the MCP surface to 9 core tools with parameter descriptions on every schema and compact outputs; the legacy long tail (65 tools) remains behind `ALICE_MCP_LEGACY_TOOLS=1`.
- Added real agent authentication: per-agent API keys (`alice_sk_*`, hashed at rest, RLS-scoped) enforced across all vNext HTTP agent endpoints and optionally on MCP via `ALICE_AGENT_API_KEY`; payloads can no longer self-escalate `permission_profile`.
- Replaced the closed-loop vNext eval suites with an honest `retrieval_quality` benchmark that seeds a live store and can genuinely fail; reports mark suites `skipped` without a database instead of fabricating passes.
- Repositioned the project as "the continuity layer for AI agents": rewrote README/control docs, archived 43 internal process docs, and documented the `alice-memory` PyPI naming decision (`alice-core` is taken).
- Fixed alembic URL resolution so programmatically-passed database URLs win over `DATABASE_ADMIN_URL`/`DATABASE_URL` env vars (integration-test fresh databases were previously never the ones migrated when env vars were set).

## 2026-05-11

- Added the Alice vNext dogfood hardening slice: dedicated connector settings/state tables, encrypted local secret-provider fallback, connector cursor/checkpoint persistence, migration/doctor readiness checks, live `/vnext` connector configuration, browser clipper token enforcement, Telegram retry/cursor hardening, generated-output recapture prevention, and daily dogfood runbook.
- Added the Alice vNext live capture connector slice for local dogfooding: allowlisted Telegram sync, local folder/Obsidian scan and watch, browser clipper capture, Hermes/OpenClaw-style agent output ingestion, connector health telemetry, dogfooding dashboard metrics, capture-to-brief smoke validation, and review-only trust preservation.
- Prepared the Alice vNext public-preview release package for `v0.5.1-vnext-preview`.
- Promoted the vNext preview docs from release-candidate posture to tag-ready preview posture while keeping `v0.5.1` as the current stable pre-1.0 public release.
- Added vNext preview release notes and tag plan with rollback instructions.
- Completed the vNext public release checklist with current verification evidence.
- Realigned control docs from stale "Sprint 1 active" wording to the completed Sprint 1-12 preview surface and the active vNext release gate.
- Verified the vNext Postgres-backed CLI/API/MCP smoke path, full unit suite, web test/lint/build gates, control-doc truth check, eval harness, Git diff whitespace check, and post-merge GitHub Security Scans.

## 2026-04-16

- Closed out Phase 14 after shipping all five planned sprints:
  - `P14-S1` provider abstraction cleanup + OpenAI-compatible adapter
  - `P14-S2` Ollama + llama.cpp + vLLM adapters
  - `P14-S3` model packs
  - `P14-S4` reference integrations
  - `P14-S5` design partner launch
- Shipped `HF-001` to eliminate unbounded local log growth by defaulting local/Lite logging to stdout, disabling local/Lite access logs by default, and adding bounded opt-in file logging.
- Promoted the public release boundary from `v0.4.0` to `v0.5.1`.
- Added Phase 14 closeout summary and closeout packet.
- Added `v0.5.1` release checklist, tag plan, and public release runbook.
- Aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.5.1`.
- Realigned canonical quickstart, MCP, and integration docs to the shipped Phase 14 + `HF-001` baseline.

## 2026-04-15

- Closed out Phase 13 after shipping all three planned sprints:
  - `P13-S1` one-call continuity
  - `P13-S2` Alice Lite
  - `P13-S3` memory hygiene and conversation health
- Promoted the public release boundary from `v0.3.2` to `v0.4.0`.
- Added Phase 13 closeout summary and closeout packet.
- Added `v0.4.0` release checklist, tag plan, and public release runbook.
- Aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.4.0`.
- Realigned current quickstart and integration docs to the shipped Phase 13 baseline.

## 2026-04-14

- Closed out Phase 12 after shipping all five planned sprints:
  - `P12-S1` hybrid retrieval + reranking
  - `P12-S2` automated memory operations
  - `P12-S3` contradiction detection + trust calibration
  - `P12-S4` public eval harness
  - `P12-S5` task-adaptive briefing
- Added Phase 12 closeout summary and closeout packet.
- Updated the documented release target from `v0.2.0` to `v0.3.2` for the completed Phase 12 boundary.
- Aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.3.2`.
- Added `v0.3.2` release checklist, tag plan, and public release runbook.
- Kept the published release truth explicit: the latest published tag remains `v0.2.0` until `v0.3.2` is cut.

- Prepared `R1` release-readiness package for `v0.2.0` as a pre-1.0 public release boundary.
- Added `v0.2.0` release checklist, tag plan, and public release runbook.
- Realigned launch-facing docs to shipped scope through Phase 11 and Bridge `B1` through `B4`.
- Recorded release-gate evidence in `docs/archive/process/BUILD_REPORT.md` and `docs/archive/process/REVIEW_REPORT.md` for `R1`.

## 2026-04-08

- Compacted the live control docs so `README.md`, `ROADMAP.md`, and `RULES.md` carry only current Phase 9 completion truth.
- Archived superseded Phase 9 planning and control material into local-only internal archives.
- Kept the quickstart, integration, release, runbook, and evaluation artifacts as the canonical Phase 9 launch surface.

## 2026-04-07

- Prepared the first public `v0.1.0` launch documentation set for the shipped Phase 9 wedge.
- Added onboarding, integration, release, and repo policy docs without expanding product scope.

## 2026-03-11

- Hardened the local runtime and verification path used by the public release candidate.
- Kept the launch surface aligned with deterministic local startup, migration, sample-data, and health-check flows.

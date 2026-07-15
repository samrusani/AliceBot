# Alice v0.10.4 Fifth-Audit Fix Matrix

## Decision summary

All five confirmed P1 findings, the downgraded provider P2, and every
pass-through P2 item were triaged. All were confirmed and remediated within the
brief's bounded scope. No cybersecurity work was performed.

Repair Batch 16 is the current bounded correction. It closes the PostgreSQL
embedding-CAS whitespace parity finding with migration `0090`'s exact CPython
3.12 29-codepoint trim table, fail-on-old SQL-shape coverage across all three
CAS consumers, and live NBSP/U+001C no-reembed/vector-participation proof.
Batch 16 implementation, tests, full gates, static/control checks,
LongMemEval/evidence replay, unchanged-web readback, and reproducible package
verification are green. The final tracked-patch and fixed 12-file remediation-
bundle fingerprints reproduced twice and are recorded in the self-excluded
builder report. The Batch 16 carrier was builder-frozen; its reviewer approved
the production CAS semantics and returned changes required on one P3 contradiction
in the handoff. Refreeze 17 changes only that stale Batch 15/current-review
wording plus its fail-on-old control guard. Independent review of the exact
Refreeze 17 carrier remains required, so it is not release-approved.

Repair Batch 15 was independently approved after closing the three P2s
returned by review of Batch 14: string-only metadata `next_action` row
candidates across SQLite/PostgreSQL/fake, exact production tie-break ordering
in `FakeVNextMCPStore.list_open_loops`, and truthful alpha documentation scope.
The later engineering-team embedding-CAS finding superseded that approval, so
Batch 15 evidence is historical and does not approve the current tree.

Batch 14's full unit/PostgreSQL gates, release-static/control checks,
LongMemEval/evidence replay, unchanged-web readback, reproducible packages,
source/test hashes, and twice-reproduced fingerprints are historical. Its
independent review returned changes required on exactly the three P2s above.

The candidate source intended for v0.10.4 contains a corrected `0083` script
that treats every present canonical `project_scope` value as authoritative.
If finalized, it will protect future pre-`0083` upgrade chains. This changes
neither the v0.10.3 tag nor its published artifacts. One evidence limit remains
for databases that already executed the older `0083` bytes: if that run erased
an explicit empty scope, no later migration can infer the lost intent without
backup or other evidence. See `ENGINEER_HANDOFF.md` before approving an
upgrade for such a database.

## P1 findings

| Finding | Disposition | Class-wide implementation | Fail-on-old evidence |
|---|---|---|---|
| P1-1 hosted Settings workspace selection | Fixed | All 23 resolver-backed hosted Telegram handlers accept explicit workspace selection; Settings sends its entered workspace on every applicable request; channel resolution no longer mutates session workspace; panel reads are workspace-scoped. | Web Settings tests, resolver unit tests, and a live two-workspace PostgreSQL notification PATCH/brief-delivery regression. |
| P1-2 project-update review bypass and candidate resurrection | Fixed | A shared locked dispatcher classifies generic artifact reviews; HTTP, MCP, and CLI use it; queue defense rejects direct project-update lifecycle changes. Pending coupled review validates artifact/candidate status, type, workflow, digest, project, and scope, then rejects every durable supersession representation before mutation: first-class and legacy pointers, current lifecycle markers, and append-only lifecycle history. Before a terminal idempotent return, the service instead proves the already-locked terminal artifact against exactly one append-only `project_update_review` revision and exactly one total accepted/rejected event coupled through the artifact or candidate. It counts the total before expected outcome, actor, action, target, payload, or redaction validation, so contradictory evidence cannot hide behind a valid event. It deliberately does not use mutable current memory/project state as historical evidence. The exact skeleton retained by authorized true redaction is admissible; partial or fabricated redaction markers fail closed. Human/agent/CLI actor, trace, and run attribution flows into events/revisions and deferred embeddings. | HTTP, MCP, CLI, queue, and project-service regressions cover generic and dedicated review, pending promote, accepted-to-rejected, retired/mismatched candidates, all five supersession representations across accept/edit/reject, unchanged failed-review state, central-dispatch propagation, reviewer attribution, forced accepted/rejected terminal side-door states, durable artifact/revision/event corruptions, valid accepted/rejected replay after supported evolution, and zero-mutation controls. New fail-on-old cases add accepted plus rejected evidence, extra accepted evidence with the wrong action, and double rejection through the service and all six generic/dedicated HTTP/MCP/CLI adapters. HTTP exposes terminal inconsistency as 409; MCP and CLI expose the fixed error. Live PostgreSQL covers accepted/rejected replay after authorized true redaction and competing decision evidence; SQLite covers preservation of the same evidence skeleton. |
| P1-3 SQLite explicit-empty project scope | Fixed for current/runtime and future upgrade chains | One presence-aware resolver and one backend-stable identity now govern Python, SQLite, PostgreSQL, policy/key admission, capture/dedupe, retrieval, scheduler, connectors, consolidation, and rollups. Persisted sources use a dedicated complete-envelope adapter: root canonical; embedded `metadata_json` then `scope_json` canonical; nested agentic/identity canonical; aliases only after canonical absence. That adapter governs both stores' source and parent-chunk searches, retrieval source admission, Brain, Projects, Connections, Contradictions, and HTTP artifact-trace authorization; scheduler/HTTP/MCP/CLI inherit shared services. Only the six ASCII whitespace characters normalize; ASCII-only identifiers compare case-insensitively; any identifier containing a non-ASCII code point compares exactly and case-sensitively. Strings, finite mathematically integral numbers, and explicit boolean scalar values normalize identically across backends; fractional/non-finite numbers, mappings, and null are excluded. SQLite SQL keys on canonical property presence and preserves `[]` through reopen. The v0.10.4 copy of `0083` now backfills only when the canonical key is absent; PostgreSQL predicates and forward migration `0090` mirror the shared identity without locale-dependent folding. | SQLite SQL/reopen tests, adapter/auth tests, migration unit tests, and live PostgreSQL parity tests cover empty/absent/malformed, ASCII case/order/whitespace/duplicates, mixed deterministic order, exact non-ASCII self-match, `İ/i`, `Straße/STRASSE`, `Σ/σ/ς`, Unicode whitespace, embedding CAS whitespace, and source/chunk/runtime consumer parity. E0 proves stale root alias plus embedded `[]` is visible nowhere; E1 proves stale alias plus embedded `[real]` is visible only to `real`. A live `0082`→head chain proves present empty/null/malformed/nonempty values remain authoritative and absent legacy scope still backfills. |
| P1-5 OpenAPI phantom responses | Fixed class-wide | All 294 operations are structurally covered: 49 exact contracts plus 243 closed source-derived registry contracts and two genuinely polymorphic contracts. TypedDict and authoritative row/service shapes replace fabricated wrappers; all named audit samples were corrected. | `tests/unit/test_main.py` validates registry completeness, closure, runtime payloads, phantom-key rejection, and no dangling local schema references. The scheduler regression invokes the actual endpoint handler, parses its response, and validates the exact 13-field payload against the generated required, closed schema. |
| P1-6 publication-stale PyPI description | Fixed prospectively | Package metadata now uses evergreen `docs/pypi-description.md`, not candidate-mode README prose. Release checks validate the source and the exact wheel `METADATA`/sdist `PKG-INFO` description and reject version or release-state language. | Release-check unit tests plus two-build artifact verification, Twine, distribution smoke, and metadata readback. Existing v0.10.3 PyPI metadata remains immutable. |

## P2 triage and closure

| Item | Triage | Closure and proof |
|---|---|---|
| OpenAI-compatible `auth_mode=none` | Confirmed, bounded | Invocation now carries `auth_mode` and omits Authorization for `none`; unit and PostgreSQL provider API tests cover provider test and runtime invocation. |
| Canonical project identity | Confirmed, broader than original shorthand but bounded by brief | Shared presence/identity core, current predicates/backfills/dedupe, retrieval admission, policy/key comparisons, scheduler grouping, both stores, and forward `0090` completed. ASCII-only identity is case-insensitive; non-ASCII identity and Unicode whitespace are exact. Scope is a deduplicated set sorted by Unicode code-point order. Blank key bindings/claims fail closed. No transport redesign. |
| Embedding CAS and migration raw-text `strip`/`btrim` mismatch | Confirmed, bounded | PostgreSQL digest SQL and migration `0090` now normalize raw text with CRLF/CR to LF followed by CPython 3.12's explicit locale-independent 29-codepoint `str.strip()` table. Project identifiers intentionally keep their separate six-ASCII-whitespace contract. Unit golden digests and live PostgreSQL upgrade/recapture regressions cover NBSP U+00A0, NEL U+0085, and EM SPACE U+2003 and prove no duplicate source is created. |
| Web API base-path discard | Confirmed, bounded | URL construction preserves configured path prefixes for every `requestJson` caller and the browser-clipper displayed endpoint while retaining local operator-key routing; web tests cover prefixed URLs. |
| Active release-document truth gaps | Confirmed, bounded | Active control docs identify v0.10.3 as latest published and v0.10.4 as uncommitted remediation; links, checksum pointers, install tag, and mirrors align. Truth checks now reconcile these fields and evergreen package metadata. Immutable historical release files were untouched. |
| Hosted onboarding | Confirmed, resized | Truthful instruction/preview copy replaces claims of live provisioning. A real onboarding wizard remains a separate product feature. |
| Navigation/copy omissions | Confirmed, bounded | Continuity and Chief-of-Staff navigation/cards are present; the landing page reports 16 views and live/fixture/mixed modes. |
| Hosted rate-limit metric | Confirmed, bounded | UI uses the exact overview count with a deterministic summary fallback; fail-on-old web tests pass. |
| Serial API waterfalls | Confirmed, bounded | Task, artifact, memory, and trace pages issue independent selected-record requests in parallel. Trace detail and events are composed independently after the same settled wave: either fulfilled leg remains visible when the other fails, with truthful `live`, `fixture`, or `unavailable` provenance per leg. Focused web tests cover both asymmetric failures and same-wave concurrency. |
| Reviewer attribution | Confirmed, class-coupled with P1-2 | Shared dispatcher/service boundaries preserve human, agent, and CLI attribution. Human HTTP reviews use `request.user_id`; deferred embedding persistence carries actor and trace. The dedicated MCP project-review schema now exposes the same flat agent identity/profile/scope/run/trace fields as other agent-aware tools, and a schema-validated call proves persisted identity and event attribution. |
| Migration `0087`/`0089` operator preflight | Confirmed, documentation/verification gap | Headless/release docs now provide duplicate preflight, backup-first survivor repair, retry, and unique-index readback. The guidance was reviewed directly and the complete control-document truth suite passes; no dedicated marker test claims to enforce these exact paragraphs. |
| Migration `0088` fingerprint stability | Confirmed, bounded | Historical migration calls immutable `provider_config_fingerprint_v1`; the current helper delegates to v1; a literal golden digest locks output. |

## Store and adapter parity

- HTTP: hosted workspace routing, generic/dedicated artifact review, generic
  memory lifecycle, scope-bearing vNext requests, source-aware artifact-trace
  authorization, OpenAPI, provider runtime.
- MCP: generic/dedicated artifact review, memory lifecycle, capture/recall,
  policy and scope adapters, including schema-validated dedicated-review agent
  attribution.
- CLI: generic/dedicated artifact review, memory lifecycle, capture/retrieval,
  connector/automation and scheduler adapters.
- Scheduler: canonical project identity, filtering/grouping, attributed
  generation, and inherited shared-service source scope; it never performs
  project review.
- Web: explicit hosted workspace, base-prefix URL builder, browser clipper,
  navigation/copy/metrics, and parallel page loads.
- PostgreSQL: project/artifact lifecycle, canonical scope predicates/dedupe,
  complete persisted-source envelope precedence in source/parent-chunk search,
  explicit ASCII-only folding and exact non-ASCII ordering, embedding CAS,
  hosted workspace isolation, migrations `0088` and `0090`.
- SQLite: canonical empty/absent/malformed scope, complete persisted-source
  envelope precedence in source/parent-chunk search, the same ASCII/non-ASCII
  identity rule, exact lookup, source dedupe, generic memory lifecycle, and
  bootstrap/reopen idempotence.

## Builder Repair Batch 2 closure

The first independent review pass returned three bounded correctness gaps.
The builder refreeze closes each without broadening release scope:

1. Project-update review now rejects first-class `superseded_by`, legacy
   `metadata_json.superseded_by`, `review_superseded`,
   `superseded_by_consolidation`, and append-only history equivalents before
   accept, edit, or reject can mutate artifact, project, memory, revision, or
   event state. The central dispatcher regression proves adapter propagation.
2. Project identity no longer relies on backend-dependent Unicode case
   behavior. Python, SQLite, PostgreSQL, migration `0090`, and API-key policy
   implement the explicit ASCII/exact-non-ASCII contract above. Regressions
   include Turkish dotted I, German sharp S, all three Greek sigma forms,
   non-breaking/Unicode whitespace, and blank-scope fail-closed behavior.
3. `alice_project_update_review` now uses the common agent-aware MCP schema.
   Its regression invokes the normal schema validator with agent identity,
   type, profile, project scope, run, and trace fields, then verifies the
   persisted identity and accepted-event actor/run/trace values.

## Builder Repair Batch 3 closure

The second independent review pass found two bounded gaps. The builder
refreeze closes both without reopening other remediation classes:

1. The `0083` backfill now uses canonical-key absence, not type or array
   length, as its only fallback gate. Present `[]`, JSON null, malformed, and
   nonempty canonical values cannot be overwritten or supply `project_id`
   through stale nested scope. An `0082`→head PostgreSQL regression proves
   those cases plus the intended absent-key legacy backfill.
2. The trace page preserves fulfilled detail and fulfilled events
   independently. A rejected request is labeled unavailable rather than
   inheriting live provenance, while the live list summary remains the bounded
   source for fields that were actually returned.

## Builder Repair Batch 4 closure

The third independent review pass found five bounded parity and evidence gaps.
The final builder refreeze closes them without reopening other remediation
classes:

1. Scheduler status now publishes a closed OpenAPI object containing the
   complete service status plus daemon state. A runtime-versus-generated-schema
   regression fails on the former daemon-only contract.
2. SQLite source-dedupe repair resolves canonical and legacy scope with the
   shared presence-aware resolver. Migration `0090` mirrors that resolver's
   precedence and supported fallbacks before computing source identity.
3. Migration `0083` normalizes only ASCII SP/HT/LF/VT/FF/CR; a live
   `0082`→head regression proves an identifier containing U+2003 remains
   exact rather than collapsing to ASCII space.
4. The release-engineer handoff now orders governed version/document
   finalization before clean-SHA selection, delegates GitHub Release creation
   solely to the transactional publish workflow, and defers the durable
   checksum record to the evidence-backed post-publication commit.
5. Builder evidence now quotes the release check's actual output and describes
   the migration-guidance review without inventing a dedicated marker test.

## Builder Repair Batch 5 closure (terminal detail superseded)

The fourth independent review pass found four bounded gaps. Refreeze 5 closes
three fully and introduced a terminal-consistency guard whose evidence model
was corrected by Repair Batch 6:

1. Refreeze 5 added a fail-closed terminal project-update guard and adapter
   side-door tests, but its proof incorrectly depended on mutable current
   memory/project state. The fixed repair instruction and zero-mutation
   behavior remain; Repair Batch 6 replaces only that proof model.
2. Migration `0090` uses the explicit CPython 3.12 29-codepoint whitespace
   table after newline normalization. Live NBSP, NEL, and EM SPACE upgrades
   match runtime digests and recapture the original source without duplication.
3. Release instructions require brand-new empty primary and reproducibility
   directories, do not reuse or delete user-owned artifacts, and state
   truthfully that ignored caches may refresh but are excluded from evidence.
4. The scheduler OpenAPI regression invokes the endpoint handler, parses its
   JSON response, and validates the exact 13 keys against the generated
   required, closed schema, including phantom-key rejection.

## Historical Builder Repair Batch 6 closure (superseded)

The fifth independent review pass found one bounded lifecycle defect in the
Refreeze 5 terminal proof. Repair Batch 6 closes that class without reopening
pending-review validation or any other remediation area:

1. A terminal accepted/rejected retry now proves the original outcome from the
   already-locked artifact plus exactly one append-only
   `project_update_review` revision and exactly one actor-coupled decision
   event. It does not compare current candidate-memory fields, require the
   current memory row to exist, or compare current project state.
2. Normal revision/event evidence validates the action and original linkage;
   the authorized true-redaction path is admitted only when it retains the
   exact content-free skeleton. Partial markers, duplicate or contradictory
   decision evidence, actor/linkage drift, and accepted-event redaction with a
   surviving integrity hash fail closed.
3. Valid terminal replay therefore survives supported correction, undo,
   forget, a genuine later accepted project update, and authorized true
   redaction without mutating artifact, memory, project, revision, or event
   state. Live role-separated PostgreSQL proves accepted and rejected
   redaction/replay; SQLite proves the same revision/event skeleton survives
   its redaction implementation.
4. A fabricated accepted/rejected status without the coupled evidence remains
   rejected through generic and dedicated HTTP, MCP, and CLI adapters. HTTP
   returns the fixed 409 detail; MCP and CLI return the fixed error; every
   regression snapshots durable state and proves zero mutation.

Historically, Refreeze 6 completed 3,197 unit tests, 447 role-separated
PostgreSQL tests, release-static, LongMemEval, web invariance, and reproducible
installed wheel/sdist checks. Its tracked patch is
`0527362a0876d8807488ba3db4818cac6a3da83b06eb8a544619036ca888d3d4`;
its pre-carrier bundle was
`966429239311313957baf616967a933f0e197f7f25f021332caf93c2066b5672`.
The verified package hashes are wheel
`1994bd808a618f670dea7f7bcb50f3f034ee032afa0b78c4a355da5bd7e60670`
and sdist
`1137b5a3b99f7023aa5bc0da7a165a953864fd2ea5b60a6fc7746ed2b81a9e8f`.
Refreeze 7 changed only those untracked handoff carriers. Repair Batch 8
supersedes both freezes; their results and hashes are not current-tree approval
evidence.

## Builder Repair Batch 8 closure

The sixth independent review pass found two bounded defects. Batch 8 closes
both without reopening other remediation classes:

1. Terminal replay collects every artifact/candidate-coupled accepted/rejected
   event before it filters or validates expected outcome, actor, action,
   target, payload, or redaction form, then requires exactly one total coupled
   event. Accepted-plus-rejected, extra accepted with the wrong action, and
   double-rejection histories fail closed without mutation across the service
   and all six generic/dedicated HTTP, MCP, and CLI adapters. Valid ordinary
   and redacted accepted/rejected replay remains admissible.
2. Persisted source scope follows the complete source envelope rather than a
   flat memory envelope. SQLite and PostgreSQL source/parent-chunk searches,
   retrieval lexical/chunk/provenance/evidence/reference/currency/temporal
   admission, Brain, Projects, Connections, Contradictions, and HTTP
   artifact-trace authorization share that rule; scheduler/HTTP/MCP/CLI callers
   inherit it. E0 (stale root alias plus embedded `[]`) is visible nowhere.
   E1 (stale alias plus embedded `[real]`) is visible only to `real`.
   Strings, finite mathematically integral numbers, and the explicit boolean
   scalar values agree across Python, SQLite, and PostgreSQL; fractional and
   non-finite numbers, mappings, and null are excluded.

Current evidence is green for `release-static`, 3,230 unit tests (75.58%
overall coverage and 52.64% for `main.py`), 450 role-separated PostgreSQL
tests, and 127 model-free LongMemEval tests. Web
type/lint/unit/coverage/build/budget/Playwright gates also passed against an
unchanged fingerprint. Two fresh package builds were byte-identical, Twine and
release-check passed, and both installed artifacts passed isolated smoke
checks. Their SHA-256 values are wheel
`72feafee3f423f283a454a0ded6f7ffd49848fef159e344da782076f7113932e`
and sdist
`1b5f8bb48ccd82a1da494403fd813e7c7ad62b7c2b50b57cfd082fc40027d118`.
The Batch 8 tracked-patch and bundle fingerprints were recorded only in the
self-excluded `BUILD_REPORT.md` and reproduced twice. Its subsequent
independent review returned changes required, so that evidence is historical
and does not approve the current tree.

Independent review, clean-SHA semantic attestation, version finalization, and
publication remain external gates.

## Historical Builder Repair Batch 9 closure (superseded)

The independent review of Batch 8 found eight bounded gaps. Batch 9 closed
them without reopening the larger fifth-audit scope:

| Finding | Disposition | Closure evidence |
| --- | --- | --- |
| Capture identity integrity | Fixed | Fast-key, content-hash, and atomic dedupe paths validate the current source envelope and classification. SQLite/PostgreSQL identity-bearing updates rotate stale keys atomically; collisions and HTTP review roll back without mutation. |
| Key-bound core MCP explanation | Fixed | Memory supersession, provenance sources, entity-backing memories, and continuity objects authorize before expansion; mixed or missing backing evidence returns the same generic unavailable result. |
| Candidate-created terminal binding | Fixed | The distinct candidate-created target set must equal the locked artifact. Exact ordinary and true-redaction forms pass, including repeated same-target rows; foreign targets fail before mutation. |
| Numeric project-scope parity | Fixed | Python, SQLite, PostgreSQL, and migration `0090` canonicalize finite integral JSON numbers and signed zero, reject fractional/non-finite values, and retain explicit boolean scalar identifiers. |
| Legacy MCP context tree | Fixed | Effective project scope applies before limits across five resource groups (projects, memories, sources, open loops, and artifacts); sources use the persisted-source resolver and the separate event group is target-specific to admitted rows. The tool remains outside the core MCP surface and disabled on key-bound servers. |
| MCP open-loop/resume starvation | Fixed | Project predicates run before bounded limits and event reads are coupled only to admitted targets. |
| Protected-path metadata | Fixed | `ENGINEER_HANDOFF.md` carries the completed Upgrade Overview with exactly memory schema and continuity APIs checked, plus an executable parser/guard regression. |
| Batch 8/9 freeze truth | Fixed for the Batch 9 carrier | Control documents describe Batch 8 hashes as twice-reproduced historical evidence followed by changes required. Batch 9 was also frozen and twice fingerprinted, then received a changes-required review on five bounded findings; its evidence is historical rather than approval for the current tree. |

Batch 9 builder verification was green: 3,301 units with coverage floors, 455
role-separated PostgreSQL integrations, 127 LongMemEval tests plus evidence
replay, release-static, the full web matrix, reproducible packages, archive
byte parity, and isolated wheel/sdist smokes passed. The 906-unit/18-PostgreSQL/
3-migration focused sweep and 47 control/guard tests also passed. Final
fingerprints were recorded and reproduced twice. Its subsequent independent
review returned changes required on five bounded findings, so independent
review of the current carrier remains a separate gate.

## Builder Repair Batch 10 closure

The Batch 9 review returned changes required on five bounded findings. Batch
10 remains constrained to those findings:

| Finding | Disposition | Closure evidence |
| --- | --- | --- |
| Dangling explanation supersession pointer | Fixed | Both chain directions fail before audit-envelope reads when a non-null target is unresolved. Key-bound MCP maps direct and reachable-then-dangling cases to the same generic unavailable response without the missing identifier; authorized complete chains pass. |
| Nested generic-resource project scope | Fixed | Shared Python resolution and generic SQLite/PostgreSQL memory, artifact, and open-loop predicates treat nested canonical `agentic_memory.project_scope` and `agent_identity.project_scope` as authoritative. Scalar/array forms preserve string, finite-integral, and boolean parity; empty, null, malformed, and stale-alias combinations fail closed before limits. |
| Resume pre-limit admission and event starvation | Fixed | Decision and next-action memory queries plus open-loop queries push status, type, canonical project, query, and time predicates before limits. Dedicated memory/open-loop event joins scope targets before event-time ordering and limiting, including older targets with newer events. |
| Resume canonical explicit project | Fixed | Resume passes the policy-resolved effective project set into canonical store predicates and no longer applies the incompatible legacy `metadata_json.project_id`/domain matcher. |
| Context-tree and freeze documentation | Fixed | Public and handoff docs state five resource groups plus events, no entity group, and the legacy/key-bound boundary. Executable control truth rejects the stale Batch 9 pending-freeze claim. |

Batch 10 builder gates are green: 3,325 units with coverage floors, 457
role-separated PostgreSQL integrations, the 1,171-test integrated seam,
release-static, 127 LongMemEval tests plus evidence replay, the unchanged web
carrier, reproducible packages, archive parity, and installed-artifact smokes
passed. Final tracked-patch and bundle fingerprints were reproduced twice.
The subsequent independent review returned changes required on exactly two
bounded findings; historical Batch 8/9/10 evidence does not approve the
current carrier.

## Builder Repair Batch 11 closure

The Batch 10 review returned changes required on exactly two bounded findings.
Batch 11 remains constrained to those findings:

| Finding | Disposition | Closure evidence |
| --- | --- | --- |
| Persisted-source nested canonical presence | Fixed | PostgreSQL source and parent-chunk predicates plus migration `0090` choose the nested `agentic_memory`/`agent_identity.project_scope` tier by key presence. Present blank, null, malformed, and fractional values resolve empty instead of falling through to stale aliases; valid scalar/array leaves and both nested containers retain Python/SQLite merge and identity parity. |
| Resume open-loop query semantics | Fixed | `_vnext_resume` passes `query` to open-loop row and event joins in both stores before limits. Title, description, next-action metadata, and relevant event payload text participate for scoped and unscoped calls; newer mismatching rows cannot appear in or starve `open_loops`, `next_action`, or `recent_changes`, and queryless behavior remains intact. |

Focused Batch 11 gates are green: 7 persisted-source/migration tests, 3
resume-query tests, 595 owned/shared units, 9 role-separated PostgreSQL
scope/source/resume cases, and 4 migration `0090` cases passed. Ruff, format,
mypy, and diff checks passed. The final gate added 3,327 units with coverage
floors, 460 role-separated PostgreSQL integrations, release-static, 127
LongMemEval tests plus evidence, the unchanged web carrier, reproducible
packages, archive parity, and both isolated installed-artifact smokes. Final
fingerprints reproduced twice. Independent review approved persisted-source
closure and every other bounded area, but returned changes required on the one
event-payload P2; Batch 11 evidence is historical.

## Historical Builder Repair Batch 12 closure (review rejected)

The Batch 11 review returned changes required on exactly one bounded P2. Batch
12 remains constrained to that finding:

| Finding | Disposition | Closure evidence |
| --- | --- | --- |
| Resume event-payload string-leaf semantics | Fixed | SQLite `json_tree` and PostgreSQL recursive `jsonb_path_query` restrict payload matching to case-insensitive string leaf values. Keys, numbers, booleans, nulls, and serialization structure cannot match. Nested object/array strings remain supported; row fields, scope/status/time-before-limit, event ordering, scoped/unscoped calls, optional defaults, and queryless behavior are preserved. |

Focused Batch 12 gates are green: 442 owned units, all 9 role-separated
PostgreSQL scope/source/resume cases, and the three separate SQLite/SQL-shape/
live-PostgreSQL regressions passed. Regressions use 62 newer mismatch rows and
cover key-only negative, nested-string, and array-string behavior. Ruff,
format, mypy, diff-check, and pre-documentation release-static passed. The
final 3,327-unit/460-PostgreSQL gate, release-static, LongMemEval/evidence,
unchanged web carrier, reproducible package pair, parity, and both isolated
smokes passed. Final fingerprints reproduced twice. Independent review
approved the production SQLite/PostgreSQL recursive string-leaf behavior but
returned changes required because the fake store could combine strings from
separate leaves. Batch 12 does not approve the current tree.

## Historical Builder Repair Batch 13 closure (never frozen)

Batch 13 corrected only the fake cross-leaf defect: one query had to occur in
one recursive string leaf. Two focused regressions, the 256-test MCP file, and
3,328 full units passed. Exact production-file hashes remained those of the
frozen Batch 12 carrier, so its 460 role-separated PostgreSQL integrations were
carried without rerun.

Batch 13 was never frozen. It had no final static, package, fingerprint, or
release claim. Independent review returned one Unicode/collation P2 because
Python Unicode folding and SQL backend lower/collation behavior were not one
deterministic cross-backend rule.

## Historical Builder Repair Batch 14 closure (review rejected)

Repair Batch 14 was frozen and fully verified before review:

| Finding | Disposition | Historical closure proof |
| --- | --- | --- |
| Resume query cross-backend comparison | Fixed; builder verification green; review rejected | SQLite, PostgreSQL, and the fake use **ASCII case-insensitive literal substring** comparison for title, description, root/nested next-action fields, and each recursive event string leaf. ASCII letters fold; non-ASCII remains exact without normalization or locale dependence. Cross-leaf concatenation remains forbidden. SQL `%`, `_`, and backslash remain literal. Blank/queryless behavior, pre-limit scope/status/time filtering, event ordering, scoped/unscoped calls, and optional defaults are unchanged. Four focused units, 338 complete MCP/store units, 3,329 full units with required coverage floors, 461 role-separated PostgreSQL integrations, release-static/control checks, 127 LongMemEval tests plus replay, unchanged-web readback, and two reproducible package builds with isolated smokes passed. Final tracked-patch and fixed 12-file bundle fingerprints reproduced twice. Independent review then returned exactly the three bounded P2s identified below. |

Exact Batch 14 commands, timings, coverage, package hashes, source/test hashes,
and final twice-reproduced tracked-patch and bundle fingerprints are recorded
in the self-excluded `BUILD_REPORT.md`. The builder carrier is frozen.
Independent review returned changes required on exactly these bounded P2s:

1. non-string root/nested metadata `next_action` row parity;
2. overbroad alpha-documentation scope; and
3. the fake open-loop list's missing `created_at` tie-break.

Batch 14 does not approve the current tree.

## Historical Builder Repair Batch 15 closure

Repair Batch 15 was the then-current bounded correction:

| Finding | Disposition | Closure proof |
| --- | --- | --- |
| Non-string metadata `next_action` row parity | Fixed; builder verification green | SQLite, PostgreSQL, and the fake admit root `metadata_json.next_action` and nested `metadata_json.agentic_memory.next_action` as row candidates only when the JSON value is a string. Objects, arrays, numbers, booleans, and null do not match through those fields. Title/description comparison and recursive per-string-leaf event payload matching remain unchanged. Five focused units, the 339-test owned seam, focused live PostgreSQL, and all 10 affected PostgreSQL cases passed. |
| Alpha documentation scope | Fixed; builder verification green | Alpha docs limit the **ASCII case-insensitive literal substring**, exact non-ASCII, and literal `%`, `_`, and backslash contract to open-loop row fields and loop-event recursive string leaves. It does not govern decision-memory or next-action-memory search. Release-static passed all 14 control documents and the control suite passed 44 tests. |
| Fake open-loop tie-break ordering | Fixed; builder verification green | `FakeVNextMCPStore.list_open_loops` sorts by `opened_at DESC`, then `created_at DESC`, then `id DESC`, matching production. Focused equal-`opened_at`/different-`created_at` parity and the complete owned seam passed. |

The full gate passed 3,331 units with required coverage floors and 461
role-separated PostgreSQL integrations, 3,792 tests total. Release-static,
Ruff/format/`py_compile`, control, mirror/diff, 127 LongMemEval tests plus
evidence replay, unchanged-web readback, and two byte-identical normalized
package builds with Twine/release-check/seven-file parity and isolated smokes
passed. Exact timings, coverage, source/test hashes, carrier digests, and
package hashes are recorded in `BUILD_REPORT.md`. The final tracked-patch and
fixed 12-file remediation-bundle fingerprints reproduced twice. Independent
review subsequently approved that exact carrier, but the later Batch 16
embedding-CAS whitespace finding superseded it. Clean-SHA semantic attestation,
version finalization, and publication remain external gates after successful
Batch 16 review.

## Builder Repair Batch 16 closure

Batch 15 is historical and superseded by the engineering-team whitespace
finding even though its independent review approved the then-frozen carrier.
Repair Batch 16 is limited to one release-blocking P2 class:

| Finding | Disposition | Closure proof |
| --- | --- | --- |
| Embedding CAS Python-strip parity | Fixed; production semantics approved by review | `_MEMORY_EMBEDDING_CONTENT_SHA256_SQL` now trims title, canonical text, and summary with a private runtime copy of migration `0090`'s exact CPython 3.12 29-codepoint table expressed as `btrim(..., chr(...) || ...)`. It no longer uses POSIX `[[:space:]]`, and it preserves blank omission, first-occurrence deduplication, LF joining, and SHA-256. A fail-on-old unit test proves all 29 codepoints—especially U+001C–U+001F, NEL, and NBSP—appear in each of the three generated SQL consumers: signed vector freshness, embedding-update CAS, and missing-embedding selection. Live role-separated PostgreSQL passes NBSP, U+001C, and mixed blank/deduplicated field cases through CAS acceptance, empty missing-embedding selection, and signed vector participation. The complete affected unit/PostgreSQL files, 3,332-unit coverage gate, 463-case PostgreSQL matrix, release-static/control, LongMemEval/evidence, unchanged web readback, and reproducible package/parity/smoke gate pass. Batch 16 review approved those production semantics and returned changes required only on the stale handoff-truth P3 addressed by Refreeze 17. |

No migration, Python embedding-text function, SQLite path, transport, provider,
vector ranking, or unrelated normalization behavior changes in Batch 16.

## Refreeze 17 documentation-truth closure

Refreeze 17 changes no runtime, migration, provider, store, web, or semantic-
regression behavior. It makes Batch 16 current in the builder/fix summaries,
makes the independently approved then-superseded Batch 15 sections historical,
and qualifies the remaining review gate as Refreeze 17 review. The control-
truth checker now rejects the exact line-wrapped stale claim that Batch 15 is
current while review is pending. Verification and final carrier fingerprints
are recorded in the self-excluded `BUILD_REPORT.md`; independent Refreeze 17
review remains required.

## Explicit residual limitation

The candidate source intended for v0.10.4 contains the corrected `0083`
script, so a future database upgrading from `0082` or earlier will be protected
if the candidate is finalized. The v0.10.3 tag, wheel, sdist, release notes,
and checksums remain untouched.

If a database already ran an older packaged copy of `0083` and that execution
overwrote an explicit empty scope, neither the corrected script nor `0090` can
distinguish lost intent from an intentional resulting scope. Repair for that
already-executed case requires a backup, audit record, or other external
evidence; the release must not claim automatic reconstruction.

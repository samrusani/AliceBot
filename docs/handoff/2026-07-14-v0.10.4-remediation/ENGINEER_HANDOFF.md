# Alice v0.10.4 Release-Engineer Handoff

## Start here

Review the uncommitted tree in this order:

1. `SURFACE_INVENTORY.md` for the frozen pre-edit class enumeration.
2. `FIX_MATRIX.md` for disposition, implementation boundary, and parity.
3. The corrected `20260711_0083_memory_lifecycle_invariants.py`, its live
   `0082`→head regression, the new `20260714_0090_project_scope_identity.py`,
   and the already-executed-upgrade limitation below.
4. Shared lifecycle files `vnext_artifact_review.py` and
   `vnext_project_update_guard.py`, then HTTP/MCP/CLI adapters.
5. Shared scope identity, persisted-source envelope resolution, both store
   implementations, retrieval admission and shared source consumers, API-key
   admission, and forward migration `0090`.
6. Hosted workspace routing and web Settings tests.
7. OpenAPI contract derivation and `tests/unit/test_main.py`.
8. Provider no-auth/base-prefix fixes, release tooling, active docs, and the
   evergreen PyPI description.
9. The embedding CAS strip table in `vnext_store.py`, its exact parity with
   migration `0090`, and the unit/live PostgreSQL fail-on-old coverage.
10. `BUILD_REPORT.md`, the historical Batch 15 `REVIEW_REPORT.md`, then the
    independent Refreeze 17 review when supplied.

Do not select a release commit until Batch 16's production gates and Refreeze
17's truth gates have passed, the final tracked-patch and bundle fingerprints
have been recorded and reproduced, and the reviewer has approved that exact
Refreeze 17 carrier.

## High-risk review points

- Confirm memory embedding CAS SQL uses the explicit CPython 3.12 29-codepoint
  `chr()` table from migration `0090`, including U+001C–U+001F, NEL, and NBSP,
  without POSIX `[[:space:]]`. Confirm vector freshness, signed update CAS,
  and missing-embedding selection all interpolate the same digest fragment.
- Confirm root and nested metadata `next_action` values enter open-loop row
  matching only when their JSON value is a string in SQLite, PostgreSQL, and
  the fake; objects, arrays, numbers, booleans, and null must not be stringified
  into candidates. Recursive event payload matching remains per individual
  string leaf.
- Confirm `FakeVNextMCPStore.list_open_loops` orders by `opened_at DESC`, then
  `created_at DESC`, then `id DESC`, including equal-`opened_at` cases.
- Confirm alpha docs scope the ASCII/exact/literal query contract only to
  open-loop row fields and loop-event leaves, with no claim about
  decision-memory or next-action-memory search.
- Confirm every generic artifact-review entry point routes through
  `dispatch_vnext_artifact_review`, and direct queue review rejects a project
  update even if an adapter regresses.
- Confirm accept/edit/reject validates the locked candidate memory before any
  state mutation and cannot resurrect or relabel superseded state. Review the
  first-class/legacy pointer, current lifecycle, and append-only history
  guards together.
- Confirm every terminal project-update retry validates the locked artifact
  against exactly one append-only `project_update_review` revision and exactly
  one total accepted/rejected event coupled through the artifact or candidate.
  The service must collect the total before checking the expected outcome,
  actor, action, target, payload, or redaction form; otherwise contradictory
  evidence can hide behind a valid event. The historical
  proof must not depend on current candidate-memory fields, current memory-row
  existence, or current project state: those can legitimately change after a
  review. Authorized true redaction must leave only the exact revision/event
  skeleton accepted by the proof, including a cleared integrity hash for a
  redacted accepted event, and accepted/rejected replay must remain
  mutation-free. Fabricated, duplicate, or contradictory terminal states
  through all six generic/dedicated HTTP, MCP, and CLI adapters must return the
  fixed conflict/error and make zero mutations; valid outcomes remain
  idempotent.
- Confirm `project.update_candidate_created` evidence resolves to exactly the
  locked artifact: ordinary rows carry its exact candidate ID, authorized true
  redaction carries only the supported content-free skeleton, repeated rows
  may name that same target, and any distinct target fails before mutation.
- Confirm key presence, not array length/truthiness, controls legacy project
  scope fallback in Python, SQLite, and PostgreSQL.
- Confirm the v0.10.4 `0083` script gates legacy promotion on canonical-key
  absence (`NOT (metadata_json ? 'project_scope')`) and that present empty,
  null, malformed, or nonempty values cannot populate `project_id` from stale
  nested scope.
- Confirm project identity normalizes only ASCII SP/HT/LF/VT/FF/CR, folds case
  only when the complete normalized identifier is ASCII, preserves every
  non-ASCII code point exactly, and uses the same deterministic set ordering
  in Python, SQLite, PostgreSQL, migration `0090`, and agent-key policy.
  Finite mathematically integral JSON numbers, including signed zero, are
  canonicalized; fractional and non-finite numbers are rejected. The existing
  explicit `true` and `false` scalar identifiers remain supported.
- Confirm SQLite source-dedupe repair version 4 and migration `0090` adapt the
  complete persisted source envelope before applying the shared precedence:
  root canonical; metadata then scope canonical; nested agentic/identity
  scopes; root aliases; then metadata/scope and nested-agentic aliases. Nested
  singular `agent_identity` aliases remain intentionally unsupported.
- Confirm migration `0090` normalizes source raw text with CRLF/CR to LF and
  CPython 3.12's explicit locale-independent 29-codepoint `str.strip()` table.
  This is intentionally broader than the six-ASCII-whitespace project-identity
  rule. The table is U+0009–000D, U+001C–0020, U+0085, U+00A0, U+1680,
  U+2000–200A, U+2028, U+2029, U+202F, U+205F, and U+3000; NBSP U+00A0, NEL
  U+0085, and EM SPACE U+2003 must reproduce runtime digests and recapture the
  original source without creating a duplicate.
- Confirm runtime source reads apply that same persisted-envelope resolver,
  not the flat memory resolver. This includes SQLite and PostgreSQL
  `search_sources` plus parent chunks; retrieval lexical, chunk, provenance,
  evidence, reference, currency, and temporal post-admission; Brain, Projects,
  Connections, and Contradictions; and HTTP artifact-trace authorization.
  Scheduler, HTTP, MCP, and CLI should inherit these shared services rather
  than reimplementing scope. E0 (stale outer alias plus embedded `[]`) must be
  visible nowhere. E1 (stale outer alias plus embedded `[real]`) must be
  visible only to `real`. Python/SQLite/PostgreSQL must agree that strings,
  finite mathematically integral numbers, and the explicit boolean scalar
  values can normalize to identifiers, while fractional/non-finite numbers,
  mappings, and null cannot.
- Confirm the persisted-source PostgreSQL SQL and migration `0090` select the
  nested canonical tier when either `agentic_memory` or `agent_identity`
  contains the `project_scope` key, even when its value is blank, null,
  malformed, or fractional. They must normalize the selected tier to an empty
  identity instead of falling through to a stale alias. Source and parent
  chunk predicates and migration dedupe identity must match Python and SQLite;
  valid scalar/array values and both nested containers must retain their
  established merge order.
- Confirm key-bound core MCP `alice_explain` authorizes the root and every
  expanded supersession, provenance, entity-backing, and continuity resource;
  mixed, missing, or malformed evidence must return the same generic
  unavailable response without identifiers.
- Confirm the legacy MCP context tree applies the effective project set before
  each store limit across its five resource groups (projects, memories,
  sources, open loops, and artifacts), uses source-specific scope for sources,
  and reads its separate event group only for admitted targets. Confirm the
  tool remains outside the core MCP surface and disabled on key-bound servers.
  Core open-loop and resume reads must apply the same pre-limit scope and
  bounded target-specific event rule.
- Confirm `alice_resume.query` reaches both `list_open_loops` and
  `list_open_loop_events` in SQLite and PostgreSQL before their limits. It must
  search loop title, description, next-action metadata, and recursive string
  leaf values in relevant event payloads using one **ASCII case-insensitive
  literal substring** comparator shared with the MCP fake. ASCII letters fold;
  non-ASCII remains exact with no normalization or locale dependence. Payload
  keys, non-string values, serialization structure, and text split across
  separate leaves must not match. `%`, `_`, and backslash are literal
  characters, never SQL wildcard syntax. Scoped and unscoped calls must
  exclude newer mismatching noise from `open_loops`, `next_action`, and
  `recent_changes` while preserving blank/queryless behavior, pre-limit
  admission, and established ordering.
- Confirm blank project-scoped key bindings and claims fail closed rather than
  being dropped into an unscoped identity.
- Confirm the dedicated `alice_project_update_review` MCP schema exposes the
  agent identity/type/profile/scope/run/trace fields and that its normal
  schema-validated call persists actor, run, and trace attribution.
- Confirm `0090` is the sole new Alembic head and its source-dedupe survivor
  behavior is deterministic and evidence-preserving.
- Confirm OpenAPI closure does not introduce import cycles and runtime payloads
  validate against the generated schemas. The scheduler regression must invoke
  the actual endpoint handler, parse its response, and validate all twelve
  service-status fields plus `daemon` against the generated required, closed
  schema, including phantom-key rejection.
- Confirm `auth_mode=none` reaches response invocation without an Authorization
  header and a configured web API path prefix survives every URL builder.
- Confirm candidate-mode active docs do not claim v0.10.4 was published and
  package metadata contains no release-state prose.
- Confirm trace detail and events retain independent `live`/`fixture`/
  `unavailable` provenance after `Promise.allSettled`, including both
  asymmetric partial-outage directions.

## Builder Repair Batch 2 review deltas

The initial independent review found three bounded gaps after the first
builder freeze. The refrozen tree adds:

- a pre-mutation supersession guard for five persisted marker forms across all
  three project-review actions, plus central-dispatch propagation evidence;
- one explicit cross-backend project-identity algorithm with Unicode and
  blank-scope fail-closed regressions across runtime, stores, migration, and
  key policy; and
- the common agent-aware schema on the dedicated MCP project-review tool with
  end-to-end persisted attribution evidence.

The final independent reviewer must review these deltas on the new bundle
fingerprint in `BUILD_REPORT.md`; the first-pass approval does not carry over
automatically.

## Builder Repair Batch 3 review deltas

The second independent review found two bounded gaps after the second builder
freeze. The refrozen tree adds:

- canonical-key-presence protection directly to the `0083` script intended
  for v0.10.4, with unit SQL-shape and live `0082`→head coverage for present
  and absent canonical forms; and
- independent trace detail/event composition and source labels, with both
  asymmetric failures and same-wave concurrency covered.

The final reviewer must evaluate these changes on the Refreeze 3 fingerprints;
no approval from an earlier tree carries over.

## Builder Repair Batch 4 review deltas

The third independent review found five bounded truth/parity gaps after the
third builder freeze. The final refrozen tree adds:

- the complete closed runtime shape for scheduler status, with a fail-on-old
  runtime-versus-generated-OpenAPI regression;
- presence-aware legacy scope resolution in both SQLite source-dedupe repair
  and PostgreSQL migration `0090`, plus exact ASCII-whitespace handling in
  migration `0083` and live upgrade-chain parity evidence; and
- a canonical release-engineer sequence and evidence wording that match
  `RELEASING.md` and the release tooling's actual behavior.

The final reviewer must evaluate these changes on the Refreeze 4 fingerprints;
no approval from an earlier tree carries over.

## Builder Repair Batch 5 review deltas

The fourth independent review found four bounded correctness and evidence
gaps after the fourth builder freeze. The Refreeze 5 tree adds:

- a locked durable-consistency proof before every terminal project-update
  idempotent return, with the fixed fail-closed repair message and service plus
  generic/dedicated HTTP, MCP, and CLI regressions for forced accepted/rejected
  states and valid controls;
- exact CPython 3.12 source raw-text normalization in migration `0090`, with
  locale-independent 29-codepoint trimming and live NBSP/NEL/EM SPACE upgrade
  plus recapture evidence;
- brand-new empty distribution/reproducibility directories in both release
  matrices, truthful ignored-cache boundaries, and executable documentation
  checks for those operational constraints; and
- an OpenAPI regression that invokes the actual scheduler-status endpoint,
  parses the serialized response, and validates its exact 13 fields against
  the generated required, closed schema with phantom-key rejection.

The Refreeze 5 terminal-proof claim is superseded by Repair Batch 6 below. No
Refreeze 5 approval carries over to the current tree.

## Historical Builder Repair Batch 6 review deltas (superseded)

The fifth independent review found that the Refreeze 5 terminal guard treated
mutable current candidate-memory and project state as evidence of the original
review. That made a valid retry fail after supported lifecycle operations, a
later accepted update, or true redaction. Repair Batch 6 narrows the proof to
the durable decision record:

- the already-locked terminal artifact must retain its exact project-update
  workflow, decision, candidate, project, digest, scope, and terminal metadata;
- the candidate link must have exactly one append-only
  `project_update_review` revision of the action-appropriate type and exactly
  one actor-coupled accepted/rejected event;
- ordinary evidence validates the original linkage and decision fields, while
  authorized true redaction is accepted only as the exact preserved
  revision/event skeleton and accepted-event integrity hash clearing;
- current memory contents, lifecycle status, key, project linkage, row
  existence, and current project state are intentionally excluded from the
  historical proof; and
- forced generic HTTP, MCP, and CLI terminal side-door states still fail with
  the fixed 409/error and zero mutation, while genuine accepted/rejected
  replay remains mutation-free after supported evolution and PostgreSQL true
  redaction. SQLite store tests cover preservation of the same redaction
  skeleton because SQLite does not expose the project/artifact repository
  surface required for service replay.

Historically, Refreeze 6 completed 3,197 unit tests, 447 role-separated
PostgreSQL tests, release-static, LongMemEval, web invariance, and reproducible
installed wheel/sdist checks. It recorded tracked patch
`0527362a0876d8807488ba3db4818cac6a3da83b06eb8a544619036ca888d3d4`,
pre-carrier bundle
`966429239311313957baf616967a933f0e197f7f25f021332caf93c2066b5672`,
wheel SHA-256
`1994bd808a618f670dea7f7bcb50f3f034ee032afa0b78c4a355da5bd7e60670`,
and sdist SHA-256
`1137b5a3b99f7023aa5bc0da7a165a953864fd2ea5b60a6fc7746ed2b81a9e8f`.
Refreeze 7 changes only the untracked handoff carrier; `BUILD_REPORT.md`
records its historical bundle. Those results and hashes are superseded by
Repair Batch 8 and do not approve the current tree. Clean-SHA semantic
attestation, version finalization, and publication remain external gates, and
no approval from an earlier tree carries over.

## Builder Repair Batch 8 review deltas

The sixth independent review found two bounded defects after the Refreeze 7
carrier:

- The terminal guard selected the expected event too early. Batch 8 now
  gathers every artifact/candidate-coupled accepted/rejected decision event,
  requires exactly one total, and only then validates outcome, actor, action,
  target, payload, and redaction form. Regressions inject accepted plus
  rejected evidence, an extra accepted event with the wrong action, and two
  rejections; service and all six generic/dedicated HTTP/MCP/CLI adapters fail
  closed without mutation. Live PostgreSQL covers competing accepted and
  rejected evidence while valid replay remains green.
- Persisted-source reads incorrectly treated the stored source envelope as a
  flat resource, allowing a stale outer alias to override embedded canonical
  scope. Batch 8 applies the complete source-envelope precedence to SQLite and
  PostgreSQL source/parent-chunk search, every retrieval source admission arm,
  Brain, Projects, Connections, Contradictions, and HTTP artifact-trace
  authorization. E0 and E1 controls lock explicit-empty suppression and
  real-project-only visibility, including string/finite-integral/explicit-
  boolean parity and fractional/non-finite/mapping/null exclusion.

Historical Batch 8 evidence includes 3,230 unit tests (75.58% overall coverage;
52.64% for `main.py`), 450 role-separated PostgreSQL tests, `release-static`,
127 model-free LongMemEval tests, and the full byte-identical web type/lint/
unit/coverage/build/budget/Playwright matrix. Two fresh package builds were
byte-identical, Twine and release-check passed, and isolated wheel/sdist smokes
passed. Their SHA-256 values are wheel
`72feafee3f423f283a454a0ded6f7ffd49848fef159e344da782076f7113932e`
and sdist
`1b5f8bb48ccd82a1da494403fd813e7c7ad62b7c2b50b57cfd082fc40027d118`.
Its tracked-patch and bundle fingerprints were recorded in the self-excluded
`BUILD_REPORT.md` and reproduced twice. The subsequent independent review
returned changes required, so none of those results or hashes approves the
current tree.

## Historical Builder Repair Batch 9 review deltas (superseded)

The independent review of the twice-fingerprinted Batch 8 carrier returned
eight bounded findings. Batch 9 closed only those findings:

1. Capture validates source envelope and classification on fast-key,
   content-hash, and atomic dedupe paths. SQLite and PostgreSQL update stale
   dedupe keys atomically with identity-bearing fields; collisions fail closed
   and the HTTP review transaction rolls back before returning `409`.
2. Key-bound core MCP `alice_explain` authorizes complete memory chains,
   provenance sources, entity-backing memories, and continuity objects before
   expansion and uses a generic no-leak unavailable result on failure.
3. Terminal replay binds candidate-created evidence to exactly the locked
   artifact, with exact ordinary/redacted forms and same-target repetition.
4. Python, SQLite, PostgreSQL, and migration `0090` share finite-integral
   numeric scope normalization while rejecting fractional/non-finite values
   and preserving the established explicit boolean scalar contract.
5. The legacy MCP context tree scopes five resource groups before limits and
   admits only source-aware rows and their target-specific event group. It
   remains outside the core MCP surface and disabled on key-bound servers.
6. MCP open-loop and resume reads scope rows before bounded limits and read
   only events coupled to admitted targets.
7. The completed Upgrade Overview below supplies the protected-path metadata
   for the memory-schema and continuity-API changes.
8. Control documents distinguish Batch 8's historical twice-reproduced
   fingerprints and changes-required review from Batch 9's then-current freeze.

Batch 9 builder evidence was green: 3,301 units at 75.6699% coverage, the
52.6343% `main.py` floor, 455 role-separated PostgreSQL integrations, 127
LongMemEval tests plus evidence replay, release-static, the 280-test/10-case web
matrix, two byte-identical fresh package builds, archive byte parity, and both
isolated installed-artifact smokes. The 906-unit/18-PostgreSQL/3-migration
focused seam sweep and 47 control/guard tests also passed. Final fingerprints
were recorded in the self-excluded builder report and reproduced twice. The
subsequent independent review returned changes required on five bounded
findings, so that evidence does not approve the current tree.

## Builder Repair Batch 10 review deltas

The Batch 9 review returned changes required on five bounded findings. Repair
Batch 10 closes only those findings:

1. A non-null `supersedes` or `superseded_by` pointer that cannot be resolved
   now fails before raw audit or explanation-envelope reads. Key-bound core MCP
   calls return the same identifier-free unavailable response; complete,
   authorized chains and keyless validation semantics remain intact.
2. Generic PostgreSQL memory, artifact, and open-loop scope predicates now
   honor nested canonical `project_scope` under both `agentic_memory` and
   `agent_identity`, including the established string, finite-integral, and
   boolean scalar forms. Presence is authoritative even when the canonical
   value is empty, null, or malformed, so stale aliases cannot widen access.
3. Resume decision/open-loop status, project, query, and time predicates run in
   each store before row limits. Recent memory and open-loop events are joined
   to scope-admitted targets and event-time bounded before their limits, so old
   targets with new events cannot be starved by newer foreign rows. The legacy
   explicit project matcher is no longer part of resume admission.
4. Context-tree documentation now describes five resource groups plus events,
   no entity group, and the actual legacy boundary: `alice_vnext_context_tree`
   is outside the core MCP surface and disabled on key-bound servers.
5. Control-document regressions record Batch 9 as historically frozen and
   twice fingerprinted before its changes-required review. The final Batch 10
   carrier then proceeded to its own independent review.

Batch 10 builder evidence was green: 3,325 units with coverage floors, 457
role-separated PostgreSQL integrations, the 1,171-test integrated seam,
release-static, 127 LongMemEval tests plus evidence replay, the unchanged web
carrier, reproducible packages, archive parity, and installed-artifact smokes
passed. Its final fingerprints reproduced twice. The subsequent independent
review returned changes required on exactly two bounded findings, so no Batch
10 result or hash approves the current tree.

## Builder Repair Batch 11 review deltas

Repair Batch 11 closes only the two findings returned by the Batch 10 review:

1. Persisted-source PostgreSQL predicates and migration `0090` now choose the
   nested `agentic_memory`/`agent_identity.project_scope` tier by property
   presence. A present blank, null, malformed, or fractional value resolves to
   an empty identity and cannot fall through to a stale alias; valid scalar and
   array leaves, both nested containers, source/parent-chunk admission, and
   migration dedupe identity retain Python/SQLite parity.
2. `alice_resume.query` now reaches open-loop row and event joins before limits
   in both stores. Loop title, description, next-action metadata, and relevant
   event payload text participate. Scoped and unscoped calls exclude newer
   mismatching noise from `open_loops`, `next_action`, and `recent_changes`,
   while queryless calls retain their established ordering and content.

Focused Batch 11 evidence is green: 7 persisted-source/migration tests, 3
resume-query tests, 595 owned/shared units, 9 role-separated PostgreSQL
scope/source/resume cases, and 4 migration `0090` cases passed. Ruff, format,
mypy on the three touched production files, and `git diff --check` passed. The
final full gate passed 3,327 units at 75.72% coverage and 460 role-separated
PostgreSQL integrations. Release-static, 127 LongMemEval tests plus evidence,
the unchanged web carrier, reproducible packages, archive parity, and both
installed-artifact smokes passed. Final fingerprints reproduced twice.
Independent review approved the persisted-source closure and every other
bounded area, but returned changes required on one event-payload P2; Batch 11
evidence is historical.

## Historical Builder Repair Batch 12 review deltas (review rejected)

Batch 12 closes only the one P2 returned by the Batch 11 review:

1. SQLite event-payload query matching uses recursive `json_tree` string-leaf
   rows. PostgreSQL uses recursive `jsonb_path_query` values restricted to the
   JSON string type. Both compare case-insensitively and cannot match keys,
   numbers, booleans, nulls, or serialization punctuation.
2. The fake store mirrors value-only recursive matching and blank-query
   normalization. Real SQLite and live PostgreSQL tests cover scoped and
   unscoped requests, nested object and array strings, the key-only negative
   `{"text":"completely unrelated value"}` queried with `text`, and 62 newer
   mismatch rows before the older matches.

Focused Batch 12 evidence is green: 442 owned units and all 9 cases in the
role-separated PostgreSQL scope/source/resume file passed. The three focused
SQLite, PostgreSQL SQL-shape, and live PostgreSQL regressions passed
independently. Ruff, format, mypy on both stores, diff-check, and the
pre-documentation release-static gate passed. Full final gates, package
evidence, and final fingerprints subsequently passed. Independent review
approved the production SQLite/PostgreSQL recursive-leaf behavior but returned
changes required because the fake store could match a query across text from
different leaves. Batch 12 evidence and fingerprints are historical.

## Historical Builder Repair Batch 13 review deltas (never frozen)

Batch 13 changed only the MCP fake so each recursive string leaf was evaluated
independently. Two focused regressions, the complete 256-test MCP file, and
3,328 full units passed. Exact production-file hashes remained those of Batch
12, so its 460-case PostgreSQL result was carried without rerun.

Batch 13 was never frozen and never received static, package, fingerprint, or
release approval. Independent review returned one Unicode/collation P2 because
the fake's Unicode folding and the two SQL backends did not define one
deterministic non-ASCII comparison rule.

## Historical Builder Repair Batch 14 review deltas (review rejected)

Repair Batch 14 was the frozen predecessor. It established
**ASCII case-insensitive literal substring** matching across SQLite,
PostgreSQL, and the fake for both open-loop row fields and each recursive event
string leaf.
ASCII letters fold; non-ASCII code points remain exact, with no normalization
or locale dependency. `%`, `_`, and backslash are literal characters rather
than pattern operators. Cross-leaf matching stays forbidden. Blank queries,
scope/status/time-before-limit predicates, event ordering, scoped/unscoped
behavior, optional defaults, and queryless behavior remain unchanged.

Batch 14 builder verification is green: 4 focused units, 338 complete MCP/store
units, 3,329 full units with branch-inclusive coverage 49,494/65,357
(75.72869011735544%) and `main.py` coverage 4,126/7,839
(52.63426457456308%, above 45%), and 461 role-separated PostgreSQL integrations
all passed. Release-static/control checks, 127 LongMemEval tests plus evidence
replay, unchanged-web readback, and two reproducible package builds with
Twine/release-check/archive parity and isolated wheel/sdist smokes also passed.
The final tracked-patch and fixed 12-file remediation-bundle fingerprints
reproduced twice and are recorded in the self-excluded builder report.
Independent review returned changes required on exactly three bounded P2s:

1. Non-string root/nested metadata `next_action` values were not excluded with
   one identical row-candidate rule across SQLite, PostgreSQL, and the fake.
2. Alpha documentation described the ASCII/exact/literal comparison rule more
   broadly than the implementation surface, incorrectly reaching
   decision-memory and next-action-memory search.
3. `FakeVNextMCPStore.list_open_loops` omitted `created_at` from the production
   tie-break order.

Batch 14 gates, packages, source/test hashes, and twice-reproduced fingerprints
are historical and do not approve the current tree.

## Historical Builder Repair Batch 15 review deltas

Repair Batch 15 was a bounded correction and changed only those three
reviewed areas. Root `metadata_json.next_action` and nested
`metadata_json.agentic_memory.next_action` are row candidates only when their
JSON value is a string in SQLite, PostgreSQL, and the fake. Recursive event
payload matching remains limited to each individual string leaf and is
otherwise unchanged. The fake open-loop list must order by `opened_at DESC`,
then `created_at DESC`, then `id DESC`. Alpha documentation must limit the
**ASCII case-insensitive literal substring**, exact non-ASCII, and literal
`%`/`_`/backslash contract to open-loop row fields and loop-event leaves; it
does not define decision-memory or next-action-memory search.

Batch 15 builder verification is green. Five focused units, 339 complete owned
MCP/store units, the focused and complete affected PostgreSQL files, 3,331 full
units with required statement/branch/`main.py` coverage floors, 44 control
tests, and 461 role-separated PostgreSQL integrations all passed.
Release-static, mirror/diff checks, 127 LongMemEval tests plus evidence replay,
unchanged-web readback, and two byte-identical normalized package builds with
Twine/release-check/archive parity and isolated wheel/sdist smokes also passed.
The final tracked-patch and fixed 12-file remediation-bundle fingerprints
reproduced twice and are recorded in the self-excluded builder report.
Independent review subsequently approved that exact carrier, but the Batch 16
embedding-CAS whitespace finding superseded it.

## Builder Repair Batch 16 review delta

Independent review approved the frozen Batch 15 open-loop correction, but the
engineering team then found one pre-tag embedding-CAS truth gap. PostgreSQL's
SQL mirror of Python `str.strip()` used locale-dependent POSIX `[[:space:]]`.
That form deterministically omits U+001C–U+001F and can differ for NBSP-class
whitespace, even though migration `0090` already uses an explicit CPython 3.12
29-codepoint table. Batch 15's approval is therefore historical and cannot
approve the current tree.

Repair Batch 16 changes only `vnext_store.py`'s private embedding-content
digest SQL plus fail-on-old unit, live role-separated PostgreSQL, and truth-
documentation evidence. The runtime now uses `btrim` with the same 29
`chr()`-enumerated codepoints as migration `0090`; it does not import migration
code. Title, canonical-text, and summary order, blank omission, first-
occurrence deduplication, LF joining, and SHA-256 remain unchanged.

The unit SQL-shape regression binds all three consumers—signed vector-search
freshness, signed update CAS, and missing-embedding selection—to every
codepoint and rejects the POSIX trim. Live cases cover NBSP, U+001C, and a
mixed blank/deduplicated field shape through successful CAS, empty re-embed
selection, and signed vector participation. Focused verification passed 4
selected units, all 82 affected units, 3 focused PostgreSQL cases, and all 4
affected PostgreSQL cases. The full unit gate passed 3,332 tests at 75.7255%
branch-inclusive coverage; `main.py` statement coverage was 54.7181%, above
its 45% floor. All 463 role-separated PostgreSQL integrations passed.
Release-static/control, 127 LongMemEval tests plus evidence replay, exact
unchanged-web readback, and two byte-identical package builds with Twine,
release-check, seven-file archive parity, and isolated wheel/sdist smokes
passed. Final tracked-patch and fixed 12-file bundle fingerprints reproduced
twice and are recorded in the self-excluded builder report. Batch 16 review
approved the production CAS semantics and returned changes required on one
documentation-truth P3. Refreeze 17 changes only that stale Batch 15/current-
review wording plus its fail-on-old control guard. Independent review of the
exact Refreeze 17 carrier remains required.

## Copy-ready protected-path metadata

The structure below is complete and its Batch 16 Validation paragraph contains
the current exact production evidence; the Refreeze 17 builder receipt is in
`BUILD_REPORT.md`. Do not copy it into a finalization pull
request until the exact frozen carrier is independently approved. Then prepare
and validate the body
before committing; after pushing, run the actual protected-path guard against
the real pull-request event before merge.

```md
## Upgrade Overview

### Protected Areas

- [x] memory schema
- [ ] evidence pipeline
- [ ] trust rules
- [ ] promotion logic
- [x] continuity APIs

### Compatibility Impact

This is a behavior-changing but backward-compatible isolation correction. It tightens capture/dedupe identity, key-bound explanation expansion, context-tree/open-loop/resume project filtering, and terminal replay evidence without changing request shapes. Finite mathematically integral numeric project identifiers are canonicalized across backends; fractional and non-finite numbers are rejected, while the established explicit true/false scalar identifiers remain supported.

### Migration / Rollout

Back up and rehearse before production. The corrected 0083 protects only future 0082-to-head upgrades; a database that already ran the older 0083 may have irreversibly lost explicit-empty intent and requires backup or audit evidence. Migration 0090 performs forward normalization and deterministic dedupe repair. Run migrations before starting application or scheduler processes, and deploy both from the same verified SHA. No feature flag is used.

### Operator Action

Take and verify a restorable backup. Before migration, run the documented 0087 and 0089 duplicate-group preflight and resolve any collision with evidence-backed survivor/loser handling. After migration, verify the Alembic head, unique indexes, and representative scope readback. Record evidence for any database that previously ran the older 0083. No other manual data repair is prescribed.

### Validation

Batch 16 review approved the production CAS semantics and returned changes required on one documentation-truth P3. Refreeze 17 changes only the stale Batch 15/current-review wording and its fail-on-old control guard. Its focused and final verification plus fingerprints are recorded in the self-excluded builder report. Independent review of the exact Refreeze 17 carrier remains required; historical Batch 15 and Batch 16 reviews do not satisfy that gate.

### Historical pre-review Batch 16 Validation

Batch 16 replaces the locale-dependent POSIX memory-embedding digest trim with migration 0090's explicit CPython 3.12 29-codepoint chr() table while preserving field order, blank omission, first-occurrence deduplication, LF joining, and SHA-256. The fail-on-old SQL-shape test proves signed vector freshness, signed update CAS, and missing-embedding selection each contain all 29 codepoints, including U+001C–U+001F, NEL, and NBSP, and contain no POSIX trim. Four focused units and all 82 affected units passed. Three focused live role-separated PostgreSQL cases and all 4 affected PostgreSQL cases passed, proving CAS acceptance, no re-embed loop, and signed vector participation for NBSP, U+001C, and mixed blank/deduplicated fields. The final unit gate passed 3,332 tests with 75.7255% branch-inclusive coverage and 54.7181% main.py statement coverage against its 45% floor; all 463 role-separated PostgreSQL integrations passed. Release-static/control, 127 LongMemEval tests and seven-arm evidence replay, exact unchanged-web readback, two byte-identical package builds, Twine, release-check, seven-file workspace/wheel/sdist parity, archive exclusions, and installed wheel/sdist smokes passed. The final tracked-patch and fixed 12-file bundle fingerprints reproduced twice and are recorded in the self-excluded builder report. Independent Batch 16 review remains required; the historical Batch 15 approval does not satisfy this gate.

### Historical Batch 15 Validation

Batch 15 builder verification passed the string-only root/nested metadata `next_action` row-candidate contract across SQLite, PostgreSQL, and the fake; unchanged per-string-leaf loop-event payload matching; fake `opened_at DESC`, `created_at DESC`, then `id DESC` ordering; and alpha-documentation scope limited to open-loop row fields and loop-event leaves rather than decision-memory or next-action-memory search. Five focused units passed with 334 deselected in 0.41 seconds, the complete owned MCP/store seam passed 339 tests in 0.53 seconds, focused live PostgreSQL passed 1 with 9 deselected in 1.25 seconds, and the affected PostgreSQL file passed all 10 in 11.54 seconds. The initial fixture run passed 4 and failed 1 because the blank-query expectation requested 23 rows through the established default limit of 20; setting that fixture's explicit limit to 50 produced the clean pass without changing production behavior. The first live PostgreSQL attempt was sandbox-blocked; the approved rerun passed. The full unit gate passed 3,331 tests in 62.90 seconds with combined branch-aware coverage 49,494/65,361 (75.7241%), statement coverage 40,520/51,557 (78.5926%), branch coverage 8,974/13,804 (65.0101%), `main.py` statement coverage 3,775/6,899 (54.7181%, above 45%), and branch-aware `main.py` coverage 4,126/7,839 (52.6343%). The control suite passed 44 tests in 0.26 seconds and the role-separated PostgreSQL gate passed 461 tests in 465.73 seconds, for 3,792 tests in 528.63 seconds. Release-static passed in 1.31 seconds with 14 control documents, release-check, Ruff, and mypy over 146 files; format, `py_compile`, mirror, and diff checks passed. LongMemEval passed 127 tests in 4.26 seconds against a 4.67-second target plus evidence replay, preserving the 892-row baseline SHA-256 `027db2960a761d44bb3b20e9ed04a5f434a16d88a3ff9cf65b43a64a3b96589f`. The unchanged web carrier was read back without rerun at 202-input digest `f02db64c821d16481a7f9e49dcb7812c0347989e0cf7d310afbfaa02a9ee630b`, diff digest `df3f667a4e06be6a998478a5a4b4ee0af4a2f27b4cbe7b516b7a80b85aa1e0d4`, and lock digest `f684d9f418db5b6b52964cdafdf27ab326aa68b777c5fc1a7b90dc4f7a4206d9`, carrying the prior 71-file/280-test coverage/types/lint/build/budgets and 10-browser-case evidence. Two package builds completed in 3.68 and 3.12 seconds and normalized in 0.40 seconds each to byte-identical archives: the 1,224,931-byte wheel SHA-256 was `8fd31e9cb289da7b85389201eecfa1160f5e8ca2afd6abca6dc18eb7e838b407`, the 1,071,126-byte sdist SHA-256 was `263666ccc16faced4a54f270edefc17359c8dad128414220342ecd776f28f2a6`, Twine passed in 0.29 seconds, release-check passed in 0.17 seconds, and seven-file parity, exclusions, and 15.03/15.66-second isolated smokes passed; repository `dist/` was untouched. The final tracked-patch and fixed 12-file remediation-bundle fingerprints reproduced twice and are recorded in the self-excluded builder report. The independent reviewer must approve that exact frozen Batch 15 carrier. Historical review-rejected Batch 14 evidence does not satisfy this gate.

That final Batch 15 pending-review sentence is retained only as the historical
builder receipt. `REVIEW_REPORT.md` later approved Batch 15, and the Batch 16
engineering finding then superseded that approval.

### Rollback

Stop application writers and the scheduler before rollback. Do not blindly downgrade schema revisions after 0090; restore the verified pre-upgrade backup, then redeploy the previously verified application and scheduler SHA together. An older 0083 execution that erased explicit-empty intent has no automatic rollback and must be resolved only from external evidence.
```

## Already-executed `0083` evidence limitation

The candidate source intended for v0.10.4 corrects `0083` for future upgrade
chains. A database upgraded from `0082` or earlier using these bytes preserves
every present canonical scope and still backfills a truly absent legacy scope.
The v0.10.3 tag and published artifacts are not changed.

The remaining limitation applies only when a database already ran an older
packaged copy of `0083` and that execution erased explicit-empty intent. Before
approving v0.10.4 for such a database:

1. Rehearse against a restored representative backup.
2. Compare backup/audit evidence with the post-`0083` row; do not infer intent
   from the resulting scope alone.
3. Apply only an evidence-backed repair procedure for affected rows.
4. Do not claim already-erased project-scope intent can be repaired
   automatically.

## Finalization sequence

1. Preserve the immutable v0.10.3 release notes/checksums and historical tag.
   Do not begin finalization until `BUILD_REPORT.md` contains the complete
   Batch 16 focused, full Python/PostgreSQL, web, package, documentation,
   repository-readback, and fingerprint evidence and the independent reviewer
   has approved the exact Refreeze 17 truth carrier. Batch 16 review approved
   the production CAS semantics and returned one documentation P3; Batch 15
   was independently approved before the engineering-team CAS finding and is
   now historical. Neither historical review satisfies the Refreeze 17 gate.
2. Review `git diff` and remove no user-owned files. `coverage.json` and
   `uv.lock` predate this remediation and remain untracked.
3. Before the finalization commit, bump every governed version source to
   `0.10.4`, including `pyproject.toml` and `apps/web/package.json`, and align
   the candidate-mode control documents. Move the candidate changelog entries
   under a dated v0.10.4 heading and finalize the v0.10.4 release-note
   title/body with the exact line-2 structured state still
   `pending`/`pending`. Do **not** create
   `docs/release/v0.10.4-checksums.txt` yet.
4. Before committing, prepare the pull-request body with the completed Upgrade
   Overview above and validate it locally. Commit and push the finalization
   tree, then run the actual protected-path guard against the real pull-request
   event. Merge through protected `main` only after that guard and review pass.
   Select the resulting clean SHA only after confirming it is the exact remote
   `main` head.
5. Run the complete clean-SHA release matrix from `RELEASING.md` using the
   copy-paste block below. It requires brand-new empty `DIST_DIR` and
   `REPRO_DIST_DIR` paths, role-separated PostgreSQL, the `0082`→head
   migration-chain regression, web gates, reproducible distributions,
   `make release-finalization-check`, and the required GitHub checks on that
   exact SHA. Never reuse or clear user-owned artifact directories.
6. Run the provider-backed semantic release gate against that exact SHA with
   the configured OpenAI embedding provider. Inspect the credential-free
   report and attestation and confirm their source SHA, report digest, passing
   suites, PostgreSQL backend, and positive signed-vector candidate count.
7. Create an annotated `v0.10.4` tag on the verified SHA. Run
   `release_check.py` with `--tag v0.10.4`, `--expected-sha`,
   `--require-main-head`, and `--require-clean`; read back and attest the
   external controls; reverify the exact-SHA semantic artifact; and confirm no
   stable GitHub Release already exists for the tag.
8. Dispatch `publish-pypi.yml` from the annotated tag in `publish` mode. Do
   not create a GitHub Release manually: the workflow stages and verifies the
   draft, publishes those same bytes to PyPI, then finalizes that draft.
9. After public readback succeeds, create a separate evidence-backed
   post-publication commit that adds the durable
   `docs/release/v0.10.4-checksums.txt` and changes the structured release-note
   state to `published`/`recorded` together with the active-document truth
   update.

### Copy-paste clean-SHA matrix

Run without `-j`. Configure the required role-separated PostgreSQL and
embedding-provider environment first. `release-check` already invokes
`release-artifacts`; do not invoke that target separately.

```sh
set -eu

make setup
make setup-browser
make migrate
make release-finalization-check

release_run_root="$(mktemp -d /tmp/alice-release-check.XXXXXX)"
dist_dir="$release_run_root/dist"
repro_dist_dir="$release_run_root/reproducibility-check"
semantic_dir="$release_run_root/semantic"

mkdir "$dist_dir" "$repro_dist_dir" "$semantic_dir"

for directory in "$dist_dir" "$repro_dist_dir" "$semantic_dir"; do
  test -z "$(find "$directory" -mindepth 1 -maxdepth 1 -print -quit)"
done

make release-check \
  DIST_DIR="$dist_dir" \
  REPRO_DIST_DIR="$repro_dist_dir" \
  PYTHON_COVERAGE_JSON="$release_run_root/python-coverage.json" \
  SEMANTIC_EVAL_ARTIFACT_DIR="$semantic_dir" \
  SEMANTIC_EVAL_REPORT="$semantic_dir/semantic-eval-report.json" \
  SEMANTIC_EVAL_ATTESTATION="$semantic_dir/semantic-eval-attestation.json"

printf 'Release evidence retained under %s\n' "$release_run_root"
```

The Makefile performs no cleanup or emptiness check. It writes the primary
wheel, sdist, and `SHA256SUMS` to `DIST_DIR` and the comparison build to
`REPRO_DIST_DIR`. Pass both values explicitly, retain the temporary root as
evidence, and never delete, overwrite, or rely on ignored historical
`dist/` artifacts.

## External-only items intentionally not performed

- Version bump and release commit selection.
- Provider-backed semantic attestation for the final clean SHA.
- GitHub Actions/release-environment approval.
- Tag, push, GitHub Release, PyPI publication, or public metadata readback.
- Post-publication active-document flip.

# Alice v0.10.4 Fifth-Audit Surface Inventory

## Identity and boundary

- Inventory date: 2026-07-14
- Base branch: `main`
- Base HEAD: `d52e32114eb0b4ef63499e53be14b70dc0864487`
- Published runtime baseline: immutable `v0.10.3` tag at
  `948a75c040e79186a1d3c1675cf216cf2ca0c82b`
- Scope: non-security correctness, persistence, API/documentation truth,
  provider runtime, web behavior, migrations, tests, and release tooling.
- Explicit exclusion: cybersecurity audit.
- Immutable files excluded from edits:
  `docs/release/v0.10.3-release-notes.md` and
  `docs/release/v0.10.3-checksums.txt`.
- Version sources remain `0.10.3` during this uncommitted remediation. The
  release engineer selects and commits the next version only after review.

This inventory was completed before source-code edits. It records every
reachable HTTP, MCP, CLI, scheduler, web, PostgreSQL, and SQLite surface for
the fifth-audit findings. A dash means that the behavior has no implementation
on that surface, not that the surface was skipped.

## Summary matrix

| Finding | HTTP | MCP | CLI | Scheduler | Web | PostgreSQL | SQLite |
|---|---|---|---|---|---|---|---|
| P1-1 hosted workspace selection | 23 resolver-backed Telegram operations | - | - | receives explicit workspace after HTTP resolution | 14 Settings operations | hosted channel services/tables | - |
| P1-2 project-update lifecycle | generic + dedicated review; generic memory lifecycle | generic + dedicated review; generic memory lifecycle | generic + dedicated review; generic memory lifecycle | generates only | generic artifact/memory actions | artifacts, projects, memories, revisions, events | generic memory lifecycle only |
| P1-3 explicit-empty project scope | all scope-bearing vNext requests | capture/recall/context/commit/automation | capture/recall/connectors/automation | filters and grouping | indirect callers | runtime predicates correct on key presence; historical migration affected | memory/source/open-loop predicates, dedupe, bootstrap affected |
| P1-5 OpenAPI truth | all 294 operations | raw service-shape evidence only | raw service-shape evidence only | result shapes feed four HTTP contracts | hand-written client types only | direct row envelopes | parity evidence for shared raw service shapes |
| P1-6 package description | artifact metadata validation | - | installed-artifact smoke | - | PyPI rendering only | - | - |
| P2 provider no-auth | config bootstrap/PATCH, provider test, runtime invoke | - | - | separate provider path | - | provider records | - |
| P2 API base prefix | server HTTP origin | - | - | - | every `requestJson` caller + clipper display | - | - |
| P2 reviewer attribution | generic/dedicated review | generic/dedicated review | generic/dedicated review | generation already attributed | uses HTTP | revisions/events/artifacts | generic memory events |
| P2 web truth/performance | existing APIs only | - | - | - | onboarding, navigation, admin, tasks/artifacts/memories/traces | - | - |
| P2 embedding CAS | - | - | backfill/reindex callers | embedding workflows | - | SQL digest mirror | Python UDF already aligned |
| P2 migration operations | operator upgrade path | - | Alembic command | - | - | migrations 0087-0089 | - |

## P1-1: hosted Settings workspace selection

### Web inventory

`HostedSettingsPanel` is the only client and invokes 14 method/path pairs.

Already explicit:

- `POST /v1/channels/telegram/link/start`
- `GET /v1/channels/telegram/status`
- `POST /v1/channels/telegram/unlink`

Challenge-bound rather than session-selected:

- `POST /v1/channels/telegram/link/confirm`

Missing the entered workspace on current HEAD:

- `GET /v1/channels/telegram/messages`
- `GET /v1/channels/telegram/threads`
- `GET /v1/channels/telegram/delivery-receipts`
- `GET /v1/channels/telegram/notification-preferences`
- `PATCH /v1/channels/telegram/notification-preferences`
- `GET /v1/channels/telegram/daily-brief`
- `POST /v1/channels/telegram/daily-brief/deliver`
- `GET /v1/channels/telegram/open-loop-prompts`
- `POST /v1/channels/telegram/open-loop-prompts/deliver`
- `GET /v1/channels/telegram/scheduler/jobs`

### HTTP inventory

Twenty-three channel handlers call
`_resolve_workspace_for_hosted_channel_request`. Three already pass a
requested workspace. The following 20 pass `None` on current HEAD and need an
optional explicit `workspace_id`:

- `list_v1_telegram_messages`
- `list_v1_telegram_threads`
- `dispatch_v1_telegram_message`
- `list_v1_telegram_delivery_receipts`
- `get_v1_telegram_notification_preferences`
- `patch_v1_telegram_notification_preferences`
- `get_v1_telegram_daily_brief`
- `post_v1_telegram_daily_brief_deliver`
- `list_v1_telegram_open_loop_prompts`
- `post_v1_telegram_open_loop_prompt_deliver`
- `list_v1_telegram_scheduler_jobs`
- `handle_v1_telegram_message`
- `get_v1_telegram_message_result`
- `list_v1_telegram_recall`
- `get_v1_telegram_resumption_brief`
- `get_v1_telegram_open_loops`
- `review_action_v1_telegram_open_loop`
- `list_v1_telegram_approvals`
- `approve_v1_telegram_approval`
- `reject_v1_telegram_approval`

The resolver currently calls `set_session_workspace` in both the requested
and fallback branches. Channel reads and actions must resolve without mutating
the authenticated session's selected workspace. Explicit workspace-selection
endpoints remain the only writers of that session preference.

Downstream `telegram_channels` and `telegram_notifications` service methods
already receive a concrete workspace ID. Scheduled jobs are PostgreSQL-only
and correctly key their rows by that value. There is no equivalent MCP, CLI,
or SQLite hosted-channel surface.

### Required regressions

- Web: every Settings request uses entered workspace B regardless of action
  order.
- HTTP: with session workspace A and explicit B, preferences and brief
  delivery touch only B.
- Resolver: selecting B for a channel call does not persist B into the
  authentication session.
- Class guard: all 20 handlers accept and pass an explicit workspace.

## P1-2: project-update artifact and candidate-memory lifecycle

### Every `review_artifact` caller

| Caller | Current behavior |
|---|---|
| Generic HTTP review (`main.py`) | Dispatches project candidates to `review_project_update` |
| Generic MCP review (`mcp_tools.py`) | Dispatches project candidates to `review_project_update` |
| Generic CLI review (`cli.py`) | Calls `VNextQueueService.review_artifact` directly; defective |
| CLI smoke-review helper | Reviews a known non-project artifact |
| Web artifact actions | Use the generic HTTP endpoint |
| Scheduler | Generates project candidates; never reviews them |

Dedicated project-review callers also exist in HTTP, MCP, and CLI. The
generic queue transition table allows `accepted -> rejected`; therefore both
central dispatch and defense-in-depth generic-queue refusal are required for
`project_auto_update` artifacts.

### Candidate-memory coupling

`generate_project_update_candidate` creates a `project_state` candidate and
links it from the artifact through `candidate_memory_id`, project identity,
scope, workflow, and automation digest. `review_project_update` currently
checks only artifact classification/status and candidate existence before
activating the memory.

The coupled review must require, under the existing row locks:

- memory status exactly `candidate`;
- memory type `project_state`;
- workflow `project_auto_update`;
- matching automation digest;
- matching project ID and canonical scope;
- no contradictory retired/superseded linkage.

Generic memory lifecycle remains independently reachable through:

- HTTP review, undo, correct, forget, expire, unexpire, and redact;
- MCP canonical review/correct/manage and legacy vNext aliases;
- CLI undo, correct, forget, expire, unexpire, and redact;
- web generic memory actions.

Those operations can retire a candidate. A later coupled artifact decision
must fail closed rather than resurrecting it. PostgreSQL owns project/artifact
review; generic memory lifecycle also runs against SQLite, so the
classification/link-validation helpers must be backend-neutral where used.

### Reviewer attribution

Queue and project-review services currently discard authenticated identity
and hardcode `system` or incomplete `user` actors in artifacts, revisions, and
events. HTTP, MCP, and CLI review adapters must pass explicit actor type/ID
and trace/run IDs into a shared dispatcher and the service boundary.
Scheduler generation already uses `scheduler` and is unaffected.

### Required regressions

- HTTP, MCP, and CLI generic review all route project updates through the
  coupled service.
- Pending generic promote and accepted-to-rejected transitions fail on all
  three adapters.
- Retired, superseded, wrong-workflow, wrong-type, wrong-project, and
  wrong-digest candidate memories cannot be activated.
- Failed validation leaves artifact, project, memory, revision, and event
  state unchanged.
- Actor type/ID are preserved for human, agent, and CLI review events.
- Store-level memory classification/link helpers have SQLite/PostgreSQL
  parity where both stores implement the contract.

## P1-3 and P2 flagship: canonical project scope and identity

### Shared Python semantics

`vnext_project_scope.normalize_project_scope` currently collapses whitespace
but preserves case and first-seen order. `resource_project_scope` duplicates
that algorithm. Retrieval, consolidation, contradiction, connection,
scheduler, and roll-up code then add independent casefold/sort behavior.

The remediation contract is split deliberately. The inventory's original
`casefold` shorthand was refined during implementation and independent review
because SQLite and PostgreSQL cannot guarantee identical locale-independent
Unicode folding:

- presence-aware resolution decides whether legacy fallback is allowed;
- a canonical identity key collapses only ASCII SP/HT/LF/VT/FF/CR;
- ASCII-only identifiers map `A-Z` to `a-z`, while any identifier containing a
  non-ASCII code point, including Unicode whitespace, remains exact and
  case-sensitive;
- scope identity deduplicates as a set and sorts in Unicode code-point order,
  mirrored by PostgreSQL `COLLATE "C"` and SQLite binary ordering;
- display spelling may remain separate from the identity key.

A present canonical key, including `[]` or a malformed value, suppresses all
legacy fallback.

### SQLite inventory

Affected SQL and bootstrap classes:

- `_project_clause`: memory list/count/FTS/vector/time/staleness/roll-up
  callers; currently requires a non-empty canonical array.
- `_metadata_scope_clause`: sources, source chunks, and open loops; currently
  OR-flattens canonical and legacy fields without precedence.
- `find_live_memory_by_canonical_text`: repeats the non-empty check and
  compares raw JSON array order/case.
- `_backfill_legacy_memory_project_scopes`: selects canonical empty arrays and
  overwrites them on every bootstrap/reopen.
- source-capture dedupe backfill: sorts without shared casefold/dedupe
  semantics.

Explicit empty scope must survive repeated bootstrap unchanged, never match a
stale nested/direct project, and dedupe under the same identity as PostgreSQL.

### PostgreSQL inventory

The current `_jsonb_project_scope_values_sql` correctly honors canonical-key
presence. Its consumers cover memory events, source chunks, list/count,
staleness and roll-ups, FTS/vector/time search, sources, beliefs, open loops,
artifacts, and ratings. Comparisons and `find_live_memory_by_canonical_text`
still use raw case/order-sensitive JSON identity.

The pre-edit `0083` script rewrites canonical empty scope from nested legacy
metadata. The initial inventory incorrectly assumed the brief prohibited
amending that script. The final v0.10.4 remediation intentionally corrects its
canonical-key gate for future upgrade chains while leaving the v0.10.3 tag and
published artifacts untouched. Migration `0085` computes a different capture
identity than runtime and remains reconciled by forward migration `0090`.

### Transport and workflow callers

- HTTP: capture, connector ingestion, context/recall, review assignments,
  proposals/commit, project/open-loop automation, and scheduler routes.
- MCP: identity parsing/policy, recall/context, capture/ingestion,
  proposal/commit, and automation tools.
- CLI: capture/connectors, context/brief/proposal, generic retrieval,
  scheduler, connection/contradiction/project/open-loop commands.
- Scheduler: project filters, row matching, grouping, and digest identity.
- Web: mostly singular project IDs; it is an indirect HTTP contract consumer.

### Required parity matrix

Both SQLite and PostgreSQL must prove:

1. canonical `[]` suppresses stale nested/direct scope;
2. absent canonical key permits legacy fallback;
3. malformed present canonical scope fails closed;
4. ASCII case, order, duplicates, and ASCII whitespace share one identity,
   while non-ASCII case and Unicode whitespace remain exact;
5. exact live-memory and source-capture dedupe use that identity;
6. list/count, search, time, sources/chunks, loops, beliefs, artifacts, and
   roll-ups use the same overlap semantics;
7. SQLite reopen is idempotent and PostgreSQL fix-forward migration preserves
   explicit empty scope;
8. HTTP, MCP, CLI, and scheduler adapters preserve the shared identity.

## P1-5: OpenAPI response truth

### Inventory

- 294 live operations total.
- 49 exact Pydantic/TypedDict contracts.
- 245 literal registry entries.
- Of the literal entries, 65 are closed/source-verified and 180 are open.
- 176 of the 180 open contracts accept `{}` plus arbitrary keys.
- 102 open handlers already expose named `TypedDict` return types.
- Only 34 of those 102 advertised key sets match; 68 have phantom or missing
  keys.
- 78 additional routes return direct service/store/dataclass/JSON objects.

The mismatch class spans continuity, vNext, authentication, Telegram,
hosted/runtime, policies, tools, approvals, tasks, Gmail, calendar,
workspaces, artifacts, budgets, retrieval, embeddings, and entities. This is
materially broader than the five audit samples.

Required named samples:

- queue process-next -> `status,task_id,artifact_id,error_message`
- Telegram sync -> `ConnectorSyncResult` fields
- graph neighborhood -> `target_id,from_edges,to_edges,edge_count`
- belief review -> the authoritative belief-row fields
- belief state -> `belief_id,current,history,previous_statuses`
- project dashboard -> `project,state,memories,open_loops,artifacts,counts`
- scheduler run-now/run-due/pause/resume -> authoritative scheduler results

OpenAPI is HTTP-only. MCP and CLI return some of the same raw service results
and provide independent shape evidence. Scheduler result dictionaries are the
source for four HTTP contracts. Web does not generate types from OpenAPI.
Direct row envelopes originate in PostgreSQL; shared service return shapes
must remain compatible with SQLite-backed CLI/MCP execution.

### Bounded class-wide correction

- Derive and close the 102 already typed operations from their authoritative
  response types.
- For remaining unverified open routes, remove fabricated advertised
  properties rather than inventing envelopes.
- Keep only genuinely polymorphic response operations open, with each variant
  closed.
- Add manifest and representative actual-payload validation so the registry
  cannot self-validate against another speculative list.
- Do not redesign runtime payloads as part of this documentation repair.

## P1-6: publication-neutral package description

### Consumers

- `pyproject.toml` currently points project `readme` at `README.md`.
- Setuptools bakes that file into wheel `METADATA`, sdist `PKG-INFO`, and the
  PyPI project page.
- `release_check.py` verifies versions but not the long description.
- `test_distribution_artifact.py`, Twine, tests workflow, and publish workflow
  validate syntax/runtime only.

### Correction boundary

- Add evergreen `docs/pypi-description.md` with product purpose, install
  command, and stable documentation/releases links.
- It must contain no version literal, latest-version claim, candidate state,
  release-gating state, or version-specific release-note link.
- Point `pyproject.toml` at it without changing the package version.
- Validate both wheel `METADATA` and sdist `PKG-INFO` against the evergreen
  source and reject release-state language.

The existing v0.10.3 PyPI metadata is immutable. This correction affects the
next release only.

## P2 triage

### Confirmed and bounded

- **OpenAI-compatible no-auth invocation:** discovery uses `auth_mode`, but
  invocation drops it and sends the stored sentinel as a Bearer token. State
  is reachable through provider PATCH and workspace bootstrap configuration;
  provider test and runtime invoke share the broken adapter. PostgreSQL stores
  configuration; no SQLite/MCP/CLI/web twin exists.
- **Web API base prefix:** sanitization intentionally preserves path prefixes,
  but leading-slash URL resolution discards them for every `requestJson`
  caller. The fix must also preserve local vNext operator-key route detection
  and the browser-clipper displayed endpoint.
- **Navigation/copy:** Continuity is absent from global navigation; home cards
  omit Continuity and Chief-of-Staff; the page reports 14 rather than 16 views
  and two rather than three data modes.
- **Hosted admin rate metric:** it counts a capped mixed event list instead of
  the exact `rate_limited_count` already returned by the overview.
- **Serial API waterfalls:** task, artifact, memory, and trace pages perform
  independent selected-record reads serially. Each needs an all-settled
  parallel wave while preserving per-call fallback behavior. For traces,
  detail and ordered events must also retain independent provenance and render
  whichever leg succeeds; the live list summary is not proof that a rejected
  detail or event request was live.
- **Embedding CAS:** Python and SQLite use `str.strip`; PostgreSQL uses default
  `btrim`, which differs for tabs/newlines and can repeatedly mark valid
  embeddings stale.
- **Migration duplicate preflight:** migrations 0087 and 0089 detect invalid
  concurrent indexes but cannot choose which duplicate rows to retain.
  Existing 0087 integration coverage manually deletes a collision before
  retry; 0089 lacks the equivalent real collision regression. Operator
  preflight/repair guidance is absent.
- **Migration 0088 fingerprint stability:** the historical migration imports
  a runtime helper. Pin a named v1 helper and literal golden vectors so future
  runtime evolution cannot alter fresh historical upgrades silently.
- **Reviewer attribution:** confirmed across generic/dedicated artifact and
  project review; actor identity is discarded before revisions/events.
- **Active release-document truth:** README, CURRENT_STATE and its mirror,
  ARCHITECTURE, PRODUCT_BRIEF, ROADMAP, RELEASING, vNext README, integration
  reference paths, and headless install contain stale v0.10.2 links or claims.
  Truth checks do not reconcile checksum pointers, latest-release links,
  install tags, future-state language, or package-description neutrality.

### Confirmed but resized

- **Hosted onboarding:** the component is a static checklist with no API
  client for magic-link, session, workspace, bootstrap, devices, or
  preferences. Building a real wizard is a separate product feature. This
  remediation will truthfully label it as an instruction/preview surface and
  remove claims that actions are performed in the page.
- **Project identity:** substantially broader than the original three-word
  case/order/presence summary. The bounded remediation is the shared
  presence/identity core, all current store predicates/backfills/dedupe,
  retrieval admission, policy/key comparisons, scheduler grouping, and a
  fix-forward migration. It does not redesign project transport payloads.

### Rejected

- None after current-HEAD verification.

## Release/document truth inventory

Active consumers to update without claiming publication:

- `README.md`
- `CURRENT_STATE.md` and `.ai/handoff/CURRENT_STATE.md`
- `ARCHITECTURE.md`
- `PRODUCT_BRIEF.md`
- `ROADMAP.md`
- `RELEASING.md`
- `docs/vnext/README.md`
- `docs/integrations/reference-paths.md`
- `docs/alpha/headless-ubuntu-install.md`
- `CHANGELOG.md` unreleased section only
- `scripts/check_control_doc_truth.py` and unit tests
- `scripts/release_check.py` and artifact tests

Candidate-mode truth must continue to identify v0.10.3 as the latest
published immutable release while describing the current tree as uncommitted
v0.10.4 remediation. Latest-release notes, checksum pointers, and install tags
must all resolve to v0.10.3 until the release engineer performs the structured
post-publication truth update.

## Migration inventory

- `0083`: the pre-edit project-scope backfill can overwrite any present empty
  or malformed canonical scope. The candidate source intended for v0.10.4
  corrects the script for future `0082`→head chains; databases that already
  ran the older bytes require evidence-based repair if intent was erased.
- `0085`: historical source-dedupe identity differs from the new canonical
  runtime identity; leave immutable and document/reconcile forward.
- `0087`: interrupted concurrent unique-index build is retry-safe only after
  operators resolve duplicate data; add preflight/repair guidance.
- `0088`: backfill imports a mutable helper; pin v1 semantics and golden
  vectors without changing current output.
- `0089`: invalid-index retry exists, but add real duplicate-collision
  regression and the same operator guidance as 0087.

Migration `0083` is the one intentional in-place script correction in the
candidate source intended for v0.10.4; its revision ID and ordering are
unchanged. This does not rewrite the v0.10.3 tag, wheel, sdist, release notes,
or checksums. All other migration repairs remain additive/fix-forward.

## Repair Batch 8 correction appendix

This appendix corrects two incomplete conclusions in the historical pre-edit
inventory above. It describes the Batch 8 code-frozen tree; the original
inventory remains intact as the record of what was believed before edits.

### Terminal project-update decision-evidence surface

The earlier P1-2 inventory required a terminal artifact to retain a coupled
revision/event proof, but that statement was incomplete: selecting the expected
decision event before uniqueness validation allowed a second contradictory or
wrong-action event to remain outside the proof.

The corrected invariant is:

1. Lock and validate the terminal artifact and collect all
   `project_update_review` revisions coupled to the candidate.
2. Require exactly one total coupled revision.
3. Collect every accepted/rejected decision event coupled through the artifact
   ID, candidate-memory ID, or the supported true-redaction linkage.
4. Require exactly one total coupled decision event before filtering by
   expected outcome, actor, action, target, payload, or redaction form.
5. Only then validate the exact ordinary or authorized-redaction evidence.

The service boundary supplies the invariant to all six adapter paths:

- generic HTTP artifact review and dedicated HTTP project-update review;
- generic MCP artifact review and dedicated MCP project-update review; and
- generic CLI artifact review and dedicated CLI project-update review.

Scheduler generates candidates but does not review them. SQLite has no
project/artifact repository service, so its role remains revision/event
redaction-skeleton parity rather than terminal service replay. Unit regressions
inject accepted plus rejected evidence, extra accepted evidence with the wrong
action, and double rejection. Live role-separated PostgreSQL covers competing
decision evidence. Every invalid retry returns the fixed conflict/error and
leaves artifact, memory, project, revision, and event state unchanged.

### Persisted-source envelope scope surface

The earlier P1-3 inventory correctly identified source and source-chunk SQL as
affected, but its flat `_metadata_scope_clause` framing understated the defect.
A persisted source stores another historical envelope inside its outer
`metadata_json`. Passing that outer value through the memory resolver allowed a
stale root alias to override authoritative embedded canonical scope.

The corrected persisted-source precedence is:

1. Root canonical `project_scope`.
2. Canonical `project_scope` in embedded `metadata_json`.
3. Canonical `project_scope` in embedded `scope_json`.
4. Nested `agentic_memory.project_scope` and
   `agent_identity.project_scope` canonical values from those containers.
5. Root aliases.
6. Embedded metadata/scope aliases and nested-agentic aliases, only after all
   canonical tiers are absent. Nested singular `agent_identity` aliases remain
   unsupported.

Canonical presence is authoritative even when the value is empty, null, or
malformed; later tiers cannot revive stale scope. The two fail-on-old envelope
controls are:

- E0: root alias `stale` plus embedded canonical `[]` is visible nowhere.
- E1: root alias `stale` plus embedded canonical `[real]` is visible only to
  `real`, never to `stale`.

Project-identifier scalar parity is explicit: strings, finite mathematically
integral numbers, and explicit boolean scalar values normalize in Python,
SQLite, and PostgreSQL; fractional/non-finite numbers, mappings, and null are
excluded. The existing ASCII-only folding, six-ASCII-whitespace,
exact-non-ASCII, deduplicated-set, and Unicode-code-point-order contracts still
apply after leaf extraction.

The corrected source-specific resolver is used by:

- SQLite `search_sources` and `search_source_chunks` parent filtering;
- PostgreSQL `search_sources` and `search_source_chunks` parent filtering;
- retrieval lexical source, chunk, provenance, evidence, reference, currency,
  and temporal post-admission checks;
- Brain report/source selection;
- Projects automation, digest, and open-loop source selection;
- Connections and Contradictions project-scoped source search; and
- HTTP artifact-trace exact-source authorization.

Scheduler, HTTP, MCP, and CLI workflows that reach these paths inherit the
shared store/service behavior; no transport-specific source-scope resolver is
introduced. Live SQLite and role-separated PostgreSQL tests cover source and
parent-chunk visibility, and retrieval/consumer regressions cover every listed
post-admission class.

## Historical Repair Batch 9 correction appendix (superseded)

The independent Batch 8 review identified eight narrower gaps in that frozen
carrier. The current code freeze changes these exact surfaces:

- `vnext_capture.py`, SQLite/PostgreSQL source updates, SQLite repair version
  5, migration `0090`, and the HTTP source-review transaction now validate and
  atomically maintain the source identity envelope on fast, hash, and atomic
  dedupe paths, including collision rollback.
- `mcp_tools.py` and `vnext_memory_commit.py` now authorize key-bound core
  explanation roots and expanded memory-chain, provenance, entity-backing, and
  continuity resources before producing details.
- `vnext_projects.py` binds candidate-created evidence to exactly the locked
  terminal artifact, including ordinary and authorized-redaction forms.
- `vnext_project_scope.py`, SQLite/PostgreSQL predicates, and migration `0090`
  share finite-integral numeric identity behavior while retaining explicit
  boolean identifiers and rejecting fractional/non-finite values.
- `vnext_context_tree.py` plus its legacy MCP caller propagate effective
  projects to five resource groups (projects, memories, sources, open loops,
  and artifacts), filter before limits, use source-specific scope, and read a
  separate event group only for admitted targets. The legacy tool remains
  outside the core MCP surface and disabled on key-bound servers.
- MCP open-loop/resume paths apply scope before their bounded row limits and
  use target-specific event queries.
- The release-engineer handoff and protected-path test supply executable
  Upgrade Overview metadata for the touched memory-schema and continuity-API
  categories.

This appendix does not claim that unrelated reads or writes were audited or
changed. Batch 8's twice-reproduced fingerprints and full-gate results are
historical because its independent review returned changes required. Batch 9
focused and full builder gates, including reproducible package/install proof,
were green and its final fingerprints were reproduced twice; its subsequent
independent review also returned changes required on five bounded findings.

## Repair Batch 10 correction appendix

The Batch 9 review returned changes required on five bounded findings. Batch
10 changes only these surfaces:

- `vnext_memory_commit.py` makes unresolved non-null predecessor/successor
  pointers terminal validation failures before audit details are assembled;
  `mcp_tools.py` keeps the key-bound core response generic.
- `vnext_project_scope.py` and the generic scope SQL in `vnext_store.py`
  establish nested canonical presence and scalar/array parity for memory,
  artifact, and open-loop rows; SQLite follows the same shared identity.
- Resume uses store-side decision/open-loop admission before row limits and
  dedicated event joins over scope-admitted memories and open loops before
  event limits. Existing direct open-loop, scheduler, retrieval,
  consolidation, project, brain, compiler, and dogfooding consumers retain
  their established APIs.
- The legacy context tree still has five resource groups plus events: projects,
  memories, sources, open loops, artifacts, and a separate event group. It has
  no entity group, remains outside the core MCP surface, and remains disabled
  on key-bound servers.
- Active control documents and their checker distinguish Batch 9's historical
  frozen/twice-fingerprinted carrier and changes-required review from the final
  Batch 10 carrier and its separate review gate.

This appendix does not claim any unrelated production surface was changed or
re-audited. Full Batch 10 builder gates, package parity/smokes, and the
unchanged web-carrier readback were green. Final tracked-patch and bundle
fingerprints were reproduced twice; the subsequent review returned changes
required on exactly two bounded findings.

## Repair Batch 11 correction appendix

The Batch 10 review identified two remaining gaps. Batch 11 changes only these
surfaces:

- `_jsonb_source_project_scope_values_sql` in `vnext_store.py` and the
  persisted-source resolver in migration `0090` select nested canonical scope
  by `project_scope` key presence under `agentic_memory` or `agent_identity`.
  The source and parent-chunk predicates share the runtime expression;
  migration dedupe repair uses the same selected identity. Python/SQLite
  behavior is unchanged and now has explicit parity coverage for blank, null,
  malformed, fractional, scalar, array, stale-alias, and dual-container cases.
- `list_open_loops` and `list_open_loop_events` in both stores accept an
  optional query and apply it before `LIMIT` across title, description,
  next-action metadata, and relevant event payload text. `_vnext_resume`
  supplies that query for scoped and unscoped loop/event reads. Existing
  method consumers remain compatible through optional defaults, and queryless
  resume retains its established behavior.

No unrelated store, transport, scheduler, retrieval, context-tree, or web
surface was changed in Batch 11. Focused source/migration, SQLite/PostgreSQL
resume, integrated unit, Ruff, mypy, and diff gates are green. The final
3,327-unit/460-PostgreSQL gate, release-static, LongMemEval/evidence, unchanged
web carrier, package parity/smokes, and twice-reproduced final fingerprints are
green. Independent review approved persisted-source closure and every other
bounded area, but returned changes required on the one event-payload P2.

## Historical Repair Batch 12 correction appendix (review rejected)

The Batch 11 review identified one remaining P2. Batch 12 changes only these
surfaces:

- `list_open_loop_events` in `sqlite_store.py` replaces serialized-payload
  matching with `json_tree` rows restricted to string leaves.
- `list_open_loop_events` in `vnext_store.py` replaces `payload_json::text`
  matching with recursive `jsonb_path_query` results restricted to JSON
  strings.
- The MCP unit fake recursively visits mapping values and list elements, never
  keys or non-strings, and mirrors blank-query normalization.
- Existing open-loop title/description/next-action matching, optional defaults,
  scope/status/time-before-limit predicates, event-time ordering, scoped and
  unscoped behavior, and queryless behavior are unchanged.

No unrelated production or transport surface changed. Focused real SQLite,
PostgreSQL SQL-shape, and live role-separated PostgreSQL tests cover nested and
array string positives, a key-only negative, 62 newer mismatch rows, and both
scoped and unscoped calls. The 442-unit owned seam, complete 9-case PostgreSQL
file, Ruff, format, mypy, diff-check, and release-static are green. The final
3,327-unit/460-PostgreSQL gate, LongMemEval/evidence, unchanged web carrier,
package reproducibility/parity/smokes, and twice-reproduced fingerprints passed.
Independent review approved the production SQLite/PostgreSQL recursive-leaf
surface but returned changes required because the fake could combine text from
separate leaves. Batch 12 is historical and does not approve the current tree.

## Historical Repair Batch 13 correction appendix (never frozen)

Batch 13 changed only `FakeVNextMCPStore.list_open_loop_events` and its tests:
the fake visited mapping values and list elements recursively and matched the
query independently inside each string leaf. It no longer concatenated text
from separate leaves. No production store or adapter bytes changed.

Two focused regressions, the complete 256-test MCP file, and 3,328 full units
passed. Exact production-file hashes remained the frozen Batch 12 hashes, so
the historical 460-case PostgreSQL result was cited without rerun. Batch 13 was
never frozen and had no final static, package, fingerprint, or approval claim.
Independent review returned a Unicode/collation P2 because fake and SQL
backends still lacked one deterministic non-ASCII comparison contract.

## Historical Repair Batch 14 correction appendix (review rejected)

Repair Batch 14 was the frozen predecessor. Its comparison contract was
**ASCII case-insensitive literal substring** across exactly these surfaces:

- SQLite `list_open_loops` row-field admission and
  `list_open_loop_events` row-field plus recursive payload-leaf admission;
- PostgreSQL `list_open_loops` row-field admission and
  `list_open_loop_events` row-field plus recursive payload-leaf admission;
- `FakeVNextMCPStore` open-loop rows and event payloads used by MCP resume
  coverage; and
- the shared `alice_resume` MCP workflow that inherits those store/fake reads.

The row fields are title, description, root `metadata_json.next_action`, and
nested `metadata_json.agentic_memory.next_action`. Event matching considers
each recursive JSON string leaf independently. It never matches keys,
non-string values, JSON punctuation, or text split across leaves. ASCII
`A-Z` folds to `a-z`; non-ASCII code points compare exactly, without Unicode
normalization or locale dependence. `%`, `_`, and backslash are literal
characters in SQLite and PostgreSQL, not wildcard or escape syntax.

The change must not alter blank/queryless behavior, optional defaults,
scope/status/time predicates before limits, open-loop ordering, event-time
ordering, limits, or scoped/unscoped results. It introduces no HTTP, CLI,
scheduler, web, schema, migration, or persistence-write surface.

Implementation readback and the surface-focused verification are green: 4
focused units passed; the complete MCP/store seam passed 338 units; focused
role-separated PostgreSQL passed 2 cases and the complete affected PostgreSQL
file passed 10. The full gates passed 3,329 units with the required coverage
floors and 461 role-separated PostgreSQL integrations. Release-static/control
checks, 127 LongMemEval tests plus evidence replay, unchanged-web readback, and
two reproducible package builds with isolated wheel/sdist smokes also passed.
Exact timings, coverage, source/test hashes, carrier digests, and package hashes
are recorded in `BUILD_REPORT.md`. Final tracked-patch and fixed 12-file bundle
fingerprints reproduced twice. Independent review returned exactly three
bounded P2s: non-string metadata `next_action` row parity, overbroad alpha-doc
scope, and a missing `created_at` fake-list tie-break. Batch 14 is historical
and does not approve the current tree.

## Historical Repair Batch 15 correction appendix

Repair Batch 15 was a bounded correction. It is restricted to these
surfaces:

- SQLite `list_open_loops` and `list_open_loop_events` row-field admission;
- PostgreSQL `list_open_loops` and `list_open_loop_events` row-field
  admission;
- `FakeVNextMCPStore.list_open_loops` row-field admission and ordering, plus
  its unchanged per-string-leaf event matching; and
- alpha documentation that describes the resume/open-loop query comparator.

For row-field admission, root `metadata_json.next_action` and nested
`metadata_json.agentic_memory.next_action` are candidates only when the JSON
value itself is a string. Objects, arrays, numbers, booleans, and null must not
be converted to text or matched through those fields in SQLite, PostgreSQL, or
the fake. Title and description behavior is unchanged. Loop-event payload
matching still evaluates each recursive string leaf independently; it does not
match keys, non-string values, punctuation, or text split across leaves.

`FakeVNextMCPStore.list_open_loops` must mirror production order exactly:
`opened_at DESC`, then `created_at DESC`, then `id DESC`. No other ordering,
limit, blank/queryless, scope/status/time-before-limit, scoped/unscoped, or
optional-default contract changes.

Alpha documentation must limit the **ASCII case-insensitive literal
substring**, exact non-ASCII, and literal `%`, `_`, and backslash contract to
open-loop row fields and loop-event recursive string leaves. It must not claim
that this rule governs decision-memory or next-action-memory search. This
documentation correction changes no additional runtime surface.

Implementation/readback and surface-focused verification are green. Five
focused units passed with 334 deselected in 0.41 seconds; the complete owned
MCP/store seam passed 339 tests in 0.53 seconds; focused live PostgreSQL passed
1 case with 9 deselected in 1.25 seconds; and the complete affected PostgreSQL
file passed 10 tests in 11.54 seconds. These cases cover string-only metadata
row candidates, exact fake ordering, unchanged event leaves, and truthful doc
scope.

The full gates passed 3,331 units with required statement, branch, and
`main.py` coverage floors plus 461 role-separated PostgreSQL integrations.
Release-static/control, Ruff/format/`py_compile`, mirror/diff, 127 LongMemEval
tests plus evidence replay, unchanged-web readback, and two byte-identical
normalized package builds with parity and isolated wheel/sdist smokes passed.
Exact timings, coverage, source/test hashes, carrier digests, and package hashes
are recorded in `BUILD_REPORT.md`. The final tracked-patch and fixed 12-file
remediation-bundle fingerprints reproduced twice and are recorded there.
Independent review subsequently approved that exact carrier, but the Batch 16
embedding-CAS whitespace finding superseded it.

## Repair Batch 16 correction appendix

Repair Batch 16 changes one PostgreSQL runtime SQL fragment and its evidence.
The three embedding-CAS SQL consumers are:

1. `search_memories_vector`, where signed-vector freshness is enforced inside
   the candidate query;
2. `update_memory_embedding`, where a supplied content digest must still match
   the locked row before a signed vector is written; and
3. `list_memories_missing_embeddings`, where a content mismatch selects a row
   for re-embedding.

All three interpolate `_MEMORY_EMBEDDING_CONTENT_SHA256_SQL`, so one private
runtime helper now emits `btrim(expression, chr(...) || ...)` with exactly
migration `0090`'s CPython 3.12 29-codepoint table. The boundaries include
U+001C–U+001F, NEL U+0085, NBSP U+00A0, the Unicode separator spaces, and the
ordinary ASCII whitespace recognized by Python `str.strip()`. POSIX
`[[:space:]]` is no longer used for embedding digest normalization.

The Python `memory_embedding_text`/`memory_embedding_content_sha256` source of
truth, migration `0090`, SQLite's Python digest path, provider calls, signature
metadata shape, vector width, ranking, transport adapters, and persistence
schema do not change. Blank fields are still omitted, identical normalized
fields are still deduplicated by first occurrence, remaining values are joined
with LF, and the UTF-8 bytes are still SHA-256 digested.

Fail-on-old unit coverage inspects generated SQL for every consumer, every one
of the 29 `chr()` codepoints, and absence of the old POSIX trim. Live
role-separated PostgreSQL covers NBSP and U+001C boundaries plus a mixed blank
and duplicate-field case; each proves CAS acceptance, zero missing-embedding
rows afterward, and signed vector participation. Focused and complete affected
files, 3,332 full units with coverage floors, all 463 PostgreSQL integrations,
release-static/control, LongMemEval/evidence, exact unchanged-web readback, and
the reproducible package/parity/smoke gate pass. Final tracked-patch and fixed
12-file bundle fingerprints reproduced twice and are recorded in the self-
excluded builder report. Batch 16 review approved the production CAS semantics
and returned changes required on one documentation-truth P3. Refreeze 17
changes only that stale Batch 15/current-review wording plus its fail-on-old
control guard; independent review of the Refreeze 17 carrier remains required.

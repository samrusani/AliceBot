# Alice v0.11.1 Phase 2 Surface Inventory

Status at package-input freeze: implemented and builder-verified; final
package/receipt/review had not yet run. Consult final reports for outcomes.
Scope: Phase 2 items 2.0 through 2.14 only
Base commit: `5f0a92d77d02b0699af3054fced7427929808aa8`
Base tree: `560bade5b9ad20c659f03f19693288558c706945`
Branch: `codex/v0111-phase2-debt-sweep`
Candidate: `0.11.1` (uncommitted and unpublished)

This is the controlling post-cut enumeration. Existing migrations through
`0090`, immutable v0.10.x/v0.11.0 release artifacts, and the Phase 1 handoff
remain unchanged. Phase 3 and a cybersecurity audit are out of scope.

## Re-measured baseline

The published v0.11.0 cut materially changed the original debt inventory:

| Brief item | Post-cut measurement | Decision |
|---|---|---|
| 2.1 response hygiene | GitHub reported 242 open `py/stack-trace-exposure` alerts on current `main`/the published base when queried on 2026-07-16. Separately, the post-cut source baseline had 288 surviving direct or delayed public exception callsites. | Local AST/source proof is zero old-pattern exception-to-`JSONResponse` violations. Eight additional dynamic 404 branches discovered by integration bring the stable `public_exception_response` call inventory to 296. The CodeQL target-zero readback cannot exist until the carrier has an exact committed SHA and CI analyzes it. This measurement is not a cybersecurity audit. |
| 2.9 response generation | `response_generation.py` had one default consumer and measured 705 lines. | Retain only the provider-runtime prepare/transport/fail/complete path; candidate is 610 lines. |
| 2.10 empty routes | The five directories were already removed in the Phase 1 D3 rider. | Record as satisfied; do not create a no-op carrier. |
| 2.11 docs riders | Both notes were already present in the Phase 1 public docs. | Record as satisfied; keep the existing truth tests. |
| 2.12 shared Redis flake | The entrypoint rate-limit implementation, env keys, transport calls, and tests were deleted during Phase 1. No Alice Redis client survives; only a setting, health `not_checked` echo, and dependency/config/Docker/install placeholders remain. | Obsolete. No isolation config is added for a nonexistent backend. |
| 2.13 pnpm audit | pnpm 10 remains pinned and does not provide the chosen bulk-endpoint path. | Keep the stricter fail-closed wrapper and document when to revisit. |
| 2.14 stale PRs | All nine named PRs remain open against `main`; several are behind or dirty. | Fold only explicitly qualified changes into this carrier; do not claim the PRs closed or merged. |

## 2.0 — default-surface integration and release controls

### Workflow surface

`python-integration` is a two-row matrix with distinct check names:

1. `Integration tests (Postgres + pgvector, role separation)` runs the complete
   integration suite with `ALICE_LEGACY_SURFACES=1`.
2. `Default surface integration smoke (Postgres)` explicitly unsets
   `ALICE_LEGACY_SURFACES`, `ALICE_MCP_LEGACY_TOOLS`, and
   `ALICE_AGENT_API_KEY`, then runs only the default-surface smoke.

Both use PostgreSQL plus pgvector and separate application/administrator URLs.
The new exact check name is in both repository release-check inventories.
Adding it to protected-main required checks is deliberately not attempted from
an uncommitted tree; the release engineer must use the prepared MainProtect
payload after the carrier merges and verify the readback.

### Exercised product surfaces

| Surface | Exact smoke behavior |
|---|---|
| HTTP/OpenAPI | Asserts exactly 182 operations, no legacy operation keys, then `POST /v1/workspaces/bootstrap`. |
| MCP | Starts the real stdio server in a clean child process and asserts exactly the eleven core tools. |
| Capture/review | `alice_capture` creates a candidate and `alice_memory_correct` approves it. |
| Retrieval/continuity | `alice_recall`, `alice_resume`, and `alice_context_pack` all resolve the same active memory. |
| Review | `alice_memory_review` returns the active detail record. |
| PostgreSQL | Uses migrated role-separated connections and creates/reads real rows. |
| SQLite/web/scheduler | Not part of this PostgreSQL default-mount proof; they have their own existing matrices. |

## 2.1 — stable public failure contracts

### HTTP and OpenAPI

`public_errors.py` defines the stable families `invalid_request`,
`authentication_failed`, `forbidden`, `not_found`, `conflict`,
`upstream_failure`, and `internal_error`. Exception-backed HTTP responses keep
the existing top-level `detail` envelope and use
`{"detail":{"code":...,"message":...}}`. Unknown status mappings fail
closed to `internal_error`/500. Specific exception types and text are logged
server-side with the public code/status, not serialized.

The OpenAPI `APIErrorDetail` requires nonempty `code` and `message`; the outer
error schema remains compatible with FastAPI string/list validation errors.
Sentinel tests cover ordinary vNext handlers, authentication middleware,
provider/bootstrap/runtime handlers, lifecycle errors, and delayed provider
failure persistence.

### MCP, CLI, scheduler, and diagnostic carriers

| Surface | Stable carrier |
|---|---|
| MCP JSON-RPC | Standard static parse/request/params/method messages; tool failures serialize one `{error:{code,message}}` text object; startup emits one machine-readable line. |
| Hermes adapter | Uses the same tool-not-found/request/execution families without exception text. |
| PostgreSQL CLI | Parse failures use `invalid_request`; unhandled commands use `command_failed`. |
| SQLite `alice-memory` CLI | Parse failures use `invalid_request`; unhandled execution uses `alice_memory_failed`. |
| Provider/response trace | Public and persisted trace failure text is static, with a stable `error_code`; private provider details are logged. |
| Scheduler/evals/doctor/connectors | Stored skip/refusal/error notes use fixed codes/messages; provider/SQL exception types, DSNs, and raw text are absent. |

The carrier does not claim that prior external CodeQL alerts are closed before
the server analyzes a committed exact SHA.

## 2.2 — list/resume memory-query folding parity

The affected non-FTS query legs are `list_memories(query=...)` and
`list_resume_memory_events(query=...)`, used by recent decisions and resume.
They now match the existing open-loop rule. Generic `search_memories` and
`alice_recall` FTS/websearch retrieval retain separate, unchanged semantics:

- ASCII `A`–`Z` folds to `a`–`z` on both candidate and query;
- non-ASCII code points are compared byte/codepoint-exactly with no Unicode
  normalization or locale case conversion;
- `%`, `_`, and backslash are literal substring characters, not SQL patterns;
- empty query behavior, project/policy filtering, row ordering, and limits are
  unchanged.

| Store/surface | Implementation and proof |
|---|---|
| PostgreSQL | Binary-collated ASCII `translate(...)` plus escaped `LIKE`; SQL-shape and live store/public-MCP parity. |
| SQLite | Equivalent ASCII fold and `LIKE ... ESCAPE`; table-driven local tests. |
| MCP fake | Per-field ASCII fold, exact ordering, deleted-row filtering, and the same table. |
| Public tools | `alice_resume` and `alice_recent_decisions` share the contract; docs state it explicitly. |

FTS/tokenized retrieval and vector search are separate arms and are not
silently redefined by this literal-memory-leg fix.

## 2.3 — bounded terminal project-update evidence lookup

The service protocol adds one
`list_project_update_events(artifact_id, candidate_memory_id)` call. Terminal
replay performs it only after the artifact is already terminal, then validates
creation and decision evidence with the existing strict corruption rules.

PostgreSQL migration `0091` adds stored string-only payload columns
`payload_artifact_id`, `payload_candidate_memory_id`, and `payload_memory_id`.
Four user-leading partial indexes cover canonical targets and those three
payload identities for the three project-update event types. The production
query is five indexable `UNION` branches. SQL set semantics deduplicate
identical full event rows before stable `occurred_at DESC, id DESC` order.

SQLite installs equivalent target/payload indexes and performs matching union
branches without new generated columns. Both stores return only coupled event
types and preserve tenant isolation. Existing terminal corruption validation
still rejects missing, duplicate, contradictory, wrong-actor, wrong-target,
wrong-action, or malformed redaction evidence.

## 2.4 and 2.5 — project-update lifecycle guards

Reject now validates a nonblank candidate `memory_key` before any mutation,
matching accept. Tests freeze artifact, memory, revisions, project state, and
event log before null/empty/whitespace attempts and require byte-equivalent
readback after the error.

The generic mutation guard recognizes a pending coupled memory when either:

- `metadata_json.workflow == "project_auto_update"`; or
- the stripped memory key starts with reserved prefix `project_update.`.

It treats anything other than exact `metadata_json.candidate is False` as
pending. This fail-closed rule covers malformed/legacy rows and is enforced in:

- generic HTTP review and correct/forget/undo handlers;
- core `alice_memory_correct` and `alice_memory_manage`;
- legacy MCP review/correct/forget variants when enabled;
- the `alicebot vnext memories` CLI lifecycle verbs; and
- direct SQLite/PostgreSQL service calls.

The dedicated project-update review remains the only pending transition.
After a valid terminal outcome, generic correction remains available.

## 2.6 — Option A coupled true redaction

### Owner-selected policy

The selected policy covers governed content copies in the coupled memory/
project-update graph. It does not claim global source erasure: source and
source-chunk evidence is deliberately unchanged because either may support
other memories, and upstream systems, exports, and backups remain outside this
operation. Governed text uses the exact `[REDACTED]` marker, governed non-null
free-form JSON uses the exact `{"redacted":true}` marker, and nullable content
that was null stays null.

| Persisted object | Destroyed | Retained skeleton |
|---|---|---|
| Memory | original key; title/canonical text/summary/trust prose; value; source-event ids; arbitrary metadata; `commit_digest`; `confirmation_id`; embedding; fact keys | id/user and agent/project/run/supersession identities/links; `memory_type`, domain, sensitivity, confidence, salience, `confirmation_status`, trust class, promotion eligibility, evidence/independent-source counts, extracted-by-model; validity/seen/review times including `last_confirmed_at`; structural metadata; archived/deleted and creation/update state |
| Revisions | key/content values, candidate/metadata payloads, source-event ids, before/after/reason prose | id, memory/user, sequence/revision/action/type, actor, timestamp; nullable content that was null stays null |
| Coupled events | payload content and integrity hash | id/user/type/actor/target/time/trace/run plus exact `{"redacted":true,"memory_id":...,"event_type":...}` payload |
| Terminal artifact (PostgreSQL) | title, markdown, prompt hash, model details, arbitrary metadata | id/user/type/status/domain/sensitivity/generator/timestamps and exact project/workflow/candidate/review linkage with `redacted_at` |
| Quality rating (PostgreSQL) | missed-context/comments prose and arbitrary metadata | id/artifact/reviewer/time; six numeric dimensions (`usefulness`, `accuracy`, `source_grounding`, `novel_connections`, `actionability`, `hallucination_risk`) plus categorical `verbosity` |
| Provenance | quoted content for memory and artifact targets | link/source/target identities, evidence role, confidence, timestamp |
| Source and source chunks | nothing; memory redaction does not mutate them | evidence remains available because it may be shared across memories |
| Applied project state | nothing | Accepted state remains applied; redaction is not rollback. |

### Atomicity, authorization, and idempotence

The caller locks the graph deterministically. PostgreSQL uses the narrowly
scoped `app.redaction_in_progress` session flag; SQLite uses a reset-on-open and
finally-reset one-row mode flag. Migration `0092` replaces append-only
exceptions with exact marker-shape guards, protects redacted artifacts from
later updates, and blocks new quality/provenance prose after redaction. RLS and
same-user predicates remain on every PostgreSQL row.

Artifact eligibility is exact: type `project_update`, terminal accepted or
rejected status, original workflow `project_auto_update`, exact
`project_scope=[project_id]`, candidate memory link, and matching review action.
Malformed partial artifacts, fabricated redaction timestamps, fabricated event
memory IDs, broad UUIDs appearing only in prose, and cross-tenant rows do not
authorize mutation.

One content-free `memory.redacted` receipt is appended only when some governed
value changes. Exact replay preserves the first genuine redaction timestamp,
returns zero changed counts with `idempotent_replay=true`, and makes no write.
HTTP, MCP, and CLI return explicit revision/event/artifact/rating/provenance
counts plus artifact ids.

SQLite deliberately has no generated-artifact or quality-rating repository.
Its artifact/rating counts are therefore zero while the shared memory,
revision, event, and memory-provenance graph is scrubbed with equivalent marker
and replay rules.

## 2.7 — migration 0090 defensive edges

Migration `0091` repeats the explicit CPython 3.12 29-codepoint `str.strip()`
table, including NBSP and U+001C–U+001F. It clears `dedupe_key` only on live
sources whose stored `raw_text` is a string blank under that table. Missing or
non-string raw text keeps the 0090 content-hash fallback. Downgrade removes the
additive event-query substrate but intentionally does not recreate an invalid,
unreachable dedupe identity.

Application, PostgreSQL constraints, migration normalization, and SQLite
bootstrap use the same canonical source-domain/sensitivity vocabulary. Blank,
unknown, or non-ASCII case variants cannot drift between Python `casefold()`
and SQL `lower()`; unsupported values fail before becoming live identity.

## 2.8 — test-infrastructure truth

- `FakeVNextMCPStore.list_*` methods have explicit production-aligned
  signatures. Unknown keyword arguments now fail instead of disappearing.
- Fake memory/source/open-loop/artifact views remove deleted rows and deleted
  backing resources before filtering/limiting.
- `coverage>=7.7,<8.0` is explicit because the coverage checker depends on the
  JSON field introduced at that floor.
- `scripts/decode_github_release_body.py` appears in both normal cross-module
  mypy invocations.
- Workflow-shape tests require manual-only `publish-pypi.yml` triggers and
  require a background scheduler launched with `once=True` to pass `--once` to
  its child before spawn.
- Release/control checks require `pyproject.toml` to point at the evergreen
  `docs/pypi-description.md` and require that file to exist.
- No surviving hosted route enumeration gains a new hand-maintained tuple; the
  governed default/legacy inventories remain derived from the mounted route and
  OpenAPI registries.

## 2.9 through 2.13 — trim and process decisions

`response_generation.py` retains only the code used by the provider runtime:
prompt assembly, OpenAI-compatible transport, durable preparation, static
failure trace, and successful completion. Unused settings/profile resolution,
default model invocation, prepared-response compatibility wrapper, and the
old all-in-one orchestration export are deleted. Tests assert those exports are
absent and cover the retained transport/telemetry/failure behavior.

The empty web directories and both upgrade riders are Phase 1 closures. The
entrypoint-rate-limit Redis flake is obsolete because no Alice Redis client,
transport, or entrypoint reader survives; the remaining setting, health echo,
dependency/config, Docker, and install placeholders do not consume those keys.
For dependency auditing, the project keeps the bulk-advisory wrapper on Node
20/pnpm 10.23.0; it fails closed and is tested in both production-only and
complete dependency modes.

## 2.14 — dependency backlog disposition

All named PRs were still open when read on 2026-07-16. This carrier does not
write to their server state.

| PR | Proposal | Candidate disposition |
|---|---|---|
| #210 | React 19.0.0 to 19.2.7 and matching types | No Phase 2 delta: the published base already pins React 19.2.7 and `@types/react` 19.2.17. Treat the stale/dirty PR as superseded only after the carrier merges. |
| #214 | TypeScript 5.8.2 to 6.0.3 | Deferred to a dedicated major-toolchain carrier with full web matrix and budgets. |
| #235 | pytest range `<9` to `<10` | Applied as `pytest>=8.3,<10.0`; installed-wheel compatibility remains pinned independently. |
| #236 | redis-py range `<6` to `<9` | Applied exactly as `redis>=5.0,<9.0` after matching the live PR diff and confirming that PR's prior CI matrix was green. Post-range release-static and isolated Redis 8.0.1 resolution with `pip check` passed. Final artifact reproduction follows package-input freeze. The PR itself remains open. |
| #239 | `eslint-config-next` 15.5.20 to 16.2.10 | Deferred with the Next/toolchain major compatibility carrier. |
| #241 | `@types/node` 22.13.10 to 26.1.1 | Deferred to a Node type/toolchain compatibility carrier. |
| #266 | checkout 6.0.2 to 7.0.0 | Applied across active workflows at immutable commit `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0`. |
| #267/#268 | CodeQL autobuild/init 4.35.4 to 4.37.0 | Applied coherently to init, autobuild, and analyze at immutable commit `99df26d4f13ea111d4ec1a7dddef6063f76b97e9`. |

The release engineer must close or supersede obsolete Dependabot PRs only after
the committed carrier and CI establish their replacement truth.

## Documentation and release identity

Both governed version sources are `0.11.1`. `CHANGELOG.md` and pending release
notes describe the candidate while retaining v0.11.0 as latest published. Core
architecture, roadmap, product, current-state mirrors, sprint, integration,
memory-operation, MCP, CLI, and releasing docs describe the actual Phase 2
boundary and Option A semantics. At package-input freeze, the bounded local
builder matrix was green while final package reproduction, a superseding
receipt, and independent review were still pending. Their final outcomes belong
in `BUILD_REPORT.md` and reviewer-authored `REVIEW_REPORT.md`. This handoff does
not authorize a tag or publication.

## Handoff and freeze surfaces

The final handoff directory is defined to contain `README.md`, this inventory,
`FIX_MATRIX.md`, `BUILD_REPORT.md`, `ENGINEER_HANDOFF.md`, and the reviewer-
authored `REVIEW_REPORT.md`. The independent reviewer alone creates the review
report after the exact carrier receipt is frozen.

The receipt union starts from base `5f0a92d` and includes every base-relative
tracked change plus untracked candidate path, byte-sorted and de-duplicated. It
excludes exactly the self-referential build report, reviewer-authored review
report, and the protected user-owned `coverage.json` and `uv.lock`. Two
independent implementations must reproduce the same NUL-delimited manifest
before review.

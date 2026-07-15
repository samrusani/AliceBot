# v0.11.0 Phase 1 surface inventory

Status: implementation inventory, written before production edits  
Scope: Phase 1 only; Phase 2 and later work is explicitly excluded  
Base commit: `8520f29d3812aa95a75d192fdaf897e5d099a29a`  
Base tree: `7ef7984e7d396b740ecb719a411e6bd44ffe7289`  
Candidate version: `0.11.0` (unpublished)

This is the controlling enumeration for the periphery cut. Historical migrations and
the immutable v0.10.2, v0.10.3, and v0.10.4 release records remain untouched. The
working tree is delivered uncommitted and does not begin Phase 2.

## Decision vocabulary

- **Delete** means the route, implementation, public contract, active documentation,
  and exclusively owned tests disappear together. Historical schema remains inert.
- **Gate** means the route or command is not mounted by default and is mounted only
  when the shared strict parser sees `ALICE_LEGACY_SURFACES=1`.
- **Keep** means the surface remains part of the default core or adjacent provider
  runtime.
- `ALICE_MCP_LEGACY_TOOLS=1` remains the independent long-tail MCP gate. The three
  task-brief tools require both gates.

The new `ALICE_LEGACY_SURFACES` parser accepts the exact string `1`; unset, empty,
`0`, `true`, whitespace, and all other values are disabled. API, MCP, and CLI import
that parser. The value is captured at process import/start; changing it requires a
restart of affected API, worker, and web processes. The pre-existing
`ALICE_MCP_LEGACY_TOOLS` compatibility parser preserves its accepted case-insensitive
values (`1`, `true`, `yes`, `on`).

## HTTP and OpenAPI

Baseline OpenAPI operations: **294**.

### Permanently deleted: 63 operations

| Family | Count | Exact operations | Proof that fails on the old tree |
|---|---:|---|---|
| Chat response | 1 | `POST /v0/responses` | Schema/route absence test; retained runtime idempotency test proves `/v1/runtime/invoke` still works. |
| Chief of staff | 5 | `GET /v0/chief-of-staff`; `POST /v0/chief-of-staff/recommendation-outcomes`; `POST /v0/chief-of-staff/handoff-review-actions`; `POST /v0/chief-of-staff/execution-routing-actions`; `POST /v0/chief-of-staff/handoff-outcomes` | Exact deleted-route inventory test and import-spec absence for `chief_of_staff`. |
| Model packs | 5 | `GET,POST /v1/model-packs`; `GET /v1/model-packs/{pack_id}`; `POST /v1/model-packs/{pack_id}/bind`; `GET /v1/workspaces/{workspace_id}/model-pack-binding` | Exact schema absence and request/response-contract test rejecting pack fields. |
| Hosted auth/workspace/device/preferences residue | 12 | `POST /v1/auth/magic-link/start`; `POST /v1/auth/magic-link/verify`; `POST /v1/auth/logout`; `GET /v1/auth/session`; `POST /v1/workspaces`; `GET /v1/workspaces/current`; `POST /v1/devices/link/start`; `POST /v1/devices/link/confirm`; `GET /v1/devices`; `DELETE /v1/devices/{device_id}`; `GET,PATCH /v1/preferences` | Exact schema absence and deleted-module import-spec test. The two bootstrap operations below are deliberately retained. |
| Hosted admin and design partners | 15 | `GET /v1/admin/hosted/overview`; `GET /v1/admin/hosted/design-partners/dashboard`; `GET,POST /v1/admin/hosted/design-partners`; `GET,PATCH /v1/admin/hosted/design-partners/{design_partner_id}`; `POST /v1/admin/hosted/design-partners/{design_partner_id}/workspaces`; `POST /v1/admin/hosted/design-partners/{design_partner_id}/feedback`; `GET /v1/admin/hosted/workspaces`; `GET /v1/admin/hosted/delivery-receipts`; `GET /v1/admin/hosted/incidents`; `GET /v1/admin/hosted/rollout-flags`; `PATCH /v1/admin/hosted/rollout-flags`; `GET /v1/admin/hosted/analytics`; `GET /v1/admin/hosted/rate-limits` | Exact schema absence, deleted-module import-spec test, and hosted web-page absence. |
| Hosted Telegram channel/auth/delivery | 25 | Every operation under `/v1/channels/telegram/*`: link start/confirm/unlink/status; webhook; messages list; threads; message dispatch; delivery receipts; notification preferences get/patch; daily brief get/deliver; open-loop prompts list/deliver; scheduler jobs; message handle/result; recall; resume; open loops; open-loop review action; approvals list/approve/reject | Exact prefix count/absence test, deleted-module import-spec test, MCP/CLI/scheduler absence checks. |

The vNext raw-source ingestion operation `POST /v0/vnext/connectors/telegram/sync`
is **not** part of the hosted Telegram channel stack. It remains default-on for
operator-supplied raw updates. Its payload normalizer moves to a neutral connector
helper so the three `telegram_*` channel modules can be deleted. Alice no longer polls
Telegram or stores a Telegram bot token: the dedicated route requires supplied updates,
the connector is `on_demand`, and generic connector sync/ingest must reject Telegram so
it cannot bypass the allowlist-aware `sync_telegram_updates` path. The web mirrors that
boundary exactly: it accepts an explicit allowlist and non-empty caller-supplied updates,
has no token/secret-ref/polling/interval controls, and exposes no empty-update action that
can produce the retired 422 path.

### Default-off, flag-on: 49 operations

| Family | Count | Exact prefix/count inventory | Proof that fails on the old tree |
|---|---:|---|---|
| Tools | 5 | `/v0/tools*`: create, list, get, allowlist evaluate, route | Default schema/404 plus flag-on schema/smoke. |
| Approvals | 6 | `/v0/approvals*`: request, list, get, approve, reject, execute | Default schema/404 plus flag-on schema/smoke. |
| Tasks | 9 | `/v0/tasks*`: list/get; runs create/list; workspace create; artifact-chunk task retrieval (three); step create/list | Exact route inventory keeps the three task-scoped artifact retrieval operations in the gated task family while direct artifact operations remain default-on. |
| Task runs | 5 | `/v0/task-runs*`: get, tick, pause, resume, cancel | Default schema/404 plus flag-on schema/smoke. |
| Task workspaces | 3 | `/v0/task-workspaces*`: list, get, artifact registration | Default schema/404 plus flag-on schema/smoke. |
| Task steps | 2 | `/v0/task-steps*`: get, transition | Default schema/404 plus flag-on schema/smoke. |
| Execution budgets | 5 | `/v0/execution-budgets*`: create, list, get, deactivate, supersede | Default schema/404 plus flag-on schema/smoke. |
| Tool executions | 2 | `/v0/tool-executions*`: list, get | Default schema/404 plus flag-on schema/smoke. |
| Task briefs | 3 | `/v0/task-briefs*`: compile, get, compare | Default schema/404 plus flag-on schema/smoke; public contracts contain no model-pack fields. |
| Gmail | 4 | `/v0/gmail-accounts*`: connect, list, get, ingest | Default schema/404 plus flag-on schema/smoke. |
| Calendar | 5 | `/v0/calendar-accounts*`: connect, list, get, list events, ingest | Default schema/404 plus flag-on schema/smoke. |

The legacy family is selected from an explicit operation-key set, not a broad `/v0/tasks`
string test. Exactly ten direct artifact/embedding operations remain default-on:

1. `GET /v0/task-artifacts`
2. `GET /v0/task-artifacts/{task_artifact_id}`
3. `POST /v0/task-artifacts/{task_artifact_id}/ingest`
4. `GET /v0/task-artifacts/{task_artifact_id}/chunks`
5. `POST /v0/task-artifacts/{task_artifact_id}/chunks/retrieve`
6. `POST /v0/task-artifacts/{task_artifact_id}/chunks/semantic-retrieval`
7. `POST /v0/task-artifact-chunk-embeddings`
8. `GET /v0/task-artifacts/{task_artifact_id}/chunk-embeddings`
9. `GET /v0/task-artifact-chunks/{task_artifact_chunk_id}/embeddings`
10. `GET /v0/task-artifact-chunk-embeddings/{task_artifact_chunk_embedding_id}`

vNext queue tasks are memory-pipeline work and remain default-on; they are not the
legacy task engine.

### Retained identity/provider boundary

- Keep and rewrite `POST /v1/workspaces/bootstrap` and
  `GET /v1/workspaces/bootstrap/status` around a deterministic local single-workspace
  adapter.
- Keep nine `/v1/providers*` operations and `POST /v1/runtime/invoke`.
- Retained `/v1` memory, eval, contradiction, trust, provider, runtime, and bootstrap
  handlers use `X-AliceBot-User-Id` or `ALICEBOT_AUTH_USER_ID`, never hosted bearer
  sessions.
- The local adapter may reuse inert `user_accounts`, `workspaces`, and membership
  tables, sets both database user contexts, and never exposes multi-workspace CRUD.
- Provider invocation keeps `response_generation.py` and `response_jobs.py` because
  it reuses their durable idempotency machinery; only the public chat endpoint is cut.
- Provider registration, discovery, test, update, invocation, idempotency, telemetry,
  and target hardening receive focused retained-surface tests with no hosted/model-pack
  dependency.
- Hosted-era provider rows remain immutable historical data under their former
  workspace identities. They are orphaned from the deterministic local workspace;
  operators must bootstrap the local workspace and re-register providers after
  upgrading.

### Production startup boundary

- Production startup continues to require local identity, overridden application and
  administrator database URLs, and non-wildcard CORS configuration.
- `S3_ACCESS_KEY` and `S3_SECRET_KEY` are not production requirements because no S3
  client survives Phase 1. Dormant S3 settings/defaults remain accepted for
  compatibility, but `/healthz` does not echo `s3_endpoint_url`.
- Fail-on-old tests boot a valid core-only production `Settings` object and validate a
  production `.env` without S3 credentials, while existing auth/database/CORS failures
  remain enforced.

### Count acceptance

- default: `294 - 63 - 49 = 182` OpenAPI operations;
- `ALICE_LEGACY_SURFACES=1`: `294 - 63 = 231` operations;
- the phantom-key registry fence, closed-schema inventory, intentionally-open inventory,
  and polymorphic justification gates must pass in both modes.

## Python modules and contracts

### Delete

`telegram_channels.py`, `telegram_continuity.py`, `telegram_notifications.py`,
`hosted_admin.py`, `hosted_auth.py`, `hosted_devices.py`, `hosted_preferences.py`,
`hosted_rate_limits.py`, `hosted_rollout.py`, `hosted_telemetry.py`,
`hosted_workspace.py`, `design_partners.py`, `chief_of_staff.py`, and
`model_packs.py`, plus exclusively owned public contracts and store helpers.

Fail-on-old proof: an allowlisted `importlib.util.find_spec` test requires all fourteen
module specs to be absent, and contract/schema tests require hosted/model-pack/chief/
channel public names to be absent.

### Keep or extract

- `provider_runtime.py`, `response_generation.py`, `response_jobs.py`, provider secret/
  target helpers, memory/continuity/vNext modules, task artifact modules, and migration
  history remain.
- `normalize_telegram_update` is replaced by a neutral connector-payload helper used
  by `vnext_connectors.py`; polling/token resolution is removed. Telegram raw updates
  remain importable only through the allowlist-aware vNext source-ingestion path.
- `task_briefing.py` remains behind the legacy gate but loses public and semantic model-pack strategy inputs,
  output metadata, formatting, and comparisons. The immutable database column named
  `model_pack_strategy` remains only as a compatibility carrier for the neutral `briefing_strategy` value.
- `proxy_execution.py` remains only as backing for the flag-gated approval execution
  surface; it is imported lazily inside the execute handler and is absent from
  `sys.modules` in a clean default process. Flag-on mounting alone does not import it.
- The response/entrypoint rate-limiter carrier is deleted with `/v0/responses` and the
  hosted ingress surfaces: classes, globals, Redis fallback, settings/env/parser/
  validation, script exports, integration fixture, and obsolete tests are absent.
  `_request_client_identifier` remains as a proxy-trust boundary helper.

## MCP

- Keep the eleven core tools default-on:
  `alice_capture`, `alice_recall`, `alice_resume`, `alice_context_pack`,
  `alice_open_loops`, `alice_recent_decisions`, `alice_memory_review`,
  `alice_memory_correct`, `alice_explain`, `alice_memory_commit`,
  `alice_memory_manage`.
- Keep legitimate long-tail memory tools behind `ALICE_MCP_LEGACY_TOOLS=1` and the
  existing keyless-local restriction.
- `alice_task_brief`, `alice_task_brief_show`, and `alice_task_brief_compare` require
  **both** `ALICE_MCP_LEGACY_TOOLS=1` and `ALICE_LEGACY_SURFACES=1`.
- No permanently deleted hosted, Telegram-channel, chief-of-staff, chat, or model-pack
  definition/handler may remain.

Fail-on-old proof: table-driven list/call tests cover the four gate combinations
(11 default, 73 MCP-legacy-only, 76 with both; agent-key-bound always 11),
core count/name stability, task-brief dual gating, and permanent deleted-name absence.
The OpenClaw integration test is rewritten to exercise the eleven-tool recall/resume
path without `alice_recall_debug`.

## CLI

- The dedicated live-polling CLI group `vnext connectors telegram` is deleted. Generic
  `vnext connectors ingest telegram` rejects Telegram rather than bypassing the chat
  allowlist; operator-supplied Telegram updates use the dedicated HTTP/import contract.
- `task-briefs` is registered only when `ALICE_LEGACY_SURFACES=1` and loses all
  model-pack options/formatting.
- No other current top-level CLI group directly exposes the 40 legacy HTTP operations,
  Gmail/Calendar account APIs, or permanently deleted hosted/channel/chat/model-pack
  surfaces. Any dead helper exposed solely through removed tests is deleted.
- The standalone `alicebot_worker.main.run()` task executor is also disabled unless
  `ALICE_LEGACY_SURFACES=1`; it cannot remain a task-engine side door.

Fail-on-old proof: parser-help/subcommand tests verify task briefs are absent by default,
present flag-on, model-pack options absent, the Telegram polling group absent, generic
Telegram ingest rejected, retained core/vNext groups present, and no deleted name appears.

## Scheduler

- Delete hosted Telegram scheduled delivery/listing code with the Telegram modules.
- Keep vNext memory scheduler workflows and daemon; none is the deleted hosted channel
  delivery system.
- Keep allowlist-aware vNext Telegram raw-update ingestion as an on-demand connector,
  not polling and not a scheduled outbound notification job.

Fail-on-old proof: import-spec and source/registry tests require no deleted Telegram
notification/delivery job or handler, while the vNext scheduler workflow inventory and
connector ingestion smoke remain green.

## Web

### Permanently delete: 51 tracked files, 14,018 lines

```text
apps/web/app/admin/page.test.tsx
apps/web/app/admin/page.tsx
apps/web/app/chat/loading.tsx
apps/web/app/chat/page.test.tsx
apps/web/app/chat/page.tsx
apps/web/app/chief-of-staff/page.test.tsx
apps/web/app/chief-of-staff/page.tsx
apps/web/app/onboarding/page.test.tsx
apps/web/app/onboarding/page.tsx
apps/web/app/settings/page.test.tsx
apps/web/app/settings/page.tsx
apps/web/components/chief-of-staff-action-handoff-panel.test.tsx
apps/web/components/chief-of-staff-action-handoff-panel.tsx
apps/web/components/chief-of-staff-execution-routing-panel.test.tsx
apps/web/components/chief-of-staff-execution-routing-panel.tsx
apps/web/components/chief-of-staff-follow-through-panel.test.tsx
apps/web/components/chief-of-staff-follow-through-panel.tsx
apps/web/components/chief-of-staff-handoff-queue-panel.test.tsx
apps/web/components/chief-of-staff-handoff-queue-panel.tsx
apps/web/components/chief-of-staff-outcome-learning-panel.test.tsx
apps/web/components/chief-of-staff-outcome-learning-panel.tsx
apps/web/components/chief-of-staff-preparation-panel.test.tsx
apps/web/components/chief-of-staff-preparation-panel.tsx
apps/web/components/chief-of-staff-priority-panel.test.tsx
apps/web/components/chief-of-staff-priority-panel.tsx
apps/web/components/chief-of-staff-weekly-review-panel.test.tsx
apps/web/components/chief-of-staff-weekly-review-panel.tsx
apps/web/components/hosted-admin-panel.test.tsx
apps/web/components/hosted-admin-panel.tsx
apps/web/components/hosted-onboarding-panel.tsx
apps/web/components/hosted-settings-panel.test.tsx
apps/web/components/hosted-settings-panel.tsx
apps/web/components/mode-toggle.tsx
apps/web/components/request-composer.test.tsx
apps/web/components/request-composer.tsx
apps/web/components/response-composer.test.tsx
apps/web/components/response-composer.tsx
apps/web/components/response-history.test.tsx
apps/web/components/response-history.tsx
apps/web/components/thread-create.test.tsx
apps/web/components/thread-create.tsx
apps/web/components/thread-event-list.test.tsx
apps/web/components/thread-event-list.tsx
apps/web/components/thread-list.test.tsx
apps/web/components/thread-list.tsx
apps/web/components/thread-summary.test.tsx
apps/web/components/thread-summary.tsx
apps/web/components/thread-trace-panel.test.tsx
apps/web/components/thread-trace-panel.tsx
apps/web/components/thread-workflow-panel.test.tsx
apps/web/components/thread-workflow-panel.tsx
```

Keep `thread-health-dashboard.tsx`, shared execution-summary styles, and
`.response-copy` because retained continuity/vNext views use them.

### Default routes and gate

Default web exposes exactly seven views: `/`, `/vnext`, `/artifacts`, `/memories`,
`/continuity`, `/entities`, and `/traces`.

`/approvals`, `/tasks`, `/gmail`, and `/calendar` remain tracked but use a server-only
resolution of `ALICE_LEGACY_SURFACES`; the client shell receives the resolved boolean.
Default navigation hides them and their server pages call `notFound()`. Flag-on renders
and navigates to them. No `NEXT_PUBLIC_*` bypass exists. The artifact page stops fetching
or advertising the deleted hosted current-workspace endpoint.

Fail-on-old proof: route-file absence test for all 51 paths, default/flag-on rendered
shell navigation tests, page-level `notFound` tests, retained seven-view navigation
browser test, and dead API-client name/fixture absence checks. A recursive filesystem
inventory additionally requires exactly the seven core and four gated `page.tsx` files,
requires the middleware matcher to equal the four gated paths, and proves a synthetic
extra page fails. Rendered-copy tests require on-demand caller-supplied Telegram data and
externally extracted screenshot/transcript text while rejecting live polling, webhook,
Alice-executes-OCR/transcription, and retry-execution implications.

## PostgreSQL and SQLite

### PostgreSQL

- Historical tables/migrations for removed surfaces remain immutable and inert; unused
  hosted bypass setters are removed from the active database helper API.
- `POST /v1/workspaces/bootstrap` is the only creator. A new local identity adapter
  requires the foundational core `users` row, then deterministically ensures one user
  account, one local workspace, and membership for the requested local identity without
  overwriting existing account metadata; it sets both
  `app.current_user_account_id` and `app.current_user_id` RLS contexts.
- Provider records, capabilities, invocation telemetry, bootstrap status, and response
  jobs remain PostgreSQL adjacent-runtime storage.
- Provider endpoints require that prior bootstrap and fail clearly when it is absent.
  Focused role-separated live PostgreSQL tests cover local bootstrap, foreign identity
  isolation, provider register/list/get/update/test/discovery, runtime invocation,
  idempotent replay, telemetry, and target hardening without bearer sessions/model packs.

### SQLite

- No SQLite schema or migration changes are required: hosted/provider configuration is
  PostgreSQL-only, and deleted/gated mounts do not alter memory-store semantics.
- No fictitious SQLite provider-workspace implementation will be added.
- Existing SQLite/PostgreSQL parity tests for shared memory, retrieval, artifact, MCP,
  continuity, and Telegram raw-source cursor/dedupe/allowlist contracts remain the
  store-level proof. A focused regression asserts
  the shared flag parser and mount filtering are storage-independent.

The explicit parity decision is therefore: **both stores are exercised for every
retained shared memory and vNext connector contract, including Telegram raw-source
cursor/dedupe/allowlist; only PostgreSQL is exercised for the existing PostgreSQL-only
provider/local-workspace boundary**.

## Test-file disposition

The brief says 22 phase-named files / 8,672 lines. The tracked named union actually has
18 files / 8,610 lines. Adding the 62-line immutable migration-shape test yields 19 files
/ 8,672 lines, but that test must remain. The implementation records the discrepancy
rather than deleting migration history.

### Delete eight phase/surface integration pins

- `tests/integration/test_phase10_beta_hardening_launch_api.py`
- `tests/integration/test_phase10_chat_continuity_approvals_api.py`
- `tests/integration/test_phase10_daily_brief_notifications_api.py`
- `tests/integration/test_phase10_telegram_transport_api.py`
- `tests/integration/test_phase11_model_packs_api.py`
- `tests/integration/test_phase14_design_partner_launch_api.py`
- `tests/unit/test_phase10_beta_hardening_helpers.py`
- `tests/unit/test_phase10_hosted_modules.py`

Exclusively owned implementation tests for the deleted chief/model-pack/Telegram/hosted
modules are also removed with those modules; concentrated fail-on-old surface tests
replace them.

### Replace/rename five

- `test_phase10_identity_workspace_bootstrap_api.py` -> neutral local single-workspace/
  provider identity test with no hosted session/device/preferences behavior.
- `test_phase11_provider_runtime_api.py` -> `test_provider_runtime_api.py`, retaining
  registration/discovery/test/update/invoke/idempotency/telemetry/target-hardening cases.
- `test_openclaw_mcp_integration.py` -> core eleven-tool recall/resume path without
  legacy debug dependence.
- `test_phase13_alice_lite_assets.py` -> `test_alice_lite_assets.py`, a neutral
  local-runtime profile contract.
- `test_phase14_reference_integrations.py` -> future-facing agent-integration docs.

### Retain five and immutable migration shapes

- `tests/integration/test_openclaw_import.py`
- `tests/integration/test_openclaw_one_command_demo.py`
- `tests/unit/test_openclaw_adapter.py`
- `tests/unit/test_hermes_bridge_demo.py`
- `tests/unit/test_hermes_memory_provider.py`
- all migration shape/checksum/history tests.

No coverage threshold is lowered. Obsolete broad matrices that assert removed routes,
files, or copy are rewritten into Phase-1 truth gates rather than kept as false scope.

### Acceptance-chain dependency closure

Collection after the `/v0/responses` deletion exposed an obsolete acceptance/Phase-4
receipt chain whose carriers imported the removed response suite. It is retired rather
than relabeled as core evidence. The complete 30-path carrier, locked by
`tests/unit/test_retired_acceptance_chain.py`, is:

- scripts: `run_phase2_acceptance.py`, `run_mvp_acceptance.py`,
  `run_phase3_acceptance.py`, `run_phase4_acceptance.py`,
  `run_phase4_readiness_gates.py`, `run_phase4_validation_matrix.py`,
  `run_phase4_release_candidate.py`, `generate_phase4_mvp_exit_manifest.py`,
  `verify_phase4_mvp_exit_manifest.py`, `run_phase4_mvp_qualification.py`, and
  `verify_phase4_mvp_signoff_record.py`;
- integration tests: `test_mvp_acceptance_suite.py`,
  `test_phase4_acceptance_suite.py`, `test_phase4_readiness_gates.py`,
  `test_phase4_validation_matrix.py`, `test_phase4_release_candidate.py`,
  `test_phase4_mvp_exit_manifest.py`, `test_phase4_mvp_qualification.py`,
  `test_mvp_readiness_gates.py`, and `test_mvp_validation_matrix.py`;
- unit wrappers: `test_phase2_gate_wrappers.py` and
  `test_phase4_gate_wrappers.py`; and
- runbooks: `mvp-acceptance-suite.md`, `mvp-ship-gate-magnesium-reorder.md`,
  `mvp-validation-matrix.md`, `phase4-acceptance-suite.md`,
  `phase4-readiness-gates.md`, `phase4-validation-matrix.md`,
  `phase4-mvp-qualification.md`, and `phase4-closeout-packet.md`.

The surviving Phase-2/MVP/Phase-3 readiness and validation script names are
compatibility aliases for the neutral core matrix only. Historical archive verification
remains, with its test generating an inline historical fixture rather than importing a
deleted release-candidate generator.

## Documentation, control, and version surfaces

- Bump only `pyproject.toml` and `apps/web/package.json` to `0.11.0`.
- Add pending/pending `docs/release/v0.11.0-release-notes.md` and an Unreleased v0.11.0
  `CHANGELOG.md` entry. Latest-published/checksum/install references remain v0.10.4.
- Add candidate markers to `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
  `CURRENT_STATE.md`, byte-identical `.ai/handoff/CURRENT_STATE.md`, `PRODUCT_BRIEF.md`,
  `RELEASING.md`, and `docs/vnext/README.md`.
- Rewrite `ARCHITECTURE.md` around continuity/retrieval/agent interfaces, adjacent
  provider runtime, default/legacy surfaces, and a Removed Legacy Surfaces appendix.
- Replace the hosted-RLS rule in `RULES.md` with a local single-workspace invariant and
  explicit prerequisites for future multi-tenant reintroduction.
- Move Repair Batch 9-16/refreeze chronology from `ROADMAP.md` and both current-state
  mirrors to `docs/handoff/history/v0.10.4-repair-batches.md`; make active controls short,
  future-facing, and mirror-identical.
- Formally retire the Batch-16 active current-tree/version pin in
  `scripts/check_control_doc_truth.py`: require the old handoff directory and historical
  markers unconditionally, but remove the v0.10.4 version lock, filtered HEAD/tree hash,
  and worktree allowlist. Missing/renamed history or marker drift must still fail.
- Rewrite `.ai/active/SPRINT_PACKET.md` for Phase 1 with an explicit Phase 2 stop. Govern
  it at no more than 120 lines / 8,192 bytes and mutation-test whitespace-normalized
  stale live-ledger, Phase-2-active, and Alice-executes-OCR/transcription claims.
- Rewrite active vNext OCR/transcription claims as ingestion of text extracted by
  external tools; Alice itself does not execute OCR/transcription.
- Delete the operational-looking `phase2-closeout-packet.md` and
  `phase3-closeout-packet.md` runbooks. Replace them with one explicitly
  non-operational archive history, link it only from the process archive index, and
  guard both retired paths plus live-document references.
- Delete `docs/design-partners/`. Rename
  `docs/alpha/design-partner-onboarding.md` to `docs/alpha/onboarding.md` and update live
  references/tests. Remove active hosted/Telegram-channel/model-pack docs while
  preserving historical handoffs, changelog, and immutable release records.

Fail-on-old proof: control-doc truth tests cover unconditional history presence and
marker drift; v0.11/current production changes no longer trip the retired v0.10.4 pin.
Canonical truth tests cover doc length/no inline repair ledger, mirror identity,
candidate markers, sprint bounds and forbidden-claim mutations, external-extraction
wording, versions, pending release-note state, and exact retirement of the two closeout
runbooks.

## Handoff and freeze surfaces

The handoff directory contains `README.md`, this inventory, `FIX_MATRIX.md`,
`BUILD_REPORT.md`, `ENGINEER_HANDOFF.md`, and reviewer-owned `REVIEW_REPORT.md`.
The builder never creates the review report.

The frozen receipt starts from base `8520f29` and records a NUL-delimited
path/mode/content/deletion manifest for the complete changed carrier. It excludes only
`BUILD_REPORT.md`, `REVIEW_REPORT.md`, the user's `coverage.json`, and the user's
`uv.lock`; two consecutive reproductions must match. No commit, stage, push, tag,
publish, or Phase 2 work is permitted.

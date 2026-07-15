# Alice v0.11.0 Phase 1 Fix Matrix

## Decision summary

Phase 1 is implemented as a product-boundary cut, not a redesign. Permanently
removed surfaces are deleted through their route, module, contract, CLI/MCP,
web, test, and documentation carriers. Retained compatibility surfaces are
mount-time gated. Provider invocation, retrieval, memory, continuity,
provenance, traces, entities, artifacts, agent keys, and the local review
console remain.

No cybersecurity audit or Phase 2 debt sweep was performed.

## Phase 1 sign-off deviations

| ID | Disposition | Carrier result | Proof |
|---|---|---|---|
| D1 | Ratified | The ingest-only, allowlisted Telegram raw-source endpoint stays default-on with no transport, polling, token, delivery, or scheduling seam. | Existing exact HTTP inventory plus Telegram boundary unit, web, SQLite, and PostgreSQL proofs. |
| D2 | Accepted | The v0.11.0 full integration suite remains flag-on. The flag-off default-surface integration smoke job is recorded as a required Phase 2 CI deliverable and is deliberately absent here. | Workflow/test-posture guard remains unchanged; carrier diff contains no Phase 2 CI implementation. |
| D3 | Closed | Production `Settings` and `validate_env.sh` no longer require dead S3 credentials. Dormant S3 configuration remains compatible, but the health response no longer echoes its endpoint. | Fail-on-old core-only production settings and `.env` tests; explicit unit/integration health key-absence assertions; retained auth/database/CORS validation tests. |

Riders are limited to deleting the five already-empty removed web-route
directories and documenting import-time legacy-flag restart behavior plus
hosted-provider re-registration after upgrade.

## Surface matrix

| Area | Disposition | Implementation | Fail-on-old / verification |
|---|---|---|---|
| Telegram channels | Deleted | Removed the channel, continuity-delivery, notification, polling, CLI, MCP, HTTP, config, env, packaging, and web carriers. Kept only vNext caller-supplied raw updates with an explicit chat allowlist. Historical event config is rebuilt from an exact field allowlist so old token/poll keys cannot leak. The web has no token, secret-ref, polling, interval, or empty-update sync control. | Removed-operation and exact 14-module package-file/import-spec guards; generic Telegram config/sync rejection before fetch; rendered web boundary tests; Ubuntu-template absence guard; SQLite cursor/dedupe/allowlist test; live PostgreSQL raw-source parity. |
| Hosted admin and design partners | Deleted | Removed hosted admin, rollout, telemetry, rate-limit, design-partner modules, routes, contracts, panels, and active runbooks. | Permanent route inventory, deleted public-contract guard, deleted-file/web tests, clean import scan. |
| Hosted auth, devices, preferences, workspaces | Deleted | Removed magic-link/session/device/preference/workspace CRUD. Added deterministic local identity/bootstrap; provider and retained `/v1` tests use `X-AliceBot-User-Id`. | Bootstrap header/idempotency/isolation tests; four retained identity suites; provider pre-bootstrap failure and tenant-isolation tests. |
| Chief-of-staff and model packs | Deleted | Removed services, routes, web UI, contracts, MCP/CLI arguments, public task-brief vocabulary, and active docs. The immutable task-brief database column remains only as the physical carrier for neutral `briefing_strategy`. The reference handoff fixture uses `briefing_strategy: balanced` and recursively matches the full `ContinuityBriefResponse` graph, including exact action, trust, scope, provenance, section, summary, list, literal, and union shapes. | Exact module/file/route/public-name-prefix guards; model-pack retirement test; generic recursive required/optional/extra/type validation plus missing/extra-key mutations for every populated fixture record; Python/TypeScript reference-demo parity. |
| Public chat/response | Deleted | Removed `/v0/responses`, bundled chat UI, tests, acceptance runners, and Phase-4 receipt chain. Internal response jobs remain only for `/v1/runtime/invoke` idempotency. | Permanent route inventory; 30-path retired-chain guard; runtime replay unit and live provider tests. |
| Tasks, approvals, execution, Gmail, Calendar | Compatibility-gated | Mounted only when import-time `ALICE_LEGACY_SURFACES` is exactly `1`; worker task ticking uses the same exact parser. The retained proxy executor is imported only when the gated execute handler is actually invoked. | Isolated-process HTTP tests cover null/blank/false-like/non-exact values, exact `1`, same-process environment mutation, default `sys.modules` absence, and flag-on lazy proxy mounting; full integration runs flag-on; workflow/Makefile shape guard keeps unit default-off and integration flag-on. |
| MCP | Core plus explicit compatibility | Eleven core tools by default and for every agent-key-bound server. Long-tail memory tools require `ALICE_MCP_LEGACY_TOOLS`; task-brief tools additionally require the HTTP legacy flag. Tools backed only by deleted surfaces are gone. | Exact 11/73/76/11 inventories, schema closure, key-bound rejection, and OpenClaw core-only integration. |
| CLI and scheduler | Trimmed/gated | Removed Telegram polling/token and deleted-surface commands. Task ticking requires exact legacy opt-in. Task-brief output uses neutral vocabulary. | CLI absence and help tests; worker exact-flag tests; focused owned suite. |
| Provider runtime | Retained adjacent core | Provider registration/discovery/update/test and runtime invocation require prior local bootstrap; scripts use local identity, never hosted bearer sessions. Model-pack selection was removed. | 22 live PostgreSQL provider/runtime tests, AutoGen transport guard, local-provider demo tests, idempotent replay, telemetry, target hardening. |
| Web | Seven default views plus four gated views | Deleted 51 tracked files (14,018 lines); removed hosted/chat/chief/settings/onboarding carriers; server-only exact flag controls approvals/tasks/Gmail/Calendar. Telegram is on-demand caller-supplied raw updates only, and screenshots/transcripts are externally extracted text payloads. | Recursive filesystem inventory pins exactly 7 core + 4 gated `page.tsx` files, exact four middleware matchers, and synthetic-extra failure; rendered copy/forbidden-claim tests; unit/coverage/typecheck/lint/build/budget; default, legacy, outage, and partial-outage Playwright matrices. |
| OpenAPI | Reconciled fail-closed | Removed dead contracts and 137 physical registry entries. Exact mounted registry is 182 default / 231 flag-on; the 63 permanently removed operations are disjoint. Tags and app description describe the local continuity layer. | Registry closure, typed payload, phantom-key, isolated default/flag counts, and permanently-removed disjointness tests. |
| PostgreSQL and SQLite | Historical schema retained; current behavior proved | No migration edits. PostgreSQL owns the existing provider/local-workspace boundary. Shared raw-source and memory behavior remains backend-parity tested. | Immutable migration diff readback; live role-separated Postgres suite; SQLite Telegram raw-source regression; existing shared-store matrices. |
| Docs, control, and release identity | Rewritten | Version sources are `0.11.0`; active docs describe the candidate and latest published v0.10.4 truth. Repair ledgers moved to history and the control guard no longer depends on stale Batch-16 current-tree pins. The active sprint packet is Phase-1-only and bounded; obsolete Phase 2/3 closeout packets are replaced by explicitly non-operational archive history. | Control-doc truth, mutation tests for stale ledger/Phase-2-active/Alice-executes-extraction claims, 120-line/8,192-byte sprint bounds, mirrored current-state tests, exact retired-runbook/reference guards, release-static. |
| Dead limiter residue | Deleted | Removed the unused response/entrypoint limiter classes, globals, Redis fallback import, settings defaults/parser/validation, env examples, script exports, integration fixture, and obsolete tests. Preserved `_request_client_identifier` as a trust-boundary helper. | Source/carrier guard covers production, config, env, scripts, and integration setup; settings ignore retired env keys; helper-retention test. |

## Test-carrier reconciliation

The work brief's phase-named count combined 18 named active test files with one
immutable 62-line migration-shape test to arrive at 8,672 lines. The migration
test remains. Surface-owned tests were deleted; provider, OpenClaw, Alice Lite,
and reference-integration carriers were renamed or reframed around retained
core behavior. Collection also exposed the exclusively obsolete
`/v0/responses` acceptance/Phase-4 chain, which is recorded as a 30-path
dependency closure in `SURFACE_INVENTORY.md`.

Coverage thresholds were not lowered.

## Explicit non-closures

- Phase 2 response hygiene, text-folding parity, bounded project-event lookup,
  reject-leg hardening, redaction policy, migration defensive edges, and
  remaining test-infrastructure debt are not part of this tree.
- Phase 3 router/store restructuring did not begin.
- No semantic release attestation, release-SHA CI, tag, GitHub Release, or PyPI
  publication was attempted; those require a committed final SHA and release
  credentials after independent approval.

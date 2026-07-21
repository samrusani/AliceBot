# Phase 5 Enterprise Track Build Report

> Builder evidence only. The authoritative code-carrier verdict belongs in the
> independent reviewer-authored `REVIEW_REPORT.md`. Phase 5 completion remains
> **NO-GO pending owner-only gates**. Stage A is repository preparation and
> internal evidence; the owner-appointed 5.1.c external assessment is Stage B
> and cannot be self-certified by this carrier.

## Carrier identity

- Source commit: `c9d24243920a694eaf00ad595da392a1478710dd`
- Source tree: `ecc16a53f580308959e97e8b1f02edd04bbe3bfc`
- Source branch at handoff: `main`
- Carrier state: intentionally uncommitted and unstaged
- Python package version: `0.13.1`
- Web package version: `0.13.1`
- Target release after owner/release-engineer gates: `0.14.0`

## Final verification

| Lane | Reproduced result | Evidence boundary |
|---|---|---|
| Python unit and coverage | 4,012 passed, 1 skipped; total coverage 80.55%; API/router aggregate floor passed at 45% | Full application-unit run after Phase 5 production changes and before final evidence/handoff-only guard additions; those additions received focused reruns below |
| PostgreSQL integration | 405 passed, 1 skipped | Full role-separated PostgreSQL/pgvector run after browser-capability production changes; later ops/config evidence refinements were covered by the focused PostgreSQL drills below |
| Default surface | 2 passed with `ALICE_LEGACY_SURFACES`, `ALICE_MCP_LEGACY_TOOLS`, and `ALICE_AGENT_API_KEY` unset and `--require-executed-tests` | Covers the default-surface round trip and OpenAI Agents SDK tool |
| Phase 5 focused Python | 93 passed | Ops evidence, deployment contract, and release-polish selection after the final PostgreSQL-client preflight changes |
| PostgreSQL 16 ops drill | `--backend all` exited 0 with status `passed`, no proof gaps, and zero residual `alice_phase5_ops_%` databases | PostgreSQL server/client 16.13; SQLite physical/portable/v0.12-upgrade and PostgreSQL dump/destroy/restore, migrations 0093/0094, count, recall, signed-embedding, and monitoring checks passed |
| PostgreSQL mismatch drill | Failed closed with exact `postgres_client_major_mismatch`; zero disposable databases created | PostgreSQL 16.13 server against Homebrew libpq 18.4 client tools |
| Web unit | 53 files, 236 tests passed | Full Vitest lane |
| Web coverage | Core: 219 tests and 90.26%; vNext: 17 tests and 81.83% | Both configured coverage lanes passed |
| Web static/build/budgets | Typecheck, lint, production build, and budgets passed; `/` 106,168 bytes, `/continuity` 113,580 bytes, `/vnext` 137,673 bytes | Current Phase 5 web carrier |
| Browser integration | 24 passed: 21 core, 1 legacy, 1 outage, 1 partial | Full Playwright posture matrix |
| LongMemEval | 135 passed; evidence checker passed all 7 required arms | Current Phase 5 application behavior |
| Dependency posture | Advisory harness 5/5; live npm bulk audit reported zero findings in 55 production packages and 525 full-tree packages | Network-backed advisory checks were rerun outside the restricted sandbox after its loopback denial |
| Static/control checks | Focused mypy, Ruff, YAML, Bash, and `git diff --check` passed | Includes the final evidence/deployment/release-polish state |
| Handoff truth guard | Final guard: 10 passed, 1 expected integrated-mode skip; Ruff and mypy passed; explicit 122-path manifest exactly matched the live carrier | Reviewer report is present and was independently verified; it remains reviewer-owned and receipt-loop-excluded |
| Deployment validator | Local contract passed with exactly one blocker: `owner_real_host_deployment_receipt` | This is deliberately not real-host evidence |

No production source changed after its applicable full or focused verification.
The final handoff-only receipt guard changes were separately type-checked,
linted, and exercised through bytes, mode, deletion, symlink-parent, workflow,
receipt-input, protected-path, handoff-directory, and report-drift negatives.

## Owner and environment gates

- `5.1.c OWNER GATE OPEN`: no independent external security assessment receipt.
- `5.4 OWNER GATE OPEN`: no real-host deployment receipt.
- `COMMITTED-SHA CI GATE OPEN`: the carrier is uncommitted, so PR/main-only
  workflow results do not yet exist.
- Local Caddy and ShellCheck binaries were unavailable. Caddy syntax, public
  TLS/DNS/CA, firewall, and certificate lifecycle remain in the owner gate;
  adversarial repository tests validate only the checked-in contract.

## Explicit carrier receipt

Receipt format:
`alice-v0.14.0-phase5-enterprise-track-explicit-carrier-v1`.

Receipt-listed paths (122, bytewise sorted):

```text
.github/workflows/deployment-guide-smoke.yml
.github/workflows/ops-evidence.yml
.github/workflows/tests.yml
.gitignore
Makefile
README.md
SECURITY.md
apps/api/alembic/versions/20260721_0094_browser_clip_capabilities.py
apps/api/src/alicebot_api/browser_clip_capabilities.py
apps/api/src/alicebot_api/config.py
apps/api/src/alicebot_api/main.py
apps/api/src/alicebot_api/openapi_operation_contracts.py
apps/api/src/alicebot_api/routers/vnext_memories.py
apps/api/src/alicebot_api/sqlite_schema.py
apps/api/src/alicebot_api/sqlite_store.py
apps/api/src/alicebot_api/vnext_connectors.py
apps/api/src/alicebot_api/vnext_secrets.py
apps/api/src/alicebot_api/vnext_store.py
apps/api/src/alicebot_api/vnext_stores/postgres/browser_clip_capabilities.py
apps/api/src/alicebot_api/vnext_stores/sqlite/browser_clip_capabilities.py
apps/web/app/approvals/loading.tsx
apps/web/app/approvals/page.test.tsx
apps/web/app/approvals/page.tsx
apps/web/app/artifacts/loading.tsx
apps/web/app/artifacts/page.test.tsx
apps/web/app/artifacts/page.tsx
apps/web/app/entities/loading.tsx
apps/web/app/entities/page.test.tsx
apps/web/app/entities/page.tsx
apps/web/app/globals.css
apps/web/app/memories/loading.tsx
apps/web/app/memories/page.test.tsx
apps/web/app/memories/page.tsx
apps/web/app/traces/loading.tsx
apps/web/app/traces/page.test.tsx
apps/web/components/approval-detail.tsx
apps/web/components/approval-list.tsx
apps/web/components/artifact-chunk-list.tsx
apps/web/components/artifact-detail.tsx
apps/web/components/artifact-list.tsx
apps/web/components/browser-clipper.test.ts
apps/web/components/entity-detail.tsx
apps/web/components/entity-edge-list.tsx
apps/web/components/entity-list.tsx
apps/web/components/memory-label-list.tsx
apps/web/components/memory-review-lists.test.tsx
apps/web/components/memory-revision-list.tsx
apps/web/components/trace-list.tsx
apps/web/components/vnext-brain-workspace.tsx
apps/web/components/vnext-operator-auth.test.tsx
apps/web/components/vnext-workspace-model.ts
apps/web/lib/api.test.ts
apps/web/lib/api.ts
apps/web/test/browser/navigation.spec.ts
apps/web/test/browser/review-dashboard-demo.spec.ts
docs/alpha/README.md
docs/alpha/agent-integration.md
docs/alpha/backup-and-restore.md
docs/alpha/demo-mode.md
docs/alpha/first-run.md
docs/alpha/headless-ubuntu-install.md
docs/alpha/known-limitations.md
docs/alpha/quickstart.md
docs/alpha/review-dashboard-demo.md
docs/alpha/security-and-privacy.md
docs/deployment/single-tenant-self-hosted.md
docs/handoff/2026-07-21-v0.14.0-phase5-enterprise-track/ENGINEER_HANDOFF.md
docs/handoff/2026-07-21-v0.14.0-phase5-enterprise-track/FIX_MATRIX.md
docs/handoff/2026-07-21-v0.14.0-phase5-enterprise-track/README.md
docs/runbooks/disaster-recovery.md
docs/runbooks/health-and-monitoring.md
docs/runbooks/upgrade-v0.12-to-current.md
docs/runbooks/vnext-dogfood-daily-checklist.md
docs/security/README.md
docs/security/auth-authorization.md
docs/security/dependency-posture.md
docs/security/external-review-brief.md
docs/security/input-validation.md
docs/security/secrets-redaction.md
docs/security/stage-a-evidence.md
docs/security/threat-model.md
docs/vnext/architecture.md
docs/vnext/security-privacy.md
packaging/cloud/Caddyfile.example
packaging/cloud/single-tenant.env.example
scripts/_phase5_ops_seed.py
scripts/migrate.sh
scripts/run_phase5_ops_evidence.py
scripts/run_single_tenant_deployment_smoke.py
tests/integration/test_browser_clip_capabilities.py
tests/integration/test_default_surface_integration.py
tests/integration/test_migrations.py
tests/integration/test_provider_runtime_api.py
tests/integration/test_review_dashboard_demo.py
tests/integration/test_stage_a_agent_key_isolation.py
tests/unit/test_20260721_0094_browser_clip_capabilities.py
tests/unit/test_browser_clip_capabilities.py
tests/unit/test_browser_clip_capability_storage.py
tests/unit/test_config.py
tests/unit/test_legacy_gated_router_split.py
tests/unit/test_legacy_surface_test_posture.py
tests/unit/test_main.py
tests/unit/test_memories_legacy_router_split.py
tests/unit/test_phase5_enterprise_handoff_truth.py
tests/unit/test_phase5_ops_evidence.py
tests/unit/test_providers_router_split.py
tests/unit/test_runnable_docs_secret_argv.py
tests/unit/test_single_tenant_deployment.py
tests/unit/test_sqlite_store.py
tests/unit/test_stage_a_vnext_auth_surface.py
tests/unit/test_store_events_revisions_split.py
tests/unit/test_store_graph_open_loops_split.py
tests/unit/test_store_memory_access_split.py
tests/unit/test_store_memory_lifecycle_split.py
tests/unit/test_surface_gates.py
tests/unit/test_vnext_agent_keys.py
tests/unit/test_vnext_connectors.py
tests/unit/test_vnext_main.py
tests/unit/test_vnext_production_proxy_auth.py
tests/unit/test_vnext_release_polish.py
tests/unit/test_vnext_secrets.py
tests/unit/test_workspaces_router_split.py
```

The serialized receipt was 20,845 bytes in each of two independent live reads.
Both reads produced the same digest:

carrier receipt sha256: `4cf7e08b6faddd681daf2217fe3c7184746be4ca34cf7b71098637ce7eb2ed34`

Receipt-loop exclusions are exactly:

```text
docs/handoff/2026-07-21-v0.14.0-phase5-enterprise-track/BUILD_REPORT.md
docs/handoff/2026-07-21-v0.14.0-phase5-enterprise-track/REVIEW_REPORT.md
```

Any edit to a receipt input invalidates the digest and independent verdict.

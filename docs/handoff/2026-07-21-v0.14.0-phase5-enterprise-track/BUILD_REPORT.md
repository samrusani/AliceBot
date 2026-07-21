# Phase 5 Enterprise Track Build Report

> Builder evidence only. The authoritative code-carrier verdict belongs in the
> independent reviewer-authored `REVIEW_REPORT.md`. Phase 5 completion remains
> **NO-GO pending the 5.4 owner gate and green committed-SHA CI**. Stage A and
> the retained Stage B history support only the owner-accepted claim of
> "automated security scanning under OpenAI Trusted Access on the repository,
> plus internal adversarial review." The carrier grants no broader security
> assurance.

## Carrier identity

- Source commit: `c9d24243920a694eaf00ad595da392a1478710dd`
- Source tree: `ecc16a53f580308959e97e8b1f02edd04bbe3bfc`
- Superseded CI-only carrier: `e8d20189edfca5e9925cb3ed390e0621816899e7`
  with receipt `4cf7e08b...`; failed and not shippable
- Replacement topology: one fresh carrier commit directly on the source
  commit; `e8d2018` must not be in its ancestry
- Source branch at handoff: `codex/v0140-phase5-enterprise-track`
- Carrier state: intentionally uncommitted and unstaged
- Python package version: `0.13.1`
- Web package version: `0.13.1`
- Target release after owner/release-engineer gates: `0.14.0`

## Final verification

| Lane | Reproduced result | Evidence boundary |
|---|---|---|
| Python unit and coverage | Final depth-1/no-tag carrier: 4,034 passed, 10 skipped; total coverage 80.55%; exact 14-path API/router aggregate floor passed at 45% | Receipt-trailed direct-on-base scratch commit, with the base object unavailable and tracked/staged state clean |
| PostgreSQL integration | 407 passed, 1 skipped | Full role-separated run against disposable PostgreSQL 16.14 with pgvector 0.8.5; admin was superuser and application role was non-superuser |
| Default surface | 2 passed with legacy surfaces/tools and agent key unset, plus `--require-executed-tests` | Flag-off default-surface round trip and OpenAI Agents SDK tool both executed against the role-separated database |
| Ops and shallow-history contracts | Full-history receipt/truth plus ops: 45 passed; depth-1/no-tag receipt/truth plus ops: 42 passed, 3 deliberate history/tag skips | The no-tag lane delegates only authentic history-dependent proof; missing PostgreSQL URLs fail before tag lookup. Integrated mode ignores unrelated transient `.coverage.*` shards but fails on any receipt/report drift |
| Deployment contracts | 53 passed; deployment smoke status `passed` with exactly `owner_real_host_deployment_receipt` open | Includes missing-admin-DSN precedence without a repository `.venv`, exact example UUID sentinels, and exact Caddy host/upstream directives |
| Web unit | 53 files, 236 tests passed | Full Vitest lane after the two-layer bookmarklet serializer repair |
| Web coverage | Core: 219 tests, 90.26% statements/lines; vNext: 17 tests, 81.85% statements/lines | Both configured coverage lanes passed |
| Web static/build/budgets | Typecheck, full lint, production build, and budgets passed; `/` 106,168 bytes, `/continuity` 113,580 bytes, `/vnext` 137,822 bytes | Current repaired carrier; all routes retain 13,832-17,178 bytes of budget headroom |
| Browser integration | 24 passed: 21 core, 1 legacy, 1 outage, 1 partial; the hostile exact-payload clipper case also passed 10/10 under repetition | Full Playwright posture matrix with a script-free same-origin fixture and exact one-time-capability transport |
| CodeQL alert remediation | #515-#520 use a strict two-layer percent-encoded config blob; #521 covers all modeled dangerous schemes; #522 uses exact Caddy directive tokens | No suppression or allowlist; focused Python 52, Vitest 4, hostile browser round trip 10/10, build/type/lint/Ruff passed. Only fresh committed-SHA CodeQL can close the aggregate check |
| LongMemEval and eval contracts | 135 passed; evidence checker passed all 7 arms; vector contract 2 passed; six-suite model-free eval passed; canonical release gate failed closed without a vector provider | Preserves honest `fts_only` labeling and release-gate behavior |
| Dependency posture | Advisory harness 5/5; exact Gitleaks 8.30.1 reproduced the old `e8d2018` finding, then reported no leaks across the fresh one-commit `c9d2424..HEAD` replacement | No historical allowlist or scan suppression was added |
| Static/control checks | Control-doc truth, release check at `0.13.1`, full Ruff, exact CI mypy over 228 files, compileall, YAML parsing, Bash syntax, and `git diff --check` passed | `actionlint` and ShellCheck were unavailable locally; repository and committed-SHA workflow checks remain authoritative |
| Deployment validator | Local contract passed with exactly one blocker: `owner_real_host_deployment_receipt` | This is deliberately not real-host evidence |

No production source changed after the frozen matrix. The real branch was
flattened to the source commit with all 124 carrier/report paths unstaged and
an empty index. A disposable one-commit, direct-on-base carrier reproduced the
receipt and report trailers, passed the full-history and depth-1/no-tag truth
checks above, and passed the exact Gitleaks PR-range command. The first complete
shallow unit run exposed transient pytest-cov shards in the integrated-mode
worktree probe; the scoped fail-on-old repair was independently reviewed, and
the complete 4,034-test shallow rerun then passed.

## Owner and environment gates

- `5.1.c OWNER DISPOSITION ACCEPTED`: the accepted claim is "automated security
  scanning under OpenAI Trusted Access on the repository, plus internal
  adversarial review." It is not an external audit or certification.
- `5.4 OWNER GATE OPEN`: no real-host deployment receipt.
- `COMMITTED-SHA CI GATE OPEN`: the old commit failed. A fresh direct-on-base
  carrier must pass PR/main-only Gitleaks, CodeQL, tests, ops, and deployment
  workflows before release engineering may integrate it.
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

carrier receipt sha256: `94c990d7a67ebe1cd21e45a88a9cc850b06b3fefb2c372be9797e78b7a97dfb2`

Receipt-loop exclusions are exactly:

```text
docs/handoff/2026-07-21-v0.14.0-phase5-enterprise-track/BUILD_REPORT.md
docs/handoff/2026-07-21-v0.14.0-phase5-enterprise-track/REVIEW_REPORT.md
```

Any edit to a receipt input invalidates the digest and independent verdict.

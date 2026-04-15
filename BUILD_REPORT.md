# BUILD_REPORT

## Objective
Execute the `v0.3.2` release checklist against the completed Phase 12 baseline on `main`, record exact release-gate evidence, and determine whether the repo is ready for tagging.

## Release Baseline
- branch: `main`
- `HEAD`: `60430b7`
- latest published tag: `v0.2.0`
- current release target: `v0.3.2`
- merged implementation baseline:
  - `P12-S1` `e019f72`
  - `P12-S2` `0c849fd`
  - `P12-S3` `6d10d1b`
  - `P12-S4` `dd77643`
  - `P12-S5` `de19350`
- merged closeout / release-prep baseline:
  - `2e68fcb` Phase 12 closeout and `v0.3.2` release prep
  - `60430b7` bearer-auth follow-up for Phase 12 v1 APIs

## Exact Commands Run
- `docker compose up -d`
  - Result: PASS
  - Evidence: `alicebot-postgres`, `alicebot-redis`, and `alicebot-minio` reported `Running`
- `./scripts/migrate.sh`
  - Result: PASS
  - Evidence: upgraded through `20260414_0061` (`Phase 12 task-adaptive briefing persistence and model-pack strategy fields`)
- `./scripts/load_sample_data.sh`
  - Result: PASS
  - Evidence: fixture already present; returned `status=noop` for default user `00000000-0000-0000-0000-000000000001`
- `env APP_RELOAD=false ALICEBOT_AUTH_USER_ID=00000000-0000-0000-0000-000000000001 ./scripts/api_dev.sh`
  - Result: PASS
  - Evidence: API served on `http://127.0.0.1:8000`
- `curl -sS http://127.0.0.1:8000/healthz`
  - Result: PASS
  - Evidence: `{"status":"ok","environment":"development","services":{"database":{"status":"ok"}}...}`
- `python3 scripts/check_control_doc_truth.py`
  - Result: PASS
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
  - Result: PASS (`5 passed in 0.03s`)
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - Initial result: FAIL
  - Failure: `tests/unit/test_memory.py::test_get_memory_trust_dashboard_summary_is_deterministic_and_uses_canonical_components`
  - Root cause: stale expected retrieval fixture count (`6`) after the canonical retrieval fixture suite had already grown to `7`
  - Remediation: updated the stale assertion in `tests/unit/test_memory.py`
  - Re-run result: PASS (`1247 passed in 228.94s`)
- `pnpm --dir apps/web test`
  - Result: PASS (`199 passed`)
- `./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py`
  - Result: PASS
  - Evidence: provider registered, bridge ready, single external enforced
- `./.venv/bin/python scripts/run_hermes_mcp_smoke.py`
  - Result: PASS
  - Evidence: recall/resume/review flow validated; review queue resolved cleanly
- `./.venv/bin/python scripts/run_hermes_bridge_demo.py`
  - Result: PASS
  - Evidence: `recommended_path=provider_plus_mcp`, `fallback_path=mcp_only`, both smoke steps returned `0`
- `./.venv/bin/python -m alicebot_api --database-url postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot --user-id 00000000-0000-0000-0000-000000000001 evals run --report-path eval/baselines/public_eval_harness_v1.json`
  - Result: PASS
  - Evidence: report status `pass`, `suite_count=5`, `case_count=12`, `failed_case_count=0`, report digest `bf3ac58edc070a74bb6faa7a66536a08154d114494932c4d231a500e6899ed29`

## Documentation / Public Repo Readiness
- `README.md` aligned to completed Phase 12 and `v0.3.2` release target
- `docs/quickstart/local-setup-and-first-result.md` aligned
- `docs/integrations/mcp.md` aligned
- `docs/integrations/hermes-bridge-operator-guide.md` aligned
- `docs/evals/public_eval_harness.md` aligned
- `docs/briefing/task-adaptive-briefing.md` aligned
- `CONTRIBUTING.md`: present
- `SECURITY.md`: present
- `LICENSE`: present
- `CHANGELOG.md` contains a Phase 12 closeout / `v0.3.2` release-target entry

## Files Changed During Checklist Execution
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `tests/unit/test_memory.py`

## Outcome
- All runtime, test, web, Hermes, and eval release gates now pass on the current working tree.
- The only code-level issue uncovered by the checklist was a stale unit-test expectation; that has been corrected.
- The repo is release-ready in substance, but the working tree is not clean because the report updates and the test expectation fix are not yet committed.

## Remaining Before Tag
- commit the release-evidence updates and the stale test fix
- obtain explicit tag approval

## Recommended Next Step
Commit the release-checklist fixes/evidence, verify the worktree is clean, then execute `docs/release/v0.3.2-tag-plan.md`.

# Phase 9 Command Walkthrough

This page provides one reproducible command walkthrough using only shipped local paths.

## Scenario

1. Start local runtime.
2. Verify health.
3. Run recall/resume.
4. Import OpenClaw fixture.
5. Re-run recall on imported context.
6. Generate evaluation report.

## Commands

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
APP_RELOAD=false ./scripts/api_dev.sh
```

```bash
curl -sS http://127.0.0.1:8000/healthz
./.venv/bin/python -m alicebot_api recall --query local-first --limit 5
./.venv/bin/python -m alicebot_api resume --max-recent-changes 5 --max-open-loops 5
```

```bash
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_v1.json
./.venv/bin/python -m alicebot_api recall --thread-id cccccccc-cccc-4ccc-8ccc-cccccccccccc --project "Alice Public Core" --query "MCP tool surface" --limit 5
./.venv/bin/python -m alicebot_api resume --thread-id cccccccc-cccc-4ccc-8ccc-cccccccccccc --max-recent-changes 5 --max-open-loops 5
```

```bash
EVAL_USER_ID="$(./.venv/bin/python -c 'import uuid; print(uuid.uuid4())')"
EVAL_USER_EMAIL="phase9-eval-${EVAL_USER_ID}@example.com"
./scripts/run_phase9_eval.sh --user-id "${EVAL_USER_ID}" --user-email "${EVAL_USER_EMAIL}" --display-name "Phase9 Eval" --report-path eval/reports/phase9_eval_latest.json
```

## Expected Outcomes

- API health check returns `status=ok`.
- recall/resume return deterministic continuity output with provenance.
- importer command returns import summary with explicit source metadata.
- evaluation harness writes report JSON with summary status and metrics.

## Notes

Use a unique `--user-email` and `--user-id` if re-running import/eval flows in the same database and you need a fresh user scope.

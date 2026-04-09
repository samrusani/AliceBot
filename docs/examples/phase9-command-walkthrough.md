# Phase 9 Command Walkthrough

This page provides one reproducible command walkthrough using only shipped local paths.

## Scenario

1. Start local runtime.
2. Verify health.
3. Run one-command OpenClaw demo (`before -> import -> replay -> after`).
4. Generate evaluation report.

## Commands

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
APP_RELOAD=false ./scripts/api_dev.sh
```

```bash
curl -sS http://127.0.0.1:8000/healthz
./scripts/use_alice_with_openclaw.sh
```

```bash
EVAL_USER_ID="$(./.venv/bin/python -c 'import uuid; print(uuid.uuid4())')"
EVAL_USER_EMAIL="phase9-eval-${EVAL_USER_ID}@example.com"
./scripts/run_phase9_eval.sh --user-id "${EVAL_USER_ID}" --user-email "${EVAL_USER_EMAIL}" --display-name "Phase9 Eval" --report-path eval/reports/phase9_eval_latest.json
```

## Expected Outcomes

- API health check returns `status=ok`.
- OpenClaw demo shows before/after recall-resume value and idempotent replay.
- imported provenance includes source label `OpenClaw` and `source_kind=openclaw_import`.
- evaluation harness writes report JSON with summary status and metrics.

## Notes

Use a unique `--user-email` and `--user-id` if re-running import/eval flows in the same database and you need a fresh user scope.

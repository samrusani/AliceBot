# BUILD_REPORT.md

## sprint objective
Ship `P9-S37` by expanding importer coverage beyond OpenClaw to at least three production-usable importers total, generalizing deterministic provenance/dedupe posture across importers, and shipping a reproducible local evaluation harness with baseline report evidence for recall precision, resumption usefulness, correction effectiveness, importer success, and duplicate-memory posture.

## completed work
- Added two new production-usable importer paths:
  - `markdown_import` (`apps/api/src/alicebot_api/markdown_import.py`)
  - `chatgpt_import` (`apps/api/src/alicebot_api/chatgpt_import.py`)
- Generalized importer provenance/dedupe persistence:
  - shared importer model + normalization helpers in `apps/api/src/alicebot_api/importer_models.py`
  - shared importer persistence seam in `apps/api/src/alicebot_api/importers/common.py`
  - `openclaw_import.py` refactored to use shared importer persistence logic
- Added reproducible importer fixtures:
  - `fixtures/importers/markdown/workspace_v1.md`
  - `fixtures/importers/chatgpt/workspace_v1.json`
- Added importer loader commands:
  - `scripts/load_markdown_sample_data.py` + `scripts/load_markdown_sample_data.sh`
  - `scripts/load_chatgpt_sample_data.py` + `scripts/load_chatgpt_sample_data.sh`
- Added local evaluation harness and report writer:
  - `scripts/run_phase9_eval.py`
  - `scripts/run_phase9_eval.sh`
  - `apps/api/src/alicebot_api/retrieval_evaluation.py` extended with:
    - `run_phase9_evaluation`
    - `write_phase9_evaluation_report`
    - importer/eval metrics for recall, resumption, correction, and dedupe posture
- Generated and committed baseline evidence:
  - `eval/reports/phase9_eval_latest.json`
  - `eval/baselines/phase9_s37_baseline.json`
- Added tests for importer/eval behavior:
  - `tests/unit/test_importers.py`
  - `tests/unit/test_phase9_eval.py`
  - `tests/integration/test_markdown_import.py`
  - `tests/integration/test_chatgpt_import.py`
  - `tests/integration/test_phase9_eval.py`
  - plus shared-package test import stabilization via `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`
- Synced sprint-scoped docs and ADRs:
  - `README.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `RULES.md`, `.ai/handoff/CURRENT_STATE.md`, `docs/phase9-sprint-33-38-plan.md`
  - `docs/adr/ADR-005-import-provenance-and-dedupe-strategy.md`
  - `docs/adr/ADR-007-public-evaluation-harness-scope.md`

## incomplete work
- None inside `P9-S37` scope.
- Intentionally deferred (out of scope):
  - Claude importer path
  - CSV importer path
  - MCP tool-surface expansion
  - hosted/remote ingestion or evaluation infrastructure

## files changed
- `.ai/active/SPRINT_PACKET.md`
- `apps/api/src/alicebot_api/importer_models.py`
- `apps/api/src/alicebot_api/importers/__init__.py`
- `apps/api/src/alicebot_api/importers/common.py`
- `apps/api/src/alicebot_api/openclaw_import.py`
- `apps/api/src/alicebot_api/markdown_import.py`
- `apps/api/src/alicebot_api/chatgpt_import.py`
- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `scripts/load_markdown_sample_data.py`
- `scripts/load_markdown_sample_data.sh`
- `scripts/load_chatgpt_sample_data.py`
- `scripts/load_chatgpt_sample_data.sh`
- `scripts/run_phase9_eval.py`
- `scripts/run_phase9_eval.sh`
- `fixtures/importers/markdown/workspace_v1.md`
- `fixtures/importers/chatgpt/workspace_v1.json`
- `eval/reports/phase9_eval_latest.json`
- `eval/baselines/phase9_s37_baseline.json`
- `tests/unit/test_importers.py`
- `tests/unit/test_phase9_eval.py`
- `tests/integration/test_markdown_import.py`
- `tests/integration/test_chatgpt_import.py`
- `tests/integration/test_phase9_eval.py`
- `tests/__init__.py`
- `tests/unit/__init__.py`
- `tests/integration/__init__.py`
- `apps/web/components/approval-detail.test.tsx`
- `apps/web/components/continuity-open-loops-panel.test.tsx`
- `apps/web/components/workflow-memory-writeback-form.tsx`
- `README.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`
- `RULES.md`
- `.ai/handoff/CURRENT_STATE.md`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/adr/ADR-005-import-provenance-and-dedupe-strategy.md`
- `docs/adr/ADR-007-public-evaluation-harness-scope.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run
- `docker compose up -d`
  - PASS
- `./scripts/migrate.sh`
  - PASS
- `./scripts/load_sample_data.sh`
  - PASS (`status=noop`, already loaded)
- `./scripts/load_openclaw_sample_data.sh --user-id 00000000-0000-0000-0000-000000000038 --user-email openclaw-import-038@example.com --display-name "OpenClaw Import 038" --source fixtures/openclaw/workspace_v1.json`
  - PASS (`imported_count=4`, `skipped_duplicates=1`)
- `./scripts/load_markdown_sample_data.sh --user-id 00000000-0000-0000-0000-000000000038 --source fixtures/importers/markdown/workspace_v1.md`
  - PASS (`imported_count=4`, `skipped_duplicates=1`)
- `./scripts/load_chatgpt_sample_data.sh --user-id 00000000-0000-0000-0000-000000000038 --source fixtures/importers/chatgpt/workspace_v1.json`
  - PASS (`imported_count=4`, `skipped_duplicates=1`)
- `APP_RELOAD=false ./scripts/api_dev.sh`
  - PASS (startup observed; server on `127.0.0.1:8000`)
- `curl -sS http://127.0.0.1:8000/healthz`
  - PASS (`{"status":"ok", ...}`)
- `./.venv/bin/python -m alicebot_api --user-id 00000000-0000-0000-0000-000000000038 recall --thread-id eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee --project "Markdown Import Project" --query "markdown importer deterministic" --limit 5`
  - PASS (returned markdown-imported records with explicit provenance)
- `./.venv/bin/python -m alicebot_api --user-id 00000000-0000-0000-0000-000000000038 resume --thread-id eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee --project "Markdown Import Project" --max-recent-changes 5 --max-open-loops 5`
  - PASS (`last_decision` + `next_action` from `markdown_import`)
- `./scripts/run_phase9_eval.sh --user-id 00000000-0000-0000-0000-000000000039 --user-email phase9-eval-039@example.com --display-name "Phase9 Eval 039" --report-path eval/reports/phase9_eval_latest.json`
  - PASS (`status=pass`, all rates `1.0`)
- `./.venv/bin/python -m pytest tests/unit/test_importers.py tests/unit/test_phase9_eval.py -q`
  - PASS (`7 passed`)
- `./.venv/bin/python -m pytest tests/integration/test_openclaw_import.py tests/integration/test_markdown_import.py tests/integration/test_chatgpt_import.py tests/integration/test_phase9_eval.py -q`
  - PASS (`4 passed`)
- `./.venv/bin/python -m pytest tests/unit tests/integration`
  - PASS (`978 passed`)
- `pnpm --dir apps/web test`
  - PASS (`57 files, 192 tests`)

## blockers/issues
- Localhost database/network checks from sandboxed runs required escalated command execution for several required verification commands.
- One transient verification failure was encountered and resolved:
  - `load_openclaw_sample_data.sh` with a new user ID initially failed due global unique email constraint (`users_email_key`) when default import email was reused; rerun with unique `--user-email` succeeded.

## recommended next step
Execute `P9-S38` by turning the now-shipped importer/evaluation evidence and commands into launch-quality external docs without widening MCP transport or importer semantics.

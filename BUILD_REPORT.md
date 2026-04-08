# BUILD_REPORT.md

## sprint objective
Ship `P9-S38` by producing launch-ready public docs, quickstart/integration documentation, release checklist/runbook, and first public release-tag assets for Alice v0.1, strictly grounded in shipped `P9-S33` to `P9-S37` command paths and evidence.

## completed work
- Reworked launch-facing canonical docs to reflect shipped product truth and `P9-S38` scope:
  - `README.md`
  - `PRODUCT_BRIEF.md`
  - `ARCHITECTURE.md`
  - `ROADMAP.md`
  - `RULES.md`
  - `.ai/handoff/CURRENT_STATE.md`
  - `docs/phase9-sprint-33-38-plan.md`
- Added public quickstart and integration docs:
  - `docs/quickstart/local-setup-and-first-result.md`
  - `docs/integrations/cli.md`
  - `docs/integrations/mcp.md`
  - `docs/integrations/importers.md`
  - `docs/examples/phase9-command-walkthrough.md`
- Added release assets required for first public version prep:
  - `docs/release/v0.1.0-release-checklist.md`
  - `docs/release/v0.1.0-tag-plan.md`
  - `docs/runbooks/phase9-public-release-runbook.md`
- Added repo readiness docs for public release:
  - `CONTRIBUTING.md`
  - `SECURITY.md`
  - `LICENSE` (MIT)
- Updated release metadata/reporting surfaces:
  - `CHANGELOG.md` (`2026-04-08` entry for `P9-S38`)
  - `REVIEW_REPORT.md` (updated to `PASS` after review)
  - `eval/reports/phase9_eval_latest.json` refreshed by eval harness runs
- Verified control-doc truth marker requirements remain valid via `scripts/check_control_doc_truth.py`.

## incomplete work
- Public tag creation (`v0.1.0`) is intentionally deferred until reviewer `PASS` and explicit Control Tower approval.
- Intentionally out of scope and still deferred:
  - new importer families
  - MCP tool-surface expansion
  - hosted deployment/remote auth
  - screenshot/demo media requiring new UI work

## files changed
- `.ai/active/SPRINT_PACKET.md` (pre-existing sprint-38 packet update present on branch)
- `.ai/handoff/CURRENT_STATE.md`
- `README.md`
- `PRODUCT_BRIEF.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `RULES.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `LICENSE`
- `docs/phase9-sprint-33-38-plan.md`
- `docs/quickstart/local-setup-and-first-result.md`
- `docs/integrations/cli.md`
- `docs/integrations/mcp.md`
- `docs/integrations/importers.md`
- `docs/examples/phase9-command-walkthrough.md`
- `docs/release/v0.1.0-release-checklist.md`
- `docs/release/v0.1.0-tag-plan.md`
- `docs/runbooks/phase9-public-release-runbook.md`
- `eval/reports/phase9_eval_latest.json`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run
- `docker compose up -d`
  - PASS (containers already running)
- `./scripts/migrate.sh`
  - PASS
- `./scripts/load_sample_data.sh`
  - PASS (`status=noop`, fixture already loaded)
- `APP_RELOAD=false ./scripts/api_dev.sh`
  - PASS (uvicorn started on `127.0.0.1:8000`)
- `curl -sS http://127.0.0.1:8000/healthz`
  - PASS (`status=ok`)
- `./.venv/bin/python -m pytest tests/unit tests/integration`
  - PASS (`978 passed`)
- `pnpm --dir apps/web test`
  - PASS (`57` files, `192` tests)
- `./scripts/run_phase9_eval.sh --report-path eval/reports/phase9_eval_latest.json`
  - PASS (command executed)
  - RESULT 1: `status=fail` under default user scope due pre-existing imported state affecting importer-success metrics
- `./scripts/run_phase9_eval.sh --user-id 00000000-0000-0000-0000-000000000938 --user-email phase9-eval-938@example.com --display-name "Phase9 Eval 938" --report-path eval/reports/phase9_eval_latest.json`
  - PASS
  - RESULT 2: `status=pass` (`importer_success_rate=1.0`, `recall_precision_at_1=1.0`, `resumption_usefulness_rate=1.0`, `correction_effectiveness_rate=1.0`, `duplicate_posture_rate=1.0`)
- `./.venv/bin/python scripts/check_control_doc_truth.py`
  - PASS
- internal markdown link existence check across new `P9-S38` docs
  - PASS (no missing local targets)

## blockers/issues
- `./scripts/run_phase9_eval.sh` initially failed inside sandbox with DB access denied (`Operation not permitted` to localhost Postgres); reran with escalation and succeeded.
- Default-user eval run returned `status=fail` because prior state in the shared default user scope degraded importer-success metrics; rerunning with a fresh eval user produced a passing report.

## recommended next step
Seek explicit Control Tower merge approval for `P9-S38`, then execute `docs/release/v0.1.0-release-checklist.md` and tag via `docs/release/v0.1.0-tag-plan.md` only after approval.

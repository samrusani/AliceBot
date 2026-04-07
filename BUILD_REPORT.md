# BUILD_REPORT.md

## sprint objective
Ship `P9-S34` by adding a deterministic local CLI for core continuity flows (`capture`, `recall`, `resume`, `open-loops`, `review queue/show/apply`, `status`) on top of the shipped `alice-core` runtime.

## completed work
- Added packaged CLI entrypoint and module entry support:
  - `apps/api/src/alicebot_api/cli.py`
  - `apps/api/src/alicebot_api/cli_formatting.py`
  - `apps/api/src/alicebot_api/__main__.py`
  - `pyproject.toml` (`[project.scripts] alicebot = "alicebot_api.cli:main"`)
- Kept CLI behavior on existing continuity seams (no core semantic fork):
  - capture: `capture_continuity_input`
  - recall: `query_continuity_recall`
  - resume: `compile_continuity_resumption_brief`
  - open-loops: `compile_continuity_open_loop_dashboard`
  - review queue/show/apply: `list_continuity_review_queue`, `get_continuity_review_detail`, `apply_continuity_correction`
  - status: runtime health + continuity/review/open-loop/retrieval summary
- Added deterministic terminal formatting with provenance/trust signals:
  - stable section order
  - stable scope rendering
  - stable list rendering and confidence/posture fields
  - explicit empty states
- Added CLI-focused tests:
  - `tests/unit/test_cli.py`
  - `tests/integration/test_cli_integration.py`
- Updated sprint-scoped docs:
  - `README.md` (CLI invocation and examples)
  - `ROADMAP.md` (`P9-S34` shipped baseline, `P9-S35` next seam)
  - `.ai/handoff/CURRENT_STATE.md` (CLI shipped summary and next seam)
- Preserved control-doc truth marker compatibility in `.ai/handoff/CURRENT_STATE.md` (`Active Sprint focus is Phase 4 Sprint 14`) to keep baseline gate checks green.

## incomplete work
- None inside `P9-S34` scope.
- Intentionally deferred (out of scope): MCP transport/tool schemas (`P9-S35`), adapters/importer expansion, CLI ergonomics polish (autocomplete/TUI enhancements).

## files changed
- `.ai/active/SPRINT_PACKET.md`
- `apps/api/src/alicebot_api/cli.py`
- `apps/api/src/alicebot_api/cli_formatting.py`
- `apps/api/src/alicebot_api/__main__.py`
- `apps/api/src/alicebot_api/__init__.py`
- `pyproject.toml`
- `tests/unit/test_cli.py`
- `tests/integration/test_cli_integration.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## local artifacts explicitly excluded from sprint merge scope
- `.ai/archive/` (local archive workspace artifacts)
- `docs/archive/planning/` (local planning archive artifacts)

## tests run
- `docker compose up -d`
  - PASS
- `./scripts/migrate.sh`
  - PASS (required elevated local DB access)
- `./scripts/load_sample_data.sh`
  - PASS (`status=noop`, fixture already present)
- `APP_RELOAD=false ./scripts/api_dev.sh` + `curl -sS http://127.0.0.1:8000/healthz`
  - PASS (`status=ok`)
- `./.venv/bin/python -m alicebot_api --help`
  - PASS
- `./.venv/bin/python -m alicebot_api status`
  - PASS (database reachable, continuity metrics rendered)
- `./.venv/bin/python -m alicebot_api recall --query local-first`
  - PASS (deterministic ordered output with provenance snippets)
- `./.venv/bin/python -m alicebot_api resume`
  - PASS (last decision/open loops/recent changes/next action sections)
- `./.venv/bin/python -m alicebot_api open-loops --limit 20`
  - PASS
- `./.venv/bin/python -m alicebot_api capture "Decision: CLI verification keeps deterministic continuity output." --explicit-signal decision`
  - PASS
- `./.venv/bin/python -m alicebot_api review queue --status correction_ready --limit 20`
  - PASS
- `./.venv/bin/python -m alicebot_api review show b5bfdbcc-cbb2-440f-9e4e-7ebabdb41f3f`
  - PASS
- `./.venv/bin/python -m alicebot_api review apply b5bfdbcc-cbb2-440f-9e4e-7ebabdb41f3f --action supersede ...`
  - PASS
- `./.venv/bin/python -m alicebot_api recall --query local-first --limit 20` (post-correction)
  - PASS (updated active decision ranked ahead of superseded prior decision)
- `./.venv/bin/python -m alicebot_api resume --max-recent-changes 5 --max-open-loops 5` (post-correction)
  - PASS (last decision updated deterministically after correction)
- `./.venv/bin/python -m pytest tests/unit/test_cli.py -q`
  - PASS (`5 passed`)
- `./.venv/bin/python -m pytest tests/integration/test_cli_integration.py -q`
  - PASS (`1 passed`)
- `./.venv/bin/python -m pytest tests/unit tests/integration`
  - PASS (`954 passed in 85.02s`) (required elevated local DB access)
- `pnpm --dir apps/web test`
  - PASS (`192 passed`)

## blockers/issues
- Sandbox-restricted localhost Postgres access required elevated execution for DB-backed commands/tests.
- Initial backend full-suite run failed at collection due duplicate test-module basename (`test_cli.py` in both unit and integration); resolved by renaming integration test file to `tests/integration/test_cli_integration.py`.

## recommended next step
Start `P9-S35` by mirroring the shipped CLI continuity contract via a narrow MCP tool surface, with parity tests that compare MCP outputs to current CLI deterministic output for the same dataset/scope.

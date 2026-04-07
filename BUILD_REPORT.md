# BUILD_REPORT.md

## sprint objective
Ship `P9-S35` by adding a deterministic local MCP server that exposes the ADR-003 continuity tool surface (`alice_capture`, `alice_recall`, `alice_resume`, `alice_open_loops`, `alice_recent_decisions`, `alice_recent_changes`, `alice_memory_review`, `alice_memory_correct`, `alice_context_pack`) over the shipped `alice-core` runtime without changing `P9-S33` startup flow or `P9-S34` semantics.

## completed work
- Added runnable MCP transport entrypoint:
  - `apps/api/src/alicebot_api/mcp_server.py`
  - stdio JSON-RPC loop with deterministic framing
  - supported methods: `initialize`, `ping`, `tools/list`, `tools/call`
- Added deterministic MCP tool layer:
  - `apps/api/src/alicebot_api/mcp_tools.py`
  - static deterministic tool schemas (ADR-003 tool names in fixed order)
  - direct mapping to shipped continuity seams (capture/recall/resume/open-loops/review/correction)
  - deterministic structured serialization and narrow error envelopes
- Added package script entrypoint:
  - `pyproject.toml`: `alicebot-mcp = "alicebot_api.mcp_server:main"`
- Added MCP unit and integration verification:
  - `tests/unit/test_mcp.py`
  - `tests/integration/test_mcp_server.py`
  - `tests/integration/test_mcp_cli_parity.py`
- Added interoperability evidence for a real MCP client path (stdio JSON-RPC client subprocess):
  - successful `alice_recall`
  - successful `alice_resume`
  - successful `alice_memory_correct` (`supersede`) with deterministic change in later recall/resume result
- Captured required acceptance evidence details:
  - exact MCP startup path used: `./.venv/bin/python -m alicebot_api.mcp_server`
  - exact local client/config used for proof:
    - client type: stdio JSON-RPC MCP client subprocess
    - transport command: `python -m alicebot_api.mcp_server`
    - env: `DATABASE_URL=postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot`
    - env: `ALICEBOT_AUTH_USER_ID=00000000-0000-0000-0000-000000000001`
  - intentionally deferred concern: no hosted/remote auth layer (local process + local user scope only)
- Updated sprint-scoped docs:
  - `README.md` with exact MCP startup path and compatible local client config example
  - `ROADMAP.md` marking `P9-S35` shipped baseline
  - `.ai/handoff/CURRENT_STATE.md` with MCP shipped baseline and `P9-S36` next seam

## incomplete work
- None inside `P9-S35` scope.
- Intentionally deferred (out of scope):
  - OpenClaw adapter implementation (`P9-S36`)
  - importer expansion
  - hosted/remote auth systems
  - MCP ergonomics beyond the initial narrow wedge (pagination/advanced discovery ergonomics)

## files changed
- `.ai/active/SPRINT_PACKET.md`
- `apps/api/src/alicebot_api/mcp_server.py`
- `apps/api/src/alicebot_api/mcp_tools.py`
- `pyproject.toml`
- `tests/unit/test_mcp.py`
- `tests/integration/test_mcp_server.py`
- `tests/integration/test_mcp_cli_parity.py`
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
  - PASS (`status=noop`, fixture already loaded)
- `APP_RELOAD=false ./scripts/api_dev.sh`
  - PASS (server started on `http://127.0.0.1:8000`)
- `curl -sS http://127.0.0.1:8000/healthz`
  - PASS (`status":"ok"`)
- `./.venv/bin/python -m alicebot_api --help`
  - PASS
- `./.venv/bin/python -m alicebot_api.mcp_server --help`
  - PASS
- `./.venv/bin/python -m pytest tests/unit/test_mcp.py -q`
  - PASS (`5 passed`)
- `./.venv/bin/python -m pytest tests/integration/test_mcp_server.py -q`
  - PASS (`1 passed`)
- `./.venv/bin/python -m pytest tests/integration/test_mcp_cli_parity.py -q`
  - PASS (`1 passed`)
- `./.venv/bin/python -m pytest tests/unit/test_mcp.py tests/integration/test_mcp_server.py tests/integration/test_mcp_cli_parity.py -q`
  - PASS (`7 passed`)
- `./.venv/bin/python -m pytest tests/unit tests/integration`
  - PASS (`961 passed in 97.32s`) (required elevated local DB access)
- `pnpm --dir apps/web test`
  - PASS (`57 files, 192 tests`)
- MCP smoke client against new entrypoint (`python -m alicebot_api.mcp_server`)
  - PASS
  - initialize protocol: `2024-11-05`
  - `alice_recall`: `isError=false`, returned count `3`
  - `alice_resume`: `isError=false`, last decision present

## blockers/issues
- Sandbox restrictions required elevated execution for localhost Postgres connections and binding to localhost `:8000`.
- Initial MCP integration test failure due missing `if __name__ == "__main__":` in `mcp_server.py`; fixed by adding module entry invocation.
- Remaining non-sprint workspace artifacts are limited to untracked local archive directories:
  - `.ai/archive/`
  - `docs/archive/planning/`

## recommended next step
Start `P9-S36` by implementing the OpenClaw adapter against the now-stable MCP tool contract, keeping strict parity checks so adapter integration does not reopen continuity transport semantics.

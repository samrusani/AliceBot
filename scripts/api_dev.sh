#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${REPO_ROOT}/.env" ]; then
  set -a
  . "${REPO_ROOT}/.env"
  set +a
fi

PYTHON_BIN="python3"
if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
fi

cd "${REPO_ROOT}"

UVICORN_ARGS=(
  --app-dir "${REPO_ROOT}/apps/api/src"
  --host "${APP_HOST:-127.0.0.1}"
  --port "${APP_PORT:-8000}"
)

if [ "${APP_RELOAD:-true}" = "true" ]; then
  UVICORN_ARGS+=(--reload)
fi

exec "${PYTHON_BIN}" -m uvicorn alicebot_api.main:app "${UVICORN_ARGS[@]}"

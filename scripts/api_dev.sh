#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${REPO_ROOT}/.env" ]; then
  PRESERVE_ENV_KEYS=(
    APP_ENV
    APP_HOST
    APP_PORT
    APP_RELOAD
    DATABASE_URL
    DATABASE_ADMIN_URL
    REDIS_URL
    S3_ENDPOINT_URL
    S3_ACCESS_KEY
    S3_SECRET_KEY
    S3_BUCKET
    HEALTHCHECK_TIMEOUT_SECONDS
    TASK_WORKSPACE_ROOT
    ALICEBOT_AUTH_USER_ID
    PUBLIC_SAMPLE_DATA_PATH
    RESPONSE_RATE_LIMIT_WINDOW_SECONDS
    RESPONSE_RATE_LIMIT_MAX_REQUESTS
    ENTRYPOINT_RATE_LIMIT_BACKEND
  )

  for key in "${PRESERVE_ENV_KEYS[@]}"; do
    if [ "${!key+x}" = "x" ]; then
      export "__PRESERVE_${key}=${!key}"
    fi
  done

  set -a
  . "${REPO_ROOT}/.env"
  set +a

  for key in "${PRESERVE_ENV_KEYS[@]}"; do
    preserve_key="__PRESERVE_${key}"
    if [ "${!preserve_key+x}" = "x" ]; then
      export "${key}=${!preserve_key}"
      unset "${preserve_key}"
    fi
  done
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

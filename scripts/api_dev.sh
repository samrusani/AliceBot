#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

fail() {
  printf '[alice-api-dev] ERROR: %s\n' "$*" >&2
  exit 1
}

PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
if [ ! -x "${PYTHON_BIN}" ]; then
  fail "Missing ${PYTHON_BIN}. Run 'make setup' before starting Alice."
fi

if [ -f "${REPO_ROOT}/.env" ]; then
  "${REPO_ROOT}/scripts/validate_env.sh" "${REPO_ROOT}/.env"
  PRESERVE_ENV_KEYS=(
    APP_ENV
    APP_HOST
    APP_PORT
    APP_RELOAD
    APP_LOG_MODE
    APP_LOG_LEVEL
    APP_LOG_PATH
    APP_LOG_MAX_BYTES
    APP_LOG_BACKUP_COUNT
    APP_ACCESS_LOG
    CALENDAR_SECRET_MANAGER_URL
    CORS_ALLOWED_HEADERS
    CORS_ALLOWED_METHODS
    CORS_ALLOWED_ORIGINS
    CORS_ALLOW_CREDENTIALS
    CORS_PREFLIGHT_MAX_AGE_SECONDS
    DATABASE_URL
    DATABASE_ADMIN_URL
    GMAIL_SECRET_MANAGER_URL
    HEALTHCHECK_TIMEOUT_SECONDS
    ALICE_LEGACY_SURFACES
    ALICE_MCP_LEGACY_TOOLS
    LEGACY_V0_ENABLED_OUTSIDE_DEV
    MODEL_API_KEY
    MODEL_BASE_URL
    MODEL_NAME
    MODEL_PROVIDER
    MODEL_TIMEOUT_SECONDS
    PROVIDER_SECRET_MANAGER_URL
    REDIS_URL
    RETRIEVAL_TRACE_RETENTION_DAYS
    S3_ENDPOINT_URL
    S3_ACCESS_KEY
    S3_SECRET_KEY
    S3_BUCKET
    SECURITY_HEADERS_ENABLED
    SECURITY_HEADERS_HSTS_INCLUDE_SUBDOMAINS
    SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS
    TASK_WORKSPACE_ROOT
    ALICEBOT_AUTH_USER_ID
    PUBLIC_SAMPLE_DATA_PATH
    TRUSTED_PROXY_IPS
    TRUST_PROXY_HEADERS
    WORKSPACE_PROVIDER_CONFIGS_JSON
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

cd "${REPO_ROOT}"

export APP_LOG_MODE="${APP_LOG_MODE:-stdout}"
export APP_ACCESS_LOG="${APP_ACCESS_LOG:-false}"
if [ -n "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="${REPO_ROOT}/apps/api/src:${PYTHONPATH}"
else
  export PYTHONPATH="${REPO_ROOT}/apps/api/src"
fi

exec "${PYTHON_BIN}" -m alicebot_api.local_server

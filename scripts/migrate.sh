#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

fail() {
  printf '[alice-migrate] ERROR: %s\n' "$*" >&2
  exit 1
}

PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
if [ ! -x "${PYTHON_BIN}" ]; then
  fail "Missing ${PYTHON_BIN}. Run 'make setup' before migrating Alice."
fi

if [ -f "${REPO_ROOT}/.env" ]; then
  "${REPO_ROOT}/scripts/validate_env.sh" "${REPO_ROOT}/.env"
  # Fill only variables not already set so explicitly exported values
  # (for example DATABASE_URL) keep precedence over .env defaults.
  set -a
  while IFS= read -r env_line || [ -n "${env_line}" ]; do
    env_line="${env_line#"${env_line%%[![:space:]]*}"}"
    case "${env_line}" in
      ''|\#*) continue ;;
    esac
    env_line="${env_line#export }"
    env_key="${env_line%%=*}"
    case "${env_key}" in
      *[!A-Za-z0-9_]*|'')
        eval "${env_line}"
        continue
        ;;
    esac
    if [ -z "${!env_key+x}" ]; then
      eval "${env_line}"
    fi
  done < "${REPO_ROOT}/.env"
  set +a
fi

if [ -z "${DATABASE_ADMIN_URL:-}" ]; then
  fail "DATABASE_ADMIN_URL is required for migrations; inject the admin DSN into this migration process only."
fi

cd "${REPO_ROOT}"

"${PYTHON_BIN}" -m alembic -c "${REPO_ROOT}/apps/api/alembic.ini" upgrade "${1:-head}"

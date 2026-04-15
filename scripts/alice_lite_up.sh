#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${REPO_ROOT}/.env" ]; then
  set -a
  . "${REPO_ROOT}/.env"
  set +a
fi

if [ -f "${REPO_ROOT}/.env.lite" ]; then
  set -a
  . "${REPO_ROOT}/.env.lite"
  set +a
fi

PYTHON_BIN="python3"
if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
fi

export APP_RELOAD="${APP_RELOAD:-false}"
export ENTRYPOINT_RATE_LIMIT_BACKEND="${ENTRYPOINT_RATE_LIMIT_BACKEND:-memory}"

cd "${REPO_ROOT}"

docker compose -f "${REPO_ROOT}/docker-compose.lite.yml" up -d

"${PYTHON_BIN}" -c '
import os
import sys
import time

import psycopg

database_url = os.getenv(
    "DATABASE_ADMIN_URL",
    "postgresql://alicebot_admin:alicebot_admin@localhost:5432/alicebot",
)
deadline = time.time() + 60

while time.time() < deadline:
    try:
        with psycopg.connect(database_url, connect_timeout=1) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", ("alicebot_app",))
                if cur.fetchone() == (1,):
                    sys.exit(0)
    except psycopg.Error:
        pass
    time.sleep(1)

raise SystemExit("Timed out waiting for Alice Lite Postgres readiness and alicebot_app bootstrap")
'

"${REPO_ROOT}/scripts/migrate.sh"
"${REPO_ROOT}/scripts/load_sample_data.sh"

echo "Alice Lite is ready on http://${APP_HOST:-127.0.0.1}:${APP_PORT:-8000}"
echo "Next terminal:"
echo "  ${PYTHON_BIN} ${REPO_ROOT}/scripts/bootstrap_alice_lite_workspace.py"

exec "${REPO_ROOT}/scripts/api_dev.sh"

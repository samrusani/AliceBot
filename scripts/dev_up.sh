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

docker compose up -d

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

raise SystemExit("Timed out waiting for Postgres readiness and alicebot_app bootstrap")
'

"${PYTHON_BIN}" -m alembic -c "${REPO_ROOT}/apps/api/alembic.ini" upgrade head

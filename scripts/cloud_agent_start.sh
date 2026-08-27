#!/usr/bin/env bash
# Per-boot Cloud Agent start: Docker daemon, compose, migrate, seed, then API+web.
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

ensure_dockerd() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi
  if ! pgrep -x dockerd >/dev/null 2>&1; then
    sudo dockerd >/tmp/dockerd.log 2>&1 &
  fi
  for _ in $(seq 1 60); do
    if docker info >/dev/null 2>&1; then
      sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
      return 0
    fi
    if sudo docker info >/dev/null 2>&1; then
      sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
      if docker info >/dev/null 2>&1; then
        return 0
      fi
    fi
    sleep 1
  done
  echo "[cloud-agent-start] ERROR: dockerd failed to become ready" >&2
  tail -50 /tmp/dockerd.log >&2 || true
  exit 1
}

if [ ! -x "${REPO_ROOT}/.venv/bin/python" ]; then
  echo "[cloud-agent-start] ERROR: missing .venv. Run install first." >&2
  exit 1
fi

ensure_dockerd

if [ -f "${REPO_ROOT}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "${REPO_ROOT}/.env"
  set +a
fi

"${REPO_ROOT}/scripts/dev_up.sh"
"${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/scripts/seed_local_user.py"

echo "[cloud-agent-start] starting API (8000) and web (3000)"
APP_RELOAD=false "${REPO_ROOT}/scripts/api_dev.sh" &
api_pid=$!
pnpm --dir apps/web dev --hostname 127.0.0.1 --port 3000 &
web_pid=$!
trap 'kill "$api_pid" "$web_pid" 2>/dev/null || true' INT TERM EXIT
wait "$api_pid" "$web_pid"

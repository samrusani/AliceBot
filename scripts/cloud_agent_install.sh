#!/usr/bin/env bash
# Idempotent Cloud Agent install for AliceMemory (full Postgres stack).
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

export DEBIAN_FRONTEND=noninteractive

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

# python3-venv is required for make setup on Debian/Ubuntu base images.
if ! python3 -c 'import ensurepip' >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3.12-venv python3-pip
fi

# Nested Docker for compose-backed Postgres/Redis/MinIO.
if ! need_cmd docker; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq ca-certificates curl fuse-overlayfs iptables
  curl -fsSL https://get.docker.com | sudo sh
fi

if [ ! -f /etc/docker/daemon.json ]; then
  sudo mkdir -p /etc/docker
  cat <<'EOF' | sudo tee /etc/docker/daemon.json >/dev/null
{
  "storage-driver": "fuse-overlayfs",
  "iptables": false,
  "ip6tables": false
}
EOF
fi

sudo update-alternatives --set iptables /usr/sbin/iptables-legacy 2>/dev/null || true
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy 2>/dev/null || true

make setup

echo "[cloud-agent-install] complete"

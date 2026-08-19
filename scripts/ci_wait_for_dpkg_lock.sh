#!/usr/bin/env bash
# Fresh ubuntu-24.04 GitHub runners still run unattended-upgrades, which
# holds /var/lib/dpkg/lock-frontend. Timed apt-get in ci_apt_get.sh
# calls this first. Linux CI only.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  printf '%s\n' "ci_wait_for_dpkg_lock: not Linux, nothing to do"
  exit 0
fi

if ! command -v sudo >/dev/null 2>&1; then
  printf '%s\n' "ci_wait_for_dpkg_lock: sudo is required on Linux CI" >&2
  exit 1
fi

sudo systemctl mask --now unattended-upgrades.service 2>/dev/null || true
sudo systemctl stop unattended-upgrades.service 2>/dev/null || true
sudo systemctl stop apt-daily.service apt-daily-upgrade.service 2>/dev/null || true
sudo systemctl stop apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
sudo killall -9 unattended-upgr unattended-upgrades apt-get apt 2>/dev/null || true

lock=/var/lib/dpkg/lock-frontend
for _ in $(seq 1 45); do
  if ! sudo fuser "${lock}" >/dev/null 2>&1; then
    exit 0
  fi
  printf '%s\n' "ci_wait_for_dpkg_lock: waiting for ${lock}"
  sleep 2
done

printf '%s\n' "ci_wait_for_dpkg_lock: ${lock} still held after 90s" >&2
exit 1

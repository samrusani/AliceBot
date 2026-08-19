#!/usr/bin/env bash
# Timed, retried apt-get for GitHub-hosted Linux runners.
# apt-get update/install has sat until the job timeout on ubuntu-24.04
# even after the dpkg lock was free. Bound each attempt and kill the
# process group so a hung mirror cannot eat the job budget.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  printf '%s\n' "ci_apt_get: not Linux" >&2
  exit 1
fi

if [[ "$#" -lt 1 ]]; then
  printf '%s\n' "usage: ci_apt_get.sh <apt-package>..." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/ci_wait_for_dpkg_lock.sh
bash "${script_dir}/ci_wait_for_dpkg_lock.sh"

rewrite_apt_mirrors() {
  local src
  for src in /etc/apt/sources.list /etc/apt/sources.list.d/ubuntu.sources; do
    if [[ -f "${src}" ]] && grep -q 'archive.ubuntu.com' "${src}"; then
      sudo sed -i.bak \
        -e 's|http://archive.ubuntu.com/ubuntu|http://azure.archive.ubuntu.com/ubuntu|g' \
        -e 's|http://security.ubuntu.com/ubuntu|http://azure.archive.ubuntu.com/ubuntu|g' \
        "${src}" || true
    fi
  done
}

run_timed() {
  local seconds="$1"
  shift
  sudo -E env DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a \
    setsid --wait timeout --signal=TERM --kill-after=15s "${seconds}s" "$@"
}

clear_orphans() {
  sudo killall -9 apt-get apt 2>/dev/null || true
  bash "${script_dir}/ci_wait_for_dpkg_lock.sh"
}

apt_opts=(
  -o Acquire::Retries=3
  -o Acquire::http::Timeout=15
  -o Acquire::https::Timeout=15
  -o Acquire::ForceIPv4=true
  -o Dpkg::Use-Pty=0
)

rewrite_apt_mirrors

for attempt in 1 2 3; do
  if run_timed 120 apt-get "${apt_opts[@]}" update \
    && run_timed 180 apt-get "${apt_opts[@]}" install --yes --no-install-recommends "$@"; then
    exit 0
  fi
  printf '%s\n' "ci_apt_get: attempt ${attempt} failed" >&2
  clear_orphans
done

printf '%s\n' "ci_apt_get: all attempts failed" >&2
exit 1

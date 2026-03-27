#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shlex
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
TARGET_SCRIPT = ROOT_DIR / "scripts" / "run_phase3_acceptance.py"


def _resolve_python_executable() -> str:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def main() -> int:
    command = [_resolve_python_executable(), str(TARGET_SCRIPT), *sys.argv[1:]]
    print("Phase 4 acceptance entrypoint -> scripts/run_phase3_acceptance.py", flush=True)
    print(shlex.join(command), flush=True)
    completed = subprocess.run(
        command,
        cwd=ROOT_DIR,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

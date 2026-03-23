#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
INDUCED_FAILURE_ENV = "MVP_ACCEPTANCE_INDUCED_FAILURE_SCENARIO"
ACCEPTANCE_SCENARIOS = (
    "response_memory",
    "capture_resumption",
    "approval_execution",
    "magnesium_reorder",
)
ACCEPTANCE_TEST_NODE_IDS = (
    "tests/integration/test_mvp_acceptance_suite.py::test_acceptance_response_path_uses_admitted_memory_and_preference_correction",
    "tests/integration/test_mvp_acceptance_suite.py::test_acceptance_explicit_signal_capture_flows_into_resumption_brief",
    "tests/integration/test_mvp_acceptance_suite.py::test_acceptance_approval_lifecycle_resolution_execution_and_trace_availability",
    "tests/integration/test_mvp_acceptance_suite.py::test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence",
)


def _resolve_python_executable() -> str:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _build_pytest_command(python_executable: str) -> list[str]:
    return [python_executable, "-m", "pytest", "-q", *ACCEPTANCE_TEST_NODE_IDS]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the bounded MVP acceptance evidence suite.",
    )
    parser.add_argument(
        "--induce-failure",
        choices=ACCEPTANCE_SCENARIOS,
        default=None,
        help="Intentionally fail one acceptance scenario to validate deterministic failure signaling.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    python_executable = _resolve_python_executable()
    command = _build_pytest_command(python_executable)

    env = os.environ.copy()
    if args.induce_failure is None:
        env.pop(INDUCED_FAILURE_ENV, None)
    else:
        env[INDUCED_FAILURE_ENV] = args.induce_failure

    print("MVP acceptance test subset:")
    for node_id in ACCEPTANCE_TEST_NODE_IDS:
        print(f" - {node_id}")
    if args.induce_failure is not None:
        print(
            "Induced failure enabled: "
            f"{INDUCED_FAILURE_ENV}={args.induce_failure}"
        )
    print("Running command:")
    print(shlex.join(command))

    completed = subprocess.run(
        command,
        cwd=ROOT_DIR,
        env=env,
        check=False,
    )

    if completed.returncode == 0:
        print("MVP acceptance suite result: PASS")
    else:
        print(f"MVP acceptance suite result: FAIL (exit code {completed.returncode})")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

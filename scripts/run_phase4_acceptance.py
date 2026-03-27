#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Literal


ROOT_DIR = Path(__file__).resolve().parents[1]

INDUCED_FAILURE_ENV = "MVP_ACCEPTANCE_INDUCED_FAILURE_SCENARIO"
ScenarioId = Literal["response_memory", "capture_resumption", "approval_execution", "magnesium_reorder"]


@dataclass(frozen=True, slots=True)
class AcceptanceScenario:
    scenario: ScenarioId
    node_id: str
    evidence: str


ACCEPTANCE_SCENARIOS: tuple[AcceptanceScenario, ...] = (
    AcceptanceScenario(
        scenario="response_memory",
        node_id=(
            "tests/integration/test_mvp_acceptance_suite.py::"
            "test_acceptance_response_path_uses_admitted_memory_and_preference_correction"
        ),
        evidence="admitted memory and preference correction path remains deterministic",
    ),
    AcceptanceScenario(
        scenario="capture_resumption",
        node_id=(
            "tests/integration/test_mvp_acceptance_suite.py::"
            "test_acceptance_explicit_signal_capture_flows_into_resumption_brief"
        ),
        evidence="explicit signal capture persists and flows into bounded resumption brief",
    ),
    AcceptanceScenario(
        scenario="approval_execution",
        node_id=(
            "tests/integration/test_mvp_acceptance_suite.py::"
            "test_acceptance_approval_lifecycle_resolution_execution_and_trace_availability"
        ),
        evidence="approval resolution drives execution and trace evidence deterministically",
    ),
    AcceptanceScenario(
        scenario="magnesium_reorder",
        node_id=(
            "tests/integration/test_mvp_acceptance_suite.py::"
            "test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence"
        ),
        evidence=(
            "canonical MVP ship gate (request -> approval -> execution -> memory write-back) "
            "for magnesium reorder"
        ),
    ),
)

ACCEPTANCE_SCENARIO_IDS: tuple[ScenarioId, ...] = tuple(
    scenario.scenario for scenario in ACCEPTANCE_SCENARIOS
)
ACCEPTANCE_TEST_NODE_IDS: tuple[str, ...] = tuple(
    scenario.node_id for scenario in ACCEPTANCE_SCENARIOS
)


def _resolve_python_executable() -> str:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _build_pytest_command(python_executable: str) -> list[str]:
    return [python_executable, "-m", "pytest", "-q", *ACCEPTANCE_TEST_NODE_IDS]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic Phase 4 acceptance evidence checks, including canonical "
            "magnesium reorder ship-gate coverage."
        ),
    )
    parser.add_argument(
        "--induce-failure",
        choices=ACCEPTANCE_SCENARIO_IDS,
        default=None,
        help="Intentionally fail one acceptance scenario to validate deterministic no-go signaling.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    command = _build_pytest_command(_resolve_python_executable())

    env = os.environ.copy()
    if args.induce_failure is None:
        env.pop(INDUCED_FAILURE_ENV, None)
    else:
        env[INDUCED_FAILURE_ENV] = args.induce_failure

    print("Phase 4 acceptance scenario evidence mapping:")
    for scenario in ACCEPTANCE_SCENARIOS:
        print(f" - {scenario.scenario}: {scenario.node_id}")
        print(f"   evidence: {scenario.evidence}")
    if args.induce_failure is not None:
        print(f"Induced failure enabled: {INDUCED_FAILURE_ENV}={args.induce_failure}")
    print("Running command:")
    print(shlex.join(command), flush=True)

    completed = subprocess.run(
        command,
        cwd=ROOT_DIR,
        env=env,
        check=False,
    )

    if completed.returncode == 0:
        print("Phase 4 acceptance suite result: PASS")
    else:
        print(f"Phase 4 acceptance suite result: FAIL (exit code {completed.returncode})")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

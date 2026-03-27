#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Callable, Literal


ROOT_DIR = Path(__file__).resolve().parents[1]

INDUCED_FAILURE_EXIT_CODE = 97

GateStatus = Literal["PASS", "FAIL"]

GATE_PHASE4_ACCEPTANCE = "phase4_acceptance"
GATE_MAGNESIUM_SHIP_GATE = "canonical_magnesium_ship_gate"
GATE_PHASE3_COMPAT = "phase3_readiness_compat"
GATE_IDS: tuple[str, ...] = (
    GATE_PHASE4_ACCEPTANCE,
    GATE_MAGNESIUM_SHIP_GATE,
    GATE_PHASE3_COMPAT,
)

MAGNESIUM_NODE_ID = (
    "tests/integration/test_mvp_acceptance_suite.py::"
    "test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence"
)


@dataclass(frozen=True, slots=True)
class ReadinessGate:
    gate: str
    description: str
    command: tuple[str, ...]
    coverage: str


@dataclass(frozen=True, slots=True)
class ReadinessGateResult:
    gate: str
    status: GateStatus
    exit_code: int
    duration_seconds: float
    command: tuple[str, ...]
    coverage: str
    induced_failure: bool


CommandExecutor = Callable[[tuple[str, ...], Path], int]


def _resolve_python_executable() -> str:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def build_readiness_gate_steps(*, python_executable: str | None = None) -> list[ReadinessGate]:
    resolved_python = python_executable or _resolve_python_executable()
    return [
        ReadinessGate(
            gate=GATE_PHASE4_ACCEPTANCE,
            description="Run canonical Phase 4 acceptance command contract.",
            command=(resolved_python, "scripts/run_phase4_acceptance.py"),
            coverage="Phase 4 acceptance evidence chain ownership",
        ),
        ReadinessGate(
            gate=GATE_MAGNESIUM_SHIP_GATE,
            description="Run canonical magnesium reorder ship-gate evidence check directly.",
            command=(resolved_python, "-m", "pytest", "-q", MAGNESIUM_NODE_ID),
            coverage="request -> approval -> execution -> memory write-back canonical MVP scenario",
        ),
        ReadinessGate(
            gate=GATE_PHASE3_COMPAT,
            description="Run Phase 3 readiness command for compatibility posture.",
            command=(resolved_python, "scripts/run_phase3_readiness_gates.py"),
            coverage="Phase 3 readiness compatibility remains PASS",
        ),
    ]


def _execute_command(command: tuple[str, ...], cwd: Path) -> int:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
    )
    return completed.returncode


def _build_induced_failure_command(*, gate: str, python_executable: str) -> tuple[str, ...]:
    return (
        python_executable,
        "-c",
        (
            "import sys; "
            f"print('Induced phase4 readiness failure for gate: {gate}'); "
            f"sys.exit({INDUCED_FAILURE_EXIT_CODE})"
        ),
    )


def run_readiness_gates(
    *,
    induce_gate: str | None = None,
    execute_command: CommandExecutor = _execute_command,
) -> list[ReadinessGateResult]:
    results: list[ReadinessGateResult] = []
    gate_steps = build_readiness_gate_steps()
    python_executable = _resolve_python_executable()

    for gate_step in gate_steps:
        induced_failure = induce_gate == gate_step.gate
        gate_command = (
            _build_induced_failure_command(gate=gate_step.gate, python_executable=python_executable)
            if induced_failure
            else gate_step.command
        )

        started = time.perf_counter()
        exit_code = execute_command(gate_command, ROOT_DIR)
        duration_seconds = time.perf_counter() - started
        status: GateStatus = "PASS" if exit_code == 0 else "FAIL"
        results.append(
            ReadinessGateResult(
                gate=gate_step.gate,
                status=status,
                exit_code=exit_code,
                duration_seconds=duration_seconds,
                command=gate_command,
                coverage=gate_step.coverage,
                induced_failure=induced_failure,
            )
        )

    return results


def exit_code_for_gate_results(gate_results: list[ReadinessGateResult]) -> int:
    return 0 if all(result.status == "PASS" for result in gate_results) else 1


def _print_gate_results(gate_results: list[ReadinessGateResult]) -> None:
    print("Phase 4 readiness gate results:")
    for result in gate_results:
        print(f" - {result.gate}: {result.status}")
        print(f"   command: {shlex.join(result.command)}")
        print(f"   measured: exit_code={result.exit_code}")
        print("   threshold: exit_code == 0")
        print(f"   duration_seconds: {result.duration_seconds:.3f}")
        print(f"   coverage: {result.coverage}")
        if result.induced_failure:
            print("   induced_failure: true")

    failing_gates = [result.gate for result in gate_results if result.status != "PASS"]
    if failing_gates:
        print(f"Failing gates: {', '.join(failing_gates)}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic Phase 4 readiness gates for canonical acceptance ownership, "
            "magnesium ship-gate evidence, and Phase 3 compatibility."
        ),
    )
    parser.add_argument(
        "--induce-gate",
        choices=GATE_IDS,
        default=None,
        help="Force one readiness gate to fail deterministically for no-go contract validation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    gate_results = run_readiness_gates(induce_gate=args.induce_gate)
    _print_gate_results(gate_results)

    exit_code = exit_code_for_gate_results(gate_results)
    if exit_code == 0:
        print("Phase 4 readiness gate result: PASS")
    else:
        print("Phase 4 readiness gate result: NO_GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

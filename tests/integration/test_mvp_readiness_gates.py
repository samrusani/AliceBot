from __future__ import annotations

import contextlib

import scripts.run_mvp_readiness_gates as readiness_gates


def test_latency_p95_calculation_is_deterministic() -> None:
    durations = [0.42, 0.31, 0.55, 0.29, 0.48, 0.61, 0.50, 0.33, 0.45, 0.58]

    p95 = readiness_gates.calculate_p95_seconds(durations)

    assert p95 == 0.61


def test_cache_reuse_ratio_requires_cached_telemetry_for_all_samples() -> None:
    ratio = readiness_gates.calculate_cache_reuse_ratio(
        [
            {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
                "cached_input_tokens": 80,
            },
            {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
            },
        ]
    )

    assert ratio is None


def test_cache_reuse_gate_enforces_threshold_math() -> None:
    gate = readiness_gates._evaluate_cache_reuse_gate(
        [
            {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
                "cached_input_tokens": 50,
            },
            {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
                "cached_input_tokens": 50,
            },
        ]
    )

    assert gate.gate == readiness_gates.CACHE_GATE_NAME
    assert gate.status == "FAIL"
    assert gate.measured == "cache_reuse_ratio=0.500000"
    assert gate.threshold == "cache_reuse_ratio >= 0.70"


def test_memory_quality_gate_posture_alignment() -> None:
    pass_gate = readiness_gates._evaluate_memory_quality_gate(
        {
            "label_row_counts_by_value": {"correct": 8, "incorrect": 2},
            "unlabeled_memory_count": 0,
        }
    )
    fail_gate = readiness_gates._evaluate_memory_quality_gate(
        {
            "label_row_counts_by_value": {"correct": 6, "incorrect": 4},
            "unlabeled_memory_count": 0,
        }
    )
    blocked_gate = readiness_gates._evaluate_memory_quality_gate(
        {
            "label_row_counts_by_value": {"correct": 5, "incorrect": 1},
            "unlabeled_memory_count": 0,
        }
    )

    assert pass_gate.status == "PASS"
    assert "posture=on_track" in pass_gate.measured
    assert fail_gate.status == "FAIL"
    assert "posture=needs_review" in fail_gate.measured
    assert blocked_gate.status == "BLOCKED"
    assert "posture=insufficient_evidence" in blocked_gate.measured


def test_exit_code_is_non_zero_when_any_gate_is_failed_or_blocked() -> None:
    pass_only = [
        readiness_gates.GateResult(
            gate="acceptance_suite",
            status="PASS",
            measured="exit_code=0",
            threshold="exit_code == 0",
            detail="ok",
        )
    ]
    with_failure = [
        *pass_only,
        readiness_gates.GateResult(
            gate="latency_p95",
            status="FAIL",
            measured="p95_seconds=5.200000",
            threshold="p95_seconds < 5.0",
            detail="probe_count=8",
        ),
    ]
    with_blocked = [
        *pass_only,
        readiness_gates.GateResult(
            gate="cache_reuse",
            status="BLOCKED",
            measured="cache_reuse_ratio=unavailable",
            threshold="cache_reuse_ratio >= 0.70",
            detail="missing telemetry",
        ),
    ]

    assert readiness_gates.exit_code_for_gate_results(pass_only) == 0
    assert readiness_gates.exit_code_for_gate_results(with_failure) == 1
    assert readiness_gates.exit_code_for_gate_results(with_blocked) == 1


def test_run_readiness_gates_returns_blocked_when_probe_setup_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        readiness_gates,
        "_run_acceptance_suite_gate",
        lambda *, induce_failure: readiness_gates.GateResult(
            gate=readiness_gates.ACCEPTANCE_GATE_NAME,
            status="PASS",
            measured="exit_code=0",
            threshold="exit_code == 0",
            detail=f"induce_failure={induce_failure}",
        ),
    )

    @contextlib.contextmanager
    def broken_database_context():
        raise RuntimeError("probe setup unavailable")
        yield

    monkeypatch.setattr(readiness_gates, "_temporary_database_urls", broken_database_context)

    gates = readiness_gates.run_readiness_gates()

    assert [gate.gate for gate in gates] == [
        readiness_gates.ACCEPTANCE_GATE_NAME,
        readiness_gates.LATENCY_GATE_NAME,
        readiness_gates.CACHE_GATE_NAME,
        readiness_gates.MEMORY_GATE_NAME,
    ]
    assert gates[0].status == "PASS"
    assert gates[1].status == "BLOCKED"
    assert gates[2].status == "BLOCKED"
    assert gates[3].status == "BLOCKED"
    assert "probe setup unavailable" in gates[1].detail

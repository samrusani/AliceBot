from __future__ import annotations

import contextlib
from types import SimpleNamespace
from uuid import UUID, uuid4

import scripts.run_mvp_readiness_gates as mvp_readiness_alias
import scripts.run_phase2_readiness_gates as readiness_gates


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
            "label_row_counts_by_value": {"correct": 17, "incorrect": 3},
            "unlabeled_memory_count": 0,
        }
    )
    fail_gate = readiness_gates._evaluate_memory_quality_gate(
        {
            "label_row_counts_by_value": {"correct": 15, "incorrect": 5},
            "unlabeled_memory_count": 0,
        }
    )
    blocked_gate = readiness_gates._evaluate_memory_quality_gate(
        {
            "label_row_counts_by_value": {"correct": 9, "incorrect": 1},
            "unlabeled_memory_count": 0,
        }
    )

    assert pass_gate.status == "PASS"
    assert "posture=on_track" in pass_gate.measured
    assert fail_gate.status == "FAIL"
    assert "posture=needs_review" in fail_gate.measured
    assert blocked_gate.status == "BLOCKED"
    assert "posture=insufficient_evidence" in blocked_gate.measured
    assert pass_gate.threshold == "precision > 0.80 and adjudicated_sample >= 20"


def test_memory_quality_gate_rejects_precision_boundary_at_point_80() -> None:
    boundary_gate = readiness_gates._evaluate_memory_quality_gate(
        {
            "label_row_counts_by_value": {"correct": 16, "incorrect": 4},
            "unlabeled_memory_count": 0,
        }
    )

    assert boundary_gate.status == "FAIL"
    assert "precision=0.800000" in boundary_gate.measured
    assert "posture=needs_review" in boundary_gate.measured


def test_memory_quality_gate_blocks_when_sample_is_below_20_even_with_perfect_precision() -> None:
    blocked_gate = readiness_gates._evaluate_memory_quality_gate(
        {
            "label_row_counts_by_value": {"correct": 19, "incorrect": 0},
            "unlabeled_memory_count": 0,
        }
    )

    assert blocked_gate.status == "BLOCKED"
    assert "adjudicated_sample=19" in blocked_gate.measured
    assert "posture=insufficient_evidence" in blocked_gate.measured


def test_memory_capture_message_profiles_are_deterministic() -> None:
    on_track_messages = readiness_gates._build_memory_capture_messages(profile="on_track")
    needs_review_messages = readiness_gates._build_memory_capture_messages(profile="needs_review")
    insufficient_messages = readiness_gates._build_memory_capture_messages(profile="insufficient_evidence")

    assert len(on_track_messages) == 20
    assert len(set(on_track_messages)) == 20

    assert len(needs_review_messages) == 20
    assert len(set(needs_review_messages)) == 16
    assert needs_review_messages[-4:] == needs_review_messages[:4]

    assert len(insufficient_messages) == 10
    assert len(set(insufficient_messages)) == 9
    assert insufficient_messages[-1] == insufficient_messages[0]


def test_capture_adjudication_maps_admission_decisions_to_memory_review_labels() -> None:
    add_memory_id = str(uuid4())
    noop_memory_id = str(uuid4())

    adjudications = readiness_gates._adjudicate_capture_admissions(
        [
            {"decision": "ADD", "memory": {"id": add_memory_id}},
            {"decision": "NOOP", "memory": {"id": noop_memory_id}},
        ]
    )

    assert adjudications[0].memory_id == UUID(add_memory_id)
    assert adjudications[0].label == "correct"
    assert adjudications[1].label == "incorrect"


def test_run_readiness_gates_routes_memory_profiles_through_capture_derived_path(monkeypatch) -> None:
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
    def fake_database_context():
        yield {"admin": "postgresql://admin/db", "app": "postgresql://app/db"}

    monkeypatch.setattr(readiness_gates, "_temporary_database_urls", fake_database_context)
    monkeypatch.setattr(readiness_gates, "make_alembic_config", lambda _: object())
    monkeypatch.setattr(readiness_gates.command, "upgrade", lambda *_args: None)
    monkeypatch.setattr(
        readiness_gates,
        "_seed_probe_state",
        lambda _database_url: {
            "user_id": uuid4(),
            "thread_id": uuid4(),
            "session_id": uuid4(),
            "source_event_id": uuid4(),
        },
    )
    monkeypatch.setattr(
        readiness_gates,
        "_run_response_probes",
        lambda **_kwargs: readiness_gates.ProbeRun(
            durations_seconds=[0.1] * readiness_gates.PROBE_CALL_COUNT,
            usages=[
                {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "total_tokens": 120,
                    "cached_input_tokens": 80,
                }
                for _ in range(readiness_gates.PROBE_CALL_COUNT)
            ],
        ),
    )

    captured_profiles: list[str] = []

    def fake_capture_and_adjudicate(**kwargs) -> None:  # noqa: ANN003
        captured_profiles.append(kwargs["profile"])

    monkeypatch.setattr(
        readiness_gates,
        "_capture_and_adjudicate_memory_quality_sample",
        fake_capture_and_adjudicate,
    )

    def fake_fetch_memory_summary(*, settings, user_id):  # noqa: ANN001
        del settings
        del user_id
        profile = captured_profiles[-1]
        if profile == "on_track":
            return {
                "label_row_counts_by_value": {"correct": 20, "incorrect": 0},
                "unlabeled_memory_count": 0,
            }
        if profile == "needs_review":
            return {
                "label_row_counts_by_value": {"correct": 16, "incorrect": 4},
                "unlabeled_memory_count": 0,
            }
        return {
            "label_row_counts_by_value": {"correct": 9, "incorrect": 1},
            "unlabeled_memory_count": 0,
        }

    monkeypatch.setattr(readiness_gates, "_fetch_memory_summary", fake_fetch_memory_summary)

    scenarios = [
        (None, "on_track", "PASS", "posture=on_track"),
        ("memory_needs_review", "needs_review", "FAIL", "posture=needs_review"),
        ("memory_insufficient", "insufficient_evidence", "BLOCKED", "posture=insufficient_evidence"),
    ]
    for induced_gate, expected_profile, expected_status, expected_posture in scenarios:
        gates = readiness_gates.run_readiness_gates(induce_gate=induced_gate)
        memory_gate = next(gate for gate in gates if gate.gate == readiness_gates.MEMORY_GATE_NAME)
        assert captured_profiles[-1] == expected_profile
        assert memory_gate.status == expected_status
        assert expected_posture in memory_gate.measured


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


def test_mvp_readiness_alias_forwards_to_phase2_entrypoint(monkeypatch, capsys) -> None:
    forwarded_args = ["--induce-gate", "cache_fail"]
    captured: dict[str, object] = {}

    def fake_run(command, *, cwd, check):  # noqa: ANN001
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check
        return SimpleNamespace(returncode=19)

    monkeypatch.setattr(mvp_readiness_alias, "_resolve_python_executable", lambda: "/usr/bin/python3")
    monkeypatch.setattr(
        mvp_readiness_alias.sys,
        "argv",
        ["scripts/run_mvp_readiness_gates.py", *forwarded_args],
    )
    monkeypatch.setattr(mvp_readiness_alias.subprocess, "run", fake_run)

    exit_code = mvp_readiness_alias.main()
    output = capsys.readouterr().out

    assert exit_code == 19
    assert (
        captured["command"]
        == ["/usr/bin/python3", str(mvp_readiness_alias.TARGET_SCRIPT), *forwarded_args]
    )
    assert captured["cwd"] == mvp_readiness_alias.ROOT_DIR
    assert captured["check"] is False
    assert "MVP readiness compatibility alias -> scripts/run_phase2_readiness_gates.py" in output

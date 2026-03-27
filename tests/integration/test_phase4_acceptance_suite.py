from __future__ import annotations

from types import SimpleNamespace

import scripts.run_phase4_acceptance as phase4_acceptance


def test_acceptance_scenario_mapping_is_deterministic_and_contains_magnesium() -> None:
    assert [scenario.scenario for scenario in phase4_acceptance.ACCEPTANCE_SCENARIOS] == [
        "response_memory",
        "capture_resumption",
        "approval_execution",
        "magnesium_reorder",
    ]
    assert phase4_acceptance.ACCEPTANCE_TEST_NODE_IDS == (
        "tests/integration/test_mvp_acceptance_suite.py::"
        "test_acceptance_response_path_uses_admitted_memory_and_preference_correction",
        "tests/integration/test_mvp_acceptance_suite.py::"
        "test_acceptance_explicit_signal_capture_flows_into_resumption_brief",
        "tests/integration/test_mvp_acceptance_suite.py::"
        "test_acceptance_approval_lifecycle_resolution_execution_and_trace_availability",
        "tests/integration/test_mvp_acceptance_suite.py::"
        "test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence",
    )


def test_phase4_acceptance_induced_failure_sets_mvp_compat_env(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, *, cwd, env, check):  # noqa: ANN001
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        captured["check"] = check
        return SimpleNamespace(returncode=13)

    monkeypatch.setattr(phase4_acceptance, "_resolve_python_executable", lambda: "/usr/bin/python3")
    monkeypatch.setattr(
        phase4_acceptance.sys,
        "argv",
        ["scripts/run_phase4_acceptance.py", "--induce-failure", "magnesium_reorder"],
    )
    monkeypatch.setattr(phase4_acceptance.subprocess, "run", fake_run)

    exit_code = phase4_acceptance.main()
    output = capsys.readouterr().out

    assert exit_code == 13
    assert captured["command"] == [
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        *phase4_acceptance.ACCEPTANCE_TEST_NODE_IDS,
    ]
    assert captured["cwd"] == phase4_acceptance.ROOT_DIR
    assert captured["check"] is False
    assert (
        captured["env"][phase4_acceptance.INDUCED_FAILURE_ENV]  # type: ignore[index]
        == "magnesium_reorder"
    )
    assert "magnesium_reorder" in output
    assert "canonical MVP ship gate" in output

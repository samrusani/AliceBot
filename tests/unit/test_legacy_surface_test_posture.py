from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_integration_runners_enable_legacy_surfaces_without_changing_unit_posture() -> None:
    workflow = _read(".github/workflows/tests.yml")
    integration_job = workflow.split("  python-integration:", 1)[1].split(
        "\n  web:", 1
    )[0]
    unit_job = workflow.split("  python-unit:", 1)[1].split(
        "\n  python-quality:", 1
    )[0]
    make_test_python = _read("Makefile").split("test-python:", 1)[1].split(
        "\n\ntest-web:", 1
    )[0]

    assert (
        "run: ALICE_LEGACY_SURFACES=1 ./.venv/bin/python -m pytest "
        "tests/integration -q -p no:cacheprovider"
    ) in integration_job
    assert (
        "ALICE_LEGACY_SURFACES=1 $(PYTHON) -m pytest tests/integration -q"
    ) in make_test_python

    assert "ALICE_LEGACY_SURFACES" not in unit_job
    unit_command = next(
        line
        for line in make_test_python.splitlines()
        if "-m pytest tests/unit" in line
    )
    assert "ALICE_LEGACY_SURFACES" not in unit_command

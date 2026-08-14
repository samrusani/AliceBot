from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from alicebot_api import local_server
from alicebot_api.config import Settings


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_local_server(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def fake_run(app: str, **kwargs: Any) -> None:
        captured["app"] = app
        captured.update(kwargs)

    monkeypatch.setattr(local_server, "get_settings", lambda: Settings(app_env="test"))
    monkeypatch.setattr(local_server.uvicorn, "run", fake_run)
    assert local_server.main() == 0
    return captured


def test_local_server_does_not_reload_unless_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_RELOAD", raising=False)

    captured = _run_local_server(monkeypatch)

    assert captured["app"] == "alicebot_api.main:app"
    assert captured["reload"] is False


@pytest.mark.parametrize("raw_value", ("false", "0", "no", "off", "", "  "))
def test_local_server_reload_stays_off_for_negative_values(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str,
) -> None:
    monkeypatch.setenv("APP_RELOAD", raw_value)

    assert _run_local_server(monkeypatch)["reload"] is False


@pytest.mark.parametrize("raw_value", ("true", "1", "yes", "on", "TRUE"))
def test_local_server_reload_can_be_opted_into(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str,
) -> None:
    monkeypatch.setenv("APP_RELOAD", raw_value)

    assert _run_local_server(monkeypatch)["reload"] is True


def test_systemd_unit_pins_reload_off() -> None:
    unit = (REPO_ROOT / "packaging" / "systemd" / "alice-api.service").read_text(encoding="utf-8")

    assert "Environment=APP_RELOAD=false" in unit
    assert "-m alicebot_api.local_server" in unit


def test_makefile_defaults_reload_off_and_still_allows_opting_in() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "APP_RELOAD ?= false" in makefile
    assert "APP_RELOAD=false ./scripts/api_dev.sh" not in makefile
    assert makefile.count("APP_RELOAD=$(APP_RELOAD) ./scripts/api_dev.sh") == 3

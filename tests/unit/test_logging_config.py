from __future__ import annotations

from pathlib import Path

from alicebot_api.config import Settings
from alicebot_api.logging_config import build_uvicorn_log_config


def test_stdout_logging_config_disables_access_handler_when_access_logs_are_off() -> None:
    config = build_uvicorn_log_config(
        Settings(
            app_log_mode="stdout",
            app_access_log=False,
        )
    )

    assert config["handlers"]["stdout"]["class"] == "logging.StreamHandler"
    assert config["handlers"]["stdout"]["stream"] == "ext://sys.stdout"
    assert config["loggers"]["uvicorn.access"]["handlers"] == ["null"]


def test_file_logging_config_uses_bounded_rotation(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "alicebot.log"

    config = build_uvicorn_log_config(
        Settings(
            app_log_mode="file",
            app_log_path=str(log_path),
            app_log_max_bytes=2048,
            app_log_backup_count=4,
            app_access_log=True,
        )
    )

    assert log_path.parent.exists()
    assert config["handlers"]["file"]["class"] == "logging.handlers.RotatingFileHandler"
    assert config["handlers"]["file"]["filename"] == str(log_path)
    assert config["handlers"]["file"]["maxBytes"] == 2048
    assert config["handlers"]["file"]["backupCount"] == 4
    assert config["loggers"]["uvicorn.access"]["handlers"] == ["file"]

from __future__ import annotations

import logging
import os
from pathlib import Path
import subprocess
import sys
from contextlib import contextmanager
from uuid import uuid4

import workers.alicebot_worker.main as main_module
from apps.api.src.alicebot_api.config import Settings
from workers.alicebot_worker.task_runs import WorkerTickOutcome


def test_run_logs_skip_message_when_worker_user_id_is_missing(caplog, monkeypatch) -> None:
    monkeypatch.delenv("ALICEBOT_WORKER_USER_ID", raising=False)

    with caplog.at_level(logging.INFO, logger="alicebot.worker"):
        main_module.run()

    assert caplog.messages == [
        "Worker tick skipped because ALICEBOT_WORKER_USER_ID is not configured.",
    ]


def test_run_ticks_one_task_run_when_worker_user_id_is_configured(caplog, monkeypatch) -> None:
    worker_user_id = uuid4()
    monkeypatch.setenv("ALICEBOT_WORKER_USER_ID", str(worker_user_id))
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_acquire_and_tick_one_task_run(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return WorkerTickOutcome(
            task_run_id="run-1",
            previous_status="queued",
            status="running",
            stop_reason=None,
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "acquire_and_tick_one_task_run", fake_acquire_and_tick_one_task_run)

    with caplog.at_level(logging.INFO, logger="alicebot.worker"):
        main_module.run()

    assert captured == {
        "database_url": "postgresql://app",
        "current_user_id": worker_user_id,
        "store_type": "ContinuityStore",
        "user_id": worker_user_id,
    }
    assert caplog.messages == [
        "Worker ticked task run run-1 from queued to running (stop_reason=None).",
    ]


def test_module_entrypoint_logs_skip_message_when_worker_user_id_is_missing() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    pythonpath_entries = [str(repo_root / "apps" / "api" / "src"), str(repo_root / "workers")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    env.pop("ALICEBOT_WORKER_USER_ID", None)

    result = subprocess.run(
        [sys.executable, "-m", "alicebot_worker.main"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Worker tick skipped because ALICEBOT_WORKER_USER_ID is not configured." in result.stderr

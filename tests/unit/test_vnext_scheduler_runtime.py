from __future__ import annotations

import json
import os
from pathlib import Path
import signal
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

import alicebot_api.vnext_scheduler_runtime as scheduler_runtime
from alicebot_api.vnext_scheduler import VNextSchedulerValidationError
from alicebot_api.vnext_scheduler_runtime import (
    SchedulerRuntimeConfig,
    _acquire_owner_lease,
    _lease_is_stale,
    _owner_file,
    _release_owner_lease,
    _sleep_interruptibly,
    daemon_status,
    run_due_workflows_durable,
    run_foreground_daemon,
    stop_daemon,
)


def test_background_scheduler_keeps_database_url_out_of_argv_and_in_child_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spawned_commands: list[list[str]] = []
    spawned_envs: list[dict[str, str]] = []

    class FakeProcess:
        pid = 24680

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            raise AssertionError("healthy spawned process must not be terminated")

    def fake_popen(command, **kwargs):
        spawned_commands.append(list(command))
        spawned_envs.append(dict(kwargs["env"]))
        return FakeProcess()

    monkeypatch.setattr(scheduler_runtime, "daemon_status", lambda **_kwargs: {"running": False})
    monkeypatch.setattr(scheduler_runtime, "_process_identity", lambda pid: f"identity:{pid}")
    monkeypatch.setattr(scheduler_runtime, "_acquire_owner_lease", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(scheduler_runtime, "_replace_owner_lease", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(scheduler_runtime.subprocess, "Popen", fake_popen)

    database_url = "postgresql://alice:scheduler-secret@db/alice"
    config = SchedulerRuntimeConfig(
        database_url=database_url,
        user_id=uuid4(),
        pid_file=tmp_path / "scheduler.pid",
        status_file=tmp_path / "scheduler-status.json",
        log_file=tmp_path / "scheduler.log",
        once=True,
    )

    result = scheduler_runtime.start_background_daemon(config)

    assert result["started"] is True
    assert len(spawned_commands) == 1
    command = spawned_commands[0]
    assert "--database-url" not in command
    assert database_url not in command
    assert "scheduler-secret" not in "\0".join(command)
    assert spawned_envs[0]["DATABASE_URL"] == database_url
    assert spawned_envs[0][scheduler_runtime.INSTANCE_TOKEN_ENV]
    assert command.count("--once") == 1
    assert command.index("--foreground") < command.index("--once")


def test_daemon_status_preserves_explicit_stopped_state_for_foreground_once(tmp_path: Path) -> None:
    pid_file = tmp_path / "scheduler.pid"
    status_file = tmp_path / "scheduler-status.json"
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    status_file.write_text(
        json.dumps({"pid": os.getpid(), "running": False, "mode": "foreground"}),
        encoding="utf-8",
    )

    status = daemon_status(pid_file=pid_file, status_file=status_file)

    assert status["pid"] == os.getpid()
    assert status["running"] is False


def test_sleep_interruptibly_uses_short_slices_and_stops_early() -> None:
    calls: list[float] = []

    def sleep_fn(seconds: float) -> None:
        calls.append(seconds)

    _sleep_interruptibly(60, should_stop=lambda: len(calls) >= 2, sleep_fn=sleep_fn)

    assert calls == [0.5, 0.5]


def test_scheduler_owner_lease_allows_only_one_concurrent_launcher(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pid_file = tmp_path / "scheduler.pid"
    identity = "test-process-birth"
    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._process_identity",
        lambda _pid: identity,
    )

    def acquire(token: str) -> bool:
        return _acquire_owner_lease(
            pid_file,
            pid=os.getpid(),
            instance_token=token,
            process_identity=identity,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(acquire, ("token-a", "token-b")))

    assert sorted(results) == [False, True]
    record = json.loads(_owner_file(pid_file).read_text(encoding="utf-8"))
    _release_owner_lease(pid_file, instance_token=str(record["instance_token"]))
    assert not _owner_file(pid_file).exists()


def test_scheduler_owner_lease_reclamation_fails_closed_for_live_unknown_identity(
    monkeypatch,
) -> None:
    record = {
        "pid": 123,
        "instance_token": "owner-token",
        "process_identity": "expected-birth",
    }
    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._pid_running",
        lambda _pid: True,
    )
    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._process_identity",
        lambda _pid: None,
    )

    assert _lease_is_stale(record) is False

    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._process_identity",
        lambda _pid: "different-birth",
    )
    assert _lease_is_stale(record) is True

    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._pid_running",
        lambda _pid: False,
    )
    assert _lease_is_stale(record) is True


def test_stop_daemon_refuses_legacy_pid_without_ownership_identity(tmp_path: Path) -> None:
    pid_file = tmp_path / "scheduler.pid"
    status_file = tmp_path / "scheduler-status.json"
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    status_file.write_text(
        json.dumps({"pid": os.getpid(), "running": True}),
        encoding="utf-8",
    )

    result = stop_daemon(pid_file=pid_file, status_file=status_file)

    assert result["stopped"] is False
    assert "unverified" in str(result["message"])


def test_daemon_status_verifies_one_canonical_process_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pid_file = tmp_path / "scheduler.pid"
    status_file = tmp_path / "scheduler-status.json"
    owner_file = _owner_file(pid_file)
    identity = "ps-sha256:stable-child-birth"
    record = {
        "pid": os.getpid(),
        "instance_token": "child-token",
        "process_identity": identity,
    }
    pid_file.write_text(json.dumps(record), encoding="utf-8")
    owner_file.write_text(json.dumps(record), encoding="utf-8")
    status_file.write_text(
        json.dumps({**record, "running": True, "mode": "background"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._process_identity",
        lambda _pid: identity,
    )

    status = daemon_status(pid_file=pid_file, status_file=status_file)

    assert status["ownership_records_match"] is True
    assert status["ownership_verified"] is True
    assert status["running"] is True


def test_foreground_once_returns_nonzero_when_claimed_workflow_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._process_identity",
        lambda _pid: "test-process-birth",
    )
    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime.run_due_workflows_durable",
        lambda **_kwargs: {
            "checked_at": "2026-07-13T00:00:00+00:00",
            "due_count": 1,
            "failed_count": 1,
            "reaped_count": 0,
            "runs": [{"run": {"status": "failed"}}],
        },
    )
    config = SchedulerRuntimeConfig(
        database_url="postgresql://db/alice",
        user_id=uuid4(),
        pid_file=tmp_path / "scheduler.pid",
        status_file=tmp_path / "scheduler-status.json",
        log_file=tmp_path / "scheduler.log",
        once=True,
    )

    result = run_foreground_daemon(config)

    assert result["exit_code"] == 1
    assert result["last_error"] == "Scheduler workflow execution failed"
    assert result["last_error_code"] == "scheduler_workflow_failed"
    assert result["running"] is False


def test_foreground_once_scan_exception_is_static_and_omits_exception_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = "UNIQUE_SCHEDULER_SCAN_EXCEPTION_SENTINEL"
    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._process_identity",
        lambda _pid: "test-process-birth",
    )

    def fail_scan(**_kwargs: object) -> dict[str, object]:
        raise RuntimeError(sentinel)

    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime.run_due_workflows_durable",
        fail_scan,
    )
    config = SchedulerRuntimeConfig(
        database_url="postgresql://db/alice",
        user_id=uuid4(),
        pid_file=tmp_path / "scheduler.pid",
        status_file=tmp_path / "scheduler-status.json",
        log_file=tmp_path / "scheduler.log",
        once=True,
    )

    result = run_foreground_daemon(config)

    assert result["exit_code"] == 1
    assert result["last_error_code"] == "scheduler_scan_failed"
    assert result["last_error"] == "Scheduler scan failed"
    assert result["last_error_type"] is None
    assert sentinel not in json.dumps(result)


def test_successful_daemon_scan_clears_stale_error_type(
    tmp_path: Path,
    monkeypatch,
) -> None:
    attempts = 0
    sleeps = 0

    def fake_run_due(**_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("transient scan failure")
        return {
            "checked_at": "2026-07-13T00:01:00+00:00",
            "due_count": 0,
            "failed_count": 0,
            "reaped_count": 0,
            "runs": [],
        }

    def fake_sleep(*_args, **_kwargs) -> None:
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            os.kill(os.getpid(), signal.SIGTERM)

    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._process_identity",
        lambda _pid: "test-process-birth",
    )
    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime.run_due_workflows_durable",
        fake_run_due,
    )
    monkeypatch.setattr(
        "alicebot_api.vnext_scheduler_runtime._sleep_interruptibly",
        fake_sleep,
    )
    config = SchedulerRuntimeConfig(
        database_url="postgresql://db/alice",
        user_id=uuid4(),
        interval_seconds=1,
        pid_file=tmp_path / "scheduler.pid",
        status_file=tmp_path / "scheduler-status.json",
        log_file=tmp_path / "scheduler.log",
    )

    result = run_foreground_daemon(config)

    assert attempts == 2
    assert result["last_error"] is None
    assert result["last_error_type"] is None
    assert result["exit_code"] == 0


def test_durable_scheduler_fails_closed_on_sqlite() -> None:
    with pytest.raises(
        VNextSchedulerValidationError,
        match="requires PostgreSQL",
    ):
        run_due_workflows_durable(
            database_url="sqlite:///tmp/alice.db",
            user_id=uuid4(),
        )

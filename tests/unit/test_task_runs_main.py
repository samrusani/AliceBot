from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.task_runs import (
    TaskRunNotFoundError,
    TaskRunTransitionError,
    TaskRunValidationError,
)
from alicebot_api.tasks import TaskNotFoundError


def test_create_task_run_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    task_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_task_run_record(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "task_run": {
                "id": "run-1",
                "task_id": str(task_id),
                "status": "queued",
                "checkpoint": {"cursor": 0, "target_steps": 2, "wait_for_signal": False},
                "tick_count": 0,
                "step_count": 0,
                "max_ticks": 2,
                "stop_reason": None,
                "created_at": "2026-03-27T10:00:00+00:00",
                "updated_at": "2026-03-27T10:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_task_run_record", fake_create_task_run_record)

    response = main_module.create_task_run(
        task_id,
        main_module.CreateTaskRunRequest(
            user_id=user_id,
            max_ticks=2,
            checkpoint={"cursor": 0, "target_steps": 2, "wait_for_signal": False},
        ),
    )

    assert response.status_code == 201
    assert json.loads(response.body)["task_run"]["id"] == "run-1"
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["request"].task_id == task_id


def test_create_task_run_endpoint_maps_not_found_and_validation_errors(monkeypatch) -> None:
    user_id = uuid4()
    task_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)

    monkeypatch.setattr(
        main_module,
        "create_task_run_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TaskNotFoundError(f"task {task_id} was not found")),
    )
    not_found_response = main_module.create_task_run(
        task_id,
        main_module.CreateTaskRunRequest(user_id=user_id, max_ticks=1, checkpoint={}),
    )
    assert not_found_response.status_code == 404
    assert json.loads(not_found_response.body) == {"detail": f"task {task_id} was not found"}

    monkeypatch.setattr(
        main_module,
        "create_task_run_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TaskRunValidationError("checkpoint.cursor must be an integer")),
    )
    validation_response = main_module.create_task_run(
        task_id,
        main_module.CreateTaskRunRequest(user_id=user_id, max_ticks=1, checkpoint={"cursor": "x"}),
    )
    assert validation_response.status_code == 400
    assert json.loads(validation_response.body) == {"detail": "checkpoint.cursor must be an integer"}


def test_list_and_get_task_runs_endpoints_return_payload(monkeypatch) -> None:
    user_id = uuid4()
    task_id = uuid4()
    task_run_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_task_run_records",
        lambda *_args, **_kwargs: {
            "items": [
                {
                    "id": str(task_run_id),
                    "task_id": str(task_id),
                    "status": "running",
                    "checkpoint": {"cursor": 1, "target_steps": 2, "wait_for_signal": False},
                    "tick_count": 1,
                    "step_count": 1,
                    "max_ticks": 2,
                    "stop_reason": None,
                    "created_at": "2026-03-27T10:00:00+00:00",
                    "updated_at": "2026-03-27T10:01:00+00:00",
                }
            ],
            "summary": {
                "task_id": str(task_id),
                "total_count": 1,
                "order": ["created_at_asc", "id_asc"],
            },
        },
    )
    monkeypatch.setattr(
        main_module,
        "get_task_run_record",
        lambda *_args, **_kwargs: {
            "task_run": {
                "id": str(task_run_id),
                "task_id": str(task_id),
                "status": "running",
                "checkpoint": {"cursor": 1, "target_steps": 2, "wait_for_signal": False},
                "tick_count": 1,
                "step_count": 1,
                "max_ticks": 2,
                "stop_reason": None,
                "created_at": "2026-03-27T10:00:00+00:00",
                "updated_at": "2026-03-27T10:01:00+00:00",
            }
        },
    )

    list_response = main_module.list_task_runs(task_id, user_id)
    get_response = main_module.get_task_run(task_run_id, user_id)

    assert list_response.status_code == 200
    assert json.loads(list_response.body)["summary"]["task_id"] == str(task_id)
    assert get_response.status_code == 200
    assert json.loads(get_response.body)["task_run"]["id"] == str(task_run_id)


def test_get_task_run_endpoint_maps_missing_record_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_run_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "get_task_run_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TaskRunNotFoundError(f"task run {task_run_id} was not found")),
    )

    response = main_module.get_task_run(task_run_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task run {task_run_id} was not found"}


def test_task_run_tick_pause_resume_cancel_endpoints_map_conflicts(monkeypatch) -> None:
    user_id = uuid4()
    task_run_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def conflict(*_args, **_kwargs):
        raise TaskRunTransitionError(f"task run {task_run_id} is completed and cannot be resumed")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "tick_task_run_record", conflict)
    monkeypatch.setattr(main_module, "pause_task_run_record", conflict)
    monkeypatch.setattr(main_module, "resume_task_run_record", conflict)
    monkeypatch.setattr(main_module, "cancel_task_run_record", conflict)

    request = main_module.MutateTaskRunRequest(user_id=user_id)
    tick_response = main_module.tick_task_run(task_run_id, request)
    pause_response = main_module.pause_task_run(task_run_id, request)
    resume_response = main_module.resume_task_run(task_run_id, request)
    cancel_response = main_module.cancel_task_run(task_run_id, request)

    expected = {"detail": f"task run {task_run_id} is completed and cannot be resumed"}
    assert tick_response.status_code == 409
    assert json.loads(tick_response.body) == expected
    assert pause_response.status_code == 409
    assert json.loads(pause_response.body) == expected
    assert resume_response.status_code == 409
    assert json.loads(resume_response.body) == expected
    assert cancel_response.status_code == 409
    assert json.loads(cancel_response.body) == expected

from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.tasks import (
    TaskNotFoundError,
    TaskStepNotFoundError,
    TaskStepSequenceError,
    TaskStepTransitionError,
)


def test_list_task_steps_endpoint_returns_payload(monkeypatch) -> None:
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
        "list_task_step_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {
                "task_id": str(task_id),
                "total_count": 0,
                "latest_sequence_no": None,
                "latest_status": None,
                "next_sequence_no": 1,
                "append_allowed": False,
                "order": ["sequence_no_asc", "created_at_asc", "id_asc"],
            },
        },
    )

    response = main_module.list_task_steps(task_id, user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {
            "task_id": str(task_id),
            "total_count": 0,
            "latest_sequence_no": None,
            "latest_status": None,
            "next_sequence_no": 1,
            "append_allowed": False,
            "order": ["sequence_no_asc", "created_at_asc", "id_asc"],
        },
    }


def test_list_task_steps_endpoint_maps_task_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_list_task_step_records(*_args, **_kwargs):
        raise TaskNotFoundError(f"task {task_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_task_step_records", fake_list_task_step_records)

    response = main_module.list_task_steps(task_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task {task_id} was not found"}


def test_get_task_step_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_step_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_task_step_record(*_args, **_kwargs):
        raise TaskStepNotFoundError(f"task step {task_step_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_task_step_record", fake_get_task_step_record)

    response = main_module.get_task_step(task_step_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task step {task_step_id} was not found"}


def test_create_next_task_step_endpoint_maps_sequence_conflict_to_409(monkeypatch) -> None:
    task_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_create_next_task_step_record(*_args, **_kwargs):
        raise TaskStepSequenceError(f"task {task_id} latest step blocked append")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_next_task_step_record", fake_create_next_task_step_record)

    response = main_module.create_next_task_step(
        task_id,
        main_module.CreateNextTaskStepRequest(
            user_id=user_id,
            kind="governed_request",
            status="created",
            request=main_module.TaskStepRequestSnapshot(
                thread_id=uuid4(),
                tool_id=uuid4(),
                action="tool.run",
                scope="workspace",
                attributes={},
            ),
            outcome=main_module.TaskStepOutcomeRequest(
                routing_decision="approval_required",
                approval_status="pending",
            ),
            lineage=main_module.TaskStepLineageRequest(parent_step_id=uuid4()),
        ),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {"detail": f"task {task_id} latest step blocked append"}


def test_transition_task_step_endpoint_maps_transition_conflict_to_409(monkeypatch) -> None:
    task_step_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_transition_task_step_record(*_args, **_kwargs):
        raise TaskStepTransitionError(f"task step {task_step_id} is created and cannot transition")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "transition_task_step_record", fake_transition_task_step_record)

    response = main_module.transition_task_step(
        task_step_id,
        main_module.TransitionTaskStepRequest(
            user_id=user_id,
            status="approved",
            outcome=main_module.TaskStepOutcomeRequest(
                routing_decision="approval_required",
                approval_status="approved",
            ),
        ),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"task step {task_step_id} is created and cannot transition"
    }

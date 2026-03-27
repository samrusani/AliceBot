from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import (
    TaskRunCancelInput,
    TaskRunCreateInput,
    TaskRunPauseInput,
    TaskRunResumeInput,
    TaskRunTickInput,
)
from alicebot_api.task_runs import (
    TaskRunNotFoundError,
    TaskRunTransitionError,
    TaskRunValidationError,
    cancel_task_run_record,
    create_task_run_record,
    get_task_run_record,
    list_task_run_records,
    pause_task_run_record,
    resume_task_run_record,
    tick_task_run_record,
)
from alicebot_api.tasks import TaskNotFoundError


class TaskRunStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 27, 10, 0, tzinfo=UTC)
        self.user_id = uuid4()
        self.tasks: list[dict[str, object]] = []
        self.task_runs: list[dict[str, object]] = []

    def seed_task(self) -> UUID:
        task_id = uuid4()
        self.tasks.append(
            {
                "id": task_id,
                "user_id": self.user_id,
                "thread_id": uuid4(),
                "tool_id": uuid4(),
                "status": "approved",
                "request": {
                    "thread_id": str(uuid4()),
                    "tool_id": str(uuid4()),
                    "action": "tool.run",
                    "scope": "workspace",
                    "domain_hint": None,
                    "risk_hint": None,
                    "attributes": {},
                },
                "tool": {"id": str(uuid4()), "tool_key": "proxy.echo"},
                "latest_approval_id": None,
                "latest_execution_id": None,
                "created_at": self.base_time,
                "updated_at": self.base_time,
            }
        )
        return task_id

    def get_task_optional(self, task_id: UUID) -> dict[str, object] | None:
        return next((task for task in self.tasks if task["id"] == task_id), None)

    def create_task_run(
        self,
        *,
        task_id: UUID,
        status: str,
        checkpoint: dict[str, object],
        tick_count: int,
        step_count: int,
        max_ticks: int,
        stop_reason: str | None,
    ) -> dict[str, object]:
        row = {
            "id": uuid4(),
            "user_id": self.user_id,
            "task_id": task_id,
            "status": status,
            "checkpoint": dict(checkpoint),
            "tick_count": tick_count,
            "step_count": step_count,
            "max_ticks": max_ticks,
            "stop_reason": stop_reason,
            "created_at": self.base_time + timedelta(minutes=len(self.task_runs)),
            "updated_at": self.base_time + timedelta(minutes=len(self.task_runs)),
        }
        self.task_runs.append(row)
        self.task_runs.sort(key=lambda item: (item["created_at"], item["id"]))
        return row

    def list_task_runs_for_task(self, task_id: UUID) -> list[dict[str, object]]:
        return [row for row in self.task_runs if row["task_id"] == task_id]

    def get_task_run_optional(self, task_run_id: UUID) -> dict[str, object] | None:
        return next((row for row in self.task_runs if row["id"] == task_run_id), None)

    def update_task_run_optional(
        self,
        *,
        task_run_id: UUID,
        status: str,
        checkpoint: dict[str, object],
        tick_count: int,
        step_count: int,
        stop_reason: str | None,
    ) -> dict[str, object] | None:
        row = self.get_task_run_optional(task_run_id)
        if row is None:
            return None
        row["status"] = status
        row["checkpoint"] = dict(checkpoint)
        row["tick_count"] = tick_count
        row["step_count"] = step_count
        row["stop_reason"] = stop_reason
        row["updated_at"] = self.base_time + timedelta(hours=1, minutes=tick_count + step_count)
        return row


def test_create_list_and_get_task_run_records_are_deterministic() -> None:
    store = TaskRunStoreStub()
    task_id = store.seed_task()

    first = create_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunCreateInput(
            task_id=task_id,
            max_ticks=2,
            checkpoint={"cursor": 0, "target_steps": 2, "wait_for_signal": False},
        ),
    )
    second = create_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunCreateInput(
            task_id=task_id,
            max_ticks=1,
            checkpoint={"cursor": 0, "target_steps": 1, "wait_for_signal": False},
        ),
    )

    listed = list_task_run_records(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        task_id=task_id,
    )
    detail = get_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        task_run_id=UUID(second["task_run"]["id"]),
    )

    assert [item["id"] for item in listed["items"]] == [
        first["task_run"]["id"],
        second["task_run"]["id"],
    ]
    assert listed["summary"] == {
        "task_id": str(task_id),
        "total_count": 2,
        "order": ["created_at_asc", "id_asc"],
    }
    assert detail == {"task_run": second["task_run"]}


def test_tick_advances_checkpoint_and_completes_run() -> None:
    store = TaskRunStoreStub()
    task_id = store.seed_task()
    created = create_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunCreateInput(
            task_id=task_id,
            max_ticks=3,
            checkpoint={"cursor": 0, "target_steps": 2, "wait_for_signal": False},
        ),
    )
    task_run_id = UUID(created["task_run"]["id"])

    first_tick = tick_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunTickInput(task_run_id=task_run_id),
    )
    second_tick = tick_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunTickInput(task_run_id=task_run_id),
    )

    assert first_tick["previous_status"] == "queued"
    assert first_tick["task_run"]["status"] == "running"
    assert first_tick["task_run"]["tick_count"] == 1
    assert first_tick["task_run"]["step_count"] == 1
    assert first_tick["task_run"]["checkpoint"]["cursor"] == 1
    assert first_tick["task_run"]["stop_reason"] is None

    assert second_tick["previous_status"] == "running"
    assert second_tick["task_run"]["status"] == "completed"
    assert second_tick["task_run"]["checkpoint"]["cursor"] == 2
    assert second_tick["task_run"]["tick_count"] == 2
    assert second_tick["task_run"]["step_count"] == 2
    assert second_tick["task_run"]["stop_reason"] == "completed"


def test_tick_sets_budget_exhaustion_stop_reason_in_safe_non_running_state() -> None:
    store = TaskRunStoreStub()
    task_id = store.seed_task()
    created = create_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunCreateInput(
            task_id=task_id,
            max_ticks=1,
            checkpoint={"cursor": 0, "target_steps": 3, "wait_for_signal": False},
        ),
    )
    task_run_id = UUID(created["task_run"]["id"])

    first_tick = tick_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunTickInput(task_run_id=task_run_id),
    )
    exhausted_tick = tick_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunTickInput(task_run_id=task_run_id),
    )

    assert first_tick["task_run"]["status"] == "running"
    assert exhausted_tick["task_run"]["status"] == "paused"
    assert exhausted_tick["task_run"]["stop_reason"] == "budget_exhausted"
    assert exhausted_tick["task_run"]["tick_count"] == 1


def test_wait_resume_pause_cancel_transitions_are_deterministic() -> None:
    store = TaskRunStoreStub()
    task_id = store.seed_task()
    created = create_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunCreateInput(
            task_id=task_id,
            max_ticks=3,
            checkpoint={"cursor": 0, "target_steps": 2, "wait_for_signal": True},
        ),
    )
    task_run_id = UUID(created["task_run"]["id"])

    waiting = tick_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunTickInput(task_run_id=task_run_id),
    )
    resumed = resume_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunResumeInput(task_run_id=task_run_id),
    )
    paused = pause_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunPauseInput(task_run_id=task_run_id),
    )
    cancelled = cancel_task_run_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskRunCancelInput(task_run_id=task_run_id),
    )

    assert waiting["task_run"]["status"] == "waiting"
    assert waiting["task_run"]["stop_reason"] == "wait_state"
    assert waiting["task_run"]["checkpoint"]["wait_for_signal"] is True
    assert resumed["task_run"]["status"] == "running"
    assert resumed["task_run"]["checkpoint"]["wait_for_signal"] is False
    assert paused["task_run"]["status"] == "paused"
    assert paused["task_run"]["stop_reason"] == "paused"
    assert cancelled["task_run"]["status"] == "cancelled"
    assert cancelled["task_run"]["stop_reason"] == "cancelled"

    with pytest.raises(
        TaskRunTransitionError,
        match="cannot be resumed",
    ):
        resume_task_run_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=TaskRunResumeInput(task_run_id=task_run_id),
        )


def test_create_task_run_rejects_invalid_checkpoint_and_missing_task() -> None:
    store = TaskRunStoreStub()

    with pytest.raises(TaskNotFoundError, match="was not found"):
        create_task_run_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=TaskRunCreateInput(
                task_id=uuid4(),
                max_ticks=1,
                checkpoint={"cursor": 0, "target_steps": 1, "wait_for_signal": False},
            ),
        )

    task_id = store.seed_task()
    with pytest.raises(TaskRunValidationError, match="checkpoint.cursor must be an integer"):
        create_task_run_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=TaskRunCreateInput(
                task_id=task_id,
                max_ticks=1,
                checkpoint={"cursor": "zero", "target_steps": 1, "wait_for_signal": False},
            ),
        )


def test_get_task_run_raises_not_found_for_missing_record() -> None:
    store = TaskRunStoreStub()

    with pytest.raises(TaskRunNotFoundError, match="task run"):
        get_task_run_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            task_run_id=uuid4(),
        )

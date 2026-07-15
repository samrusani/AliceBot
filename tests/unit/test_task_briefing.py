from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import TaskBriefCompileRequestInput
from alicebot_api.task_briefing import (
    TaskBriefValidationError,
    compare_task_briefs,
    compile_and_persist_task_brief,
    compile_task_brief_record,
    get_persisted_task_brief,
)


class TaskBriefStoreStub:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self._task_briefs: dict[UUID, dict[str, object]] = {}

    def list_continuity_recall_candidates(self):
        return list(self._rows)

    def create_task_brief(self, **kwargs):
        task_brief_id = uuid4()
        row = {
            "id": task_brief_id,
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "mode": kwargs["mode"],
            "query_text": kwargs["query_text"],
            "scope": kwargs["scope"],
            "provider_strategy": kwargs["provider_strategy"],
            "model_pack_strategy": kwargs["model_pack_strategy"],
            "token_budget": kwargs["token_budget"],
            "estimated_tokens": kwargs["estimated_tokens"],
            "item_count": kwargs["item_count"],
            "deterministic_key": kwargs["deterministic_key"],
            "payload": kwargs["payload"],
            "created_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
        }
        self._task_briefs[task_brief_id] = row
        return row

    def get_task_brief_optional(self, *, task_brief_id: UUID):
        return self._task_briefs.get(task_brief_id)

    def replace_task_brief_payload(
        self,
        *,
        task_brief_id: UUID,
        payload: dict[str, object],
    ) -> None:
        self._task_briefs[task_brief_id]["payload"] = payload


def _candidate(
    *,
    title: str,
    object_type: str,
    created_at: datetime,
    thread_id: UUID,
    status: str = "active",
    is_promotable: bool | None = None,
) -> dict[str, object]:
    resolved_is_promotable = object_type != "MemoryFact" if is_promotable is None else is_promotable
    return {
        "id": uuid4(),
        "user_id": UUID("11111111-1111-4111-8111-111111111111"),
        "capture_event_id": uuid4(),
        "object_type": object_type,
        "status": status,
        "is_preserved": True,
        "is_searchable": True,
        "is_promotable": resolved_is_promotable,
        "title": title,
        "body": {"text": title},
        "provenance": {"thread_id": str(thread_id)},
        "confidence": 0.9,
        "last_confirmed_at": None,
        "supersedes_object_id": None,
        "superseded_by_object_id": None,
        "object_created_at": created_at,
        "object_updated_at": created_at,
        "admission_posture": "DERIVED",
        "admission_reason": "seeded",
        "explicit_signal": None,
        "capture_created_at": created_at,
    }


def test_worker_subtask_brief_is_smaller_than_user_recall_and_deterministic() -> None:
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    rows = [
        _candidate(
            title="Decision: Freeze release scope",
            object_type="Decision",
            created_at=datetime(2026, 4, 14, 8, 0, tzinfo=UTC),
            thread_id=thread_id,
        ),
        _candidate(
            title="Waiting For: Legal approval",
            object_type="WaitingFor",
            created_at=datetime(2026, 4, 14, 8, 5, tzinfo=UTC),
            thread_id=thread_id,
        ),
        _candidate(
            title="Next Action: Draft rollout note",
            object_type="NextAction",
            created_at=datetime(2026, 4, 14, 8, 6, tzinfo=UTC),
            thread_id=thread_id,
        ),
        _candidate(
            title="Memory Fact: Customer is launch-sensitive",
            object_type="MemoryFact",
            created_at=datetime(2026, 4, 14, 8, 7, tzinfo=UTC),
            thread_id=thread_id,
            is_promotable=True,
        ),
        _candidate(
            title="Note: Keep the migration artifact-only",
            object_type="Note",
            created_at=datetime(2026, 4, 14, 8, 8, tzinfo=UTC),
            thread_id=thread_id,
        ),
    ]
    store = TaskBriefStoreStub(rows)
    user_id = UUID("11111111-1111-4111-8111-111111111111")

    user_recall_one = compile_task_brief_record(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=TaskBriefCompileRequestInput(mode="user_recall", thread_id=thread_id),
    )
    user_recall_two = compile_task_brief_record(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=TaskBriefCompileRequestInput(mode="user_recall", thread_id=thread_id),
    )
    worker = compile_task_brief_record(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=TaskBriefCompileRequestInput(mode="worker_subtask", thread_id=thread_id),
    )

    assert user_recall_one == user_recall_two
    assert worker["summary"]["estimated_tokens"] < user_recall_one["summary"]["estimated_tokens"]
    assert worker["summary"]["selected_item_count"] <= user_recall_one["summary"]["selected_item_count"]
    assert [section["section_key"] for section in worker["sections"]] == [
        "current_objective",
        "active_constraints",
        "critical_context",
    ]


def test_task_brief_compare_and_persistence_round_trip() -> None:
    thread_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    rows = [
        _candidate(
            title="Decision: Keep phased rollout",
            object_type="Decision",
            created_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
            thread_id=thread_id,
        ),
        _candidate(
            title="Blocker: Vendor dependency unresolved",
            object_type="Blocker",
            created_at=datetime(2026, 4, 14, 9, 5, tzinfo=UTC),
            thread_id=thread_id,
        ),
        _candidate(
            title="Next Action: Escalate vendor issue",
            object_type="NextAction",
            created_at=datetime(2026, 4, 14, 9, 10, tzinfo=UTC),
            thread_id=thread_id,
        ),
    ]
    store = TaskBriefStoreStub(rows)
    user_id = UUID("11111111-1111-4111-8111-111111111111")

    comparison = compare_task_briefs(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        primary_request=TaskBriefCompileRequestInput(mode="worker_subtask", thread_id=thread_id),
        secondary_request=TaskBriefCompileRequestInput(mode="user_recall", thread_id=thread_id),
    )
    assert comparison["comparison"]["primary_mode"] == "worker_subtask"
    assert comparison["comparison"]["secondary_mode"] == "user_recall"
    assert comparison["comparison"]["smaller_mode"] == "worker_subtask"

    persisted = compile_and_persist_task_brief(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=TaskBriefCompileRequestInput(mode="resume", thread_id=thread_id),
    )
    loaded = get_persisted_task_brief(
        store,  # type: ignore[arg-type]
        task_brief_id=UUID(persisted["persistence"]["task_brief_id"]),
    )
    assert loaded == persisted
    assert [section["section_key"] for section in loaded["task_brief"]["sections"]] == [
        "last_decision",
        "open_loops",
        "recent_changes",
        "next_action",
    ]


def test_historical_persisted_task_brief_is_normalized_without_mutating_storage() -> None:
    store = TaskBriefStoreStub([])
    persisted = compile_and_persist_task_brief(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=TaskBriefCompileRequestInput(
            mode="worker_subtask",
            briefing_strategy="compact",
        ),
    )
    task_brief_id = UUID(persisted["persistence"]["task_brief_id"])
    historical_payload = cast(dict[str, object], deepcopy(persisted["task_brief"]))
    historical_strategy = cast(dict[str, object], historical_payload["strategy"])
    historical_strategy["model_pack_strategy"] = historical_strategy.pop(
        "briefing_strategy"
    )
    historical_payload["workspace_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    historical_payload["pack_id"] = "legacy-pack"
    historical_payload["pack_version"] = "1.0.0"
    historical_strategy["workspace_id"] = historical_payload["workspace_id"]
    historical_strategy["pack_id"] = historical_payload["pack_id"]
    historical_strategy["pack_version"] = historical_payload["pack_version"]
    stored_snapshot = deepcopy(historical_payload)
    store.replace_task_brief_payload(
        task_brief_id=task_brief_id,
        payload=historical_payload,
    )

    loaded = get_persisted_task_brief(
        store,  # type: ignore[arg-type]
        task_brief_id=task_brief_id,
    )

    loaded_brief = loaded["task_brief"]
    loaded_strategy = loaded_brief["strategy"]
    stale_keys = {"workspace_id", "pack_id", "pack_version", "model_pack_strategy"}
    assert loaded_strategy["briefing_strategy"] == "compact"
    assert not stale_keys & loaded_brief.keys()
    assert not stale_keys & loaded_strategy.keys()
    assert store.get_task_brief_optional(task_brief_id=task_brief_id)["payload"] == stored_snapshot


def test_worker_subtask_filters_non_promotable_facts_by_default() -> None:
    thread_id = UUID("12121212-1212-4212-8212-121212121212")
    rows = [
        _candidate(
            title="Decision: Keep the existing contract",
            object_type="Decision",
            created_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
            thread_id=thread_id,
        ),
        _candidate(
            title="Memory Fact: Draft summary is stale",
            object_type="MemoryFact",
            created_at=datetime(2026, 4, 14, 9, 5, tzinfo=UTC),
            thread_id=thread_id,
            is_promotable=False,
        ),
        _candidate(
            title="Note: Keep the rollout note short",
            object_type="Note",
            created_at=datetime(2026, 4, 14, 9, 10, tzinfo=UTC),
            thread_id=thread_id,
        ),
    ]
    store = TaskBriefStoreStub(rows)
    user_id = UUID("11111111-1111-4111-8111-111111111111")

    default_brief = compile_task_brief_record(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=TaskBriefCompileRequestInput(
            mode="worker_subtask",
            thread_id=thread_id,
            token_budget=1024,
        ),
    )
    override_brief = compile_task_brief_record(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=TaskBriefCompileRequestInput(
            mode="worker_subtask",
            thread_id=thread_id,
            token_budget=1024,
            include_non_promotable_facts=True,
        ),
    )

    default_context_titles = [
        item["title"]
        for item in default_brief["sections"][2]["items"]
    ]
    override_context_titles = [
        item["title"]
        for item in override_brief["sections"][2]["items"]
    ]

    assert "Memory Fact: Draft summary is stale" not in default_context_titles
    assert "Memory Fact: Draft summary is stale" in override_context_titles


def test_task_brief_uses_explicit_briefing_strategy_without_model_pack_vocabulary() -> None:
    thread_id = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
    rows = [
        _candidate(
            title="Decision: Keep rollout compact",
            object_type="Decision",
            created_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),
            thread_id=thread_id,
        ),
        _candidate(
            title="Next Action: Send the smallest handoff",
            object_type="NextAction",
            created_at=datetime(2026, 4, 14, 9, 5, tzinfo=UTC),
            thread_id=thread_id,
        ),
    ]
    store = TaskBriefStoreStub(rows)
    user_id = UUID("11111111-1111-4111-8111-111111111111")
    request = TaskBriefCompileRequestInput(
        mode="agent_handoff",
        thread_id=thread_id,
        briefing_strategy="detailed",
    )

    brief = compile_task_brief_record(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=request,
    )

    assert brief["mode"] == "agent_handoff"
    assert brief["strategy"]["briefing_strategy"] == "detailed"
    assert brief["strategy"]["token_budget"] == 216
    assert brief["strategy"]["budget_source"] == "mode_default"
    assert request.as_payload()["briefing_strategy"] == "detailed"
    assert not {"workspace_id", "pack_id", "pack_version", "model_pack_strategy"} & request.as_payload().keys()
    assert [section["section_key"] for section in brief["sections"]] == [
        "handoff_focus",
        "handoff_open_loops",
        "handoff_recent_changes",
    ]


def test_task_brief_rejects_unknown_briefing_strategy() -> None:
    store = TaskBriefStoreStub([])

    with pytest.raises(TaskBriefValidationError, match="briefing_strategy must be one of"):
        compile_task_brief_record(
            store,  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            request=TaskBriefCompileRequestInput(
                mode="user_recall",
                briefing_strategy="verbose",  # type: ignore[arg-type]
            ),
        )

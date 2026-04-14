from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from alicebot_api.contracts import TaskBriefCompileRequestInput
from alicebot_api.task_briefing import (
    compare_task_briefs,
    compile_and_persist_task_brief,
    compile_task_brief_record,
    get_persisted_task_brief,
)


class TaskBriefStoreStub:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self._task_briefs: dict[UUID, dict[str, object]] = {}
        self._visible_workspaces: set[UUID] = set()
        self._workspace_bindings: dict[UUID, dict[str, object]] = {}
        self._packs_by_id: dict[tuple[UUID, UUID], dict[str, object]] = {}
        self._packs_by_key: dict[tuple[UUID, str, str], dict[str, object]] = {}

    def list_continuity_recall_candidates(self):
        return list(self._rows)

    def add_workspace_model_pack(
        self,
        *,
        workspace_id: UUID,
        pack_row_id: UUID,
        pack_id: str,
        pack_version: str,
        briefing_strategy: str,
        briefing_max_tokens: int | None,
        bind_as_default: bool = False,
    ) -> None:
        self._visible_workspaces.add(workspace_id)
        pack = {
            "id": pack_row_id,
            "workspace_id": workspace_id,
            "created_by_user_account_id": UUID("11111111-1111-4111-8111-111111111111"),
            "pack_id": pack_id,
            "pack_version": pack_version,
            "display_name": f"{pack_id}@{pack_version}",
            "family": "custom",
            "description": "stub",
            "status": "active",
            "briefing_strategy": briefing_strategy,
            "briefing_max_tokens": briefing_max_tokens,
            "contract": {"contract_version": "model_pack_contract_v1"},
            "metadata": {},
            "created_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
        }
        self._packs_by_id[(workspace_id, pack_row_id)] = pack
        self._packs_by_key[(workspace_id, pack_id, pack_version)] = pack
        if bind_as_default:
            self._workspace_bindings[workspace_id] = {"model_pack_id": pack_row_id}

    def workspace_visible_to_user_account(self, *, workspace_id: UUID, user_account_id: UUID) -> bool:
        return workspace_id in self._visible_workspaces

    def get_latest_workspace_model_pack_binding_optional(self, *, workspace_id: UUID):
        return self._workspace_bindings.get(workspace_id)

    def get_model_pack_for_workspace_optional(self, *, workspace_id: UUID, pack_id: str, pack_version: str | None):
        if pack_version is None:
            candidates = [
                pack
                for (candidate_workspace_id, candidate_pack_id, _), pack in self._packs_by_key.items()
                if candidate_workspace_id == workspace_id and candidate_pack_id == pack_id
            ]
            if not candidates:
                return None
            return sorted(candidates, key=lambda pack: str(pack["pack_version"]), reverse=True)[0]
        return self._packs_by_key.get((workspace_id, pack_id, pack_version))

    def get_model_pack_for_workspace_by_row_id_optional(self, *, workspace_id: UUID, model_pack_id: UUID):
        return self._packs_by_id.get((workspace_id, model_pack_id))

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


def test_task_brief_uses_workspace_selected_model_pack_defaults() -> None:
    thread_id = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
    workspace_id = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
    pack_row_id = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
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
    store.add_workspace_model_pack(
        workspace_id=workspace_id,
        pack_row_id=pack_row_id,
        pack_id="compact-pack",
        pack_version="1.0.0",
        briefing_strategy="detailed",
        briefing_max_tokens=144,
        bind_as_default=True,
    )
    user_id = UUID("11111111-1111-4111-8111-111111111111")

    brief = compile_task_brief_record(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=TaskBriefCompileRequestInput(
            mode="agent_handoff",
            workspace_id=workspace_id,
            thread_id=thread_id,
        ),
    )

    assert brief["mode"] == "agent_handoff"
    assert brief["strategy"]["model_pack_strategy"] == "detailed"
    assert brief["strategy"]["token_budget"] == 144
    assert brief["strategy"]["budget_source"] == "model_pack_default"
    assert [section["section_key"] for section in brief["sections"]] == [
        "handoff_focus",
        "handoff_open_loops",
        "handoff_recent_changes",
    ]

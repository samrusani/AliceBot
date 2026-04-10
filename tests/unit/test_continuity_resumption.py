from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import ContinuityResumptionBriefRequestInput


class ContinuityResumptionStoreStub:
    def __init__(
        self,
        rows: list[dict[str, object]],
        *,
        alias_matches: dict[tuple[str, str], list[dict[str, object]]] | None = None,
    ) -> None:
        self._rows = rows
        self._alias_matches = alias_matches or {}

    def list_continuity_recall_candidates(self):
        return list(self._rows)

    def find_entity_alias_matches(self, *, entity_type: str, normalized_alias: str):
        return list(self._alias_matches.get((entity_type, normalized_alias), []))

    def get_latest_entity_merge_for_source_optional(self, source_entity_id: UUID):
        return None


def make_candidate_row(
    *,
    title: str,
    object_type: str,
    capture_created_at: datetime,
    provenance: dict[str, object] | None = None,
    confidence: float = 1.0,
    status: str = "active",
    is_searchable: bool = True,
    is_promotable: bool | None = None,
    project_entity_id: UUID | None = None,
    person_entity_id: UUID | None = None,
    topic_entity_id: UUID | None = None,
) -> dict[str, object]:
    resolved_is_promotable = (
        object_type in {"Decision", "Commitment", "WaitingFor", "Blocker", "NextAction"}
        if is_promotable is None
        else is_promotable
    )
    return {
        "id": uuid4(),
        "user_id": UUID("11111111-1111-4111-8111-111111111111"),
        "capture_event_id": uuid4(),
        "object_type": object_type,
        "status": status,
        "is_preserved": True,
        "is_searchable": is_searchable,
        "is_promotable": resolved_is_promotable,
        "title": title,
        "body": {"text": title},
        "provenance": provenance or {},
        "project_entity_id": project_entity_id,
        "person_entity_id": person_entity_id,
        "topic_entity_id": topic_entity_id,
        "confidence": confidence,
        "last_confirmed_at": None,
        "supersedes_object_id": None,
        "superseded_by_object_id": None,
        "object_created_at": capture_created_at,
        "object_updated_at": capture_created_at,
        "admission_posture": "DERIVED",
        "admission_reason": "seeded",
        "explicit_signal": None,
        "capture_created_at": capture_created_at,
    }


def test_resumption_brief_includes_required_sections_deterministically() -> None:
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    rows = [
        make_candidate_row(
            title="Decision: Freeze API contract",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
        ),
        make_candidate_row(
            title="Waiting For: Vendor quote",
            object_type="WaitingFor",
            capture_created_at=datetime(2026, 3, 29, 10, 5, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
        ),
        make_candidate_row(
            title="Next Action: Send approval email",
            object_type="NextAction",
            capture_created_at=datetime(2026, 3, 29, 10, 6, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
        ),
        make_candidate_row(
            title="Decision: Keep rollout phased",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 10, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
        ),
    ]

    payload = compile_continuity_resumption_brief(
        ContinuityResumptionStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityResumptionBriefRequestInput(
            thread_id=thread_id,
            max_recent_changes=3,
            max_open_loops=2,
        ),
    )

    brief = payload["brief"]

    assert brief["last_decision"]["item"] is not None
    assert brief["last_decision"]["item"]["title"] == "Decision: Keep rollout phased"
    assert brief["open_loops"]["summary"] == {
        "limit": 2,
        "returned_count": 1,
        "total_count": 1,
        "order": ["created_at_desc", "id_desc"],
    }
    assert [item["title"] for item in brief["open_loops"]["items"]] == [
        "Waiting For: Vendor quote",
    ]
    assert [item["title"] for item in brief["recent_changes"]["items"]] == [
        "Decision: Keep rollout phased",
        "Next Action: Send approval email",
        "Waiting For: Vendor quote",
    ]
    assert brief["next_action"]["item"] is not None
    assert brief["next_action"]["item"]["title"] == "Next Action: Send approval email"


def test_resumption_brief_uses_explicit_empty_states_when_sections_are_missing() -> None:
    task_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    rows = [
        make_candidate_row(
            title="Note: Context only",
            object_type="Note",
            capture_created_at=datetime(2026, 3, 29, 9, 0, tzinfo=UTC),
            provenance={"task_id": str(task_id)},
        ),
    ]

    payload = compile_continuity_resumption_brief(
        ContinuityResumptionStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityResumptionBriefRequestInput(
            task_id=task_id,
            max_recent_changes=2,
            max_open_loops=2,
        ),
    )

    brief = payload["brief"]

    assert brief["last_decision"] == {
        "item": None,
        "empty_state": {
            "is_empty": True,
            "message": "No decision found in the requested scope.",
        },
    }
    assert brief["open_loops"]["items"] == []
    assert brief["open_loops"]["empty_state"] == {
        "is_empty": True,
        "message": "No open loops found in the requested scope.",
    }
    assert brief["next_action"] == {
        "item": None,
        "empty_state": {
            "is_empty": True,
            "message": "No next action found in the requested scope.",
        },
    }


def test_resumption_brief_uses_full_scoped_set_instead_of_recall_limit() -> None:
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    base_time = datetime(2026, 3, 29, 8, 0, tzinfo=UTC)
    rows: list[dict[str, object]] = []

    for index in range(110):
        rows.append(
            make_candidate_row(
                title=f"Decision: historical {index}",
                object_type="Decision",
                capture_created_at=base_time + timedelta(minutes=index),
                provenance={"thread_id": str(thread_id)},
                confidence=1.0,
            )
        )

    rows.append(
        make_candidate_row(
            title="Decision: newest low confidence",
            object_type="Decision",
            capture_created_at=base_time + timedelta(minutes=200),
            provenance={"thread_id": str(thread_id)},
            confidence=0.01,
        )
    )
    rows.append(
        make_candidate_row(
            title="Next Action: newest low confidence",
            object_type="NextAction",
            capture_created_at=base_time + timedelta(minutes=201),
            provenance={"thread_id": str(thread_id)},
            confidence=0.01,
        )
    )

    payload = compile_continuity_resumption_brief(
        ContinuityResumptionStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityResumptionBriefRequestInput(
            thread_id=thread_id,
            max_recent_changes=2,
            max_open_loops=1,
        ),
    )

    brief = payload["brief"]
    assert brief["last_decision"]["item"] is not None
    assert brief["last_decision"]["item"]["title"] == "Decision: newest low confidence"
    assert brief["next_action"]["item"] is not None
    assert brief["next_action"]["item"]["title"] == "Next Action: newest low confidence"
    assert [item["title"] for item in brief["recent_changes"]["items"]] == [
        "Next Action: newest low confidence",
        "Decision: newest low confidence",
    ]


def test_resumption_brief_ignores_superseded_for_primary_sections_but_keeps_recent_changes() -> None:
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    rows = [
        make_candidate_row(
            title="Decision: superseded old decision",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
            status="superseded",
        ),
        make_candidate_row(
            title="Decision: active latest decision",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 5, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
            status="active",
        ),
    ]

    payload = compile_continuity_resumption_brief(
        ContinuityResumptionStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityResumptionBriefRequestInput(
            thread_id=thread_id,
            max_recent_changes=5,
            max_open_loops=2,
        ),
    )

    brief = payload["brief"]
    assert brief["last_decision"]["item"] is not None
    assert brief["last_decision"]["item"]["title"] == "Decision: active latest decision"
    assert [item["title"] for item in brief["recent_changes"]["items"]] == [
        "Decision: active latest decision",
        "Decision: superseded old decision",
    ]


def test_resumption_brief_excludes_completed_and_stale_from_primary_open_loop_sections() -> None:
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    rows = [
        make_candidate_row(
            title="Waiting For: completed item",
            object_type="WaitingFor",
            capture_created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
            status="completed",
        ),
        make_candidate_row(
            title="Waiting For: deferred stale item",
            object_type="WaitingFor",
            capture_created_at=datetime(2026, 3, 29, 10, 1, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
            status="stale",
        ),
        make_candidate_row(
            title="Waiting For: still blocked active item",
            object_type="WaitingFor",
            capture_created_at=datetime(2026, 3, 29, 10, 2, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
            status="active",
        ),
        make_candidate_row(
            title="Next Action: done item",
            object_type="NextAction",
            capture_created_at=datetime(2026, 3, 29, 10, 3, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
            status="completed",
        ),
    ]

    payload = compile_continuity_resumption_brief(
        ContinuityResumptionStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityResumptionBriefRequestInput(
            thread_id=thread_id,
            max_recent_changes=5,
            max_open_loops=5,
        ),
    )

    brief = payload["brief"]
    assert [item["title"] for item in brief["open_loops"]["items"]] == [
        "Waiting For: still blocked active item",
    ]
    assert brief["next_action"]["item"] is None
    assert [item["title"] for item in brief["recent_changes"]["items"]] == [
        "Next Action: done item",
        "Waiting For: still blocked active item",
        "Waiting For: deferred stale item",
        "Waiting For: completed item",
    ]


def test_resumption_brief_excludes_non_promotable_memory_facts_by_default_but_can_override() -> None:
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    rows = [
        make_candidate_row(
            title="Memory Fact: searchable but not promotable",
            object_type="MemoryFact",
            capture_created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
            is_promotable=False,
        ),
        make_candidate_row(
            title="Decision: still visible",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 5, tzinfo=UTC),
            provenance={"thread_id": str(thread_id)},
        ),
    ]

    default_payload = compile_continuity_resumption_brief(
        ContinuityResumptionStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityResumptionBriefRequestInput(
            thread_id=thread_id,
            max_recent_changes=5,
            max_open_loops=2,
        ),
    )
    override_payload = compile_continuity_resumption_brief(
        ContinuityResumptionStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityResumptionBriefRequestInput(
            thread_id=thread_id,
            max_recent_changes=5,
            max_open_loops=2,
            include_non_promotable_facts=True,
        ),
    )

    assert [item["title"] for item in default_payload["brief"]["recent_changes"]["items"]] == [
        "Decision: still visible",
    ]
    assert [item["title"] for item in override_payload["brief"]["recent_changes"]["items"]] == [
        "Decision: still visible",
        "Memory Fact: searchable but not promotable",
    ]


def test_resumption_brief_resolves_project_aliases_to_canonical_entity_scope() -> None:
    project_entity_id = UUID("12121212-1212-4121-8121-121212121212")
    rows = [
        make_candidate_row(
            title="Decision: Keep the staged launch",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
            provenance={"project": "Project Orion"},
            project_entity_id=project_entity_id,
        ),
    ]

    payload = compile_continuity_resumption_brief(
        ContinuityResumptionStoreStub(
            rows,
            alias_matches={
                ("project", "legacy project label"): [
                    {
                        "entity_id": project_entity_id,
                        "entity_type": "project",
                        "entity_name": "Project Orion",
                        "created_at": datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
                    }
                ]
            },
        ),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityResumptionBriefRequestInput(
            project="Legacy Project Label",
            max_recent_changes=3,
            max_open_loops=2,
        ),
    )

    assert payload["brief"]["last_decision"]["item"] is not None
    assert payload["brief"]["last_decision"]["item"]["title"] == "Decision: Keep the staged launch"
    assert payload["brief"]["scope"]["project_entity_id"] == str(project_entity_id)

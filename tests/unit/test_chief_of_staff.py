from __future__ import annotations

from uuid import UUID

import alicebot_api.chief_of_staff as chief
from alicebot_api.contracts import ChiefOfStaffPriorityBriefRequestInput


def _recall_item(
    *,
    item_id: str,
    object_type: str,
    status: str,
    title: str,
    created_at: str,
    confidence: float = 0.9,
    confirmation_status: str = "confirmed",
) -> dict[str, object]:
    return {
        "id": item_id,
        "capture_event_id": f"capture-{item_id}",
        "object_type": object_type,
        "status": status,
        "title": title,
        "body": {"text": title},
        "provenance": {"thread_id": "thread-1", "source_event_ids": [f"event-{item_id}"]},
        "confirmation_status": confirmation_status,
        "admission_posture": "DERIVED",
        "confidence": confidence,
        "relevance": 120.0,
        "last_confirmed_at": None,
        "supersedes_object_id": None,
        "superseded_by_object_id": None,
        "scope_matches": [{"kind": "thread", "value": "thread-1"}],
        "provenance_references": [{"source_kind": "continuity_capture_event", "source_id": f"capture-{item_id}"}],
        "ordering": {
            "scope_match_count": 1,
            "query_term_match_count": 1,
            "confirmation_rank": 3,
            "freshness_posture": "fresh",
            "freshness_rank": 4,
            "provenance_posture": "strong",
            "provenance_rank": 3,
            "supersession_posture": "current",
            "supersession_rank": 3,
            "posture_rank": 2,
            "lifecycle_rank": 4,
            "confidence": confidence,
        },
        "created_at": created_at,
        "updated_at": created_at,
    }


def test_priority_brief_is_deterministic_and_provenance_backed(monkeypatch) -> None:
    recall_items = [
        _recall_item(
            item_id="next-1",
            object_type="NextAction",
            status="active",
            title="Next Action: Send launch update",
            created_at="2026-03-31T10:05:00+00:00",
            confidence=0.98,
        ),
        _recall_item(
            item_id="commitment-1",
            object_type="Commitment",
            status="active",
            title="Commitment: Close sprint report",
            created_at="2026-03-28T09:50:00+00:00",
            confidence=0.9,
        ),
        _recall_item(
            item_id="waiting-1",
            object_type="WaitingFor",
            status="active",
            title="Waiting For: Vendor quote",
            created_at="2026-03-27T09:00:00+00:00",
            confidence=0.9,
            confirmation_status="unconfirmed",
        ),
        _recall_item(
            item_id="blocker-1",
            object_type="Blocker",
            status="active",
            title="Blocker: Missing API key",
            created_at="2026-03-23T08:30:00+00:00",
            confidence=0.95,
            confirmation_status="unconfirmed",
        ),
    ]

    def fake_recall(*args, **kwargs):
        return {
            "items": recall_items,
            "summary": {
                "query": None,
                "filters": {"thread_id": "thread-1", "since": None, "until": None},
                "limit": 100,
                "returned_count": len(recall_items),
                "total_count": len(recall_items),
                "order": ["relevance_desc", "created_at_desc", "id_desc"],
            },
        }

    def fake_open_loops(*args, **kwargs):
        return {
            "dashboard": {
                "scope": {"thread_id": "thread-1", "since": None, "until": None},
                "waiting_for": {
                    "items": [recall_items[2]],
                    "summary": {"limit": 20, "returned_count": 1, "total_count": 1, "order": ["created_at_desc", "id_desc"]},
                    "empty_state": {"is_empty": False, "message": "none"},
                },
                "blocker": {
                    "items": [recall_items[3]],
                    "summary": {"limit": 20, "returned_count": 1, "total_count": 1, "order": ["created_at_desc", "id_desc"]},
                    "empty_state": {"is_empty": False, "message": "none"},
                },
                "stale": {
                    "items": [],
                    "summary": {"limit": 20, "returned_count": 0, "total_count": 0, "order": ["created_at_desc", "id_desc"]},
                    "empty_state": {"is_empty": True, "message": "none"},
                },
                "next_action": {
                    "items": [recall_items[0]],
                    "summary": {"limit": 20, "returned_count": 1, "total_count": 1, "order": ["created_at_desc", "id_desc"]},
                    "empty_state": {"is_empty": False, "message": "none"},
                },
                "summary": {
                    "limit": 20,
                    "total_count": 3,
                    "posture_order": ["waiting_for", "blocker", "stale", "next_action"],
                    "item_order": ["created_at_desc", "id_desc"],
                },
                "sources": ["continuity_capture_events", "continuity_objects"],
            }
        }

    def fake_resumption(*args, **kwargs):
        return {
            "brief": {
                "assembly_version": "continuity_resumption_brief_v0",
                "scope": {"thread_id": "thread-1", "since": None, "until": None},
                "last_decision": {"item": None, "empty_state": {"is_empty": True, "message": "none"}},
                "open_loops": {
                    "items": [recall_items[2], recall_items[3]],
                    "summary": {"limit": 20, "returned_count": 2, "total_count": 2, "order": ["created_at_desc", "id_desc"]},
                    "empty_state": {"is_empty": False, "message": "none"},
                },
                "recent_changes": {
                    "items": [recall_items[0], recall_items[1], recall_items[2], recall_items[3]],
                    "summary": {"limit": 20, "returned_count": 4, "total_count": 4, "order": ["created_at_desc", "id_desc"]},
                    "empty_state": {"is_empty": False, "message": "none"},
                },
                "next_action": {"item": recall_items[0], "empty_state": {"is_empty": False, "message": "none"}},
                "sources": ["continuity_capture_events", "continuity_objects"],
            }
        }

    def fake_trust(*args, **kwargs):
        return {
            "dashboard": {
                "quality_gate": {"status": "healthy"},
                "retrieval_quality": {"status": "pass"},
            }
        }

    monkeypatch.setattr(chief, "query_continuity_recall", fake_recall)
    monkeypatch.setattr(chief, "compile_continuity_open_loop_dashboard", fake_open_loops)
    monkeypatch.setattr(chief, "compile_continuity_resumption_brief", fake_resumption)
    monkeypatch.setattr(chief, "get_memory_trust_dashboard_summary", fake_trust)

    request = ChiefOfStaffPriorityBriefRequestInput(thread_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"), limit=4)

    first = chief.compile_chief_of_staff_priority_brief(
        object(),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=request,
    )
    second = chief.compile_chief_of_staff_priority_brief(
        object(),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=request,
    )

    assert first == second
    assert first["brief"]["ranked_items"][0]["id"] == "next-1"
    assert first["brief"]["ranked_items"][0]["priority_posture"] == "urgent"
    assert first["brief"]["recommended_next_action"]["action_type"] == "execute_next_action"
    assert first["brief"]["recommended_next_action"]["target_priority_id"] == "next-1"
    assert first["brief"]["summary"]["trust_confidence_posture"] == "high"
    assert first["brief"]["summary"]["follow_through_posture_order"] == [
        "overdue",
        "stale_waiting_for",
        "slipped_commitment",
    ]
    assert first["brief"]["summary"]["follow_through_item_order"] == [
        "recommendation_action_desc",
        "age_hours_desc",
        "created_at_desc",
        "id_desc",
    ]
    assert first["brief"]["summary"]["follow_through_total_count"] == 3
    assert first["brief"]["summary"]["overdue_count"] == 1
    assert first["brief"]["summary"]["stale_waiting_for_count"] == 1
    assert first["brief"]["summary"]["slipped_commitment_count"] == 1
    assert first["brief"]["overdue_items"][0]["id"] == "blocker-1"
    assert first["brief"]["overdue_items"][0]["recommendation_action"] == "escalate"
    assert first["brief"]["stale_waiting_for_items"][0]["id"] == "waiting-1"
    assert first["brief"]["slipped_commitments"][0]["id"] == "commitment-1"
    assert first["brief"]["escalation_posture"]["posture"] == "critical"
    assert first["brief"]["draft_follow_up"]["status"] == "drafted"
    assert first["brief"]["draft_follow_up"]["mode"] == "draft_only"
    assert first["brief"]["draft_follow_up"]["approval_required"] is True
    assert first["brief"]["draft_follow_up"]["auto_send"] is False
    assert first["brief"]["draft_follow_up"]["target_metadata"]["continuity_object_id"] == "blocker-1"
    assert "artifact-only" in first["brief"]["draft_follow_up"]["content"]["body"]
    assert first["brief"]["ranked_items"][0]["rationale"]["provenance_references"]
    assert first["brief"]["ranked_items"][0]["rationale"]["reasons"]
    assert first["brief"]["preparation_brief"]["summary"]["order"] == [
        "rank_asc",
        "created_at_desc",
        "id_desc",
    ]
    assert first["brief"]["what_changed_summary"]["summary"]["order"] == [
        "rank_asc",
        "created_at_desc",
        "id_desc",
    ]
    assert first["brief"]["prep_checklist"]["summary"]["order"] == [
        "rank_asc",
        "created_at_desc",
        "id_desc",
    ]
    assert first["brief"]["suggested_talking_points"]["summary"]["order"] == [
        "rank_asc",
        "created_at_desc",
        "id_desc",
    ]
    assert first["brief"]["resumption_supervision"]["summary"]["order"] == [
        "rank_asc",
    ]
    assert first["brief"]["preparation_brief"]["confidence_posture"] == "high"
    assert first["brief"]["what_changed_summary"]["confidence_posture"] == "high"
    assert first["brief"]["prep_checklist"]["confidence_posture"] == "high"
    assert first["brief"]["suggested_talking_points"]["confidence_posture"] == "high"
    assert first["brief"]["resumption_supervision"]["confidence_posture"] == "high"
    assert first["brief"]["preparation_brief"]["context_items"]
    assert first["brief"]["what_changed_summary"]["items"]
    assert first["brief"]["prep_checklist"]["items"]
    assert first["brief"]["suggested_talking_points"]["items"]
    assert first["brief"]["resumption_supervision"]["recommendations"]


def test_follow_through_item_ranking_is_deterministic_for_ties() -> None:
    def _follow_item(
        *,
        item_id: str,
        recommendation_action: str,
        age_hours: float,
        created_at: str,
    ) -> dict[str, object]:
        return {
            "rank": 0,
            "id": item_id,
            "capture_event_id": f"capture-{item_id}",
            "object_type": "NextAction",
            "status": "active",
            "title": f"Next Action: {item_id}",
            "current_priority_posture": "urgent",
            "follow_through_posture": "overdue",
            "recommendation_action": recommendation_action,
            "reason": "deterministic test fixture",
            "age_hours": age_hours,
            "provenance_references": [],
            "created_at": created_at,
            "updated_at": created_at,
        }

    ranked = chief._rank_follow_through_items(  # type: ignore[attr-defined]
        [
            _follow_item(
                item_id="id-a",
                recommendation_action="nudge",
                age_hours=72.0,
                created_at="2026-03-30T10:00:00+00:00",
            ),
            _follow_item(
                item_id="id-b",
                recommendation_action="nudge",
                age_hours=72.0,
                created_at="2026-03-30T10:00:00+00:00",
            ),
            _follow_item(
                item_id="id-c",
                recommendation_action="nudge",
                age_hours=72.0,
                created_at="2026-03-31T10:00:00+00:00",
            ),
            _follow_item(
                item_id="id-d",
                recommendation_action="escalate",
                age_hours=60.0,
                created_at="2026-03-29T10:00:00+00:00",
            ),
        ],
        limit=10,
    )

    assert [item["id"] for item in ranked] == ["id-d", "id-c", "id-b", "id-a"]
    assert [item["rank"] for item in ranked] == [1, 2, 3, 4]


def test_priority_brief_downgrades_confidence_when_trust_is_weak(monkeypatch) -> None:
    recall_item = _recall_item(
        item_id="next-1",
        object_type="NextAction",
        status="active",
        title="Next Action: Ship priority brief",
        created_at="2026-03-31T10:05:00+00:00",
        confidence=0.99,
        confirmation_status="confirmed",
    )

    monkeypatch.setattr(
        chief,
        "query_continuity_recall",
        lambda *args, **kwargs: {
            "items": [recall_item],
            "summary": {
                "query": None,
                "filters": {"since": None, "until": None},
                "limit": 100,
                "returned_count": 1,
                "total_count": 1,
                "order": ["relevance_desc", "created_at_desc", "id_desc"],
            },
        },
    )
    monkeypatch.setattr(
        chief,
        "compile_continuity_open_loop_dashboard",
        lambda *args, **kwargs: {
            "dashboard": {
                "waiting_for": {"items": []},
                "blocker": {"items": []},
                "stale": {"items": []},
                "next_action": {"items": [recall_item]},
            }
        },
    )
    monkeypatch.setattr(
        chief,
        "compile_continuity_resumption_brief",
        lambda *args, **kwargs: {
            "brief": {
                "recent_changes": {"items": [recall_item]},
                "next_action": {"item": recall_item},
            }
        },
    )
    monkeypatch.setattr(
        chief,
        "get_memory_trust_dashboard_summary",
        lambda *args, **kwargs: {
            "dashboard": {
                "quality_gate": {"status": "degraded"},
                "retrieval_quality": {"status": "pass"},
            }
        },
    )

    payload = chief.compile_chief_of_staff_priority_brief(
        object(),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ChiefOfStaffPriorityBriefRequestInput(limit=1),
    )

    ranked = payload["brief"]["ranked_items"][0]
    assert payload["brief"]["summary"]["trust_confidence_posture"] == "low"
    assert ranked["confidence_posture"] == "low"
    assert ranked["rationale"]["trust_signals"]["downgraded_by_trust"] is True
    assert payload["brief"]["recommended_next_action"]["confidence_posture"] == "low"
    assert payload["brief"]["escalation_posture"]["posture"] == "watch"
    assert payload["brief"]["draft_follow_up"]["status"] == "none"
    assert payload["brief"]["preparation_brief"]["confidence_posture"] == "low"
    assert payload["brief"]["what_changed_summary"]["confidence_posture"] == "low"
    assert payload["brief"]["prep_checklist"]["confidence_posture"] == "low"
    assert payload["brief"]["suggested_talking_points"]["confidence_posture"] == "low"
    assert payload["brief"]["resumption_supervision"]["confidence_posture"] == "low"
    assert payload["brief"]["resumption_supervision"]["recommendations"][0]["action"] in {
        "execute_next_action",
        "capture_new_priority",
    }
    assert any(
        recommendation["action"] == "review_scope" and recommendation["provenance_references"]
        for recommendation in payload["brief"]["resumption_supervision"]["recommendations"]
    )


def test_priority_brief_retrieval_failure_respects_non_healthy_quality_caps(monkeypatch) -> None:
    recall_item = _recall_item(
        item_id="next-1",
        object_type="NextAction",
        status="active",
        title="Next Action: Validate confidence caps",
        created_at="2026-03-31T10:05:00+00:00",
        confidence=0.99,
        confirmation_status="confirmed",
    )

    monkeypatch.setattr(
        chief,
        "query_continuity_recall",
        lambda *args, **kwargs: {
            "items": [recall_item],
            "summary": {
                "query": None,
                "filters": {"since": None, "until": None},
                "limit": 100,
                "returned_count": 1,
                "total_count": 1,
                "order": ["relevance_desc", "created_at_desc", "id_desc"],
            },
        },
    )
    monkeypatch.setattr(
        chief,
        "compile_continuity_open_loop_dashboard",
        lambda *args, **kwargs: {
            "dashboard": {
                "waiting_for": {"items": []},
                "blocker": {"items": []},
                "stale": {"items": []},
                "next_action": {"items": [recall_item]},
            }
        },
    )
    monkeypatch.setattr(
        chief,
        "compile_continuity_resumption_brief",
        lambda *args, **kwargs: {
            "brief": {
                "recent_changes": {"items": [recall_item]},
                "next_action": {"item": recall_item},
            }
        },
    )

    def compile_with_trust_status(status: str) -> dict[str, object]:
        monkeypatch.setattr(
            chief,
            "get_memory_trust_dashboard_summary",
            lambda *args, **kwargs: {
                "dashboard": {
                    "quality_gate": {"status": status},
                    "retrieval_quality": {"status": "fail"},
                }
            },
        )
        return chief.compile_chief_of_staff_priority_brief(
            object(),  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            request=ChiefOfStaffPriorityBriefRequestInput(limit=1),
        )

    needs_review_payload = compile_with_trust_status("needs_review")
    needs_review_ranked = needs_review_payload["brief"]["ranked_items"][0]
    assert needs_review_payload["brief"]["summary"]["trust_confidence_posture"] == "medium"
    assert needs_review_ranked["confidence_posture"] == "medium"
    assert needs_review_ranked["rationale"]["trust_signals"]["retrieval_status"] == "fail"
    assert needs_review_ranked["rationale"]["trust_signals"]["trust_confidence_cap"] == "medium"
    assert "needs review" in needs_review_ranked["rationale"]["trust_signals"]["reason"]

    insufficient_sample_payload = compile_with_trust_status("insufficient_sample")
    insufficient_sample_ranked = insufficient_sample_payload["brief"]["ranked_items"][0]
    assert insufficient_sample_payload["brief"]["summary"]["trust_confidence_posture"] == "low"
    assert insufficient_sample_ranked["confidence_posture"] == "low"
    assert insufficient_sample_ranked["rationale"]["trust_signals"]["retrieval_status"] == "fail"
    assert insufficient_sample_ranked["rationale"]["trust_signals"]["trust_confidence_cap"] == "low"
    assert "weak" in insufficient_sample_ranked["rationale"]["trust_signals"]["reason"]
    assert insufficient_sample_payload["brief"]["draft_follow_up"]["status"] == "none"
    assert insufficient_sample_payload["brief"]["resumption_supervision"]["confidence_posture"] == "low"

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import alicebot_api.chief_of_staff as chief
from alicebot_api.contracts import (
    ChiefOfStaffHandoffReviewActionInput,
    ChiefOfStaffPriorityBriefRequestInput,
    ChiefOfStaffRecommendationOutcomeCaptureInput,
)


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


def _outcome_recall_item(
    *,
    item_id: str,
    created_at: str,
    outcome: str,
    recommendation_action_type: str,
    recommendation_title: str,
    target_priority_id: str | None = None,
    rationale: str | None = None,
) -> dict[str, object]:
    item = _recall_item(
        item_id=item_id,
        object_type="Note",
        status="active",
        title=f"Recommendation outcome: {outcome}",
        created_at=created_at,
        confidence=1.0,
        confirmation_status="confirmed",
    )
    item["body"] = {
        "kind": "chief_of_staff_recommendation_outcome",
        "outcome": outcome,
        "recommendation_action_type": recommendation_action_type,
        "recommendation_title": recommendation_title,
        "target_priority_id": target_priority_id,
        "rationale": rationale,
        "rewritten_title": None,
    }
    return item


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
        _outcome_recall_item(
            item_id="outcome-accept-1",
            created_at="2026-03-31T11:00:00+00:00",
            outcome="accept",
            recommendation_action_type="execute_next_action",
            recommendation_title="Next Action: Send launch update",
            target_priority_id="next-1",
            rationale="Accepted and executed directly.",
        ),
        _outcome_recall_item(
            item_id="outcome-ignore-1",
            created_at="2026-03-31T10:30:00+00:00",
            outcome="ignore",
            recommendation_action_type="follow_up_waiting_for",
            recommendation_title="Waiting For: Vendor quote",
            target_priority_id="waiting-1",
            rationale="Deferred by operator due to dependency risk.",
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

    def fake_weekly_review(*args, **kwargs):
        return {
            "review": {
                "assembly_version": "continuity_weekly_review_v0",
                "scope": {"thread_id": "thread-1", "since": None, "until": None},
                "rollup": {
                    "total_count": 3,
                    "waiting_for_count": 1,
                    "blocker_count": 1,
                    "stale_count": 0,
                    "correction_recurrence_count": 0,
                    "freshness_drift_count": 0,
                    "next_action_count": 1,
                    "posture_order": ["waiting_for", "blocker", "stale", "next_action"],
                },
                "waiting_for": {"items": [], "summary": {"limit": 5, "returned_count": 0, "total_count": 0, "order": []}, "empty_state": {"is_empty": True, "message": "none"}},
                "blocker": {"items": [], "summary": {"limit": 5, "returned_count": 0, "total_count": 0, "order": []}, "empty_state": {"is_empty": True, "message": "none"}},
                "stale": {"items": [], "summary": {"limit": 5, "returned_count": 0, "total_count": 0, "order": []}, "empty_state": {"is_empty": True, "message": "none"}},
                "next_action": {"items": [], "summary": {"limit": 5, "returned_count": 0, "total_count": 0, "order": []}, "empty_state": {"is_empty": True, "message": "none"}},
                "sources": ["continuity_capture_events", "continuity_objects"],
            }
        }

    monkeypatch.setattr(chief, "query_continuity_recall", fake_recall)
    monkeypatch.setattr(chief, "compile_continuity_open_loop_dashboard", fake_open_loops)
    monkeypatch.setattr(chief, "compile_continuity_weekly_review", fake_weekly_review)
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
    assert first["brief"]["weekly_review_brief"]["summary"]["guidance_order"] == ["close", "defer", "escalate"]
    assert first["brief"]["recommendation_outcomes"]["summary"]["total_count"] == 2
    assert first["brief"]["recommendation_outcomes"]["summary"]["outcome_counts"]["accept"] == 1
    assert first["brief"]["recommendation_outcomes"]["summary"]["outcome_counts"]["ignore"] == 1
    assert first["brief"]["priority_learning_summary"]["acceptance_rate"] == 0.5
    assert first["brief"]["priority_learning_summary"]["override_rate"] == 0.5
    assert "Prioritization is reinforcing" in first["brief"]["priority_learning_summary"]["priority_shift_explanation"]
    assert first["brief"]["pattern_drift_summary"]["posture"] == "stable"
    assert first["brief"]["action_handoff_brief"]["order"] == [
        "score_desc",
        "source_order_asc",
        "source_reference_id_asc",
    ]
    assert first["brief"]["action_handoff_brief"]["source_order"] == [
        "recommended_next_action",
        "follow_through",
        "prep_checklist",
        "weekly_review",
    ]
    assert first["brief"]["summary"]["handoff_item_count"] == len(first["brief"]["handoff_items"])
    assert first["brief"]["summary"]["handoff_item_order"] == [
        "score_desc",
        "source_order_asc",
        "source_reference_id_asc",
    ]
    assert first["brief"]["handoff_queue_summary"]["state_order"] == [
        "ready",
        "pending_approval",
        "executed",
        "stale",
        "expired",
    ]
    assert first["brief"]["handoff_queue_summary"]["item_order"] == [
        "queue_rank_asc",
        "handoff_rank_asc",
        "score_desc",
        "handoff_item_id_asc",
    ]
    assert first["brief"]["handoff_queue_summary"]["total_count"] == len(first["brief"]["handoff_items"])
    assert first["brief"]["summary"]["handoff_queue_total_count"] == len(first["brief"]["handoff_items"])
    assert first["brief"]["summary"]["handoff_queue_state_order"] == [
        "ready",
        "pending_approval",
        "executed",
        "stale",
        "expired",
    ]
    assert first["brief"]["summary"]["handoff_queue_item_order"] == [
        "queue_rank_asc",
        "handoff_rank_asc",
        "score_desc",
        "handoff_item_id_asc",
    ]
    assert first["brief"]["handoff_queue_groups"]["ready"]["summary"]["order"] == [
        "queue_rank_asc",
        "handoff_rank_asc",
        "score_desc",
        "handoff_item_id_asc",
    ]
    assert first["brief"]["handoff_review_actions"] == []
    assert first["brief"]["execution_routing_summary"]["total_handoff_count"] == len(first["brief"]["handoff_items"])
    assert first["brief"]["execution_routing_summary"]["routed_handoff_count"] == 0
    assert first["brief"]["execution_routing_summary"]["unrouted_handoff_count"] == len(
        first["brief"]["handoff_items"]
    )
    assert first["brief"]["execution_routing_summary"]["route_target_order"] == [
        "task_workflow_draft",
        "approval_workflow_draft",
        "follow_up_draft_only",
    ]
    assert first["brief"]["execution_routing_summary"]["routed_item_order"] == [
        "handoff_rank_asc",
        "handoff_item_id_asc",
    ]
    assert first["brief"]["execution_routing_summary"]["audit_order"] == [
        "created_at_desc",
        "id_desc",
    ]
    assert first["brief"]["routed_handoff_items"]
    assert first["brief"]["routed_handoff_items"][0]["routed_targets"] == []
    assert first["brief"]["routing_audit_trail"] == []
    assert first["brief"]["execution_readiness_posture"]["posture"] == "approval_required_draft_only"
    assert first["brief"]["execution_readiness_posture"]["approval_required"] is True
    assert first["brief"]["execution_readiness_posture"]["autonomous_execution"] is False
    assert first["brief"]["execution_readiness_posture"]["external_side_effects_allowed"] is False
    assert first["brief"]["execution_readiness_posture"]["approval_path_visible"] is True
    assert first["brief"]["execution_readiness_posture"]["transition_order"] == [
        "routed",
        "reaffirmed",
    ]
    assert first["brief"]["summary"]["execution_posture_order"] == ["approval_bounded_artifact_only"]
    assert [item["source_kind"] for item in first["brief"]["handoff_items"]] == [
        "recommended_next_action",
        "follow_through",
        "prep_checklist",
        "weekly_review",
    ]
    top_handoff_item = first["brief"]["handoff_items"][0]
    assert first["brief"]["task_draft"]["source_handoff_item_id"] == top_handoff_item["handoff_item_id"]
    assert first["brief"]["approval_draft"]["source_handoff_item_id"] == top_handoff_item["handoff_item_id"]
    assert first["brief"]["task_draft"]["mode"] == "governed_request_draft"
    assert first["brief"]["task_draft"]["approval_required"] is True
    assert first["brief"]["task_draft"]["auto_execute"] is False
    assert first["brief"]["approval_draft"]["mode"] == "approval_request_draft"
    assert first["brief"]["approval_draft"]["decision"] == "approval_required"
    assert first["brief"]["approval_draft"]["approval_required"] is True
    assert first["brief"]["approval_draft"]["auto_submit"] is False
    assert first["brief"]["execution_posture"]["posture"] == "approval_bounded_artifact_only"
    assert first["brief"]["execution_posture"]["approval_required"] is True
    assert first["brief"]["execution_posture"]["autonomous_execution"] is False
    assert first["brief"]["execution_posture"]["external_side_effects_allowed"] is False
    assert first["brief"]["execution_posture"]["default_routing_decision"] == "approval_required"
    assert "No task, approval, connector send, or external side effect is executed" in first["brief"][
        "execution_posture"
    ]["non_autonomous_guarantee"]


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
        "compile_continuity_weekly_review",
        lambda *args, **kwargs: {
            "review": {
                "scope": {"thread_id": None, "since": None, "until": None},
                "rollup": {
                    "total_count": 0,
                    "waiting_for_count": 0,
                    "blocker_count": 0,
                    "stale_count": 0,
                    "correction_recurrence_count": 0,
                    "freshness_drift_count": 0,
                    "next_action_count": 0,
                    "posture_order": ["waiting_for", "blocker", "stale", "next_action"],
                },
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
    assert payload["brief"]["action_handoff_brief"]["confidence_posture"] == "low"
    assert payload["brief"]["handoff_items"]
    assert payload["brief"]["task_draft"]["approval_required"] is True
    assert payload["brief"]["task_draft"]["auto_execute"] is False
    assert payload["brief"]["approval_draft"]["decision"] == "approval_required"
    assert payload["brief"]["approval_draft"]["auto_submit"] is False
    assert payload["brief"]["execution_posture"]["autonomous_execution"] is False
    assert payload["brief"]["execution_posture"]["external_side_effects_allowed"] is False
    assert payload["brief"]["execution_routing_summary"]["routed_handoff_count"] == 0
    assert payload["brief"]["routing_audit_trail"] == []
    assert payload["brief"]["execution_readiness_posture"]["approval_required"] is True


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
    monkeypatch.setattr(
        chief,
        "compile_continuity_weekly_review",
        lambda *args, **kwargs: {
            "review": {
                "scope": {"thread_id": None, "since": None, "until": None},
                "rollup": {
                    "total_count": 0,
                    "waiting_for_count": 0,
                    "blocker_count": 0,
                    "stale_count": 0,
                    "correction_recurrence_count": 0,
                    "freshness_drift_count": 0,
                    "next_action_count": 0,
                    "posture_order": ["waiting_for", "blocker", "stale", "next_action"],
                },
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


def test_capture_handoff_review_action_records_transition_and_returns_updated_queue(monkeypatch) -> None:
    class _FakeStore:
        def __init__(self) -> None:
            self.capture_event_payloads: list[dict[str, object]] = []
            self.object_payloads: list[dict[str, object]] = []

        def create_continuity_capture_event(
            self,
            *,
            raw_content: str,
            explicit_signal: str,
            admission_posture: str,
            admission_reason: str,
        ) -> dict[str, object]:
            self.capture_event_payloads.append(
                {
                    "raw_content": raw_content,
                    "explicit_signal": explicit_signal,
                    "admission_posture": admission_posture,
                    "admission_reason": admission_reason,
                }
            )
            return {"id": UUID("11111111-1111-4111-8111-111111111111")}

        def create_continuity_object(
            self,
            *,
            capture_event_id: UUID,
            object_type: str,
            status: str,
            title: str,
            body: dict[str, object],
            provenance: dict[str, object],
            confidence: float,
        ) -> dict[str, object]:
            self.object_payloads.append(
                {
                    "capture_event_id": capture_event_id,
                    "object_type": object_type,
                    "status": status,
                    "title": title,
                    "body": body,
                    "provenance": provenance,
                    "confidence": confidence,
                }
            )
            return {
                "id": UUID("22222222-2222-4222-8222-222222222222"),
                "capture_event_id": capture_event_id,
                "created_at": datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
                "updated_at": datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
            }

    first_brief = {
        "handoff_queue_groups": {
            "ready": {
                "items": [
                    {
                        "handoff_item_id": "handoff-1",
                        "lifecycle_state": "ready",
                    }
                ]
            },
            "pending_approval": {"items": []},
            "executed": {"items": []},
            "stale": {"items": []},
            "expired": {"items": []},
        }
    }
    second_brief = {
        "handoff_queue_summary": {
            "total_count": 1,
            "ready_count": 0,
            "pending_approval_count": 0,
            "executed_count": 0,
            "stale_count": 1,
            "expired_count": 0,
            "state_order": ["ready", "pending_approval", "executed", "stale", "expired"],
            "group_order": ["ready", "pending_approval", "executed", "stale", "expired"],
            "item_order": ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
            "review_action_order": ["mark_ready", "mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"],
        },
        "handoff_queue_groups": {
            "ready": {"items": []},
            "pending_approval": {"items": []},
            "executed": {"items": []},
            "stale": {
                "items": [
                    {
                        "handoff_item_id": "handoff-1",
                        "lifecycle_state": "stale",
                    }
                ]
            },
            "expired": {"items": []},
        },
        "handoff_review_actions": [],
    }

    compile_calls = {"count": 0}

    def fake_compile(*args, **kwargs):
        compile_calls["count"] += 1
        if compile_calls["count"] == 1:
            return {"brief": first_brief}
        return {"brief": second_brief}

    monkeypatch.setattr(chief, "compile_chief_of_staff_priority_brief", fake_compile)

    store = _FakeStore()
    response = chief.capture_chief_of_staff_handoff_review_action(
        store,  # type: ignore[arg-type]
        user_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        request=ChiefOfStaffHandoffReviewActionInput(
            handoff_item_id="handoff-1",
            review_action="mark_stale",
            thread_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        ),
    )

    assert compile_calls["count"] == 2
    assert store.capture_event_payloads
    assert store.object_payloads
    assert store.object_payloads[0]["body"]["kind"] == "chief_of_staff_handoff_review_action"
    assert response["review_action"]["handoff_item_id"] == "handoff-1"
    assert response["review_action"]["review_action"] == "mark_stale"
    assert response["review_action"]["previous_lifecycle_state"] == "ready"
    assert response["review_action"]["next_lifecycle_state"] == "stale"
    assert response["handoff_queue_summary"]["stale_count"] == 1


def test_capture_execution_routing_action_records_transition_and_returns_updated_routing(monkeypatch) -> None:
    class _FakeStore:
        def __init__(self) -> None:
            self.capture_event_payloads: list[dict[str, object]] = []
            self.object_payloads: list[dict[str, object]] = []

        def create_continuity_capture_event(
            self,
            *,
            raw_content: str,
            explicit_signal: str,
            admission_posture: str,
            admission_reason: str,
        ) -> dict[str, object]:
            self.capture_event_payloads.append(
                {
                    "raw_content": raw_content,
                    "explicit_signal": explicit_signal,
                    "admission_posture": admission_posture,
                    "admission_reason": admission_reason,
                }
            )
            return {"id": UUID("11111111-1111-4111-8111-111111111111")}

        def create_continuity_object(
            self,
            *,
            capture_event_id: UUID,
            object_type: str,
            status: str,
            title: str,
            body: dict[str, object],
            provenance: dict[str, object],
            confidence: float,
        ) -> dict[str, object]:
            self.object_payloads.append(
                {
                    "capture_event_id": capture_event_id,
                    "object_type": object_type,
                    "status": status,
                    "title": title,
                    "body": body,
                    "provenance": provenance,
                    "confidence": confidence,
                }
            )
            return {
                "id": UUID("33333333-3333-4333-8333-333333333333"),
                "capture_event_id": capture_event_id,
                "created_at": datetime(2026, 4, 1, 9, 30, tzinfo=UTC),
                "updated_at": datetime(2026, 4, 1, 9, 30, tzinfo=UTC),
            }

    first_brief = {
        "routed_handoff_items": [
            {
                "handoff_rank": 1,
                "handoff_item_id": "handoff-1",
                "title": "Next Action: Ship dashboard",
                "source_kind": "recommended_next_action",
                "recommendation_action": "execute_next_action",
                "route_target_order": ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"],
                "available_route_targets": ["task_workflow_draft", "approval_workflow_draft"],
                "routed_targets": [],
                "is_routed": False,
                "task_workflow_draft_routed": False,
                "approval_workflow_draft_routed": False,
                "follow_up_draft_only_routed": False,
                "follow_up_draft_only_applicable": False,
                "task_draft": {
                    "status": "draft",
                    "mode": "governed_request_draft",
                    "approval_required": True,
                    "auto_execute": False,
                    "source_handoff_item_id": "handoff-1",
                    "title": "Next Action: Ship dashboard",
                    "summary": "Draft-only governed request.",
                    "target": {"thread_id": "thread-1", "task_id": None, "project": None, "person": None},
                    "request": {
                        "action": "execute_next_action",
                        "scope": "chief_of_staff_priority",
                        "domain_hint": "planning",
                        "risk_hint": "governed_handoff",
                        "attributes": {"handoff_item_id": "handoff-1"},
                    },
                    "rationale": "deterministic fixture",
                    "provenance_references": [],
                },
                "approval_draft": {
                    "status": "draft_only",
                    "mode": "approval_request_draft",
                    "decision": "approval_required",
                    "approval_required": True,
                    "auto_submit": False,
                    "source_handoff_item_id": "handoff-1",
                    "request": {
                        "action": "execute_next_action",
                        "scope": "chief_of_staff_priority",
                        "domain_hint": "planning",
                        "risk_hint": "governed_handoff",
                        "attributes": {"handoff_item_id": "handoff-1"},
                    },
                    "reason": "approval required",
                    "required_checks": ["operator_review_handoff_artifact"],
                    "provenance_references": [],
                },
                "last_routing_transition": None,
            }
        ]
    }
    second_brief = {
        "execution_routing_summary": {
            "total_handoff_count": 1,
            "routed_handoff_count": 1,
            "unrouted_handoff_count": 0,
            "task_workflow_draft_count": 1,
            "approval_workflow_draft_count": 0,
            "follow_up_draft_only_count": 0,
            "route_target_order": ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"],
            "routed_item_order": ["handoff_rank_asc", "handoff_item_id_asc"],
            "audit_order": ["created_at_desc", "id_desc"],
            "transition_order": ["routed", "reaffirmed"],
            "approval_required": True,
            "non_autonomous_guarantee": "No task, approval, connector send, or external side effect is executed by this endpoint.",
            "reason": "Routing transitions are explicit and auditable.",
        },
        "routed_handoff_items": [
            {
                **first_brief["routed_handoff_items"][0],
                "routed_targets": ["task_workflow_draft"],
                "is_routed": True,
                "task_workflow_draft_routed": True,
                "last_routing_transition": {
                    "id": "route-1",
                    "capture_event_id": "capture-route-1",
                    "handoff_item_id": "handoff-1",
                    "route_target": "task_workflow_draft",
                    "transition": "routed",
                    "previously_routed": False,
                    "route_state": True,
                    "reason": "Operator routed handoff.",
                    "note": None,
                    "provenance_references": [],
                    "created_at": "2026-04-01T09:30:00+00:00",
                    "updated_at": "2026-04-01T09:30:00+00:00",
                },
            }
        ],
        "routing_audit_trail": [],
        "execution_readiness_posture": {
            "posture": "approval_required_draft_only",
            "approval_required": True,
            "autonomous_execution": False,
            "external_side_effects_allowed": False,
            "approval_path_visible": True,
            "route_target_order": ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"],
            "required_route_targets": ["task_workflow_draft", "approval_workflow_draft"],
            "transition_order": ["routed", "reaffirmed"],
            "non_autonomous_guarantee": "No task, approval, connector send, or external side effect is executed by this endpoint.",
            "reason": "draft-only",
        },
    }

    compile_calls = {"count": 0}

    def fake_compile(*args, **kwargs):
        compile_calls["count"] += 1
        if compile_calls["count"] == 1:
            return {"brief": first_brief}
        return {"brief": second_brief}

    monkeypatch.setattr(chief, "compile_chief_of_staff_priority_brief", fake_compile)

    store = _FakeStore()
    response = chief.capture_chief_of_staff_execution_routing_action(
        store,  # type: ignore[arg-type]
        user_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        request=chief.ChiefOfStaffExecutionRoutingActionInput(
            handoff_item_id="handoff-1",
            route_target="task_workflow_draft",
            thread_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        ),
    )

    assert compile_calls["count"] == 2
    assert store.capture_event_payloads
    assert store.object_payloads
    assert store.object_payloads[0]["body"]["kind"] == "chief_of_staff_execution_routing_action"
    assert response["routing_action"]["handoff_item_id"] == "handoff-1"
    assert response["routing_action"]["route_target"] == "task_workflow_draft"
    assert response["routing_action"]["transition"] == "routed"
    assert response["execution_routing_summary"]["routed_handoff_count"] == 1
    assert response["routed_handoff_items"][0]["task_workflow_draft_routed"] is True
    assert response["execution_readiness_posture"]["approval_required"] is True


def test_governed_handoff_state_maps_keep_executed_over_pending() -> None:
    class _FakeStore:
        def list_approvals(self) -> list[dict[str, object]]:
            return [
                {
                    "status": "pending",
                    "request": {"attributes": {"handoff_item_id": "handoff-executed"}},
                },
                {
                    "status": "pending",
                    "request": {"attributes": {"handoff_item_id": "handoff-pending"}},
                },
            ]

        def list_tasks(self) -> list[dict[str, object]]:
            return [
                {
                    "status": "executed",
                    "request": {"attributes": {"handoff_item_id": "handoff-executed"}},
                },
                {
                    "status": "pending_approval",
                    "request": {"attributes": {"handoff_item_id": "handoff-pending-from-task"}},
                },
            ]

    pending_ids, executed_ids = chief._build_governed_handoff_state_maps(  # type: ignore[attr-defined]
        store=_FakeStore(),  # type: ignore[arg-type]
    )

    assert executed_ids == {"handoff-executed"}
    assert pending_ids == {"handoff-pending", "handoff-pending-from-task"}
    assert "handoff-executed" not in pending_ids


def test_handoff_queue_infers_deterministic_governed_and_age_based_states() -> None:
    class _FakeStore:
        def list_approvals(self) -> list[dict[str, object]]:
            return [
                {
                    "status": "pending",
                    "request": {"attributes": {"handoff_item_id": "handoff-pending"}},
                }
            ]

        def list_tasks(self) -> list[dict[str, object]]:
            return [
                {
                    "status": "executed",
                    "request": {"attributes": {"handoff_item_id": "handoff-executed"}},
                }
            ]

    handoff_items = [
        {
            "rank": 5,
            "handoff_item_id": "handoff-ready",
            "source_kind": "recommended_next_action",
            "source_reference_id": "source-latest",
            "title": "Next Action: Ready",
            "recommendation_action": "execute_next_action",
            "priority_posture": "urgent",
            "confidence_posture": "high",
            "score": 1500.0,
            "provenance_references": [],
        },
        {
            "rank": 1,
            "handoff_item_id": "handoff-pending",
            "source_kind": "recommended_next_action",
            "source_reference_id": "source-pending",
            "title": "Next Action: Pending",
            "recommendation_action": "execute_next_action",
            "priority_posture": "urgent",
            "confidence_posture": "high",
            "score": 1400.0,
            "provenance_references": [],
        },
        {
            "rank": 2,
            "handoff_item_id": "handoff-executed",
            "source_kind": "recommended_next_action",
            "source_reference_id": "source-executed",
            "title": "Next Action: Executed",
            "recommendation_action": "execute_next_action",
            "priority_posture": "urgent",
            "confidence_posture": "high",
            "score": 1300.0,
            "provenance_references": [],
        },
        {
            "rank": 3,
            "handoff_item_id": "handoff-stale",
            "source_kind": "recommended_next_action",
            "source_reference_id": "source-stale",
            "title": "Next Action: Stale",
            "recommendation_action": "execute_next_action",
            "priority_posture": "high",
            "confidence_posture": "medium",
            "score": 1200.0,
            "provenance_references": [],
        },
        {
            "rank": 4,
            "handoff_item_id": "handoff-expired",
            "source_kind": "recommended_next_action",
            "source_reference_id": "source-expired",
            "title": "Next Action: Expired",
            "recommendation_action": "execute_next_action",
            "priority_posture": "high",
            "confidence_posture": "medium",
            "score": 1100.0,
            "provenance_references": [],
        },
    ]
    recall_items = [
        _recall_item(
            item_id="source-latest",
            object_type="NextAction",
            status="active",
            title="Latest source",
            created_at="2026-04-01T12:00:00+00:00",
        ),
        _recall_item(
            item_id="source-pending",
            object_type="NextAction",
            status="active",
            title="Pending source",
            created_at="2026-04-01T11:00:00+00:00",
        ),
        _recall_item(
            item_id="source-executed",
            object_type="NextAction",
            status="active",
            title="Executed source",
            created_at="2026-04-01T10:00:00+00:00",
        ),
        _recall_item(
            item_id="source-stale",
            object_type="NextAction",
            status="active",
            title="Stale source",
            created_at="2026-03-27T11:00:00+00:00",
        ),
        _recall_item(
            item_id="source-expired",
            object_type="NextAction",
            status="active",
            title="Expired source",
            created_at="2026-03-18T11:00:00+00:00",
        ),
    ]

    summary, groups = chief._build_handoff_queue(  # type: ignore[attr-defined]
        store=_FakeStore(),  # type: ignore[arg-type]
        handoff_items=handoff_items,  # type: ignore[arg-type]
        recall_items=recall_items,  # type: ignore[arg-type]
        all_follow_through_items=[],
        handoff_review_actions=[],
    )

    assert summary["total_count"] == 5
    assert summary["ready_count"] == 1
    assert summary["pending_approval_count"] == 1
    assert summary["executed_count"] == 1
    assert summary["stale_count"] == 1
    assert summary["expired_count"] == 1
    assert groups["ready"]["items"][0]["handoff_item_id"] == "handoff-ready"
    assert groups["pending_approval"]["items"][0]["handoff_item_id"] == "handoff-pending"
    assert groups["executed"]["items"][0]["handoff_item_id"] == "handoff-executed"
    assert groups["stale"]["items"][0]["handoff_item_id"] == "handoff-stale"
    assert groups["expired"]["items"][0]["handoff_item_id"] == "handoff-expired"
    assert groups["ready"]["items"][0]["queue_rank"] == 1
    assert groups["pending_approval"]["items"][0]["queue_rank"] == 2
    assert groups["executed"]["items"][0]["queue_rank"] == 3
    assert groups["stale"]["items"][0]["queue_rank"] == 4
    assert groups["expired"]["items"][0]["queue_rank"] == 5
    assert groups["ready"]["items"][0]["lifecycle_state"] == "ready"
    assert groups["pending_approval"]["items"][0]["lifecycle_state"] == "pending_approval"
    assert groups["executed"]["items"][0]["lifecycle_state"] == "executed"
    assert groups["stale"]["items"][0]["lifecycle_state"] == "stale"
    assert groups["expired"]["items"][0]["lifecycle_state"] == "expired"
    assert "mark_ready" not in groups["ready"]["items"][0]["available_review_actions"]
    assert "mark_pending_approval" not in groups["pending_approval"]["items"][0]["available_review_actions"]
    assert "mark_executed" not in groups["executed"]["items"][0]["available_review_actions"]
    assert "mark_stale" not in groups["stale"]["items"][0]["available_review_actions"]
    assert "mark_expired" not in groups["expired"]["items"][0]["available_review_actions"]


def test_capture_recommendation_outcome_creates_auditable_note_and_returns_learning(monkeypatch) -> None:
    class _FakeStore:
        def __init__(self) -> None:
            self.capture_event_payloads: list[dict[str, object]] = []
            self.object_payloads: list[dict[str, object]] = []

        def create_continuity_capture_event(
            self,
            *,
            raw_content: str,
            explicit_signal: str,
            admission_posture: str,
            admission_reason: str,
        ) -> dict[str, object]:
            self.capture_event_payloads.append(
                {
                    "raw_content": raw_content,
                    "explicit_signal": explicit_signal,
                    "admission_posture": admission_posture,
                    "admission_reason": admission_reason,
                }
            )
            return {"id": UUID("11111111-1111-4111-8111-111111111111")}

        def create_continuity_object(
            self,
            *,
            capture_event_id: UUID,
            object_type: str,
            status: str,
            title: str,
            body: dict[str, object],
            provenance: dict[str, object],
            confidence: float,
        ) -> dict[str, object]:
            self.object_payloads.append(
                {
                    "capture_event_id": capture_event_id,
                    "object_type": object_type,
                    "status": status,
                    "title": title,
                    "body": body,
                    "provenance": provenance,
                    "confidence": confidence,
                }
            )
            return {
                "id": UUID("22222222-2222-4222-8222-222222222222"),
                "capture_event_id": capture_event_id,
                "created_at": datetime(2026, 3, 31, 12, 0, tzinfo=UTC),
                "updated_at": datetime(2026, 3, 31, 12, 0, tzinfo=UTC),
            }

    monkeypatch.setattr(
        chief,
        "compile_chief_of_staff_priority_brief",
        lambda *args, **kwargs: {
            "brief": {
                "recommendation_outcomes": {
                    "items": [],
                    "summary": {
                        "returned_count": 0,
                        "total_count": 1,
                        "outcome_counts": {"accept": 1, "defer": 0, "ignore": 0, "rewrite": 0},
                        "order": ["created_at_desc", "id_desc"],
                    },
                },
                "priority_learning_summary": {
                    "total_count": 1,
                    "accept_count": 1,
                    "defer_count": 0,
                    "ignore_count": 0,
                    "rewrite_count": 0,
                    "acceptance_rate": 1.0,
                    "override_rate": 0.0,
                    "defer_hotspots": [],
                    "ignore_hotspots": [],
                    "priority_shift_explanation": "Prioritization is reinforcing currently accepted recommendation patterns while tracking defer/override hotspots.",
                    "hotspot_order": ["count_desc", "key_asc"],
                },
                "pattern_drift_summary": {
                    "posture": "improving",
                    "reason": "Accepted outcomes are leading with bounded defers/overrides, indicating improving recommendation fit.",
                    "supporting_signals": [],
                },
            }
        },
    )

    store = _FakeStore()
    response = chief.capture_chief_of_staff_recommendation_outcome(
        store,  # type: ignore[arg-type]
        user_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        request=ChiefOfStaffRecommendationOutcomeCaptureInput(
            outcome="accept",
            recommendation_action_type="execute_next_action",
            recommendation_title="Next Action: Ship dashboard",
            rationale="Accepted in weekly review.",
            target_priority_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            thread_id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        ),
    )

    assert store.capture_event_payloads
    assert store.object_payloads
    assert store.object_payloads[0]["object_type"] == "Note"
    assert store.object_payloads[0]["body"]["kind"] == "chief_of_staff_recommendation_outcome"
    assert response["outcome"]["outcome"] == "accept"
    assert response["outcome"]["recommendation_action_type"] == "execute_next_action"
    assert response["recommendation_outcomes"]["summary"]["outcome_counts"]["accept"] == 1
    assert response["priority_learning_summary"]["acceptance_rate"] == 1.0
    assert response["pattern_drift_summary"]["posture"] == "improving"

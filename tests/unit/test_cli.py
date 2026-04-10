from __future__ import annotations

from uuid import UUID, uuid4

import alicebot_api.cli as cli_module
from alicebot_api.config import Settings
from alicebot_api.contracts import ContinuityRecallResponse


def test_parser_routes_required_commands() -> None:
    parser = cli_module.build_parser()
    continuity_object_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    cases = [
        (["capture", "Decision: Keep rollout phased"], "_run_capture"),
        (["recall"], "_run_recall"),
        (["state-at", continuity_object_id], "_run_state_at"),
        (["timeline", continuity_object_id], "_run_timeline"),
        (["lifecycle", "list"], "_run_lifecycle_list"),
        (["lifecycle", "show", continuity_object_id], "_run_lifecycle_show"),
        (["resume"], "_run_resume"),
        (["open-loops"], "_run_open_loops"),
        (["review", "queue"], "_run_review_queue"),
        (["review", "show", continuity_object_id], "_run_review_show"),
        (["review", "apply", continuity_object_id, "--action", "confirm"], "_run_review_apply"),
        (["explain", continuity_object_id], "_run_explain"),
        (["explain", "--entity-id", continuity_object_id], "_run_explain"),
        (["evidence", "artifact", continuity_object_id], "_run_evidence_artifact"),
        (["patterns", "list"], "_run_pattern_list"),
        (["patterns", "explain", continuity_object_id], "_run_pattern_explain"),
        (["playbooks", "list"], "_run_playbook_list"),
        (["playbooks", "explain", continuity_object_id], "_run_playbook_explain"),
        (["status"], "_run_status"),
    ]

    for argv, expected_handler_name in cases:
        parsed = parser.parse_args(argv)
        assert parsed.handler.__name__ == expected_handler_name


def test_resolve_user_id_prefers_flag_then_settings_then_env_then_default(monkeypatch) -> None:
    flag_user_id = UUID("11111111-1111-4111-8111-111111111111")
    configured_user_id = UUID("22222222-2222-4222-8222-222222222222")
    env_user_id = UUID("33333333-3333-4333-8333-333333333333")

    settings_without_auth = Settings(auth_user_id="")
    settings_with_auth = Settings(auth_user_id=str(configured_user_id))

    monkeypatch.setenv("ALICEBOT_AUTH_USER_ID", str(env_user_id))
    assert cli_module._resolve_user_id(settings_without_auth, str(flag_user_id)) == flag_user_id
    assert cli_module._resolve_user_id(settings_with_auth, None) == configured_user_id
    assert cli_module._resolve_user_id(settings_without_auth, None) == env_user_id

    monkeypatch.delenv("ALICEBOT_AUTH_USER_ID")
    assert cli_module._resolve_user_id(settings_without_auth, None) == UUID(cli_module.DEFAULT_CLI_USER_ID)


def test_main_returns_error_for_non_object_json_on_review_apply(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli_module,
        "get_settings",
        lambda: Settings(database_url="postgresql://db", auth_user_id=str(uuid4())),
    )

    exit_code = cli_module.main(
        [
            "review",
            "apply",
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "--action",
            "edit",
            "--body-json",
            "[]",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "error: --body-json must be a JSON object" in captured.err


def test_recall_formatting_is_deterministic() -> None:
    payload: ContinuityRecallResponse = {
        "items": [
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "capture_event_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "object_type": "Decision",
                "status": "active",
                "lifecycle": {
                    "is_preserved": True,
                    "preservation_status": "preserved",
                    "is_searchable": True,
                    "searchability_status": "searchable",
                    "is_promotable": True,
                    "promotion_status": "promotable",
                },
                "title": "Decision: Keep rollout phased",
                "body": {"decision_text": "Keep rollout phased"},
                "provenance": {"thread_id": "thread-1"},
                "confirmation_status": "confirmed",
                "admission_posture": "DERIVED",
                "confidence": 0.95,
                "relevance": 1.0,
                "last_confirmed_at": "2026-03-30T10:00:00+00:00",
                "supersedes_object_id": None,
                "superseded_by_object_id": None,
                "scope_matches": [{"kind": "thread", "value": "thread-1"}],
                "provenance_references": [
                    {"source_kind": "continuity_capture_event", "source_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"},
                    {"source_kind": "thread", "source_id": "thread-1"},
                ],
                "ordering": {
                    "scope_match_count": 1,
                    "query_term_match_count": 2,
                    "confirmation_rank": 3,
                    "freshness_posture": "fresh",
                    "freshness_rank": 4,
                    "provenance_posture": "strong",
                    "provenance_rank": 3,
                    "supersession_posture": "current",
                    "supersession_rank": 3,
                    "posture_rank": 2,
                    "lifecycle_rank": 4,
                    "confidence": 0.95,
                },
                "explanation": {
                    "source_facts": [
                        {"kind": "capture_event", "label": "raw_content", "value": "Decision: Keep rollout phased"},
                        {"kind": "body", "label": "decision_text", "value": "Keep rollout phased"},
                    ],
                    "trust": {
                        "trust_class": "human_curated",
                        "trust_reason": "Inferred from confirmation or correction history.",
                        "confirmation_status": "confirmed",
                        "confidence": 0.95,
                        "provenance_posture": "strong",
                        "evidence_segment_count": 1,
                        "correction_count": 0,
                    },
                    "evidence_segments": [
                        {
                            "relationship": "captured_from",
                            "source_kind": "continuity_capture_event",
                            "source_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                            "display_name": "capture event",
                            "relative_path": None,
                            "segment_kind": "capture_event",
                            "locator": None,
                            "snippet": "Decision: Keep rollout phased",
                            "created_at": "2026-03-30T09:58:00+00:00",
                        }
                    ],
                    "supersession_notes": [],
                    "timestamps": {
                        "capture_created_at": "2026-03-30T09:58:00+00:00",
                        "created_at": "2026-03-30T09:59:00+00:00",
                        "updated_at": "2026-03-30T10:00:00+00:00",
                        "last_confirmed_at": "2026-03-30T10:00:00+00:00",
                    },
                },
                "created_at": "2026-03-30T09:59:00+00:00",
                "updated_at": "2026-03-30T10:00:00+00:00",
            }
        ],
        "summary": {
            "query": "rollout",
            "filters": {"thread_id": "thread-1", "since": None, "until": None},
            "limit": 20,
            "returned_count": 1,
            "total_count": 1,
            "order": ["relevance_desc", "created_at_desc", "id_desc"],
        },
    }

    rendered = cli_module.format_recall_output(payload)

    assert rendered == (
        "recall summary\n"
        "query: rollout\n"
        "filters: thread_id=thread-1\n"
        "returned: 1/1 (limit=20)\n"
        "order: relevance_desc, created_at_desc, id_desc\n"
        "items:\n"
        "  1. [Decision|active] Decision: Keep rollout phased\n"
        "    id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa capture_event_id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb\n"
        "    lifecycle=preserved:True searchable:True promotable:True\n"
        "    confidence=0.950 relevance=1.000 confirmation=confirmed\n"
        "    freshness=fresh provenance=strong supersession=current\n"
        "    source=(unknown)\n"
        "    provenance_refs=continuity_capture_event:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb; thread:thread-1\n"
        "    trust=human_curated reason=Inferred from confirmation or correction history. evidence_segments=1 corrections=0\n"
        "    timestamps=capture_created_at=2026-03-30T09:58:00+00:00 created_at=2026-03-30T09:59:00+00:00 updated_at=2026-03-30T10:00:00+00:00 last_confirmed_at=2026-03-30T10:00:00+00:00\n"
        "    source_facts=raw_content=Decision: Keep rollout phased | decision_text=Keep rollout phased\n"
        "    evidence_segments=continuity_capture_event:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb \"Decision: Keep rollout phased\"\n"
        "    supersession_notes=(none)"
    )


def test_status_command_returns_unreachable_without_db_connection(monkeypatch, capsys) -> None:
    user_id = UUID("44444444-4444-4444-8444-444444444444")
    monkeypatch.setattr(
        cli_module,
        "get_settings",
        lambda: Settings(
            database_url="postgresql://db",
            healthcheck_timeout_seconds=2,
            auth_user_id=str(user_id),
        ),
    )
    monkeypatch.setattr(cli_module, "ping_database", lambda *_args, **_kwargs: False)

    exit_code = cli_module.main(["status"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "database: unreachable" in captured.out
    assert f"user_id: {user_id}" in captured.out


def test_recall_formatting_renders_provenance_source_label_when_present() -> None:
    payload: ContinuityRecallResponse = {
        "items": [
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "capture_event_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "object_type": "Decision",
                "status": "active",
                "lifecycle": {
                    "is_preserved": True,
                    "preservation_status": "preserved",
                    "is_searchable": True,
                    "searchability_status": "searchable",
                    "is_promotable": True,
                    "promotion_status": "promotable",
                },
                "title": "Decision: Keep rollout phased",
                "body": {"decision_text": "Keep rollout phased"},
                "provenance": {"source_kind": "openclaw_import", "source_label": "OpenClaw"},
                "confirmation_status": "confirmed",
                "admission_posture": "DERIVED",
                "confidence": 0.95,
                "relevance": 1.0,
                "last_confirmed_at": "2026-03-30T10:00:00+00:00",
                "supersedes_object_id": None,
                "superseded_by_object_id": None,
                "scope_matches": [],
                "provenance_references": [
                    {"source_kind": "continuity_capture_event", "source_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}
                ],
                "ordering": {
                    "scope_match_count": 0,
                    "query_term_match_count": 0,
                    "confirmation_rank": 3,
                    "freshness_posture": "fresh",
                    "freshness_rank": 4,
                    "provenance_posture": "strong",
                    "provenance_rank": 3,
                    "supersession_posture": "current",
                    "supersession_rank": 3,
                    "posture_rank": 2,
                    "lifecycle_rank": 4,
                    "confidence": 0.95,
                },
                "explanation": {
                    "source_facts": [],
                    "trust": {
                        "trust_class": "llm_single_source",
                        "trust_reason": "Inferred from a single capture or provenance chain.",
                        "confirmation_status": "confirmed",
                        "confidence": 0.95,
                        "provenance_posture": "strong",
                        "evidence_segment_count": 1,
                        "correction_count": 0,
                    },
                    "evidence_segments": [
                        {
                            "relationship": "captured_from",
                            "source_kind": "continuity_capture_event",
                            "source_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                            "display_name": "capture event",
                            "relative_path": None,
                            "segment_kind": "capture_event",
                            "locator": None,
                            "snippet": "Decision: Keep rollout phased",
                            "created_at": "2026-03-30T09:58:00+00:00",
                        }
                    ],
                    "supersession_notes": [],
                    "timestamps": {
                        "capture_created_at": "2026-03-30T09:58:00+00:00",
                        "created_at": "2026-03-30T09:59:00+00:00",
                        "updated_at": "2026-03-30T10:00:00+00:00",
                        "last_confirmed_at": "2026-03-30T10:00:00+00:00",
                    },
                },
                "created_at": "2026-03-30T09:59:00+00:00",
                "updated_at": "2026-03-30T10:00:00+00:00",
            }
        ],
        "summary": {
            "query": None,
            "filters": {"since": None, "until": None},
            "limit": 20,
            "returned_count": 1,
            "total_count": 1,
            "order": ["relevance_desc", "created_at_desc", "id_desc"],
        },
    }

    rendered = cli_module.format_recall_output(payload)
    assert "source=OpenClaw (openclaw_import)" in rendered

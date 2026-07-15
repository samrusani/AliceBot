from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import anyio
import pytest

import alicebot_api.main as main_module
from alicebot_api.config import Settings
from alicebot_api.db import user_connection
from alicebot_api.mcp_tools import redact_memory_flow
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_agent_keys import create_agent_key
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_projects import (
    PROJECT_UPDATE_TERMINAL_CONSISTENCY_MESSAGE,
    ProjectAutomationRequest,
    VNextProjectService,
    VNextProjectTerminalConsistencyError,
)
from alicebot_api.vnext_store import PostgresVNextStore


def invoke_request(
    method: str,
    path: str,
    *,
    query_params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    authorization: str | None = None,
) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, object]] = []
    encoded_body = b"" if payload is None else json.dumps(payload).encode()
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}

        request_received = True
        return {"type": "http.request", "body": encoded_body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    query_string = urlencode(query_params or {}).encode()
    headers = [(b"content-type", b"application/json")]
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }

    anyio.run(main_module.app, scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return int(start_message["status"]), json.loads(body)


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


@pytest.mark.parametrize(
    ("action", "terminal_status", "revision_type"),
    [
        ("accept", "accepted", "promoted"),
        ("reject", "rejected", "rejected"),
    ],
)
def test_project_update_terminal_replay_survives_authorized_true_redaction(
    migrated_database_urls,
    action: str,
    terminal_status: str,
    revision_type: str,
) -> None:
    user_id = seed_user(
        migrated_database_urls["app"],
        email=f"project-update-{terminal_status}-redaction@example.com",
    )
    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = PostgresVNextStore(conn)
        project = store.create_project(
            {
                "name": f"{terminal_status.title()} redaction replay",
                "slug": f"{terminal_status}-redaction-replay-{uuid4().hex[:12]}",
                "status": "active",
                "current_state": "Initial project state.",
                "domain": "project",
                "sensitivity": "private",
            }
        )
        project_id = str(project["id"])
        store.create_source(
            {
                "source_type": "manual_text",
                "title": f"{terminal_status.title()} project update",
                "content_hash": f"sha256:{uuid4().hex}",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {
                    "project_scope": [project_id],
                    "raw_text": f"Decision: The {terminal_status} redaction replay project is ready for its reviewed state.",
                },
            }
        )
        service = VNextProjectService(store)
        candidate = service.generate_project_update_candidate(
            ProjectAutomationRequest(project_id=project_id, domains=("project",))
        )
        artifact_id = str(candidate["id"])
        reviewed = service.review_project_update(artifact_id=artifact_id, action=action)
        reviewed_metadata = reviewed["metadata_json"]
        assert isinstance(reviewed_metadata, dict)
        memory_id = str(reviewed_metadata["candidate_memory_id"])

        review_revisions_before = [
            revision for revision in store.list_revisions(memory_id) if revision["action"] == "project_update_review"
        ]
        assert len(review_revisions_before) == 1
        review_revision_before = review_revisions_before[0]
        assert review_revision_before["revision_type"] == revision_type

        event_target_type = "project" if action == "accept" else "artifact"
        event_target_id = project_id if action == "accept" else artifact_id
        event_type = f"project.update_candidate_{terminal_status}"
        review_events_before = [
            event
            for event in store.list_events(target_type=event_target_type, target_id=event_target_id)
            if event["event_type"] == event_type
        ]
        assert len(review_events_before) == 1
        review_event_before = review_events_before[0]
        creation_events_before = [
            event
            for event in store.list_events(target_type="artifact", target_id=artifact_id)
            if event["event_type"] == "project.update_candidate_created"
        ]
        assert len(creation_events_before) == 1
        creation_event_before = creation_events_before[0]
        creation_payload_before = creation_event_before["payload_json"]
        assert isinstance(creation_payload_before, dict)
        append_event(
            store,
            event_type="project.update_candidate_created",
            actor_type=str(creation_event_before["actor_type"]),
            actor_id=str(creation_event_before["actor_id"])
            if creation_event_before.get("actor_id") is not None
            else None,
            target_type="artifact",
            target_id=artifact_id,
            trace_id=str(creation_event_before["trace_id"])
            if creation_event_before.get("trace_id") is not None
            else None,
            run_id=str(creation_event_before["run_id"]) if creation_event_before.get("run_id") is not None else None,
            payload=dict(creation_payload_before),
        )

        # The app-role connection is tenant-bound by RLS. identity=None is
        # the explicit human path authorized by memory.redact policy.
        redacted = redact_memory_flow(
            store,
            memory_id=memory_id,
            reason="User requested erasure after the project review.",
            identity=None,
        )
        assert redacted["status"] == "redacted"
        assert redacted["forgotten_first"] is (action == "accept")
        assert int(redacted["redacted_revisions"]) >= 1
        assert int(redacted["redacted_events"]) >= 1

        review_revisions_after = [
            revision for revision in store.list_revisions(memory_id) if revision["action"] == "project_update_review"
        ]
        assert len(review_revisions_after) == 1
        review_revision_after = review_revisions_after[0]
        for field in (
            "id",
            "memory_id",
            "sequence_no",
            "action",
            "memory_key",
            "revision_number",
            "revision_type",
            "actor_type",
            "actor_id",
            "created_at",
        ):
            assert review_revision_after[field] == review_revision_before[field]
        assert review_revision_after["metadata_json"] == {"redacted": True}
        assert review_revision_after["text_before"] == "[REDACTED]"
        assert review_revision_after["text_after"] == "[REDACTED]"
        assert review_revision_after["reason"] == "[REDACTED]"

        review_events_after = [
            event
            for event in store.list_events(target_type=event_target_type, target_id=event_target_id)
            if event["event_type"] == event_type
        ]
        assert len(review_events_after) == 1
        review_event_after = review_events_after[0]
        for field in (
            "id",
            "event_type",
            "actor_type",
            "actor_id",
            "target_type",
            "target_id",
            "occurred_at",
            "trace_id",
            "run_id",
        ):
            assert review_event_after[field] == review_event_before[field]
        if action == "accept":
            assert review_event_after["payload_json"] == {
                "redacted": True,
                "memory_id": memory_id,
                "event_type": event_type,
            }
            assert review_event_after["integrity_hash"] is None
        else:
            # The rejection event targets the artifact and never carries the
            # candidate memory id, so memory redaction legitimately leaves its
            # already content-free linkage payload intact.
            assert review_event_after["payload_json"] == review_event_before["payload_json"]

        creation_events_after = [
            event
            for event in store.list_events(target_type="artifact", target_id=artifact_id)
            if event["event_type"] == "project.update_candidate_created"
        ]
        assert len(creation_events_after) == 2
        for creation_event_after in creation_events_after:
            assert creation_event_after["target_type"] == "artifact"
            assert str(creation_event_after["target_id"]) == artifact_id
            assert creation_event_after["payload_json"] == {
                "redacted": True,
                "memory_id": memory_id,
                "event_type": "project.update_candidate_created",
            }
            assert creation_event_after["integrity_hash"] is None

        def terminal_state() -> dict[str, object]:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, status, deleted_at, title, canonical_text, summary,
                           value, metadata_json, memory_type, memory_key,
                           project_id, updated_at
                    FROM memories
                    WHERE id = %s::uuid
                    """,
                    (memory_id,),
                )
                raw_memory = cur.fetchone()
            return {
                "artifact": store.get_artifact(artifact_id),
                "project": store.get_project(project_id),
                "memory": raw_memory,
                "revisions": store.list_revisions(memory_id),
                "events": store.list_events(),
            }

        frozen_state = terminal_state()
        assert service.review_project_update(artifact_id=artifact_id, action=action) == reviewed
        assert terminal_state() == frozen_state

        if action == "accept":
            clone_metadata = dict(reviewed_metadata)
            clone_metadata.pop("idempotency_digest", None)
            clone = store.create_artifact(
                {
                    "artifact_type": reviewed["artifact_type"],
                    "title": reviewed["title"],
                    "content_markdown": reviewed["content_markdown"],
                    "status": reviewed["status"],
                    "domain": reviewed["domain"],
                    "sensitivity": reviewed["sensitivity"],
                    "generated_by": reviewed["generated_by"],
                    "prompt_hash": reviewed["prompt_hash"],
                    "model_info_json": reviewed["model_info_json"],
                    "metadata_json": clone_metadata,
                },
                actor_type="system",
            )
            clone_id = str(clone["id"])

            def clone_terminal_state() -> dict[str, object]:
                return {**terminal_state(), "clone": store.get_artifact(clone_id)}

            frozen_clone_state = clone_terminal_state()
            with pytest.raises(VNextProjectTerminalConsistencyError) as excinfo:
                service.review_project_update(artifact_id=clone_id, action="accept")

            assert str(excinfo.value) == PROJECT_UPDATE_TERMINAL_CONSISTENCY_MESSAGE
            assert clone_terminal_state() == frozen_clone_state


@pytest.mark.parametrize("action", ["accept", "reject"])
def test_project_update_terminal_replay_rejects_competing_postgres_decision_without_mutation(
    migrated_database_urls,
    action: str,
) -> None:
    user_id = seed_user(
        migrated_database_urls["app"],
        email=f"project-update-{action}-competing-decision@example.com",
    )
    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = PostgresVNextStore(conn)
        project = store.create_project(
            {
                "name": f"{action.title()} competing decision",
                "slug": f"{action}-competing-decision-{uuid4().hex[:12]}",
                "status": "active",
                "current_state": "Initial project state.",
                "domain": "project",
                "sensitivity": "private",
            }
        )
        project_id = str(project["id"])
        store.create_source(
            {
                "source_type": "manual_text",
                "title": f"{action.title()} competing project update",
                "content_hash": f"sha256:{uuid4().hex}",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {
                    "project_scope": [project_id],
                    "raw_text": f"Decision: The {action} competing-decision project is ready for review.",
                },
            }
        )
        service = VNextProjectService(store)
        candidate = service.generate_project_update_candidate(
            ProjectAutomationRequest(project_id=project_id, domains=("project",))
        )
        artifact_id = str(candidate["id"])
        reviewed = service.review_project_update(artifact_id=artifact_id, action=action)
        metadata = reviewed["metadata_json"]
        assert isinstance(metadata, dict)
        memory_id = str(metadata["candidate_memory_id"])

        if action == "accept":
            append_event(
                store,
                event_type="project.update_candidate_rejected",
                actor_type="system",
                target_type="artifact",
                target_id=artifact_id,
                payload={
                    "project_id": project_id,
                    "source_ids": list(metadata["source_ids"]),
                },
            )
        else:
            append_event(
                store,
                event_type="project.update_candidate_accepted",
                actor_type="system",
                target_type="project",
                target_id=project_id,
                payload={
                    "artifact_id": artifact_id,
                    "candidate_memory_id": memory_id,
                    "action": "accept",
                },
            )

        def terminal_state() -> dict[str, object]:
            return {
                "artifact": store.get_artifact(artifact_id),
                "project": store.get_project(project_id),
                "memory": store.get_memory(memory_id),
                "revisions": store.list_revisions(memory_id),
                "events": store.list_events(),
            }

        frozen_state = terminal_state()
        with pytest.raises(VNextProjectTerminalConsistencyError) as excinfo:
            service.review_project_update(artifact_id=artifact_id, action=action)

        assert str(excinfo.value) == PROJECT_UPDATE_TERMINAL_CONSISTENCY_MESSAGE
        assert terminal_state() == frozen_state


def test_vnext_live_workspace_happy_path_writes_reviewable_postgres_state(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="vnext-live-workspace@example.com")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )
    user_id_text = str(user_id)
    generated_for = datetime.now(timezone.utc).date().isoformat()

    workspace_status, workspace_payload = invoke_request(
        "GET",
        "/v0/vnext/workspace",
        query_params={"user_id": user_id_text},
    )
    assert workspace_status == 200
    assert workspace_payload["mode"] == "live"
    assert workspace_payload["summary"]["source_count"] == 0

    project_status, project_payload = invoke_request(
        "POST",
        "/v0/vnext/projects",
        payload={
            "user_id": user_id_text,
            "name": "Alice Live UI",
            "description": "Live-backed vNext workspace sprint.",
            "current_state": "Preparing live workspace smoke coverage.",
            "domain": "project",
            "sensitivity": "private",
        },
    )
    assert project_status == 201
    project_id = project_payload["project"]["id"]

    source_status, source_payload = invoke_request(
        "POST",
        "/v0/vnext/sources",
        payload={
            "user_id": user_id_text,
            "raw_text": "\n".join(
                [
                    "Decision: Alice Live UI uses Postgres workspace data.",
                    "Todo: Confirm project dashboard updates before release.",
                    "Question: Did the live workspace preserve provenance?",
                ]
            ),
            "title": "Live workspace launch note",
            "domain": "project",
            "sensitivity": "private",
        },
    )
    assert source_status == 201
    assert source_payload["candidate_memory_count"] >= 3
    source_id = source_payload["source_id"]

    refreshed_status, refreshed_payload = invoke_request(
        "GET",
        "/v0/vnext/workspace",
        query_params={"user_id": user_id_text},
    )
    assert refreshed_status == 200
    assert refreshed_payload["summary"]["source_count"] == 1
    assert refreshed_payload["summary"]["candidate_memory_count"] >= 3
    review_memories = refreshed_payload["review_memories"]
    decision_memory = next(memory for memory in review_memories if "Alice Live UI" in memory["canonical_text"])
    rejected_memory = next(memory for memory in review_memories if memory["id"] != decision_memory["id"])

    edit_status, edit_payload = invoke_request(
        "POST",
        f"/v0/vnext/memories/{decision_memory['id']}/review",
        payload={
            "user_id": user_id_text,
            "action": "edit",
            "canonical_text": "Alice Live UI uses Postgres workspace data with provenance intact.",
            "summary": "Alice Live UI is backed by Postgres workspace state.",
            "domain": "project",
            "sensitivity": "private",
            "reason": "Smoke-test edit before accepting the candidate.",
        },
    )
    assert edit_status == 200
    assert edit_payload["memory"]["canonical_text"].startswith("Alice Live UI uses Postgres")

    assign_status, assign_payload = invoke_request(
        "POST",
        f"/v0/vnext/memories/{decision_memory['id']}/review",
        payload={
            "user_id": user_id_text,
            "action": "assign_project",
            "project_id": project_id,
            "reason": "Attach the accepted memory to the live UI project.",
        },
    )
    assert assign_status == 200
    assert assign_payload["memory"]["metadata_json"]["project_id"] == project_id

    accept_status, accept_payload = invoke_request(
        "POST",
        f"/v0/vnext/memories/{decision_memory['id']}/review",
        payload={"user_id": user_id_text, "action": "accept"},
    )
    assert accept_status == 200
    assert accept_payload["memory"]["status"] == "active"

    reject_status, reject_payload = invoke_request(
        "POST",
        f"/v0/vnext/memories/{rejected_memory['id']}/review",
        payload={"user_id": user_id_text, "action": "reject", "reason": "Smoke-test rejection path."},
    )
    assert reject_status == 200
    assert reject_payload["memory"]["status"] == "rejected"

    pack_status, pack_payload = invoke_request(
        "POST",
        "/v0/vnext/context-packs",
        payload={
            "user_id": user_id_text,
            "query": "Alice Live UI uses Postgres",
            "scope": {"domains": ["project"]},
            "options": {"sensitivity_allowed": ["public", "internal", "private", "unknown"], "max_items": 6},
        },
    )
    assert pack_status == 201
    assert pack_payload["relevant_memories"]
    assert pack_payload["sources"]
    assert pack_payload["trace"]["selected_count"] >= 2
    assert "supporting_evidence" in pack_payload
    assert "contradicting_evidence" in pack_payload

    openclaw_identity = {
        "agent_id": "openclaw",
        "agent_type": "coding_agent",
        "agent_run_id": "openclaw-smoke-run-1",
        "task_id": "openclaw-task-1",
        "project_scope": [project_id],
        "permission_profile": "project_scoped_agent",
    }
    openclaw_pack_status, openclaw_pack_payload = invoke_request(
        "POST",
        "/v0/vnext/context-packs",
        payload={
            "user_id": user_id_text,
            "agent_identity": openclaw_identity,
            "project_scope": [project_id],
            "query": "Alice Live UI uses Postgres",
            "scope": {"domains": ["project"]},
            "options": {"sensitivity_allowed": ["public", "internal", "private", "unknown"], "max_items": 6},
        },
    )
    assert openclaw_pack_status == 201
    assert openclaw_pack_payload["agent_identity"]["agent_id"] == "openclaw"
    assert openclaw_pack_payload["policy_decision"]["decision"] == "allowed"
    assert openclaw_pack_payload["trace"]["selected_count"] >= 1

    proposal_status, proposal_payload = invoke_request(
        "POST",
        "/v0/vnext/memory-proposals",
        payload={
            "user_id": user_id_text,
            "agent_identity": openclaw_identity,
            "proposal_type": "candidate_memory",
            "title": "OpenClaw project memory proposal",
            "canonical_text": "OpenClaw should use Alice project context through governed memory proposals.",
            "source_refs": [source_id],
            "project_scope": [project_id],
            "domain": "project",
            "sensitivity": "private",
            "confidence": 0.72,
            "rationale": "Agentic scheduler smoke proposal.",
        },
    )
    assert proposal_status == 201
    assert proposal_payload["proposal"]["status"] == "candidate"
    assert proposal_payload["proposal"]["metadata_json"]["review_required"] is True
    assert proposal_payload["review_required"] is True

    restricted_status, restricted_payload = invoke_request(
        "POST",
        "/v0/vnext/context-packs",
        payload={
            "user_id": user_id_text,
            "agent_identity": openclaw_identity,
            "query": "restricted family and health context",
            "scope": {"domains": ["family", "health"], "projects": [project_id]},
            "options": {"sensitivity_allowed": ["private", "highly_sensitive"], "max_items": 6},
        },
    )
    assert restricted_status == 403
    assert restricted_payload["policy_decision"]["decision"] == "blocked"
    assert "all_requested_domains_restricted" in restricted_payload["policy_decision"]["reasons"]

    open_loop_status, open_loop_payload = invoke_request(
        "POST",
        "/v0/vnext/open-loops",
        payload={
            "user_id": user_id_text,
            "agent_identity": {
                "agent_id": "hermes",
                "agent_type": "personal_assistant",
                "agent_run_id": "hermes-smoke-run-1",
                "project_scope": [project_id],
                "permission_profile": "trusted_local_agent",
            },
            "title": "Confirm project dashboard updates before release",
            "description": "Created from the live /vnext workspace smoke.",
            "priority": "high",
            "memory_id": decision_memory["id"],
            "project_id": project_id,
            "source_id": source_id,
            "domain": "project",
            "sensitivity": "private",
        },
    )
    assert open_loop_status == 201
    loop_id = open_loop_payload["open_loop"]["id"]
    assert open_loop_payload["open_loop"]["metadata_json"]["agent_id"] == "hermes"

    edit_loop_status, edit_loop_payload = invoke_request(
        "POST",
        f"/v0/vnext/open-loops/{loop_id}/review",
        payload={
            "user_id": user_id_text,
            "action": "edit",
            "title": "Confirm dashboard counts before release",
            "priority": "urgent",
        },
    )
    assert edit_loop_status == 200
    assert edit_loop_payload["priority"] == "urgent"

    snooze_status, snooze_payload = invoke_request(
        "POST",
        f"/v0/vnext/open-loops/{loop_id}/review",
        payload={"user_id": user_id_text, "action": "snooze", "due_at": "2026-05-12T09:00:00Z"},
    )
    assert snooze_status == 200
    assert snooze_payload["due_at"].startswith("2026-05-12T09:00:00")

    close_status, close_payload = invoke_request(
        "POST",
        f"/v0/vnext/open-loops/{loop_id}/review",
        payload={"user_id": user_id_text, "action": "close", "resolution_note": "Closed in smoke."},
    )
    assert close_status == 200
    assert close_payload["status"] == "resolved"

    reopen_status, reopen_payload = invoke_request(
        "POST",
        f"/v0/vnext/open-loops/{loop_id}/review",
        payload={"user_id": user_id_text, "action": "reopen"},
    )
    assert reopen_status == 200
    assert reopen_payload["status"] == "open"

    daily_status, daily_payload = invoke_request(
        "POST",
        "/v0/vnext/artifacts/generate/daily-brief",
        payload={
            "user_id": user_id_text,
            "scope": {"domains": ["project"]},
            "options": {"generated_for": generated_for},
        },
    )
    assert daily_status == 201
    assert daily_payload["artifact_type"] == "daily_brief"
    assert daily_payload["status"] == "needs_review"

    daily_review_status, daily_review_payload = invoke_request(
        "POST",
        f"/v0/vnext/artifacts/{daily_payload['id']}/review",
        payload={"user_id": user_id_text, "action": "archive"},
    )
    assert daily_review_status == 200
    assert daily_review_payload["status"] == "archived"

    weekly_status, weekly_payload = invoke_request(
        "POST",
        "/v0/vnext/artifacts/generate/weekly-synthesis",
        payload={
            "user_id": user_id_text,
            "scope": {"domains": ["project"]},
            "options": {"generated_for": generated_for},
        },
    )
    assert weekly_status == 201
    assert weekly_payload["artifact_type"] == "weekly_synthesis"
    assert weekly_payload["metadata_json"]["candidate_memory_ids"]

    weekly_review_status, weekly_review_payload = invoke_request(
        "POST",
        f"/v0/vnext/artifacts/{weekly_payload['id']}/review",
        payload={"user_id": user_id_text, "action": "accept"},
    )
    assert weekly_review_status == 200
    assert weekly_review_payload["status"] == "accepted"

    scheduler_status, scheduler_payload = invoke_request(
        "GET",
        "/v0/vnext/scheduler/status",
        query_params={"user_id": user_id_text},
    )
    assert scheduler_status == 200
    assert scheduler_payload["disabled_by_default"] is True
    assert {workflow["workflow_type"] for workflow in scheduler_payload["workflows"]} >= {
        "daily_brief",
        "weekly_synthesis",
    }

    daily_enable_status, daily_enable_payload = invoke_request(
        "PATCH",
        "/v0/vnext/scheduler/workflows/daily_brief",
        payload={
            "user_id": user_id_text,
            "enabled": True,
            "schedule_json": {"kind": "daily", "time_of_day": "08:00", "days_of_week": ["monday"]},
            "timezone": "UTC",
        },
    )
    assert daily_enable_status == 200
    assert daily_enable_payload["workflow"]["enabled"] is True

    weekly_enable_status, weekly_enable_payload = invoke_request(
        "PATCH",
        "/v0/vnext/scheduler/workflows/weekly_synthesis",
        payload={
            "user_id": user_id_text,
            "enabled": True,
            "schedule_json": {"kind": "weekly", "day_of_week": "monday", "time_of_day": "09:00"},
            "timezone": "UTC",
        },
    )
    assert weekly_enable_status == 200
    assert weekly_enable_payload["workflow"]["enabled"] is True

    pause_status, pause_payload = invoke_request(
        "POST",
        "/v0/vnext/scheduler/pause",
        payload={"user_id": user_id_text},
    )
    assert pause_status == 200
    assert pause_payload["paused_count"] >= 2

    resume_status, resume_payload = invoke_request(
        "POST",
        "/v0/vnext/scheduler/resume",
        payload={"user_id": user_id_text},
    )
    assert resume_status == 200
    assert resume_payload["resumed_count"] >= 2

    scheduler_daily_status, scheduler_daily_payload = invoke_request(
        "POST",
        "/v0/vnext/scheduler/workflows/daily_brief/run-now",
        payload={
            "user_id": user_id_text,
            "scope": {"domains": ["project"]},
            "options": {
                "generated_for": generated_for,
                "sensitivity_allowed": ["public", "internal", "private", "unknown"],
            },
        },
    )
    assert scheduler_daily_status == 201
    assert scheduler_daily_payload["run"]["status"] == "succeeded"
    assert scheduler_daily_payload["artifact"]["generated_by"] == "scheduler"
    assert (
        scheduler_daily_payload["artifact"]["metadata_json"]["scheduler_run_id"] == scheduler_daily_payload["run"]["id"]
    )

    scheduler_weekly_status, scheduler_weekly_payload = invoke_request(
        "POST",
        "/v0/vnext/scheduler/workflows/weekly_synthesis/run-now",
        payload={
            "user_id": user_id_text,
            "scope": {"domains": ["project"]},
            "options": {
                "generated_for": generated_for,
                "sensitivity_allowed": ["public", "internal", "private", "unknown"],
            },
        },
    )
    assert scheduler_weekly_status == 201
    assert scheduler_weekly_payload["run"]["status"] == "succeeded"
    assert scheduler_weekly_payload["artifact"]["metadata_json"]["generated_by"] == "scheduler"

    scheduler_review_status, scheduler_review_payload = invoke_request(
        "POST",
        f"/v0/vnext/artifacts/{scheduler_daily_payload['artifact']['id']}/review",
        payload={"user_id": user_id_text, "action": "archive"},
    )
    assert scheduler_review_status == 200
    assert scheduler_review_payload["status"] == "archived"

    project_update_status, project_update_payload = invoke_request(
        "POST",
        "/v0/vnext/projects/update-candidates",
        payload={
            "user_id": user_id_text,
            "scope": {"domains": ["project"]},
            "options": {"project_id": project_id, "max_items": 6},
        },
    )
    assert project_update_status == 201
    assert project_update_payload["artifact_type"] == "project_update"
    assert project_update_payload["status"] == "needs_review"

    dashboard_status, dashboard_payload = invoke_request(
        "GET",
        f"/v0/vnext/projects/{project_id}/dashboard",
        query_params={"user_id": user_id_text},
    )
    assert dashboard_status == 200
    assert dashboard_payload["counts"]["memories"] >= 1
    assert dashboard_payload["counts"]["open_loops"] >= 1
    assert dashboard_payload["counts"]["artifacts"] >= 1

    charter_status, charter_payload = invoke_request(
        "PUT",
        "/v0/vnext/settings/brain-charter",
        payload={
            "user_id": user_id_text,
            "content_markdown": "# ALICE.md\n\nPrefer provenance-first review.",
            "owner_json": {"name": "Alice Live UI"},
            "memory_philosophy_json": {"promotion": "review_required"},
            "life_domains_json": {"project": {"default_sensitivity": "private"}},
            "active_projects_json": [{"id": project_id, "name": "Alice Live UI"}],
            "communication_style_json": {"tone": "direct"},
            "priorities_json": {"current": ["live workspace"]},
            "autonomous_rules_json": [{"rule": "no_auto_promotion"}],
            "quality_standard_json": [{"rule": "source-backed"}],
            "sensitivity": "private",
        },
    )
    assert charter_status == 200
    assert charter_payload["brain_charter"]["content_markdown"].startswith("# ALICE.md")

    charter_get_status, charter_get_payload = invoke_request(
        "GET",
        "/v0/vnext/settings/brain-charter",
        query_params={"user_id": user_id_text},
    )
    assert charter_get_status == 200
    assert charter_get_payload["brain_charter"]["owner_json"]["name"] == "Alice Live UI"

    final_workspace_status, final_workspace_payload = invoke_request(
        "GET",
        "/v0/vnext/workspace",
        query_params={"user_id": user_id_text},
    )
    assert final_workspace_status == 200
    assert final_workspace_payload["summary"]["artifact_count"] >= 3
    assert final_workspace_payload["summary"]["agent_count"] >= 2
    assert final_workspace_payload["summary"]["scheduler_enabled_count"] >= 2
    assert final_workspace_payload["project_dashboards"][0]["counts"]["open_loops"] >= 1
    assert final_workspace_payload["brain_charter"]["id"] == charter_payload["brain_charter"]["id"]
    assert final_workspace_payload["recent_events"]
    assert final_workspace_payload["agent_activity"]["agents"]
    assert final_workspace_payload["agent_activity"]["policy_blocks"]
    assert final_workspace_payload["scheduler"]["recent_runs"]

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT event_type FROM event_log ORDER BY occurred_at ASC, id ASC")
            event_types = {row["event_type"] for row in cur.fetchall()}
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE status = 'active'
                  AND memory_type = 'artifact_summary'
                  AND metadata_json ->> 'discovered_by' = 'vnext_weekly_synthesis'
                """
            )
            active_artifact_summary_count = cur.fetchone()["count"]
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE status = 'candidate'
                  AND metadata_json ->> 'proposal_type' = 'candidate_memory'
                  AND metadata_json ->> 'agent_id' = 'openclaw'
                """
            )
            openclaw_candidate_count = cur.fetchone()["count"]
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM scheduler_runs
                WHERE status = 'succeeded'
                  AND workflow_type IN ('daily_brief', 'weekly_synthesis')
                """
            )
            scheduler_success_count = cur.fetchone()["count"]

    assert {
        "project.created",
        "source.created",
        "source.captured",
        "policy.decision",
        "agent.context_pack_requested",
        "agent.memory_proposed",
        "agent.policy_blocked",
        "review.item_created",
        "memory.updated",
        "memory_revision.created",
        "graph_edge.created",
        "retrieval.context_pack_compiled",
        "open_loop.created",
        "open_loop.updated",
        "artifact.generated",
        "artifact.reviewed",
        "project.update_candidate_created",
        "scheduler.workflow_enabled",
        "scheduler.workflow_paused",
        "scheduler.workflow_resumed",
        "scheduler.run_started",
        "scheduler.run_succeeded",
        "scheduler.artifact_created",
        "brain_charter.upserted",
    }.issubset(event_types)
    assert active_artifact_summary_count == 0
    assert openclaw_candidate_count == 1
    assert scheduler_success_count >= 2


def test_assign_project_replaces_postgres_scope_for_memory_and_source_retrieval(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="scope-reassignment@example.com")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )
    user_id_text = str(user_id)
    old_project = "release-project-old"
    new_project = "release-project-new"
    marker = "Canonical scope reassignment sentinel"

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.create_source(
            {
                "source_type": "manual_text",
                "title": marker,
                "content_hash": f"sha256:{uuid4().hex}",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {
                    "raw_text": marker,
                    "project_id": old_project,
                    "project_scope": [old_project],
                },
            },
            actor_type="user",
        )
        memory = store.create_memory(
            {
                "memory_key": f"project.scope.{uuid4().hex}",
                "value": {"text": marker},
                "status": "active",
                "memory_type": "semantic",
                "canonical_text": marker,
                "domain": "project",
                "sensitivity": "private",
                "project_id": old_project,
                "metadata_json": {
                    "project_id": old_project,
                    "project_scope": [old_project],
                },
            },
            actor_type="user",
        )

    source_status, source_payload = invoke_request(
        "POST",
        f"/v0/vnext/sources/{source['id']}/review",
        payload={
            "user_id": user_id_text,
            "action": "assign_project",
            "project_id": new_project,
        },
    )
    memory_status, memory_payload = invoke_request(
        "POST",
        f"/v0/vnext/memories/{memory['id']}/review",
        payload={
            "user_id": user_id_text,
            "action": "assign_project",
            "project_id": new_project,
        },
    )

    assert source_status == 200
    assert source_payload["source"]["metadata_json"]["project_scope"] == [new_project]
    assert memory_status == 200
    assert memory_payload["memory"]["project_id"] == new_project
    assert memory_payload["memory"]["project_scope"] == [new_project]
    assert memory_payload["memory"]["metadata_json"]["project_scope"] == [new_project]

    def scoped_pack(project_id: str) -> dict[str, Any]:
        status, payload = invoke_request(
            "POST",
            "/v0/vnext/context-packs",
            payload={
                "user_id": user_id_text,
                "query": marker,
                "scope": {"projects": [project_id]},
                "options": {
                    "include_sources": True,
                    "sensitivity_allowed": ["private"],
                    "max_items": 8,
                },
            },
        )
        assert status == 201
        return payload

    old_pack = scoped_pack(old_project)
    new_pack = scoped_pack(new_project)
    assert str(memory["id"]) not in {str(row["id"]) for row in old_pack["relevant_memories"]}
    assert str(source["id"]) not in {str(row["id"]) for row in old_pack["sources"]}
    assert str(memory["id"]) in {str(row["id"]) for row in new_pack["relevant_memories"]}
    assert str(source["id"]) in {str(row["id"]) for row in new_pack["sources"]}

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT project_id, metadata_json FROM memories WHERE id = %s::uuid",
                (str(memory["id"]),),
            )
            persisted_memory = cur.fetchone()
            cur.execute(
                "SELECT metadata_json FROM sources WHERE id = %s::uuid",
                (str(source["id"]),),
            )
            persisted_source = cur.fetchone()
    assert persisted_memory["project_id"] == new_project
    assert persisted_memory["metadata_json"]["project_scope"] == [new_project]
    assert persisted_source["metadata_json"]["project_scope"] == [new_project]


def test_vnext_artifact_routes_enforce_persisted_scope_with_live_postgres(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="artifact-scope@example.com")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )
    user_id_text = str(user_id)
    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = PostgresVNextStore(conn)
        artifact = store.create_artifact(
            {
                "artifact_type": "daily_brief",
                "title": "Project B private brief",
                "content_markdown": "# Project B\n\nPersisted private content.",
                "status": "needs_review",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_id": "project-b"},
            },
            actor_type="user",
        )
        _reader_record, reader_key = create_agent_key(
            store,
            user_id=user_id,
            agent_id="project-b-reader",
            permission_profile="read_only_agent",
            project_scope="project-b",
        )
        _admin_a_record, admin_a_key = create_agent_key(
            store,
            user_id=user_id,
            agent_id="project-a-admin",
            permission_profile="admin_agent",
            project_scope="project-a",
        )
        _trusted_b_record, trusted_b_key = create_agent_key(
            store,
            user_id=user_id,
            agent_id="project-b-trusted",
            permission_profile="trusted_local_agent",
            project_scope="project-b",
        )
        _admin_b_record, admin_b_key = create_agent_key(
            store,
            user_id=user_id,
            agent_id="project-b-admin",
            permission_profile="admin_agent",
            project_scope="project-b",
        )

    artifact_id = str(artifact["id"])
    feedback_status, _feedback_payload = invoke_request(
        "POST",
        f"/v0/vnext/artifacts/{artifact_id}/insight-feedback",
        authorization=f"Bearer {reader_key}",
        payload={"user_id": user_id_text, "useful_insight": "yes"},
    )
    assert feedback_status == 403

    denied_status, denied_payload = invoke_request(
        "GET",
        f"/v0/vnext/artifacts/{artifact_id}",
        authorization=f"Bearer {admin_a_key}",
        query_params={"user_id": user_id_text},
    )
    assert denied_status == 403
    assert "project_scope_binding_violation" in denied_payload["policy_decision"]["reasons"]
    assert "content_markdown" not in denied_payload

    allowed_status, allowed_payload = invoke_request(
        "GET",
        f"/v0/vnext/artifacts/{artifact_id}",
        authorization=f"Bearer {trusted_b_key}",
        query_params={"user_id": user_id_text},
    )
    assert allowed_status == 200
    assert allowed_payload["id"] == artifact_id

    rating_status, _rating_payload = invoke_request(
        "POST",
        f"/v0/vnext/artifacts/{artifact_id}/quality-ratings",
        authorization=f"Bearer {trusted_b_key}",
        payload={"user_id": user_id_text, "verbosity": "right_sized", "usefulness": 5},
    )
    assert rating_status == 201

    review_status, review_payload = invoke_request(
        "POST",
        f"/v0/vnext/artifacts/{artifact_id}/review",
        authorization=f"Bearer {admin_b_key}",
        payload={"user_id": user_id_text, "action": "accept"},
    )
    assert review_status == 200
    assert review_payload["status"] == "accepted"

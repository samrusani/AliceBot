from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlencode
from uuid import uuid4

import anyio

import apps.api.src.alicebot_api.main as main_module
from alicebot_api.config import Settings
from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.vnext_memory_version import memory_version_snapshot
from alicebot_api.vnext_project_scope import memory_project_scope


class FakeVNextStore:
    def __init__(self, _conn) -> None:
        self.sources: dict[str, dict[str, object]] = {}
        self.source_by_hash: dict[str, dict[str, object]] = {}
        self.chunks: list[dict[str, object]] = []
        self.memories: list[dict[str, object]] = []
        self.open_loops: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []
        self.provenance_links: list[dict[str, object]] = []
        self.tasks: list[dict[str, object]] = []
        self.artifacts: dict[str, dict[str, object]] = {}
        self.quality_ratings: list[dict[str, object]] = []
        self.edges: dict[str, dict[str, object]] = {}
        self.beliefs: dict[str, dict[str, object]] = {}
        self.projects: dict[str, dict[str, object]] = {}
        self.agent_identities: dict[str, dict[str, object]] = {}
        self.agent_api_keys: list[dict[str, object]] = []
        self.revisions: list[dict[str, object]] = []

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def get_source_by_content_hash(self, content_hash: str) -> dict[str, object] | None:
        return self.source_by_hash.get(content_hash)

    def create_source(self, source: dict[str, object], **_kwargs) -> dict[str, object]:
        source_id = str(uuid4())
        row = {**source, "id": source_id}
        self.sources[source_id] = row
        self.source_by_hash[str(source["content_hash"])] = row
        return row

    def get_source(self, source_id: str) -> dict[str, object] | None:
        source = self.sources.get(source_id)
        if source is not None and source.get("deleted_at") is None:
            return source
        return None

    def list_sources(self, **kwargs) -> list[dict[str, object]]:
        return list(self.sources.values())[: kwargs.get("limit", 20)]

    def update_source(self, *, source_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        source = self.sources[source_id]
        source.update(patch)
        return source

    def delete_source(self, *, source_id: str, **_kwargs) -> dict[str, object]:
        source = self.sources[source_id]
        source["deleted_at"] = "now"
        return source

    def create_source_chunk(self, chunk: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**chunk, "id": f"chunk-{len(self.chunks) + 1}"}
        self.chunks.append(row)
        return row

    def list_source_chunks(self, source_id: str) -> list[dict[str, object]]:
        return [chunk for chunk in self.chunks if chunk.get("source_id") == source_id]

    def create_memory(self, memory: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**memory, "id": f"memory-{len(self.memories) + 1}"}
        self.memories.append(row)
        return row

    def list_memories(self, *, status: str | None = None) -> list[dict[str, object]]:
        return [memory for memory in self.memories if status is None or memory.get("status") == status]

    def update_memory(self, *, memory_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        for memory in self.memories:
            if memory["id"] == memory_id:
                memory.update(patch)
                return memory
        raise AssertionError(memory_id)

    def get_memory(self, memory_id: str) -> dict[str, object] | None:
        for memory in self.memories:
            if str(memory["id"]) == str(memory_id):
                return memory
        return None

    def redact_memory_content(self, *, memory_id: str, actor_type: str = "user") -> dict[str, object]:
        memory = self.get_memory(memory_id)
        assert memory is not None, memory_id
        memory.update(
            {
                "title": "[REDACTED]",
                "canonical_text": "[REDACTED]",
                "summary": "[REDACTED]",
                "value": {"redacted": True},
                "metadata_json": {"redacted": True},
                "status": "archived",
            }
        )
        self.append_event(
            {
                "event_type": "memory.redacted",
                "actor_type": actor_type,
                "target_type": "memory",
                "target_id": memory_id,
                "payload_json": {"operation": "redact_memory_content"},
            }
        )
        return memory

    def redact_memory_revisions(self, *, memory_id: str, actor_type: str = "user") -> dict[str, object]:
        redacted = 0
        for revision in self.revisions:
            if str(revision.get("memory_id")) == str(memory_id):
                revision.update({"text_before": "[REDACTED]", "text_after": "[REDACTED]", "reason": "[REDACTED]"})
                redacted += 1
        self.append_event(
            {
                "event_type": "memory.redacted",
                "actor_type": actor_type,
                "target_type": "memory",
                "target_id": memory_id,
                "payload_json": {"operation": "redact_memory_revisions", "redacted_revisions": redacted},
            }
        )
        return {"memory_id": memory_id, "redacted_revisions": redacted}

    def redact_memory_events(self, *, memory_id: str, actor_type: str = "user") -> dict[str, object]:
        redacted = 0
        for event in self.events:
            if str(event.get("target_id")) == str(memory_id):
                event["payload_json"] = {"redacted": True, "memory_id": memory_id}
                redacted += 1
        self.append_event(
            {
                "event_type": "memory.redacted",
                "actor_type": actor_type,
                "target_type": "memory",
                "target_id": memory_id,
                "payload_json": {"operation": "redact_memory_events", "redacted_events": redacted},
            }
        )
        return {"memory_id": memory_id, "redacted_events": redacted}

    def append_revision(self, revision: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**revision, "id": f"revision-{len(self.revisions) + 1}"}
        self.revisions.append(row)
        return row

    def create_provenance_link(self, link: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**link, "id": f"provenance-{len(self.provenance_links) + 1}"}
        self.provenance_links.append(row)
        return row

    def create_open_loop(self, loop: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**loop, "id": f"loop-{len(self.open_loops) + 1}", "status": loop.get("status", "open")}
        self.open_loops.append(row)
        return row

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
        **_filters: object,
    ) -> list[dict[str, object]]:
        del query, domains, sensitivity_allowed
        return self.memories[:limit]

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
        **_filters: object,
    ) -> list[dict[str, object]]:
        del query, domains, sensitivity_allowed
        return list(self.sources.values())[:limit]

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        project_id: str | None = None,
        person_id: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        rows = [
            row
            for row in self.open_loops
            if (status is None or row.get("status") == status)
            and (project_id is None or row.get("project_id") == project_id)
            and (person_id is None or row.get("person_id") == person_id)
        ]
        return rows[:limit]

    def get_open_loop(self, loop_id: str) -> dict[str, object] | None:
        for loop in self.open_loops:
            if loop["id"] == loop_id:
                return loop
        return None

    def update_open_loop(self, *, loop_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        loop = self.get_open_loop(loop_id)
        if loop is None:
            raise AssertionError(loop_id)
        loop.update(patch)
        return loop

    def update_open_loop_status(
        self,
        *,
        loop_id: str,
        status: str,
        resolution_note: str | None = None,
        **_kwargs,
    ) -> dict[str, object]:
        loop = self.update_open_loop(loop_id=loop_id, patch={"status": status})
        if resolution_note is not None:
            loop["resolution_note"] = resolution_note
        return loop

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[dict[str, object]]:
        return [
            link
            for link in self.provenance_links
            if link.get("target_type") == target_type and link.get("target_id") == target_id
        ]

    def create_task(self, task: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**task, "id": str(uuid4()), "status": task.get("status", "pending")}
        self.tasks.append(row)
        return row

    def claim_next_task(self) -> dict[str, object] | None:
        for task in self.tasks:
            if task.get("status") == "pending":
                task["status"] = "running"
                return task
        return None

    def update_task_status(
        self,
        *,
        task_id: str,
        status: str,
        details: dict[str, object] | None = None,
        **_kwargs,
    ) -> dict[str, object]:
        for task in self.tasks:
            if task.get("id") == task_id:
                task["status"] = status
                if details is not None:
                    task.update(details)
                return task
        raise AssertionError(task_id)

    def create_artifact(self, artifact: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**artifact, "id": str(uuid4())}
        self.artifacts[str(row["id"])] = row
        return row

    def get_artifact(self, artifact_id: str) -> dict[str, object] | None:
        return self.artifacts.get(artifact_id)

    def get_artifact_for_update(self, artifact_id: str) -> dict[str, object] | None:
        return self.artifacts.get(artifact_id)

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 4,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        rows = [
            row
            for row in self.artifacts.values()
            if artifact_type is None or row.get("artifact_type") == artifact_type
        ]
        return rows[:limit]

    def update_artifact_status(self, *, artifact_id: str, status: str, **_kwargs) -> dict[str, object]:
        artifact = self.artifacts[artifact_id]
        artifact["status"] = status
        return artifact

    def create_artifact_quality_rating(self, rating: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**rating, "id": f"quality-{len(self.quality_ratings) + 1}"}
        self.quality_ratings.append(row)
        return row

    def list_artifact_quality_ratings(
        self,
        *,
        artifact_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        rows = [
            row
            for row in self.quality_ratings
            if artifact_id is None or row.get("artifact_id") == artifact_id
        ]
        return rows[:limit]

    def get_project(self, project_id: str) -> dict[str, object] | None:
        return self.projects.get(project_id)

    def list_projects(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        rows = [row for row in self.projects.values() if status is None or row.get("status") == status]
        return rows[:limit]

    def update_project(self, *, project_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        project = self.projects[project_id]
        project.update(patch)
        return project

    def create_edge(self, edge: dict[str, object], *, actor_type: str = "system") -> dict[str, object]:
        del actor_type
        row = {**edge, "id": f"edge-{len(self.edges) + 1}"}
        self.edges[str(row["id"])] = row
        return row

    def update_edge_status(self, *, edge_id: str, status: str) -> dict[str, object]:
        edge = self.edges[edge_id]
        metadata = edge.get("metadata_json")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.update({"status": status, "candidate": status != "accepted"})
        edge["metadata_json"] = metadata
        if status == "rejected":
            edge["valid_to"] = "now"
        return edge

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[dict[str, object]]:
        return [
            edge
            for edge in self.edges.values()
            if (from_id is None or edge.get("from_id") == from_id)
            and (to_id is None or edge.get("to_id") == to_id)
            and edge.get("valid_to") is None
        ]

    def create_belief(self, belief: dict[str, object]) -> dict[str, object]:
        row = {**belief, "id": f"belief-{len(self.beliefs) + 1}"}
        self.beliefs[str(row["id"])] = row
        return row

    def get_belief(self, belief_id: str) -> dict[str, object] | None:
        return self.beliefs.get(belief_id)

    def list_beliefs(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        rows = [row for row in self.beliefs.values() if status is None or row.get("status") == status]
        return rows[:limit]

    def update_belief_status(
        self,
        *,
        belief_id: str,
        status: str,
        confidence: float | None = None,
        superseded_by: str | None = None,
    ) -> dict[str, object]:
        belief = self.beliefs[belief_id]
        belief["status"] = status
        if confidence is not None:
            belief["confidence"] = confidence
        if superseded_by is not None:
            belief["superseded_by"] = superseded_by
        self.append_event(
            {
                "event_type": "belief.updated",
                "target_type": "belief",
                "target_id": belief_id,
                "payload_json": {"status": status},
            }
        )
        return belief

    def list_events(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        rows = [
            event
            for event in self.events
            if (target_type is None or event.get("target_type") == target_type)
            and (target_id is None or event.get("target_id") == target_id)
        ]
        return rows[:limit] if limit is not None else rows

    def upsert_agent_identity(self, identity: dict[str, object], **_kwargs) -> dict[str, object]:
        self.agent_identities[str(identity["agent_id"])] = identity
        return identity

    def create_agent_api_key(self, key: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {
            **key,
            "id": str(uuid4()),
            "created_at": "now",
            "revoked_at": None,
            "last_used_at": None,
        }
        self.agent_api_keys.append(row)
        return row

    def get_agent_api_key_by_hash(self, key_hash: str) -> dict[str, object] | None:
        for row in self.agent_api_keys:
            if row.get("key_hash") == key_hash:
                return row
        return None

    def list_agent_api_keys(self, *, limit: int = 50) -> list[dict[str, object]]:
        return self.agent_api_keys[:limit]

    def revoke_agent_api_key(self, *, key_id: str, **_kwargs) -> dict[str, object] | None:
        for row in self.agent_api_keys:
            if row["id"] == key_id and row.get("revoked_at") is None:
                row["revoked_at"] = "now"
                return row
        return None

    def touch_agent_api_key(self, *, key_id: str) -> dict[str, object]:
        for row in self.agent_api_keys:
            if row["id"] == key_id:
                row["last_used_at"] = "now"
                return row
        raise AssertionError(key_id)

    def count_active_agent_api_keys(self) -> int:
        return len([row for row in self.agent_api_keys if row.get("revoked_at") is None])

    def list_scheduler_runs(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def connector_storage_status(self) -> dict[str, object]:
        return {
            "connector_settings_exists": True,
            "connector_state_exists": True,
            "artifact_quality_ratings_exists": True,
            "scheduler_workflows_exists": True,
            "scheduler_runs_exists": True,
            "migration_revision": "test",
        }

    def list_connector_settings(self) -> list[dict[str, object]]:
        return [
            {
                "connector_name": name,
                "enabled": False,
                "configured": True,
                "default_domain": "project",
                "default_sensitivity": "private",
                "sync_mode": "manual",
                "poll_interval_seconds": None,
                "secret_ref": None,
                "validation_errors_json": [],
                "metadata_json": {"config_json": {}},
            }
            for name in ("telegram", "local_folder", "browser_clipper", "agent_output")
        ]

    def list_connector_states(self) -> list[dict[str, object]]:
        return [
            {
                "connector_name": name,
                "cursor_type": "sync_cursor",
                "cursor_value": None,
                "state_json": {},
                "items_seen": 0,
                "items_captured": 0,
                "items_deduped": 0,
                "items_failed": 0,
            }
            for name in ("telegram", "local_folder", "browser_clipper", "agent_output")
        ]


def _install_fake_vnext_store(monkeypatch, store: FakeVNextStore) -> None:
    @contextmanager
    def fake_user_connection(database_url, current_user_id):
        assert database_url == "postgresql://db"
        assert current_user_id is not None
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://db"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "PostgresVNextStore", lambda _conn: store)


def _invoke_vnext_request(
    method: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
    authorization: str | None = None,
) -> tuple[int, dict[str, object]]:
    messages: list[dict[str, object]] = []
    body = b"" if payload is None else json.dumps(payload).encode()
    received = False

    async def receive() -> dict[str, object]:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

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
        "query_string": urlencode(query or {}).encode(),
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }
    anyio.run(main_module.app, scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), json.loads(response_body)


def test_vnext_http_auth_gate_covers_query_and_json_routes(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    # Fresh local installs keep their explicit keyless compatibility path.
    assert _invoke_vnext_request(
        "GET", "/v0/vnext/projects", query={"user_id": str(user_id)}
    )[0] == 200

    _record, raw_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="hermes",
        permission_profile="trusted_local_agent",
    )
    assert _invoke_vnext_request(
        "GET", "/v0/vnext/projects", query={"user_id": str(user_id)}
    )[0] == 401
    assert _invoke_vnext_request(
        "GET",
        "/v0/vnext/projects",
        query={"user_id": str(user_id)},
        authorization=raw_key,
    )[0] == 401
    assert _invoke_vnext_request(
        "GET",
        "/v0/vnext/projects",
        query={"user_id": str(user_id)},
        authorization="Bearer alice_sk_invalid",
    )[0] == 401
    assert _invoke_vnext_request(
        "GET",
        "/v0/vnext/projects",
        query={"user_id": str(user_id)},
        authorization=f"Bearer {raw_key}",
    )[0] == 200

    created_status, _created_payload = _invoke_vnext_request(
        "POST",
        "/v0/vnext/sources",
        authorization=f"Bearer {raw_key}",
        payload={
            "user_id": str(user_id),
            "raw_text": "Fact: the centralized gate preserves JSON bodies.",
            "domain": "project",
            "sensitivity": "internal",
        },
    )
    assert created_status == 201
    assert store.sources
    assert _invoke_vnext_request("GET", "/v0/vnext/projects")[0] == 400

    _scoped_record, scoped_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="project-reader",
        permission_profile="read_only_agent",
        project_scope="project-a",
    )
    scoped_status, scoped_payload = _invoke_vnext_request(
        "GET",
        "/v0/vnext/projects",
        query={"user_id": str(user_id)},
        authorization=f"Bearer {scoped_key}",
    )
    assert scoped_status == 403
    assert "trusted_or_admin_agent_required_for_operator_route" in scoped_payload["policy_decision"]["reasons"]
    assert "unbound_operator_key_required" in scoped_payload["policy_decision"]["reasons"]

    _reader_record, reader_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="unbound-reader",
        permission_profile="read_only_agent",
    )
    mutation_status, mutation_payload = _invoke_vnext_request(
        "POST",
        "/v0/vnext/doctor/run",
        authorization=f"Bearer {reader_key}",
        payload={"user_id": str(user_id)},
    )
    assert mutation_status == 403
    assert "trusted_or_admin_agent_required_for_operator_route" in mutation_payload["policy_decision"]["reasons"]

    # Every central operator-console route requires an unbound trusted/admin
    # key once keys exist. Target-aware routes retain their local policy.
    assert _invoke_vnext_request(
        "GET",
        "/v0/vnext/connectors",
        query={"user_id": str(user_id)},
        authorization=f"Bearer {raw_key}",
    )[0] == 200
    assert _invoke_vnext_request(
        "GET",
        "/v0/vnext/artifacts",
        query={"user_id": str(user_id)},
        authorization=f"Bearer {raw_key}",
    )[0] == 200
    assert _invoke_vnext_request(
        "POST",
        "/v0/vnext/queue/process-next",
        authorization=f"Bearer {raw_key}",
        payload={"user_id": str(user_id)},
    )[0] == 200

    _project_operator_record, project_operator_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="unbound-project-operator",
        permission_profile="project_scoped_agent",
    )
    brain_status, brain_payload = _invoke_vnext_request(
        "PUT",
        "/v0/vnext/settings/brain-charter",
        authorization=f"Bearer {project_operator_key}",
        payload={"user_id": str(user_id)},
    )
    assert brain_status == 403
    assert "trusted_or_admin_agent_required_for_operator_route" in brain_payload["policy_decision"]["reasons"]

    _bound_operator_record, bound_operator_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="bound-trusted-operator",
        permission_profile="trusted_local_agent",
        project_scope="project-a",
    )
    bound_status, bound_payload = _invoke_vnext_request(
        "GET",
        "/v0/vnext/connectors",
        query={"user_id": str(user_id)},
        authorization=f"Bearer {bound_operator_key}",
    )
    assert bound_status == 403
    assert "unbound_operator_key_required" in bound_payload["policy_decision"]["reasons"]


def test_vnext_route_inventory_fails_closed_without_route_local_policy() -> None:
    registered = {
        (method, str(route.path))
        for route in main_module.app.routes
        if str(getattr(route, "path", "")).startswith("/v0/vnext")
        for method in (getattr(route, "methods", None) or set())
        if method != "OPTIONS"
    }
    assert not (
        main_module._VNEXT_ROUTE_LOCAL_POLICY
        & main_module._VNEXT_CENTRAL_OPERATOR_ROUTES
    )
    assert (
        main_module._VNEXT_ROUTE_LOCAL_POLICY
        | main_module._VNEXT_CENTRAL_OPERATOR_ROUTES
    ) == registered
    assert len(registered) == 70

    project_bound = main_module.AgentIdentity(
        agent_id="project-reader",
        permission_profile="read_only_agent",
        project_scope=("project-a",),
        project_scope_locked=True,
    )
    read_only = main_module.AgentIdentity(
        agent_id="reader",
        permission_profile="read_only_agent",
    )
    proposal_only = main_module.AgentIdentity(
        agent_id="proposer",
        permission_profile="memory_proposal_agent",
    )
    project_scoped = main_module.AgentIdentity(
        agent_id="project-operator",
        permission_profile="project_scoped_agent",
    )
    trusted = main_module.AgentIdentity(
        agent_id="trusted-operator",
        permission_profile="trusted_local_agent",
    )
    admin = main_module.AgentIdentity(
        agent_id="admin-operator",
        permission_profile="admin_agent",
    )
    bound_trusted = main_module.AgentIdentity(
        agent_id="bound-trusted",
        permission_profile="trusted_local_agent",
        project_scope=("project-a",),
        project_scope_locked=True,
    )
    for method, path in main_module._VNEXT_CENTRAL_OPERATOR_ROUTES:
        for identity in (project_bound, read_only, proposal_only, project_scoped, bound_trusted):
            decision = main_module._vnext_central_route_policy(
                identity=identity,
                method=method,
                route_path=path,
            )
            assert decision is not None and decision.decision == "blocked", (
                identity.permission_profile,
                method,
                path,
            )
        for identity in (trusted, admin):
            decision = main_module._vnext_central_route_policy(
                identity=identity,
                method=method,
                route_path=path,
            )
            assert decision is not None and decision.decision == "allowed", (
                identity.permission_profile,
                method,
                path,
            )
        assert main_module._vnext_central_route_policy(
            identity=None,
            method=method,
            route_path=path,
        ) is None

    unknown = main_module._vnext_central_route_policy(
        identity=admin,
        method="GET",
        route_path="/v0/vnext/new-unclassified-route",
    )
    assert unknown is not None and unknown.decision == "blocked"
    assert unknown.reasons == ("vnext_route_not_classified",)


def test_create_vnext_source_endpoint_captures_text(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    response = main_module.create_vnext_source(
        main_module.VNextSourceCaptureRequest(
            user_id=user_id,
            raw_text="Fact: vNext source API preserves provenance.",
            title="API capture",
            domain="project",
            sensitivity="private",
        )
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["status"] == "imported"
    assert payload["candidate_memory_count"] == 1
    assert list(store.sources.values())[0]["domain"] == "project"
    assert store.memories[0]["canonical_text"] == "vNext source API preserves provenance."


def _sqlite_vnext_store() -> SQLiteVNextStore:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, "capture-scope@example.com")
    return SQLiteVNextStore(conn, user_id)


def test_create_vnext_source_threads_project_scope_into_captured_memory(monkeypatch) -> None:
    # Audit P1 #4: the HTTP handler validates the request's project scope but,
    # before the fix, dropped it on the way into capture -- the memory persisted
    # with an empty scope, so the owning project's filtered recall found nothing
    # while unscoped recall found it. Uses the real SQLite store so the recall
    # filter (search_memories_fts projects clause) is exercised end to end.
    store = _sqlite_vnext_store()
    _install_fake_vnext_store(monkeypatch, store)

    response = main_module.create_vnext_source(
        main_module.VNextSourceCaptureRequest(
            user_id=uuid4(),
            raw_text="Decision: The Helios launch ships behind a staged rollout flag.",
            title="Helios launch decision",
            domain="project",
            sensitivity="internal",
            project_scope=["project-helios"],
        )
    )
    assert response.status_code == 201
    assert json.loads(response.body)["status"] == "imported"

    candidates = store.list_memories(status="candidate")
    assert candidates, "capture must promote at least one candidate memory"
    assert memory_project_scope(candidates[0]) == ("project-helios",)
    for memory in candidates:
        store.update_memory(memory_id=str(memory["id"]), patch={"status": "active"}, actor_type="system")

    owning = store.search_memories_fts(
        query="Helios staged rollout", projects=("project-helios",), limit=10
    )
    other = store.search_memories_fts(
        query="Helios staged rollout", projects=("project-decoy",), limit=10
    )
    unscoped = store.search_memories_fts(query="Helios staged rollout", limit=10)

    assert len(owning) == 1, "the owning project's filtered recall must retrieve the captured memory"
    assert len(other) == 0, "another project must not see the captured memory"
    assert len(unscoped) == 1


def test_vnext_connector_endpoints_list_and_sync_payloads(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    list_response = main_module.list_vnext_connectors(user_id=user_id)
    sync_response = main_module.sync_vnext_connector(
        "browser_clipper",
        main_module.VNextConnectorSyncRequest(
            user_id=user_id,
            items=[
                {
                    "external_id": "clip-1",
                    "cursor": "1",
                    "title": "API connector clip",
                    "url": "https://example.test/api-clip",
                    "text": "Fact: API connector sync preserves raw evidence.",
                }
            ],
            default_domain="learning",
            default_sensitivity="private",
        ),
    )

    list_payload = json.loads(list_response.body)
    sync_payload = json.loads(sync_response.body)
    assert list_response.status_code == 200
    assert "browser_clipper" in list_payload["order"]
    assert sync_response.status_code == 201
    assert sync_payload["status"] == "ok"
    assert sync_payload["sync_cursor"] == "1"
    source = next(iter(store.sources.values()))
    assert source["connector_name"] == "browser_clipper"
    assert source["metadata_json"]["raw_payload"]["external_id"] == "clip-1"
    assert store.events[-1]["event_type"] == "connector.sync_completed"


def test_get_vnext_source_endpoint_returns_404_for_missing_source(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    missing_source_id = uuid4()

    response = main_module.get_vnext_source(missing_source_id, user_id=uuid4())

    assert response.status_code == 404
    assert f"vNext source {missing_source_id} was not found" in json.loads(response.body)["detail"]


def test_delete_vnext_source_endpoint_soft_deletes_source(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {"id": source_id, "deleted_at": None}
    _install_fake_vnext_store(monkeypatch, store)

    response = main_module.delete_vnext_source(source_id=uuid4(), user_id=uuid4())
    assert response.status_code == 404

    response = main_module.delete_vnext_source(source_id=main_module.UUID(source_id), user_id=uuid4())

    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["id"] == source_id
    assert payload["deleted_at"] == "now"


def test_vnext_source_review_trace_and_doctor_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    artifact_id = str(uuid4())
    store.sources[source_id] = {
        "id": source_id,
        "source_type": "manual_text",
        "title": "Operator console source",
        "content_hash": "sha256:source",
        "captured_at": "2026-05-12T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {
            "raw_text": "Fact: source review persists.",
            "project_id": "project-old",
            "project_scope": ["project-old"],
        },
    }
    store.chunks.append({"id": "chunk-1", "source_id": source_id, "chunk_index": 0, "text": "Fact: source review persists."})
    store.memories.append(
        {
            "id": "memory-1",
            "memory_key": "memory.operator.source",
            "memory_type": "semantic",
            "canonical_text": "Source review persists.",
            "status": "candidate",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"source_id": source_id},
        }
    )
    store.artifacts[artifact_id] = {
        "id": artifact_id,
        "artifact_type": "daily_brief",
        "title": "Daily",
        "content_markdown": "# Daily",
        "status": "needs_review",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"source_refs": [f"source:{source_id}"]},
    }
    store.open_loops.append({"id": "loop-1", "title": "Review source", "source_id": source_id, "status": "open"})
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    review_response = main_module.review_vnext_source(
        main_module.UUID(source_id),
        main_module.VNextSourceReviewRequest(
            user_id=user_id,
            action="assign_project",
            title="Reviewed source",
            domain="project",
            sensitivity="private",
            project_id="project-1",
            review_note="Reviewed from test.",
        ),
    )
    trace_response = main_module.get_vnext_source_trace(main_module.UUID(source_id), user_id=user_id)
    artifact_trace_response = main_module.get_vnext_artifact_trace(main_module.UUID(artifact_id), user_id=user_id)
    doctor_response = main_module.run_vnext_doctor(
        main_module.VNextDoctorRunRequest(user_id=user_id, fix_safe=False, ci=True)
    )

    review_payload = json.loads(review_response.body)
    old_scope_response = main_module.create_vnext_context_pack(
        main_module.VNextContextPackRequest(
            user_id=user_id,
            query="source review persists",
            scope={"projects": ["project-old"]},
            options={"include_sources": True},
        )
    )
    new_scope_response = main_module.create_vnext_context_pack(
        main_module.VNextContextPackRequest(
            user_id=user_id,
            query="source review persists",
            scope={"projects": ["project-1"]},
            options={"include_sources": True},
        )
    )
    old_scope_payload = json.loads(old_scope_response.body)
    new_scope_payload = json.loads(new_scope_response.body)
    trace_payload = json.loads(trace_response.body)
    artifact_trace_payload = json.loads(artifact_trace_response.body)
    doctor_payload = json.loads(doctor_response.body)

    assert review_response.status_code == 200
    assert review_payload["source"]["title"] == "Reviewed source"
    assert review_payload["source"]["metadata_json"]["project_id"] == "project-1"
    assert review_payload["source"]["metadata_json"]["project_scope"] == ["project-1"]
    assert old_scope_response.status_code == 201
    assert old_scope_payload["sources"] == []
    assert new_scope_response.status_code == 201
    assert [row["id"] for row in new_scope_payload["sources"]] == [source_id]
    assert review_payload["trace"]["summary"]["candidate_memory_count"] == 1
    assert trace_response.status_code == 200
    assert trace_payload["summary"]["chunk_count"] == 1
    assert trace_payload["summary"]["artifact_count"] == 1
    assert artifact_trace_response.status_code == 200
    assert artifact_trace_payload["summary"]["source_count"] == 1
    assert doctor_response.status_code == 200
    assert doctor_payload["blocking_failure_count"] == 0
    assert any(check["name"] == "migrations" for check in doctor_payload["checks"])


def test_create_vnext_context_pack_endpoint_returns_structured_pack(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {
        "id": source_id,
        "source_type": "manual_text",
        "title": "Alice context source",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
    }
    store.memories.append(
        {
            "id": "memory-1",
            "memory_type": "semantic",
            "canonical_text": "Alice context packs include sources.",
            "status": "active",
            "confidence": 0.9,
            "domain": "project",
            "sensitivity": "private",
            "first_seen_at": "2026-05-10T00:00:00Z",
            "last_seen_at": "2026-05-10T00:00:00Z",
        }
    )
    _install_fake_vnext_store(monkeypatch, store)

    response = main_module.create_vnext_context_pack(
        main_module.VNextContextPackRequest(
            user_id=uuid4(),
            query="Alice context sources",
            scope={"domains": ["project"]},
            options={"sensitivity_allowed": ["public", "private"], "max_items": 4},
        )
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["relevant_memories"][0]["id"] == "memory-1"
    assert payload["sources"][0]["id"] == source_id
    assert payload["trace_id"] == payload["trace"]["trace_id"]
    assert store.events[-1]["event_type"] == "retrieval.context_pack_compiled"


def test_vnext_brain_artifact_generation_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {
        "id": source_id,
        "source_type": "manual_text",
        "title": "Alice daily API note",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"raw_text": "TODO: validate daily API endpoint"},
    }
    store.memories.append(
        {
            "id": "memory-1",
            "memory_type": "project_state",
            "canonical_text": "Alice vNext API generates brain artifacts.",
            "status": "active",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    request = main_module.VNextBrainArtifactGenerateRequest(
        user_id=user_id,
        scope={"domains": ["project"]},
        options={"generated_for": "2026-05-10", "sensitivity_allowed": ["public", "private"]},
    )

    daily_response = main_module.generate_vnext_daily_brief(request)
    weekly_response = main_module.generate_vnext_weekly_synthesis(request)

    daily_payload = json.loads(daily_response.body)
    weekly_payload = json.loads(weekly_response.body)
    assert daily_response.status_code == 201
    assert daily_payload["artifact_type"] == "daily_brief"
    assert daily_payload["metadata_json"]["candidate_open_loop_ids"] == ["loop-1"]
    assert weekly_response.status_code == 201
    assert weekly_payload["artifact_type"] == "weekly_synthesis"
    assert weekly_payload["metadata_json"]["candidate_memory_ids"] == ["memory-2"]
    assert store.events[-1]["event_type"] == "artifact.generated"


def test_vnext_connection_and_graph_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {
        "id": source_id,
        "source_type": "manual_text",
        "title": "Queue retrieval pattern note",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"raw_text": "Queue retrieval provenance trace review."},
    }
    store.memories.append(
        {
            "id": "memory-1",
            "memory_type": "semantic",
            "canonical_text": "Retrieval provenance trace review improves queue artifacts.",
            "status": "active",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    generate_response = main_module.generate_vnext_connection_report(
        main_module.VNextConnectionReportGenerateRequest(
            user_id=user_id,
            scope={"domains": ["project"]},
            options={"max_connections": 1},
        )
    )
    review_response = main_module.review_vnext_graph_edge(
        "edge-1",
        main_module.VNextGraphEdgeReviewRequest(user_id=user_id, action="accept"),
    )
    neighborhood_response = main_module.get_vnext_graph_neighborhood(source_id, user_id=user_id)

    generate_payload = json.loads(generate_response.body)
    review_payload = json.loads(review_response.body)
    neighborhood_payload = json.loads(neighborhood_response.body)
    assert generate_response.status_code == 201
    assert generate_payload["artifact_type"] == "connection_report"
    assert generate_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_response.status_code == 200
    assert review_payload["metadata_json"]["status"] == "accepted"
    assert neighborhood_response.status_code == 200
    assert neighborhood_payload["edge_count"] == 1
    assert neighborhood_payload["from_edges"][0]["id"] == "edge-1"


def test_vnext_contradiction_and_belief_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    source_id = str(uuid4())
    store.sources[source_id] = {
        "id": source_id,
        "source_type": "manual_text",
        "title": "Artifact policy note",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"raw_text": "Alice should not auto-promote generated artifacts into memory."},
    }
    store.beliefs["belief-1"] = {
        "id": "belief-1",
        "memory_id": "memory-belief-1",
        "claim": "Alice should auto-promote generated artifacts into memory.",
        "status": "active",
        "confidence": 0.8,
        "domain": "project",
        "sensitivity": "private",
        "memory_type": "belief",
    }
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    generate_response = main_module.generate_vnext_contradiction_report(
        main_module.VNextContradictionReportGenerateRequest(
            user_id=user_id,
            scope={"domains": ["project"]},
            options={"max_contradictions": 1},
        )
    )
    review_response = main_module.review_vnext_belief(
        "belief-1",
        main_module.VNextBeliefReviewRequest(user_id=user_id, action="challenge", confidence=0.25),
    )
    state_response = main_module.get_vnext_belief_state("belief-1", user_id=user_id)

    generate_payload = json.loads(generate_response.body)
    review_payload = json.loads(review_response.body)
    state_payload = json.loads(state_response.body)
    assert generate_response.status_code == 201
    assert generate_payload["artifact_type"] == "contradiction_report"
    assert generate_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_response.status_code == 200
    assert review_payload["status"] == "challenged"
    assert review_payload["confidence"] == 0.25
    assert state_response.status_code == 200
    assert state_payload["current"]["status"] == "challenged"
    assert "challenged" in state_payload["previous_statuses"]


def test_vnext_project_and_open_loop_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    store.projects["project-1"] = {
        "id": "project-1",
        "name": "Alice vNext",
        "slug": "alice-vnext",
        "status": "active",
        "current_state": "Sprint 7 complete.",
        "domain": "project",
        "sensitivity": "private",
    }
    store.sources[str(uuid4())] = {
        "id": "source-1",
        "source_type": "manual_text",
        "title": "Alice project note",
        "content_hash": "sha256:abc",
        "captured_at": "2026-05-10T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {
            "raw_text": "Project: Alice vNext needs project automation.\nTODO: validate dashboard Owner: Samir"
        },
    }
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    request = main_module.VNextProjectAutomationRequest(
        user_id=user_id,
        scope={"domains": ["project"], "project_id": "project-1"},
        options={"sensitivity_allowed": ["public", "private"]},
    )

    update_response = main_module.generate_vnext_project_update_candidate(request)
    update_payload = json.loads(update_response.body)
    extract_response = main_module.extract_vnext_open_loops(request)
    review_update_response = main_module.review_vnext_project_update_candidate(
        update_payload["id"],
        main_module.VNextProjectUpdateReviewRequest(
            user_id=user_id,
            action="edit",
            edited_current_state="Project automation reviewed.",
        ),
    )
    review_loop_response = main_module.review_vnext_open_loop(
        "loop-1",
        main_module.VNextOpenLoopReviewRequest(
            user_id=user_id,
            action="snooze",
            due_at="2026-05-12T09:00:00Z",
        ),
    )
    dashboard_response = main_module.get_vnext_project_dashboard("project-1", user_id=user_id)

    extract_payload = json.loads(extract_response.body)
    review_update_payload = json.loads(review_update_response.body)
    review_loop_payload = json.loads(review_loop_response.body)
    dashboard_payload = json.loads(dashboard_response.body)
    assert update_response.status_code == 201
    assert update_payload["artifact_type"] == "project_update"
    assert update_payload["metadata_json"]["candidate_memory_id"] == "memory-1"
    assert extract_response.status_code == 201
    assert extract_payload["created_count"] == 1
    assert extract_payload["open_loops"][0]["metadata_json"]["owner"] == "Samir"
    assert review_update_response.status_code == 200
    assert review_update_payload["status"] == "accepted"
    assert store.projects["project-1"]["current_state"] == "Project automation reviewed."
    assert review_loop_response.status_code == 200
    assert review_loop_payload["due_at"] == "2026-05-12T09:00:00Z"
    assert dashboard_response.status_code == 200
    assert dashboard_payload["counts"]["open_loops"] == 1


def test_vnext_queue_and_artifact_endpoints(monkeypatch, tmp_path) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    create_response = main_module.create_vnext_queue_task(
        main_module.VNextQueueTaskCreateRequest(
            user_id=user_id,
            title="Draft launch note",
            task_type="draft",
            instructions="Write from approved sources.",
            domain="project",
            sensitivity="private",
            scope_json={"project": "alice"},
            allowed_sources_json=["source-1"],
        )
    )

    create_payload = json.loads(create_response.body)
    assert create_response.status_code == 201
    assert create_payload["status"] == "pending"
    assert create_payload["requested_by"] == "api"
    assert store.events[-1]["event_type"] == "queue.task_enqueued"

    process_response = main_module.process_next_vnext_queue_task(
        main_module.VNextQueueProcessNextRequest(user_id=user_id)
    )

    process_payload = json.loads(process_response.body)
    artifact_id = process_payload["artifact_id"]
    assert process_response.status_code == 200
    assert process_payload["status"] == "completed"
    assert store.tasks[0]["status"] == "completed"
    assert store.tasks[0]["output_artifact_id"] == artifact_id
    assert store.artifacts[artifact_id]["content_markdown"].startswith("# Draft launch note")

    get_response = main_module.get_vnext_artifact(main_module.UUID(artifact_id), user_id=user_id)
    assert get_response.status_code == 200
    assert json.loads(get_response.body)["id"] == artifact_id

    review_response = main_module.review_vnext_artifact(
        main_module.UUID(artifact_id),
        main_module.VNextArtifactReviewRequest(user_id=user_id, action="accept"),
    )
    assert review_response.status_code == 200
    assert json.loads(review_response.body)["status"] == "accepted"

    quality_response = main_module.rate_vnext_artifact_quality(
        main_module.UUID(artifact_id),
        main_module.VNextArtifactQualityRatingRequest(
            user_id=user_id,
            reviewer_id="reviewer-1",
            usefulness=4,
            accuracy=5,
            source_grounding=5,
            novel_connections=3,
            actionability=4,
            hallucination_risk=1,
            verbosity="right_sized",
            comments="Useful and grounded.",
        ),
    )
    quality_payload = json.loads(quality_response.body)
    export_quality_response = main_module.list_vnext_quality_evals(
        user_id=user_id,
        artifact_id=main_module.UUID(artifact_id),
        limit=10,
    )
    export_quality_payload = json.loads(export_quality_response.body)

    assert quality_response.status_code == 201
    assert quality_payload["artifact_id"] == artifact_id
    assert quality_payload["usefulness"] == 4
    assert export_quality_response.status_code == 200
    assert export_quality_payload["count"] == 1
    assert export_quality_payload["items"][0]["artifact_id"] == artifact_id

    export_response = main_module.export_vnext_artifact(
        main_module.UUID(artifact_id),
        main_module.VNextArtifactExportRequest(user_id=user_id, output_dir=str(tmp_path)),
    )
    export_payload = json.loads(export_response.body)
    output_path = Path(export_payload["output_path"])
    assert export_response.status_code == 200
    assert output_path.name.startswith("artifact-")
    assert output_path.suffix == ".md"
    assert output_path.read_text(encoding="utf-8").startswith("# Draft launch note")


def test_vnext_artifact_review_endpoint_maps_validation_errors(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    artifact_id = str(uuid4())
    store.artifacts[artifact_id] = {"id": artifact_id, "title": "Draft", "content_markdown": "# Draft"}

    invalid_response = main_module.review_vnext_artifact(
        main_module.UUID(artifact_id),
        main_module.VNextArtifactReviewRequest(user_id=user_id, action="ship"),
    )
    missing_response = main_module.review_vnext_artifact(
        uuid4(),
        main_module.VNextArtifactReviewRequest(user_id=user_id, action="accept"),
    )

    assert invalid_response.status_code == 400
    assert missing_response.status_code == 404


def test_live_capture_connector_api_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    config_response = main_module.update_vnext_connector_config(
        "telegram",
        main_module.VNextConnectorConfigRequest(
            user_id=user_id,
            enabled=True,
            secret_ref="env:TELEGRAM_BOT_TOKEN",
            config_json={"allowed_chat_ids": ["999001"]},
        ),
    )
    telegram_response = main_module.sync_vnext_telegram_connector(
        main_module.VNextTelegramSyncRequest(
            user_id=user_id,
            updates=[
                {
                    "update_id": 1,
                    "message": {
                        "message_id": 10,
                        "date": 1_778_400_000,
                        "chat": {"id": 999001},
                        "from": {"id": 1001, "username": "samir"},
                        "text": "Fact: API Telegram capture works.",
                    },
                }
            ],
        )
    )
    browser_response = main_module.capture_vnext_browser_clip(
        main_module.VNextBrowserClipperCaptureRequest(
            user_id=user_id,
            url="https://example.test/clip",
            title="Clip",
            selected_text="Fact: Browser API clip works.",
            user_note="Remember: keep this reviewable.",
        )
    )
    health_response = main_module.get_vnext_connectors_health(user_id=user_id)

    assert config_response.status_code == 200
    assert telegram_response.status_code == 201
    assert browser_response.status_code == 201
    assert json.loads(telegram_response.body)["imported_count"] == 1
    assert json.loads(browser_response.body)["imported_count"] == 1
    health_payload = json.loads(health_response.body)
    assert health_payload["count"] >= 4
    assert any(item["connector_name"] == "telegram" for item in health_payload["items"])


def test_vnext_agent_endpoint_with_bearer_key_uses_key_identity(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    _record, raw_key = create_agent_key(
        store, user_id=user_id, agent_id="openclaw", permission_profile="project_scoped_agent"
    )

    response = main_module.create_vnext_source(
        main_module.VNextSourceCaptureRequest(
            user_id=user_id,
            raw_text="Fact: keyed agents authenticate with per-agent API keys.",
            domain="project",
            sensitivity="private",
            agent_id="openclaw",
            agent_run_id="run-keyed-1",
        ),
        authorization=f"Bearer {raw_key}",
    )

    assert response.status_code == 201
    recorded_identity = store.agent_identities["openclaw"]
    assert recorded_identity["permission_profile"] == "project_scoped_agent"
    policy_events = [event for event in store.events if event.get("event_type") == "policy.decision"]
    assert policy_events
    identity_record = policy_events[0]["payload_json"]["agent_identity"]
    assert identity_record["auth"] == "agent_api_key"
    assert identity_record["permission_profile"] == "project_scoped_agent"
    assert store.agent_api_keys[0]["last_used_at"] == "now"


def test_vnext_agent_endpoint_rejects_keyless_agent_call_when_keys_exist(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    create_agent_key(
        store, user_id=user_id, agent_id="openclaw", permission_profile="project_scoped_agent"
    )

    response = main_module.create_vnext_source(
        main_module.VNextSourceCaptureRequest(
            user_id=user_id,
            raw_text="Fact: keyless agent calls are rejected once keys exist.",
            domain="project",
            sensitivity="private",
            agent_id="openclaw",
        )
    )

    assert response.status_code == 401
    detail = json.loads(response.body)["detail"]
    assert "Authorization: Bearer alice_sk_" in detail
    assert store.sources == {}


def test_vnext_memory_commit_rejects_keyless_agent_call_when_keys_exist(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    create_agent_key(
        store, user_id=user_id, agent_id="hermes", permission_profile="trusted_local_agent"
    )

    response = main_module.commit_vnext_memory(
        main_module.VNextMemoryCommitRequest(
            user_id=user_id,
            title="Keyless agent commit",
            canonical_text="Keyless agent commits stay rejected once keys exist.",
            agent_id="hermes",
        )
    )

    assert response.status_code == 401
    assert "Authorization: Bearer alice_sk_" in json.loads(response.body)["detail"]
    assert store.memories == []


def test_vnext_memory_commit_without_identity_commits_as_direct_user(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    user_id = uuid4()
    response = main_module.commit_vnext_memory(
        main_module.VNextMemoryCommitRequest(
            user_id=user_id,
            title="Direct user commit",
            canonical_text="Direct human commits need no agent identity.",
            confidence=0.95,
        )
    )

    assert response.status_code == 201
    payload = json.loads(response.body)
    assert payload["status"] == "committed"
    assert payload["write_mode"] == "commit"
    assert payload["policy_decision"]["policy_decision"]["permission_profile"] == "user_or_system"
    assert store.memories[0]["created_by_agent_id"] is None


def test_vnext_agent_endpoint_rejects_payload_profile_escalation(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    _record, raw_key = create_agent_key(
        store, user_id=user_id, agent_id="openclaw", permission_profile="project_scoped_agent"
    )

    response = main_module.create_vnext_source(
        main_module.VNextSourceCaptureRequest(
            user_id=user_id,
            raw_text="Fact: escalation attempts are rejected.",
            domain="project",
            sensitivity="private",
            agent_id="openclaw",
            permission_profile="admin_agent",
        ),
        authorization=f"Bearer {raw_key}",
    )

    assert response.status_code == 403
    assert store.sources == {}
    assert any(event.get("event_type") == "agent.key_escalation_rejected" for event in store.events)
    assert raw_key not in json.dumps([event for event in store.events], default=str)


def test_vnext_agent_endpoint_rejects_agent_id_mismatch(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    _record, raw_key = create_agent_key(
        store, user_id=user_id, agent_id="openclaw", permission_profile="project_scoped_agent"
    )

    response = main_module.create_vnext_source(
        main_module.VNextSourceCaptureRequest(
            user_id=user_id,
            raw_text="Fact: keys are bound to a single agent id.",
            domain="project",
            sensitivity="private",
            agent_id="hermes",
        ),
        authorization=f"Bearer {raw_key}",
    )

    assert response.status_code == 403
    assert store.sources == {}


def test_vnext_agent_endpoint_without_keys_marks_unauthenticated_local(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    response = main_module.create_vnext_source(
        main_module.VNextSourceCaptureRequest(
            user_id=user_id,
            raw_text="Fact: fresh installs keep working without keys.",
            domain="project",
            sensitivity="private",
            agent_id="openclaw",
        )
    )

    assert response.status_code == 201
    policy_events = [event for event in store.events if event.get("event_type") == "policy.decision"]
    assert policy_events
    identity_record = policy_events[0]["payload_json"]["agent_identity"]
    assert identity_record["auth"] == "unauthenticated_local"


def _seed_active_memory(store: FakeVNextStore, *, text: str = "The quarterly plan is drafted.") -> str:
    memory_id = str(uuid4())
    store.memories.append(
        {
            "id": memory_id,
            "memory_type": "semantic",
            "memory_key": f"seed.{memory_id}",
            "value": {"text": text},
            "status": "active",
            "confidence": 0.9,
            "title": text[:60],
            "canonical_text": text,
            "summary": text,
            "domain": "professional",
            "sensitivity": "internal",
            "metadata_json": {},
            "valid_to": None,
        }
    )
    return memory_id


def test_assign_project_replaces_canonical_memory_scope_used_by_retrieval(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    memory_id = _seed_active_memory(store, text="Release scope reassignment marker.")
    memory = store.get_memory(memory_id)
    assert memory is not None
    memory.update(
        {
            "domain": "project",
            "project_id": "project-old",
            "metadata_json": {
                "project_id": "project-old",
                "project_scope": ["project-old"],
            },
        }
    )

    response = main_module.review_vnext_memory(
        main_module.UUID(memory_id),
        main_module.VNextMemoryReviewRequest(
            user_id=user_id,
            action="assign_project",
            project_id="project-new",
        ),
    )

    assert response.status_code == 200
    reassigned = store.get_memory(memory_id)
    assert reassigned is not None
    assert reassigned["project_id"] == "project-new"
    assert reassigned["metadata_json"]["project_id"] == "project-new"
    assert reassigned["metadata_json"]["project_scope"] == ["project-new"]

    def scoped_pack(project_id: str) -> dict[str, object]:
        pack_response = main_module.create_vnext_context_pack(
            main_module.VNextContextPackRequest(
                user_id=user_id,
                query="release scope reassignment marker",
                scope={"projects": [project_id]},
                options={"include_sources": False},
            )
        )
        assert pack_response.status_code == 201
        return json.loads(pack_response.body)

    assert scoped_pack("project-old")["relevant_memories"] == []
    assert [row["id"] for row in scoped_pack("project-new")["relevant_memories"]] == [memory_id]


def test_vnext_memory_expire_and_unexpire_endpoints(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    memory_id = _seed_active_memory(store)

    expired = main_module.expire_vnext_memory(
        main_module.VNextMemoryExpireRequest(user_id=user_id, memory_id=memory_id, reason="Window closed")
    )
    assert expired.status_code == 200
    expired_payload = json.loads(expired.body)
    assert expired_payload["status"] == "expired"
    assert expired_payload["valid_to"]
    assert store.get_memory(memory_id)["valid_to"] == expired_payload["valid_to"]
    # Expiry is temporal, not a lifecycle judgment: the row stays active.
    assert store.get_memory(memory_id)["status"] == "active"
    assert any(event.get("event_type") == "agent.memory_expired" for event in store.events)

    unexpired = main_module.unexpire_vnext_memory(
        main_module.VNextMemoryUnexpireRequest(user_id=user_id, memory_id=memory_id, reason="Deadline extended")
    )
    assert unexpired.status_code == 200
    assert json.loads(unexpired.body)["status"] == "active"
    assert store.get_memory(memory_id)["valid_to"] is None
    assert any(event.get("event_type") == "agent.memory_unexpired" for event in store.events)


def test_vnext_memory_accept_consolidation_endpoint_supersedes_members(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    member_id = _seed_active_memory(store, text="Standup happens in the morning.")
    candidate_id = _seed_active_memory(store, text="Standup happens every morning at 9:30am.")
    candidate = store.get_memory(candidate_id)
    candidate["status"] = "candidate"
    candidate["metadata_json"] = {
        "consolidation": {
            "proposal_kind": "merge",
            "cluster_member_ids": [member_id],
            "proposed_supersede": [member_id],
        },
        "review_required": True,
    }

    response = main_module.accept_vnext_memory_consolidation(
        main_module.VNextMemoryAcceptConsolidationRequest(
            user_id=user_id, memory_id=candidate_id, reason="Duplicates of one fact"
        )
    )

    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["status"] == "accepted"
    assert payload["superseded_member_ids"] == [member_id]
    assert store.get_memory(candidate_id)["status"] == "active"
    assert store.get_memory(member_id)["status"] == "superseded"
    assert store.get_memory(member_id)["superseded_by"] == candidate_id
    assert any(
        event.get("event_type") == "agent.memory_consolidation_accepted" for event in store.events
    )


def test_generic_http_review_delegates_consolidation_acceptance_and_rejects_stale_input(
    monkeypatch,
) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    first_id = _seed_active_memory(store, text="First duplicate fact.")
    second_id = _seed_active_memory(store, text="Second duplicate fact.")

    def seed_candidate() -> str:
        candidate_id = _seed_active_memory(store, text="Canonical merged fact.")
        candidate = store.get_memory(candidate_id)
        candidate["status"] = "candidate"
        candidate["metadata_json"] = {
            "candidate_kind": "memory_consolidation",
            "review_required": True,
            "consolidation": {
                "proposal_kind": "merge",
                "cluster_member_ids": [first_id, second_id],
                "member_snapshots": [
                    memory_version_snapshot(store.get_memory(first_id)),
                    memory_version_snapshot(store.get_memory(second_id)),
                ],
                "proposed_supersede": [first_id, second_id],
            },
        }
        return candidate_id

    candidate_id = seed_candidate()
    edited = main_module.review_vnext_memory(
        main_module.UUID(candidate_id),
        main_module.VNextMemoryReviewRequest(
            user_id=user_id,
            action="edit",
            canonical_text="Unsafe edited merge.",
        ),
    )
    assert edited.status_code == 400
    assert store.get_memory(candidate_id)["status"] == "candidate"
    assert store.get_memory(first_id)["status"] == "active"

    accepted = main_module.review_vnext_memory(
        main_module.UUID(candidate_id),
        main_module.VNextMemoryReviewRequest(
            user_id=user_id,
            action="accept",
            reason="Reviewed duplicates.",
        ),
    )
    assert accepted.status_code == 200
    payload = json.loads(accepted.body)
    assert payload["consolidation_acceptance"]["status"] == "accepted"
    assert payload["consolidation_acceptance"]["superseded_member_ids"] == [
        first_id,
        second_id,
    ]
    assert store.get_memory(candidate_id)["metadata_json"]["consolidation"]["accepted"]
    assert store.get_memory(first_id)["superseded_by"] == candidate_id

    # A stale generic approval must not partially supersede any member.
    fresh_first = _seed_active_memory(store, text="Fresh first fact.")
    fresh_second = _seed_active_memory(store, text="Fresh second fact.")
    stale_id = _seed_active_memory(store, text="Stale merge candidate.")
    stale = store.get_memory(stale_id)
    stale["status"] = "candidate"
    stale["metadata_json"] = {
        "candidate_kind": "memory_consolidation",
        "review_required": True,
        "consolidation": {
            "proposal_kind": "merge",
            "cluster_member_ids": [fresh_first, fresh_second],
            "member_snapshots": [
                memory_version_snapshot(store.get_memory(fresh_first)),
                memory_version_snapshot(store.get_memory(fresh_second)),
            ],
            "proposed_supersede": [fresh_first, fresh_second],
        },
    }
    store.get_memory(fresh_first)["canonical_text"] = "Changed after proposal."

    rejected = main_module.review_vnext_memory(
        main_module.UUID(stale_id),
        main_module.VNextMemoryReviewRequest(user_id=user_id, action="accept"),
    )
    assert rejected.status_code == 400
    assert "candidate is stale" in json.loads(rejected.body)["detail"]
    assert store.get_memory(stale_id)["status"] == "candidate"
    assert store.get_memory(fresh_first)["status"] == "active"
    assert store.get_memory(fresh_second)["status"] == "active"


def test_vnext_memory_redact_endpoint_forgets_then_scrubs(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    memory_id = _seed_active_memory(store, text="The secret codename is Kestrel.")

    response = main_module.redact_vnext_memory(
        main_module.VNextMemoryRedactRequest(user_id=user_id, memory_id=memory_id, reason="Erasure request")
    )

    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["status"] == "redacted"
    assert payload["forgotten_first"] is True
    assert payload["redaction_marker"] == "[REDACTED]"
    memory = store.get_memory(memory_id)
    assert memory["status"] == "archived"
    assert memory["canonical_text"] == "[REDACTED]"
    # Order of operations: the forget transition ran before the scrub, and
    # the memory.redacted trail survives it (earlier trail payloads are
    # themselves scrubbed by the events pass — event types are what remain).
    assert any(revision.get("revision_type") == "archived" for revision in store.revisions)
    redaction_trail = [event for event in store.events if event.get("event_type") == "memory.redacted"]
    assert len(redaction_trail) == 3  # content, revisions, and events operations
    assert redaction_trail[-1]["payload_json"].get("operation") == "redact_memory_events"

    missing = main_module.redact_vnext_memory(
        main_module.VNextMemoryRedactRequest(user_id=user_id, memory_id=uuid4(), reason="Nothing there")
    )
    assert missing.status_code == 404


def test_vnext_memory_redact_endpoint_blocks_non_admin_agents(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    memory_id = _seed_active_memory(store)

    response = main_module.redact_vnext_memory(
        main_module.VNextMemoryRedactRequest(
            user_id=user_id, memory_id=memory_id, reason="Not allowed", agent_id="hermes"
        )
    )

    assert response.status_code == 403
    assert store.get_memory(memory_id)["status"] == "active"
    blocked_events = [event for event in store.events if event.get("event_type") == "agent.policy_blocked"]
    assert blocked_events
    decision = blocked_events[0]["payload_json"]["policy_decision"]
    assert decision["action"] == "memory.redact"
    assert "human_or_admin_review_required" in decision["reasons"]


def test_vnext_memory_lifecycle_endpoints_share_agent_key_auth(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    memory_id = _seed_active_memory(store)
    _record, raw_key = create_agent_key(
        store, user_id=user_id, agent_id="hermes", permission_profile="trusted_local_agent"
    )

    # Keyless agent calls are rejected once keys exist — parity with the
    # other vNext agent endpoints.
    keyless = main_module.expire_vnext_memory(
        main_module.VNextMemoryExpireRequest(
            user_id=user_id, memory_id=memory_id, reason="Window closed", agent_id="hermes"
        )
    )
    assert keyless.status_code == 401
    assert "Authorization: Bearer alice_sk_" in json.loads(keyless.body)["detail"]
    assert store.get_memory(memory_id)["valid_to"] is None

    # With the key, the same call succeeds under the key-bound identity.
    keyed = main_module.expire_vnext_memory(
        main_module.VNextMemoryExpireRequest(
            user_id=user_id, memory_id=memory_id, reason="Window closed", agent_id="hermes"
        ),
        authorization=f"Bearer {raw_key}",
    )
    assert keyed.status_code == 200
    assert store.get_memory(memory_id)["valid_to"] is not None
    policy_events = [event for event in store.events if event.get("event_type") == "policy.decision"]
    assert policy_events
    identity_record = policy_events[-1]["payload_json"]["agent_identity"]
    assert identity_record["auth"] == "agent_api_key"

    keyless_unexpire = main_module.unexpire_vnext_memory(
        main_module.VNextMemoryUnexpireRequest(
            user_id=user_id, memory_id=memory_id, reason="Extended", agent_id="hermes"
        )
    )
    assert keyless_unexpire.status_code == 401
    keyless_redact = main_module.redact_vnext_memory(
        main_module.VNextMemoryRedactRequest(
            user_id=user_id, memory_id=memory_id, reason="Erase", agent_id="hermes"
        )
    )
    assert keyless_redact.status_code == 401
    keyless_accept = main_module.accept_vnext_memory_consolidation(
        main_module.VNextMemoryAcceptConsolidationRequest(
            user_id=user_id, memory_id=memory_id, reason="Merge", agent_id="hermes"
        )
    )
    assert keyless_accept.status_code == 401


def test_http_memory_review_rejects_non_admin_and_out_of_scope_keys(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    memory_id = _seed_active_memory(store, text="Project B review target.")
    store.get_memory(memory_id)["status"] = "candidate"
    store.get_memory(memory_id)["project_id"] = "project-b"

    _reader_record, reader_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="reader",
        permission_profile="read_only_agent",
        project_scope="project-b",
    )
    reader_response = main_module.review_vnext_memory(
        main_module.UUID(memory_id),
        main_module.VNextMemoryReviewRequest(user_id=user_id, action="accept"),
        authorization=f"Bearer {reader_key}",
    )
    assert reader_response.status_code == 403
    assert store.get_memory(memory_id)["status"] == "candidate"
    assert "human_or_admin_review_required" in json.loads(reader_response.body)["policy_decision"]["reasons"]

    _admin_record, admin_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="admin",
        permission_profile="admin_agent",
        project_scope="project-a",
    )
    scope_response = main_module.review_vnext_memory(
        main_module.UUID(memory_id),
        main_module.VNextMemoryReviewRequest(user_id=user_id, action="accept"),
        authorization=f"Bearer {admin_key}",
    )
    assert scope_response.status_code == 403
    assert store.get_memory(memory_id)["status"] == "candidate"
    assert "project_scope_binding_violation" in json.loads(scope_response.body)["policy_decision"]["reasons"]


def test_http_memory_lifecycle_authorizes_the_persisted_target_scope(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    memory_id = _seed_active_memory(store, text="Project B lifecycle target.")
    store.get_memory(memory_id)["project_id"] = "project-b"
    _record, raw_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="openclaw",
        permission_profile="project_scoped_agent",
        project_scope="project-a",
    )

    response = main_module.forget_vnext_memory(
        main_module.VNextMemoryForgetRequest(
            user_id=user_id,
            memory_id=memory_id,
            reason="Cross-project attempt.",
        ),
        authorization=f"Bearer {raw_key}",
    )

    assert response.status_code == 403
    assert store.get_memory(memory_id)["status"] == "active"
    assert "project_scope_binding_violation" in json.loads(response.body)["policy_decision"]["reasons"]


def test_agent_output_ingest_api_creates_review_only_records(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()

    response = main_module.ingest_vnext_agent_output(
        main_module.VNextAgentOutputIngestRequest(
            user_id=user_id,
            agent_id="openclaw",
            agent_type="coding_agent",
            permission_profile="project_scoped_agent",
            agent_run_id="run-1",
            project_scope=["Alice"],
            title="Sprint summary",
            content="Decision: API agent output ingestion is review-only.",
            output_type="sprint_summary",
            propose_memory=True,
        )
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["status"] == "imported"
    assert payload["artifact_id"] in store.artifacts
    assert store.artifacts[payload["artifact_id"]]["status"] == "needs_review"
    assert payload["memory_id"] is not None
    assert any(memory["status"] == "candidate" for memory in store.memories)


def test_dogfooding_dashboard_and_insight_feedback_api(monkeypatch) -> None:
    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    artifact = store.create_artifact(
        {
            "artifact_type": "daily_brief",
            "title": "Daily",
            "content_markdown": "# Daily",
            "status": "needs_review",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    store.create_artifact_quality_rating(
        {
            "artifact_id": artifact["id"],
            "usefulness": 5,
            "verbosity": "right_sized",
            "metadata_json": {},
        }
    )

    feedback_response = main_module.record_vnext_artifact_insight_feedback(
        main_module.UUID(str(artifact["id"])),
        main_module.VNextArtifactInsightFeedbackRequest(user_id=user_id, useful_insight="yes", surfaced_missed="yes"),
    )
    dashboard_response = main_module.get_vnext_dogfooding_dashboard(user_id=user_id)
    dashboard = json.loads(dashboard_response.body)

    assert feedback_response.status_code == 201
    assert dashboard_response.status_code == 200
    assert dashboard["artifact_quality_rating_count"] == 1
    assert dashboard["insight_feedback"]["useful_yes"] == 1


def test_artifact_routes_authorize_persisted_target_scope_and_profile(monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    store = FakeVNextStore(None)
    _install_fake_vnext_store(monkeypatch, store)
    user_id = uuid4()
    artifact_id = str(uuid4())
    store.artifacts[artifact_id] = {
        "id": artifact_id,
        "artifact_type": "daily_brief",
        "title": "Project B private brief",
        "content_markdown": "# Project B\n\nPrivate target content.",
        "status": "needs_review",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"project_id": "project-b"},
    }

    _reader_record, reader_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="project-b-reader",
        permission_profile="read_only_agent",
        project_scope="project-b",
    )
    feedback_status, feedback_payload = _invoke_vnext_request(
        "POST",
        f"/v0/vnext/artifacts/{artifact_id}/insight-feedback",
        authorization=f"Bearer {reader_key}",
        payload={"user_id": str(user_id), "useful_insight": "yes"},
    )
    assert feedback_status == 403
    assert "read_only_agent_cannot_write" in feedback_payload["policy_decision"]["reasons"]

    sensitive_source_id = str(uuid4())
    public_artifact_id = str(uuid4())
    store.sources[sensitive_source_id] = {
        "id": sensitive_source_id,
        "domain": "health",
        "sensitivity": "highly_sensitive",
        "metadata_json": {"project_id": "project-b", "raw_text": "VERY SECRET"},
    }
    store.artifacts[public_artifact_id] = {
        "id": public_artifact_id,
        "artifact_type": "daily_brief",
        "title": "Public shell",
        "content_markdown": "# Public shell",
        "status": "needs_review",
        "domain": "project",
        "sensitivity": "public",
        "metadata_json": {
            "project_id": "project-b",
            "source_refs": [f"source:{sensitive_source_id}"],
        },
    }
    trace_status, trace_payload = _invoke_vnext_request(
        "GET",
        f"/v0/vnext/traces/artifacts/{public_artifact_id}",
        query={"user_id": str(user_id)},
        authorization=f"Bearer {reader_key}",
    )
    assert trace_status == 200
    assert trace_payload["sources"] == []
    assert "VERY SECRET" not in json.dumps(trace_payload)

    _project_a_record, project_a_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="project-a-admin",
        permission_profile="admin_agent",
        project_scope="project-a",
    )
    denied_requests = (
        (
            "GET",
            f"/v0/vnext/artifacts/{artifact_id}",
            {"query": {"user_id": str(user_id)}},
        ),
        (
            "GET",
            f"/v0/vnext/traces/artifacts/{artifact_id}",
            {"query": {"user_id": str(user_id)}},
        ),
        (
            "POST",
            f"/v0/vnext/artifacts/{artifact_id}/review",
            {"payload": {"user_id": str(user_id), "action": "accept"}},
        ),
        (
            "POST",
            f"/v0/vnext/artifacts/{artifact_id}/quality-ratings",
            {"payload": {"user_id": str(user_id), "verbosity": "right_sized"}},
        ),
        (
            "POST",
            f"/v0/vnext/artifacts/{artifact_id}/export",
            {"payload": {"user_id": str(user_id), "output_dir": "/tmp"}},
        ),
    )
    for method, path, kwargs in denied_requests:
        status, payload = _invoke_vnext_request(
            method,
            path,
            authorization=f"Bearer {project_a_key}",
            **kwargs,
        )
        assert status == 403, (method, path, payload)
        assert "project_scope_binding_violation" in payload["policy_decision"]["reasons"]
        assert "content_markdown" not in payload

    _trusted_b_record, trusted_b_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="project-b-trusted",
        permission_profile="trusted_local_agent",
        project_scope="project-b",
    )
    assert _invoke_vnext_request(
        "GET",
        f"/v0/vnext/artifacts/{artifact_id}",
        query={"user_id": str(user_id)},
        authorization=f"Bearer {trusted_b_key}",
    )[0] == 200
    assert _invoke_vnext_request(
        "GET",
        f"/v0/vnext/traces/artifacts/{artifact_id}",
        query={"user_id": str(user_id)},
        authorization=f"Bearer {trusted_b_key}",
    )[0] == 200
    assert _invoke_vnext_request(
        "POST",
        f"/v0/vnext/artifacts/{artifact_id}/insight-feedback",
        authorization=f"Bearer {trusted_b_key}",
        payload={"user_id": str(user_id), "useful_insight": "yes"},
    )[0] == 201
    assert _invoke_vnext_request(
        "POST",
        f"/v0/vnext/artifacts/{artifact_id}/quality-ratings",
        authorization=f"Bearer {trusted_b_key}",
        payload={"user_id": str(user_id), "verbosity": "right_sized", "usefulness": 5},
    )[0] == 201
    assert _invoke_vnext_request(
        "POST",
        f"/v0/vnext/artifacts/{artifact_id}/export",
        authorization=f"Bearer {trusted_b_key}",
        payload={"user_id": str(user_id), "output_dir": "/tmp"},
    )[0] == 200

    _admin_b_record, admin_b_key = create_agent_key(
        store,
        user_id=user_id,
        agent_id="project-b-admin",
        permission_profile="admin_agent",
        project_scope="project-b",
    )
    assert _invoke_vnext_request(
        "POST",
        f"/v0/vnext/artifacts/{artifact_id}/review",
        authorization=f"Bearer {admin_b_key}",
        payload={"user_id": str(user_id), "action": "accept"},
    )[0] == 200

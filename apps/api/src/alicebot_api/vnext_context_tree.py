from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


DEFAULT_CONTEXT_TREE_LIMIT = 12
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")


class VNextContextTreeValidationError(ValueError):
    """Raised when context-tree inputs are invalid."""


class VNextContextTreeStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def list_projects(self, **kwargs) -> list[JsonObject]: ...

    def search_sources(self, **kwargs) -> list[JsonObject]: ...

    def search_memories(self, **kwargs) -> list[JsonObject]: ...

    def list_open_loops(self, **kwargs) -> list[JsonObject]: ...

    def list_artifacts(self, **kwargs) -> list[JsonObject]: ...

    def list_events(self, **kwargs) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class ContextTreeRequest:
    query: str = ""
    domains: tuple[str, ...] = ()
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    limit: int = DEFAULT_CONTEXT_TREE_LIMIT
    include_events: bool = True
    generated_by: str = "system"
    agent_identity: JsonObject | None = None
    policy_decision: JsonObject | None = None
    trace_id: str | None = None


def _validate_request(request: ContextTreeRequest) -> None:
    if request.limit < 1 or request.limit > 50:
        raise VNextContextTreeValidationError("limit must be between 1 and 50")
    if not request.sensitivity_allowed:
        raise VNextContextTreeValidationError("sensitivity_allowed must not be empty")


def _domains(request: ContextTreeRequest) -> list[str] | None:
    return list(request.domains) if request.domains else None


def _sensitivity(request: ContextTreeRequest) -> list[str]:
    return list(request.sensitivity_allowed)


def _node(
    *,
    node_id: str,
    label: str,
    node_type: str,
    ref: str | None = None,
    children: list[JsonObject] | None = None,
    metadata: JsonObject | None = None,
) -> JsonObject:
    payload: JsonObject = {
        "id": node_id,
        "label": label,
        "type": node_type,
        "ref": ref,
        "children": children or [],
        "metadata": metadata or {},
    }
    payload["child_count"] = len(payload["children"]) if isinstance(payload["children"], list) else 0
    return payload


def _label(row: JsonObject, *keys: str, fallback: str) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())[:180]
    return fallback


def _row_node(prefix: str, row: JsonObject, *, label_keys: tuple[str, ...], fallback: str) -> JsonObject:
    row_id = str(row.get("id", "unknown"))
    return _node(
        node_id=f"{prefix}:{row_id}",
        label=_label(row, *label_keys, fallback=fallback),
        node_type=prefix,
        ref=f"{prefix}:{row_id}",
        metadata={
            key: row.get(key)
            for key in (
                "domain",
                "sensitivity",
                "status",
                "memory_type",
                "artifact_type",
                "source_type",
                "updated_at",
                "created_at",
                "captured_at",
            )
            if row.get(key) is not None
        },
    )


class VNextContextTreeService:
    def __init__(self, store: VNextContextTreeStore) -> None:
        self.store = store

    def build_tree(self, request: ContextTreeRequest | None = None) -> JsonObject:
        request = request or ContextTreeRequest()
        _validate_request(request)
        trace_id = request.trace_id or str(uuid4())
        domains = _domains(request)
        sensitivity = _sensitivity(request)
        query = request.query or "project decision preference open loop artifact"

        projects = self.store.list_projects(
            status="active",
            domains=domains,
            sensitivity_allowed=sensitivity,
            limit=request.limit,
        )
        memories = self.store.search_memories(
            query=query,
            domains=domains,
            sensitivity_allowed=sensitivity,
            limit=request.limit,
        )
        sources = self.store.search_sources(
            query=query,
            domains=domains,
            sensitivity_allowed=sensitivity,
            limit=request.limit,
        )
        open_loops = self.store.list_open_loops(
            status="open",
            domains=domains,
            sensitivity_allowed=sensitivity,
            limit=request.limit,
        )
        artifacts = self.store.list_artifacts(
            domains=domains,
            sensitivity_allowed=sensitivity,
            limit=request.limit,
        )
        events = self.store.list_events(limit=request.limit) if request.include_events else []

        roots = [
            _node(
                node_id="root:projects",
                label="Projects",
                node_type="group",
                children=[
                    _row_node("project", row, label_keys=("name", "title", "slug"), fallback="Project")
                    for row in projects
                ],
            ),
            _node(
                node_id="root:memories",
                label="Memories",
                node_type="group",
                children=[
                    _row_node("memory", row, label_keys=("title", "canonical_text", "memory_key"), fallback="Memory")
                    for row in memories
                ],
            ),
            _node(
                node_id="root:sources",
                label="Sources",
                node_type="group",
                children=[
                    _row_node("source", row, label_keys=("title", "source_type"), fallback="Source")
                    for row in sources
                ],
            ),
            _node(
                node_id="root:open_loops",
                label="Open Loops",
                node_type="group",
                children=[
                    _row_node("open_loop", row, label_keys=("title", "description"), fallback="Open loop")
                    for row in open_loops
                ],
            ),
            _node(
                node_id="root:artifacts",
                label="Artifacts",
                node_type="group",
                children=[
                    _row_node("artifact", row, label_keys=("title", "artifact_type"), fallback="Artifact")
                    for row in artifacts
                ],
            ),
            _node(
                node_id="root:events",
                label="Recent Events",
                node_type="group",
                children=[
                    _row_node("event", row, label_keys=("event_type",), fallback="Event")
                    for row in events
                ],
            ),
        ]
        summary = {
            "projects": len(projects),
            "memories": len(memories),
            "sources": len(sources),
            "open_loops": len(open_loops),
            "artifacts": len(artifacts),
            "events": len(events),
        }
        payload = {
            "schema_version": "vnext_context_tree_v0",
            "generated_at": datetime.now(UTC).isoformat(),
            "trace_id": trace_id,
            "query": request.query,
            "read_only": True,
            "summary": summary,
            "roots": roots,
            "agent_identity": request.agent_identity,
            "policy_decision": request.policy_decision,
        }
        append_event(
            self.store,
            event_type="context_tree.generated",
            actor_type=request.generated_by,
            target_type="context_tree",
            target_id=trace_id,
            trace_id=trace_id,
            payload={"summary": summary, "read_only": True},
        )
        return payload


__all__ = [
    "ContextTreeRequest",
    "VNextContextTreeService",
    "VNextContextTreeStore",
    "VNextContextTreeValidationError",
]

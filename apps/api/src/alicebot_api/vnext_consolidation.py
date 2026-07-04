from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Protocol

from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_model_intelligence import (
    ModelBackedRequest,
    ModelRoutingRequest,
    build_model_backed_artifact,
    resolve_model_route,
)
from alicebot_api.vnext_repositories import JsonObject


DEFAULT_CONSOLIDATION_LIMIT = 12
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
SENSITIVITY_RANK = {
    "public": 1,
    "internal": 2,
    "unknown": 2,
    "private": 3,
    "confidential": 4,
    "highly_sensitive": 5,
    "sacred": 6,
    "regulated": 6,
}


class VNextConsolidationValidationError(ValueError):
    """Raised when a memory-consolidation request is invalid."""


class VNextConsolidationStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def list_memories(self, *, status: str | None = None) -> list[JsonObject]: ...

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONSOLIDATION_LIMIT,
    ) -> list[JsonObject]: ...

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONSOLIDATION_LIMIT,
    ) -> list[JsonObject]: ...

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONSOLIDATION_LIMIT,
    ) -> list[JsonObject]: ...

    def list_events(self, **kwargs) -> list[JsonObject]: ...

    def list_artifact_quality_ratings(self, **kwargs) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class MemoryConsolidationRequest:
    domains: tuple[str, ...] = ()
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    generated_for: str | None = None
    source_limit: int = DEFAULT_CONSOLIDATION_LIMIT
    memory_limit: int = DEFAULT_CONSOLIDATION_LIMIT
    artifact_limit: int = 8
    event_limit: int = 30
    rating_limit: int = 20
    create_candidate_memories: bool = True
    generated_by: str = "system"
    trace_id: str | None = None
    run_id: str | None = None
    agent_identity: JsonObject | None = None
    policy_decision: JsonObject | None = None
    metadata_json: JsonObject = field(default_factory=dict)
    generation_mode: str = "deterministic"
    model_route_mode: str | None = None
    model_provider: str | None = None
    model: str | None = None
    model_temperature: float = 0.2
    allow_cloud_private: bool = False


def _validate_request(request: MemoryConsolidationRequest) -> None:
    if not request.sensitivity_allowed:
        raise VNextConsolidationValidationError("sensitivity_allowed must not be empty")
    if request.generation_mode not in {"deterministic", "model_backed"}:
        raise VNextConsolidationValidationError("generation_mode must be deterministic or model_backed")
    for field_name in ("source_limit", "memory_limit", "artifact_limit", "event_limit", "rating_limit"):
        value = getattr(request, field_name)
        if value < 1 or value > 100:
            raise VNextConsolidationValidationError(f"{field_name} must be between 1 and 100")
    if request.model_temperature < 0.0 or request.model_temperature > 2.0:
        raise VNextConsolidationValidationError("model_temperature must be between 0.0 and 2.0")


def _allowed_domains(request: MemoryConsolidationRequest) -> list[str] | None:
    return list(request.domains) if request.domains else None


def _allowed_sensitivity(request: MemoryConsolidationRequest) -> list[str]:
    return list(request.sensitivity_allowed)


def _highest_sensitivity(rows: list[JsonObject]) -> str:
    sensitivities = [str(row.get("sensitivity", "unknown")) for row in rows]
    if not sensitivities:
        return "unknown"
    return max(sensitivities, key=lambda value: SENSITIVITY_RANK.get(value, SENSITIVITY_RANK["unknown"]))


def _domain(request: MemoryConsolidationRequest, rows: list[JsonObject]) -> str:
    if len(request.domains) == 1:
        return request.domains[0]
    domains = {row.get("domain") for row in rows if isinstance(row.get("domain"), str)}
    if len(domains) == 1:
        return str(next(iter(domains)))
    return "unknown"


def _text(row: JsonObject) -> str:
    for key in ("canonical_text", "summary", "title", "content_markdown", "memory_key"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    metadata = row.get("metadata_json")
    if isinstance(metadata, dict):
        raw_text = metadata.get("raw_text")
        if isinstance(raw_text, str) and raw_text.strip():
            return " ".join(raw_text.split())
    return str(row.get("id", "item"))


def _ref(prefix: str, row: JsonObject) -> str | None:
    value = row.get("id")
    return None if value is None else f"{prefix}:{value}"


def _digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()[:16]


def _source_refs(rows: list[JsonObject]) -> list[str]:
    refs = [
        ref
        for ref in (
            *(_ref("source", row) for row in rows if row.get("source_type") is not None),
            *(_ref("memory", row) for row in rows if row.get("memory_key") is not None),
            *(_ref("artifact", row) for row in rows if row.get("artifact_type") is not None),
        )
        if ref is not None
    ]
    return list(dict.fromkeys(refs))


def _existing_candidate_ids(store: VNextConsolidationStore, digest: str) -> list[str]:
    matches: list[str] = []
    for memory in store.list_memories(status="candidate"):
        metadata = memory.get("metadata_json")
        if isinstance(metadata, dict) and metadata.get("consolidation_digest") == digest and memory.get("id") is not None:
            matches.append(str(memory["id"]))
    return matches


class VNextConsolidationService:
    def __init__(self, store: VNextConsolidationStore) -> None:
        self.store = store

    def generate_memory_consolidation(self, request: MemoryConsolidationRequest | None = None) -> JsonObject:
        request = request or MemoryConsolidationRequest()
        _validate_request(request)
        domains = _allowed_domains(request)
        sensitivity = _allowed_sensitivity(request)
        sources = self.store.search_sources(
            query="decision preference fact todo procedure pattern",
            domains=domains,
            sensitivity_allowed=sensitivity,
            limit=request.source_limit,
        )
        memories = self.store.search_memories(
            query="decision preference project procedure pattern",
            domains=domains,
            sensitivity_allowed=sensitivity,
            limit=request.memory_limit,
        )
        memories = [row for row in memories if row.get("status") in {"active", "accepted"}]
        artifacts = self.store.list_artifacts(
            domains=domains,
            sensitivity_allowed=sensitivity,
            limit=request.artifact_limit,
        )
        artifacts = [row for row in artifacts if row.get("artifact_type") != "memory_consolidation"]
        events = self.store.list_events(limit=request.event_limit)
        try:
            ratings = self.store.list_artifact_quality_ratings(limit=request.rating_limit)
        except AttributeError:
            ratings = []

        input_rows = [*sources, *memories, *artifacts]
        digest = _digest_payload(
            {
                "sources": [str(row.get("id")) for row in sources],
                "memories": [str(row.get("id")) for row in memories],
                "artifacts": [str(row.get("id")) for row in artifacts],
                "ratings": [str(row.get("id")) for row in ratings[:10]],
            }
        )
        refs = _source_refs(input_rows)
        candidate_ids = _existing_candidate_ids(self.store, digest)
        candidate_theme_lines = [
            f"- {_text(row)[:220]} [{ref}]"
            for row, ref in (
                (row, _ref("memory", row) or _ref("source", row) or _ref("artifact", row) or "unlinked")
                for row in input_rows[:10]
            )
        ]
        if not candidate_theme_lines:
            candidate_theme_lines = ["- No consolidation input matched this scope."]

        lines = [
            f"# Memory Consolidation - {request.generated_for or datetime.now(UTC).date().isoformat()}",
            "",
            "## Consolidation Summary",
            f"- Sources scanned: {len(sources)}",
            f"- Active memories scanned: {len(memories)}",
            f"- Generated artifacts scanned: {len(artifacts)}",
            f"- Recent events scanned: {len(events)}",
            f"- Artifact ratings scanned: {len(ratings)}",
            "",
            "## Candidate Themes",
            *candidate_theme_lines,
            "",
            "## Review Policy",
            "- This artifact is review-only.",
            "- Consolidation may create candidate memories, but it does not promote or update trusted memory automatically.",
            "- Review accepted candidates in `/vnext` before they affect future recall.",
        ]
        content = "\n".join(lines)
        metadata = {
            **request.metadata_json,
            "workflow": "memory_consolidation",
            "workflow_type": "memory_consolidation",
            "trace_id": request.trace_id,
            "scheduler_run_id": request.run_id,
            "review_status": "needs_review",
            "generation_mode": request.generation_mode,
            "source_refs": refs,
            "consolidation_digest": digest,
            "candidate_memory_ids": candidate_ids,
            "input_counts": {
                "sources": len(sources),
                "memories": len(memories),
                "artifacts": len(artifacts),
                "events": len(events),
                "ratings": len(ratings),
            },
            "policy_decision": request.policy_decision,
            "agent_identity": request.agent_identity,
        }
        prompt_hash: str | None = None
        model_info_json: JsonObject | None = None
        if request.generation_mode == "model_backed":
            route = resolve_model_route(
                ModelRoutingRequest(
                    workflow_type="memory_consolidation",
                    generation_mode="model_backed",
                    domains=request.domains,
                    sensitivity_allowed=request.sensitivity_allowed,
                    agent_identity=request.agent_identity,
                    brain_charter=self._brain_charter(),
                    requested_route_mode=request.model_route_mode,
                    requested_provider=request.model_provider,
                    requested_model=request.model,
                    allow_cloud_private=request.allow_cloud_private,
                )
            )
            model_artifact = build_model_backed_artifact(
                ModelBackedRequest(
                    workflow_type="memory_consolidation",
                    title=f"Memory Consolidation - {request.generated_for or datetime.now(UTC).date().isoformat()}",
                    deterministic_markdown=content,
                    context_rows=tuple(input_rows),
                    source_refs=tuple(refs),
                    open_questions=("Which candidate consolidation should be promoted, edited, or rejected?",),
                    trace_id=request.trace_id,
                    route=route,
                    temperature=request.model_temperature,
                    config={"generated_by": request.generated_by},
                )
            )
            content = model_artifact.content_markdown
            prompt_hash = model_artifact.prompt_hash
            model_info_json = model_artifact.model_info
            metadata = {**metadata, **model_artifact.metadata}

        if request.create_candidate_memories and input_rows and not candidate_ids:
            candidate = self.store.create_memory(
                {
                    "memory_key": f"vnext.consolidation.{digest}",
                    "value": {
                        "kind": "memory_consolidation",
                        "consolidation_digest": digest,
                        "source_refs": refs,
                    },
                    "status": "candidate",
                    "memory_type": "semantic",
                    "confidence": 0.72,
                    "trust_class": "llm_single_source" if request.generation_mode == "model_backed" else "deterministic",
                    "promotion_eligibility": "promotable",
                    "title": f"Consolidated memory candidate {digest}",
                    "canonical_text": "Review this consolidation candidate before promoting it into trusted memory.",
                    "summary": f"Candidate produced from {len(sources)} sources, {len(memories)} memories, and {len(artifacts)} artifacts.",
                    "domain": _domain(request, input_rows),
                    "sensitivity": _highest_sensitivity(input_rows),
                    "metadata_json": {
                        "candidate_kind": "memory_consolidation",
                        "consolidation_digest": digest,
                        "source_refs": refs,
                        "review_required": True,
                    },
                },
                actor_type=request.generated_by,
            )
            candidate_ids = [str(candidate["id"])]
            metadata = {**metadata, "candidate_memory_ids": candidate_ids}

        artifact = self.store.create_artifact(
            {
                "artifact_type": "memory_consolidation",
                "title": f"Memory Consolidation - {request.generated_for or datetime.now(UTC).date().isoformat()}",
                "content_markdown": content,
                "status": "needs_review",
                "domain": _domain(request, input_rows),
                "sensitivity": _highest_sensitivity(input_rows),
                "generated_by": request.generated_by,
                "prompt_hash": prompt_hash,
                "model_info_json": model_info_json,
                "metadata_json": metadata,
            },
            actor_type=request.generated_by,
        )
        append_event(
            self.store,
            event_type="memory.consolidation.generated",
            actor_type=request.generated_by,
            target_type="artifact",
            target_id=str(artifact["id"]),
            trace_id=request.trace_id,
            run_id=request.run_id,
            payload={
                "consolidation_digest": digest,
                "candidate_memory_ids": candidate_ids,
                "input_counts": metadata["input_counts"],
            },
        )
        return artifact

    def _brain_charter(self) -> JsonObject | None:
        getter = getattr(self.store, "get_brain_charter", None)
        if not callable(getter):
            return None
        charter = getter()
        return charter if isinstance(charter, dict) else None


__all__ = [
    "MemoryConsolidationRequest",
    "VNextConsolidationService",
    "VNextConsolidationStore",
    "VNextConsolidationValidationError",
]

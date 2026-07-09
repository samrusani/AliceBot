from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Protocol

from alicebot_api.memory_provenance import (
    ASSERTION_CLASS_ASSISTANT_ESTIMATE,
    ASSERTION_CLASS_USER_ASSERTED,
    PROVENANCE_ROLE_USER,
    classify_assertion,
    derive_speaker_role,
    order_by_provenance,
    provenance_promotion_rank,
)
from alicebot_api.vnext_embeddings import attach_memory_embedding
from alicebot_api.vnext_entities import (
    ENTITY_EXTRACTION_SKIP_SENSITIVITIES,
    EntityLinkingService,
    store_supports_entity_linking,
)
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


DEFAULT_CHUNK_MAX_CHARS = 2_400
SUPPORTED_TEXT_SUFFIXES = frozenset({".md", ".markdown", ".txt", ".text"})


class VNextCaptureValidationError(ValueError):
    """Raised when a vNext capture request cannot be normalized."""


class VNextCaptureStore(Protocol):
    def append_event(self, event: JsonObject) -> JsonObject: ...

    def get_source_by_content_hash(self, content_hash: str) -> JsonObject | None: ...

    def create_source(self, source: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def create_source_chunk(self, chunk: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def create_provenance_link(self, link: JsonObject, *, actor_type: str = "system") -> JsonObject: ...


@dataclass(frozen=True, slots=True)
class CaptureCandidate:
    text: str
    memory_type: str
    source_chunk_id: str
    source_chunk_index: int
    confidence: float
    extraction_rule: str
    # Speaker provenance, derived only from a leading "[USER]:" /
    # "[ASSISTANT]:" transcript tag in the line itself (content shape, never
    # external labels). None for untagged content, which keeps the exact
    # pre-provenance candidate shape.
    provenance_role: str | None = None
    assertion_class: str | None = None


@dataclass(frozen=True, slots=True)
class CaptureResult:
    status: str
    source_id: str | None
    content_hash: str
    chunk_count: int = 0
    candidate_memory_count: int = 0
    duplicate: bool = False
    errors: tuple[str, ...] = ()

    def to_record(self) -> JsonObject:
        return {
            "status": self.status,
            "source_id": self.source_id,
            "content_hash": self.content_hash,
            "chunk_count": self.chunk_count,
            "candidate_memory_count": self.candidate_memory_count,
            "duplicate": self.duplicate,
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class BatchImportResult:
    status: str
    imported_count: int
    duplicate_count: int
    failed_count: int
    source_ids: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_record(self) -> JsonObject:
        return {
            "status": self.status,
            "imported_count": self.imported_count,
            "duplicate_count": self.duplicate_count,
            "failed_count": self.failed_count,
            "source_ids": list(self.source_ids),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class SourceCaptureInput:
    source_type: str
    raw_text: str
    title: str | None = None
    author: str | None = None
    uri: str | None = None
    raw_path: str | None = None
    connector_name: str | None = None
    external_id: str | None = None
    domain: str = "unknown"
    sensitivity: str = "unknown"
    captured_at: str | None = None
    source_created_at: str | None = None
    source_modified_at: str | None = None
    metadata_json: JsonObject = field(default_factory=dict)


def normalize_text(raw_text: str) -> str:
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if normalized == "":
        raise VNextCaptureValidationError("source text must not be empty")
    return normalized


def content_hash_for_text(raw_text: str) -> str:
    normalized = normalize_text(raw_text)
    return "sha256:" + sha256(normalized.encode("utf-8")).hexdigest()


def _truncate(value: str, *, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def _split_large_part(part: str, *, max_chars: int) -> list[str]:
    words = part.split()
    if not words:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in words:
        if len(word) > max_chars:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_length = 0
            chunks.extend(word[index : index + max_chars] for index in range(0, len(word), max_chars))
            continue

        projected_length = current_length + len(word) + (1 if current else 0)
        if current and projected_length > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_length = len(word)
            continue

        current.append(word)
        current_length = projected_length

    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_text(raw_text: str, *, max_chars: int = DEFAULT_CHUNK_MAX_CHARS) -> list[str]:
    if max_chars < 200:
        raise VNextCaptureValidationError("chunk max_chars must be at least 200")

    normalized = normalize_text(raw_text)
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_large_part(paragraph, max_chars=max_chars))
            continue

        separator = "\n\n" if current else ""
        projected = f"{current}{separator}{paragraph}"
        if current and len(projected) > max_chars:
            chunks.append(current)
            current = paragraph
            continue
        current = projected

    if current:
        chunks.append(current)
    return chunks or [normalized]


_PREFIX_RULES: tuple[tuple[str, str, float, str], ...] = (
    ("decision:", "decision", 0.86, "prefixed_decision"),
    ("preference:", "preference", 0.84, "prefixed_preference"),
    ("prefer:", "preference", 0.82, "prefixed_preference"),
    ("remember:", "semantic", 0.82, "prefixed_semantic"),
    ("fact:", "semantic", 0.82, "prefixed_semantic"),
    ("belief:", "belief", 0.78, "prefixed_belief"),
    ("question:", "question", 0.72, "prefixed_question"),
    ("answer:", "answer", 0.72, "prefixed_answer"),
    ("commitment:", "open_loop", 0.76, "prefixed_commitment"),
    ("todo:", "open_loop", 0.74, "prefixed_open_loop"),
    ("next action:", "open_loop", 0.74, "prefixed_open_loop"),
    ("procedure:", "procedure", 0.80, "prefixed_procedure"),
    ("playbook:", "procedure", 0.80, "prefixed_procedure"),
    ("happened:", "episode", 0.74, "prefixed_episode"),
    ("log:", "episode", 0.72, "prefixed_episode"),
)

# "How to ..." lines are playbook headings, not colon prefixes, so the whole
# line is kept as the candidate text. Lines ending in "?" stay with the
# existing question rule: "How to fix the printer?" is a question the user
# asked, not procedure content.
_HOW_TO_PREFIX = "how to "


def _strip_markdown_prefix(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^[-*]\s+", "", stripped)
    stripped = re.sub(r"^\d+\.\s+", "", stripped)
    stripped = re.sub(r"^#{1,6}\s+", "", stripped)
    return stripped.strip()


# Confidence bias for speaker-classified assertions (bias, not suppression:
# assistant estimates keep a healthy floor and still capture/promote).
USER_ASSERTED_CONFIDENCE_BOOST = 0.08
USER_ASSERTED_CONFIDENCE_CAP = 0.95
ASSISTANT_ESTIMATE_CONFIDENCE_PENALTY = 0.06
ASSISTANT_ESTIMATE_CONFIDENCE_FLOOR = 0.30
USER_ASSERTED_VALUE_CONFIDENCE = 0.72


def _annotate_candidate_provenance(candidate: CaptureCandidate) -> CaptureCandidate:
    """Attach speaker provenance and apply the assertion-class confidence bias.

    Gated on a leading speaker tag in the candidate text: untagged content
    derives no role and is returned unchanged (byte-identical old path).
    """
    role = derive_speaker_role(candidate.text)
    if role is None:
        return candidate
    assertion_class = classify_assertion(candidate.text, role)
    confidence = candidate.confidence
    if assertion_class == ASSERTION_CLASS_USER_ASSERTED:
        confidence = min(USER_ASSERTED_CONFIDENCE_CAP, confidence + USER_ASSERTED_CONFIDENCE_BOOST)
    elif assertion_class == ASSERTION_CLASS_ASSISTANT_ESTIMATE:
        confidence = max(ASSISTANT_ESTIMATE_CONFIDENCE_FLOOR, confidence - ASSISTANT_ESTIMATE_CONFIDENCE_PENALTY)
    return replace(
        candidate,
        confidence=round(confidence, 4),
        provenance_role=role,
        assertion_class=assertion_class,
    )


def candidate_promotion_rank(candidate: CaptureCandidate) -> int:
    """Promotion-rank ordinal for a capture candidate (lower wins ties)."""
    return provenance_promotion_rank(
        provenance_role=candidate.provenance_role,
        assertion_class=candidate.assertion_class,
    )


def order_candidates_for_promotion(candidates: list[CaptureCandidate]) -> list[CaptureCandidate]:
    """Same-slot promotion bias: user-asserted values outrank assistant estimates.

    Stable ordering by provenance rank only — candidate lists without any
    speaker-tagged content come back in their original order unchanged.
    """
    return order_by_provenance(candidates, rank_of=candidate_promotion_rank)


def _candidate_from_line(line: str, *, source_chunk_id: str, source_chunk_index: int) -> CaptureCandidate | None:
    candidate = _base_candidate_from_line(
        line,
        source_chunk_id=source_chunk_id,
        source_chunk_index=source_chunk_index,
    )
    if candidate is not None:
        return _annotate_candidate_provenance(candidate)

    # New (gated) rule: a speaker-tagged USER line asserting a concrete
    # value in the first person ("[USER]: I paid $50 for the taxi") becomes
    # a semantic candidate even though it matches no legacy rule. Untagged
    # lines never reach this branch with a role, so the legacy behavior is
    # byte-identical for them.
    normalized = _strip_markdown_prefix(line)
    if not normalized:
        return None
    role = derive_speaker_role(normalized)
    if role != PROVENANCE_ROLE_USER:
        return None
    if classify_assertion(normalized, role) != ASSERTION_CLASS_USER_ASSERTED:
        return None
    return CaptureCandidate(
        text=normalized,
        memory_type="semantic",
        source_chunk_id=source_chunk_id,
        source_chunk_index=source_chunk_index,
        confidence=USER_ASSERTED_VALUE_CONFIDENCE,
        extraction_rule="user_asserted_value",
        provenance_role=role,
        assertion_class=ASSERTION_CLASS_USER_ASSERTED,
    )


def _base_candidate_from_line(line: str, *, source_chunk_id: str, source_chunk_index: int) -> CaptureCandidate | None:
    normalized = _strip_markdown_prefix(line)
    if not normalized or normalized == "---":
        return None

    lowered = normalized.casefold()
    for prefix, memory_type, confidence, rule in _PREFIX_RULES:
        if not lowered.startswith(prefix):
            continue
        text = normalized[len(prefix) :].strip()
        if text:
            return CaptureCandidate(
                text=text,
                memory_type=memory_type,
                source_chunk_id=source_chunk_id,
                source_chunk_index=source_chunk_index,
                confidence=confidence,
                extraction_rule=rule,
            )

    if lowered.startswith(_HOW_TO_PREFIX) and len(normalized) > len(_HOW_TO_PREFIX) and not normalized.endswith("?"):
        return CaptureCandidate(
            text=normalized,
            memory_type="procedure",
            source_chunk_id=source_chunk_id,
            source_chunk_index=source_chunk_index,
            confidence=0.68,
            extraction_rule="how_to_procedure",
        )

    if normalized.endswith("?"):
        return CaptureCandidate(
            text=normalized,
            memory_type="question",
            source_chunk_id=source_chunk_id,
            source_chunk_index=source_chunk_index,
            confidence=0.62,
            extraction_rule="question_sentence",
        )

    if len(normalized) >= 24 and re.search(r"\b(is|are|was|were|will|should|needs?|must|prefers?)\b", lowered):
        return CaptureCandidate(
            text=normalized,
            memory_type="semantic",
            source_chunk_id=source_chunk_id,
            source_chunk_index=source_chunk_index,
            confidence=0.58,
            extraction_rule="claim_sentence",
        )

    return None


def extract_candidate_memories(chunks: list[JsonObject]) -> list[CaptureCandidate]:
    candidates: list[CaptureCandidate] = []
    seen: set[str] = set()
    for chunk in chunks:
        chunk_id = str(chunk["id"])
        chunk_index = int(chunk["chunk_index"])
        text = str(chunk["text"])
        for line in text.splitlines():
            candidate = _candidate_from_line(
                line,
                source_chunk_id=chunk_id,
                source_chunk_index=chunk_index,
            )
            if candidate is None:
                continue
            dedupe_key = f"{candidate.memory_type}:{candidate.text.casefold()}"
            if dedupe_key in seen:
                continue
            candidates.append(candidate)
            seen.add(dedupe_key)
    return candidates


def _memory_key(*, content_hash: str, candidate: CaptureCandidate) -> str:
    digest = sha256(f"{content_hash}|{candidate.source_chunk_index}|{candidate.text}".encode("utf-8")).hexdigest()[:16]
    return f"vnext.capture.{candidate.memory_type}.{digest}"


def _extract_text_from_json_value(value: object) -> list[str]:
    if isinstance(value, str):
        normalized = " ".join(value.split()).strip()
        return [normalized] if normalized else []

    if isinstance(value, list):
        texts: list[str] = []
        for item in value:
            texts.extend(_extract_text_from_json_value(item))
        return texts

    if not isinstance(value, dict):
        return []

    texts = []
    for key in ("text", "message"):
        if key in value:
            texts.extend(_extract_text_from_json_value(value[key]))

    content = value.get("content")
    if isinstance(content, dict):
        for key in ("parts", "text", "content", "message"):
            if key in content:
                texts.extend(_extract_text_from_json_value(content[key]))
    elif content is not None:
        texts.extend(_extract_text_from_json_value(content))

    mapping = value.get("mapping")
    if isinstance(mapping, dict):
        for node_key in sorted(mapping):
            texts.extend(_extract_text_from_json_value(mapping[node_key]))

    for key in ("messages", "conversations", "items", "records"):
        if key in value:
            texts.extend(_extract_text_from_json_value(value[key]))

    deduped: list[str] = []
    seen: set[str] = set()
    for text in texts:
        if text in seen:
            continue
        deduped.append(text)
        seen.add(text)
    return deduped


class VNextCaptureService:
    def __init__(
        self,
        store: VNextCaptureStore,
        *,
        chunk_max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
        actor_type: str = "system",
        actor_id: str | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
        agent_identity: JsonObject | None = None,
        policy_decision: JsonObject | None = None,
    ) -> None:
        self.store = store
        self.chunk_max_chars = chunk_max_chars
        self.actor_type = actor_type
        self.actor_id = actor_id
        self.trace_id = trace_id
        self.run_id = run_id
        self.agent_identity = agent_identity
        self.policy_decision = policy_decision

    def _log_event(
        self,
        *,
        event_type: str,
        payload: JsonObject,
        target_type: str | None = None,
        target_id: str | None = None,
    ) -> JsonObject:
        return append_event(
            self.store,
            event_type=event_type,
            actor_type=self.actor_type,
            actor_id=self.actor_id,
            trace_id=self.trace_id,
            run_id=self.run_id,
            payload={
                **payload,
                "agent_identity": self.agent_identity,
                "policy_decision": self.policy_decision,
            },
            target_type=target_type,
            target_id=target_id,
        )

    def _log_failure(self, *, source_type: str, title: str | None, error: Exception, metadata: JsonObject) -> None:
        self._log_event(
            event_type="source.import_failed",
            target_type="source",
            payload={
                "source_type": source_type,
                "title": title,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "metadata_json": metadata,
            },
        )

    def capture_text(
        self,
        raw_text: str,
        *,
        title: str | None = None,
        domain: str = "unknown",
        sensitivity: str = "unknown",
        metadata_json: JsonObject | None = None,
    ) -> CaptureResult:
        return self.capture_source(
            SourceCaptureInput(
                source_type="manual_text",
                title=title,
                raw_text=raw_text,
                domain=domain,
                sensitivity=sensitivity,
                metadata_json=metadata_json or {},
            )
        )

    def capture_file(
        self,
        path: str | Path,
        *,
        domain: str = "unknown",
        sensitivity: str = "unknown",
        metadata_json: JsonObject | None = None,
    ) -> CaptureResult:
        file_path = Path(path).expanduser().resolve()
        if file_path.suffix.casefold() not in SUPPORTED_TEXT_SUFFIXES:
            raise VNextCaptureValidationError(f"unsupported vNext text source type: {file_path.suffix}")
        raw_text = file_path.read_text(encoding="utf-8")
        return self.capture_source(
            SourceCaptureInput(
                source_type="file",
                title=file_path.name,
                raw_text=raw_text,
                raw_path=str(file_path),
                connector_name="manual_file",
                external_id=str(file_path),
                domain=domain,
                sensitivity=sensitivity,
                metadata_json={
                    **(metadata_json or {}),
                    "filename": file_path.name,
                    "suffix": file_path.suffix.casefold(),
                },
            )
        )

    def capture_source(self, source_input: SourceCaptureInput) -> CaptureResult:
        try:
            normalized_text = normalize_text(source_input.raw_text)
            content_hash = content_hash_for_text(normalized_text)
            duplicate = self.store.get_source_by_content_hash(content_hash)
            if duplicate is not None:
                source_id = str(duplicate["id"])
                self._log_event(
                    event_type="source.duplicate_skipped",
                    target_type="source",
                    target_id=source_id,
                    payload={
                        "content_hash": content_hash,
                        "source_type": source_input.source_type,
                        "title": source_input.title,
                    },
                )
                return CaptureResult(
                    status="duplicate",
                    source_id=source_id,
                    content_hash=content_hash,
                    duplicate=True,
                )

            source = self.store.create_source(
                {
                    "source_type": source_input.source_type,
                    "title": source_input.title,
                    "author": source_input.author,
                    "uri": source_input.uri,
                    "raw_path": source_input.raw_path,
                    "content_hash": content_hash,
                    "captured_at": source_input.captured_at,
                    "source_created_at": source_input.source_created_at,
                    "source_modified_at": source_input.source_modified_at,
                    "connector_name": source_input.connector_name,
                    "external_id": source_input.external_id,
                    "domain": source_input.domain,
                    "sensitivity": source_input.sensitivity,
                    "metadata_json": {
                        **source_input.metadata_json,
                        "generated_by": self.actor_type,
                        "agent_identity": self.agent_identity,
                        "agent_id": self.actor_id if self.actor_type == "agent" else None,
                        "trace_id": self.trace_id,
                        "policy_decision": self.policy_decision,
                        "raw_text": normalized_text,
                        "raw_text_sha256": content_hash,
                    },
                },
                actor_type=self.actor_type,
            )
            source_id = str(source["id"])
            self._log_event(
                event_type="source.captured",
                target_type="source",
                target_id=source_id,
                payload={
                    "content_hash": content_hash,
                    "source_type": source_input.source_type,
                    "title": source_input.title,
                    "raw_preserved": True,
                },
            )

            chunk_rows: list[JsonObject] = []
            for chunk_index, chunk in enumerate(chunk_text(normalized_text, max_chars=self.chunk_max_chars)):
                chunk_row = self.store.create_source_chunk(
                    {
                        "source_id": source_id,
                        "chunk_index": chunk_index,
                        "text": chunk,
                        "token_count": len(chunk.split()),
                        "metadata_json": {"content_hash": content_hash},
                    },
                    actor_type=self.actor_type,
                )
                chunk_rows.append(chunk_row)

            self._log_event(
                event_type="source.chunked",
                target_type="source",
                target_id=source_id,
                payload={"content_hash": content_hash, "chunk_count": len(chunk_rows)},
            )

            candidates = extract_candidate_memories(chunk_rows)
            memory_rows: list[JsonObject] = []
            for candidate in candidates:
                # Speaker provenance is only stamped when a role was derived,
                # so provenance-free captures keep byte-identical metadata.
                provenance_metadata: JsonObject = (
                    {
                        "provenance_role": candidate.provenance_role,
                        "assertion_class": candidate.assertion_class,
                    }
                    if candidate.provenance_role is not None
                    else {}
                )
                memory = self.store.create_memory(
                    {
                        "memory_key": _memory_key(content_hash=content_hash, candidate=candidate),
                        "value": {
                            "text": candidate.text,
                            "source_id": source_id,
                            "source_chunk_id": candidate.source_chunk_id,
                        },
                        "status": "candidate",
                        "source_event_ids": [source_id, candidate.source_chunk_id],
                        "memory_type": candidate.memory_type,
                        "confidence": candidate.confidence,
                        "title": _truncate(candidate.text, max_length=120),
                        "canonical_text": candidate.text,
                        "summary": _truncate(candidate.text, max_length=280),
                        "domain": source_input.domain,
                        "sensitivity": source_input.sensitivity,
                        "metadata_json": {
                            "source_id": source_id,
                            "source_chunk_id": candidate.source_chunk_id,
                            "source_chunk_index": candidate.source_chunk_index,
                            "extraction_rule": candidate.extraction_rule,
                            "capture_content_hash": content_hash,
                            **provenance_metadata,
                            "generated_by": self.actor_type,
                            "agent_identity": self.agent_identity,
                            "agent_id": self.actor_id if self.actor_type == "agent" else None,
                            "trace_id": self.trace_id,
                            "policy_decision": self.policy_decision,
                        },
                    },
                    actor_type=self.actor_type,
                )
                memory_rows.append(memory)
                attach_memory_embedding(
                    self.store,
                    memory,
                    actor_type=self.actor_type,
                    actor_id=self.actor_id,
                    trace_id=self.trace_id,
                )
                self.store.create_provenance_link(
                    {
                        "target_type": "memory",
                        "target_id": str(memory["id"]),
                        "source_id": source_id,
                        "source_chunk_id": candidate.source_chunk_id,
                        "quote": candidate.text,
                        "evidence_role": "quoted_from",
                        "confidence": candidate.confidence,
                    },
                    actor_type=self.actor_type,
                )
                self._log_event(
                    event_type="memory.candidate_created",
                    target_type="memory",
                    target_id=str(memory["id"]),
                    payload={
                        "source_id": source_id,
                        "source_chunk_id": candidate.source_chunk_id,
                        "memory_type": candidate.memory_type,
                        "confidence": candidate.confidence,
                    },
                )

            self._link_captured_entities(
                source=source,
                source_id=source_id,
                raw_text=normalized_text,
                sensitivity=source_input.sensitivity,
                memory_rows=memory_rows,
            )

            return CaptureResult(
                status="imported",
                source_id=source_id,
                content_hash=content_hash,
                chunk_count=len(chunk_rows),
                candidate_memory_count=len(candidates),
            )
        except Exception as exc:
            self._log_failure(
                source_type=source_input.source_type,
                title=source_input.title,
                error=exc,
                metadata=source_input.metadata_json,
            )
            raise

    def _link_captured_entities(
        self,
        *,
        source: JsonObject,
        source_id: str,
        raw_text: str,
        sensitivity: str,
        memory_rows: list[JsonObject],
    ) -> None:
        """Best-effort deterministic entity linking after a successful capture.

        - Sensitivity gate: sources at or above 'private' skip extraction
          entirely, because entity rows leak content into ``entities.name``
          (a person/org name IS content).
        - Optional surface: stores without the entity substrate skip
          silently, mirroring how ``attach_memory_embedding`` degrades.
        - Failure isolation: extraction/link errors NEVER fail capture;
          they are logged as ``entity.extraction_failed`` and capture
          continues, mirroring embedding attach failures.
        """
        if str(sensitivity).casefold() in ENTITY_EXTRACTION_SKIP_SENSITIVITIES:
            return
        if not store_supports_entity_linking(self.store):
            return
        # Event time for entity observations and mention edges: the
        # source's own timestamp, falling back to ingestion time.
        observed_at = (
            source.get("source_created_at")
            or source.get("captured_at")
            or datetime.now(UTC).isoformat().replace("+00:00", "Z")
        )
        try:
            linker = EntityLinkingService(
                self.store,
                actor_type=self.actor_type,
                actor_id=self.actor_id,
                trace_id=self.trace_id,
            )
            linker.link_entities_for_source(source_id=source_id, text=raw_text, observed_at=observed_at)
            for memory_row in memory_rows:
                text = str(memory_row.get("canonical_text") or "")
                if text.strip():
                    linker.link_entities_for_memory(
                        memory_id=str(memory_row["id"]),
                        text=text,
                        observed_at=observed_at,
                    )
        except Exception as exc:
            self._log_event(
                event_type="entity.extraction_failed",
                target_type="source",
                target_id=source_id,
                payload={
                    "stage": "capture",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )

    def import_markdown_folder(
        self,
        folder: str | Path,
        *,
        domain: str = "unknown",
        sensitivity: str = "unknown",
    ) -> BatchImportResult:
        folder_path = Path(folder).expanduser().resolve()
        if not folder_path.exists() or not folder_path.is_dir():
            raise VNextCaptureValidationError(f"markdown source folder does not exist: {folder_path}")

        source_ids: list[str] = []
        errors: list[str] = []
        duplicate_count = 0
        failed_count = 0
        run_hashes: set[str] = set()

        for file_path in sorted(folder_path.rglob("*.md")):
            try:
                raw_text = file_path.read_text(encoding="utf-8")
                content_hash = content_hash_for_text(raw_text)
                if content_hash in run_hashes:
                    duplicate_count += 1
                    self._log_event(
                        event_type="source.duplicate_skipped",
                        target_type="source",
                        payload={
                            "content_hash": content_hash,
                            "source_type": "markdown",
                            "raw_path": str(file_path),
                            "duplicate_scope": "batch",
                        },
                    )
                    continue
                run_hashes.add(content_hash)

                result = self.capture_source(
                    SourceCaptureInput(
                        source_type="markdown",
                        title=file_path.stem,
                        raw_text=raw_text,
                        raw_path=str(file_path),
                        connector_name="markdown_folder",
                        external_id=str(file_path.relative_to(folder_path)),
                        domain=domain,
                        sensitivity=sensitivity,
                        metadata_json={
                            "folder": str(folder_path),
                            "relative_path": str(file_path.relative_to(folder_path)),
                        },
                    )
                )
                if result.duplicate:
                    duplicate_count += 1
                    continue
                if result.source_id is not None:
                    source_ids.append(result.source_id)
            except Exception as exc:
                failed_count += 1
                errors.append(f"{file_path}: {exc}")
                self._log_failure(
                    source_type="markdown",
                    title=file_path.name,
                    error=exc,
                    metadata={"raw_path": str(file_path), "folder": str(folder_path)},
                )

        imported_count = len(source_ids)
        status = "ok" if failed_count == 0 else "partial"
        if imported_count == 0 and duplicate_count > 0 and failed_count == 0:
            status = "duplicate"
        if imported_count == 0 and duplicate_count == 0 and failed_count > 0:
            status = "failed"

        self._log_event(
            event_type="source.batch_import_completed",
            target_type="source",
            payload={
                "source_type": "markdown",
                "folder": str(folder_path),
                "imported_count": imported_count,
                "duplicate_count": duplicate_count,
                "failed_count": failed_count,
            },
        )
        return BatchImportResult(
            status=status,
            imported_count=imported_count,
            duplicate_count=duplicate_count,
            failed_count=failed_count,
            source_ids=tuple(source_ids),
            errors=tuple(errors),
        )

    def import_chatgpt_export_file(
        self,
        path: str | Path,
        *,
        domain: str = "personal",
        sensitivity: str = "private",
    ) -> CaptureResult:
        export_path = Path(path).expanduser().resolve()
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        extracted_texts = _extract_text_from_json_value(payload)
        source_text = "\n".join(extracted_texts) if extracted_texts else json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return self.capture_source(
            SourceCaptureInput(
                source_type="chatgpt_export",
                title=export_path.name,
                raw_text=source_text,
                raw_path=str(export_path),
                connector_name="chatgpt_export",
                external_id=str(export_path),
                domain=domain,
                sensitivity=sensitivity,
                metadata_json={"filename": export_path.name, "raw_json": payload},
            )
        )


__all__ = [
    "ASSISTANT_ESTIMATE_CONFIDENCE_FLOOR",
    "ASSISTANT_ESTIMATE_CONFIDENCE_PENALTY",
    "BatchImportResult",
    "CaptureCandidate",
    "CaptureResult",
    "SourceCaptureInput",
    "USER_ASSERTED_CONFIDENCE_BOOST",
    "USER_ASSERTED_CONFIDENCE_CAP",
    "USER_ASSERTED_VALUE_CONFIDENCE",
    "VNextCaptureService",
    "VNextCaptureStore",
    "VNextCaptureValidationError",
    "candidate_promotion_rank",
    "chunk_text",
    "content_hash_for_text",
    "extract_candidate_memories",
    "normalize_text",
    "order_candidates_for_promotion",
]

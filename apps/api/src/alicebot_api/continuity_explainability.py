from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from alicebot_api.contracts import (
    ContinuityExplanationEvidenceSegmentRecord,
    ContinuityExplanationRecord,
    ContinuityExplanationSourceFactRecord,
    ContinuityExplanationSupersessionNoteRecord,
    ContinuityExplanationTimestampsRecord,
    ContinuityExplanationTrustRecord,
    ContinuityRecallProvenancePosture,
    MemoryConfirmationStatus,
    MemoryTrustClass,
    isoformat_or_none,
)
from alicebot_api.store import (
    ContinuityCaptureEventRow,
    ContinuityCorrectionEventRow,
    ContinuityObjectEvidenceRow,
    JsonObject,
)


_MAX_SOURCE_FACTS = 8
_MAX_EVIDENCE_SEGMENTS = 5
_MAX_SUPERSESSION_NOTES = 5
_MAX_SNIPPET_LENGTH = 220
_SCOPE_CONTEXT_KEYS = {
    "thread_id",
    "thread",
    "task_id",
    "task",
    "project",
    "project_id",
    "project_name",
    "person",
    "person_id",
    "person_name",
    "owner",
    "assignee",
}


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip()
    if normalized == "":
        return None
    return normalized


def _truncate(value: str) -> str:
    normalized = _normalize_text(value)
    if normalized is None:
        return ""
    if len(normalized) <= _MAX_SNIPPET_LENGTH:
        return normalized
    return normalized[: _MAX_SNIPPET_LENGTH - 1].rstrip() + "…"


def _iter_leaf_values(payload: object, *, prefix: str = "") -> list[tuple[str, str]]:
    leaves: list[tuple[str, str]] = []
    if isinstance(payload, dict):
        for key, child in payload.items():
            next_prefix = key if prefix == "" else f"{prefix}.{key}"
            leaves.extend(_iter_leaf_values(child, prefix=next_prefix))
        return leaves
    if isinstance(payload, list):
        rendered_values = [
            _normalize_text(str(item))
            for item in payload
            if _normalize_text(str(item)) is not None
        ]
        if rendered_values:
            leaves.append((prefix or "value", ", ".join(rendered_values)))
        return leaves
    if isinstance(payload, (str, int, float, bool)):
        normalized = _normalize_text(str(payload))
        if normalized is not None:
            leaves.append((prefix or "value", normalized))
    return leaves


def _extract_confirmation_status(
    *,
    body: JsonObject,
    provenance: JsonObject,
    last_confirmed_at: datetime | None,
) -> MemoryConfirmationStatus:
    for payload in (provenance, body):
        for key, value in _iter_leaf_values(payload):
            lowered_key = key.casefold()
            lowered_value = value.casefold()
            if lowered_key.endswith("confirmation_status") or lowered_key.endswith(
                "memory_confirmation_status"
            ):
                if lowered_value in {"unconfirmed", "confirmed", "contested"}:
                    return cast(MemoryConfirmationStatus, lowered_value)
    if last_confirmed_at is not None:
        return "confirmed"
    return "unconfirmed"


def _collect_source_event_ids(payload: object) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                lowered_key = key.casefold()
                if lowered_key.endswith("source_event_id") and isinstance(child, (str, UUID)):
                    rendered = str(child)
                    if rendered not in seen:
                        seen.add(rendered)
                        ordered.append(rendered)
                elif lowered_key.endswith("source_event_ids") and isinstance(child, list):
                    for item in child:
                        if isinstance(item, (str, UUID)):
                            rendered = str(item)
                            if rendered not in seen:
                                seen.add(rendered)
                                ordered.append(rendered)
                visit(child)
            return
        if isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return ordered


def _has_scope_context(payload: object) -> bool:
    if isinstance(payload, dict):
        for key, child in payload.items():
            if key.casefold() in _SCOPE_CONTEXT_KEYS:
                normalized = _normalize_text(str(child)) if not isinstance(child, (dict, list)) else None
                if normalized is not None:
                    return True
                if isinstance(child, list) and any(_normalize_text(str(item)) for item in child):
                    return True
            if _has_scope_context(child):
                return True
    elif isinstance(payload, list):
        return any(_has_scope_context(child) for child in payload)
    return False


def derive_provenance_posture(*, body: JsonObject, provenance: JsonObject) -> ContinuityRecallProvenancePosture:
    has_source_events = bool(_collect_source_event_ids(provenance) or _collect_source_event_ids(body))
    has_scope_context = _has_scope_context(provenance) or _has_scope_context(body)
    if has_source_events and has_scope_context:
        return "strong"
    if has_source_events or has_scope_context:
        return "partial"
    if provenance:
        return "weak"
    return "missing"


def _safe_call[TReturn](
    store: object,
    method_name: str,
    fallback: TReturn,
    *args: object,
    **kwargs: object,
) -> TReturn:
    method = getattr(store, method_name, None)
    if not callable(method):
        return fallback
    return cast(TReturn, method(*args, **kwargs))


def _load_capture_event(
    store: object,
    *,
    capture_event_id: UUID,
) -> ContinuityCaptureEventRow | None:
    return _safe_call(
        store,
        "get_continuity_capture_event_optional",
        None,
        capture_event_id,
    )


def _load_evidence_rows(
    store: object,
    *,
    continuity_object_id: UUID,
) -> list[ContinuityObjectEvidenceRow]:
    return _safe_call(
        store,
        "list_continuity_object_evidence",
        [],
        continuity_object_id,
    )


def _load_correction_events(
    store: object,
    *,
    continuity_object_id: UUID,
) -> list[ContinuityCorrectionEventRow]:
    return _safe_call(
        store,
        "list_continuity_correction_events",
        [],
        continuity_object_id=continuity_object_id,
        limit=_MAX_SUPERSESSION_NOTES,
    )


def _source_facts(
    *,
    title: str,
    body: JsonObject,
    provenance: JsonObject,
    capture_event: ContinuityCaptureEventRow | None,
) -> list[ContinuityExplanationSourceFactRecord]:
    facts: list[ContinuityExplanationSourceFactRecord] = []
    seen: set[tuple[str, str, str]] = set()

    def add_fact(kind: str, label: str, value: str) -> None:
        normalized = _normalize_text(value)
        if normalized is None:
            return
        key = (kind, label, normalized)
        if key in seen:
            return
        seen.add(key)
        facts.append(
            {
                "kind": kind,
                "label": label,
                "value": normalized,
            }
        )

    if capture_event is not None:
        add_fact("capture_event", "raw_content", capture_event["raw_content"])
    add_fact("title", "title", title)
    for key, value in _iter_leaf_values(body):
        add_fact("body", key, value)
        if len(facts) >= _MAX_SOURCE_FACTS:
            return facts[:_MAX_SOURCE_FACTS]
    for key, value in _iter_leaf_values(provenance):
        add_fact("provenance", key, value)
        if len(facts) >= _MAX_SOURCE_FACTS:
            return facts[:_MAX_SOURCE_FACTS]
    return facts[:_MAX_SOURCE_FACTS]


def _evidence_segments(
    *,
    capture_event_id: UUID,
    capture_event: ContinuityCaptureEventRow | None,
    evidence_rows: list[ContinuityObjectEvidenceRow],
    title: str,
) -> list[ContinuityExplanationEvidenceSegmentRecord]:
    segments: list[ContinuityExplanationEvidenceSegmentRecord] = []

    for row in evidence_rows[:_MAX_EVIDENCE_SEGMENTS]:
        snippet_source = row["segment_raw_content"] or row["artifact_copy_content_text"] or title
        segments.append(
            {
                "relationship": row["relationship"],
                "source_kind": row["source_kind"],
                "source_id": str(row["artifact_segment_id"] or row["artifact_id"]),
                "display_name": row["display_name"],
                "relative_path": row["relative_path"],
                "segment_kind": row["segment_kind"],
                "locator": row["segment_locator"],
                "snippet": _truncate(snippet_source),
                "created_at": (
                    row["segment_created_at"].isoformat()
                    if row["segment_created_at"] is not None
                    else row["created_at"].isoformat()
                ),
            }
        )

    if segments:
        return segments

    synthetic_snippet = title
    synthetic_created_at: str | None = None
    if capture_event is not None:
        synthetic_snippet = capture_event["raw_content"]
        synthetic_created_at = capture_event["created_at"].isoformat()

    return [
        {
            "relationship": "captured_from",
            "source_kind": "continuity_capture_event",
            "source_id": str(capture_event_id),
            "display_name": "capture event",
            "relative_path": None,
            "segment_kind": "capture_event",
            "locator": None,
            "snippet": _truncate(synthetic_snippet),
            "created_at": synthetic_created_at,
        }
    ]


def _infer_trust_class(
    *,
    confirmation_status: MemoryConfirmationStatus,
    provenance_posture: ContinuityRecallProvenancePosture,
    evidence_segment_count: int,
    correction_count: int,
    source_event_count: int,
) -> tuple[MemoryTrustClass, str]:
    if correction_count > 0 or confirmation_status == "confirmed":
        return "human_curated", "Inferred from confirmation or correction history."
    if evidence_segment_count > 1 or source_event_count > 1:
        return "llm_corroborated", "Inferred from multiple supporting evidence or source events."
    if evidence_segment_count > 0 or source_event_count > 0 or provenance_posture in {"strong", "partial"}:
        return "llm_single_source", "Inferred from a single capture or provenance chain."
    return "deterministic", "Inferred from structured continuity fields without external evidence."


def _trust_record(
    *,
    confidence: float,
    confirmation_status: MemoryConfirmationStatus,
    provenance_posture: ContinuityRecallProvenancePosture,
    evidence_segment_count: int,
    correction_count: int,
    source_event_count: int,
) -> ContinuityExplanationTrustRecord:
    trust_class, trust_reason = _infer_trust_class(
        confirmation_status=confirmation_status,
        provenance_posture=provenance_posture,
        evidence_segment_count=evidence_segment_count,
        correction_count=correction_count,
        source_event_count=source_event_count,
    )
    return {
        "trust_class": trust_class,
        "trust_reason": trust_reason,
        "confirmation_status": confirmation_status,
        "confidence": confidence,
        "provenance_posture": provenance_posture,
        "evidence_segment_count": evidence_segment_count,
        "correction_count": correction_count,
    }


def _proposal_rationale(
    *,
    status: str,
    source_fact_count: int,
    evidence_segment_count: int,
    trust_class: MemoryTrustClass,
    confirmation_status: MemoryConfirmationStatus,
    provenance_posture: ContinuityRecallProvenancePosture,
    correction_count: int,
) -> str:
    lifecycle_clause = f"Candidate entered review with lifecycle status '{status}'."
    source_clause = (
        f"It is backed by {source_fact_count} source fact(s) and {evidence_segment_count} evidence segment(s)."
    )
    trust_clause = (
        "Trust posture resolves to "
        f"'{trust_class}' with confirmation status '{confirmation_status}' and provenance posture "
        f"'{provenance_posture}'."
    )
    correction_clause = f"Correction history includes {correction_count} event(s)."
    return " ".join(
        [
            lifecycle_clause,
            source_clause,
            trust_clause,
            correction_clause,
        ]
    )


def _supersession_notes(
    *,
    status: str,
    supersedes_object_id: UUID | None,
    superseded_by_object_id: UUID | None,
    correction_events: list[ContinuityCorrectionEventRow],
) -> list[ContinuityExplanationSupersessionNoteRecord]:
    notes: list[ContinuityExplanationSupersessionNoteRecord] = []

    def add_note(
        *,
        kind: str,
        note: str,
        action: str | None = None,
        related_object_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> None:
        notes.append(
            {
                "kind": kind,
                "note": note,
                "action": action,
                "related_object_id": None if related_object_id is None else str(related_object_id),
                "created_at": None if created_at is None else created_at.isoformat(),
            }
        )

    if supersedes_object_id is not None:
        add_note(
            kind="supersedes",
            note="This object supersedes an earlier continuity object.",
            related_object_id=supersedes_object_id,
        )
    if superseded_by_object_id is not None:
        add_note(
            kind="superseded_by",
            note="This object has been superseded by a newer continuity object.",
            related_object_id=superseded_by_object_id,
        )
    if status != "active":
        add_note(
            kind="status",
            note=f"Current lifecycle status is {status}.",
        )

    for event in correction_events[:_MAX_SUPERSESSION_NOTES]:
        action_value = event.get("action")
        action = action_value if isinstance(action_value, str) and action_value.strip() else "unknown"
        created_at_value = event.get("created_at")
        reason_suffix = ""
        reason_value = event.get("reason")
        if isinstance(reason_value, str) and reason_value.strip():
            reason_suffix = f" Reason: {reason_value}."
        add_note(
            kind="correction_event",
            note=f"Correction event {action} updated the explanation chain.{reason_suffix}",
            action=action,
            created_at=created_at_value if isinstance(created_at_value, datetime) else None,
        )

    return notes[:_MAX_SUPERSESSION_NOTES]


def _timestamps_record(
    *,
    created_at: datetime,
    updated_at: datetime,
    capture_event: ContinuityCaptureEventRow | None,
    last_confirmed_at: datetime | None,
) -> ContinuityExplanationTimestampsRecord:
    return {
        "capture_created_at": (
            None if capture_event is None else capture_event["created_at"].isoformat()
        ),
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "last_confirmed_at": isoformat_or_none(last_confirmed_at),
    }


def build_continuity_item_explanation(
    store: object,
    *,
    continuity_object_id: UUID,
    capture_event_id: UUID,
    title: str,
    body: JsonObject,
    provenance: JsonObject,
    status: str,
    confidence: float,
    last_confirmed_at: datetime | None,
    supersedes_object_id: UUID | None,
    superseded_by_object_id: UUID | None,
    created_at: datetime,
    updated_at: datetime,
    confirmation_status: MemoryConfirmationStatus | None = None,
    provenance_posture: ContinuityRecallProvenancePosture | None = None,
) -> ContinuityExplanationRecord:
    capture_event = _load_capture_event(store, capture_event_id=capture_event_id)
    evidence_rows = _load_evidence_rows(store, continuity_object_id=continuity_object_id)
    correction_events = _load_correction_events(store, continuity_object_id=continuity_object_id)
    resolved_confirmation_status = (
        confirmation_status
        if confirmation_status is not None
        else _extract_confirmation_status(
            body=body,
            provenance=provenance,
            last_confirmed_at=last_confirmed_at,
        )
    )
    resolved_provenance_posture = (
        provenance_posture
        if provenance_posture is not None
        else derive_provenance_posture(body=body, provenance=provenance)
    )
    source_event_count = len(_collect_source_event_ids(provenance)) + len(_collect_source_event_ids(body))
    evidence_segments = _evidence_segments(
        capture_event_id=capture_event_id,
        capture_event=capture_event,
        evidence_rows=evidence_rows,
        title=title,
    )
    source_facts = _source_facts(
        title=title,
        body=body,
        provenance=provenance,
        capture_event=capture_event,
    )
    trust = _trust_record(
        confidence=confidence,
        confirmation_status=resolved_confirmation_status,
        provenance_posture=resolved_provenance_posture,
        evidence_segment_count=len(evidence_segments),
        correction_count=len(correction_events),
        source_event_count=source_event_count,
    )
    supersession_notes = _supersession_notes(
        status=status,
        supersedes_object_id=supersedes_object_id,
        superseded_by_object_id=superseded_by_object_id,
        correction_events=correction_events,
    )
    return {
        "source_facts": source_facts,
        "trust": trust,
        "evidence_segments": evidence_segments,
        "supersession_notes": supersession_notes,
        "timestamps": _timestamps_record(
            created_at=created_at,
            updated_at=updated_at,
            capture_event=capture_event,
            last_confirmed_at=last_confirmed_at,
        ),
        "proposal_rationale": _proposal_rationale(
            status=status,
            source_fact_count=len(source_facts),
            evidence_segment_count=len(evidence_segments),
            trust_class=trust["trust_class"],
            confirmation_status=resolved_confirmation_status,
            provenance_posture=resolved_provenance_posture,
            correction_count=len(correction_events),
        ),
    }


__all__ = [
    "build_continuity_item_explanation",
    "derive_provenance_posture",
]

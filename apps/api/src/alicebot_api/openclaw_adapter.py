from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from alicebot_api.openclaw_models import (
    OpenClawAdapterValidationError,
    OpenClawNormalizedBatch,
    OpenClawNormalizedItem,
    OpenClawWorkspaceContext,
    as_json_object,
    canonical_json_string,
    ensure_json_object,
    merge_json_objects,
    normalize_optional_text,
    parse_optional_confidence,
    parse_optional_status,
    pick_first_text,
    to_string_list,
)
from alicebot_api.store import JsonObject


_OPENCLAW_TYPE_TO_OBJECT_TYPE: dict[str, str] = {
    "decision": "Decision",
    "decisions": "Decision",
    "task": "NextAction",
    "next": "NextAction",
    "next_action": "NextAction",
    "nextaction": "NextAction",
    "action": "NextAction",
    "commitment": "Commitment",
    "waiting": "WaitingFor",
    "waiting_for": "WaitingFor",
    "waitingfor": "WaitingFor",
    "blocker": "Blocker",
    "fact": "MemoryFact",
    "memory_fact": "MemoryFact",
    "memory": "MemoryFact",
    "note": "Note",
}

_OBJECT_TYPE_TO_BODY_KEY: dict[str, str] = {
    "Note": "body",
    "MemoryFact": "fact_text",
    "Decision": "decision_text",
    "Commitment": "commitment_text",
    "WaitingFor": "waiting_for_text",
    "Blocker": "blocking_reason",
    "NextAction": "action_text",
}

_OBJECT_TYPE_TO_PREFIX: dict[str, str] = {
    "Decision": "Decision",
    "Commitment": "Commitment",
    "WaitingFor": "Waiting For",
    "Blocker": "Blocker",
    "NextAction": "Next Action",
    "MemoryFact": "Memory Fact",
    "Note": "Note",
}

_DEFAULT_CONFIDENCE = 0.82
_SUPPORTED_WORKSPACE_FILENAMES = (
    "workspace.json",
    "openclaw_workspace.json",
)
_SUPPORTED_MEMORY_FILENAMES = (
    "durable_memory.json",
    "memories.json",
    "openclaw_memories.json",
)


def _truncate(value: str, *, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def _normalize_object_type(value: object) -> str:
    normalized = normalize_optional_text(value)
    if normalized is None:
        return "Note"

    if normalized in _OBJECT_TYPE_TO_BODY_KEY:
        return normalized

    lowered = normalized.casefold().replace("-", "_").replace(" ", "_")
    return _OPENCLAW_TYPE_TO_OBJECT_TYPE.get(lowered, "Note")


def _build_body(*, object_type: str, text: str, raw_entry: JsonObject) -> JsonObject:
    body_key = _OBJECT_TYPE_TO_BODY_KEY[object_type]
    return {
        body_key: text,
        "raw_import_text": text,
        "openclaw_raw_entry": raw_entry,
    }


def _build_title(*, object_type: str, text: str, explicit_title: str | None) -> str:
    if explicit_title is not None:
        return _truncate(explicit_title, max_length=280)
    prefix = _OBJECT_TYPE_TO_PREFIX[object_type]
    return _truncate(f"{prefix}: {text}", max_length=280)


def _build_raw_content(*, object_type: str, text: str) -> str:
    prefix = _OBJECT_TYPE_TO_PREFIX[object_type]
    return f"{prefix}: {text}"


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OpenClawAdapterValidationError(
            f"invalid JSON at {path}: {exc.msg}"
        ) from exc


def _extract_workspace_payloads(payload: object) -> tuple[JsonObject | None, list[JsonObject]]:
    if isinstance(payload, list):
        entries = [ensure_json_object(item, field_name="entry") for item in payload]
        return None, entries

    if not isinstance(payload, dict):
        raise OpenClawAdapterValidationError("OpenClaw source root must be a JSON object or array")

    workspace_payload = payload.get("workspace")
    if workspace_payload is not None and not isinstance(workspace_payload, dict):
        raise OpenClawAdapterValidationError("workspace must be a JSON object when provided")
    workspace_json = as_json_object(workspace_payload) if workspace_payload is not None else None

    entries: list[JsonObject] = []
    found_memory_key = False
    for key in ("durable_memory", "memories", "items", "records"):
        raw_entries = payload.get(key)
        if raw_entries is None:
            continue
        found_memory_key = True
        if not isinstance(raw_entries, list):
            raise OpenClawAdapterValidationError(f"{key} must be a JSON array")
        entries.extend(ensure_json_object(item, field_name=f"{key}[]") for item in raw_entries)

    if found_memory_key:
        return workspace_json, entries

    if workspace_payload is not None:
        return workspace_json, []

    # Single-record convenience format.
    if payload.get("content") is not None or payload.get("text") is not None:
        return None, [ensure_json_object(payload, field_name="payload")]

    raise OpenClawAdapterValidationError(
        "OpenClaw payload must include one of: durable_memory, memories, items, or records"
    )


def _extract_scope_provenance(entry: JsonObject, *, raw_provenance: JsonObject) -> JsonObject:
    entry_context = as_json_object(entry.get("context"))

    thread_id = pick_first_text(
        entry.get("thread_id"),
        raw_provenance.get("thread_id"),
        entry_context.get("thread_id"),
    )
    task_id = pick_first_text(
        entry.get("task_id"),
        raw_provenance.get("task_id"),
        entry_context.get("task_id"),
    )
    project = pick_first_text(
        entry.get("project"),
        entry.get("project_name"),
        raw_provenance.get("project"),
        entry_context.get("project"),
        entry_context.get("project_name"),
    )
    person = pick_first_text(
        entry.get("person"),
        entry.get("owner"),
        raw_provenance.get("person"),
        raw_provenance.get("owner"),
        entry_context.get("person"),
        entry_context.get("owner"),
    )
    topic = pick_first_text(
        entry.get("topic"),
        entry.get("topic_name"),
        raw_provenance.get("topic"),
        raw_provenance.get("topic_name"),
        entry_context.get("topic"),
        entry_context.get("topic_name"),
    )
    confirmation_status = pick_first_text(
        entry.get("confirmation_status"),
        raw_provenance.get("confirmation_status"),
        entry_context.get("confirmation_status"),
    )

    source_event_ids = to_string_list(entry.get("source_event_ids"))
    if not source_event_ids:
        source_event_ids = to_string_list(raw_provenance.get("source_event_ids"))
    if not source_event_ids:
        source_event_ids = to_string_list(entry_context.get("source_event_ids"))

    payload: JsonObject = {}
    if thread_id is not None:
        payload["thread_id"] = thread_id
    if task_id is not None:
        payload["task_id"] = task_id
    if project is not None:
        payload["project"] = project
    if person is not None:
        payload["person"] = person
    if topic is not None:
        payload["topic"] = topic
    if confirmation_status is not None:
        payload["confirmation_status"] = confirmation_status.casefold()
    if source_event_ids:
        payload["source_event_ids"] = source_event_ids

    tags = to_string_list(entry.get("tags"))
    if tags:
        payload["openclaw_tags"] = tags

    return payload


def _item_text(entry: JsonObject) -> str:
    text = pick_first_text(
        entry.get("text"),
        entry.get("content"),
        entry.get("summary"),
        entry.get("message"),
    )
    if text is None:
        raise OpenClawAdapterValidationError("OpenClaw entry must include text/content/summary/message")
    return text


def _normalize_entry(
    *,
    entry: JsonObject,
    source_file: str,
    entry_index: int,
    workspace_id: str,
) -> OpenClawNormalizedItem:
    source_identifier = pick_first_text(
        entry.get("id"),
        entry.get("memory_id"),
        entry.get("entry_id"),
    )
    source_item_id = source_identifier if source_identifier is not None else f"{source_file}:{entry_index + 1}"

    object_type = _normalize_object_type(
        pick_first_text(
            entry.get("object_type"),
            entry.get("type"),
            entry.get("kind"),
            entry.get("category"),
        )
    )
    status = parse_optional_status(entry.get("status")) or "active"

    text = _item_text(entry)
    title = _build_title(
        object_type=object_type,
        text=text,
        explicit_title=pick_first_text(entry.get("title")),
    )
    raw_entry = as_json_object(entry)

    raw_provenance = as_json_object(entry.get("provenance"))
    source_provenance = merge_json_objects(
        _extract_scope_provenance(entry, raw_provenance=raw_provenance),
        {
            "openclaw_record_type": pick_first_text(
                entry.get("type"),
                entry.get("kind"),
                entry.get("category"),
            )
            or "unknown",
        },
    )
    if source_identifier is not None:
        source_provenance["openclaw_source_identifier"] = source_identifier

    confidence = parse_optional_confidence(entry.get("confidence"))
    if confidence is None:
        confidence = parse_optional_confidence(raw_provenance.get("confidence"))
    if confidence is None:
        confidence = _DEFAULT_CONFIDENCE

    dedupe_payload: JsonObject = {
        "workspace_id": workspace_id,
        "source_identifier": source_identifier,
        "object_type": object_type,
        "status": status,
        "title": title,
        "body": _build_body(object_type=object_type, text=text, raw_entry=raw_entry),
        "source_provenance": source_provenance,
    }
    dedupe_key = sha256(canonical_json_string(dedupe_payload).encode("utf-8")).hexdigest()

    return OpenClawNormalizedItem(
        source_item_id=source_item_id,
        source_file=source_file,
        source_locator={
            "source_identifier": source_identifier,
            "entry_index": entry_index + 1,
        },
        source_segment_text=canonical_json_string(raw_entry),
        source_segment_kind="openclaw_entry",
        object_type=object_type,
        status=status,
        raw_content=_build_raw_content(object_type=object_type, text=text),
        title=title,
        body=_build_body(object_type=object_type, text=text, raw_entry=raw_entry),
        confidence=confidence,
        source_provenance=source_provenance,
        dedupe_key=dedupe_key,
    )


def _extract_context(
    *,
    source_path: Path,
    workspace_payload: JsonObject | None,
    fallback_fixture_id: str | None,
) -> OpenClawWorkspaceContext:
    payload = workspace_payload or {}
    workspace_id = pick_first_text(
        payload.get("id"),
        payload.get("workspace_id"),
        fallback_fixture_id,
        source_path.stem,
    )
    if workspace_id is None:
        raise OpenClawAdapterValidationError("workspace id could not be resolved")

    return OpenClawWorkspaceContext(
        fixture_id=fallback_fixture_id,
        workspace_id=workspace_id,
        workspace_name=pick_first_text(payload.get("name"), payload.get("title")),
        source_path=str(source_path),
    )


def list_openclaw_source_files(source: str | Path) -> tuple[Path, list[Path]]:
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise OpenClawAdapterValidationError(f"OpenClaw source path does not exist: {source_path}")

    if source_path.is_file():
        return source_path, [source_path]

    files: list[Path] = []
    for filename in (*_SUPPORTED_WORKSPACE_FILENAMES, *_SUPPORTED_MEMORY_FILENAMES):
        candidate = source_path / filename
        if candidate.exists():
            files.append(candidate)

    if files:
        return source_path, files

    json_files = sorted(path for path in source_path.iterdir() if path.suffix == ".json")
    if not json_files:
        raise OpenClawAdapterValidationError("no OpenClaw memory entries were found at the source path")
    return source_path, json_files


def load_openclaw_payload(source: str | Path) -> OpenClawNormalizedBatch:
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise OpenClawAdapterValidationError(f"OpenClaw source path does not exist: {source_path}")

    entries_by_file: list[tuple[str, list[JsonObject]]] = []
    workspace_payload: JsonObject | None = None
    fixture_id: str | None = None

    if source_path.is_file():
        payload = _read_json(source_path)
        parsed_workspace, entries = _extract_workspace_payloads(payload)
        if isinstance(payload, dict):
            fixture_id = normalize_optional_text(payload.get("fixture_id"))
        workspace_payload = parsed_workspace
        entries_by_file.append((source_path.name, entries))
    else:
        for filename in _SUPPORTED_WORKSPACE_FILENAMES:
            candidate = source_path / filename
            if not candidate.exists():
                continue
            payload = _read_json(candidate)
            parsed_workspace, _ = _extract_workspace_payloads(payload)
            workspace_payload = parsed_workspace or workspace_payload
            if isinstance(payload, dict):
                fixture_id = fixture_id or normalize_optional_text(payload.get("fixture_id"))
            break

        for filename in _SUPPORTED_MEMORY_FILENAMES:
            candidate = source_path / filename
            if not candidate.exists():
                continue
            payload = _read_json(candidate)
            parsed_workspace, entries = _extract_workspace_payloads(payload)
            if parsed_workspace is not None:
                workspace_payload = parsed_workspace
            if isinstance(payload, dict):
                fixture_id = fixture_id or normalize_optional_text(payload.get("fixture_id"))
            entries_by_file.append((filename, entries))

        if not entries_by_file:
            json_files = sorted(path for path in source_path.iterdir() if path.suffix == ".json")
            for path in json_files:
                payload = _read_json(path)
                parsed_workspace, entries = _extract_workspace_payloads(payload)
                if parsed_workspace is not None:
                    workspace_payload = parsed_workspace
                if isinstance(payload, dict):
                    fixture_id = fixture_id or normalize_optional_text(payload.get("fixture_id"))
                if entries:
                    entries_by_file.append((path.name, entries))

    if not entries_by_file:
        raise OpenClawAdapterValidationError("no OpenClaw memory entries were found at the source path")

    context = _extract_context(
        source_path=source_path,
        workspace_payload=workspace_payload,
        fallback_fixture_id=fixture_id,
    )

    normalized_items: list[OpenClawNormalizedItem] = []
    for source_file, entries in entries_by_file:
        for index, entry in enumerate(entries):
            normalized_items.append(
                _normalize_entry(
                    entry=entry,
                    source_file=source_file,
                    entry_index=index,
                    workspace_id=context.workspace_id,
                )
            )

    if not normalized_items:
        raise OpenClawAdapterValidationError("OpenClaw source did not contain any importable entries")

    return OpenClawNormalizedBatch(
        context=context,
        items=normalized_items,
    )


__all__ = [
    "OpenClawAdapterValidationError",
    "list_openclaw_source_files",
    "load_openclaw_payload",
]

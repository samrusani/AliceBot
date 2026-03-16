from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from uuid import UUID

import psycopg

from alicebot_api.contracts import (
    TASK_ARTIFACT_LIST_ORDER,
    TASK_ARTIFACT_CHUNK_LIST_ORDER,
    TASK_ARTIFACT_CHUNK_RETRIEVAL_ORDER,
    ArtifactScopedArtifactChunkRetrievalInput,
    TaskArtifactChunkRetrievalItem,
    TaskArtifactChunkRetrievalMatch,
    TaskArtifactChunkRetrievalResponse,
    TaskArtifactChunkRetrievalScope,
    TaskArtifactChunkRetrievalScopeKind,
    TaskArtifactChunkRetrievalSummary,
    TaskArtifactCreateResponse,
    TaskArtifactDetailResponse,
    TaskArtifactChunkListResponse,
    TaskArtifactChunkListSummary,
    TaskArtifactChunkRecord,
    TaskArtifactListResponse,
    TaskArtifactRecord,
    TaskArtifactIngestInput,
    TaskArtifactIngestionResponse,
    TaskArtifactRegisterInput,
    TaskArtifactStatus,
    TaskArtifactIngestionStatus,
    TaskScopedArtifactChunkRetrievalInput,
)
from alicebot_api.store import ContinuityStore, TaskArtifactChunkRow, TaskArtifactRow
from alicebot_api.tasks import TaskNotFoundError
from alicebot_api.workspaces import TaskWorkspaceNotFoundError

SUPPORTED_TEXT_ARTIFACT_MEDIA_TYPES = ("text/plain", "text/markdown")
SUPPORTED_PDF_ARTIFACT_MEDIA_TYPE = "application/pdf"
SUPPORTED_ARTIFACT_MEDIA_TYPES = (
    *SUPPORTED_TEXT_ARTIFACT_MEDIA_TYPES,
    SUPPORTED_PDF_ARTIFACT_MEDIA_TYPE,
)
SUPPORTED_ARTIFACT_EXTENSIONS = {
    ".txt": "text/plain",
    ".text": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".pdf": SUPPORTED_PDF_ARTIFACT_MEDIA_TYPE,
}
TASK_ARTIFACT_CHUNK_MAX_CHARS = 1000
TASK_ARTIFACT_CHUNKING_RULE = "normalized_utf8_text_fixed_window_1000_chars_v1"
TASK_ARTIFACT_CHUNK_RETRIEVAL_MATCHING_RULE = (
    "casefolded_unicode_word_overlap_unique_query_terms_v1"
)
_LEXICAL_TERM_PATTERN = re.compile(r"\w+")
_PDF_INDIRECT_OBJECT_PATTERN = re.compile(rb"(?s)(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj\b")
_PDF_REFERENCE_PATTERN = re.compile(rb"(\d+)\s+(\d+)\s+R")
_PDF_NUMERIC_TOKEN_PATTERN = re.compile(rb"[+-]?(?:\d+(?:\.\d+)?|\.\d+)")
_PDF_CONTENT_OPERATORS = {
    b'"',
    b"'",
    b"*",
    b"B",
    b"BT",
    b"BX",
    b"B*",
    b"BI",
    b"BMC",
    b"BDC",
    b"b",
    b"b*",
    b"cm",
    b"CS",
    b"cs",
    b"Do",
    b"DP",
    b"EI",
    b"EMC",
    b"ET",
    b"EX",
    b"f",
    b"F",
    b"f*",
    b"G",
    b"g",
    b"gs",
    b"h",
    b"i",
    b"ID",
    b"j",
    b"J",
    b"K",
    b"k",
    b"l",
    b"M",
    b"m",
    b"MP",
    b"n",
    b"q",
    b"Q",
    b"re",
    b"RG",
    b"rg",
    b"ri",
    b"s",
    b"S",
    b"SC",
    b"sc",
    b"SCN",
    b"scn",
    b"sh",
    b"T*",
    b"Tc",
    b"Td",
    b"TD",
    b"Tf",
    b"TJ",
    b"Tj",
    b"TL",
    b"Tm",
    b"Tr",
    b"Ts",
    b"Tw",
    b"Tz",
    b"v",
    b"w",
    b"W",
    b"W*",
    b"y",
}


@dataclass(frozen=True, slots=True)
class _PdfObject:
    object_id: int
    generation: int
    dictionary: bytes
    stream: bytes | None
    raw_content: bytes


class TaskArtifactNotFoundError(LookupError):
    """Raised when a task artifact is not visible inside the current user scope."""


class TaskArtifactAlreadyExistsError(RuntimeError):
    """Raised when the same workspace-relative artifact path is registered twice."""


class TaskArtifactValidationError(ValueError):
    """Raised when a local artifact path cannot satisfy registration constraints."""


class TaskArtifactChunkRetrievalValidationError(ValueError):
    """Raised when an artifact chunk retrieval request cannot be evaluated safely."""


def resolve_artifact_path(local_path: str) -> Path:
    return Path(local_path).expanduser().resolve()


def ensure_artifact_path_is_rooted(*, workspace_path: Path, artifact_path: Path) -> None:
    resolved_workspace_path = workspace_path.resolve()
    resolved_artifact_path = artifact_path.resolve()
    try:
        resolved_artifact_path.relative_to(resolved_workspace_path)
    except ValueError as exc:
        raise TaskArtifactValidationError(
            f"artifact path {resolved_artifact_path} escapes workspace root {resolved_workspace_path}"
        ) from exc


def build_workspace_relative_artifact_path(*, workspace_path: Path, artifact_path: Path) -> str:
    relative_path = artifact_path.relative_to(workspace_path).as_posix()
    if relative_path in ("", "."):
        raise TaskArtifactValidationError(
            f"artifact path {artifact_path} must point to a file beneath workspace root {workspace_path}"
        )
    return relative_path


def _require_existing_file(artifact_path: Path) -> None:
    if not artifact_path.exists():
        raise TaskArtifactValidationError(f"artifact path {artifact_path} was not found")
    if not artifact_path.is_file():
        raise TaskArtifactValidationError(f"artifact path {artifact_path} is not a regular file")


def _duplicate_registration_message(*, task_workspace_id: UUID, relative_path: str) -> str:
    return (
        f"artifact {relative_path} is already registered for task workspace {task_workspace_id}"
    )


def serialize_task_artifact_row(row: TaskArtifactRow) -> TaskArtifactRecord:
    return {
        "id": str(row["id"]),
        "task_id": str(row["task_id"]),
        "task_workspace_id": str(row["task_workspace_id"]),
        "status": cast(TaskArtifactStatus, row["status"]),
        "ingestion_status": cast(TaskArtifactIngestionStatus, row["ingestion_status"]),
        "relative_path": row["relative_path"],
        "media_type_hint": row["media_type_hint"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def serialize_task_artifact_chunk_row(row: TaskArtifactChunkRow) -> TaskArtifactChunkRecord:
    return {
        "id": str(row["id"]),
        "task_artifact_id": str(row["task_artifact_id"]),
        "sequence_no": row["sequence_no"],
        "char_start": row["char_start"],
        "char_end_exclusive": row["char_end_exclusive"],
        "text": row["text"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def infer_task_artifact_media_type(row: TaskArtifactRow) -> str | None:
    if row["media_type_hint"] is not None:
        return row["media_type_hint"]

    artifact_path = Path(row["relative_path"])
    return SUPPORTED_ARTIFACT_EXTENSIONS.get(artifact_path.suffix.lower())


def resolve_supported_task_artifact_media_type(row: TaskArtifactRow) -> str:
    media_type = infer_task_artifact_media_type(row)
    if media_type in SUPPORTED_ARTIFACT_MEDIA_TYPES:
        return cast(str, media_type)

    supported_types = ", ".join(SUPPORTED_ARTIFACT_MEDIA_TYPES)
    raise TaskArtifactValidationError(
        f"artifact {row['relative_path']} has unsupported media type "
        f"{media_type or 'unknown'}; supported types: {supported_types}"
    )


def normalize_artifact_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def chunk_normalized_artifact_text(
    text: str,
    *,
    chunk_size: int = TASK_ARTIFACT_CHUNK_MAX_CHARS,
) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    for char_start in range(0, len(text), chunk_size):
        char_end_exclusive = min(char_start + chunk_size, len(text))
        chunks.append((char_start, char_end_exclusive, text[char_start:char_end_exclusive]))
    return chunks


def _extract_text_from_utf8_artifact_bytes(*, relative_path: str, payload: bytes) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TaskArtifactValidationError(
            f"artifact {relative_path} is not valid UTF-8 text"
        ) from exc


def _extract_pdf_name(dictionary: bytes, key: bytes) -> bytes | None:
    match = re.search(rb"/" + re.escape(key) + rb"\s*/([A-Za-z0-9_.#-]+)", dictionary)
    if match is None:
        return None
    return match.group(1)


def _extract_pdf_reference(dictionary: bytes, key: bytes) -> tuple[int, int] | None:
    match = re.search(rb"/" + re.escape(key) + rb"\s+(\d+)\s+(\d+)\s+R", dictionary)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _extract_pdf_reference_array(dictionary: bytes, key: bytes) -> list[tuple[int, int]]:
    match = re.search(rb"/" + re.escape(key) + rb"\s*\[(.*?)\]", dictionary, re.DOTALL)
    if match is None:
        return []
    return [
        (int(ref_match.group(1)), int(ref_match.group(2)))
        for ref_match in _PDF_REFERENCE_PATTERN.finditer(match.group(1))
    ]


def _extract_pdf_filter_names(dictionary: bytes) -> list[bytes]:
    array_match = re.search(rb"/Filter\s*\[(.*?)\]", dictionary, re.DOTALL)
    if array_match is not None:
        return re.findall(rb"/([A-Za-z0-9_.#-]+)", array_match.group(1))

    filter_name = _extract_pdf_name(dictionary, b"Filter")
    if filter_name is None:
        return []
    return [filter_name]


def _extract_pdf_stream_payload(
    *,
    relative_path: str,
    dictionary: bytes,
    body: bytes,
    stream_start: int,
) -> bytes:
    length_match = re.search(rb"/Length\s+(\d+)", dictionary)
    if length_match is not None:
        stream_length = int(length_match.group(1))
        stream_end = stream_start + stream_length
        if stream_end <= len(body):
            return body[stream_start:stream_end]

    stream_end = body.rfind(b"endstream")
    if stream_end == -1 or stream_end < stream_start:
        raise TaskArtifactValidationError(
            f"artifact {relative_path} contains an unreadable PDF stream"
        )

    payload = body[stream_start:stream_end]
    if payload.endswith(b"\r\n"):
        return payload[:-2]
    if payload.endswith((b"\n", b"\r")):
        return payload[:-1]
    return payload


def _parse_pdf_objects(*, relative_path: str, payload: bytes) -> dict[tuple[int, int], _PdfObject]:
    objects: dict[tuple[int, int], _PdfObject] = {}
    for match in _PDF_INDIRECT_OBJECT_PATTERN.finditer(payload):
        object_id = int(match.group(1))
        generation = int(match.group(2))
        body = match.group(3).strip()
        dictionary = body
        stream: bytes | None = None
        stream_index = body.find(b"stream")
        if stream_index != -1:
            dictionary = body[:stream_index].rstrip()
            stream_start = stream_index + len(b"stream")
            if body[stream_start : stream_start + 2] == b"\r\n":
                stream_start += 2
            elif body[stream_start : stream_start + 1] in (b"\r", b"\n"):
                stream_start += 1
            stream = _extract_pdf_stream_payload(
                relative_path=relative_path,
                dictionary=dictionary,
                body=body,
                stream_start=stream_start,
            )
        objects[(object_id, generation)] = _PdfObject(
            object_id=object_id,
            generation=generation,
            dictionary=dictionary,
            stream=stream,
            raw_content=body,
        )

    if not objects:
        raise TaskArtifactValidationError(f"artifact {relative_path} is not a valid PDF")
    return objects


def _read_pdf_literal_string(payload: bytes, start: int) -> tuple[bytes, int]:
    cursor = start + 1
    depth = 1
    result = bytearray()
    while cursor < len(payload):
        current = payload[cursor]
        if current == ord("\\"):
            cursor += 1
            if cursor >= len(payload):
                break
            escaped = payload[cursor]
            if escaped in b"nrtbf()\\":
                result.extend(
                    {
                        ord("n"): b"\n",
                        ord("r"): b"\r",
                        ord("t"): b"\t",
                        ord("b"): b"\b",
                        ord("f"): b"\f",
                        ord("("): b"(",
                        ord(")"): b")",
                        ord("\\"): b"\\",
                    }[escaped]
                )
                cursor += 1
                continue
            if escaped in b"\r\n":
                if escaped == ord("\r") and payload[cursor : cursor + 2] == b"\r\n":
                    cursor += 2
                else:
                    cursor += 1
                continue
            if chr(escaped).isdigit():
                octal_digits = bytes([escaped])
                cursor += 1
                while cursor < len(payload) and len(octal_digits) < 3 and chr(payload[cursor]).isdigit():
                    octal_digits += bytes([payload[cursor]])
                    cursor += 1
                result.append(int(octal_digits, 8))
                continue
            result.append(escaped)
            cursor += 1
            continue
        if current == ord("("):
            depth += 1
            result.append(current)
            cursor += 1
            continue
        if current == ord(")"):
            depth -= 1
            cursor += 1
            if depth == 0:
                return bytes(result), cursor
            result.append(current)
            continue
        result.append(current)
        cursor += 1

    raise TaskArtifactValidationError("PDF literal string terminated unexpectedly")


def _read_pdf_hex_string(payload: bytes, start: int) -> tuple[bytes, int]:
    cursor = start + 1
    hex_digits = bytearray()
    while cursor < len(payload):
        current = payload[cursor]
        if current == ord(">"):
            cursor += 1
            break
        if chr(current).isspace():
            cursor += 1
            continue
        hex_digits.append(current)
        cursor += 1

    if len(hex_digits) % 2 == 1:
        hex_digits.append(ord("0"))
    return bytes.fromhex(hex_digits.decode("ascii")), cursor


def _skip_pdf_whitespace_and_comments(payload: bytes, start: int) -> int:
    cursor = start
    while cursor < len(payload):
        current = payload[cursor]
        if chr(current).isspace():
            cursor += 1
            continue
        if current == ord("%"):
            while cursor < len(payload) and payload[cursor] not in b"\r\n":
                cursor += 1
            continue
        break
    return cursor


def _read_pdf_content_token(payload: bytes, start: int) -> tuple[object | None, int]:
    cursor = _skip_pdf_whitespace_and_comments(payload, start)
    if cursor >= len(payload):
        return None, cursor

    current = payload[cursor]
    if current == ord("("):
        return _read_pdf_literal_string(payload, cursor)
    if current == ord("<") and payload[cursor : cursor + 2] != b"<<":
        return _read_pdf_hex_string(payload, cursor)
    if current == ord("["):
        items: list[object] = []
        cursor += 1
        while True:
            cursor = _skip_pdf_whitespace_and_comments(payload, cursor)
            if cursor >= len(payload):
                raise TaskArtifactValidationError("PDF array terminated unexpectedly")
            if payload[cursor] == ord("]"):
                return items, cursor + 1
            item, cursor = _read_pdf_content_token(payload, cursor)
            if item is None:
                raise TaskArtifactValidationError("PDF array terminated unexpectedly")
            items.append(item)
    if current == ord("/"):
        cursor += 1
        token_start = cursor
        while cursor < len(payload) and not chr(payload[cursor]).isspace() and payload[cursor] not in b"()<>[]{}/%":
            cursor += 1
        return payload[token_start - 1 : cursor], cursor

    token_start = cursor
    while cursor < len(payload) and not chr(payload[cursor]).isspace() and payload[cursor] not in b"()<>[]{}/%":
        cursor += 1
    return payload[token_start:cursor], cursor


def _decode_pdf_text_bytes(raw: bytes) -> str:
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be", errors="ignore")
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le", errors="ignore")
    return raw.decode("latin-1", errors="ignore")


def _decode_pdf_text_operand(value: object | None) -> str:
    if isinstance(value, bytes):
        return _decode_pdf_text_bytes(value)
    if isinstance(value, list):
        return "".join(
            _decode_pdf_text_bytes(item) for item in value if isinstance(item, bytes)
        )
    return ""


def _pop_last_pdf_text_operand(operands: list[object]) -> object | None:
    for index in range(len(operands) - 1, -1, -1):
        candidate = operands[index]
        if isinstance(candidate, (bytes, list)):
            return operands.pop(index)
    return None


def _extract_text_from_pdf_content_stream(stream: bytes) -> str:
    operands: list[object] = []
    fragments: list[str] = []
    inside_text_block = False
    pending_newline = False
    cursor = 0

    def request_newline() -> None:
        nonlocal pending_newline
        if fragments:
            pending_newline = True

    def append_text(text: str) -> None:
        nonlocal pending_newline
        if text == "":
            return
        if pending_newline and fragments and fragments[-1] != "\n":
            fragments.append("\n")
        pending_newline = False
        fragments.append(text)

    while True:
        token, cursor = _read_pdf_content_token(stream, cursor)
        if token is None:
            break
        if isinstance(token, list) or (
            isinstance(token, bytes)
            and (
                token.startswith(b"/")
                or _PDF_NUMERIC_TOKEN_PATTERN.fullmatch(token) is not None
                or token in {b"true", b"false", b"null"}
            )
        ):
            operands.append(token)
            continue
        if not isinstance(token, bytes):
            operands.append(token)
            continue

        operator = token
        if operator == b"BT":
            inside_text_block = True
            operands.clear()
            continue
        if operator == b"ET":
            inside_text_block = False
            operands.clear()
            continue
        if operator not in _PDF_CONTENT_OPERATORS:
            operands.append(token)
            continue
        if not inside_text_block:
            operands.clear()
            continue
        if operator in {b"T*", b"Td", b"TD", b"Tm"}:
            request_newline()
            operands.clear()
            continue
        if operator in {b"Tj", b"TJ"}:
            append_text(_decode_pdf_text_operand(_pop_last_pdf_text_operand(operands)))
            operands.clear()
            continue
        if operator in {b"'", b'"'}:
            request_newline()
            append_text(_decode_pdf_text_operand(_pop_last_pdf_text_operand(operands)))
            operands.clear()
            continue
        operands.clear()

    return "".join(fragments).strip()


def _decode_pdf_stream(*, relative_path: str, pdf_object: _PdfObject) -> bytes:
    if pdf_object.stream is None:
        raise TaskArtifactValidationError(
            f"artifact {relative_path} contains a PDF content reference without a stream"
        )

    filters = _extract_pdf_filter_names(pdf_object.dictionary)
    if not filters:
        return pdf_object.stream
    if filters == [b"FlateDecode"]:
        try:
            return zlib.decompress(pdf_object.stream)
        except zlib.error as exc:
            raise TaskArtifactValidationError(
                f"artifact {relative_path} contains an unreadable FlateDecode PDF stream"
            ) from exc

    filter_names = ", ".join(f"/{name.decode('ascii', errors='ignore')}" for name in filters)
    raise TaskArtifactValidationError(
        f"artifact {relative_path} uses unsupported PDF stream filters {filter_names}"
    )


def _collect_pdf_page_refs(
    *,
    relative_path: str,
    objects: dict[tuple[int, int], _PdfObject],
    current_ref: tuple[int, int],
    collected_refs: list[tuple[int, int]],
    visited_refs: set[tuple[int, int]],
) -> None:
    if current_ref in visited_refs:
        return
    visited_refs.add(current_ref)
    current_object = objects.get(current_ref)
    if current_object is None:
        raise TaskArtifactValidationError(
            f"artifact {relative_path} references a missing PDF object {current_ref[0]} {current_ref[1]} R"
        )

    object_type = _extract_pdf_name(current_object.dictionary, b"Type")
    if object_type == b"Page":
        collected_refs.append(current_ref)
        return
    if object_type != b"Pages":
        raise TaskArtifactValidationError(
            f"artifact {relative_path} uses unsupported PDF page tree structure"
        )

    child_refs = _extract_pdf_reference_array(current_object.dictionary, b"Kids")
    if not child_refs:
        raise TaskArtifactValidationError(
            f"artifact {relative_path} uses unsupported PDF page tree structure"
        )
    for child_ref in child_refs:
        _collect_pdf_page_refs(
            relative_path=relative_path,
            objects=objects,
            current_ref=child_ref,
            collected_refs=collected_refs,
            visited_refs=visited_refs,
        )


def _resolve_pdf_page_refs(
    *,
    relative_path: str,
    objects: dict[tuple[int, int], _PdfObject],
) -> list[tuple[int, int]]:
    catalog_ref = next(
        (
            object_ref
            for object_ref, pdf_object in objects.items()
            if _extract_pdf_name(pdf_object.dictionary, b"Type") == b"Catalog"
        ),
        None,
    )
    if catalog_ref is None:
        raise TaskArtifactValidationError(f"artifact {relative_path} is not a valid PDF")

    pages_ref = _extract_pdf_reference(objects[catalog_ref].dictionary, b"Pages")
    if pages_ref is None:
        raise TaskArtifactValidationError(
            f"artifact {relative_path} uses unsupported PDF page tree structure"
        )

    page_refs: list[tuple[int, int]] = []
    _collect_pdf_page_refs(
        relative_path=relative_path,
        objects=objects,
        current_ref=pages_ref,
        collected_refs=page_refs,
        visited_refs=set(),
    )
    return page_refs


def _extract_text_from_pdf_artifact_bytes(*, relative_path: str, payload: bytes) -> str:
    if not payload.startswith(b"%PDF-"):
        raise TaskArtifactValidationError(f"artifact {relative_path} is not a valid PDF")

    objects = _parse_pdf_objects(relative_path=relative_path, payload=payload)
    page_refs = _resolve_pdf_page_refs(relative_path=relative_path, objects=objects)
    page_fragments: list[str] = []
    for page_ref in page_refs:
        page_object = objects[page_ref]
        content_refs = _extract_pdf_reference_array(page_object.dictionary, b"Contents")
        if not content_refs:
            single_content_ref = _extract_pdf_reference(page_object.dictionary, b"Contents")
            if single_content_ref is not None:
                content_refs = [single_content_ref]

        stream_fragments: list[str] = []
        for content_ref in content_refs:
            content_object = objects.get(content_ref)
            if content_object is None:
                raise TaskArtifactValidationError(
                    f"artifact {relative_path} references a missing PDF object {content_ref[0]} {content_ref[1]} R"
                )
            extracted = _extract_text_from_pdf_content_stream(
                _decode_pdf_stream(relative_path=relative_path, pdf_object=content_object)
            )
            if extracted != "":
                stream_fragments.append(extracted)
        if stream_fragments:
            page_fragments.append("\n".join(stream_fragments))

    extracted_text = "\n".join(page_fragments).strip()
    if extracted_text == "":
        raise TaskArtifactValidationError(
            f"artifact {relative_path} does not contain extractable PDF text"
        )
    return extracted_text


def extract_artifact_text(*, row: TaskArtifactRow, artifact_path: Path, media_type: str) -> str:
    payload = artifact_path.read_bytes()
    if media_type in SUPPORTED_TEXT_ARTIFACT_MEDIA_TYPES:
        return _extract_text_from_utf8_artifact_bytes(
            relative_path=row["relative_path"],
            payload=payload,
        )
    if media_type == SUPPORTED_PDF_ARTIFACT_MEDIA_TYPE:
        return _extract_text_from_pdf_artifact_bytes(
            relative_path=row["relative_path"],
            payload=payload,
        )
    raise TaskArtifactValidationError(
        f"artifact {row['relative_path']} has unsupported media type {media_type}"
    )


def resolve_registered_artifact_path(*, workspace_path: Path, relative_path: str) -> Path:
    artifact_path = (workspace_path / relative_path).resolve()
    ensure_artifact_path_is_rooted(
        workspace_path=workspace_path,
        artifact_path=artifact_path,
    )
    return artifact_path


def build_task_artifact_chunk_list_summary(
    chunk_rows: list[TaskArtifactChunkRow],
    *,
    media_type: str,
) -> TaskArtifactChunkListSummary:
    total_characters = sum(len(row["text"]) for row in chunk_rows)
    return {
        "total_count": len(chunk_rows),
        "total_characters": total_characters,
        "media_type": media_type,
        "chunking_rule": TASK_ARTIFACT_CHUNKING_RULE,
        "order": list(TASK_ARTIFACT_CHUNK_LIST_ORDER),
    }


def extract_unique_lexical_terms(text: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for match in _LEXICAL_TERM_PATTERN.finditer(text.casefold()):
        term = match.group(0)
        if term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms


def resolve_artifact_chunk_retrieval_query_terms(query: str) -> list[str]:
    terms = extract_unique_lexical_terms(query)
    if not terms:
        raise TaskArtifactChunkRetrievalValidationError(
            "artifact chunk retrieval query must include at least one word"
        )
    return terms


def build_task_artifact_chunk_retrieval_scope(
    *,
    kind: str,
    task_id: UUID,
    task_artifact_id: UUID | None = None,
) -> TaskArtifactChunkRetrievalScope:
    scope: TaskArtifactChunkRetrievalScope = {
        "kind": cast(TaskArtifactChunkRetrievalScopeKind, kind),
        "task_id": str(task_id),
    }
    if task_artifact_id is not None:
        scope["task_artifact_id"] = str(task_artifact_id)
    return scope


def build_task_artifact_chunk_retrieval_summary(
    *,
    total_count: int,
    searched_artifact_count: int,
    query: str,
    query_terms: list[str],
    scope: TaskArtifactChunkRetrievalScope,
) -> TaskArtifactChunkRetrievalSummary:
    return {
        "total_count": total_count,
        "searched_artifact_count": searched_artifact_count,
        "query": query,
        "query_terms": list(query_terms),
        "matching_rule": TASK_ARTIFACT_CHUNK_RETRIEVAL_MATCHING_RULE,
        "order": list(TASK_ARTIFACT_CHUNK_RETRIEVAL_ORDER),
        "scope": scope,
    }


def match_artifact_chunk_text(
    *,
    query_terms: list[str],
    chunk_text: str,
) -> TaskArtifactChunkRetrievalMatch | None:
    first_positions: dict[str, int] = {}
    for match in _LEXICAL_TERM_PATTERN.finditer(chunk_text.casefold()):
        term = match.group(0)
        if term not in first_positions:
            first_positions[term] = match.start()

    matched_terms = [term for term in query_terms if term in first_positions]
    if not matched_terms:
        return None

    return {
        "matched_query_terms": matched_terms,
        "matched_query_term_count": len(matched_terms),
        "first_match_char_start": min(first_positions[term] for term in matched_terms),
    }


def serialize_task_artifact_chunk_retrieval_item(
    *,
    artifact_row: TaskArtifactRow,
    chunk_row: TaskArtifactChunkRow,
    match: TaskArtifactChunkRetrievalMatch,
) -> TaskArtifactChunkRetrievalItem:
    return {
        "id": str(chunk_row["id"]),
        "task_id": str(artifact_row["task_id"]),
        "task_artifact_id": str(chunk_row["task_artifact_id"]),
        "relative_path": artifact_row["relative_path"],
        "media_type": infer_task_artifact_media_type(artifact_row) or "unknown",
        "sequence_no": chunk_row["sequence_no"],
        "char_start": chunk_row["char_start"],
        "char_end_exclusive": chunk_row["char_end_exclusive"],
        "text": chunk_row["text"],
        "match": match,
    }


def retrieve_matching_task_artifact_chunks(
    store: ContinuityStore,
    *,
    artifact_rows: list[TaskArtifactRow],
    query_terms: list[str],
) -> tuple[list[TaskArtifactChunkRetrievalItem], int]:
    matched_items_with_keys: list[
        tuple[tuple[int, int, str, int, str], TaskArtifactChunkRetrievalItem]
    ] = []
    searched_artifact_count = 0

    for artifact_row in artifact_rows:
        if artifact_row["ingestion_status"] != "ingested":
            continue

        searched_artifact_count += 1
        chunk_rows = store.list_task_artifact_chunks(artifact_row["id"])
        for chunk_row in chunk_rows:
            match = match_artifact_chunk_text(
                query_terms=query_terms,
                chunk_text=chunk_row["text"],
            )
            if match is None:
                continue

            item = serialize_task_artifact_chunk_retrieval_item(
                artifact_row=artifact_row,
                chunk_row=chunk_row,
                match=match,
            )
            matched_items_with_keys.append(
                (
                    (
                        -match["matched_query_term_count"],
                        match["first_match_char_start"],
                        artifact_row["relative_path"],
                        chunk_row["sequence_no"],
                        str(chunk_row["id"]),
                    ),
                    item,
                )
            )

    matched_items_with_keys.sort(key=lambda entry: entry[0])
    return [item for _, item in matched_items_with_keys], searched_artifact_count


def register_task_artifact_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskArtifactRegisterInput,
) -> TaskArtifactCreateResponse:
    del user_id

    workspace = store.get_task_workspace_optional(request.task_workspace_id)
    if workspace is None:
        raise TaskWorkspaceNotFoundError(
            f"task workspace {request.task_workspace_id} was not found"
        )

    workspace_path = Path(workspace["local_path"]).expanduser().resolve()
    artifact_path = resolve_artifact_path(request.local_path)
    _require_existing_file(artifact_path)
    ensure_artifact_path_is_rooted(
        workspace_path=workspace_path,
        artifact_path=artifact_path,
    )
    relative_path = build_workspace_relative_artifact_path(
        workspace_path=workspace_path,
        artifact_path=artifact_path,
    )

    store.lock_task_artifacts(workspace["id"])
    existing = store.get_task_artifact_by_workspace_relative_path_optional(
        task_workspace_id=workspace["id"],
        relative_path=relative_path,
    )
    if existing is not None:
        raise TaskArtifactAlreadyExistsError(
            _duplicate_registration_message(
                task_workspace_id=workspace["id"],
                relative_path=relative_path,
            )
        )

    try:
        row = store.create_task_artifact(
            task_id=workspace["task_id"],
            task_workspace_id=workspace["id"],
            status="registered",
            ingestion_status="pending",
            relative_path=relative_path,
            media_type_hint=request.media_type_hint,
        )
    except psycopg.errors.UniqueViolation as exc:
        raise TaskArtifactAlreadyExistsError(
            _duplicate_registration_message(
                task_workspace_id=workspace["id"],
                relative_path=relative_path,
            )
        ) from exc

    return {"artifact": serialize_task_artifact_row(row)}


def list_task_artifact_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> TaskArtifactListResponse:
    del user_id

    items = [serialize_task_artifact_row(row) for row in store.list_task_artifacts()]
    return {
        "items": items,
        "summary": {
            "total_count": len(items),
            "order": list(TASK_ARTIFACT_LIST_ORDER),
        },
    }


def get_task_artifact_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_artifact_id: UUID,
) -> TaskArtifactDetailResponse:
    del user_id

    row = store.get_task_artifact_optional(task_artifact_id)
    if row is None:
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")
    return {"artifact": serialize_task_artifact_row(row)}


def ingest_task_artifact_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskArtifactIngestInput,
) -> TaskArtifactIngestionResponse:
    del user_id

    row = store.get_task_artifact_optional(request.task_artifact_id)
    if row is None:
        raise TaskArtifactNotFoundError(f"task artifact {request.task_artifact_id} was not found")

    store.lock_task_artifact_ingestion(row["id"])
    row = store.get_task_artifact_optional(request.task_artifact_id)
    if row is None:
        raise TaskArtifactNotFoundError(f"task artifact {request.task_artifact_id} was not found")

    media_type = resolve_supported_task_artifact_media_type(row)
    chunk_rows = store.list_task_artifact_chunks(row["id"])
    if row["ingestion_status"] == "ingested":
        return {
            "artifact": serialize_task_artifact_row(row),
            "summary": build_task_artifact_chunk_list_summary(chunk_rows, media_type=media_type),
        }

    workspace = store.get_task_workspace_optional(row["task_workspace_id"])
    if workspace is None:
        raise TaskWorkspaceNotFoundError(
            f"task workspace {row['task_workspace_id']} was not found"
        )

    workspace_path = Path(workspace["local_path"]).expanduser().resolve()
    artifact_path = resolve_registered_artifact_path(
        workspace_path=workspace_path,
        relative_path=row["relative_path"],
    )
    _require_existing_file(artifact_path)
    text = extract_artifact_text(
        row=row,
        artifact_path=artifact_path,
        media_type=media_type,
    )
    normalized_text = normalize_artifact_text(text)
    for index, (char_start, char_end_exclusive, chunk_text) in enumerate(
        chunk_normalized_artifact_text(normalized_text),
        start=1,
    ):
        store.create_task_artifact_chunk(
            task_artifact_id=row["id"],
            sequence_no=index,
            char_start=char_start,
            char_end_exclusive=char_end_exclusive,
            text=chunk_text,
        )

    artifact_row = store.update_task_artifact_ingestion_status(
        task_artifact_id=row["id"],
        ingestion_status="ingested",
    )
    chunk_rows = store.list_task_artifact_chunks(row["id"])
    return {
        "artifact": serialize_task_artifact_row(artifact_row),
        "summary": build_task_artifact_chunk_list_summary(chunk_rows, media_type=media_type),
    }


def list_task_artifact_chunk_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_artifact_id: UUID,
) -> TaskArtifactChunkListResponse:
    del user_id

    row = store.get_task_artifact_optional(task_artifact_id)
    if row is None:
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")

    chunk_rows = store.list_task_artifact_chunks(task_artifact_id)
    media_type = infer_task_artifact_media_type(row) or "unknown"
    return {
        "items": [serialize_task_artifact_chunk_row(chunk_row) for chunk_row in chunk_rows],
        "summary": build_task_artifact_chunk_list_summary(chunk_rows, media_type=media_type),
    }


def retrieve_task_scoped_artifact_chunk_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskScopedArtifactChunkRetrievalInput,
) -> TaskArtifactChunkRetrievalResponse:
    del user_id

    task = store.get_task_optional(request.task_id)
    if task is None:
        raise TaskNotFoundError(f"task {request.task_id} was not found")

    query_terms = resolve_artifact_chunk_retrieval_query_terms(request.query)
    artifact_rows = store.list_task_artifacts_for_task(request.task_id)
    items, searched_artifact_count = retrieve_matching_task_artifact_chunks(
        store,
        artifact_rows=artifact_rows,
        query_terms=query_terms,
    )
    scope = build_task_artifact_chunk_retrieval_scope(
        kind="task",
        task_id=request.task_id,
    )
    return {
        "items": items,
        "summary": build_task_artifact_chunk_retrieval_summary(
            total_count=len(items),
            searched_artifact_count=searched_artifact_count,
            query=request.query,
            query_terms=query_terms,
            scope=scope,
        ),
    }


def retrieve_artifact_scoped_artifact_chunk_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ArtifactScopedArtifactChunkRetrievalInput,
) -> TaskArtifactChunkRetrievalResponse:
    del user_id

    artifact_row = store.get_task_artifact_optional(request.task_artifact_id)
    if artifact_row is None:
        raise TaskArtifactNotFoundError(f"task artifact {request.task_artifact_id} was not found")

    query_terms = resolve_artifact_chunk_retrieval_query_terms(request.query)
    items, searched_artifact_count = retrieve_matching_task_artifact_chunks(
        store,
        artifact_rows=[artifact_row],
        query_terms=query_terms,
    )
    scope = build_task_artifact_chunk_retrieval_scope(
        kind="artifact",
        task_id=artifact_row["task_id"],
        task_artifact_id=artifact_row["id"],
    )
    return {
        "items": items,
        "summary": build_task_artifact_chunk_retrieval_summary(
            total_count=len(items),
            searched_artifact_count=searched_artifact_count,
            query=request.query,
            query_terms=query_terms,
            scope=scope,
        ),
    }

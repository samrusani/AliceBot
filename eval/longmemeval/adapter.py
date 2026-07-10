"""Alice adapter: ingest LongMemEval haystacks and answer via real retrieval.

Per question the harness creates an isolated SQLite store (one file, no
services), then:

1. **Ingest** — every haystack session is rendered as speaker-tagged turns
   (one paragraph per turn, so ``vnext_capture.chunk_text`` chunks on turn
   boundaries) and captured through the real ``VNextCaptureService`` write
   path: sources, chunks, provenance, event log, candidate memories, and —
   when ``ALICE_EMBEDDINGS_BASE_URL``/``ALICE_EMBEDDINGS_MODEL`` are set —
   embed-on-write via the real provider. Candidate memories are then
   promoted to ``active`` with ``update_memory`` (the store's review-accept
   patch), because Alice's search stages only see active/accepted memories.
2. **Retrieve** — ``VNextRetrievalService.compile_context_pack`` runs with
   the benchmark question as the query (hybrid FTS5 + vector KNN + RRF, or
   FTS-only when no embedding provider is configured), and the pack is
   rendered into a compact context block: retrieved memories first, then
   chunk excerpts of the retrieved source sessions under a character
   budget — each source is guaranteed its best chunk (by query-term
   overlap) before the leftover budget goes to the next-best chunks
   globally, and the selected excerpts render oldest-session-first.
   When a session's best-matching *line* would be cut by the head-biased
   chunk boundary (late chess moves, item 7 of a numbered list), the
   source's guaranteed excerpt becomes a query-anchored window centered
   on that line instead — same cost cap, so packing stays round-robin.

The answer prompt is the official LongMemEval reading template with the
history slot filled by Alice's context block instead of the full haystack.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import time
from typing import Iterator
from uuid import UUID

from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user, sqlite_user_connection
from alicebot_api.vnext_capture import SourceCaptureInput, VNextCaptureService
from alicebot_api.vnext_retrieval import (
    VECTOR_STAGE_ENABLED,
    VNextRetrievalRequest,
    VNextRetrievalService,
    query_terms,
)
from alicebot_api.vnext_fact_keys import attach_memory_fact_keys
from alicebot_api.vnext_temporal_query import parse_event_datetime

from longmemeval.dataset import LongMemEvalQuestion, SessionTurn


LME_USER_ID = UUID("22222222-2222-4222-8222-222222222222")
LME_USER_EMAIL = "longmemeval@alice.local"
SOURCE_TYPE = "chat_session"
SOURCE_DOMAIN = "unknown"  # never domain-filtered by the retrieval policy
SOURCE_SENSITIVITY = "internal"

CONTEXT_CHAR_BUDGET_ENV = "ALICE_LME_CONTEXT_CHAR_BUDGET"
MAX_ITEMS_ENV = "ALICE_LME_MAX_ITEMS"
DEFAULT_CONTEXT_CHAR_BUDGET = 12_000
DEFAULT_MAX_ITEMS = 8

EMPTY_CONTEXT_PLACEHOLDER = "(no relevant chat history was retrieved)"

# Official LongMemEval reading templates (src/generation/run_generation.py in
# xiaowu0162/LongMemEval), verbatim; the history slot receives Alice's
# retrieved context block instead of the full haystack.
ANSWER_PROMPT_TEMPLATE = (
    "I will give you several history chats between you and a user. "
    "Please answer the question based on the relevant chat history.\n\n\n"
    "History Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer:"
)
ANSWER_PROMPT_TEMPLATE_COT = (
    "I will give you several history chats between you and a user. "
    "Please answer the question based on the relevant chat history. "
    "Answer the question step by step: first extract all the relevant information, "
    "and then reason over the information to get the answer.\n\n\n"
    "History Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer (step by step):"
)
ANSWER_MAX_TOKENS = 500
ANSWER_MAX_TOKENS_COT = 800

_WORD_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]+")


@dataclass(frozen=True, slots=True)
class IngestStats:
    session_count: int
    source_count: int
    duplicate_count: int
    chunk_count: int
    candidate_memory_count: int
    promoted_memory_count: int
    ingest_seconds: float

    def to_record(self) -> dict[str, object]:
        return {
            "session_count": self.session_count,
            "source_count": self.source_count,
            "duplicate_count": self.duplicate_count,
            "chunk_count": self.chunk_count,
            "candidate_memory_count": self.candidate_memory_count,
            "promoted_memory_count": self.promoted_memory_count,
            "ingest_seconds": round(self.ingest_seconds, 3),
        }


@dataclass(frozen=True, slots=True)
class RetrievalOutcome:
    context_block: str
    context_chars: int
    approx_context_tokens: int
    memory_count: int
    source_count: int
    excerpt_count: int
    vector_stage: str
    vector_enabled: bool
    warnings: tuple[str, ...]
    retrieval_seconds: float
    # Pack provenance, persisted in checkpoint rows so any later paired flip
    # is attributable offline: which sessions the source stage retrieved,
    # which memory rows the pack selected, and a digest of the exact
    # rendered context block (ids + hash only -- never the context text).
    source_session_ids: tuple[str, ...] = ()
    memory_ids: tuple[str, ...] = ()
    context_sha256: str = ""

    def to_record(self) -> dict[str, object]:
        return {
            "context_chars": self.context_chars,
            "approx_context_tokens": self.approx_context_tokens,
            "memory_count": self.memory_count,
            "source_count": self.source_count,
            "excerpt_count": self.excerpt_count,
            "vector_stage": self.vector_stage,
            "vector_enabled": self.vector_enabled,
            "warnings": list(self.warnings),
            "retrieval_seconds": round(self.retrieval_seconds, 3),
            "provenance": {
                "source_session_ids": list(self.source_session_ids),
                "memory_ids": list(self.memory_ids),
                "context_sha256": self.context_sha256,
            },
        }


def collapse_intra_turn_blank_lines(content: str) -> str:
    """Keep each turn a single chunking paragraph without reflowing lines."""
    return re.sub(r"\n\s*\n+", "\n", content.replace("\r\n", "\n").replace("\r", "\n")).strip()


def render_session_text(session_id: str, date: str, turns: tuple[SessionTurn, ...]) -> str:
    """Speaker-tagged session text; one paragraph per turn for chunking."""
    paragraphs = [f"Chat session {session_id} on {date}."]
    for turn in turns:
        content = collapse_intra_turn_blank_lines(turn.content)
        if content == "":
            continue
        paragraphs.append(f"[{turn.role.upper()}]: {content}")
    return "\n\n".join(paragraphs)


def build_answer_prompt(*, context_block: str, question: str, question_date: str, cot: bool = False) -> str:
    history = context_block if context_block.strip() else EMPTY_CONTEXT_PLACEHOLDER
    template = ANSWER_PROMPT_TEMPLATE_COT if cot else ANSWER_PROMPT_TEMPLATE
    return template.format(history, question_date, question)


def context_char_budget_from_env() -> int:
    raw = os.environ.get(CONTEXT_CHAR_BUDGET_ENV, "").strip()
    return int(raw) if raw else DEFAULT_CONTEXT_CHAR_BUDGET


def max_items_from_env() -> int:
    raw = os.environ.get(MAX_ITEMS_ENV, "").strip()
    return int(raw) if raw else DEFAULT_MAX_ITEMS


def _chunk_overlap_score(chunk_text: str, terms: frozenset[str]) -> int:
    if not terms:
        return 0
    tokens = set(_WORD_PATTERN.findall(chunk_text.casefold()))
    return len(terms & tokens)


def _iso_date(value: object) -> str | None:
    """``YYYY-MM-DD`` prefix of an ISO timestamp string, or None."""
    text = str(value or "")
    return text[:10] if len(text) >= 10 else None


def _validity_suffix(memory: dict[str, object]) -> str:
    """Compact suffix rendering a pack item's ``validity`` annotation.

    Factual metadata only, quoted from the retrieval pack (validity window
    dates, supersession state, correction timestamps) -- never instruction
    text, so the official reading templates stay untouched. Memories
    without the annotation render exactly as before (empty suffix).
    """
    validity = memory.get("validity")
    if not isinstance(validity, dict):
        return ""
    parts: list[str] = []
    valid_from = _iso_date(validity.get("valid_from"))
    valid_to = _iso_date(validity.get("valid_to"))
    if valid_from and valid_to:
        parts.append(f"valid {valid_from} → {valid_to}")
    elif valid_to:
        parts.append(f"valid until {valid_to}")
    elif valid_from:
        parts.append(f"valid from {valid_from}")
    corrected_at = _iso_date(validity.get("corrected_at"))
    if validity.get("superseded"):
        parts.append("superseded by a newer entry")
    elif validity.get("supersedes_memory_id"):
        updated_on = corrected_at or _iso_date(memory.get("created_at"))
        parts.append(
            f"updated {updated_on}; supersedes an earlier value"
            if updated_on
            else "supersedes an earlier value"
        )
    elif corrected_at:
        parts.append(f"corrected {corrected_at}")
    if not parts:
        return ""
    return f" [{'; '.join(parts)}]"
# -- query-anchored excerpt windows ------------------------------------------
#
# The head-biased failure mode: a source's best chunk (whole-chunk term
# overlap) contains the query's best-matching line near its tail, and the
# answer sits just past the chunk boundary ("28. Kg3" after "27. Kg2 Bd5+"),
# or an enumerated list is cut mid-run before the asked-about item. All
# triggers below are query-surface (query-term matches) or content-shape
# (line-initial/inline numbering density) — no benchmark labels.

_ANCHOR_MIN_SCORE = 3  # weighted line score required before anchoring may replace the head path
_ANCHOR_EXTENSION_MAX_CHARS = 1_600  # cap on the keep-the-enumeration-intact continuation
_ENUMERATED_LINE_HEAD_PATTERN = re.compile(r"^\s*\d{1,3}[.)]\s")
_INLINE_ENUMERATION_PATTERN = re.compile(r"(?:^|\s)\d{1,3}\.(?=\s|$)")


def _line_anchor_score(line: str, terms: frozenset[str]) -> int:
    """Weighted query-term overlap for one line; distinctive terms count double.

    Terms carrying a digit (move numbers, list ordinals, notation like
    ``kg2``) or five-plus characters are worth 2, short stopwordy terms 1,
    so "27. Kg2 Bd5+" outranks a chatty line matching "the ... move".
    """
    if not terms:
        return 0
    matched = terms & set(_WORD_PATTERN.findall(line.casefold()))
    return sum(2 if len(term) >= 5 or any(ch.isdigit() for ch in term) else 1 for term in matched)


def _has_enumeration_signal(line: str) -> bool:
    """Content-shape check: line-initial numbering or dense inline numbering.

    Catches numbered list items ("7. Transcriptionist") and wrapped move
    records ("bxc3 exd4 9. cxd4 Bb4 10. Rb1 a5 ...") without reading any
    benchmark metadata.
    """
    if _ENUMERATED_LINE_HEAD_PATTERN.match(line):
        return True
    return len(_INLINE_ENUMERATION_PATTERN.findall(line)) >= 2


def _trim_line_around_matches(line: str, terms: frozenset[str], *, max_chars: int) -> str:
    """Char window of an overlong line centered on its query-term matches."""
    spans = [match.span() for match in _WORD_PATTERN.finditer(line.casefold()) if match.group(0) in terms]
    if not spans:
        return line[:max_chars]
    center = (spans[0][0] + spans[-1][1]) // 2
    start = max(0, min(center - max_chars // 2, len(line) - max_chars))
    return line[start : start + max_chars]


@dataclass(frozen=True, slots=True)
class _AnchoredExcerpt:
    chunk_index: int  # chunk containing the anchor line (used for the excerpt header)
    text: str  # window text; costs no more than the baseline chunk it replaces
    extension_text: str  # downward enumeration continuation ("" if none); spent from the second-pass pool
    upward_extension_text: str  # upward enumeration continuation ("" if none); same pool
    covered_chunk_indexes: frozenset[int]  # chunks the window overlaps (kept out of pass 2)
    extension_chunk_indexes: frozenset[int]  # chunks the downward extension overlaps (excluded only if applied)
    upward_extension_chunk_indexes: frozenset[int]  # chunks the upward extension overlaps (excluded only if applied)


def _query_anchored_excerpt(
    ordered_chunks: list[tuple[int, str]],
    terms: frozenset[str],
    *,
    baseline_chunk_index: int,
    baseline_text: str,
) -> _AnchoredExcerpt | None:
    """Query-anchored window replacing a source's head-biased best chunk.

    Returns ``None`` whenever anchoring is not clearly warranted, in which
    case the caller keeps today's byte-identical best-chunk excerpt:
    single-chunk sources (the whole session is already visible), no line
    with a weighted score of at least ``_ANCHOR_MIN_SCORE``, or no
    enumeration shape near the matched line. Ordinary prose never anchors —
    not even when the best-matching line sits outside the baseline chunk —
    because a prose anchor move displaces the head-biased best chunk that
    usually carries the surrounding answer context; only enumerated runs
    (move records, numbered lists) have the cut-mid-run failure mode this
    window exists to fix.

    The window is centered on the best-matching line over the session's
    concatenated chunk stream (ties break to the earliest line), expands to
    whichever side is lighter (ties extend downward, where answers to
    "after X" questions live), and never exceeds the baseline entry's cost,
    so pass-1 packing admits exactly the same sources as before. When the
    window's lower edge cuts an enumerated run, the continuation through
    the run (capped) is returned separately for the second-pass pool; when
    the window's upper edge cuts an enumerated run, the lines above it are
    returned the same way (list items 1..k-1 when the window starts at k).
    """
    if len(ordered_chunks) < 2 or not terms:
        return None
    lines: list[tuple[int, str]] = []
    for position, (chunk_index, text) in enumerate(ordered_chunks):
        if position:
            lines.append((chunk_index, ""))  # paragraph seam between adjacent chunks
        for line in text.split("\n"):
            lines.append((chunk_index, line))
    best_index = -1
    best_score = 0
    for index, (_chunk_index, line) in enumerate(lines):
        score = _line_anchor_score(line, terms)
        if score > best_score:
            best_index, best_score = index, score
    if best_score < _ANCHOR_MIN_SCORE:
        return None
    anchor_chunk = lines[best_index][0]
    enumerated_shape = any(
        _has_enumeration_signal(lines[index][1])
        for index in range(max(0, best_index - 3), min(len(lines), best_index + 4))
    )
    if not enumerated_shape:
        return None
    # Cost parity with the baseline entry: same header except the excerpt
    # ordinal, so cap the window text to keep entry_length from growing.
    cap = len(baseline_text) + len(str(baseline_chunk_index + 1)) - len(str(anchor_chunk + 1))
    if cap <= 0:
        return None
    anchor_line = lines[best_index][1]
    low = high = best_index
    if len(anchor_line) > cap:
        window_text = _trim_line_around_matches(anchor_line, terms, max_chars=cap)
    else:
        length = len(anchor_line)
        above = below = 0
        while True:
            up_cost = len(lines[low - 1][1]) + 1 if low > 0 else None
            down_cost = len(lines[high + 1][1]) + 1 if high + 1 < len(lines) else None
            can_up = up_cost is not None and length + up_cost <= cap
            can_down = down_cost is not None and length + down_cost <= cap
            if can_down and (not can_up or below <= above):
                high += 1
                below += down_cost or 0
                length += down_cost or 0
            elif can_up:
                low -= 1
                above += up_cost or 0
                length += up_cost or 0
            else:
                break
        while low < best_index and lines[low][1] == "":
            low += 1
        while high > best_index and lines[high][1] == "":
            high -= 1
        window_text = "\n".join(line for _chunk_index, line in lines[low : high + 1])
    extension_lines: list[tuple[int, str]] = []
    if _has_enumeration_signal(lines[high][1]):
        extension_length = 0
        for chunk_index, line in lines[high + 1 :]:
            if not _has_enumeration_signal(line):
                break
            if extension_length + len(line) + 1 > _ANCHOR_EXTENSION_MAX_CHARS:
                break
            extension_lines.append((chunk_index, line))
            extension_length += len(line) + 1
    extension_text = "\n".join(line for _chunk_index, line in extension_lines)
    # Symmetric upward continuation: the window's TOP edge cutting an
    # enumerated run loses items 1..k-1 ("3. Tomato ..." without steps 1-2),
    # so walk upward while the shape holds, under the same cap, also spent
    # from the second-pass pool (never displacing pass-1 guarantees).
    upward_lines: list[tuple[int, str]] = []
    if low > 0 and _has_enumeration_signal(lines[low][1]):
        upward_length = 0
        for chunk_index, line in lines[low - 1 :: -1]:
            if not _has_enumeration_signal(line):
                break
            if upward_length + len(line) + 1 > _ANCHOR_EXTENSION_MAX_CHARS:
                break
            upward_lines.append((chunk_index, line))
            upward_length += len(line) + 1
    upward_lines.reverse()
    upward_extension_text = "\n".join(line for _chunk_index, line in upward_lines)
    if window_text == baseline_text and extension_text == "" and upward_extension_text == "":
        return None  # anchoring would change nothing; keep the old path
    return _AnchoredExcerpt(
        chunk_index=anchor_chunk,
        text=window_text,
        extension_text=extension_text,
        upward_extension_text=upward_extension_text,
        covered_chunk_indexes=frozenset(chunk_index for chunk_index, _line in lines[low : high + 1]),
        extension_chunk_indexes=frozenset(chunk_index for chunk_index, _line in extension_lines),
        upward_extension_chunk_indexes=frozenset(chunk_index for chunk_index, _line in upward_lines),
    )


class QuestionRun:
    """One LongMemEval question against one isolated Alice store."""

    def __init__(self, question: LongMemEvalQuestion, store: SQLiteVNextStore) -> None:
        self.question = question
        self.store = store
        self._source_sessions: dict[str, tuple[str, str]] = {}  # source_id -> (session_id, date)

    # -- ingest ------------------------------------------------------------

    def ingest(self) -> IngestStats:
        started = time.monotonic()
        capture = VNextCaptureService(self.store, actor_type="system")
        source_count = 0
        duplicate_count = 0
        chunk_count = 0
        candidate_count = 0
        session_count = 0
        for session_id, date, turns in self.question.sessions_with_metadata():
            session_count += 1
            text = render_session_text(session_id, date, turns)
            result = capture.capture_source(
                SourceCaptureInput(
                    source_type=SOURCE_TYPE,
                    title=f"Chat session {session_id} on {date}",
                    raw_text=text,
                    connector_name="longmemeval",
                    external_id=f"{self.question.question_id}/{session_id}",
                    domain=SOURCE_DOMAIN,
                    sensitivity=SOURCE_SENSITIVITY,
                    metadata_json={
                        "benchmark": "longmemeval",
                        "question_id": self.question.question_id,
                        "session_id": session_id,
                        "session_date": date,
                    },
                )
            )
            if result.duplicate:
                duplicate_count += 1
            else:
                source_count += 1
                chunk_count += result.chunk_count
                candidate_count += result.candidate_memory_count
            if result.source_id is not None and result.source_id not in self._source_sessions:
                self._source_sessions[result.source_id] = (session_id, date)
        promoted = self._promote_candidate_memories()
        return IngestStats(
            session_count=session_count,
            source_count=source_count,
            duplicate_count=duplicate_count,
            chunk_count=chunk_count,
            candidate_memory_count=candidate_count,
            promoted_memory_count=promoted,
            ingest_seconds=time.monotonic() - started,
        )

    def _promote_candidate_memories(self) -> int:
        """Accept capture candidates so Alice's search stages can see them.

        Mirrors the store-level review-accept patch (``status: active``) used
        by the product's review flow; without it, ``search_memories*`` only
        matches pre-existing active/accepted rows and the memory stages would
        run empty for every question.
        """
        promoted = 0
        for memory in self.store.list_memories(status="candidate"):
            updated = self.store.update_memory(
                memory_id=str(memory["id"]),
                patch={"status": "active"},
                actor_type="system",
            )
            # Promotion is also the derived-retrieval-key moment (mirrors
            # the product review-accept path); deterministic tier only so
            # keyless ingest never makes a model call.
            attach_memory_fact_keys(self.store, updated, use_env_provider=False)
            promoted += 1
        return promoted

    # -- retrieval ----------------------------------------------------------

    def retrieve(
        self,
        *,
        max_items: int | None = None,
        context_char_budget: int | None = None,
    ) -> RetrievalOutcome:
        resolved_max_items = max_items if max_items is not None else max_items_from_env()
        budget = context_char_budget if context_char_budget is not None else context_char_budget_from_env()
        service = VNextRetrievalService(self.store)
        request = VNextRetrievalRequest(
            query=self.question.question,
            max_items=resolved_max_items,
            include_sources=True,
            actor_type="system",
            # The question's own date is official benchmark input (the
            # reading template already presents it to the answering model);
            # passing it as the anchor clock lets relative phrases like
            # "two weeks ago" resolve against the conversation's timeline
            # instead of the wall clock.
            reference_time=parse_event_datetime(self.question.question_date),
        )
        started = time.monotonic()
        pack = service.compile_context_pack(request)
        retrieval_seconds = time.monotonic() - started
        context_block, excerpt_count = self._render_context_block(pack, budget=budget)
        memories = pack.get("relevant_memories") or []
        sources = pack.get("sources") or []
        trace = pack.get("trace") if isinstance(pack.get("trace"), dict) else {}
        vector_stage = str(trace.get("vector_stage", "unknown"))
        warnings = pack.get("warnings") or []
        source_session_ids = tuple(
            self._session_label(str(source.get("id")))[0]
            for source in sources
            if isinstance(source, dict) and source.get("id")
        )
        memory_ids = tuple(
            str(memory.get("id"))
            for memory in memories
            if isinstance(memory, dict) and memory.get("id")
        )
        return RetrievalOutcome(
            context_block=context_block,
            context_chars=len(context_block),
            approx_context_tokens=len(context_block) // 4,
            memory_count=len(memories),
            source_count=len(sources),
            excerpt_count=excerpt_count,
            vector_stage=vector_stage,
            vector_enabled=vector_stage == VECTOR_STAGE_ENABLED,
            warnings=tuple(str(warning) for warning in warnings),
            retrieval_seconds=retrieval_seconds,
            source_session_ids=source_session_ids,
            memory_ids=memory_ids,
            context_sha256=hashlib.sha256(context_block.encode("utf-8")).hexdigest(),
        )

    def _session_label(self, source_id: str) -> tuple[str, str]:
        if source_id in self._source_sessions:
            return self._source_sessions[source_id]
        source = self.store.get_source(source_id)
        if source is not None and isinstance(source.get("metadata_json"), dict):
            metadata = source["metadata_json"]
            session_id = str(metadata.get("session_id") or source_id)
            date = str(metadata.get("session_date") or "undated")
            self._source_sessions[source_id] = (session_id, date)
            return session_id, date
        return source_id, "undated"

    def _render_context_block(self, pack: dict[str, object], *, budget: int) -> tuple[str, int]:
        """Compact prompt block: memory facts, session excerpts, grounding notes.

        Fact lines append the pack's per-memory ``validity`` annotation when
        present (see ``_validity_suffix``): validity windows, supersession
        state, and correction dates, rendered as bracketed factual metadata.

        Excerpt packing is two-pass so one wordy session cannot crowd out
        the rest: pass 1 guarantees every retrieved source its single best
        excerpt (in source rank order), pass 2 spends the remaining budget
        on the next-best chunks globally by lexical-overlap score. A
        source's guaranteed excerpt is its best chunk, unless a query
        anchor fires (see ``_query_anchored_excerpt``): then it is a window
        centered on the best-matching line at the same cost, and any
        enumeration continuation is charged to the pass-2 pool. The
        selected excerpts render in session-timestamp order (oldest
        first), each prefixed with its session id and date.
        """
        lines: list[str] = []
        used = 0

        memories = pack.get("relevant_memories") or []
        fact_lines: list[str] = []
        for memory in memories:
            if not isinstance(memory, dict):
                continue
            text = str(memory.get("canonical_text") or memory.get("summary") or memory.get("title") or "").strip()
            if text == "":
                continue
            metadata = memory.get("metadata_json") if isinstance(memory.get("metadata_json"), dict) else {}
            source_id = str(metadata.get("source_id") or "")
            _session_id, date = self._session_label(source_id) if source_id else ("", "undated")
            fact_lines.append(f"- [{date}] {text}{_validity_suffix(memory)}")
        if fact_lines:
            lines.append("### Facts Alice remembers (with session dates):")
            lines.extend(fact_lines)
            used = sum(len(line) + 1 for line in lines)

        # Grounding note (pack-level retrieval statistic from
        # vnext_grounding): factual line(s) about salient query entities
        # with zero corpus support. Rendered with the other
        # retrieval-derived content below; the cost is reserved up front
        # so the note always fits inside the budget.
        grounding = pack.get("grounding") if isinstance(pack.get("grounding"), dict) else None
        grounding_lines: list[str] = []
        if grounding:
            for name in grounding.get("unsupported_entities") or []:
                grounding_lines.append(f'Note: no stored memories mention "{name}".')
        if grounding_lines:
            used += sum(len(line) + 1 for line in grounding_lines) + 1

        terms = frozenset(query_terms(self.question.question))
        # One entry per chunk: (-score, source_rank, chunk_index, session_id, date, text).
        chunks_by_source: list[list[tuple[int, int, int, str, str, str]]] = []
        ordered_chunks_by_source: list[list[tuple[int, str]]] = []  # (chunk_index, text) in session order
        sources = pack.get("sources") or []
        for source_rank, source in enumerate(sources):
            if not isinstance(source, dict):
                continue
            source_id = str(source.get("id"))
            session_id, date = self._session_label(source_id)
            source_chunks: list[tuple[int, int, int, str, str, str]] = []
            ordered_chunks: list[tuple[int, str]] = []
            for chunk in self.store.list_source_chunks(source_id):
                chunk_text = str(chunk.get("text") or "")
                if chunk_text.strip() == "":
                    continue
                score = _chunk_overlap_score(chunk_text, terms)
                chunk_index = int(chunk.get("chunk_index") or 0)
                source_chunks.append((-score, source_rank, chunk_index, session_id, date, chunk_text))
                ordered_chunks.append((chunk_index, chunk_text))
            source_chunks.sort(key=lambda item: (item[0], item[2]))  # best score first, then position
            ordered_chunks.sort(key=lambda item: item[0])
            if source_chunks:
                chunks_by_source.append(source_chunks)
                ordered_chunks_by_source.append(ordered_chunks)

        def entry_length(entry: tuple[int, int, int, str, str, str]) -> int:
            _neg_score, _source_rank, chunk_index, session_id, date, chunk_text = entry
            header = f"[Session {session_id} | {date} | excerpt {chunk_index + 1}]"
            return len(header) + len(chunk_text) + 3

        # Pass 1: every retrieved source gets its single best excerpt (source
        # rank order), so one wordy session cannot crowd out the rest. A
        # query-anchored window is capped at the baseline chunk's cost, so
        # admission decisions are identical either way; its enumeration
        # extension waits for the leftover pool below.
        selected: list[tuple[int, int, int, str, str, str]] = []
        # Per source: (chunk entries not yet shown, chunk indexes covered by an anchored window).
        leftovers: list[tuple[list[tuple[int, int, int, str, str, str]], frozenset[int]]] = []
        # (selected position, leftovers position, extension text, extension chunk indexes, joins above window).
        pending_extensions: list[tuple[int, int, str, frozenset[int], bool]] = []
        for source_chunks, ordered_chunks in zip(chunks_by_source, ordered_chunks_by_source):
            best = source_chunks[0]
            anchored = _query_anchored_excerpt(
                ordered_chunks, terms, baseline_chunk_index=best[2], baseline_text=best[5]
            )
            entry = best
            if anchored is not None:
                entry = (best[0], best[1], anchored.chunk_index, best[3], best[4], anchored.text)
            cost = entry_length(entry)
            if used + cost <= budget:
                selected.append(entry)
                used += cost
                if anchored is None:
                    leftovers.append((source_chunks[1:], frozenset()))
                else:
                    leftovers.append((source_chunks, anchored.covered_chunk_indexes))
                    if anchored.extension_text:
                        pending_extensions.append(
                            (
                                len(selected) - 1,
                                len(leftovers) - 1,
                                anchored.extension_text,
                                anchored.extension_chunk_indexes,
                                False,
                            )
                        )
                    if anchored.upward_extension_text:
                        pending_extensions.append(
                            (
                                len(selected) - 1,
                                len(leftovers) - 1,
                                anchored.upward_extension_text,
                                anchored.upward_extension_chunk_indexes,
                                True,
                            )
                        )
            else:
                leftovers.append((source_chunks, frozenset()))
        # Enumeration extensions spend the leftover pool first (source rank
        # order): a kept-intact list never evicts another source's
        # guaranteed excerpt, only competes with pass-2 chunks.
        for selected_position, leftover_position, extension_text, extension_chunk_indexes, joins_above in pending_extensions:
            extra = len(extension_text) + 1  # joined to the window with one newline
            if used + extra > budget:
                continue
            neg_score, source_rank, chunk_index, session_id, date, window_text = selected[selected_position]
            selected[selected_position] = (
                neg_score,
                source_rank,
                chunk_index,
                session_id,
                date,
                extension_text + "\n" + window_text if joins_above else window_text + "\n" + extension_text,
            )
            used += extra
            entries, covered = leftovers[leftover_position]
            leftovers[leftover_position] = (entries, covered | extension_chunk_indexes)
        # Pass 2: spend what is left on the next-best chunks globally,
        # skipping chunks an anchored window (or applied extension) already shows.
        remaining = [entry for entries, covered in leftovers for entry in entries if entry[2] not in covered]
        remaining.sort(key=lambda item: item[:3])
        for entry in remaining:
            cost = entry_length(entry)
            if used + cost > budget:
                continue
            selected.append(entry)
            used += cost

        # Render oldest-first so the excerpts read chronologically.
        selected.sort(key=lambda item: (item[4], item[1], item[2]))
        excerpt_count = len(selected)
        excerpt_lines: list[str] = []
        for _neg_score, _source_rank, chunk_index, session_id, date, chunk_text in selected:
            excerpt_lines.append(f"[Session {session_id} | {date} | excerpt {chunk_index + 1}]")
            excerpt_lines.append(chunk_text)
            excerpt_lines.append("")
        if excerpt_lines:
            if lines:
                lines.append("")
            lines.append("### Retrieved chat history excerpts:")
            lines.extend(excerpt_lines)

        if grounding_lines:
            # Retrieval statistic, not an instruction: it belongs with the
            # retrieval output, after the excerpts it summarizes.
            if lines:
                lines.append("")
            lines.extend(grounding_lines)

        return "\n".join(lines).strip(), excerpt_count


@contextmanager
def question_run(question: LongMemEvalQuestion, db_path: str | Path) -> Iterator[QuestionRun]:
    """Open an isolated per-question store and yield a :class:`QuestionRun`.

    Uses ``sqlite_user_connection`` (schema bootstrap + one transaction that
    commits on clean exit), exactly like the product's SQLite on-ramp.
    """
    with sqlite_user_connection(db_path, LME_USER_ID) as conn:
        ensure_sqlite_user(conn, LME_USER_ID, LME_USER_EMAIL, "LongMemEval Harness")
        store = SQLiteVNextStore(conn, LME_USER_ID)
        yield QuestionRun(question, store)


__all__ = [
    "ANSWER_MAX_TOKENS",
    "ANSWER_MAX_TOKENS_COT",
    "ANSWER_PROMPT_TEMPLATE",
    "ANSWER_PROMPT_TEMPLATE_COT",
    "CONTEXT_CHAR_BUDGET_ENV",
    "DEFAULT_CONTEXT_CHAR_BUDGET",
    "DEFAULT_MAX_ITEMS",
    "EMPTY_CONTEXT_PLACEHOLDER",
    "IngestStats",
    "LME_USER_EMAIL",
    "LME_USER_ID",
    "MAX_ITEMS_ENV",
    "QuestionRun",
    "RetrievalOutcome",
    "build_answer_prompt",
    "collapse_intra_turn_blank_lines",
    "context_char_budget_from_env",
    "max_items_from_env",
    "question_run",
    "render_session_text",
]

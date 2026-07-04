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
   chunk excerpts of the retrieved source sessions ranked by query-term
   overlap, under a character budget.

The answer prompt is the official LongMemEval reading template with the
history slot filled by Alice's context block instead of the full haystack.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
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
            self.store.update_memory(
                memory_id=str(memory["id"]),
                patch={"status": "active"},
                actor_type="system",
            )
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
        """Compact prompt block: memory facts, then ranked session excerpts."""
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
            fact_lines.append(f"- [{date}] {text}")
        if fact_lines:
            lines.append("### Facts Alice remembers (with session dates):")
            lines.extend(fact_lines)
            used = sum(len(line) + 1 for line in lines)

        terms = frozenset(query_terms(self.question.question))
        scored_chunks: list[tuple[int, int, int, str, str, str]] = []
        sources = pack.get("sources") or []
        for source_rank, source in enumerate(sources):
            if not isinstance(source, dict):
                continue
            source_id = str(source.get("id"))
            session_id, date = self._session_label(source_id)
            for chunk in self.store.list_source_chunks(source_id):
                chunk_text = str(chunk.get("text") or "")
                if chunk_text.strip() == "":
                    continue
                score = _chunk_overlap_score(chunk_text, terms)
                chunk_index = int(chunk.get("chunk_index") or 0)
                scored_chunks.append((-score, source_rank, chunk_index, session_id, date, chunk_text))
        scored_chunks.sort(key=lambda item: item[:3])

        excerpt_count = 0
        excerpt_lines: list[str] = []
        for _neg_score, _source_rank, chunk_index, session_id, date, chunk_text in scored_chunks:
            header = f"[Session {session_id} | {date} | excerpt {chunk_index + 1}]"
            entry_length = len(header) + len(chunk_text) + 3
            if used + entry_length > budget:
                continue
            excerpt_lines.append(header)
            excerpt_lines.append(chunk_text)
            excerpt_lines.append("")
            used += entry_length
            excerpt_count += 1
        if excerpt_lines:
            if lines:
                lines.append("")
            lines.append("### Retrieved chat history excerpts:")
            lines.extend(excerpt_lines)

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

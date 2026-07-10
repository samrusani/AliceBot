from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.vnext_capture import (
    USER_ASSERTED_VALUE_CONFIDENCE,
    USER_ASSERTED_VALUE_RULE,
    VNextCaptureService,
    VNextCaptureValidationError,
    chunk_text,
    content_hash_for_text,
    extract_candidate_memories,
    order_candidates_for_promotion,
)
from alicebot_api.vnext_entities import ENTITY_MENTION_EDGE_TYPE


class InMemoryVNextCaptureStore:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.events: list[dict[str, object]] = []
        self.sources: list[dict[str, object]] = []
        self.chunks: list[dict[str, object]] = []
        self.memories: list[dict[str, object]] = []
        self.provenance_links: list[dict[str, object]] = []
        self._source_by_hash: dict[str, dict[str, object]] = {}
        self._next_source_id = 1
        self._next_chunk_id = 1
        self._next_memory_id = 1
        self._next_provenance_id = 1

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.calls.append(f"append_event:{event['event_type']}")
        self.events.append(event)
        return event

    def get_source_by_content_hash(self, content_hash: str) -> dict[str, object] | None:
        self.calls.append("get_source_by_content_hash")
        return self._source_by_hash.get(content_hash)

    def create_source(self, source: dict[str, object], **_kwargs) -> dict[str, object]:
        self.calls.append("create_source")
        row = {
            **source,
            "id": f"source-{self._next_source_id}",
        }
        self._next_source_id += 1
        self.sources.append(row)
        self._source_by_hash[str(source["content_hash"])] = row
        return row

    def create_source_chunk(self, chunk: dict[str, object], **_kwargs) -> dict[str, object]:
        self.calls.append("create_source_chunk")
        row = {
            **chunk,
            "id": f"chunk-{self._next_chunk_id}",
        }
        self._next_chunk_id += 1
        self.chunks.append(row)
        return row

    def create_memory(self, memory: dict[str, object], **_kwargs) -> dict[str, object]:
        self.calls.append("create_memory")
        row = {
            **memory,
            "id": f"memory-{self._next_memory_id}",
        }
        self._next_memory_id += 1
        self.memories.append(row)
        return row

    def create_provenance_link(self, link: dict[str, object], **_kwargs) -> dict[str, object]:
        self.calls.append("create_provenance_link")
        row = {
            **link,
            "id": f"provenance-{self._next_provenance_id}",
        }
        self._next_provenance_id += 1
        self.provenance_links.append(row)
        return row


def test_capture_text_preserves_raw_source_before_normalization_and_links_candidates() -> None:
    store = InMemoryVNextCaptureStore()
    service = VNextCaptureService(store)

    result = service.capture_text(
        "Decision: Build vNext on a provenance-first kernel.\nFact: Alice vNext needs source chunks.",
        title="Manual capture",
        domain="project",
        sensitivity="private",
    )

    assert result.status == "imported"
    assert result.chunk_count == 1
    assert result.candidate_memory_count == 2
    assert store.calls.index("create_source") < store.calls.index("create_source_chunk")
    assert store.calls.index("create_source_chunk") < store.calls.index("create_memory")
    assert store.sources[0]["metadata_json"]["raw_text"].startswith("Decision: Build vNext")
    assert store.sources[0]["domain"] == "project"
    assert store.sources[0]["sensitivity"] == "private"
    assert store.memories[0]["status"] == "candidate"
    assert store.memories[0]["memory_type"] == "decision"
    assert store.memories[0]["domain"] == "project"
    assert store.provenance_links[0]["target_id"] == store.memories[0]["id"]
    assert store.provenance_links[0]["source_id"] == store.sources[0]["id"]
    assert store.provenance_links[0]["source_chunk_id"] == store.chunks[0]["id"]
    assert [event["event_type"] for event in store.events] == [
        "source.captured",
        "source.chunked",
        "memory.candidate_created",
        "memory.candidate_created",
    ]


def test_capture_text_deduplicates_existing_content_by_hash() -> None:
    store = InMemoryVNextCaptureStore()
    service = VNextCaptureService(store)
    raw_text = "Fact: Duplicate content should not create another source."

    first = service.capture_text(raw_text)
    second = service.capture_text(raw_text)

    assert first.status == "imported"
    assert second.status == "duplicate"
    assert second.duplicate is True
    assert len(store.sources) == 1
    assert len(store.chunks) == 1
    assert [event["event_type"] for event in store.events if event["event_type"] == "source.duplicate_skipped"]


def test_import_markdown_folder_imports_100_files_without_batch_duplicates(tmp_path: Path) -> None:
    for index in range(100):
        (tmp_path / f"note-{index:03d}.md").write_text(
            f"Fact: Markdown source {index} belongs in Alice vNext.\n",
            encoding="utf-8",
        )
    (tmp_path / "duplicate.md").write_text("Fact: Markdown source 42 belongs in Alice vNext.\n", encoding="utf-8")

    store = InMemoryVNextCaptureStore()
    service = VNextCaptureService(store)

    result = service.import_markdown_folder(tmp_path, domain="project", sensitivity="private")

    assert result.status == "ok"
    assert result.imported_count == 100
    assert result.duplicate_count == 1
    assert result.failed_count == 0
    assert len(store.sources) == 100
    assert len(store.memories) == 100
    assert all(link["evidence_role"] == "quoted_from" for link in store.provenance_links)
    assert store.events[-1]["event_type"] == "source.batch_import_completed"
    assert store.events[-1]["payload_json"]["imported_count"] == 100


def test_import_markdown_folder_logs_failed_imports_and_continues(tmp_path: Path) -> None:
    (tmp_path / "good.md").write_text("Fact: Valid markdown still imports.\n", encoding="utf-8")
    (tmp_path / "bad.md").write_bytes(b"\xff\xfe\x00\x00")

    store = InMemoryVNextCaptureStore()
    service = VNextCaptureService(store)

    result = service.import_markdown_folder(tmp_path)

    assert result.status == "partial"
    assert result.imported_count == 1
    assert result.failed_count == 1
    assert len(store.sources) == 1
    failure_events = [event for event in store.events if event["event_type"] == "source.import_failed"]
    assert len(failure_events) == 1
    assert failure_events[0]["payload_json"]["error_type"] == "UnicodeDecodeError"


def test_import_chatgpt_export_extracts_message_text_and_preserves_raw_json(tmp_path: Path) -> None:
    export_path = tmp_path / "conversations.json"
    export_payload = {
        "conversations": [
            {
                "title": "Alice vNext",
                "messages": [
                    {
                        "author": {"role": "user"},
                        "content": {"parts": ["Fact: ChatGPT exports should preserve provenance."]},
                    }
                ],
            }
        ]
    }
    export_path.write_text(json.dumps(export_payload), encoding="utf-8")
    store = InMemoryVNextCaptureStore()
    service = VNextCaptureService(store)

    result = service.import_chatgpt_export_file(export_path)

    assert result.status == "imported"
    assert result.candidate_memory_count == 1
    assert store.sources[0]["source_type"] == "chatgpt_export"
    assert store.sources[0]["metadata_json"]["raw_json"] == export_payload
    assert store.chunks[0]["text"] == "Fact: ChatGPT exports should preserve provenance."
    assert store.memories[0]["canonical_text"] == "ChatGPT exports should preserve provenance."


def test_chunking_and_candidate_extraction_are_deterministic() -> None:
    chunks = chunk_text("Fact: One durable claim.\n\nQuestion: What should Alice do next?", max_chars=200)
    chunk_rows = [{"id": f"chunk-{index}", "chunk_index": index, "text": text} for index, text in enumerate(chunks)]
    candidates = extract_candidate_memories(chunk_rows)

    assert content_hash_for_text("  Fact: One durable claim.\n") == content_hash_for_text("Fact: One durable claim.")
    assert [candidate.memory_type for candidate in candidates] == ["semantic", "question"]
    assert [candidate.text for candidate in candidates] == ["One durable claim.", "What should Alice do next?"]


def test_capture_file_rejects_unsupported_suffix(tmp_path: Path) -> None:
    binary_file = tmp_path / "archive.bin"
    binary_file.write_bytes(b"not text")
    service = VNextCaptureService(InMemoryVNextCaptureStore())

    with pytest.raises(VNextCaptureValidationError, match="unsupported vNext text source type"):
        service.capture_file(binary_file)


def _single_candidate(line: str):
    candidates = extract_candidate_memories([{"id": "chunk-0", "chunk_index": 0, "text": line}])
    assert len(candidates) == 1
    return candidates[0]


def test_procedure_prefix_extracts_procedure_candidate() -> None:
    candidate = _single_candidate("Procedure: Restart the ingest worker after every config change.")

    assert candidate.memory_type == "procedure"
    assert candidate.extraction_rule == "prefixed_procedure"
    assert candidate.text == "Restart the ingest worker after every config change."


def test_playbook_prefix_extracts_procedure_candidate() -> None:
    candidate = _single_candidate("Playbook: Rotate the Telegram bot token monthly via connector settings.")

    assert candidate.memory_type == "procedure"
    assert candidate.extraction_rule == "prefixed_procedure"
    assert candidate.text == "Rotate the Telegram bot token monthly via connector settings."


def test_how_to_line_extracts_procedure_and_keeps_full_text() -> None:
    candidate = _single_candidate("How to recover a failed scheduler run from the run history")

    assert candidate.memory_type == "procedure"
    assert candidate.extraction_rule == "how_to_procedure"
    assert candidate.text == "How to recover a failed scheduler run from the run history"


def test_how_to_question_still_captures_as_question() -> None:
    candidate = _single_candidate("How to fix the printer?")

    assert candidate.memory_type == "question"
    assert candidate.extraction_rule == "question_sentence"


def test_happened_prefix_extracts_episode_candidate() -> None:
    candidate = _single_candidate("Happened: The Postgres restore drill completed in 40 minutes.")

    assert candidate.memory_type == "episode"
    assert candidate.extraction_rule == "prefixed_episode"
    assert candidate.text == "The Postgres restore drill completed in 40 minutes."


def test_log_prefix_extracts_episode_candidate() -> None:
    candidate = _single_candidate("Log: Deployed v0.7.1 to the dogfood box at 09:12 UTC.")

    assert candidate.memory_type == "episode"
    assert candidate.extraction_rule == "prefixed_episode"
    assert candidate.text == "Deployed v0.7.1 to the dogfood box at 09:12 UTC."


# -- entity linking on the capture path ---------------------------------------------


def _sqlite_store() -> SQLiteVNextStore:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, "capture@example.com")
    return SQLiteVNextStore(conn, user_id)


def test_capture_links_entities_for_source_and_candidate_memories() -> None:
    store = _sqlite_store()
    service = VNextCaptureService(store)

    result = service.capture_text(
        "Fact: We met Sami Rusani of Type3 Capital.",
        title="Team note",
        domain="professional",
        sensitivity="internal",
    )

    assert result.status == "imported"
    assert result.candidate_memory_count == 1
    person = store.get_entity_by_normalized_name("person", "sami rusani")
    org = store.get_entity_by_normalized_name("organization", "type3 capital")
    assert person is not None and org is not None

    source_edges = store.list_edges(from_id=result.source_id)
    assert {(str(edge["to_id"]), str(edge["edge_type"])) for edge in source_edges} == {
        (str(person["id"]), ENTITY_MENTION_EDGE_TYPE),
        (str(org["id"]), ENTITY_MENTION_EDGE_TYPE),
    }
    # Event time on the edges is the source's own timestamp (captured_at
    # fallback since manual text carries no source_created_at).
    source_row = store.get_source(result.source_id)
    for edge in source_edges:
        assert edge["observed_at"] == source_row["captured_at"]

    # The candidate memory extracted from the prefixed line links too.
    candidate_memory = store.list_memories(status="candidate")[0]
    memory_edges = store.list_edges(from_id=str(candidate_memory["id"]))
    assert {str(edge["to_id"]) for edge in memory_edges} == {str(person["id"]), str(org["id"])}
    assert all(edge["from_type"] == "memory" for edge in memory_edges)


def test_recapturing_duplicate_content_does_not_double_count_mentions() -> None:
    store = _sqlite_store()
    service = VNextCaptureService(store)
    raw_text = "Fact: We met Sami Rusani of Type3 Capital."

    first = service.capture_text(raw_text, sensitivity="internal")
    second = service.capture_text(raw_text, sensitivity="internal")

    assert second.status == "duplicate"
    person = store.get_entity_by_normalized_name("person", "sami rusani")
    # One source mention + one candidate-memory mention from the first
    # capture; the duplicate recapture added nothing.
    assert person["mention_count"] == 2
    assert len(store.list_edges(from_id=first.source_id)) == 2


def test_private_sensitivity_skips_entity_extraction_entirely() -> None:
    store = _sqlite_store()
    service = VNextCaptureService(store)

    result = service.capture_text(
        "Fact: We met Sami Rusani of Type3 Capital.",
        sensitivity="private",
    )

    assert result.status == "imported"
    assert store.list_entities() == []
    assert store.list_edges(from_id=result.source_id) == []
    assert not [
        event
        for event in store.list_events()
        if str(event.get("event_type", "")).startswith("entity.")
    ]


class _BrokenEntityLookupStore(SQLiteVNextStore):
    def find_entities_by_names(self, normalized_names):  # type: ignore[override]
        raise RuntimeError("entity lookup exploded")


def test_entity_extraction_failure_never_fails_capture() -> None:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, "broken@example.com")
    store = _BrokenEntityLookupStore(conn, user_id)
    service = VNextCaptureService(store)

    result = service.capture_text(
        "Fact: We met Sami Rusani of Type3 Capital.",
        sensitivity="internal",
    )

    assert result.status == "imported"
    assert store.list_entities() == []
    failures = [
        event for event in store.list_events() if event.get("event_type") == "entity.extraction_failed"
    ]
    assert len(failures) == 1
    assert failures[0]["target_id"] == result.source_id
    assert failures[0]["payload_json"]["error_type"] == "RuntimeError"
    # No source.import_failed was logged: the capture itself succeeded.
    assert not [
        event for event in store.list_events() if event.get("event_type") == "source.import_failed"
    ]


def test_stores_without_the_entity_surface_skip_linking_silently() -> None:
    store = InMemoryVNextCaptureStore()
    service = VNextCaptureService(store)

    result = service.capture_text("Fact: We met Sami Rusani of Type3 Capital.", sensitivity="internal")

    assert result.status == "imported"
    assert not [
        event for event in store.events if event.get("event_type") == "entity.extraction_failed"
    ]


def test_existing_prefix_rules_are_untouched_by_new_rules() -> None:
    chunk_rows = [
        {
            "id": "chunk-0",
            "chunk_index": 0,
            "text": "\n".join(
                [
                    "Decision: Ship the staleness sweep this sprint.",
                    "Preference: Sam prefers review-first memory writes.",
                    "Remember: Alice is the continuity layer for agents.",
                    "Commitment: Send the migration notes by Friday.",
                ]
            ),
        }
    ]

    candidates = extract_candidate_memories(chunk_rows)

    assert [candidate.memory_type for candidate in candidates] == [
        "decision",
        "preference",
        "semantic",
        "open_loop",
    ]


# -- speaker provenance and promotion bias -------------------------------------------


def test_user_asserted_value_line_captures_with_provenance() -> None:
    candidate = _single_candidate("[USER]: I paid $50 for the taxi from the airport.")

    assert candidate.memory_type == "semantic"
    assert candidate.extraction_rule == "user_asserted_value"
    assert candidate.text == "[USER]: I paid $50 for the taxi from the airport."
    assert candidate.provenance_role == "user"
    assert candidate.assertion_class == "user_asserted"
    assert candidate.confidence == USER_ASSERTED_VALUE_CONFIDENCE


def test_assistant_estimate_still_captures_with_unchanged_legacy_confidence() -> None:
    candidate = _single_candidate(
        "[ASSISTANT]: The taxi fare from the airport is usually about $180-270 depending on traffic."
    )

    assert candidate.memory_type == "semantic"
    assert candidate.extraction_rule == "claim_sentence"
    assert candidate.provenance_role == "assistant"
    assert candidate.assertion_class == "assistant_estimate"
    # Provenance biases promotion ORDER only; confidence deltas were removed
    # because pack ranking never reads confidence (config must not imply
    # behavior that does not exist). Legacy claim_sentence confidence stands.
    assert candidate.confidence == pytest.approx(0.58)


def test_untagged_lines_take_the_byte_identical_legacy_path() -> None:
    tagged = _single_candidate("[USER]: My monthly rent is $1,850 for the new apartment.")
    untagged = _single_candidate("The monthly rent is $1,850 for the new apartment downtown.")

    assert tagged.provenance_role == "user"
    assert untagged.provenance_role is None
    assert untagged.assertion_class is None
    assert untagged.extraction_rule == "claim_sentence"
    assert untagged.confidence == 0.58  # legacy claim_sentence confidence, unchanged


def test_untagged_user_style_sentence_without_speaker_tag_gets_no_new_rule() -> None:
    # Same content shape as a user assertion but without a transcript tag:
    # the new gated rule must NOT fire, so no candidate is produced (the
    # legacy rules never matched "paid"-style sentences).
    candidates = extract_candidate_memories(
        [{"id": "chunk-0", "chunk_index": 0, "text": "I paid $50 for the taxi from the airport."}]
    )

    assert candidates == []


def test_same_slot_promotion_bias_user_value_beats_assistant_estimate() -> None:
    chunk_rows = [
        {
            "id": "chunk-0",
            "chunk_index": 0,
            "text": "\n".join(
                [
                    "[ASSISTANT]: A flight to Denver is typically around $200-300 for that route.",
                    "[USER]: I paid $150 for my flight to Denver.",
                ]
            ),
        }
    ]

    candidates = extract_candidate_memories(chunk_rows)
    assert len(candidates) == 2
    assistant_candidate, user_candidate = candidates
    assert assistant_candidate.assertion_class == "assistant_estimate"
    assert user_candidate.assertion_class == "user_asserted"

    ordered = order_candidates_for_promotion(candidates)
    assert [candidate.assertion_class for candidate in ordered] == [
        "user_asserted",
        "assistant_estimate",
    ]
    assert user_candidate.confidence > assistant_candidate.confidence


def test_order_candidates_for_promotion_keeps_untagged_order_unchanged() -> None:
    chunk_rows = [
        {
            "id": "chunk-0",
            "chunk_index": 0,
            "text": "\n".join(
                [
                    "Fact: The ingest worker restarts nightly at 02:00.",
                    "Decision: Ship the staleness sweep this sprint.",
                    "Question: Who owns the launch checklist?",
                ]
            ),
        }
    ]

    candidates = extract_candidate_memories(chunk_rows)
    assert order_candidates_for_promotion(candidates) == candidates


def test_capture_stamps_provenance_metadata_only_for_tagged_candidates() -> None:
    store = InMemoryVNextCaptureStore()
    service = VNextCaptureService(store)

    service.capture_text(
        "[USER]: I paid $50 for the taxi from the airport.\n\n"
        "Fact: Untagged content keeps its legacy metadata shape."
    )

    tagged = next(memory for memory in store.memories if memory["metadata_json"]["extraction_rule"] == "user_asserted_value")
    untagged = next(memory for memory in store.memories if memory["metadata_json"]["extraction_rule"] == "prefixed_semantic")
    assert tagged["metadata_json"]["provenance_role"] == "user"
    assert tagged["metadata_json"]["assertion_class"] == "user_asserted"
    assert "provenance_role" not in untagged["metadata_json"]
    assert "assertion_class" not in untagged["metadata_json"]


def test_assistant_derived_memory_still_promotes_and_recalls() -> None:
    store = _sqlite_store()
    service = VNextCaptureService(store)

    service.capture_text(
        "Chat session s1 on 2026/07/01.\n\n"
        "[ASSISTANT]: The Kyoto shuttle fare is usually about $40 per ride in peak season."
    )

    candidates = store.list_memories(status="candidate")
    assistant_memories = [
        memory
        for memory in candidates
        if memory["metadata_json"].get("provenance_role") == "assistant"
    ]
    assert assistant_memories, "assistant-derived content must still capture"
    for memory in candidates:
        store.update_memory(memory_id=str(memory["id"]), patch={"status": "active"}, actor_type="system")

    hits = store.search_memories_fts(query="Kyoto shuttle fare", limit=10)
    assert any(
        hit["metadata_json"].get("provenance_role") == "assistant" for hit in hits
    ), "assistant-derived memories must remain recallable"


# -- cross-batch dedupe of user-asserted-value promotions ----------------------------


_OMEGA_LINE = "[USER]: I paid $3,200 for my Omega Seamaster watch last spring."


def test_user_asserted_value_dedupes_against_existing_store_memories() -> None:
    """The same user-asserted value line in a LATER session must not mint a
    second memory with identical canonical text (cross-batch duplicate)."""
    store = _sqlite_store()
    service = VNextCaptureService(store)

    first = service.capture_text(f"Chat session s1 on 2026/07/01.\n\n{_OMEGA_LINE}")
    second = service.capture_text(
        f"Chat session s9 on 2026/07/08.\n\n{_OMEGA_LINE}\n\n"
        "[USER]: I also paid $40 for the strap replacement yesterday."
    )

    assert first.status == "imported" and second.status == "imported"
    omega_memories = [
        memory for memory in store.list_memories() if "Omega Seamaster" in str(memory.get("canonical_text"))
    ]
    assert len(omega_memories) == 1
    # The novel user-asserted line in the second session still captures.
    strap_memories = [
        memory for memory in store.list_memories() if "strap replacement" in str(memory.get("canonical_text"))
    ]
    assert len(strap_memories) == 1


def test_cross_batch_dedupe_is_scoped_to_user_asserted_value_rule() -> None:
    """Legacy rules keep their batch-local dedupe behavior byte-identical:
    a prefixed fact repeated across two captures still creates two rows."""
    store = _sqlite_store()
    service = VNextCaptureService(store)

    service.capture_text("Note one.\n\nFact: The ingest worker restarts nightly at 02:00.")
    service.capture_text("Note two.\n\nFact: The ingest worker restarts nightly at 02:00.")

    repeated = [
        memory for memory in store.list_memories() if "restarts nightly" in str(memory.get("canonical_text"))
    ]
    assert len(repeated) == 2


def test_cross_batch_dedupe_degrades_when_store_lacks_list_memories() -> None:
    """Minimal stores without ``list_memories`` skip the check instead of failing."""
    store = InMemoryVNextCaptureStore()
    service = VNextCaptureService(store)

    first = service.capture_text(f"Chat session s1 on 2026/07/01.\n\n{_OMEGA_LINE}")
    second = service.capture_text(f"Chat session s9 on 2026/07/08.\n\n{_OMEGA_LINE}\n\nExtra line.")

    assert first.status == "imported" and second.status == "imported"

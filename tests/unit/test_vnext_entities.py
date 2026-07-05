from __future__ import annotations

import sqlite3
from uuid import uuid4

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.vnext_entities import (
    ENTITY_EXTRACTION_BLOCKLIST,
    ENTITY_EXTRACTION_SKIP_SENSITIVITIES,
    ENTITY_MENTION_EDGE_TYPE,
    PERSON_ABOUT_EDGE_TYPE,
    RULE_CONFIDENCE,
    EntityLinkingService,
    derive_person_name_from_title,
    extract_entity_candidates,
    store_supports_entity_linking,
)
from alicebot_api.vnext_entity_names import ENTITY_TYPES


OBSERVED_AT = "2026-07-01T10:00:00Z"
LATER_OBSERVED_AT = "2026-07-02T09:30:00Z"
EARLIER_OBSERVED_AT = "2026-06-20T08:00:00Z"


# -- extraction: rule by rule -----------------------------------------------------


def _by_normalized(text: str) -> dict[str, object]:
    return {candidate.normalized: candidate for candidate in extract_entity_candidates(text)}


def test_capitalized_multi_word_span_extracts_person_guess() -> None:
    candidates = extract_entity_candidates("Yesterday Sami Rusani shipped the retrieval fix.")

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.name == "Sami Rusani"
    assert candidate.normalized == "sami rusani"
    assert candidate.entity_type == "person"
    assert candidate.source_rule == "capitalized_span"
    assert candidate.confidence == RULE_CONFIDENCE["capitalized_span"]


def test_org_suffix_span_guesses_organization() -> None:
    candidates = _by_normalized("We met Type3 Capital and Redwood Labs about the raise.")

    assert candidates["type3 capital"].entity_type == "organization"
    assert candidates["redwood labs"].entity_type == "organization"


def test_honorific_span_guesses_person_even_with_three_tokens() -> None:
    candidates = extract_entity_candidates("They invited Dr Sami Rusani to speak.")

    assert len(candidates) == 1
    assert candidates[0].normalized == "dr sami rusani"
    assert candidates[0].entity_type == "person"


def test_three_token_span_without_suffix_or_honorific_guesses_other() -> None:
    candidates = extract_entity_candidates("The Alice Continuity Kernel handles memory writes.")

    assert len(candidates) == 1
    # Leading blocklisted "The" is stripped from the span.
    assert candidates[0].name == "Alice Continuity Kernel"
    assert candidates[0].entity_type == "other"


def test_all_caps_acronym_extracts_between_2_and_6_chars() -> None:
    candidates = _by_normalized("The MCP server uses RRF fusion but not HTTPX yet.")

    assert candidates["mcp"].source_rule == "acronym"
    assert candidates["mcp"].entity_type == "other"
    assert candidates["mcp"].confidence == RULE_CONFIDENCE["acronym"]
    assert "rrf" in candidates
    assert "httpx" in candidates


def test_single_letter_and_overlong_caps_are_not_acronyms() -> None:
    candidates = _by_normalized("Grade A material for the ALICEBOTKERNEL run.")

    assert "a" not in candidates
    assert "alicebotkernel" not in candidates


def test_handle_extracts_person_and_skips_email_addresses() -> None:
    candidates = _by_normalized("Ping @samirusani, not sam@type3.capital, when it lands.")

    assert candidates["samirusani"].name == "@samirusani"
    assert candidates["samirusani"].entity_type == "person"
    assert candidates["samirusani"].source_rule == "handle"
    # The email's local part never becomes a handle; its domain still
    # resolves through the domain rule.
    assert candidates["type3.capital"].source_rule == "domain"


def test_bare_domain_extracts_organization_and_skips_file_suffixes() -> None:
    candidates = _by_normalized("Read type3.capital before editing notes.md or app.py today.")

    assert candidates["type3.capital"].entity_type == "organization"
    assert candidates["type3.capital"].confidence == RULE_CONFIDENCE["domain"]
    assert "notes.md" not in candidates
    assert "app.py" not in candidates


def test_numeric_dotted_values_are_not_domains() -> None:
    assert extract_entity_candidates("pi is 3.14 and the build is v1.2") == ()


def test_repeated_single_capitalized_token_requires_two_occurrences() -> None:
    none_found = extract_entity_candidates("Ask Hermes about the deploy window tomorrow.")
    repeated = extract_entity_candidates(
        "Hermes shipped the fix today. Everyone later thanked Hermes for it."
    )

    assert none_found == ()
    assert len(repeated) == 1
    assert repeated[0].normalized == "hermes"
    assert repeated[0].source_rule == "repeated_capitalized"
    assert repeated[0].confidence == RULE_CONFIDENCE["repeated_capitalized"]


def test_sentence_initial_only_single_words_are_skipped() -> None:
    # Both occurrences start a sentence: ordinary English capitalization,
    # not evidence of an entity.
    candidates = extract_entity_candidates("Hermes shipped the fix. Hermes left early.")

    assert candidates == ()


def test_blocklist_drops_weekday_month_and_sentence_starters() -> None:
    for token in ("monday", "january", "the", "this"):
        assert token in ENTITY_EXTRACTION_BLOCKLIST

    candidates = extract_entity_candidates(
        "This happened on Monday. Monday was rough. January was better than December January."
    )

    assert candidates == ()


def test_blocklisted_edge_tokens_are_stripped_from_spans() -> None:
    candidates = extract_entity_candidates("The Alice Core launch happens after The Alice Core review.")

    assert [candidate.name for candidate in candidates] == ["Alice Core"]


def test_span_occurrences_do_not_double_count_into_the_single_token_rule() -> None:
    candidates = extract_entity_candidates(
        "Sami Rusani wrote the plan. Later Sami Rusani revised the plan."
    )

    assert [candidate.normalized for candidate in candidates] == ["sami rusani"]


def test_empty_and_blank_text_yield_no_candidates() -> None:
    assert extract_entity_candidates("") == ()
    assert extract_entity_candidates("   \n\t  ") == ()


def test_all_confidences_stay_inside_the_documented_band() -> None:
    assert set(RULE_CONFIDENCE) == {
        "capitalized_span",
        "domain",
        "handle",
        "acronym",
        "repeated_capitalized",
    }
    for confidence in RULE_CONFIDENCE.values():
        assert 0.5 <= confidence <= 0.8


def test_entity_type_guesses_are_valid_store_entity_types() -> None:
    candidates = extract_entity_candidates(
        "Dr Sami Rusani of Type3 Capital pinged @hermes about MCP via type3.capital. "
        "Hermes agreed and later Hermes confirmed."
    )

    assert candidates
    for candidate in candidates:
        assert candidate.entity_type in ENTITY_TYPES


def test_private_or_stricter_sensitivities_are_in_the_skip_set() -> None:
    for sensitivity in ("private", "secret", "confidential", "highly_sensitive", "sacred", "regulated"):
        assert sensitivity in ENTITY_EXTRACTION_SKIP_SENSITIVITIES
    for sensitivity in ("public", "internal", "unknown"):
        assert sensitivity not in ENTITY_EXTRACTION_SKIP_SENSITIVITIES


def test_derive_person_name_from_title_takes_the_head_before_separators() -> None:
    assert derive_person_name_from_title("Sami Rusani") == "Sami Rusani"
    assert derive_person_name_from_title("Sami Rusani — Type3 intro") == "Sami Rusani"
    assert derive_person_name_from_title("Sami Rusani: GP at Type3") == "Sami Rusani"
    assert derive_person_name_from_title("Sami Rusani, investor") == "Sami Rusani"
    assert derive_person_name_from_title("Jean-Luc Picard - captain") == "Jean-Luc Picard"
    assert derive_person_name_from_title("...") is None
    assert derive_person_name_from_title("") is None


# -- linking service on live sqlite ------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(connection)
    yield connection
    connection.close()


def _store(conn: sqlite3.Connection, email: str = "owner@example.com") -> SQLiteVNextStore:
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, email)
    return SQLiteVNextStore(conn, user_id)


def _source(store: SQLiteVNextStore, title: str = "Note") -> str:
    row = store.create_source(
        {
            "source_type": "manual_text",
            "title": title,
            "content_hash": f"sha256:{uuid4().hex}",
            "domain": "professional",
            "sensitivity": "internal",
        }
    )
    return str(row["id"])


def test_store_support_guard_accepts_sqlite_store_and_rejects_bare_objects(conn) -> None:
    assert store_supports_entity_linking(_store(conn)) is True
    assert store_supports_entity_linking(object()) is False


def test_linking_creates_new_entities_with_observation_window_and_mention_edges(conn) -> None:
    store = _store(conn)
    source_id = _source(store)
    service = EntityLinkingService(store)

    linked = service.link_entities_for_source(
        source_id=source_id,
        text="Sami Rusani runs Type3 Capital.",
        observed_at=OBSERVED_AT,
    )

    assert [record["action"] for record in linked] == ["created", "created"]
    person = store.get_entity_by_normalized_name("person", "sami rusani")
    org = store.get_entity_by_normalized_name("organization", "type3 capital")
    assert person is not None and org is not None
    assert person["mention_count"] == 1
    assert person["first_observed_at"] == OBSERVED_AT
    assert person["last_observed_at"] == OBSERVED_AT

    edges = store.list_edges(from_id=source_id)
    assert {(str(edge["to_id"]), str(edge["edge_type"])) for edge in edges} == {
        (str(person["id"]), ENTITY_MENTION_EDGE_TYPE),
        (str(org["id"]), ENTITY_MENTION_EDGE_TYPE),
    }
    for edge in edges:
        assert edge["from_type"] == "source"
        assert edge["to_type"] == "entity"
        assert edge["observed_at"] == OBSERVED_AT
        assert edge["valid_from"] == OBSERVED_AT
        assert edge["created_by"] == "vnext_entity_linker"


def test_second_source_records_mention_and_widens_the_observation_window(conn) -> None:
    store = _store(conn)
    service = EntityLinkingService(store)
    first_source = _source(store, "First")
    second_source = _source(store, "Second")

    service.link_entities_for_source(
        source_id=first_source, text="Sami Rusani shipped it.", observed_at=OBSERVED_AT
    )
    linked = service.link_entities_for_source(
        source_id=second_source, text="Sami Rusani reviewed it.", observed_at=LATER_OBSERVED_AT
    )

    assert [record["action"] for record in linked] == ["mentioned"]
    entity = store.get_entity_by_normalized_name("person", "sami rusani")
    assert entity["mention_count"] == 2
    assert entity["first_observed_at"] == OBSERVED_AT
    assert entity["last_observed_at"] == LATER_OBSERVED_AT
    # One mentions edge per owning source.
    assert len(store.list_edges(to_id=str(entity["id"]))) == 2


def test_out_of_order_observation_only_widens_the_window_backwards(conn) -> None:
    store = _store(conn)
    service = EntityLinkingService(store)
    service.link_entities_for_source(
        source_id=_source(store), text="Sami Rusani shipped it.", observed_at=OBSERVED_AT
    )

    service.link_entities_for_source(
        source_id=_source(store), text="Sami Rusani planned it.", observed_at=EARLIER_OBSERVED_AT
    )

    entity = store.get_entity_by_normalized_name("person", "sami rusani")
    assert entity["first_observed_at"] == EARLIER_OBSERVED_AT
    assert entity["last_observed_at"] == OBSERVED_AT


def test_relinking_the_same_source_is_idempotent(conn) -> None:
    store = _store(conn)
    service = EntityLinkingService(store)
    source_id = _source(store)
    text = "Sami Rusani runs Type3 Capital."

    service.link_entities_for_source(source_id=source_id, text=text, observed_at=OBSERVED_AT)
    replay = service.link_entities_for_source(source_id=source_id, text=text, observed_at=LATER_OBSERVED_AT)

    assert [record["action"] for record in replay] == ["already_linked", "already_linked"]
    entity = store.get_entity_by_normalized_name("person", "sami rusani")
    assert entity["mention_count"] == 1
    assert entity["last_observed_at"] == OBSERVED_AT
    assert len(store.list_edges(from_id=source_id)) == 2


def test_honorific_variant_matches_existing_entity_and_appends_alias(conn) -> None:
    store = _store(conn)
    service = EntityLinkingService(store)
    service.link_entities_for_source(
        source_id=_source(store), text="Sami Rusani joined the call.", observed_at=OBSERVED_AT
    )

    linked = service.link_entities_for_source(
        source_id=_source(store), text="Dr Sami Rusani presented.", observed_at=LATER_OBSERVED_AT
    )

    assert [record["action"] for record in linked] == ["mentioned"]
    entity = store.get_entity_by_normalized_name("person", "sami rusani")
    assert entity["mention_count"] == 2
    assert entity["aliases"] == ["dr sami rusani"]
    # No second entity was created for the honorific variant.
    assert store.get_entity_by_normalized_name("person", "dr sami rusani") is None

    # A third variant occurrence resolves through the alias without
    # duplicating it.
    service.link_entities_for_source(
        source_id=_source(store), text="Dr Sami Rusani closed the round.", observed_at=LATER_OBSERVED_AT
    )
    entity = store.get_entity_by_normalized_name("person", "sami rusani")
    assert entity["mention_count"] == 3
    assert entity["aliases"] == ["dr sami rusani"]


def test_memory_linking_creates_memory_to_entity_edges(conn) -> None:
    store = _store(conn)
    service = EntityLinkingService(store)
    memory = store.create_memory(
        {
            "memory_key": f"memory.{uuid4()}",
            "value": {"text": "Sami Rusani prefers async standups."},
            "status": "active",
            "memory_type": "semantic",
            "title": "Standup preference",
            "canonical_text": "Sami Rusani prefers async standups.",
        }
    )

    linked = service.link_entities_for_memory(
        memory_id=str(memory["id"]),
        text=str(memory["canonical_text"]),
        observed_at=OBSERVED_AT,
    )

    assert [record["action"] for record in linked] == ["created"]
    edges = store.list_edges(from_id=str(memory["id"]))
    assert len(edges) == 1
    assert edges[0]["from_type"] == "memory"
    assert edges[0]["edge_type"] == ENTITY_MENTION_EDGE_TYPE
    assert edges[0]["observed_at"] == OBSERVED_AT


def test_link_memory_to_person_creates_person_entity_and_about_edge(conn) -> None:
    store = _store(conn)
    service = EntityLinkingService(store)
    memory = store.create_memory(
        {
            "memory_key": f"memory.{uuid4()}",
            "value": {},
            "status": "active",
            "memory_type": "person",
            "title": "Sami Rusani",
            "canonical_text": "GP at Type3 Capital.",
        }
    )

    result = service.link_memory_to_person(
        memory_id=str(memory["id"]), person_name="Sami Rusani", observed_at=OBSERVED_AT
    )
    replay = service.link_memory_to_person(
        memory_id=str(memory["id"]), person_name="Sami Rusani", observed_at=LATER_OBSERVED_AT
    )

    assert result["action"] == "created"
    assert result["edge"] is not None
    entity = store.get_entity_by_normalized_name("person", "sami rusani")
    assert entity is not None
    edges = [
        edge
        for edge in store.list_edges(from_id=str(memory["id"]))
        if str(edge["edge_type"]) == PERSON_ABOUT_EDGE_TYPE
    ]
    assert len(edges) == 1
    assert edges[0]["metadata_json"]["relation"] == "about"
    assert edges[0]["observed_at"] == OBSERVED_AT
    # Replay records the mention but never duplicates the edge.
    assert replay["action"] == "mentioned"
    assert replay["edge"] is None
    assert entity["id"] == store.get_entity_by_normalized_name("person", "sami rusani")["id"]


def test_linking_is_isolated_between_users_sharing_a_database(conn) -> None:
    store_a = _store(conn, "a@example.com")
    store_b = _store(conn, "b@example.com")
    source_a = _source(store_a)

    EntityLinkingService(store_a).link_entities_for_source(
        source_id=source_a, text="Sami Rusani runs Type3 Capital.", observed_at=OBSERVED_AT
    )

    assert store_b.list_entities() == []
    assert store_b.list_edges(from_id=source_a) == []

    # User B linking the same names creates B-scoped rows, not shared ones.
    source_b = _source(store_b)
    EntityLinkingService(store_b).link_entities_for_source(
        source_id=source_b, text="Sami Rusani runs Type3 Capital.", observed_at=OBSERVED_AT
    )
    entity_a = store_a.get_entity_by_normalized_name("person", "sami rusani")
    entity_b = store_b.get_entity_by_normalized_name("person", "sami rusani")
    assert entity_a is not None and entity_b is not None
    assert entity_a["id"] != entity_b["id"]
    assert entity_a["mention_count"] == 1
    assert entity_b["mention_count"] == 1

from __future__ import annotations

import pytest

from alicebot_api.vnext_coverage_query import (
    AGGREGATION_KIND_COMPARATIVE,
    AGGREGATION_KIND_COUNT,
    AGGREGATION_KIND_ENUMERATE,
    AGGREGATION_KIND_ORDERING,
    AGGREGATION_KIND_TOTAL,
    COVERAGE_MAX_CLAUSES,
    EXCLUSION_REASON_COVERAGE_REDUNDANT,
    apply_instance_diversity,
    clause_stage_name,
    coverage_stage_record,
    decompose_clauses,
    detect_aggregation_intent,
    source_chunk_text_provider,
)
from alicebot_api.vnext_retrieval import RetrievalCandidate


# -- intent detection ------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "kind"),
    (
        ("How many hours did I play?", AGGREGATION_KIND_COUNT),
        ("how many times did I visit the dentist this year", AGGREGATION_KIND_COUNT),
        ("Roughly HOW MANY books did I finish?", AGGREGATION_KIND_COUNT),
        ("How much did I spend in total on car repairs?", AGGREGATION_KIND_TOTAL),
        ("How much time did I spend commuting altogether?", AGGREGATION_KIND_TOTAL),
        ("In total, how much did the renovations cost?", AGGREGATION_KIND_TOTAL),
        ("What are all the books I mentioned reading?", AGGREGATION_KIND_ENUMERATE),
        ("Tell me about all of my doctor appointments", AGGREGATION_KIND_ENUMERATE),
        ("List every restaurant I tried in March", AGGREGATION_KIND_ENUMERATE),
        ("Name all the countries I visited", AGGREGATION_KIND_ENUMERATE),
        ("What did each of my doctors recommend?", AGGREGATION_KIND_ENUMERATE),
        ("In what order did I visit these cities?", AGGREGATION_KIND_ORDERING),
        ("in which order did the deliveries arrive", AGGREGATION_KIND_ORDERING),
        ("Which of my trips was the most expensive?", AGGREGATION_KIND_COMPARATIVE),
        ("which of the concerts I attended was the longest", AGGREGATION_KIND_COMPARATIVE),
    ),
)
def test_detector_fires_on_aggregation_surface_shapes(query: str, kind: str) -> None:
    intent = detect_aggregation_intent(query)

    assert intent is not None
    assert intent.kind == kind
    assert intent.trigger != ""


@pytest.mark.parametrize(
    "query",
    (
        "What did Marcus say about the roadmap?",
        # "how much" without a totality word is a single-fact question.
        "How much did the concert ticket cost?",
        "When did I adopt my dog?",
        "Where did I buy my espresso machine?",
        "What is the status of the beta rollout?",
        "Did I finish the marathon last October?",
        "Tell me about my last trip to Boston",
        "Who owns the incident postmortem for Meridian?",
        # "all" without the enumeration scaffold stays dormant.
        "Is the migration all done?",
        # "which of" without a comparative/superlative stays dormant.
        "Which of my colleagues moved to Berlin?",
        "",
        "   ",
    ),
)
def test_detector_stays_dormant_for_single_target_queries(query: str) -> None:
    assert detect_aggregation_intent(query) is None


def test_detector_reads_only_the_query_surface() -> None:
    # Same words, different casing/whitespace: still detected; the trigger
    # reports the matched surface text.
    intent = detect_aggregation_intent("  HOW   MANY  concerts\n did I attend? ")

    assert intent is not None
    assert intent.kind == AGGREGATION_KIND_COUNT
    assert intent.trigger == "how many"


# -- clause decomposition ---------------------------------------------------


def test_single_clause_aggregation_returns_the_query_itself() -> None:
    assert decompose_clauses("How many hours did I play?") == ["How many hours did I play"]


def test_coordinated_clauses_split_into_sub_queries() -> None:
    clauses = decompose_clauses("How many hours did I spend on hiking and swimming?")

    assert clauses == ["How many hours did I spend on hiking", "swimming"]


def test_comparative_pair_splits_on_comma_and_or() -> None:
    clauses = decompose_clauses("Which was more expensive, my trip to Paris or my trip to Rome?")

    assert clauses == ["Which was more expensive", "my trip to Paris", "my trip to Rome"]


def test_scaffold_only_fragments_are_dropped() -> None:
    # "was that the" carries no content tokens, so this stays single-clause.
    clauses = decompose_clauses("what did I do and was that the")

    assert clauses == ["what did I do and was that the"]


def test_duplicate_fragments_are_deduplicated_case_insensitively() -> None:
    clauses = decompose_clauses("trips to Paris and trips to paris and trips to Rome")

    assert clauses == ["trips to Paris", "trips to Rome"]


def test_decomposition_caps_at_max_clauses() -> None:
    query = "visits to Paris, visits to Rome, visits to Berlin, visits to Oslo, visits to Cairo"

    clauses = decompose_clauses(query)

    assert len(clauses) == COVERAGE_MAX_CLAUSES
    assert clauses == ["visits to Paris", "visits to Rome", "visits to Berlin", "visits to Oslo"]
    assert decompose_clauses(query, max_clauses=2) == ["visits to Paris", "visits to Rome"]


def test_empty_query_decomposes_to_nothing() -> None:
    assert decompose_clauses("   ") == []


def test_clause_stage_names_are_prefixed_and_indexed() -> None:
    assert clause_stage_name(1) == "coverage_clause_1"
    assert clause_stage_name(3) == "coverage_clause_3"


# -- stage record ------------------------------------------------------------


def test_coverage_stage_record_reports_intent_clauses_and_demotions() -> None:
    intent = detect_aggregation_intent("how many concerts did I attend")
    assert intent is not None

    record = coverage_stage_record(
        intent=intent,
        clause_count=2,
        clause_candidate_count=5,
        source_diversity_enabled=True,
        memory_demotions=2,
        source_demotions=1,
    )

    assert record == {
        "source": "coverage_mode",
        "intent": "count",
        "trigger": "how many",
        "clauses": 2,
        "clause_candidate_count": 5,
        "diversity_status": "enabled",
        "diversity_demotions": 3,
        "memory_demotions": 2,
        "source_demotions": 1,
    }

    disabled = coverage_stage_record(
        intent=intent,
        clause_count=1,
        clause_candidate_count=0,
        source_diversity_enabled=False,
        memory_demotions=0,
        source_demotions=0,
    )
    assert disabled["diversity_status"] == "disabled: store does not support source chunks"


# -- source instance diversity ------------------------------------------------


_DUPLICATE_TEXT = "friday board game night with the usual crowd we played catan and ate pizza"
_INSTANCE_TEXTS = {
    "inst-1": "board game night we played azul with sam and casey at the river cafe",
    "inst-2": "board game night we hosted wingspan for the neighbors on the porch",
    "inst-3": "board game night with codenames and homemade tacos at dana's loft",
    "inst-4": "board game night featuring terraforming mars and root with the club",
    "inst-5": "board game night where gloomhaven ran long and we ordered dumplings",
    "inst-6": "board game night trying splendor and ticket to ride with visiting cousins",
}


def _source_candidate(source_id: str, rank: int, *, selected: bool, exclusion_reason: str | None) -> RetrievalCandidate:
    return RetrievalCandidate(
        item={"id": source_id, "title": f"Chat session {source_id}"},
        target_type="source",
        rank=rank,
        rrf_score=1.0 / (60 + rank),
        stage_ranks={"title_recency": rank},
        selected=selected,
        exclusion_reason=exclusion_reason,
    )


def _diversity_fixture() -> tuple[list[RetrievalCandidate], dict[str, str]]:
    """Ten near-verbatim duplicates outranking six distinct instances."""
    texts: dict[str, str] = {}
    candidates: list[RetrievalCandidate] = []
    rank = 0
    for index in range(1, 11):
        rank += 1
        source_id = f"dupe-{index:02d}"
        texts[source_id] = _DUPLICATE_TEXT
        candidates.append(
            _source_candidate(
                source_id,
                rank,
                selected=rank <= 8,
                exclusion_reason=None if rank <= 8 else "trimmed_by_limit",
            )
        )
    for source_id, text in _INSTANCE_TEXTS.items():
        rank += 1
        texts[source_id] = text
        candidates.append(_source_candidate(source_id, rank, selected=False, exclusion_reason="trimmed_by_limit"))
    return candidates, texts


def test_near_duplicates_are_demoted_so_distinct_instances_fill_the_slots() -> None:
    candidates, texts = _diversity_fixture()

    rebuilt, demotions = apply_instance_diversity(
        candidates,
        text_for=lambda item: texts[str(item.get("id"))],
        limit=8,
    )

    assert demotions == 9  # dupe-02 .. dupe-10 lost their slots to instances
    selected_ids = [str(candidate.item["id"]) for candidate in rebuilt if candidate.selected]
    # The best duplicate keeps its slot, every distinct instance gets one,
    # and the leftover slot goes back to the next duplicate in fused order.
    assert selected_ids == ["dupe-01", *_INSTANCE_TEXTS, "dupe-02"]
    assert [candidate.rank for candidate in rebuilt] == list(range(1, len(candidates) + 1))
    unselected_dupes = [
        candidate
        for candidate in rebuilt
        if not candidate.selected and str(candidate.item["id"]).startswith("dupe-")
    ]
    assert {candidate.exclusion_reason for candidate in unselected_dupes} == {
        EXCLUSION_REASON_COVERAGE_REDUNDANT
    }


def test_diversity_pass_is_identity_when_pool_is_not_deeper_than_the_slots() -> None:
    candidates, texts = _diversity_fixture()
    small_pool = candidates[:8]

    rebuilt, demotions = apply_instance_diversity(
        small_pool,
        text_for=lambda item: texts[str(item.get("id"))],
        limit=8,
    )

    assert demotions == 0
    assert rebuilt == small_pool
    assert all(left is right for left, right in zip(rebuilt, small_pool))


def test_diversity_pass_is_identity_when_no_near_duplicates_exist() -> None:
    texts = dict(_INSTANCE_TEXTS)
    candidates = [
        _source_candidate(
            source_id,
            rank,
            selected=rank <= 4,
            exclusion_reason=None if rank <= 4 else "trimmed_by_limit",
        )
        for rank, source_id in enumerate(_INSTANCE_TEXTS, start=1)
    ]

    rebuilt, demotions = apply_instance_diversity(
        candidates,
        text_for=lambda item: texts[str(item.get("id"))],
        limit=4,
    )

    assert demotions == 0
    assert all(left is right for left, right in zip(rebuilt, candidates))


def test_policy_excluded_candidates_are_never_readmitted() -> None:
    candidates, texts = _diversity_fixture()
    filtered = _source_candidate("filtered-1", len(candidates) + 1, selected=False, exclusion_reason="sensitivity_filtered")
    texts["filtered-1"] = _INSTANCE_TEXTS["inst-1"]

    rebuilt, demotions = apply_instance_diversity(
        [*candidates, filtered],
        text_for=lambda item: texts[str(item.get("id"))],
        limit=8,
    )

    assert demotions == 9
    rebuilt_filtered = [candidate for candidate in rebuilt if candidate.item["id"] == "filtered-1"]
    assert len(rebuilt_filtered) == 1
    assert rebuilt_filtered[0].selected is False
    assert rebuilt_filtered[0].exclusion_reason == "sensitivity_filtered"
    assert rebuilt_filtered[0].rank == len(rebuilt)


def test_missing_chunk_text_is_never_treated_as_similar() -> None:
    candidates, _texts = _diversity_fixture()

    rebuilt, demotions = apply_instance_diversity(
        candidates,
        text_for=lambda item: "",
        limit=8,
    )

    assert demotions == 0
    assert all(left is right for left, right in zip(rebuilt, candidates))


def test_source_chunk_text_provider_requires_the_store_capability() -> None:
    assert source_chunk_text_provider(None) is None
    assert source_chunk_text_provider("not-callable") is None

    chunks = {
        "source-1": [
            {"id": "chunk-1", "source_id": "source-1", "text": "alpha"},
            {"id": "chunk-2", "source_id": "source-1", "text": ""},
            {"id": "chunk-3", "source_id": "source-1", "text": "beta"},
        ]
    }
    provider = source_chunk_text_provider(lambda source_id: chunks.get(source_id, []))

    assert provider is not None
    assert provider({"id": "source-1"}) == "alpha\nbeta"
    assert provider({"id": "missing"}) == ""


def test_source_chunk_text_provider_caps_signature_text() -> None:
    provider = source_chunk_text_provider(
        lambda source_id: [{"id": f"chunk-{index}", "source_id": source_id, "text": "x" * 600} for index in range(10)],
        max_chars=1000,
    )

    assert provider is not None
    text = provider({"id": "source-1"})
    # Stops appending once the cap is reached: two 600-char chunks.
    assert len(text) == 1201


def test_group_key_demotes_same_source_restatements() -> None:
    """Memories re-stating an already-kept memory's source yield their slots."""
    candidates = []
    for rank, (memory_id, source_id) in enumerate(
        (
            ("mem-a1", "src-a"),
            ("mem-a2", "src-a"),
            ("mem-a3", "src-a"),
            ("mem-b1", "src-b"),
            ("mem-c1", "src-c"),
            ("mem-d1", "src-d"),
        ),
        start=1,
    ):
        candidates.append(
            RetrievalCandidate(
                item={"id": memory_id, "canonical_text": f"note {memory_id}", "metadata_json": {"source_id": source_id}},
                target_type="memory",
                rank=rank,
                rrf_score=1.0 / (60 + rank),
                stage_ranks={"fts": rank},
                selected=rank <= 4,
                exclusion_reason=None if rank <= 4 else "trimmed_by_limit",
            )
        )

    rebuilt, demotions = apply_instance_diversity(
        candidates,
        group_key_for=lambda item: (item.get("metadata_json") or {}).get("source_id"),
        limit=4,
    )

    assert demotions == 2  # mem-a2, mem-a3
    selected = [str(candidate.item["id"]) for candidate in rebuilt if candidate.selected]
    assert selected == ["mem-a1", "mem-b1", "mem-c1", "mem-d1"]
    demoted_reasons = {
        str(candidate.item["id"]): candidate.exclusion_reason
        for candidate in rebuilt
        if not candidate.selected
    }
    assert demoted_reasons["mem-a2"] == EXCLUSION_REASON_COVERAGE_REDUNDANT
    assert demoted_reasons["mem-a3"] == EXCLUSION_REASON_COVERAGE_REDUNDANT


def test_missing_group_keys_never_group() -> None:
    candidates = [
        RetrievalCandidate(
            item={"id": f"mem-{rank}", "metadata_json": {}},
            target_type="memory",
            rank=rank,
            rrf_score=1.0 / (60 + rank),
            stage_ranks={"fts": rank},
            selected=rank <= 2,
            exclusion_reason=None if rank <= 2 else "trimmed_by_limit",
        )
        for rank in range(1, 6)
    ]

    rebuilt, demotions = apply_instance_diversity(
        candidates,
        group_key_for=lambda item: (item.get("metadata_json") or {}).get("source_id"),
        limit=2,
    )

    assert demotions == 0
    assert all(left is right for left, right in zip(rebuilt, candidates))


def test_diversity_pass_without_any_criterion_is_identity() -> None:
    candidates, _texts = _diversity_fixture()

    rebuilt, demotions = apply_instance_diversity(candidates, limit=8)

    assert demotions == 0
    assert all(left is right for left, right in zip(rebuilt, candidates))


def test_interleave_clause_rows_round_robins_per_clause() -> None:
    from alicebot_api.vnext_coverage_query import interleave_clause_rows

    row_a1, row_a2, row_b1, row_c1, row_c2, row_c3 = ({"id": name} for name in ("a1", "a2", "b1", "c1", "c2", "c3"))
    interleaved = interleave_clause_rows(
        {
            "coverage_clause_1": [row_a1, row_a2],
            "coverage_clause_2": [row_b1],
            "coverage_clause_3": [row_c1, row_c2, row_c3],
        }
    )

    assert [(stage, rank, row["id"]) for stage, rank, row in interleaved] == [
        ("coverage_clause_1", 1, "a1"),
        ("coverage_clause_2", 1, "b1"),
        ("coverage_clause_3", 1, "c1"),
        ("coverage_clause_1", 2, "a2"),
        ("coverage_clause_3", 2, "c2"),
        ("coverage_clause_3", 3, "c3"),
    ]


def test_interleave_clause_rows_handles_empty_input() -> None:
    from alicebot_api.vnext_coverage_query import interleave_clause_rows

    assert interleave_clause_rows({}) == []

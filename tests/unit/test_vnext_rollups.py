"""Roll-up cards: deterministic grouping, review gate, revisions, recall.

The live-SQLite tests exercise the full loop the product runs: the
consolidation workflow proposes a roll-up candidate, a reviewer accepts it
through the memory commit service, and the accepted card becomes an
ordinary FTS-indexed memory that wins aggregation-phrased recall while
every member stays individually recallable.
"""

from __future__ import annotations

import sqlite3
from uuid import uuid4

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.vnext_consolidation import MemoryConsolidationRequest, VNextConsolidationService
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_rollups import (
    ROLLUP_CANDIDATE_KIND,
    RollupOptions,
    VNextRollupService,
    VNextRollupValidationError,
)


# -- fakes ---------------------------------------------------------------------


class FakeRollupStore:
    """Minimal store surface for the pure grouping/proposal tests.

    Deliberately lacks ``find_entities_by_names`` so the optional entity
    surface guard is exercised (extraction-only fallback).
    """

    def __init__(self) -> None:
        self.memories: list[dict] = []
        self._counter = 0

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> JsonObject:
        self._counter += 1
        row = {
            "id": memory.get("id") or str(uuid4()),
            "created_at": f"2026-07-01T00:{self._counter:02d}:00Z",
            "updated_at": f"2026-07-01T00:{self._counter:02d}:00Z",
            **{key: value for key, value in memory.items() if key != "id"},
        }
        self.memories.append(row)
        return dict(row)

    def list_memories(self, *, status: str | None = None) -> list[JsonObject]:
        return [dict(row) for row in self.memories if status is None or row.get("status") == status]


GAME_SPECS = (
    ("game-1", "I played The Last of Us Part II for 30 hours", "2023-05-10", "USER"),
    ("game-2", "I played Assassin's Creed Odyssey for 70 hours", "2023-05-18", None),
    ("game-3", "I played Hollow Knight for 25 hours", "2023-06-02", None),
    ("game-4", "I played Stardew Valley for 85 hours", "2023-06-20", None),
    ("game-5", "I played Celeste for 10 hours", "2023-07-01", None),
)


def _seed_game_memories(store, *, ids: dict[str, str] | None = None, order: tuple[int, ...] | None = None) -> dict[str, JsonObject]:
    rows: dict[str, JsonObject] = {}
    indices = order if order is not None else tuple(range(len(GAME_SPECS)))
    for index in indices:
        key, text, session_date, speaker = GAME_SPECS[index]
        metadata: JsonObject = {"session_date": session_date}
        if speaker is not None:
            metadata["speaker"] = speaker
        memory: JsonObject = {
            "memory_key": f"memory.{key}",
            "value": {"text": text},
            "status": "active",
            "memory_type": "episode",
            "title": text[:80],
            "canonical_text": text,
            "summary": text[:80],
            "domain": "personal",
            "sensitivity": "internal",
            "metadata_json": metadata,
        }
        if ids is not None:
            memory["id"] = ids[key]
        rows[key] = store.create_memory(memory)
    return rows


def _rollup_candidates(store) -> list[JsonObject]:
    return [
        row
        for row in store.list_memories(status="candidate")
        if isinstance(row.get("metadata_json"), dict)
        and row["metadata_json"].get("candidate_kind") == ROLLUP_CANDIDATE_KIND
    ]


# -- options validation ------------------------------------------------------------


def test_invalid_rollup_options_are_rejected() -> None:
    with pytest.raises(VNextRollupValidationError):
        RollupOptions.from_metadata({"rollup_options": {"min_members": 1}})
    with pytest.raises(VNextRollupValidationError):
        RollupOptions.from_metadata({"rollup_options": {"min_members": "three"}})
    with pytest.raises(VNextRollupValidationError):
        RollupOptions.from_metadata({"rollup_options": {"max_rollups": 0}})
    with pytest.raises(VNextRollupValidationError):
        RollupOptions.from_metadata({"rollup_options": {"max_groupable_memories": 50000}})


def test_options_defaults_and_overrides_parse() -> None:
    assert RollupOptions.from_metadata(None) == RollupOptions()
    parsed = RollupOptions.from_metadata({"rollup_options": {"min_members": 4, "max_rollups": 3}})
    assert parsed.min_members == 4
    assert parsed.max_rollups == 3


# -- deterministic grouping -----------------------------------------------------------


def test_same_topic_instances_produce_one_rollup_card() -> None:
    store = FakeRollupStore()
    members = _seed_game_memories(store)
    outcome = VNextRollupService(store).propose_rollups()

    candidates = _rollup_candidates(store)
    assert len(candidates) == 1
    card = candidates[0]
    consolidation = card["metadata_json"]["consolidation"]
    assert consolidation["proposal_kind"] == "rollup"
    assert sorted(consolidation["cluster_member_ids"]) == sorted(str(row["id"]) for row in members.values())
    # First proposal supersedes NOTHING: members stay individually recallable.
    assert consolidation["proposed_supersede"] == []
    assert consolidation["survivor_memory_id"] is None
    assert card["status"] == "candidate"
    assert card["trust_class"] == "deterministic"
    assert card["metadata_json"]["review_required"] is True

    rollup = card["value"]["rollup"]
    assert rollup["member_count"] == 5
    assert rollup["group_kind"] == "topic"
    assert len(rollup["instances"]) == 5

    # Card content: every instance keeps its amount and date, in date order.
    text = card["canonical_text"]
    for amount in ("30 hours", "70 hours", "25 hours", "85 hours", "10 hours"):
        assert amount in text
    for day in ("2023-05-10", "2023-05-18", "2023-06-02", "2023-06-20", "2023-07-01"):
        assert day in text
    for name in ("Assassin's Creed Odyssey", "Hollow Knight", "Stardew Valley"):
        assert name in text
    assert text.index("2023-05-10") < text.index("2023-05-18") < text.index("2023-07-01")
    # The topic label carries the group's shared words.
    assert "hours" in card["title"]
    assert "played" in card["title"]

    # USER provenance carried when the member metadata has it.
    first = next(inst for inst in rollup["instances"] if inst["date"] == "2023-05-10")
    assert first["role"] == "USER"
    assert all("role" not in inst for inst in rollup["instances"] if inst["date"] != "2023-05-10")

    assert outcome.proposals[0]["candidate_state"] == "created"
    assert outcome.proposals[0]["instance_count"] == 5


def test_grouping_is_deterministic_across_insertion_order() -> None:
    fixed_ids = {key: str(uuid4()) for key, _, _, _ in GAME_SPECS}
    store_a, store_b = FakeRollupStore(), FakeRollupStore()
    _seed_game_memories(store_a, ids=fixed_ids)
    _seed_game_memories(store_b, ids=fixed_ids, order=(4, 2, 0, 3, 1))

    VNextRollupService(store_a).propose_rollups()
    VNextRollupService(store_b).propose_rollups()
    card_a = _rollup_candidates(store_a)[0]
    card_b = _rollup_candidates(store_b)[0]

    assert card_a["metadata_json"]["rollup_digest"] == card_b["metadata_json"]["rollup_digest"]
    assert card_a["metadata_json"]["rollup_key"] == card_b["metadata_json"]["rollup_key"]
    assert card_a["canonical_text"] == card_b["canonical_text"]
    assert card_a["title"] == card_b["title"]


def test_rerun_creates_no_duplicate_candidate() -> None:
    store = FakeRollupStore()
    _seed_game_memories(store)
    service = VNextRollupService(store)
    first = service.propose_rollups()
    second = service.propose_rollups()

    assert len(_rollup_candidates(store)) == 1
    assert second.proposals == []
    assert second.candidate_ids == first.candidate_ids
    assert any(group["state"] == "existing_candidate" for group in second.groups)


def test_same_entity_memories_group_into_entity_rollup() -> None:
    store = FakeRollupStore()
    for index, text in enumerate(
        (
            "Type3 Capital closed the seed round in March",
            "Quarterly review with Type3 Capital moved to October",
            "Type3 Capital is hiring two analysts this fall",
        )
    ):
        store.create_memory(
            {
                "memory_key": f"memory.entity-{index}",
                "value": {"text": text},
                "status": "active",
                "memory_type": "project_fact",
                "title": text[:80],
                "canonical_text": text,
                "summary": text[:80],
                "domain": "project",
                "sensitivity": "internal",
                "metadata_json": {},
            }
        )
    VNextRollupService(store).propose_rollups()
    candidates = _rollup_candidates(store)
    assert len(candidates) == 1
    card = candidates[0]
    assert card["value"]["rollup"]["group_kind"] == "entity"
    assert card["metadata_json"]["rollup_key"] == "entity:type3 capital"
    assert "Type3 Capital" in card["title"]
    assert card["value"]["rollup"]["member_count"] == 3
    assert card["memory_type"] == "project_fact"


def test_near_identical_texts_are_left_to_dedup() -> None:
    store = FakeRollupStore()
    for index in range(3):
        store.create_memory(
            {
                "memory_key": f"memory.dup-{index}",
                "value": {"text": "The launch window moves to March after the review."},
                "status": "active",
                "memory_type": "semantic",
                "title": "Launch window",
                "canonical_text": "The launch window moves to March after the review.",
                "summary": "Launch window",
                "domain": "project",
                "sensitivity": "internal",
                "metadata_json": {},
            }
        )
    outcome = VNextRollupService(store).propose_rollups()
    assert _rollup_candidates(store) == []
    assert any("near_duplicate_group_left_to_dedup" in reason for reason in outcome.skipped)


def test_groups_covered_by_near_duplicate_clusters_are_skipped() -> None:
    store = FakeRollupStore()
    members = _seed_game_memories(store)
    member_ids = {str(row["id"]) for row in members.values()}
    outcome = VNextRollupService(store).propose_rollups(exclude_member_id_sets=[member_ids])
    assert _rollup_candidates(store) == []
    assert any("covered_by_near_duplicate_cluster" in reason for reason in outcome.skipped)


def test_candidate_and_rollup_card_rows_never_rejoin_grouping() -> None:
    store = FakeRollupStore()
    _seed_game_memories(store)
    service = VNextRollupService(store)
    service.propose_rollups()
    # Flip the card to active as an accepted rollup would be, then rerun:
    # the card itself must not become a member of a new group.
    card = _rollup_candidates(store)[0]
    for row in store.memories:
        if row["id"] == card["id"]:
            row["status"] = "active"
    second = service.propose_rollups()
    assert second.proposals == []
    covered = [group for group in second.groups if group["state"] == "already_covered_by_accepted"]
    assert covered and covered[0]["accepted_memory_id"] == str(card["id"])


def test_create_candidate_memories_false_reports_without_writes() -> None:
    store = FakeRollupStore()
    _seed_game_memories(store)
    outcome = VNextRollupService(store).propose_rollups(create_candidate_memories=False)
    assert _rollup_candidates(store) == []
    assert len(outcome.proposals) == 1
    assert outcome.proposals[0]["candidate_memory_id"] is None


def test_max_rollups_bound_is_reported() -> None:
    store = FakeRollupStore()
    _seed_game_memories(store)
    for index, text in enumerate(
        (
            "Ran 5 km along the river on Tuesday",
            "Ran 8 km before work with the club",
            "Ran 12 km on the trail loop this weekend",
        )
    ):
        store.create_memory(
            {
                "memory_key": f"memory.run-{index}",
                "value": {"text": text},
                "status": "active",
                "memory_type": "episode",
                "title": text[:80],
                "canonical_text": text,
                "summary": text[:80],
                "domain": "personal",
                "sensitivity": "internal",
                "metadata_json": {},
            }
        )
    outcome = VNextRollupService(store).propose_rollups(
        options=RollupOptions.from_metadata({"rollup_options": {"max_rollups": 1}})
    )
    assert len(outcome.proposals) == 1
    assert any("rollup_bound" in reason for reason in outcome.skipped)


# -- model refinement (existing provider seam, deterministic fallback) ---------------


class StubRoute:
    approval_required = False
    route_mode = "cloud_allowed"
    policy_mode = "test"

    def to_record(self) -> JsonObject:
        return {"route_mode": self.route_mode}


class StubSummaryProvider:
    provider = "stub_model"
    model = "stub-rollup-1"

    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def chat(self, *, prompt: str, temperature: float) -> str:
        self.prompts.append(prompt)
        return self.response


def test_model_backed_summary_is_grounded_and_disclosed() -> None:
    store = FakeRollupStore()
    _seed_game_memories(store)
    stub = StubSummaryProvider(
        '{"summary": "Played Hollow Knight, Stardew Valley, Celeste and more, logging 30 hours to 85 hours each."}'
    )
    VNextRollupService(store, merge_provider=stub).propose_rollups(
        generation_mode="model_backed", route=StubRoute()
    )
    card = _rollup_candidates(store)[0]
    consolidation = card["metadata_json"]["consolidation"]
    assert "Summary: Played Hollow Knight" in card["canonical_text"]
    # The deterministic instance list is still fully present.
    for amount in ("30 hours", "70 hours", "25 hours", "85 hours", "10 hours"):
        assert amount in card["canonical_text"]
    assert card["trust_class"] == "llm_single_source"
    assert consolidation["model_provenance"]["provider"] == "stub_model"
    assert consolidation["model_provenance"]["prompt_hash"].startswith("sha256:")
    assert consolidation["merge_refusal"] is None
    assert stub.prompts and "[UNTRUSTED_CONTEXT_JSON]" in stub.prompts[0]


def test_ungrounded_model_summary_falls_back_to_deterministic_card() -> None:
    store = FakeRollupStore()
    _seed_game_memories(store)
    stub = StubSummaryProvider('{"summary": "Definitely a champion speedrunner sponsored by Redwood Beverages."}')
    VNextRollupService(store, merge_provider=stub).propose_rollups(
        generation_mode="model_backed", route=StubRoute()
    )
    card = _rollup_candidates(store)[0]
    assert "Summary:" not in card["canonical_text"]
    assert card["trust_class"] == "deterministic"
    refusal = card["metadata_json"]["consolidation"]["merge_refusal"]
    assert refusal is not None and refusal.startswith("ungrounded_model_output")


def test_deterministic_mode_never_calls_a_model() -> None:
    store = FakeRollupStore()
    _seed_game_memories(store)
    stub = StubSummaryProvider('{"summary": "should never be requested"}')
    VNextRollupService(store, merge_provider=stub).propose_rollups(generation_mode="deterministic")
    assert stub.prompts == []
    card = _rollup_candidates(store)[0]
    assert card["metadata_json"]["consolidation"]["model_provenance"] is None


# -- live sqlite: review gate, acceptance, recall, revisions ---------------------------


def _live_store() -> tuple[sqlite3.Connection, SQLiteVNextStore]:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, "rollups@example.com", "Rollup User")
    return conn, SQLiteVNextStore(conn, user_id)


def _seed_live_game_memories(store: SQLiteVNextStore) -> dict[str, JsonObject]:
    return _seed_game_memories(store)


def _compile_pack(store: SQLiteVNextStore, query: str) -> JsonObject:
    from alicebot_api.vnext_retrieval import VNextRetrievalRequest, VNextRetrievalService

    return VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query=query, max_items=8, actor_type="system")
    )


AGGREGATION_QUERY = "How many hours did I play in total?"


def test_unaccepted_rollup_candidate_never_appears_in_packs(monkeypatch) -> None:
    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)
    conn, store = _live_store()
    _seed_live_game_memories(store)
    VNextRollupService(store).propose_rollups()
    candidate_id = str(_rollup_candidates(store)[0]["id"])

    pack = _compile_pack(store, AGGREGATION_QUERY)
    pack_ids = {str(memory.get("id")) for memory in pack.get("relevant_memories") or []}
    assert candidate_id not in pack_ids
    conn.close()


def test_accepted_rollup_card_wins_recall_for_aggregation_query(monkeypatch) -> None:
    """The full product loop on live SQLite: propose -> accept -> recall."""
    from alicebot_api.vnext_memory_commit import VNextMemoryCommitService

    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)
    conn, store = _live_store()
    members = _seed_live_game_memories(store)
    VNextRollupService(store).propose_rollups()
    candidate_id = str(_rollup_candidates(store)[0]["id"])

    result = VNextMemoryCommitService(store).accept_consolidation_candidate(
        candidate_id, reason="Reviewed the games roll-up."
    )
    assert result["status"] == "accepted"
    assert result["proposal_kind"] == "rollup"
    # Superseding nothing is the roll-up contract.
    assert result["superseded_member_ids"] == []
    accepted = store.get_memory(candidate_id)
    assert accepted["status"] == "active"
    assert accepted["supersedes"] is None
    for row in members.values():
        member = store.get_memory(str(row["id"]))
        assert member["status"] == "active"
        assert member["superseded_by"] is None

    pack = _compile_pack(store, AGGREGATION_QUERY)
    ranked_ids = [str(memory.get("id")) for memory in pack.get("relevant_memories") or []]
    assert candidate_id in ranked_ids
    # The card outranks every individual member: one canonical hit instead
    # of needing all five instances to win pack slots.
    member_ids = {str(row["id"]) for row in members.values()}
    card_rank = ranked_ids.index(candidate_id)
    for member_id in member_ids:
        if member_id in ranked_ids:
            assert card_rank < ranked_ids.index(member_id)

    # Members remain individually recallable by their own content.
    member_pack = _compile_pack(store, "How long did I play Hollow Knight?")
    member_pack_ids = {str(memory.get("id")) for memory in member_pack.get("relevant_memories") or []}
    assert str(members["game-3"]["id"]) in member_pack_ids
    conn.close()


def test_new_member_triggers_revision_that_retires_only_the_old_card(monkeypatch) -> None:
    from alicebot_api.vnext_memory_commit import VNextMemoryCommitService

    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)
    conn, store = _live_store()
    members = _seed_live_game_memories(store)
    service = VNextRollupService(store)
    service.propose_rollups()
    first_card_id = str(_rollup_candidates(store)[0]["id"])
    commit = VNextMemoryCommitService(store)
    commit.accept_consolidation_candidate(first_card_id, reason="Initial games roll-up.")

    # A new same-topic memory arrives (on the commit path this costs O(1);
    # only the next scheduled pass reacts).
    new_member = store.create_memory(
        {
            "memory_key": "memory.game-6",
            "value": {"text": "I played Hades for 40 hours"},
            "status": "active",
            "memory_type": "episode",
            "title": "I played Hades for 40 hours",
            "canonical_text": "I played Hades for 40 hours",
            "summary": "I played Hades for 40 hours",
            "domain": "personal",
            "sensitivity": "internal",
            "metadata_json": {"session_date": "2023-07-15"},
        }
    )

    outcome = service.propose_rollups()
    assert len(outcome.proposals) == 1
    revision = outcome.proposals[0]
    assert revision["candidate_state"] == "revision_proposed"
    assert revision["revises_memory_id"] == first_card_id
    assert revision["proposed_supersede"] == [first_card_id]
    revision_row = store.get_memory(str(revision["candidate_memory_id"]))
    assert revision_row["status"] == "candidate"  # not silent mutation
    assert str(new_member["id"]) in revision_row["metadata_json"]["consolidation"]["cluster_member_ids"]
    assert "40 hours" in revision_row["canonical_text"]
    # The old card is untouched until a reviewer accepts the revision.
    assert store.get_memory(first_card_id)["status"] == "active"

    accepted = commit.accept_consolidation_candidate(
        str(revision["candidate_memory_id"]), reason="Roll-up now includes Hades."
    )
    assert accepted["superseded_member_ids"] == [first_card_id]
    assert store.get_memory(first_card_id)["status"] == "superseded"
    for row in (*members.values(), new_member):
        assert store.get_memory(str(row["id"]))["status"] == "active"

    # Idempotent follow-up: the accepted revision covers the topic.
    third = service.propose_rollups()
    assert third.proposals == []
    assert any(group["state"] == "already_covered_by_accepted" for group in third.groups)
    conn.close()


# -- consolidation workflow integration ------------------------------------------------


def test_consolidation_run_proposes_rollups_and_stays_review_only(monkeypatch) -> None:
    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)
    conn, store = _live_store()

    class ArtifactShim:
        def __init__(self, inner: SQLiteVNextStore) -> None:
            self._inner = inner
            self.artifacts: list[JsonObject] = []

        def __getattr__(self, name: str):
            return getattr(self._inner, name)

        def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> JsonObject:
            row = {"id": str(uuid4()), **artifact}
            self.artifacts.append(row)
            return dict(row)

    shim = ArtifactShim(store)
    members = _seed_live_game_memories(store)
    artifact = VNextConsolidationService(shim, embedding_provider=None).generate_memory_consolidation(
        MemoryConsolidationRequest()
    )

    candidates = _rollup_candidates(store)
    assert len(candidates) == 1
    rollups_metadata = artifact["metadata_json"]["rollups"]
    assert rollups_metadata["enabled"] is True
    assert rollups_metadata["grouping"] == "deterministic_entity_and_lexical_topic"
    assert len(rollups_metadata["proposals"]) == 1
    assert artifact["metadata_json"]["input_counts"]["rollup_proposals"] == 1
    assert str(candidates[0]["id"]) in artifact["metadata_json"]["candidate_memory_ids"]
    assert "## Roll-up Proposals" in artifact["content_markdown"]
    assert "members stay active" in artifact["content_markdown"]
    # Review-only: nothing about the members changed.
    for row in members.values():
        assert store.get_memory(str(row["id"]))["status"] == "active"
    conn.close()


def test_consolidation_run_with_rollups_disabled_creates_none(monkeypatch) -> None:
    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)
    conn, store = _live_store()

    class ArtifactShim:
        def __init__(self, inner: SQLiteVNextStore) -> None:
            self._inner = inner

        def __getattr__(self, name: str):
            return getattr(self._inner, name)

        def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> JsonObject:
            return {"id": str(uuid4()), **artifact}

    _seed_live_game_memories(store)
    artifact = VNextConsolidationService(ArtifactShim(store), embedding_provider=None).generate_memory_consolidation(
        MemoryConsolidationRequest(propose_rollups=False)
    )
    assert _rollup_candidates(store) == []
    assert artifact["metadata_json"]["rollups"] == {"enabled": False}
    assert "propose_rollups=false" in artifact["content_markdown"]
    conn.close()


# -- commit-path guard -------------------------------------------------------------------


def test_commit_path_issues_identical_queries_with_and_without_rollups(monkeypatch) -> None:
    """Roll-ups must add zero per-commit work: the SQL statement sequence
    of a memory commit is byte-identical whether the database holds no
    roll-up cards or an accepted card over many members."""
    import re

    from alicebot_api.vnext_memory_commit import MemoryCommitRequest, VNextMemoryCommitService

    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)

    timestamp_re = re.compile(r"\d{4}-\d{2}-\d{2}[T ][\d:.+]+Z?")
    uuid_re = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
    hash_re = re.compile(r"\b[0-9a-f]{16,64}\b")

    def _mask(statement: str) -> str:
        masked = timestamp_re.sub("<TS>", statement)
        masked = uuid_re.sub("<UUID>", masked)
        return hash_re.sub("<HASH>", masked)

    def _commit_statements(seed_rollups: bool) -> list[str]:
        conn, store = _live_store()
        if seed_rollups:
            _seed_live_game_memories(store)
            VNextRollupService(store).propose_rollups()
            candidate_id = str(_rollup_candidates(store)[0]["id"])
            VNextMemoryCommitService(store).accept_consolidation_candidate(
                candidate_id, reason="Accepted games roll-up."
            )
        statements: list[str] = []

        def _trace(statement: str) -> None:
            flattened = " ".join(statement.split())
            # sqlite prefixes internal statements (FTS5 segment writes,
            # trigger bodies) with "--"; those vary with index size and are
            # not application queries. Timestamp/uuid/hash literals differ
            # between runs by nature; masking them keeps the comparison
            # about application statement SHAPE and COUNT.
            if flattened.startswith("--"):
                return
            statements.append(_mask(flattened))

        conn.set_trace_callback(_trace)
        VNextMemoryCommitService(store).commit(
            identity=None,
            request=MemoryCommitRequest(
                user_id=str(store.user_id),
                title="grocery budget note",
                canonical_text="the weekly grocery budget stays around forty dollars",
                idempotency_key="commit-timing-probe",
            ),
        )
        conn.set_trace_callback(None)
        conn.close()
        return statements

    without_rollups = _commit_statements(seed_rollups=False)
    with_rollups = _commit_statements(seed_rollups=True)
    assert without_rollups, "commit issued no SQL; trace hook is broken"
    assert without_rollups == with_rollups


def test_commit_and_capture_never_invoke_the_rollup_pass(monkeypatch) -> None:
    """Belt and braces for the O(1) commit-path guarantee: even if a store
    holds roll-up state, committing and capturing must never call into the
    roll-up service (which only the scheduled consolidation workflow runs)."""
    from alicebot_api import vnext_rollups
    from alicebot_api.vnext_capture import SourceCaptureInput, VNextCaptureService
    from alicebot_api.vnext_memory_commit import MemoryCommitRequest, VNextMemoryCommitService

    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)

    def _explode(self, **kwargs):  # pragma: no cover - failure path
        raise AssertionError("rollup pass ran on the commit/capture path")

    monkeypatch.setattr(vnext_rollups.VNextRollupService, "propose_rollups", _explode)

    conn, store = _live_store()
    result = VNextMemoryCommitService(store).commit(
        identity=None,
        request=MemoryCommitRequest(
            user_id=str(store.user_id),
            title="capture guard note",
            canonical_text="the capture guard note stays plain and lowercase",
        ),
    )
    assert result["status"] in {"committed", "needs_confirmation", "proposed"}
    capture = VNextCaptureService(store, actor_type="system")
    capture.capture_source(
        SourceCaptureInput(
            source_type="note",
            title="plain note",
            raw_text="remember: the standup moved to nine thirty on wednesdays",
        )
    )
    conn.close()

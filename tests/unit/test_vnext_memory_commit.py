from __future__ import annotations

import pytest

from alicebot_api.vnext_agent_control import AgentIdentity
from alicebot_api.vnext_memory_commit import (
    MEMORY_STATUSES,
    MemoryCommitRequest,
    VNextMemoryCommitService,
    VNextMemoryCommitValidationError,
    evaluate_memory_commit_policy,
)


@pytest.fixture(autouse=True)
def _clear_embedding_env(monkeypatch) -> None:
    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)


def _identity(permission_profile: str, *, project_scope: tuple[str, ...] = ()) -> AgentIdentity:
    return AgentIdentity(
        agent_id="hermes" if permission_profile != "project_scoped_agent" else "openclaw",
        agent_type="personal_assistant",
        permission_profile=permission_profile,
        project_scope=project_scope,
    )


def _request(**overrides: object) -> MemoryCommitRequest:
    payload = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "title": "Coffee preference",
        "canonical_text": "Sam prefers coffee before noon.",
        "domain": "personal",
        "sensitivity": "private",
        "confidence": 0.95,
    }
    payload.update(overrides)
    return MemoryCommitRequest(**payload)  # type: ignore[arg-type]


def test_trusted_explicit_direct_memory_auto_commits() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("trusted_local_agent"),
        request=_request(domain="professional", sensitivity="internal"),
    )

    assert decision.write_mode == "commit"
    assert decision.status == "committed"
    assert decision.requires_confirmation is False
    assert decision.requires_dashboard_review is False


def test_sensitive_memory_requires_inline_confirmation() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("trusted_local_agent"),
        request=_request(domain="health", sensitivity="confidential"),
    )

    assert decision.write_mode == "confirm_inline"
    assert decision.status == "confirmation_required"
    assert "sensitive_memory_requires_confirmation" in decision.reasons


def test_external_source_requires_dashboard_review() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("trusted_local_agent"),
        request=_request(source_type="browser_clip"),
    )

    assert decision.write_mode == "propose_review"
    assert decision.status == "review_required"
    assert "external_source_requires_review" in decision.reasons


def test_read_only_agent_is_rejected() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("read_only_agent"),
        request=_request(domain="professional", sensitivity="internal"),
    )

    assert decision.write_mode == "reject"
    assert decision.status == "rejected"
    assert "read_only_agent_cannot_write" in decision.reasons


def test_project_scoped_agent_can_commit_project_memory_in_scope() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("project_scoped_agent", project_scope=("Alice",)),
        request=_request(domain="project", sensitivity="private", project_scope=("Alice",)),
    )

    assert decision.write_mode == "commit"
    assert decision.status == "committed"


def test_project_scoped_agent_rejects_non_project_memory() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("project_scoped_agent", project_scope=("Alice",)),
        request=_request(domain="family", sensitivity="private", project_scope=("Alice",)),
    )

    assert decision.write_mode == "reject"
    assert "project_scoped_agent_domain_out_of_scope" in decision.reasons


def test_contradiction_requires_inline_confirmation() -> None:
    decision = evaluate_memory_commit_policy(
        identity=_identity("trusted_local_agent"),
        request=_request(domain="professional", sensitivity="internal", contradiction_refs=("memory-old",)),
    )

    assert decision.write_mode == "confirm_inline"
    assert "contradiction_requires_confirmation" in decision.reasons


class TargetedLookupStore:
    """Fake vNext store that fails loudly if the commit path falls back to full-table scans."""

    def __init__(self) -> None:
        self.memories: dict[str, dict[str, object]] = {}
        self.events: list[dict[str, object]] = []
        self.revisions: list[dict[str, object]] = []
        self.agent_identities: dict[str, dict[str, object]] = {}
        self.lookup_calls: list[tuple[str, object]] = []

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def upsert_agent_identity(self, identity: dict[str, object], **_kwargs) -> dict[str, object]:
        self.agent_identities[str(identity["agent_id"])] = identity
        return identity

    def create_memory(self, memory: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**memory, "id": f"memory-{len(self.memories) + 1}"}
        self.memories[str(row["id"])] = row
        return row

    def update_memory(self, *, memory_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        memory = self.memories[memory_id]
        memory.update(patch)
        return memory

    def get_memory(self, memory_id: str) -> dict[str, object] | None:
        return self.memories.get(memory_id)

    def list_memories(self, *, status: str | None = None) -> list[dict[str, object]]:
        raise AssertionError("commit path must use targeted lookups, not full-table scans")

    def get_memory_by_commit_digest(self, commit_digest: str) -> dict[str, object] | None:
        self.lookup_calls.append(("commit_digest", commit_digest))
        for memory in self.memories.values():
            if memory.get("commit_digest") == commit_digest:
                return memory
        return None

    def get_memory_by_confirmation_id(self, confirmation_id: str) -> dict[str, object] | None:
        self.lookup_calls.append(("confirmation_id", confirmation_id))
        for memory in self.memories.values():
            if memory.get("confirmation_id") == confirmation_id:
                return memory
        return None

    def latest_agentic_commit_memory(self, *, agent_id: str | None = None) -> dict[str, object] | None:
        self.lookup_calls.append(("latest_agentic_commit", agent_id))
        for memory in reversed(list(self.memories.values())):
            if memory.get("status") != "active":
                continue
            metadata = memory.get("metadata_json")
            agentic = metadata.get("agentic_memory", {}) if isinstance(metadata, dict) else {}
            if agentic.get("kind") != "agentic_memory_commit":
                continue
            identity = agentic.get("agent_identity")
            if agent_id is None or (isinstance(identity, dict) and identity.get("agent_id") == agent_id):
                return memory
        return None

    def append_revision(self, revision: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**revision, "id": f"revision-{len(self.revisions) + 1}"}
        self.revisions.append(row)
        return row

    def list_revisions(self, memory_id: str) -> list[dict[str, object]]:
        return [revision for revision in self.revisions if revision.get("memory_id") == memory_id]

    def list_events(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        rows = [
            event
            for event in self.events
            if (target_type is None or event.get("target_type") == target_type)
            and (target_id is None or event.get("target_id") == target_id)
        ]
        return rows[:limit] if limit is not None else rows

    def create_provenance_link(self, link: dict[str, object], **_kwargs) -> dict[str, object]:
        return {**link, "id": "provenance-1"}

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[dict[str, object]]:
        return []


def test_commit_idempotent_replay_uses_commit_digest_lookup() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")
    request = _request(
        domain="professional",
        sensitivity="internal",
        idempotency_key="retry-digest-1",
    )

    first = service.commit(identity=identity, request=request)
    second = service.commit(identity=identity, request=request)

    assert first["status"] == "committed"
    assert store.memories[str(first["memory"]["id"])]["commit_digest"] == "retry-digest-1"
    assert second["idempotent_replay"] is True
    assert second["memory"]["id"] == first["memory"]["id"]
    assert ("commit_digest", "retry-digest-1") in store.lookup_calls


def test_confirm_uses_confirmation_id_lookup_and_persisted_column() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")

    pending = service.commit(
        identity=identity,
        request=_request(domain="professional", sensitivity="internal", confidence=0.7),
    )
    confirmation_id = pending["confirmation_id"]
    assert pending["status"] == "confirmation_required"
    assert store.memories[str(pending["memory"]["id"])]["confirmation_id"] == confirmation_id

    confirmed = service.confirm(identity=identity, confirmation_id=confirmation_id)

    assert confirmed["status"] == "committed"
    assert confirmed["memory"]["status"] == "active"
    assert ("confirmation_id", confirmation_id) in store.lookup_calls


def test_memory_status_vocabulary_includes_stale() -> None:
    assert "stale" in MEMORY_STATUSES
    # The base row statuses stay present; "stale" extends, not replaces.
    for status in ("candidate", "active", "rejected", "superseded", "archived", "needs_review"):
        assert status in MEMORY_STATUSES


def test_confirm_refreshes_last_confirmed_at_and_notes_it_in_revision() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")

    pending = service.commit(
        identity=identity,
        request=_request(domain="professional", sensitivity="internal", confidence=0.7),
    )
    memory_id = str(pending["memory"]["id"])
    assert store.memories[memory_id].get("last_confirmed_at") is None

    confirmed = service.confirm(identity=identity, confirmation_id=pending["confirmation_id"])

    assert confirmed["status"] == "committed"
    assert store.memories[memory_id]["last_confirmed_at"] is not None
    confirm_revisions = [
        revision for revision in store.revisions if revision.get("action") == "agentic_memory_confirm_confirm"
    ]
    assert confirm_revisions[-1]["metadata_json"]["last_confirmed_at_refreshed"] is True


def test_repeated_confirm_is_idempotent_and_refreshes_last_confirmed_at() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")

    pending = service.commit(
        identity=identity,
        request=_request(domain="professional", sensitivity="internal", confidence=0.7),
    )
    confirmation_id = pending["confirmation_id"]
    memory_id = str(pending["memory"]["id"])

    first = service.confirm(identity=identity, confirmation_id=confirmation_id)
    first_confirmed_at = store.memories[memory_id]["last_confirmed_at"]
    replay = service.confirm(identity=identity, confirmation_id=confirmation_id)

    assert first["status"] == "committed"
    assert replay["status"] == "committed"
    assert replay["idempotent_replay"] is True
    assert replay["memory"]["id"] == memory_id
    assert len(store.memories) == 1
    assert store.memories[memory_id]["last_confirmed_at"] is not None
    assert store.memories[memory_id]["last_confirmed_at"] >= first_confirmed_at
    reconfirm_revisions = [
        revision for revision in store.revisions if revision.get("action") == "agentic_memory_reconfirm"
    ]
    assert len(reconfirm_revisions) == 1
    assert reconfirm_revisions[0]["metadata_json"]["last_confirmed_at_refreshed"] is True
    assert reconfirm_revisions[0]["revision_type"] == "edited"


def test_confirm_reject_replay_is_idempotent_without_mutation() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")

    pending = service.commit(
        identity=identity,
        request=_request(domain="professional", sensitivity="internal", confidence=0.7),
    )
    confirmation_id = pending["confirmation_id"]

    rejected = service.confirm(identity=identity, confirmation_id=confirmation_id, action="reject")
    revisions_after_reject = len(store.revisions)
    replay = service.confirm(identity=identity, confirmation_id=confirmation_id, action="reject")

    assert rejected["status"] == "rejected"
    assert replay["status"] == "rejected"
    assert replay["idempotent_replay"] is True
    assert len(store.revisions) == revisions_after_reject


def test_correct_refreshes_last_confirmed_at() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")

    committed = service.commit(
        identity=identity,
        request=_request(domain="professional", sensitivity="internal"),
    )
    memory_id = str(committed["memory"]["id"])
    committed_at = store.memories[memory_id]["last_confirmed_at"]

    corrected = service.correct(
        identity=identity,
        memory_id=memory_id,
        canonical_text="Sam prefers tea before noon.",
        reason="User corrected the beverage.",
    )

    assert corrected["status"] == "committed"
    assert store.memories[memory_id]["last_confirmed_at"] is not None
    assert store.memories[memory_id]["last_confirmed_at"] >= committed_at
    correction_revisions = [
        revision for revision in store.revisions if revision.get("action") == "agentic_memory_correct"
    ]
    assert correction_revisions[-1]["metadata_json"]["last_confirmed_at_refreshed"] is True


def test_committed_memory_persists_first_class_scope_columns() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = AgentIdentity(
        agent_id="openclaw",
        agent_type="coding_agent",
        agent_run_id="run-2026-07-04-001",
        permission_profile="project_scoped_agent",
        project_scope=("alicebot",),
    )

    committed = service.commit(
        identity=identity,
        request=_request(domain="project", sensitivity="internal", project_scope=("alicebot",)),
    )

    assert committed["status"] == "committed"
    row = store.memories[str(committed["memory"]["id"])]
    assert row["project_id"] == "alicebot"
    assert row["created_by_agent_id"] == "openclaw"
    assert row["run_id"] == "run-2026-07-04-001"


def test_scope_columns_fall_back_to_identity_project_scope_when_request_has_none() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = AgentIdentity(
        agent_id="openclaw",
        agent_type="coding_agent",
        agent_run_id="run-7",
        permission_profile="project_scoped_agent",
        project_scope=("alicebot",),
    )

    committed = service.commit(
        identity=identity,
        request=_request(domain="project", sensitivity="internal"),
    )

    row = store.memories[str(committed["memory"]["id"])]
    assert row["project_id"] == "alicebot"


def test_multi_project_scope_stays_metadata_only_and_project_id_is_null() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")

    committed = service.commit(
        identity=identity,
        request=_request(
            domain="professional",
            sensitivity="internal",
            project_scope=("alicebot", "hermes"),
        ),
    )

    row = store.memories[str(committed["memory"]["id"])]
    # Ambiguous scope: the hard column never guesses.
    assert row["project_id"] is None
    assert row["metadata_json"]["agentic_memory"]["project_scope"] == ["alicebot", "hermes"]
    assert row["created_by_agent_id"] == identity.agent_id


def test_confirmation_and_review_candidates_also_carry_scope_columns() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = AgentIdentity(
        agent_id="hermes",
        agent_type="personal_assistant",
        agent_run_id="run-9",
        permission_profile="trusted_local_agent",
        project_scope=("alicebot",),
    )

    pending = service.commit(
        identity=identity,
        request=_request(domain="professional", sensitivity="internal", confidence=0.7),
    )
    assert pending["status"] == "confirmation_required"
    pending_row = store.memories[str(pending["memory"]["id"])]
    assert pending_row["project_id"] == "alicebot"
    assert pending_row["created_by_agent_id"] == "hermes"
    assert pending_row["run_id"] == "run-9"

    review = service.commit(
        identity=identity,
        request=_request(
            domain="professional",
            sensitivity="internal",
            source_type="browser_clip",
        ),
    )
    assert review["status"] == "review_required"
    review_row = store.memories[str(review["memory"]["id"])]
    assert review_row["status"] == "candidate"
    assert review_row["project_id"] == "alicebot"
    assert review_row["created_by_agent_id"] == "hermes"
    assert review_row["run_id"] == "run-9"


def test_undo_without_memory_id_uses_latest_agentic_commit_lookup() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")

    committed = service.commit(
        identity=identity,
        request=_request(domain="professional", sensitivity="internal"),
    )
    undone = service.undo(identity=identity)

    assert undone["status"] == "undone"
    assert undone["memory"]["id"] == committed["memory"]["id"]
    assert undone["memory"]["status"] == "superseded"
    assert ("latest_agentic_commit", identity.agent_id) in store.lookup_calls


# -- temporal slice: supersession pointers and the audit chain -----------------


def _commit_active(service: VNextMemoryCommitService, identity: AgentIdentity, *, title: str, text: str) -> str:
    result = service.commit(
        identity=identity,
        request=_request(domain="professional", sensitivity="internal", title=title, canonical_text=text),
    )
    assert result["status"] == "committed"
    return str(result["memory"]["id"])


def test_undo_with_replacement_sets_pointer_columns_on_both_rows() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")
    old_id = _commit_active(service, identity, title="Coffee", text="Sam prefers coffee before noon.")
    new_id = _commit_active(service, identity, title="Tea", text="Sam switched to green tea before noon.")

    undone = service.undo(
        identity=identity,
        memory_id=old_id,
        reason="Replaced by the tea preference.",
        superseded_by_memory_id=new_id,
    )

    old_row = store.memories[old_id]
    new_row = store.memories[new_id]
    assert undone["status"] == "undone"
    assert undone["memory"]["status"] == "superseded"
    # Real pointer columns on both rows...
    assert old_row["superseded_by"] == new_id
    assert new_row["supersedes"] == old_id
    # ...plus the metadata_json copies for backward compatibility.
    assert old_row["metadata_json"]["superseded_by"] == new_id
    assert new_row["metadata_json"]["supersedes"] == old_id
    # The revision and the audit event carry the pointer too.
    superseded_revision = store.revisions[-1]
    assert superseded_revision["revision_type"] == "superseded"
    assert superseded_revision["metadata_json"]["superseded_by"] == new_id
    undone_events = [event for event in store.events if event.get("event_type") == "agent.memory_undone"]
    assert undone_events[-1]["payload_json"]["superseded_by"] == new_id


def test_undo_without_replacement_keeps_pointer_columns_null() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")
    memory_id = _commit_active(service, identity, title="Solo", text="A fact retired without replacement.")

    undone = service.undo(identity=identity, memory_id=memory_id, reason="Wrong fact")

    assert undone["memory"]["status"] == "superseded"
    assert store.memories[memory_id].get("superseded_by") is None
    assert "superseded_by" not in store.memories[memory_id]["metadata_json"]


def test_undo_rejects_missing_or_self_replacement() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")
    memory_id = _commit_active(service, identity, title="Target", text="A fact to undo.")

    with pytest.raises(VNextMemoryCommitValidationError, match="superseding memory was not found"):
        service.undo(identity=identity, memory_id=memory_id, superseded_by_memory_id="memory-missing")
    with pytest.raises(VNextMemoryCommitValidationError, match="cannot supersede itself"):
        service.undo(identity=identity, memory_id=memory_id, superseded_by_memory_id=memory_id)


def test_audit_supersession_chain_walks_both_directions_oldest_first() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    identity = _identity("trusted_local_agent")
    a_id = _commit_active(service, identity, title="v1", text="Version one of the fact.")
    b_id = _commit_active(service, identity, title="v2", text="Version two of the fact.")
    c_id = _commit_active(service, identity, title="v3", text="Version three of the fact.")
    service.undo(identity=identity, memory_id=a_id, superseded_by_memory_id=b_id)
    service.undo(identity=identity, memory_id=b_id, superseded_by_memory_id=c_id)

    audit = service.audit(memory_id=b_id)
    chain = audit["supersession_chain"]

    assert [(entry["id"], entry["relation"]) for entry in chain] == [
        (a_id, "predecessor"),
        (b_id, "self"),
        (c_id, "successor"),
    ]
    assert [entry["title"] for entry in chain] == ["v1", "v2", "v3"]
    assert [entry["status"] for entry in chain] == ["superseded", "superseded", "active"]
    assert set(chain[0]) == {"id", "title", "status", "created_at", "relation"}
    # The same chain is visible from either end.
    assert [entry["id"] for entry in service.audit(memory_id=a_id)["supersession_chain"]] == [a_id, b_id, c_id]
    assert [entry["id"] for entry in service.audit(memory_id=c_id)["supersession_chain"]] == [a_id, b_id, c_id]


def test_audit_supersession_chain_reads_metadata_only_pointers_from_legacy_rows() -> None:
    """Rows written before the pointer columns existed recorded supersession
    in metadata_json only; the chain walker falls back to those keys."""
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    old = store.create_memory(
        {
            "memory_key": "legacy.old",
            "value": {},
            "status": "superseded",
            "title": "Legacy old",
            "metadata_json": {},
        }
    )
    new = store.create_memory(
        {
            "memory_key": "legacy.new",
            "value": {},
            "status": "active",
            "title": "Legacy new",
            "metadata_json": {"supersedes": str(old["id"])},
        }
    )
    old["metadata_json"] = {"superseded_by": str(new["id"])}

    chain = service.audit(memory_id=str(old["id"]))["supersession_chain"]

    assert [(entry["id"], entry["relation"]) for entry in chain] == [
        (str(old["id"]), "self"),
        (str(new["id"]), "successor"),
    ]


def test_audit_supersession_chain_is_cycle_safe_and_depth_bounded() -> None:
    store = TargetedLookupStore()
    service = VNextMemoryCommitService(store)
    ids: list[str] = []
    for index in range(15):
        row = store.create_memory(
            {"memory_key": f"chain.{index}", "value": {}, "status": "superseded", "title": f"v{index}"}
        )
        ids.append(str(row["id"]))
    for index in range(14):
        store.memories[ids[index]]["superseded_by"] = ids[index + 1]
        store.memories[ids[index + 1]]["supersedes"] = ids[index]

    # Depth is bounded to 10 hops per direction.
    from_start = service.audit(memory_id=ids[0])["supersession_chain"]
    assert len(from_start) == 11  # self + 10 successors
    assert from_start[0]["id"] == ids[0]

    # A pointer cycle terminates instead of looping.
    store.memories[ids[14]]["superseded_by"] = ids[0]
    cyclic = service.audit(memory_id=ids[12])["supersession_chain"]
    ids_in_chain = [entry["id"] for entry in cyclic]
    assert len(ids_in_chain) == len(set(ids_in_chain))
    assert [entry["relation"] for entry in cyclic].count("self") == 1

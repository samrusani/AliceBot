"""Current committed facts outrank historical ones on default reads.

Present-tense ``alice_recall`` and the session brief used to treat two
committed addresses as equal FTS / created_at hits. They now call the
same ``_prefer_current_versions`` helper the context pack already ran.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from alicebot_api.mcp_tools import AGENT_API_KEY_ENV, MCPRuntimeContext
from alicebot_api.onramp import bootstrap_database, resolve_db_path, sqlite_url_for_path
from alicebot_api.session_briefing import compile_session_brief
from alicebot_api.sqlite_store import SQLiteVNextStore, sqlite_user_connection
from alicebot_api.vnext_embeddings import (
    EMBEDDINGS_API_KEY_ENV,
    EMBEDDINGS_BASE_URL_ENV,
    EMBEDDINGS_MODEL_ENV,
)

USER_ID = "00000000-0000-0000-0000-000000000001"
PRESENT_TENSE_QUERY = "where do I live?"
OLD_ADDRESS = "I live at 11 Old Street."
CURRENT_ADDRESS = "I live at 22 Current Street."
RESTRICTED_ADDRESS = "I live at 99 Secret Street."
CANDIDATE_NOTE = "Decision: I live at 77 Candidate Street.\n"
OLD_VALID_FROM = "2025-03-01T00:00:00Z"
CURRENT_VALID_FROM = "2026-03-01T00:00:00Z"

UNSCOPED_FENCES = {
    "effective_domains": (),
    "effective_sensitivity_allowed": ("public", "internal", "private", "unknown"),
    "effective_project_scope": (),
}


def _clear_env(monkeypatch) -> None:
    for env_name in (
        EMBEDDINGS_BASE_URL_ENV,
        EMBEDDINGS_MODEL_ENV,
        EMBEDDINGS_API_KEY_ENV,
        AGENT_API_KEY_ENV,
    ):
        monkeypatch.delenv(env_name, raising=False)


def _context(tmp_path: Path, monkeypatch) -> MCPRuntimeContext:
    _clear_env(monkeypatch)
    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    bootstrap_database(database, user_id=USER_ID, user_email="local@alice")
    return MCPRuntimeContext(database_url=sqlite_url_for_path(database), user_id=USER_ID)


def _create_fact(
    store: SQLiteVNextStore,
    *,
    memory_key: str,
    text: str,
    valid_from: str,
    sensitivity: str = "public",
    domain: str = "project",
    project: str = "acme",
    supersedes: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "memory_key": memory_key,
        "memory_type": "semantic",
        "title": "Home address",
        "canonical_text": text,
        "status": "active",
        "domain": domain,
        "sensitivity": sensitivity,
        "valid_from": valid_from,
        "project_scope": [project],
        "metadata_json": {"project_scope": [project]},
        "value": {"text": text},
    }
    if supersedes is not None:
        payload["supersedes"] = supersedes
    return store.create_memory(payload)


def _seed_address_pair(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    """Current row first, historical row second, ancestor updated last.

    Brief lists by created_at DESC and FTS ties break on updated_at DESC.
    Writing the ancestor last makes that row the top hit unless
    ``_prefer_current_versions`` moves the replacement above it.
    """

    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    with sqlite_user_connection(database, USER_ID) as connection:
        store = SQLiteVNextStore(connection, USER_ID)
        current = _create_fact(
            store,
            memory_key="fact.address.current",
            text=CURRENT_ADDRESS,
            valid_from=CURRENT_VALID_FROM,
        )
        historical = _create_fact(
            store,
            memory_key="fact.address.historical",
            text=OLD_ADDRESS,
            valid_from=OLD_VALID_FROM,
        )
        store.update_memory(
            memory_id=str(current["id"]),
            patch={"supersedes": str(historical["id"])},
            actor_type="system",
        )
        store.update_memory(
            memory_id=str(historical["id"]),
            patch={"superseded_by": str(current["id"])},
            actor_type="system",
        )
        return current, historical


def _seed_restricted_address(tmp_path: Path) -> dict[str, object]:
    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    with sqlite_user_connection(database, USER_ID) as connection:
        store = SQLiteVNextStore(connection, USER_ID)
        return _create_fact(
            store,
            memory_key="fact.address.secret",
            text=RESTRICTED_ADDRESS,
            valid_from=CURRENT_VALID_FROM,
            sensitivity="private",
            domain="personal",
            project="other",
        )


def _recall(context: MCPRuntimeContext, **arguments) -> dict:
    from alicebot_api.mcp.registry import call_mcp_tool

    return call_mcp_tool(
        context,
        name="alice_recall",
        arguments={"query": PRESENT_TENSE_QUERY, **arguments},
    )


def _compile(tmp_path: Path, **kwargs) -> str:
    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    fences = dict(UNSCOPED_FENCES)
    fences.update(kwargs)
    with sqlite_user_connection(database, USER_ID) as connection:
        store = SQLiteVNextStore(connection, USER_ID)
        return compile_session_brief(store, **fences)


def _result_texts(payload: dict) -> list[str]:
    return [str(row.get("text") or "") for row in payload.get("results") or []]


def _fact_lines(brief: str) -> list[str]:
    return [line for line in brief.splitlines() if line.startswith("**fact**:")]


def test_present_tense_recall_leads_with_the_current_address(tmp_path: Path, monkeypatch) -> None:
    """Present-tense alice_recall must not lead with last year's street.

    Fails if ``_handle_alice_recall`` skips ``_prefer_current_versions``
    after ``_order_memories_for_strategy``.
    """

    context = _context(tmp_path, monkeypatch)
    _seed_address_pair(tmp_path)

    texts = _result_texts(_recall(context))

    assert texts, "recall returned no address facts"
    assert CURRENT_ADDRESS in texts[0]
    assert OLD_ADDRESS not in texts[0]
    assert any(OLD_ADDRESS in text for text in texts), (
        "historical address was dropped; demote-not-drop no longer holds"
    )


def test_recall_leads_with_the_old_address_when_prefer_current_versions_is_skipped(
    tmp_path: Path, monkeypatch
) -> None:
    """Mutation: skip ``_prefer_current_versions`` on the recall path.

    The edit that makes
    ``test_present_tense_recall_leads_with_the_current_address`` fail is
    deleting the ``_prefer_current_versions`` call after
    ``_order_memories_for_strategy`` in ``mcp/retrieval.py``. This test
    applies that skip with a monkeypatch so the fixture stays honest:
    without the helper, fused/updated_at order still puts 11 Old Street
    first.
    """

    import alicebot_api.mcp.retrieval as retrieval_module

    def skip_prefer_current_versions(memories):
        return list(memories), 0

    monkeypatch.setattr(
        retrieval_module,
        "_prefer_current_versions",
        skip_prefer_current_versions,
    )

    context = _context(tmp_path, monkeypatch)
    _seed_address_pair(tmp_path)

    texts = _result_texts(_recall(context))

    assert texts, "recall returned no address facts"
    assert OLD_ADDRESS in texts[0]
    assert CURRENT_ADDRESS not in texts[0]


def test_session_brief_lists_the_current_address_before_the_historical_one(
    tmp_path: Path, monkeypatch
) -> None:
    """query=None brief must not lead with last year's street when both appear.

    Fails if ``compile_session_brief`` skips ``_prefer_current_versions``
    after ``list_memories`` / recent-change merge.
    """

    _context(tmp_path, monkeypatch)
    _seed_address_pair(tmp_path)

    brief = _compile(tmp_path, query=None)
    facts = _fact_lines(brief)

    assert any(CURRENT_ADDRESS in line for line in facts), brief
    assert any(OLD_ADDRESS in line for line in facts), brief
    current_index = next(index for index, line in enumerate(facts) if CURRENT_ADDRESS in line)
    historical_index = next(index for index, line in enumerate(facts) if OLD_ADDRESS in line)
    assert current_index < historical_index, brief


def test_validity_ranking_does_not_bypass_the_policy_fence(tmp_path: Path, monkeypatch) -> None:
    """The new ranking path still applies the three effective fences by hand.

    Fails if recall or the brief ranks first and then reads without
    ``effective_domains``, ``effective_sensitivity_allowed``, or
    ``effective_project_scope``. The unscoped compile/recall below is the
    vacuous-test guard: if it stops seeing the secret street, the scoped
    asserts prove nothing.
    """

    context = _context(tmp_path, monkeypatch)
    _seed_address_pair(tmp_path)
    _seed_restricted_address(tmp_path)

    parameters = inspect.signature(compile_session_brief).parameters
    for name in (
        "effective_domains",
        "effective_sensitivity_allowed",
        "effective_project_scope",
    ):
        assert parameters[name].default is inspect.Parameter.empty
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY

    unscoped_recall = _result_texts(_recall(context))
    assert any(RESTRICTED_ADDRESS in text for text in unscoped_recall), (
        "unscoped recall lost the secret street; scoped asserts are vacuous"
    )
    assert CURRENT_ADDRESS in unscoped_recall[0]

    unscoped_brief = _compile(tmp_path, query=None)
    assert RESTRICTED_ADDRESS in unscoped_brief, (
        "unscoped brief lost the secret street; scoped asserts are vacuous"
    )

    project_locked = _result_texts(_recall(context, projects=["acme"]))
    assert not any(RESTRICTED_ADDRESS in text for text in project_locked)
    assert project_locked and CURRENT_ADDRESS in project_locked[0]

    public_only = _result_texts(_recall(context, sensitivity_allowed=["public"]))
    assert not any(RESTRICTED_ADDRESS in text for text in public_only)
    assert public_only and CURRENT_ADDRESS in public_only[0]

    domain_locked = _result_texts(_recall(context, domains=["project"]))
    assert not any(RESTRICTED_ADDRESS in text for text in domain_locked)
    assert domain_locked and CURRENT_ADDRESS in domain_locked[0]

    project_brief = _compile(tmp_path, query=None, effective_project_scope=("acme",))
    assert RESTRICTED_ADDRESS not in project_brief
    assert CURRENT_ADDRESS in project_brief

    public_brief = _compile(tmp_path, query=None, effective_sensitivity_allowed=("public",))
    assert RESTRICTED_ADDRESS not in public_brief
    assert CURRENT_ADDRESS in public_brief

    domain_brief = _compile(tmp_path, query=None, effective_domains=("project",))
    assert RESTRICTED_ADDRESS not in domain_brief
    assert CURRENT_ADDRESS in domain_brief


def test_a_capture_candidate_stays_unsearchable_as_a_memory(tmp_path: Path, monkeypatch) -> None:
    """Import stays a source. Commit stays a fact. No auto-promote.

    Fails if ranking, recall, or the brief promotes a capture candidate
    so it appears as a memory / **fact**.
    """

    from alicebot_api.mcp.registry import call_mcp_tool

    context = _context(tmp_path, monkeypatch)
    _seed_address_pair(tmp_path)
    captured = call_mcp_tool(
        context,
        name="alice_capture",
        arguments={
            "raw_text": CANDIDATE_NOTE,
            "title": "Candidate address",
            "domain": "personal",
            "sensitivity": "private",
        },
    )
    assert captured["status"] == "imported", captured

    recall = _recall(context)
    assert not any("77 Candidate Street" in text for text in _result_texts(recall))
    assert CURRENT_ADDRESS in _result_texts(recall)[0]

    brief = _compile(tmp_path, query=PRESENT_TENSE_QUERY)
    assert not any("77 Candidate Street" in line for line in _fact_lines(brief))

    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    with sqlite_user_connection(database, USER_ID) as connection:
        store = SQLiteVNextStore(connection, USER_ID)
        candidates = store.list_memories(status="candidate")
        committed = store.list_memories(status=None, statuses=("active", "accepted"))
    assert any(
        "77 Candidate Street" in str(row.get("canonical_text") or "") for row in candidates
    ), "capture created no address candidate; the no-promote assert is vacuous"
    assert not any("77 Candidate Street" in str(row.get("canonical_text") or "") for row in committed)

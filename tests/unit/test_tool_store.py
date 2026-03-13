from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from alicebot_api.store import ContinuityStore


class RecordingCursor:
    def __init__(self, fetchone_results: list[dict[str, Any]], fetchall_result: list[dict[str, Any]] | None = None) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results)
        self.fetchall_result = fetchall_result or []

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, Any]]:
        return self.fetchall_result


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def test_tool_store_methods_use_expected_queries_and_jsonb_parameters() -> None:
    tool_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": tool_id,
                "tool_key": "browser.open",
                "name": "Browser Open",
                "description": "Open documentation pages.",
                "version": "1.0.0",
                "metadata_version": "tool_metadata_v0",
                "active": True,
                "tags": ["browser"],
                "action_hints": ["tool.run"],
                "scope_hints": ["workspace"],
                "domain_hints": ["docs"],
                "risk_hints": [],
                "metadata": {"transport": "proxy"},
            },
            {
                "id": tool_id,
                "tool_key": "browser.open",
                "name": "Browser Open",
                "description": "Open documentation pages.",
                "version": "1.0.0",
                "metadata_version": "tool_metadata_v0",
                "active": True,
                "tags": ["browser"],
                "action_hints": ["tool.run"],
                "scope_hints": ["workspace"],
                "domain_hints": ["docs"],
                "risk_hints": [],
                "metadata": {"transport": "proxy"},
            },
        ],
        fetchall_result=[
            {
                "id": tool_id,
                "tool_key": "browser.open",
                "name": "Browser Open",
                "description": "Open documentation pages.",
                "version": "1.0.0",
                "metadata_version": "tool_metadata_v0",
                "active": True,
                "tags": ["browser"],
                "action_hints": ["tool.run"],
                "scope_hints": ["workspace"],
                "domain_hints": ["docs"],
                "risk_hints": [],
                "metadata": {"transport": "proxy"},
            }
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_tool(
        tool_key="browser.open",
        name="Browser Open",
        description="Open documentation pages.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["browser"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=["docs"],
        risk_hints=[],
        metadata={"transport": "proxy"},
    )
    fetched = store.get_tool_optional(tool_id)
    listed = store.list_active_tools()

    assert created["id"] == tool_id
    assert fetched is not None
    assert listed[0]["id"] == tool_id

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO tools" in create_query
    assert create_params is not None
    assert create_params[:6] == (
        "browser.open",
        "Browser Open",
        "Open documentation pages.",
        "1.0.0",
        "tool_metadata_v0",
        True,
    )
    for index, expected in (
        (6, ["browser"]),
        (7, ["tool.run"]),
        (8, ["workspace"]),
        (9, ["docs"]),
        (10, []),
    ):
        assert isinstance(create_params[index], Jsonb)
        assert create_params[index].obj == expected
    assert isinstance(create_params[11], Jsonb)
    assert create_params[11].obj == {"transport": "proxy"}

    assert cursor.executed[1] == (
        """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                WHERE id = %s
                """,
        (tool_id,),
    )
    assert "WHERE active = TRUE" in cursor.executed[2][0]

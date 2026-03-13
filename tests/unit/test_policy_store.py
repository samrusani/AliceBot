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


def test_consent_store_methods_use_expected_queries_and_jsonb_parameters() -> None:
    consent_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": consent_id, "consent_key": "email_marketing", "status": "granted", "metadata": {}},
            {"id": consent_id, "consent_key": "email_marketing", "status": "revoked", "metadata": {"source": "banner"}},
        ],
        fetchall_result=[{"id": consent_id, "consent_key": "email_marketing", "status": "revoked", "metadata": {}}],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_consent(
        consent_key="email_marketing",
        status="granted",
        metadata={"source": "settings"},
    )
    updated = store.update_consent(
        consent_id=consent_id,
        status="revoked",
        metadata={"source": "banner"},
    )
    listed = store.list_consents()

    assert created["id"] == consent_id
    assert updated["status"] == "revoked"
    assert listed == [{"id": consent_id, "consent_key": "email_marketing", "status": "revoked", "metadata": {}}]

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO consents" in create_query
    assert create_params is not None
    assert create_params[:2] == ("email_marketing", "granted")
    assert isinstance(create_params[2], Jsonb)
    assert create_params[2].obj == {"source": "settings"}

    update_query, update_params = cursor.executed[1]
    assert "UPDATE consents" in update_query
    assert update_params is not None
    assert update_params[0] == "revoked"
    assert isinstance(update_params[1], Jsonb)
    assert update_params[1].obj == {"source": "banner"}
    assert update_params[2] == consent_id

    assert cursor.executed[2] == (
        """
                SELECT id, user_id, consent_key, status, metadata, created_at, updated_at
                FROM consents
                ORDER BY consent_key ASC, created_at ASC, id ASC
                """,
        None,
    )


def test_policy_store_methods_use_expected_queries_and_jsonb_parameters() -> None:
    policy_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": policy_id,
                "name": "Allow export",
                "action": "memory.export",
                "scope": "profile",
                "effect": "allow",
                "priority": 10,
                "active": True,
                "conditions": {"channel": "email"},
                "required_consents": ["email_marketing"],
            },
            {
                "id": policy_id,
                "name": "Allow export",
                "action": "memory.export",
                "scope": "profile",
                "effect": "allow",
                "priority": 10,
                "active": True,
                "conditions": {"channel": "email"},
                "required_consents": ["email_marketing"],
            },
        ],
        fetchall_result=[
            {
                "id": policy_id,
                "name": "Allow export",
                "action": "memory.export",
                "scope": "profile",
                "effect": "allow",
                "priority": 10,
                "active": True,
                "conditions": {"channel": "email"},
                "required_consents": ["email_marketing"],
            }
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_policy(
        name="Allow export",
        action="memory.export",
        scope="profile",
        effect="allow",
        priority=10,
        active=True,
        conditions={"channel": "email"},
        required_consents=["email_marketing"],
    )
    fetched = store.get_policy_optional(policy_id)
    listed = store.list_active_policies()

    assert created["id"] == policy_id
    assert fetched is not None
    assert listed[0]["id"] == policy_id

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO policies" in create_query
    assert create_params is not None
    assert create_params[:6] == ("Allow export", "memory.export", "profile", "allow", 10, True)
    assert isinstance(create_params[6], Jsonb)
    assert create_params[6].obj == {"channel": "email"}
    assert isinstance(create_params[7], Jsonb)
    assert create_params[7].obj == ["email_marketing"]

    assert cursor.executed[1] == (
        """
                SELECT
                  id,
                  user_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                WHERE id = %s
                """,
        (policy_id,),
    )
    assert "WHERE active = TRUE" in cursor.executed[2][0]

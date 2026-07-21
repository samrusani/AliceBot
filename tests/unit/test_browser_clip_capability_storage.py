from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from hashlib import sha256
import sqlite3
from threading import Barrier
from uuid import uuid4

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user, sqlite_user_connection


ORIGIN = "https://docs.example.test"


def _digest(raw_capability: str) -> str:
    return sha256(raw_capability.encode("utf-8")).hexdigest()


def _parse_sqlite_timestamp(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _make_store(conn: sqlite3.Connection, user_id: str) -> SQLiteVNextStore:
    ensure_sqlite_user(conn, user_id, f"{user_id}@example.test", "Clip User")
    return SQLiteVNextStore(conn, user_id)


def test_sqlite_capability_is_hash_only_tenant_bound_origin_bound_and_one_time() -> None:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    owner_id = str(uuid4())
    other_id = str(uuid4())
    owner = _make_store(conn, owner_id)
    other = _make_store(conn, other_id)
    raw_capability = "alice_clip_this-raw-value-must-never-be-persisted"
    capability_hash = _digest(raw_capability)

    issued = owner.create_browser_clip_capability(
        capability_hash=capability_hash,
        origin=ORIGIN,
        ttl_seconds=120,
    )

    assert set(issued) == {"id", "user_id", "origin", "expires_at", "consumed_at", "created_at"}
    assert issued["user_id"] == owner_id
    assert issued["origin"] == ORIGIN
    assert issued["consumed_at"] is None
    ttl = _parse_sqlite_timestamp(issued["expires_at"]) - _parse_sqlite_timestamp(issued["created_at"])
    assert 119.9 <= ttl.total_seconds() <= 120.1

    persisted = conn.execute(
        "SELECT * FROM browser_clip_capabilities WHERE id = ?",
        (issued["id"],),
    ).fetchone()
    assert persisted is not None
    assert capability_hash in persisted
    assert raw_capability not in repr(persisted)

    assert (
        other.consume_browser_clip_capability(
            capability_hash=capability_hash,
            origin=ORIGIN,
        )
        is None
    )
    assert (
        owner.consume_browser_clip_capability(
            capability_hash=capability_hash,
            origin="https://other.example.test",
        )
        is None
    )

    redeemed = owner.consume_browser_clip_capability(
        capability_hash=capability_hash,
        origin=ORIGIN,
    )
    assert redeemed is not None
    assert redeemed["consumed_at"] is not None
    assert (
        owner.consume_browser_clip_capability(
            capability_hash=capability_hash,
            origin=ORIGIN,
        )
        is None
    )


def test_sqlite_capability_rejects_expired_rows_and_out_of_range_ttls() -> None:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    owner = _make_store(conn, str(uuid4()))
    capability_hash = _digest("alice_clip_expired")
    issued = owner.create_browser_clip_capability(
        capability_hash=capability_hash,
        origin=ORIGIN,
        ttl_seconds=120,
    )
    conn.execute(
        """
        UPDATE browser_clip_capabilities
        SET created_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-2 minutes'),
            expires_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-1 minute')
        WHERE id = ?
        """,
        (issued["id"],),
    )

    assert (
        owner.consume_browser_clip_capability(
            capability_hash=capability_hash,
            origin=ORIGIN,
        )
        is None
    )
    max_ttl = owner.create_browser_clip_capability(
        capability_hash=_digest("alice_clip_max_ttl"),
        origin=ORIGIN,
        ttl_seconds=300,
    )
    max_ttl_delta = _parse_sqlite_timestamp(max_ttl["expires_at"]) - _parse_sqlite_timestamp(
        max_ttl["created_at"]
    )
    assert 299.9 <= max_ttl_delta.total_seconds() <= 300.1
    for ttl_seconds in (0, 301):
        with pytest.raises(ValueError, match="TTL must be between 1 and 300 seconds"):
            owner.create_browser_clip_capability(
                capability_hash=_digest(f"alice_clip_bad_ttl_{ttl_seconds}"),
                origin=ORIGIN,
                ttl_seconds=ttl_seconds,
            )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO browser_clip_capabilities (
              id, user_id, capability_hash, origin, expires_at, created_at
            )
            VALUES (?, ?, ?, ?, 'not-a-timestamp', 'not-a-timestamp')
            """,
            (str(uuid4()), owner.user_id, _digest("alice_clip_invalid_time"), ORIGIN),
        )


def test_sqlite_concurrent_double_redemption_commits_exactly_one_source(tmp_path) -> None:
    database_path = tmp_path / "browser-clip.db"
    owner_id = str(uuid4())
    raw_capability = "alice_clip_concurrent-redemption"
    capability_hash = _digest(raw_capability)
    with sqlite_user_connection(database_path, owner_id) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        store = _make_store(conn, owner_id)
        store.create_browser_clip_capability(
            capability_hash=capability_hash,
            origin=ORIGIN,
            ttl_seconds=120,
        )

    start = Barrier(2)

    def redeem(attempt: int) -> bool:
        conn = sqlite3.connect(str(database_path), timeout=10)
        conn.execute("PRAGMA busy_timeout = 10000")
        try:
            store = SQLiteVNextStore(conn, owner_id)
            start.wait(timeout=5)
            redeemed = store.consume_browser_clip_capability(
                capability_hash=capability_hash,
                origin=ORIGIN,
            )
            if redeemed is None:
                conn.commit()
                return False
            store.create_source(
                {
                    "source_type": "browser_clip",
                    "title": f"Concurrent clip {attempt}",
                    "uri": f"{ORIGIN}/guide",
                    "content_hash": "sha256:browser-clip-concurrent-redemption",
                    "connector_name": "browser_clipper",
                    "domain": "professional",
                    "sensitivity": "private",
                    "metadata_json": {"transport": "one_time_capability"},
                },
                actor_type="user",
            )
            conn.commit()
            return True
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(redeem, (1, 2)))

    assert sorted(results) == [False, True]
    with sqlite_user_connection(database_path, owner_id) as conn:
        assert (
            conn.execute(
                """
                SELECT count(*)
                FROM sources
                WHERE user_id = ?
                  AND connector_name = 'browser_clipper'
                """,
                (owner_id,),
            ).fetchone()["count(*)"]
            == 1
        )

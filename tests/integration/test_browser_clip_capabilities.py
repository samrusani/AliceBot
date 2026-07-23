from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Barrier
from uuid import UUID, uuid4

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_store import PostgresVNextStore


ORIGIN = "https://docs.example.test"


def _seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, "Browser Clip User")
    return user_id


def test_postgres_capability_is_hash_only_rls_bound_expiring_and_atomically_one_time(
    migrated_database_urls,
) -> None:
    database_url = migrated_database_urls["app"]
    owner_id = _seed_user(database_url, email=f"clip-owner-{uuid4().hex}@example.test")
    other_id = _seed_user(database_url, email=f"clip-other-{uuid4().hex}@example.test")
    raw_capability = "alice_clip_concurrent-postgres-redemption"
    capability_hash = sha256(raw_capability.encode("utf-8")).hexdigest()

    with user_connection(database_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        issued = store.create_browser_clip_capability(
            capability_hash=capability_hash,
            origin=ORIGIN,
            ttl_seconds=120,
        )
        assert set(issued) == {"id", "user_id", "origin", "expires_at", "consumed_at", "created_at"}
        assert issued["user_id"] == owner_id
        assert issued["origin"] == ORIGIN
        assert issued["consumed_at"] is None
        assert 119.9 <= (issued["expires_at"] - issued["created_at"]).total_seconds() <= 120.1
        with conn.cursor() as cur:
            cur.execute(
                "SELECT capability_hash FROM browser_clip_capabilities WHERE id = %s::uuid",
                (issued["id"],),
            )
            persisted = cur.fetchone()
        assert persisted == {"capability_hash": capability_hash}
        assert raw_capability not in repr(persisted)

        expired_hash = sha256(b"alice_clip_expired-postgres").hexdigest()
        expired = store.create_browser_clip_capability(
            capability_hash=expired_hash,
            origin=ORIGIN,
            ttl_seconds=120,
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE browser_clip_capabilities
                SET created_at = clock_timestamp() - interval '2 minutes',
                    expires_at = clock_timestamp() - interval '1 minute'
                WHERE id = %s::uuid
                """,
                (expired["id"],),
            )
        assert (
            store.consume_browser_clip_capability(
                capability_hash=expired_hash,
                origin=ORIGIN,
            )
            is None
        )

    with user_connection(database_url, other_id) as conn:
        other_store = PostgresVNextStore(conn)
        assert (
            other_store.consume_browser_clip_capability(
                capability_hash=capability_hash,
                origin=ORIGIN,
            )
            is None
        )
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS capability_count FROM browser_clip_capabilities")
            assert cur.fetchone() == {"capability_count": 0}

    with user_connection(database_url, owner_id) as conn:
        assert (
            PostgresVNextStore(conn).consume_browser_clip_capability(
                capability_hash=capability_hash,
                origin="https://other.example.test",
            )
            is None
        )

    start = Barrier(2)

    def redeem(attempt: int) -> bool:
        with user_connection(database_url, owner_id) as conn:
            store = PostgresVNextStore(conn)
            start.wait(timeout=10)
            redeemed = store.consume_browser_clip_capability(
                capability_hash=capability_hash,
                origin=ORIGIN,
            )
            if redeemed is None:
                return False
            store.create_source(
                {
                    "source_type": "browser_clip",
                    "title": f"Concurrent clip {attempt}",
                    "uri": f"{ORIGIN}/guide",
                    "content_hash": "sha256:browser-clip-concurrent-postgres-redemption",
                    "connector_name": "browser_clipper",
                    "domain": "professional",
                    "sensitivity": "private",
                    "metadata_json": {"transport": "one_time_capability"},
                },
                actor_type="user",
            )
            return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(redeem, (1, 2)))

    assert sorted(results) == [False, True]
    with user_connection(database_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        assert (
            store.consume_browser_clip_capability(
                capability_hash=capability_hash,
                origin=ORIGIN,
            )
            is None
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) AS source_count
                FROM sources
                WHERE connector_name = 'browser_clipper'
                  AND content_hash = 'sha256:browser-clip-concurrent-postgres-redemption'
                """
            )
            assert cur.fetchone() == {"source_count": 1}

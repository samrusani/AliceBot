"""Lifecycle expire/unexpire row-locking against a real migrated Postgres.

Audit P1 #2: ``expire()``/``unexpire()`` must acquire the row's write lock
(``SELECT ... FOR UPDATE``) BEFORE policy evaluation and metadata derivation,
so a concurrent correction/supersession cannot slip between the read and the
write and be silently overwritten by a stale snapshot. Only a live Postgres
run exercises ``FOR UPDATE``; the SQLite mirror serializes on a single writer.

The reproduction is deterministic: a pause is injected right after the row
load (at ``_policy_checked_write``, before metadata derivation), then a second
connection attempts a concurrent correction with a short ``lock_timeout``. When
expire/unexpire hold the row lock, that concurrent correction is forced to wait
and fails fast instead of racing ahead; without the lock it slips through.
"""

from __future__ import annotations

import threading
from uuid import uuid4

from psycopg import errors as pg_errors

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_memory_commit import VNextMemoryCommitService
from alicebot_api.vnext_store import PostgresVNextStore
import alicebot_api.vnext_memory_commit as vnext_memory_commit_module


def _clear_provider_env(monkeypatch) -> None:
    for name in (
        "ALICE_EMBEDDINGS_BASE_URL",
        "ALICE_EMBEDDINGS_MODEL",
        "ALICE_EMBEDDINGS_API_KEY",
        "ALICE_FACT_KEYS_BASE_URL",
        "ALICE_FACT_KEYS_MODEL",
        "ALICE_FACT_KEYS_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def _seed_active_memory(app_url: str, user_id) -> str:
    with user_connection(app_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, "lifecycle-race@example.invalid", "Race")
        store = PostgresVNextStore(conn)
        row = store.create_memory(
            {
                "memory_key": f"memory.{uuid4()}",
                "value": {"text": "Weekly planning cadence on Mondays."},
                "status": "active",
                "memory_type": "semantic",
                "title": "Planning cadence",
                "canonical_text": "Weekly planning cadence on Mondays.",
                "summary": "Weekly planning cadence.",
                "domain": "professional",
                "sensitivity": "internal",
                "confirmation_status": "confirmed",
            }
        )
        return str(row["id"])


def _run_locking_race(
    app_url: str,
    user_id,
    monkeypatch,
    *,
    lifecycle_call,
) -> dict[str, object]:
    """Pause a lifecycle op after its row load; race a correction against it.

    Returns whether the concurrent correction managed to apply. When the
    lifecycle op holds the row lock (the fix) the correction is blocked and
    fails with a lock timeout, so ``correction_applied`` is False.
    """
    loaded = threading.Event()
    release = threading.Event()
    paused_once = threading.Event()

    original_policy_checked_write = VNextMemoryCommitService._policy_checked_write

    def paused_policy_checked_write(self, **kwargs):
        # Runs after the row has been loaded (and locked, once fixed) and
        # before metadata is derived and written -- exactly the window the
        # audit says a concurrent write must not be able to exploit. Only the
        # first (lifecycle worker's) call pauses; the racing correction's own
        # policy check must not block, so the race stays deterministic.
        decision = original_policy_checked_write(self, **kwargs)
        if not paused_once.is_set():
            paused_once.set()
            loaded.set()
            release.wait(timeout=10)
        return decision

    monkeypatch.setattr(
        vnext_memory_commit_module.VNextMemoryCommitService,
        "_policy_checked_write",
        paused_policy_checked_write,
    )

    lifecycle_result: dict[str, object] = {}

    def run_lifecycle() -> None:
        try:
            with user_connection(app_url, user_id) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET LOCAL lock_timeout = '5s'")
                store = PostgresVNextStore(conn)
                lifecycle_result["result"] = lifecycle_call(VNextMemoryCommitService(store))
        except Exception as exc:  # noqa: BLE001 - surfaced to the assertion below
            lifecycle_result["error"] = exc

    worker = threading.Thread(target=run_lifecycle, name="lifecycle-op")
    worker.start()
    try:
        assert loaded.wait(timeout=10), "lifecycle op never reached its policy check"

        correction_applied = False
        correction_error: Exception | None = None
        with user_connection(app_url, user_id) as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL lock_timeout = '750ms'")
            store = PostgresVNextStore(conn)
            memory_id = lifecycle_call.memory_id  # type: ignore[attr-defined]
            try:
                VNextMemoryCommitService(store).correct(
                    identity=None,
                    memory_id=memory_id,
                    canonical_text="Concurrent correction wins the row.",
                    reason="Racing correction.",
                )
                correction_applied = True
            except pg_errors.LockNotAvailable as exc:
                correction_error = exc
    finally:
        release.set()
        worker.join(timeout=15)

    return {
        "correction_applied": correction_applied,
        "correction_error": correction_error,
        "lifecycle_result": lifecycle_result,
    }


class _ExpireCall:
    def __init__(self, memory_id: str) -> None:
        self.memory_id = memory_id

    def __call__(self, service: VNextMemoryCommitService):
        return service.expire(self.memory_id, reason="Concurrent expire.", identity=None)


class _UnexpireCall:
    def __init__(self, memory_id: str) -> None:
        self.memory_id = memory_id

    def __call__(self, service: VNextMemoryCommitService):
        return service.unexpire(self.memory_id, reason="Concurrent unexpire.", identity=None)


def test_expire_locks_the_row_against_a_concurrent_correction(migrated_database_urls, monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    app_url = migrated_database_urls["app"]
    user_id = uuid4()
    memory_id = _seed_active_memory(app_url, user_id)

    outcome = _run_locking_race(app_url, user_id, monkeypatch, lifecycle_call=_ExpireCall(memory_id))

    # The expiring worker holds the row lock, so the concurrent correction is
    # forced to wait and fails fast instead of overwriting the row underneath.
    assert outcome["correction_applied"] is False
    assert isinstance(outcome["correction_error"], pg_errors.LockNotAvailable)
    assert "error" not in outcome["lifecycle_result"], outcome["lifecycle_result"].get("error")
    assert outcome["lifecycle_result"]["result"]["status"] == "expired"

    # The row is intact and a correction now applies cleanly once the lock is free.
    with user_connection(app_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        assert store.get_memory(memory_id)["valid_to"] is not None
        corrected = VNextMemoryCommitService(store).correct(
            identity=None,
            memory_id=memory_id,
            canonical_text="Serialized correction after expiry.",
            reason="Retry after the lock cleared.",
        )
    assert corrected["memory"]["canonical_text"] == "Serialized correction after expiry."


def test_unexpire_locks_the_row_against_a_concurrent_correction(migrated_database_urls, monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    app_url = migrated_database_urls["app"]
    user_id = uuid4()
    memory_id = _seed_active_memory(app_url, user_id)

    # Put the row into a real expired state first (valid_to in the past).
    with user_connection(app_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        VNextMemoryCommitService(store).expire(
            memory_id, valid_to="2020-01-01T00:00:00Z", reason="Expired earlier.", identity=None
        )

    outcome = _run_locking_race(app_url, user_id, monkeypatch, lifecycle_call=_UnexpireCall(memory_id))

    assert outcome["correction_applied"] is False
    assert isinstance(outcome["correction_error"], pg_errors.LockNotAvailable)
    assert "error" not in outcome["lifecycle_result"], outcome["lifecycle_result"].get("error")
    assert outcome["lifecycle_result"]["result"]["status"] == "active"

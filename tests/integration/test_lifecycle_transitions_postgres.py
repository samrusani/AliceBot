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
from uuid import UUID, uuid4

from psycopg import errors as pg_errors
import pytest

from alicebot_api.config import Settings
from alicebot_api.db import user_connection
from alicebot_api.routers import vnext_memories as vnext_memories_router
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_memory_commit import (
    VNextMemoryCommitService,
    VNextMemoryCommitValidationError,
)
from alicebot_api.vnext_store import PostgresVNextStore
from alicebot_api.vnext_memory_version import memory_version_snapshot
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


def _seed_consolidation_pair(app_url: str, user_id) -> tuple[str, str]:
    member_id = _seed_active_memory(app_url, user_id)
    with user_connection(app_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        member = store.get_memory(member_id)
        assert member is not None
        candidate = store.create_memory(
            {
                "memory_key": f"candidate.{uuid4()}",
                "value": {"text": "Weekly planning cadence every Monday morning."},
                "status": "candidate",
                "memory_type": "semantic",
                "title": "Consolidated planning cadence",
                "canonical_text": "Weekly planning cadence every Monday morning.",
                "summary": "Consolidated planning cadence.",
                "domain": "professional",
                "sensitivity": "internal",
                "confirmation_status": "unconfirmed",
                "metadata_json": {
                    "candidate_kind": "memory_consolidation",
                    "review_required": True,
                    "consolidation": {
                        "proposal_kind": "merge",
                        "cluster_member_ids": [member_id],
                        "member_snapshots": [memory_version_snapshot(member)],
                        "proposed_supersede": [member_id],
                    },
                },
            }
        )
        return member_id, str(candidate["id"])


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


def test_inverse_supersession_edges_serialize_before_row_locks(
    migrated_database_urls, monkeypatch
) -> None:
    """Inverse A->B/B->A requests reject one edge without a PG deadlock."""
    _clear_provider_env(monkeypatch)
    app_url = migrated_database_urls["app"]
    user_id = uuid4()
    first_id = _seed_active_memory(app_url, user_id)
    with user_connection(app_url, user_id) as conn:
        second = PostgresVNextStore(conn).create_memory(
            {
                "memory_key": f"memory.{uuid4()}",
                "value": {"text": "Planning cadence moved to Tuesdays."},
                "status": "active",
                "memory_type": "semantic",
                "title": "Replacement planning cadence",
                "canonical_text": "Planning cadence moved to Tuesdays.",
                "summary": "Tuesday planning cadence.",
                "domain": "professional",
                "sensitivity": "internal",
                "confirmation_status": "confirmed",
            }
        )
    second_id = str(second["id"])
    start = threading.Barrier(2)
    outcomes: list[object] = []
    outcomes_lock = threading.Lock()

    def supersede(source_id: str, successor_id: str) -> None:
        try:
            with user_connection(app_url, user_id) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET LOCAL lock_timeout = '5s'")
                start.wait(timeout=10)
                result = VNextMemoryCommitService(PostgresVNextStore(conn)).undo(
                    identity=None,
                    memory_id=source_id,
                    superseded_by_memory_id=successor_id,
                    reason="Concurrent inverse-edge regression.",
                )
                outcome: object = result
        except Exception as exc:  # noqa: BLE001 - exact type asserted below
            outcome = exc
        with outcomes_lock:
            outcomes.append(outcome)

    workers = [
        threading.Thread(target=supersede, args=(first_id, second_id)),
        threading.Thread(target=supersede, args=(second_id, first_id)),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)
        assert not worker.is_alive(), "inverse-edge worker did not finish"

    assert len(outcomes) == 2
    assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1
    failures = [outcome for outcome in outcomes if isinstance(outcome, Exception)]
    assert len(failures) == 1
    assert isinstance(failures[0], VNextMemoryCommitValidationError)
    assert not isinstance(failures[0], pg_errors.DeadlockDetected)

    with user_connection(app_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        first = store.get_memory(first_id)
        second = store.get_memory(second_id)
    assert {first["status"], second["status"]} == {"active", "superseded"}


def _run_member_mutation(
    service: VNextMemoryCommitService,
    *,
    operation: str,
    member_id: str,
) -> dict[str, object]:
    if operation == "correct":
        return service.correct(
            identity=None,
            memory_id=member_id,
            canonical_text="Corrected while consolidation acceptance raced.",
            reason="Adversarial correction.",
        )
    if operation == "forget":
        return service.forget(
            identity=None,
            memory_id=member_id,
            reason="Adversarial forget.",
        )
    return service.undo(
        identity=None,
        memory_id=member_id,
        reason="Adversarial lifecycle transition.",
    )


@pytest.mark.parametrize("accept_surface", ["direct", "http"])
@pytest.mark.parametrize("member_operation", ["correct", "forget", "transition"])
def test_consolidation_acceptance_serializes_against_member_mutations(
    migrated_database_urls,
    monkeypatch,
    accept_surface: str,
    member_operation: str,
) -> None:
    """Candidate acceptance and member mutation never invert row locks.

    Both the direct service and generic HTTP review adapter race against every
    member mutation that invalidates derived work. Exactly one decision wins;
    the loser observes the committed lifecycle state rather than a PostgreSQL
    deadlock or lock timeout.
    """
    _clear_provider_env(monkeypatch)
    app_url = migrated_database_urls["app"]
    monkeypatch.setattr(vnext_memories_router, "get_settings", lambda: Settings(database_url=app_url))
    user_id = uuid4()
    member_id, candidate_id = _seed_consolidation_pair(app_url, user_id)
    start = threading.Barrier(2)
    outcomes: dict[str, object] = {}
    outcome_lock = threading.Lock()

    def accept_candidate() -> None:
        try:
            start.wait(timeout=10)
            if accept_surface == "http":
                outcome: object = vnext_memories_router.review_vnext_memory(
                    UUID(candidate_id),
                    vnext_memories_router.VNextMemoryReviewRequest(
                        user_id=user_id,
                        action="accept",
                        reason="Adversarial HTTP acceptance.",
                    ),
                )
            else:
                with user_connection(app_url, user_id) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SET LOCAL lock_timeout = '5s'")
                    outcome = VNextMemoryCommitService(
                        PostgresVNextStore(conn)
                    ).accept_consolidation_candidate(
                        candidate_id,
                        reason="Adversarial direct acceptance.",
                    )
        except Exception as exc:  # noqa: BLE001 - exact failure classes checked below
            outcome = exc
        with outcome_lock:
            outcomes["accept"] = outcome

    def mutate_member() -> None:
        try:
            with user_connection(app_url, user_id) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET LOCAL lock_timeout = '5s'")
                start.wait(timeout=10)
                outcome: object = _run_member_mutation(
                    VNextMemoryCommitService(PostgresVNextStore(conn)),
                    operation=member_operation,
                    member_id=member_id,
                )
        except Exception as exc:  # noqa: BLE001 - exact failure classes checked below
            outcome = exc
        with outcome_lock:
            outcomes["member"] = outcome

    workers = [
        threading.Thread(target=accept_candidate, name=f"{accept_surface}-accept"),
        threading.Thread(target=mutate_member, name=f"{member_operation}-member"),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=20)
        assert not worker.is_alive(), f"{worker.name} did not finish"

    assert set(outcomes) == {"accept", "member"}
    for outcome in outcomes.values():
        assert not isinstance(outcome, pg_errors.DeadlockDetected)
        assert not isinstance(outcome, pg_errors.LockNotAvailable)

    accept_outcome = outcomes["accept"]
    accept_succeeded = (
        accept_outcome.status_code == 200
        if accept_surface == "http" and hasattr(accept_outcome, "status_code")
        else isinstance(accept_outcome, dict)
    )
    member_succeeded = isinstance(outcomes["member"], dict)
    assert accept_succeeded is not member_succeeded

    with user_connection(app_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        member = store.get_memory(member_id)
        candidate = store.get_memory(candidate_id)
    assert member is not None and candidate is not None
    if accept_succeeded:
        assert member["status"] == "superseded"
        assert candidate["status"] == "active"
    else:
        assert candidate["status"] == "stale"


def test_http_review_acquires_graph_lock_before_candidate_row(
    migrated_database_urls,
    monkeypatch,
) -> None:
    """The HTTP adapter must not restore the reviewed row -> graph inversion."""
    _clear_provider_env(monkeypatch)
    app_url = migrated_database_urls["app"]
    monkeypatch.setattr(vnext_memories_router, "get_settings", lambda: Settings(database_url=app_url))
    user_id = uuid4()
    _member_id, candidate_id = _seed_consolidation_pair(app_url, user_id)
    graph_acquired = threading.Event()
    release_graph_holder = threading.Event()
    original_lock = PostgresVNextStore.lock_graph_mutation

    def paused_graph_lock(store: PostgresVNextStore) -> None:
        original_lock(store)
        if threading.current_thread().name == "http-review-lock-order":
            graph_acquired.set()
            assert release_graph_holder.wait(timeout=10)

    monkeypatch.setattr(PostgresVNextStore, "lock_graph_mutation", paused_graph_lock)
    outcome: dict[str, object] = {}

    def review_candidate() -> None:
        try:
            outcome["response"] = vnext_memories_router.review_vnext_memory(
                UUID(candidate_id),
                vnext_memories_router.VNextMemoryReviewRequest(
                    user_id=user_id,
                    action="accept",
                    reason="Lock-order regression.",
                ),
            )
        except Exception as exc:  # noqa: BLE001 - surfaced below
            outcome["error"] = exc

    worker = threading.Thread(target=review_candidate, name="http-review-lock-order")
    worker.start()
    try:
        assert graph_acquired.wait(timeout=10), "HTTP review never acquired the graph lock"
        # The HTTP worker is paused immediately after its graph lock. This row
        # lock succeeds only if the route did not pre-lock the candidate first.
        with user_connection(app_url, user_id) as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL lock_timeout = '750ms'")
                cur.execute(
                    """
                    SELECT id
                    FROM memories
                    WHERE user_id = app.current_user_id()
                      AND id = %s::uuid
                    FOR UPDATE
                    """,
                    (candidate_id,),
                )
                assert cur.fetchone() is not None
    finally:
        release_graph_holder.set()
        worker.join(timeout=20)

    assert not worker.is_alive(), "HTTP review worker did not finish"
    assert "error" not in outcome, outcome.get("error")
    assert outcome["response"].status_code == 200

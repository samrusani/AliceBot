from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import threading
from uuid import uuid4

import pytest

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_agent_control import AgentIdentity
from alicebot_api.vnext_brain import VNextBrainService
from alicebot_api.vnext_model_intelligence import ModelBackedArtifact
from alicebot_api.vnext_scheduler import SchedulerRunRequest, VNextSchedulerService, default_schedule
from alicebot_api.vnext_scheduler_runtime import run_due_workflows_durable, run_now_durable
from alicebot_api.vnext_store import PostgresVNextStore
import alicebot_api.vnext_scheduler_runtime as scheduler_runtime


def _seed_scheduler_input(database_url: str, user_id, *, now: datetime) -> None:
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(
            user_id,
            f"scheduler-atomic-{uuid4().hex}@example.invalid",
            "Scheduler Atomicity",
        )
        PostgresVNextStore(conn).create_source(
            {
                "source_type": "manual_text",
                "title": "Atomic scheduler input",
                "content_hash": f"sha256:{uuid4().hex}",
                "captured_at": now,
                "source_created_at": now,
                "domain": "project",
                "sensitivity": "internal",
                "metadata_json": {
                    "raw_text": "TODO: publish this candidate only with the final scheduler artifact",
                },
            },
            actor_type="user",
        )


def _seed_logical_report_inputs(database_url: str, user_id, *, now: datetime) -> None:
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(
            user_id,
            f"scheduler-replay-{uuid4().hex}@example.invalid",
            "Scheduler Replay",
        )
        store = PostgresVNextStore(conn)
        store.create_source(
            {
                "source_type": "manual_text",
                "title": "Artifact retrieval policy note",
                "content_hash": f"sha256:{uuid4().hex}",
                "captured_at": now,
                "source_created_at": now,
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {
                    "raw_text": (
                        "Alice should not auto-promote generated artifacts into memory; "
                        "retrieval provenance review is mandatory."
                    )
                },
            },
            actor_type="user",
        )
        store.create_memory(
            {
                "memory_key": f"report.semantic.{uuid4().hex}",
                "value": {"kind": "policy"},
                "status": "active",
                "memory_type": "semantic",
                "canonical_text": (
                    "Alice should not auto-promote generated artifacts into memory; "
                    "retrieval provenance review is mandatory."
                ),
                "domain": "project",
                "sensitivity": "private",
            },
            actor_type="user",
        )
        belief_memory = store.create_memory(
            {
                "memory_key": f"report.belief.{uuid4().hex}",
                "value": {"kind": "belief"},
                "status": "active",
                "memory_type": "belief",
                "canonical_text": (
                    "Alice should auto-promote generated artifacts into memory and require retrieval provenance review."
                ),
                "domain": "project",
                "sensitivity": "private",
            },
            actor_type="user",
        )
        store.create_belief(
            {
                "memory_id": str(belief_memory["id"]),
                "claim": (
                    "Alice should auto-promote generated artifacts into memory and require retrieval provenance review."
                ),
                "status": "active",
                "confidence": 0.8,
            },
            actor_type="user",
        )


def _make_workflow_due(
    database_url: str,
    user_id,
    *,
    workflow_type: str,
    checked_at: datetime,
) -> None:
    with user_connection(database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        VNextSchedulerService(store).ensure_default_workflows()
        store.update_scheduler_workflow(
            workflow_type=workflow_type,
            patch={
                "enabled": True,
                "paused": False,
                "schedule_json": default_schedule(workflow_type),
                "timezone": "UTC",
                "next_run_at": checked_at - timedelta(minutes=1),
                "metadata_json": {
                    "model_options": {
                        "generation_mode": "model_backed",
                        "discover_open_loops": True,
                        "create_candidate_memories": True,
                    }
                },
            },
            actor_type="scheduler-test",
        )


def _disable_workflow(database_url: str, user_id, workflow_type: str) -> None:
    with user_connection(database_url, user_id) as conn:
        PostgresVNextStore(conn).update_scheduler_workflow(
            workflow_type=workflow_type,
            patch={"enabled": False, "next_run_at": None},
            actor_type="scheduler-test",
        )


def _assert_no_published_workflow_side_effects(database_url: str, user_id) -> None:
    with user_connection(database_url, user_id) as conn:
        with conn.cursor() as cur:
            counts: list[int] = []
            for table in ("generated_artifacts", "memories", "open_loops"):
                cur.execute(f"SELECT COUNT(*) AS count FROM {table}")  # noqa: S608 - fixed test identifiers
                counts.append(int(cur.fetchone()["count"]))
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM event_log
                WHERE event_type LIKE 'artifact.%'
                   OR event_type LIKE 'memory.%'
                   OR event_type LIKE 'open_loop.%'
                """
            )
            workflow_event_count = int(cur.fetchone()["count"])
    assert counts == [0, 0, 0]
    assert workflow_event_count == 0


def _successful_model_artifact(*_args, **_kwargs) -> ModelBackedArtifact:
    return ModelBackedArtifact(
        content_markdown="# Staged model result",
        prompt_hash="sha256:prompt",
        input_context_hash="sha256:context",
        model_info={"provider": "test", "model": "test-model"},
        metadata={"generation_mode": "model_backed"},
    )


@pytest.mark.parametrize("failure_mode", ["provider_failure", "fence_loss"])
def test_daily_and_weekly_publish_nothing_before_successful_fenced_finalize(
    migrated_database_urls: dict[str, str],
    monkeypatch,
    failure_mode: str,
) -> None:
    database_url = migrated_database_urls["app"]
    user_id = uuid4()
    checked_at = datetime.now(UTC).replace(microsecond=0)
    _seed_scheduler_input(database_url, user_id, now=checked_at)

    def fake_model_artifact(*_args, **_kwargs) -> ModelBackedArtifact:
        if failure_mode == "provider_failure":
            raise RuntimeError("forced provider failure")
        return _successful_model_artifact()

    @contextmanager
    def fake_heartbeat(**_kwargs):
        fence_lost = threading.Event()
        if failure_mode == "fence_loss":
            fence_lost.set()
        yield fence_lost

    monkeypatch.setattr(VNextBrainService, "_model_backed_artifact", fake_model_artifact)
    monkeypatch.setattr(scheduler_runtime, "_claim_heartbeat", fake_heartbeat)

    for workflow_type in ("daily_brief", "weekly_synthesis"):
        _make_workflow_due(
            database_url,
            user_id,
            workflow_type=workflow_type,
            checked_at=checked_at,
        )
        result = run_due_workflows_durable(
            database_url=database_url,
            user_id=user_id,
            limit=1,
            now=checked_at,
            claim_lease_seconds=30,
        )

        assert result["due_count"] == 1
        assert result["failed_count"] == 1
        assert result["runs"][0]["workflow_type"] == workflow_type
        assert result["runs"][0]["artifact"] is None
        _assert_no_published_workflow_side_effects(database_url, user_id)
        _disable_workflow(database_url, user_id, workflow_type)


def test_daily_and_weekly_publish_atomically_after_live_fence(
    migrated_database_urls: dict[str, str],
    monkeypatch,
) -> None:
    database_url = migrated_database_urls["app"]
    user_id = uuid4()
    checked_at = datetime.now(UTC).replace(microsecond=0)
    _seed_scheduler_input(database_url, user_id, now=checked_at)

    @contextmanager
    def live_heartbeat(**_kwargs):
        yield threading.Event()

    monkeypatch.setattr(VNextBrainService, "_model_backed_artifact", _successful_model_artifact)
    monkeypatch.setattr(scheduler_runtime, "_claim_heartbeat", live_heartbeat)

    for index, workflow_type in enumerate(("daily_brief", "weekly_synthesis"), start=1):
        _make_workflow_due(
            database_url,
            user_id,
            workflow_type=workflow_type,
            checked_at=checked_at,
        )
        result = run_due_workflows_durable(
            database_url=database_url,
            user_id=user_id,
            limit=1,
            now=checked_at,
            claim_lease_seconds=30,
        )
        assert result["failed_count"] == 0
        assert result["runs"][0]["run"]["status"] == "succeeded"
        assert result["runs"][0]["artifact"] is not None
        with user_connection(database_url, user_id) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM generated_artifacts")
                assert int(cur.fetchone()["count"]) == index
                cur.execute("SELECT COUNT(*) AS count FROM open_loops")
                assert int(cur.fetchone()["count"]) == 1
                cur.execute("SELECT COUNT(*) AS count FROM memories")
                assert int(cur.fetchone()["count"]) == index - 1
        _disable_workflow(database_url, user_id, workflow_type)


def test_manual_daily_and_weekly_logical_replay_ignores_agent_run_id(
    migrated_database_urls: dict[str, str],
) -> None:
    database_url = migrated_database_urls["app"]
    user_id = uuid4()
    checked_at = datetime.now(UTC).replace(microsecond=0)
    _seed_scheduler_input(database_url, user_id, now=checked_at)

    for expected_artifact_count, workflow_type in enumerate(
        ("daily_brief", "weekly_synthesis"),
        start=1,
    ):
        results = []
        for agent_run_id in ("attempt-a", "attempt-b"):
            results.append(
                run_now_durable(
                    database_url=database_url,
                    user_id=user_id,
                    request=SchedulerRunRequest(
                        workflow_type=workflow_type,
                        generated_for=checked_at.date().isoformat(),
                        triggered_by="agent",
                        agent_identity=AgentIdentity(
                            agent_id="hermes",
                            agent_type="hermes",
                            agent_run_id=agent_run_id,
                            permission_profile="trusted_local_agent",
                        ),
                    ),
                )
            )

        assert results[0]["run"]["status"] == "succeeded"
        assert results[1]["run"]["status"] == "succeeded"
        assert results[0]["artifact"]["id"] == results[1]["artifact"]["id"]
        with user_connection(database_url, user_id) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM generated_artifacts")
                assert int(cur.fetchone()["count"]) == expected_artifact_count


def test_manual_durable_runner_supports_every_model_capable_workflow(
    migrated_database_urls: dict[str, str],
) -> None:
    database_url = migrated_database_urls["app"]
    user_id = uuid4()
    checked_at = datetime.now(UTC).replace(microsecond=0)
    _seed_scheduler_input(database_url, user_id, now=checked_at)

    workflow_types = (
        "daily_brief",
        "weekly_synthesis",
        "connection_report",
        "contradiction_report",
        "open_loop_review",
        "project_update_scan",
        "memory_consolidation",
    )
    for workflow_type in workflow_types:
        result = run_now_durable(
            database_url=database_url,
            user_id=user_id,
            request=SchedulerRunRequest(
                workflow_type=workflow_type,
                generated_for=checked_at.date().isoformat(),
                options={
                    "generation_mode": "model_backed",
                    "create_candidate_memories": True,
                },
            ),
        )

        assert result["run"]["status"] == "succeeded", result
        assert result["artifact"] is not None

    with user_connection(database_url, user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM scheduler_runs WHERE status = 'succeeded'")
            assert int(cur.fetchone()["count"]) == len(workflow_types)


def test_manual_run_bookkeeping_does_not_revoke_an_unrelated_due_claim(
    migrated_database_urls: dict[str, str],
) -> None:
    database_url = migrated_database_urls["app"]
    user_id = uuid4()
    checked_at = datetime.now(UTC).replace(microsecond=0)
    _seed_scheduler_input(database_url, user_id, now=checked_at)
    _make_workflow_due(
        database_url,
        user_id,
        workflow_type="daily_brief",
        checked_at=checked_at,
    )

    with user_connection(database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        claim = store.claim_due_scheduler_workflow(
            checked_at=checked_at,
            lease_expires_at=checked_at + timedelta(minutes=5),
            triggered_by="scheduler",
        )
    assert claim is not None

    manual = run_now_durable(
        database_url=database_url,
        user_id=user_id,
        request=SchedulerRunRequest(
            workflow_type="daily_brief",
            generated_for=(checked_at + timedelta(days=1)).date().isoformat(),
            triggered_by="user",
        ),
    )
    assert manual["run"]["status"] == "succeeded"

    with user_connection(database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        workflow = store.get_scheduler_workflow("daily_brief")
        assert workflow is not None
        assert workflow["claim_token"] == claim["claim_token"]
        assert int(workflow["claim_version"]) == int(claim["claim_version"])
        assert store.heartbeat_scheduler_claim(
            run_id=str(claim["run"]["id"]),
            claim_token=str(claim["claim_token"]),
            claim_version=int(claim["claim_version"]),
            lease_expires_at=checked_at + timedelta(minutes=10),
        )


def test_reaper_reports_and_emits_for_run_after_workflow_claim_was_revoked(
    migrated_database_urls: dict[str, str],
) -> None:
    database_url = migrated_database_urls["app"]
    user_id = uuid4()
    checked_at = datetime.now(UTC).replace(microsecond=0)
    _seed_scheduler_input(database_url, user_id, now=checked_at)
    _make_workflow_due(
        database_url,
        user_id,
        workflow_type="daily_brief",
        checked_at=checked_at,
    )

    with user_connection(database_url, user_id) as conn:
        claim = PostgresVNextStore(conn).claim_due_scheduler_workflow(
            checked_at=checked_at,
            lease_expires_at=checked_at + timedelta(seconds=1),
            triggered_by="scheduler",
        )
    assert claim is not None

    _disable_workflow(database_url, user_id, "daily_brief")
    with user_connection(database_url, user_id) as conn:
        reaped = PostgresVNextStore(conn).reap_expired_scheduler_claims(
            reference_time=checked_at + timedelta(seconds=2),
            actor_type="scheduler-test",
        )

    assert [str(row["id"]) for row in reaped] == [str(claim["run"]["id"])]
    assert reaped[0]["status"] == "failed"
    with user_connection(database_url, user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM event_log
                WHERE event_type = 'scheduler.run_failed'
                  AND target_id = %s
                """,
                (str(claim["run"]["id"]),),
            )
            assert int(cur.fetchone()["count"]) == 1


@pytest.mark.parametrize(
    ("workflow_type", "artifact_type"),
    [
        ("connection_report", "connection_report"),
        ("contradiction_report", "contradiction_report"),
    ],
)
def test_logical_report_concurrent_retries_publish_one_artifact_and_edge_set(
    migrated_database_urls: dict[str, str],
    monkeypatch,
    workflow_type: str,
    artifact_type: str,
) -> None:
    database_url = migrated_database_urls["app"]
    user_id = uuid4()
    checked_at = datetime.now(UTC).replace(microsecond=0)
    _seed_logical_report_inputs(database_url, user_id, now=checked_at)

    original_prepare = VNextSchedulerService.prepare_started_workflow
    prepared = threading.Barrier(2)

    def prepare_together(self, request, *, run):
        plan = original_prepare(self, request, run=run)
        prepared.wait(timeout=10)
        return plan

    monkeypatch.setattr(
        VNextSchedulerService,
        "prepare_started_workflow",
        prepare_together,
    )

    def execute(attempt: str):
        return run_now_durable(
            database_url=database_url,
            user_id=user_id,
            request=SchedulerRunRequest(
                workflow_type=workflow_type,
                generated_for=checked_at.date().isoformat(),
                triggered_by="agent",
                agent_identity=AgentIdentity(
                    agent_id="hermes",
                    agent_type="hermes",
                    agent_run_id=f"attempt-{attempt}",
                    permission_profile="trusted_local_agent",
                ),
            ),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(execute, attempt) for attempt in ("a", "b")]
        results = [future.result(timeout=20) for future in futures]

    assert [result["run"]["status"] for result in results] == ["succeeded", "succeeded"]
    assert results[0]["artifact"]["id"] == results[1]["artifact"]["id"]
    metadata = results[0]["artifact"]["metadata_json"]
    edge_ids = metadata["candidate_edge_ids"]
    assert edge_ids
    assert edge_ids == results[1]["artifact"]["metadata_json"]["candidate_edge_ids"]
    with user_connection(database_url, user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM generated_artifacts
                WHERE artifact_type = %s
                """,
                (artifact_type,),
            )
            assert int(cur.fetchone()["count"]) == 1
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM graph_edges
                WHERE metadata_json ->> 'workflow_digest' = %s
                """,
                (metadata["workflow_digest"],),
            )
            assert int(cur.fetchone()["count"]) == len(edge_ids)
            cur.execute(
                """
                SELECT COUNT(DISTINCT metadata_json ->> 'idempotency_digest') AS count
                FROM graph_edges
                WHERE metadata_json ->> 'workflow_digest' = %s
                """,
                (metadata["workflow_digest"],),
            )
            assert int(cur.fetchone()["count"]) == len(edge_ids)

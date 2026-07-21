from __future__ import annotations

from datetime import UTC, datetime, timedelta
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "run_phase5_ops_evidence.py"
SEED_PATH = ROOT / "scripts" / "_phase5_ops_seed.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ops-evidence.yml"
_SPEC = importlib.util.spec_from_file_location("run_phase5_ops_evidence", SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
ops = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ops)


def test_sqlite_operations_evidence_executes_full_physical_portable_and_upgrade_drill(tmp_path) -> None:
    args = ops._build_parser().parse_args(
        ["--backend", "sqlite", "--work-dir", str(tmp_path / "private")]
    )

    report = ops.run_evidence(args)

    assert report["status"] == "passed"
    assert report["proof_gaps"] == ["postgres_not_requested"]
    assert report["repository"]["baseline_commit"] == ops.BASELINE_COMMIT
    repository = report["repository"]
    assert "current_commit" not in repository
    assert re.fullmatch(r"[0-9a-f]{40}", repository["source_head_commit"])
    assert re.fullmatch(r"[0-9a-f]{40}", repository["source_head_tree"])
    assert repository["carrier_state"] in {"clean", "dirty"}
    assert re.fullmatch(r"[0-9a-f]{64}", repository["carrier_snapshot_sha256"])
    checks = report["checks"]
    assert checks["sqlite_physical_backup_restore"]["destroy_restore"] == "proved"
    assert checks["sqlite_physical_backup_restore"]["embedding_signature"] == "current"
    assert checks["portable_export_import"]["fidelity"] == (
        "canonical_digest_and_counts_match"
    )
    assert checks["portable_export_import"]["embeddings"] == "omitted_by_contract"
    assert checks["sqlite_v0_12_upgrade"]["source_method"] == "git_archive_no_checkout"
    assert checks["sqlite_v0_12_upgrade"]["embedding_stamp"] == (
        "one_nonempty_stable_row"
    )
    serialized = json.dumps(report, sort_keys=True)
    assert ops.SEED_QUERY not in serialized
    assert str(tmp_path) not in serialized
    assert "postgresql://" not in serialized


def _git(repo: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def test_carrier_identity_binds_tracked_and_untracked_changes_without_following_symlinks(
    tmp_path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "phase5@example.invalid")
    _git(repo, "config", "user.name", "Phase 5 Test")
    (repo / ".gitignore").write_text("ignored-output.json\n", encoding="utf-8")
    tracked = repo / "tracked.txt"
    tracked.write_text("original\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-q", "-m", "baseline")

    clean = ops.repository_carrier_identity(repo)
    assert clean["carrier_state"] == "clean"

    tracked.write_text("tracked carrier change\n", encoding="utf-8")
    tracked_change = ops.repository_carrier_identity(repo)
    assert tracked_change["source_head_commit"] == clean["source_head_commit"]
    assert tracked_change["source_head_tree"] == clean["source_head_tree"]
    assert tracked_change["carrier_state"] == "dirty"
    assert tracked_change["carrier_snapshot_sha256"] != clean["carrier_snapshot_sha256"]

    tracked.unlink()
    tracked_deletion = ops.repository_carrier_identity(repo)
    assert tracked_deletion["source_head_commit"] == clean["source_head_commit"]
    assert tracked_deletion["source_head_tree"] == clean["source_head_tree"]
    assert tracked_deletion["carrier_state"] == "dirty"
    assert tracked_deletion["carrier_snapshot_sha256"] != clean["carrier_snapshot_sha256"]
    assert (
        tracked_deletion["carrier_snapshot_sha256"]
        != tracked_change["carrier_snapshot_sha256"]
    )

    tracked.write_text("original\n", encoding="utf-8")
    untracked = repo / "new-evidence.txt"
    untracked.write_text("untracked carrier change\n", encoding="utf-8")
    untracked_change = ops.repository_carrier_identity(repo)
    assert untracked_change["source_head_commit"] == clean["source_head_commit"]
    assert untracked_change["source_head_tree"] == clean["source_head_tree"]
    assert untracked_change["carrier_state"] == "dirty"
    assert untracked_change["carrier_snapshot_sha256"] != clean["carrier_snapshot_sha256"]

    untracked.unlink()
    ignored = repo / "ignored-output.json"
    ignored.write_text("ignored receipt one\n", encoding="utf-8")
    ignored_change = ops.repository_carrier_identity(repo)
    ignored.write_text("ignored receipt two\n", encoding="utf-8")
    assert ignored_change == ops.repository_carrier_identity(repo)
    assert ignored_change == clean

    outside = tmp_path / "outside.txt"
    outside.write_text("outside version one\n", encoding="utf-8")
    link = repo / "outside-link"
    os.symlink(outside, link)
    linked = ops.repository_carrier_identity(repo)
    outside.write_text("outside version two\n", encoding="utf-8")
    linked_after_outside_change = ops.repository_carrier_identity(repo)
    assert linked["carrier_state"] == "dirty"
    assert linked["carrier_snapshot_sha256"] != clean["carrier_snapshot_sha256"]
    assert linked_after_outside_change == linked


def test_scheduler_classifier_covers_disabled_healthy_degraded_and_stuck() -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    assert ops.classify_scheduler_snapshot({}, now=now) == {
        "state": "disabled",
        "reason_codes": [],
    }
    healthy = ops.classify_scheduler_snapshot(
        {
            "configured": True,
            "reported_running": True,
            "running": True,
            "ownership_verified": True,
            "last_heartbeat_at": (now - timedelta(seconds=10)).isoformat(),
            "interval_seconds": 30,
            "last_error_code": None,
            "expired_claim_count": 0,
        },
        now=now,
    )
    assert healthy == {"state": "healthy", "reason_codes": []}
    degraded = ops.classify_scheduler_snapshot(
        {
            "configured": True,
            "reported_running": False,
            "running": False,
            "ownership_verified": True,
            "last_error_code": "claim_failed",
            "expired_claim_count": 2,
        },
        now=now,
    )
    assert degraded == {
        "state": "degraded",
        "reason_codes": ["expired_claims", "last_error"],
    }
    stuck = ops.classify_scheduler_snapshot(
        {
            "configured": True,
            "reported_running": True,
            "running": True,
            "ownership_verified": False,
            "last_heartbeat_at": (now - timedelta(minutes=10)).isoformat(),
            "interval_seconds": 30,
        },
        now=now,
    )
    assert stuck == {
        "state": "stuck",
        "reason_codes": ["heartbeat_stale", "ownership_unverified"],
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"database_url": "redacted"},
        {"value": "postgresql://alice:password@example.invalid/alice"},
        {"value": ops.SEED_QUERY},
        {"value": "phase5-ops@example.invalid"},
    ],
)
def test_sanitized_report_guard_rejects_credentials_paths_and_seed_content(payload) -> None:
    with pytest.raises(ops.EvidenceError):
        ops._assert_report_safe(payload)


def test_postgres_cli_environment_keeps_credentials_out_of_command_arguments() -> None:
    dsn = (
        "postgresql://alicebot_admin:s3cret@db.example.invalid:5544/alice"
        "?sslmode=verify-full&sslrootcert=%2Frun%2Fsecrets%2Falicebot%2Fpostgres-ca.pem"
    )

    env = ops._libpq_env(dsn)
    command = ["pg_dump", "--format=custom", "--file=alice.dump"]

    assert env["PGHOST"] == "db.example.invalid"
    assert env["PGPORT"] == "5544"
    assert env["PGUSER"] == "alicebot_admin"
    assert env["PGPASSWORD"] == "s3cret"
    assert env["PGDATABASE"] == "alice"
    assert env["PGSSLMODE"] == "verify-full"
    assert env["PGSSLROOTCERT"] == "/run/secrets/alicebot/postgres-ca.pem"
    assert all("s3cret" not in argument and "postgresql://" not in argument for argument in command)


def test_v0_12_rating_seed_sets_deterministic_timestamps_at_insert_only() -> None:
    source = SEED_PATH.read_text(encoding="utf-8")

    assert "INSERT INTO artifact_quality_ratings" in source
    assert "UPDATE artifact_quality_ratings" not in source
    assert "created_at," in source
    assert '"2020-01-01T00:00:00Z"' in source
    assert '"2021-01-01T00:00:00Z"' in source


def test_postgres_count_probe_uses_named_dict_row_shape() -> None:
    queries: list[str] = []

    class FakeResult:
        def fetchone(self):
            return {"count": "3"}

    class FakeConnection:
        def execute(self, query):
            queries.append(query)
            return FakeResult()

    counts = ops._postgres_counts(FakeConnection())

    assert set(counts) == {
        "users",
        "memories",
        "event_log",
        "generated_artifacts",
        "artifact_quality_ratings",
    }
    assert set(counts.values()) == {3}
    assert queries and all("count(*) AS count" in query for query in queries)


def test_postgres_client_version_probe_rejects_malformed_output(monkeypatch) -> None:
    monkeypatch.setattr(
        ops,
        "_run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command,
            0,
            "pg_dump version sixteen",
            "",
        ),
    )

    with pytest.raises(ops.EvidenceError) as raised:
        ops._postgres_client_major("/usr/bin/pg_dump", "pg_dump")

    assert raised.value.codes == ("postgres_pg_dump_version_invalid",)


def test_postgres_server_version_probe_rejects_malformed_output(monkeypatch) -> None:
    class FakeResult:
        def fetchone(self):
            return ("PostgreSQL sixteen",)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, query):
            assert query == "SHOW server_version_num"
            return FakeResult()

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=lambda _url: FakeConnection()),
    )

    with pytest.raises(ops.EvidenceError) as raised:
        ops._postgres_server_major("postgresql://db.example.invalid/alice")

    assert raised.value.codes == ("postgres_server_version_invalid",)


@pytest.mark.parametrize(
    ("client_major", "server_major", "failure_code"),
    [
        (18, 16, "postgres_client_major_mismatch"),
        (16, 17, "postgres_server_major_mismatch"),
    ],
)
def test_postgres_toolchain_preflight_rejects_client_or_server_major_mismatch(
    monkeypatch,
    client_major,
    server_major,
    failure_code,
) -> None:
    monkeypatch.setattr(
        ops,
        "_postgres_client_major",
        lambda _executable, _program: client_major,
    )
    monkeypatch.setattr(ops, "_postgres_server_major", lambda _url: server_major)

    with pytest.raises(ops.EvidenceError) as raised:
        ops._validate_postgres_toolchain(
            root_admin_url="postgresql://db.example.invalid/alice",
            pg_dump="/usr/bin/pg_dump",
            pg_restore="/usr/bin/pg_restore",
        )

    assert raised.value.codes == (failure_code,)


@pytest.mark.parametrize(
    ("query", "failure_code"),
    [
        ("sslrootcert=", "postgres_sslrootcert_invalid"),
        (
            "sslrootcert=%2Ffirst.pem&sslrootcert=%2Fsecond.pem",
            "postgres_sslrootcert_invalid",
        ),
        ("sslrootcert=%0A%2Fca.pem", "postgres_sslrootcert_invalid"),
        ("sslrootcert", "postgres_url_query_invalid"),
        ("sslmode=require&sslmode=verify-full", "postgres_sslmode_invalid"),
    ],
)
def test_postgres_cli_environment_rejects_ambiguous_or_unsafe_tls_query_values(
    query,
    failure_code,
) -> None:
    with pytest.raises(ops.EvidenceError) as raised:
        ops._libpq_env(f"postgresql://alicebot_admin@db.example.invalid/alice?{query}")

    assert raised.value.codes == (failure_code,)


def _mock_successful_postgres_drill(monkeypatch, tmp_path) -> None:
    class FakeQueryResult:
        def __init__(self, value):
            self.value = value

        def fetchone(self):
            return (self.value,)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, query):
            value = "160013" if "server_version_num" in query else ops.BASELINE_POSTGRES_HEAD
            return FakeQueryResult(value)

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=lambda _url: FakeConnection()),
    )
    monkeypatch.setattr(ops, "_require_tool", lambda name: name)
    monkeypatch.setattr(ops, "_extract_baseline", lambda _work_dir: tmp_path / "baseline")
    monkeypatch.setattr(ops, "_create_database", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ops, "_seed_postgres_baseline", lambda **_kwargs: None)
    monkeypatch.setattr(ops, "_dynamic_alembic_head", lambda: "current_head")
    monkeypatch.setattr(ops, "_migrate_postgres", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ops, "_verify_migration_0093", lambda _admin_url: None)
    monkeypatch.setattr(
        ops,
        "_verify_postgres_store",
        lambda *_args, **_kwargs: {
            "counts": {"users": 1, "memories": 1},
            "recall": "matched",
            "embedding_signature": "current",
        },
    )
    def fake_run(command, **_kwargs):
        output = ""
        if command[-1] == "--version":
            output = f"{Path(command[0]).name} (PostgreSQL) 16.13"
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr(ops, "_run", fake_run)
    monkeypatch.setattr(ops, "_sha256_file", lambda _path: "a" * 64)
    monkeypatch.setattr(
        ops,
        "_monitoring_drill",
        lambda: {"status": "passed"},
    )
    monkeypatch.setattr(
        ops,
        "repository_carrier_identity",
        lambda: {
            "source_head_commit": "a" * 40,
            "source_head_tree": "b" * 40,
            "carrier_state": "dirty",
            "carrier_snapshot_sha256": "c" * 64,
        },
    )


def _run_mocked_postgres_evidence(tmp_path, capsys) -> tuple[int, dict[str, object]]:
    exit_code = ops.main(
        [
            "--backend",
            "postgres",
            "--work-dir",
            str(tmp_path / "private"),
            "--database-admin-url",
            "postgresql://alicebot_admin:admin@db.example.invalid/postgres",
            "--database-url",
            "postgresql://alicebot_app:app@db.example.invalid/postgres",
        ]
    )
    return exit_code, json.loads(capsys.readouterr().out)


def test_postgres_toolchain_mismatch_fails_before_disposable_database_creation(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    _mock_successful_postgres_drill(monkeypatch, tmp_path)
    create_called = False

    def record_create(*_args, **_kwargs):
        nonlocal create_called
        create_called = True

    monkeypatch.setattr(ops, "_postgres_client_major", lambda _path, _program: 18)
    monkeypatch.setattr(ops, "_postgres_server_major", lambda _url: 16)
    monkeypatch.setattr(ops, "_create_database", record_create)

    exit_code, report = _run_mocked_postgres_evidence(tmp_path, capsys)

    assert create_called is False
    assert exit_code == 1
    assert report["status"] == "failed"
    assert report["failure_codes"] == ["postgres_client_major_mismatch"]


def test_postgres_final_cleanup_failure_cannot_report_passed(monkeypatch, tmp_path, capsys) -> None:
    _mock_successful_postgres_drill(monkeypatch, tmp_path)
    drop_calls = 0

    def fail_final_drop(_root_url, _database_name):
        nonlocal drop_calls
        drop_calls += 1
        if drop_calls == 2:
            raise RuntimeError("simulated final cleanup failure")

    monkeypatch.setattr(ops, "_drop_database", fail_final_drop)

    exit_code, report = _run_mocked_postgres_evidence(tmp_path, capsys)

    assert drop_calls == 2
    assert exit_code == 1
    assert report["status"] == "failed"
    assert report["failure_codes"] == ["postgres_cleanup_failed"]


def test_postgres_create_grant_and_cleanup_failures_are_both_reported(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    _mock_successful_postgres_drill(monkeypatch, tmp_path)
    drop_calls = 0

    def fail_after_create(*_args, **_kwargs):
        raise ops.EvidenceError("postgres_create_grant_failed")

    def fail_cleanup(_root_url, _database_name):
        nonlocal drop_calls
        drop_calls += 1
        raise RuntimeError("simulated cleanup failure")

    monkeypatch.setattr(ops, "_create_database", fail_after_create)
    monkeypatch.setattr(ops, "_drop_database", fail_cleanup)

    exit_code, report = _run_mocked_postgres_evidence(tmp_path, capsys)

    assert drop_calls == 1
    assert exit_code == 1
    assert report["status"] == "failed"
    assert report["failure_codes"] == [
        "postgres_create_grant_failed",
        "postgres_cleanup_failed",
    ]


def test_postgres_mode_fails_closed_without_both_role_separated_urls(tmp_path, capsys) -> None:
    output = tmp_path / "failed.json"

    exit_code = ops.main(
        [
            "--backend",
            "postgres",
            "--work-dir",
            str(tmp_path / "private"),
            "--database-admin-url",
            "",
            "--database-url",
            "",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["failure_codes"] == ["missing_prerequisite:postgres_urls"]
    assert json.loads(output.read_text(encoding="utf-8")) == payload


def test_ops_workflow_has_required_triggers_full_history_and_atomic_pins() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert re.search(r"(?m)^  pull_request:$", workflow)
    assert re.search(r"(?m)^  push:$", workflow)
    assert re.search(r"(?m)^      - main$", workflow)
    assert re.search(r"(?m)^  workflow_dispatch:$", workflow)
    assert "runs-on: ubuntu-24.04" in workflow
    assert "fetch-depth: 0" in workflow
    assert "postgresql-client-16" in workflow
    assert 'echo "/usr/lib/postgresql/16/bin" >> "$GITHUB_PATH"' in workflow
    assert (
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7" in workflow
    )
    assert (
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6" in workflow
    )
    assert (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7"
        in workflow
    )
    assert (
        "pgvector/pgvector:pg16@sha256:"
        "1d533553fefe4f12e5d80c7b80622ba0c382abb5758856f52983d8789179f0fb"
        in workflow
    )
    assert "scripts/run_phase5_ops_evidence.py" in workflow
    assert "--backend all" in workflow


def test_ops_docs_name_executed_commands_and_honest_boundaries() -> None:
    disaster = (ROOT / "docs" / "runbooks" / "disaster-recovery.md").read_text(
        encoding="utf-8"
    )
    monitoring = (ROOT / "docs" / "runbooks" / "health-and-monitoring.md").read_text(
        encoding="utf-8"
    )
    upgrade = (ROOT / "docs" / "runbooks" / "upgrade-v0.12-to-current.md").read_text(
        encoding="utf-8"
    )
    backup = (ROOT / "docs" / "alpha" / "backup-and-restore.md").read_text(
        encoding="utf-8"
    )

    assert "run_phase5_ops_evidence.py --backend all" in disaster
    assert "wal_checkpoint(TRUNCATE)" in disaster
    assert "pg_dump" in disaster and "pg_restore" in disaster
    assert "postgres_cleanup_failed" in disaster
    assert "PGSSLROOTCERT=/run/secrets/alicebot/postgres-ca.pem" in disaster
    assert "PostgreSQL 16 `pg_dump`" in disaster
    assert "validates all three major versions" in disaster
    assert "not_checked" in monitoring
    assert "ownership_verified" in monitoring and "last_heartbeat_at" in monitoring
    assert ops.BASELINE_COMMIT in upgrade
    assert "git archive" in upgrade
    assert ops.MIGRATION_0093 in upgrade
    assert ops.MIGRATION_0094 in upgrade
    assert "alice-memory reindex-embeddings" in backup
    assert "Portable JSONL does not contain embedding vectors" in backup

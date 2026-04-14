from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID, uuid4

from alicebot_api.contracts import MemoryCandidateInput
from alicebot_api.db import user_connection
from alicebot_api.markdown_import import import_markdown_source
from alicebot_api.memory import admit_memory_candidate
from alicebot_api.store import ContinuityStore


REPO_ROOT = Path(__file__).resolve().parents[2]


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def build_cli_env(*, database_url: str, user_id: UUID) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["ALICEBOT_AUTH_USER_ID"] = str(user_id)

    pythonpath_entries = [str(REPO_ROOT / "apps" / "api" / "src"), str(REPO_ROOT / "workers")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return env


def run_cli(args: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alicebot_api", *args],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_command_surface_and_correction_flow(migrated_database_urls) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="cli-user@example.com")
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)

        legacy_capture = store.create_continuity_capture_event(
            raw_content="Decision: Legacy rollout plan",
            explicit_signal="decision",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_decision",
        )
        legacy_decision = store.create_continuity_object(
            capture_event_id=legacy_capture["id"],
            object_type="Decision",
            status="active",
            title="Decision: Legacy rollout plan",
            body={"decision_text": "Legacy rollout plan"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["cli-seed-1"]},
            confidence=0.91,
            last_confirmed_at=datetime(2026, 3, 30, 9, 0, tzinfo=UTC),
        )

        waiting_capture = store.create_continuity_capture_event(
            raw_content="Waiting For: Reviewer PASS",
            explicit_signal="waiting_for",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_waiting_for",
        )
        waiting_for = store.create_continuity_object(
            capture_event_id=waiting_capture["id"],
            object_type="WaitingFor",
            status="active",
            title="Waiting For: Reviewer PASS",
            body={"waiting_for_text": "Reviewer PASS"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["cli-seed-2"]},
            confidence=0.9,
        )

    env = build_cli_env(database_url=migrated_database_urls["app"], user_id=user_id)

    help_result = run_cli(["--help"], env=env)
    assert help_result.returncode == 0
    assert "capture" in help_result.stdout
    assert "review" in help_result.stdout
    assert "status" in help_result.stdout

    status_result = run_cli(["status"], env=env)
    assert status_result.returncode == 0
    assert "database: reachable" in status_result.stdout
    assert "continuity_capture_events: 2" in status_result.stdout
    assert "continuity_object_lifecycle:" in status_result.stdout

    capture_result = run_cli(
        [
            "capture",
            "Task: Publish CLI usage docs",
            "--explicit-signal",
            "task",
        ],
        env=env,
    )
    assert capture_result.returncode == 0
    assert "capture_event_id:" in capture_result.stdout
    assert "derived_object_type: NextAction" in capture_result.stdout

    recall_before = run_cli(
        [
            "recall",
            "--query",
            "rollout",
            "--thread-id",
            str(thread_id),
            "--limit",
            "20",
            "--debug",
        ],
        env=env,
    )
    assert recall_before.returncode == 0
    assert "Decision: Legacy rollout plan" in recall_before.stdout
    assert "lifecycle=preserved:True searchable:True promotable:True" in recall_before.stdout
    assert "debug:" in recall_before.stdout
    assert "lexical: raw=" in recall_before.stdout

    lifecycle_list_result = run_cli(
        ["lifecycle", "list", "--limit", "20"],
        env=env,
    )
    assert lifecycle_list_result.returncode == 0
    assert "continuity lifecycle" in lifecycle_list_result.stdout
    assert "promotable=3" in lifecycle_list_result.stdout

    lifecycle_show_result = run_cli(
        ["lifecycle", "show", str(legacy_decision["id"])],
        env=env,
    )
    assert lifecycle_show_result.returncode == 0
    assert f"continuity_object_id: {legacy_decision['id']}" in lifecycle_show_result.stdout

    resume_before = run_cli(
        [
            "resume",
            "--thread-id",
            str(thread_id),
            "--max-recent-changes",
            "5",
            "--max-open-loops",
            "5",
            "--debug",
        ],
        env=env,
    )
    assert resume_before.returncode == 0
    assert "last_decision:" in resume_before.stdout
    assert "Decision: Legacy rollout plan" in resume_before.stdout
    assert "debug:" in resume_before.stdout

    open_loops_result = run_cli(
        ["open-loops", "--thread-id", str(thread_id), "--limit", "20"],
        env=env,
    )
    assert open_loops_result.returncode == 0
    assert "waiting_for (returned=1 total=1 limit=20)" in open_loops_result.stdout
    assert waiting_for["title"] in open_loops_result.stdout

    review_queue_result = run_cli(
        ["review", "queue", "--status", "correction_ready", "--limit", "20"],
        env=env,
    )
    assert review_queue_result.returncode == 0
    assert str(legacy_decision["id"]) in review_queue_result.stdout

    review_show_result = run_cli(
        ["review", "show", str(legacy_decision["id"])],
        env=env,
    )
    assert review_show_result.returncode == 0
    assert f"continuity_object_id: {legacy_decision['id']}" in review_show_result.stdout

    replacement_provenance = json.dumps({"thread_id": str(thread_id), "source_event_ids": ["cli-correction-1"]})
    review_apply_result = run_cli(
        [
            "review",
            "apply",
            str(legacy_decision["id"]),
            "--action",
            "supersede",
            "--reason",
            "Latest decision supersedes legacy plan",
            "--replacement-title",
            "Decision: Updated rollout plan",
            "--replacement-body-json",
            '{"decision_text":"Updated rollout plan"}',
            "--replacement-provenance-json",
            replacement_provenance,
            "--replacement-confidence",
            "0.97",
        ],
        env=env,
    )
    assert review_apply_result.returncode == 0
    assert "replacement_object_id: " in review_apply_result.stdout
    assert "replacement_object_id: none" not in review_apply_result.stdout

    recall_after = run_cli(
        [
            "recall",
            "--thread-id",
            str(thread_id),
            "--query",
            "rollout",
            "--limit",
            "20",
        ],
        env=env,
    )
    assert recall_after.returncode == 0
    assert "Decision: Updated rollout plan" in recall_after.stdout

    resume_after = run_cli(
        [
            "resume",
            "--thread-id",
            str(thread_id),
            "--max-recent-changes",
            "5",
            "--max-open-loops",
            "5",
        ],
        env=env,
    )
    assert resume_after.returncode == 0
    assert "Decision: Updated rollout plan" in resume_after.stdout

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        hidden_fact_capture = store.create_continuity_capture_event(
            raw_content="Remember: searchable but not promotable",
            explicit_signal="remember_this",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_remember_this",
        )
        hidden_fact = store.create_continuity_object(
            capture_event_id=hidden_fact_capture["id"],
            object_type="MemoryFact",
            status="active",
            title="Memory Fact: searchable but not promotable",
            body={"fact_text": "searchable but not promotable"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["cli-seed-3"]},
            confidence=0.88,
            is_promotable=False,
        )

    lifecycle_hidden_result = run_cli(
        ["lifecycle", "show", str(hidden_fact["id"])],
        env=env,
    )
    assert lifecycle_hidden_result.returncode == 0
    assert "promotable=False" in lifecycle_hidden_result.stdout

    resume_default_fact_result = run_cli(
        [
            "resume",
            "--thread-id",
            str(thread_id),
            "--max-recent-changes",
            "10",
            "--max-open-loops",
            "5",
        ],
        env=env,
    )
    assert resume_default_fact_result.returncode == 0
    assert "Memory Fact: searchable but not promotable" not in resume_default_fact_result.stdout

    resume_override_fact_result = run_cli(
        [
            "resume",
            "--thread-id",
            str(thread_id),
            "--max-recent-changes",
            "10",
            "--max-open-loops",
            "5",
            "--include-non-promotable-facts",
        ],
        env=env,
    )
    assert resume_override_fact_result.returncode == 0
    assert "Memory Fact: searchable but not promotable" in resume_override_fact_result.stdout

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        imported = import_markdown_source(
            ContinuityStore(conn),
            user_id=user_id,
            source=REPO_ROOT / "fixtures" / "importers" / "markdown" / "workspace_v1.md",
        )
        imported_object_id = imported["imported_object_ids"][0]
        evidence_rows = ContinuityStore(conn).list_continuity_object_evidence(UUID(imported_object_id))
        artifact_id = evidence_rows[0]["artifact_id"]

    explain_result = run_cli(["explain", imported_object_id], env=env)
    assert explain_result.returncode == 0
    assert "evidence_links: 1" in explain_result.stdout
    assert "raw_evidence=" in explain_result.stdout

    artifact_result = run_cli(["evidence", "artifact", str(artifact_id)], env=env)
    assert artifact_result.returncode == 0
    assert "artifact detail" in artifact_result.stdout
    assert "copies: 1" in artifact_result.stdout
    assert "segments:" in artifact_result.stdout


def test_cli_memory_mutation_commands_smoke(migrated_database_urls) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="cli-mutations@example.com")
    thread_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        capture = store.create_continuity_capture_event(
            raw_content="Decision: Legacy mutation plan",
            explicit_signal="decision",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_decision",
        )
        store.create_continuity_object(
            capture_event_id=capture["id"],
            object_type="Decision",
            status="active",
            title="Decision: Legacy mutation plan",
            body={"decision_text": "Legacy mutation plan"},
            provenance={"thread_id": str(thread_id)},
            confidence=0.96,
        )

    env = build_cli_env(database_url=migrated_database_urls["app"], user_id=user_id)

    generate_result = run_cli(
        [
            "mutations",
            "generate",
            "--user-content",
            "Correction: Updated mutation plan",
            "--mode",
            "assist",
            "--sync-fingerprint",
            "cli-mutation-sync-001",
            "--thread-id",
            str(thread_id),
        ],
        env=env,
    )
    assert generate_result.returncode == 0
    assert "memory operation candidates" in generate_result.stdout
    assert "[SUPERSEDE|auto_apply]" in generate_result.stdout

    candidates_result = run_cli(
        [
            "mutations",
            "candidates",
            "--sync-fingerprint",
            "cli-mutation-sync-001",
            "--limit",
            "20",
        ],
        env=env,
    )
    assert candidates_result.returncode == 0
    assert "source_candidate_id=" in candidates_result.stdout

    candidate_id_line = next(
        line for line in candidates_result.stdout.splitlines() if "id=" in line and "source_candidate_id=" in line
    )
    candidate_id = candidate_id_line.split("id=", 1)[1].split(" ", 1)[0]

    commit_result = run_cli(
        [
            "mutations",
            "commit",
            candidate_id,
        ],
        env=env,
    )
    assert commit_result.returncode == 0
    assert "memory operation commit" in commit_result.stdout
    assert "[SUPERSEDE|applied]" in commit_result.stdout

    operations_result = run_cli(
        [
            "mutations",
            "operations",
            "--sync-fingerprint",
            "cli-mutation-sync-001",
            "--limit",
            "20",
        ],
        env=env,
    )
    assert operations_result.returncode == 0
    assert "memory operations" in operations_result.stdout
    assert "[SUPERSEDE|applied]" in operations_result.stdout


def test_cli_lists_and_explains_trusted_fact_promotions(migrated_database_urls) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="trusted-cli@example.invalid")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        thread = store.create_thread("Trusted fact CLI")
        session = store.create_session(thread["id"], status="active")
        coffee_event = store.append_event(thread["id"], session["id"], "message.user", {"text": "Coffee"})["id"]
        tea_event = store.append_event(thread["id"], session["id"], "message.user", {"text": "Tea"})["id"]
        generated_event = store.append_event(
            thread["id"], session["id"], "message.user", {"text": "Model suggested mate"}
        )["id"]

        admit_memory_candidate(
            store,
            user_id=user_id,
            candidate=MemoryCandidateInput(
                memory_key="user.preference.coffee",
                value={"drink": "coffee"},
                source_event_ids=(coffee_event,),
                memory_type="preference",
                trust_class="human_curated",
                promotion_eligibility="promotable",
                evidence_count=2,
                independent_source_count=2,
                trust_reason="owner confirmed",
            ),
        )
        admit_memory_candidate(
            store,
            user_id=user_id,
            candidate=MemoryCandidateInput(
                memory_key="user.preference.tea",
                value={"drink": "tea"},
                source_event_ids=(tea_event,),
                memory_type="preference",
                trust_class="deterministic",
                promotion_eligibility="promotable",
                evidence_count=1,
                independent_source_count=1,
                trust_reason="deterministic capture",
            ),
        )
        admit_memory_candidate(
            store,
            user_id=user_id,
            candidate=MemoryCandidateInput(
                memory_key="user.preference.generated",
                value={"drink": "mate"},
                source_event_ids=(generated_event,),
                memory_type="preference",
                trust_class="llm_single_source",
                promotion_eligibility="promotable",
                evidence_count=1,
                independent_source_count=1,
                extracted_by_model="gpt-5.4-mini",
                trust_reason="single-source model extraction",
            ),
        )

    env = build_cli_env(database_url=migrated_database_urls["app"], user_id=user_id)

    patterns_list = run_cli(["patterns", "list", "--limit", "10"], env=env)
    assert patterns_list.returncode == 0
    assert "patterns" in patterns_list.stdout
    assert "fact_count=2" in patterns_list.stdout

    pattern_id = None
    for line in patterns_list.stdout.splitlines():
        if line.strip().startswith("id="):
            pattern_id = line.split("id=", 1)[1].split()[0]
            break
    assert pattern_id is not None

    pattern_explain = run_cli(["patterns", "explain", pattern_id], env=env)
    assert pattern_explain.returncode == 0
    assert "evidence_chain:" in pattern_explain.stdout
    assert "memory_key=user.preference.coffee" in pattern_explain.stdout
    assert "user.preference.generated" not in pattern_explain.stdout

    playbooks_list = run_cli(["playbooks", "list", "--limit", "10"], env=env)
    assert playbooks_list.returncode == 0
    assert "playbooks" in playbooks_list.stdout
    assert "step_count=2" in playbooks_list.stdout

    playbook_id = None
    for line in playbooks_list.stdout.splitlines():
        if line.strip().startswith("id="):
            playbook_id = line.split("id=", 1)[1].split()[0]
            break
    assert playbook_id is not None

    playbook_explain = run_cli(["playbooks", "explain", playbook_id], env=env)
    assert playbook_explain.returncode == 0
    assert "steps:" in playbook_explain.stdout
    assert "[prefer]" in playbook_explain.stdout

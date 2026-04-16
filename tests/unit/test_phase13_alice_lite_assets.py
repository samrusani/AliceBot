from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_alice_lite_env_example_uses_memory_backed_entrypoint_limits() -> None:
    env_lite = (REPO_ROOT / ".env.lite.example").read_text(encoding="utf-8")

    assert "APP_RELOAD=false" in env_lite
    assert "APP_LOG_MODE=stdout" in env_lite
    assert "APP_ACCESS_LOG=false" in env_lite
    assert "ENTRYPOINT_RATE_LIMIT_BACKEND=memory" in env_lite


def test_alice_lite_compose_only_starts_postgres() -> None:
    compose_lite = (REPO_ROOT / "docker-compose.lite.yml").read_text(encoding="utf-8")

    assert "postgres:" in compose_lite
    assert "pgvector/pgvector:pg16" in compose_lite
    assert "redis:" not in compose_lite
    assert "minio:" not in compose_lite


def test_alice_lite_start_script_runs_lite_profile_and_sample_seed() -> None:
    script = (REPO_ROOT / "scripts" / "alice_lite_up.sh").read_text(encoding="utf-8")

    assert 'docker compose -f "${REPO_ROOT}/docker-compose.lite.yml" up -d' in script
    assert 'ENTRYPOINT_RATE_LIMIT_BACKEND="${ENTRYPOINT_RATE_LIMIT_BACKEND:-memory}"' in script
    assert 'APP_LOG_MODE="${APP_LOG_MODE:-stdout}"' in script
    assert 'APP_ACCESS_LOG="${APP_ACCESS_LOG:-false}"' in script
    assert '"${REPO_ROOT}/scripts/migrate.sh"' in script
    assert '"${REPO_ROOT}/scripts/load_sample_data.sh"' in script
    assert '"${REPO_ROOT}/scripts/api_dev.sh"' in script


def test_api_dev_preserves_lite_entrypoint_override() -> None:
    script = (REPO_ROOT / "scripts" / "api_dev.sh").read_text(encoding="utf-8")

    assert "ENTRYPOINT_RATE_LIMIT_BACKEND" in script
    assert "APP_LOG_MODE" in script
    assert "APP_ACCESS_LOG" in script
    assert "-m alicebot_api.local_server" in script


def test_lite_bootstrap_script_uses_workspace_bootstrap_and_one_call_brief() -> None:
    script = (REPO_ROOT / "scripts" / "bootstrap_alice_lite_workspace.py").read_text(encoding="utf-8")

    assert '"/v1/auth/magic-link/start"' in script
    assert '"/v1/workspaces"' in script
    assert '"/v1/workspaces/bootstrap"' in script
    assert '"/v1/continuity/brief"' in script
    assert '"session_token": session_token' not in script


def test_readme_and_quickstart_make_alice_lite_and_brief_the_default_path() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "quickstart" / "local-setup-and-first-result.md").read_text(
        encoding="utf-8"
    )

    for text in (readme, quickstart):
        assert "Alice Lite" in text
        assert "./scripts/alice_lite_up.sh" in text
        assert "bootstrap_alice_lite_workspace.py" in text
        assert "alicebot_api brief" in text
        assert "deployment profile" in text

    assert "Node + pnpm" not in quickstart
    assert "Hermes runtime modules" not in quickstart

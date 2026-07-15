from pathlib import Path
from types import SimpleNamespace
from typing import Any

import scripts.bootstrap_alice_lite_workspace as lite_bootstrap


REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_USER_ID = "00000000-0000-0000-0000-000000000001"
SAMPLE_THREAD_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def test_alice_lite_env_example_uses_quiet_local_runtime_defaults() -> None:
    env_lite = (REPO_ROOT / ".env.lite.example").read_text(encoding="utf-8")

    assert "APP_RELOAD=false" in env_lite
    assert "APP_LOG_MODE=stdout" in env_lite
    assert "APP_ACCESS_LOG=false" in env_lite
    assert "ENTRYPOINT_RATE_LIMIT_BACKEND" not in env_lite


def test_alice_lite_compose_only_starts_postgres() -> None:
    compose_lite = (REPO_ROOT / "docker-compose.lite.yml").read_text(encoding="utf-8")

    assert "postgres:" in compose_lite
    assert "pgvector/pgvector:pg16" in compose_lite
    assert "redis:" not in compose_lite
    assert "minio:" not in compose_lite


def test_alice_lite_start_script_uses_one_deterministic_local_identity() -> None:
    script = (REPO_ROOT / "scripts" / "alice_lite_up.sh").read_text(encoding="utf-8")

    assert 'docker compose -f "${REPO_ROOT}/docker-compose.lite.yml" up -d' in script
    assert "ENTRYPOINT_RATE_LIMIT_BACKEND" not in script
    assert 'APP_LOG_MODE="${APP_LOG_MODE:-stdout}"' in script
    assert 'APP_ACCESS_LOG="${APP_ACCESS_LOG:-false}"' in script
    assert (
        'ALICEBOT_AUTH_USER_ID="${ALICEBOT_AUTH_USER_ID:-00000000-0000-0000-0000-000000000001}"'
        in script
    )
    assert '"${REPO_ROOT}/scripts/migrate.sh"' in script
    assert '"${REPO_ROOT}/scripts/load_sample_data.sh"' in script
    assert "bootstrap_alice_lite_workspace.py --user-id ${ALICEBOT_AUTH_USER_ID}" in script
    assert '"${REPO_ROOT}/scripts/api_dev.sh"' in script


def test_api_dev_preserves_lite_logging_overrides() -> None:
    script = (REPO_ROOT / "scripts" / "api_dev.sh").read_text(encoding="utf-8")

    assert "ENTRYPOINT_RATE_LIMIT_BACKEND" not in script
    assert "APP_LOG_MODE" in script
    assert "APP_ACCESS_LOG" in script
    assert "-m alicebot_api.local_server" in script


def test_lite_bootstrap_uses_local_identity_without_hosted_crud(monkeypatch, capsys) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request_json(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        if kwargs["path"] == "/healthz":
            return {"status": "ok"}
        if kwargs["path"] == "/v1/workspaces/bootstrap":
            return {
                "workspace": {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "bootstrap_status": "ready",
                }
            }
        if kwargs["path"] == "/v1/continuity/brief":
            return {
                "brief": {
                    "summary": "Local continuity is ready.",
                    "next_suggested_action": {"title": "Continue locally"},
                    "sources": ["sample"],
                }
            }
        raise AssertionError(f"unexpected path: {kwargs['path']}")

    monkeypatch.setattr(lite_bootstrap, "_request_json", fake_request_json)
    monkeypatch.setattr(
        lite_bootstrap,
        "_parse_args",
        lambda: SimpleNamespace(
            base_url="http://127.0.0.1:8000",
            user_id=LOCAL_USER_ID,
            query="local-first startup path",
            brief_type="general",
            thread_id=SAMPLE_THREAD_ID,
        ),
    )

    assert lite_bootstrap.main() == 0
    output = capsys.readouterr().out

    assert [call["path"] for call in calls] == [
        "/healthz",
        "/v1/workspaces/bootstrap",
        "/v1/continuity/brief",
    ]
    assert calls[0]["method"] == "GET"
    assert calls[1]["user_id"] == LOCAL_USER_ID
    assert calls[1]["payload"] == {}
    assert calls[2]["user_id"] == LOCAL_USER_ID
    assert calls[2]["payload"]["thread_id"] == SAMPLE_THREAD_ID
    assert '"workspace_bootstrap_status": "ready"' in output
    assert '"brief_summary": "Local continuity is ready."' in output


def test_lite_bootstrap_has_no_hosted_auth_or_workspace_crud_side_door() -> None:
    source = (REPO_ROOT / "scripts" / "bootstrap_alice_lite_workspace.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "/v1/auth/",
        '"/v1/workspaces",',
        "session_token",
        "--email",
        "--workspace-name",
    ):
        assert forbidden not in source
    assert 'path="/v1/workspaces/bootstrap"' in source
    assert 'path="/v1/continuity/brief"' in source
    assert "X-AliceBot-User-Id" in source


def test_quickstart_keeps_alice_lite_as_a_local_deployment_profile() -> None:
    quickstart = (REPO_ROOT / "docs" / "quickstart" / "local-setup-and-first-result.md").read_text(
        encoding="utf-8"
    )

    assert "Alice Lite" in quickstart
    assert "./scripts/alice_lite_up.sh" in quickstart
    assert "/v1/workspaces/bootstrap" in quickstart
    assert "X-AliceBot-User-Id" in quickstart
    assert "alicebot_api brief" in quickstart
    assert "deployment profile" in quickstart
    assert "Node + pnpm" not in quickstart
    assert "Hermes runtime modules" not in quickstart

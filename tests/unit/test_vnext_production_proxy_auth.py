from __future__ import annotations

import asyncio
from contextlib import contextmanager
import json
from urllib.parse import urlencode
from uuid import UUID, uuid4

import pytest
from fastapi import Request, Response

import alicebot_api.main as main_module
from alicebot_api.config import Settings
from alicebot_api.vnext_agent_keys import hash_agent_key


REMOTE_CLIENT = "203.0.113.10"
TRUSTED_PROXY = "127.0.0.1"


def _request(
    path: str,
    *,
    query: dict[str, str] | None = None,
    authorization: str | None = None,
) -> Request:
    headers = [(b"x-forwarded-for", REMOTE_CLIENT.encode("ascii"))]
    if authorization is not None:
        headers.append((b"authorization", authorization.encode("ascii")))

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": urlencode(query or {}).encode("ascii"),
            "headers": headers,
            "client": (TRUSTED_PROXY, 43120),
            "server": ("alice.example.test", 443),
            "root_path": "",
        },
        receive,
    )


def _settings(
    user_id: UUID,
    *,
    legacy_v0_enabled_outside_dev: bool,
) -> Settings:
    return Settings(
        app_env="production",
        database_url="postgresql://db",
        auth_user_id=str(user_id),
        legacy_v0_enabled_outside_dev=legacy_v0_enabled_outside_dev,
        trust_proxy_headers=True,
        trusted_proxy_ips=(TRUSTED_PROXY,),
    )


@pytest.mark.parametrize("path", ["/v0/vnext", "/v0/vnext/", "/v0/vnext/projects"])
@pytest.mark.parametrize("legacy_v0_enabled_outside_dev", [False, True])
def test_remote_production_vnext_skips_only_legacy_network_gate_and_injects_user(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    legacy_v0_enabled_outside_dev: bool,
) -> None:
    user_id = uuid4()
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: _settings(
            user_id,
            legacy_v0_enabled_outside_dev=legacy_v0_enabled_outside_dev,
        ),
    )
    observed: dict[str, object] = {}

    async def call_next(request: Request) -> Response:
        observed["user_id"] = request.query_params.get("user_id")
        observed["state_user_id"] = request.state.authenticated_user_id
        return Response(status_code=204)

    response = asyncio.run(main_module.enforce_authenticated_user_identity(_request(path), call_next))

    assert response.status_code == 204
    assert observed == {
        "user_id": str(user_id),
        "state_user_id": str(user_id),
    }


def test_remote_production_vnext_still_rejects_configured_user_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: _settings(user_id, legacy_v0_enabled_outside_dev=False),
    )
    downstream_called = False

    async def call_next(_: Request) -> Response:
        nonlocal downstream_called
        downstream_called = True
        return Response(status_code=204)

    response = asyncio.run(
        main_module.enforce_authenticated_user_identity(
            _request(
                "/v0/vnext/projects",
                query={"user_id": str(uuid4())},
            ),
            call_next,
        )
    )

    assert response.status_code == 401
    assert json.loads(response.body) == {
        "detail": {
            "code": "authentication_failed",
            "message": "Authentication failed",
        }
    }
    assert downstream_called is False


@pytest.mark.parametrize(
    "path",
    [
        "/v0/vnextish",
        "/v0/vnext-preview/status",
        "/v0/threads",
    ],
)
def test_remote_production_vnext_lookalikes_and_legacy_paths_remain_disabled(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: _settings(uuid4(), legacy_v0_enabled_outside_dev=False),
    )

    async def call_next(_: Request) -> Response:
        raise AssertionError("disabled legacy paths must not reach downstream")

    response = asyncio.run(main_module.enforce_authenticated_user_identity(_request(path), call_next))

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": "legacy v0 API is disabled outside development and test"}


@pytest.mark.parametrize("path", ["/v0/vnextish", "/v0/threads"])
def test_remote_production_legacy_paths_remain_loopback_only_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: _settings(uuid4(), legacy_v0_enabled_outside_dev=True),
    )

    async def call_next(_: Request) -> Response:
        raise AssertionError("remote legacy paths must not reach downstream")

    response = asyncio.run(main_module.enforce_authenticated_user_identity(_request(path), call_next))

    assert response.status_code == 403
    assert json.loads(response.body) == {"detail": "legacy v0 API is restricted to loopback clients"}


class _ActiveKeyStore:
    def __init__(self, *, user_id: UUID, raw_key: str) -> None:
        self.record: dict[str, object] = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "agent_id": "remote-operator",
            "permission_profile": "trusted_local_agent",
            "project_scope": None,
            "key_hash": hash_agent_key(raw_key),
            "key_prefix": raw_key[:12],
            "revoked_at": None,
        }

    def count_active_agent_api_keys(self) -> int:
        return 1

    def get_agent_api_key_by_hash(self, key_hash: str) -> dict[str, object] | None:
        if key_hash == self.record["key_hash"]:
            return self.record
        return None

    def touch_agent_api_key(self, *, key_id: str) -> dict[str, object]:
        assert key_id == self.record["id"]
        return self.record


def test_remote_production_vnext_still_requires_valid_bearer_after_user_injection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    raw_key = "alice_sk_remote-production-key"
    store = _ActiveKeyStore(user_id=user_id, raw_key=raw_key)
    settings = _settings(user_id, legacy_v0_enabled_outside_dev=False)
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id: UUID):
        assert database_url == settings.database_url
        assert current_user_id == user_id
        yield object()

    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "PostgresVNextStore", lambda _conn: store)

    downstream_calls = 0

    async def downstream(_: Request) -> Response:
        nonlocal downstream_calls
        downstream_calls += 1
        return Response(status_code=204)

    async def through_vnext_auth(request: Request) -> Response:
        return await main_module._vnext_protected_http_auth(request, downstream)

    keyless = asyncio.run(
        main_module.enforce_authenticated_user_identity(
            _request("/v0/vnext/projects"),
            through_vnext_auth,
        )
    )
    keyed = asyncio.run(
        main_module.enforce_authenticated_user_identity(
            _request(
                "/v0/vnext/projects",
                authorization=f"Bearer {raw_key}",
            ),
            through_vnext_auth,
        )
    )

    assert keyless.status_code == 401
    assert json.loads(keyless.body) == {
        "detail": {
            "code": "authentication_failed",
            "message": "Authentication failed",
        }
    }
    assert keyed.status_code == 204
    assert downstream_calls == 1

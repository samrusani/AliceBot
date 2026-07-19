"""End-to-end smoke for the OpenAI Agents SDK tool example with real key auth.

Runs the example's tool functions (docs/examples/openai_agents_sdk_tool.py)
over real HTTP against the app served by uvicorn on a loopback port, backed
by a migrated per-test Postgres database. Asserts the honest auth story the
example documents: a valid write-capable key captures and recalls; a
tampered key is rejected by the server; a ``read_only_agent`` key cannot
write.
"""

from __future__ import annotations

import importlib.util
import json
import socket
import threading
import time
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
import uvicorn

import alicebot_api.main as main_module
from alicebot_api.config import Settings
from alicebot_api.config import get_settings as config_get_settings
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_agent_keys import create_agent_key
from alicebot_api.vnext_store import PostgresVNextStore

_EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "docs/examples/openai_agents_sdk_tool.py"


def _load_example() -> ModuleType:
    spec = importlib.util.spec_from_file_location("openai_agents_sdk_tool_example", _EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def live_server(migrated_database_urls, monkeypatch):
    # get_settings is @lru_cache(maxsize=1): the FIRST caller in the process
    # pins the settings for every later caller, so an earlier test that
    # resolved settings against the root database would poison this server's
    # request path (and this test would poison later ones). Clear the cache
    # on both sides of the server's lifetime and point the env at the
    # per-test database so the re-resolution lands here.
    config_get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", migrated_database_urls["app"])
    monkeypatch.setattr(
        main_module, "get_settings", lambda: Settings(database_url=migrated_database_urls["app"])
    )
    port = _free_port()
    config = uvicorn.Config(main_module.app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("uvicorn did not start within 30s")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)
    config_get_settings.cache_clear()


def _seed_user(database_url: str):
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, "owner@example.com", "Owner")
    return user_id


def _mint_key(database_url: str, user_id, *, agent_id: str, profile: str) -> str:
    with user_connection(database_url, user_id) as conn:
        _record, raw_key = create_agent_key(
            PostgresVNextStore(conn),
            user_id=user_id,
            agent_id=agent_id,
            permission_profile=profile,
        )
    return raw_key


def test_sdk_tool_functions_exercise_real_key_auth_end_to_end(
    live_server,
    migrated_database_urls,
    monkeypatch,
) -> None:
    """One server, one database, three auth scenarios.

    Scenarios share a live uvicorn instance deliberately: the app object is a
    module singleton, so serving it repeatedly against dropped databases is a
    harness artifact, not a product configuration.
    """

    example = _load_example()
    database_url = migrated_database_urls["app"]
    user_id = _seed_user(database_url)
    writer_key = _mint_key(
        database_url, user_id, agent_id="sdk-example-writer", profile="trusted_local_agent"
    )

    monkeypatch.setenv("ALICE_BASE_URL", live_server)
    monkeypatch.setenv("ALICE_USER_ID", str(user_id))

    # 1) Valid write-capable key: capture then recall the canary.
    monkeypatch.setenv("ALICE_AGENT_API_KEY", writer_key)
    import os as _os
    print(f"\nDEBUG env DATABASE_URL == migrated: {_os.environ.get('DATABASE_URL') == database_url}", flush=True)
    canary = "The SDK integration smoke canary prefers verifiable auth stories."
    captured = json.loads(example.alice_capture_memory(canary, title="SDK smoke canary"))
    assert captured["status"] in {"committed", "confirmation_required", "review_required"}, captured

    recalled = json.loads(example.alice_recall_memories("verifiable auth stories canary"))
    assert recalled["memories"], recalled
    assert any("canary" in (m["text"] or "").lower() for m in recalled["memories"]), recalled

    # 2) Tampered key: the prefix survives but the hash cannot match; the
    #    server must reject with an auth status, not accept or 500.
    tampered = writer_key[:-1] + ("x" if writer_key[-1] != "x" else "y")
    monkeypatch.setenv("ALICE_AGENT_API_KEY", tampered)
    with pytest.raises(example.AliceMemoryToolError) as excinfo:
        example.alice_capture_memory("This write must never land.")
    assert excinfo.value.status_code in {401, 403}, excinfo.value

    # 3) read_only_agent key: the server must reject the write -- either an
    #    HTTP auth error or an explicit policy rejection naming the read-only
    #    reason. Silent success is the failure mode this guards against.
    reader_key = _mint_key(
        database_url, user_id, agent_id="sdk-example-reader", profile="read_only_agent"
    )
    monkeypatch.setenv("ALICE_AGENT_API_KEY", reader_key)
    try:
        result = json.loads(example.alice_capture_memory("Read-only keys must not write."))
    except example.AliceMemoryToolError as exc:
        assert exc.status_code in {401, 403}, exc
    else:
        assert result["status"] == "rejected", result
        assert any("read_only" in str(reason) for reason in result["reasons"]), result

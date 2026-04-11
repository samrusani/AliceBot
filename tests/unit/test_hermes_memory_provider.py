from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import sys
import types
import urllib.error

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PROVIDER_PATH = (
    REPO_ROOT
    / "docs"
    / "integrations"
    / "hermes-memory-provider"
    / "plugins"
    / "memory"
    / "alice"
    / "__init__.py"
)


def _load_provider_module(monkeypatch: pytest.MonkeyPatch):
    agent_pkg = types.ModuleType("agent")
    memory_provider_pkg = types.ModuleType("agent.memory_provider")

    class _MemoryProvider:
        pass

    memory_provider_pkg.MemoryProvider = _MemoryProvider

    tools_pkg = types.ModuleType("tools")
    tools_registry_pkg = types.ModuleType("tools.registry")

    def _tool_error(message: str) -> str:
        return f"tool_error:{message}"

    tools_registry_pkg.tool_error = _tool_error

    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.memory_provider", memory_provider_pkg)
    monkeypatch.setitem(sys.modules, "tools", tools_pkg)
    monkeypatch.setitem(sys.modules, "tools.registry", tools_registry_pkg)

    module_name = "alice_memory_provider_test_module"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, PROVIDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_base_url_enforces_https_for_non_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)

    with pytest.raises(ValueError, match="https://"):
        module._normalize_base_url("http://example.com")

    assert module._normalize_base_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert module._normalize_base_url("https://alice.example.com/v0") == "https://alice.example.com"


def test_request_json_sends_user_scope_in_header_not_query(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "base_url": "http://127.0.0.1:8000",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "timeout_seconds": 8.0,
    }

    captured: dict[str, object] = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb
            return None

        def read(self) -> bytes:
            return b'{"ok": true}'

    def _fake_urlopen(request, timeout=0):  # type: ignore[no-untyped-def]
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(module.urllib.request, "urlopen", _fake_urlopen)

    result = provider._request_json(
        "GET",
        "/v0/continuity/recall",
        params={"query": "release gating"},
    )

    assert result == {"ok": True}
    assert "user_id=" not in str(captured["url"])

    headers = {str(key).lower(): str(value) for key, value in dict(captured["headers"]).items()}
    assert headers["x-alicebot-user-id"] == "00000000-0000-0000-0000-000000000001"


def test_handle_tool_call_sanitizes_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()

    def _raise_unexpected(_args):  # type: ignore[no-untyped-def]
        raise RuntimeError("database password leaked from /private/tmp/creds.txt")

    monkeypatch.setattr(provider, "_tool_recall", _raise_unexpected)

    response = provider.handle_tool_call("alice_recall", {})
    assert "internal provider error" in response
    assert "password" not in response
    assert "/private/tmp" not in response


def test_handle_tool_call_sanitizes_http_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_provider_module(monkeypatch)
    provider = module.AliceMemoryProvider()
    provider._config = {
        "base_url": "http://127.0.0.1:8000",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "timeout_seconds": 8.0,
    }

    def _fake_urlopen(_request, timeout=0):  # type: ignore[no-untyped-def]
        del timeout
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:8000/v0/continuity/recall",
            code=500,
            msg="internal error",
            hdrs=None,
            fp=io.BytesIO(b'{"detail":"db password leaked"}'),
        )

    monkeypatch.setattr(module.urllib.request, "urlopen", _fake_urlopen)
    response = provider.handle_tool_call("alice_recall", {"query": "foo"})

    assert "HTTP status 500" in response
    assert "password leaked" not in response


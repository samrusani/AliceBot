from __future__ import annotations

import ast
import asyncio
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import Response

from alicebot_api.public_errors import public_exception_response


ROOT = Path(__file__).resolve().parents[2]
MAIN_PATH = ROOT / "apps/api/src/alicebot_api/main.py"


def _payload(response: object) -> dict[str, object]:
    body = getattr(response, "body")
    assert isinstance(body, bytes)
    payload = json.loads(body)
    assert isinstance(payload, dict)
    return payload


def _request(path: str, *, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": headers or [],
            "client": ("127.0.0.1", 50000),
            "server": ("127.0.0.1", 8000),
        }
    )


def _assert_private_error(
    response: object,
    caplog: object,
    *,
    status_code: int,
    code: str,
    message: str,
    sentinel: str,
) -> None:
    assert getattr(response, "status_code") == status_code
    payload = _payload(response)
    assert payload == {"detail": {"code": code, "message": message}}
    assert sentinel not in json.dumps(payload)
    assert sentinel in caplog.text  # type: ignore[attr-defined]


def test_public_exception_response_hides_sentinel_and_logs_it(caplog: object) -> None:
    sentinel = "PUBLIC-ERROR-PRIVATE-SENTINEL-9f44"

    with caplog.at_level(logging.ERROR, logger="alicebot_api.public_errors"):  # type: ignore[attr-defined]
        response = public_exception_response(ValueError(sentinel), status_code=400)

    assert response.status_code == 400
    payload = _payload(response)
    assert payload == {"detail": {"code": "invalid_request", "message": "The request is invalid"}}
    assert sentinel not in json.dumps(payload)
    assert "ValueError" not in json.dumps(payload)
    assert sentinel in caplog.text  # type: ignore[attr-defined]
    assert "code=invalid_request status=400" in caplog.text  # type: ignore[attr-defined]


def test_public_exception_response_fails_closed_for_unregistered_status(caplog: object) -> None:
    sentinel = "PUBLIC-ERROR-UNKNOWN-STATUS-SENTINEL-a97c"

    with caplog.at_level(logging.ERROR, logger="alicebot_api.public_errors"):  # type: ignore[attr-defined]
        response = public_exception_response(RuntimeError(sentinel), status_code=418)

    assert response.status_code == 500
    assert _payload(response) == {"detail": {"code": "internal_error", "message": "An internal error occurred"}}
    assert sentinel in caplog.text  # type: ignore[attr-defined]


def test_main_has_no_exception_text_to_public_response_conversion() -> None:
    """Fail on the old direct and delayed exception-to-detail response patterns."""

    source = MAIN_PATH.read_text()
    tree = ast.parse(source)
    exception_names = {
        handler.name
        for handler in ast.walk(tree)
        if isinstance(handler, ast.ExceptHandler) and handler.name is not None
    }
    exception_names.update({"resolution_error", "execution_error", "lifecycle_error"})

    violations: list[int] = []
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        if not isinstance(call.func, ast.Name) or call.func.id not in {
            "JSONResponse",
            "_vnext_public_error_response",
        }:
            continue
        for descendant in ast.walk(call):
            if (
                isinstance(descendant, ast.Call)
                and isinstance(descendant.func, ast.Name)
                and descendant.func.id == "str"
                and descendant.args
                and isinstance(descendant.args[0], ast.Name)
                and descendant.args[0].id in exception_names
            ):
                violations.append(call.lineno)

    assert violations == []
    assert "public_exception_response(" in source
    assert source.count("public_exception_response(") == 296
    assert 'content={"detail": f"thread {thread_id} was not found"}' not in source
    assert 'content={"detail": f"provider {provider_id} was not found"}' not in source
    assert 'content={"detail": f"provider {body.provider_id} was not found"}' not in source
    assert 'content={"detail": "local workspace is not bootstrapped;' not in source
    assert "error_detail = str(exc)" not in source
    assert "ModelInvocationError(str(exc))" not in source
    assert 'error_code="conflict"' in source
    assert '"code": result.error_code' in source
    assert '"message": result.detail' in source


def test_openapi_error_schema_requires_stable_code_and_message() -> None:
    from alicebot_api.main import app

    app.openapi_schema = None
    schema = app.openapi()
    error_detail = schema["components"]["schemas"]["APIErrorDetail"]
    error_response = schema["components"]["schemas"]["APIErrorResponse"]

    assert error_detail == {
        "title": "Stable API error detail",
        "type": "object",
        "required": ["code", "message"],
        "properties": {
            "code": {"type": "string", "minLength": 1},
            "message": {"type": "string", "minLength": 1},
        },
        "additionalProperties": True,
    }
    assert error_response["properties"]["detail"]["oneOf"] == [
        {"type": "string"},
        {"$ref": "#/components/schemas/APIErrorDetail"},
        {"type": "array", "items": {}},
    ]


def test_default_vnext_handler_keeps_exception_sentinel_private(monkeypatch: object, caplog: object) -> None:
    from alicebot_api import main as main_module
    from alicebot_api.vnext_agent_control import AgentIdentityValidationError

    sentinel = "VNEXT-PRIVATE-SENTINEL-e1cb"

    def fail_identity(_request: object) -> object:
        raise AgentIdentityValidationError(sentinel)

    monkeypatch.setattr(main_module, "_vnext_agent_identity", fail_identity)  # type: ignore[attr-defined]
    with caplog.at_level(logging.ERROR, logger="alicebot_api.public_errors"):  # type: ignore[attr-defined]
        response = main_module.create_vnext_source(
            main_module.VNextSourceCaptureRequest(user_id=uuid4(), raw_text="Fact")
        )

    _assert_private_error(
        response,
        caplog,
        status_code=400,
        code="invalid_request",
        message="The request is invalid",
        sentinel=sentinel,
    )


def test_provider_handler_keeps_exception_sentinel_private(monkeypatch: object, caplog: object) -> None:
    from alicebot_api import main as main_module

    sentinel = "PROVIDER-PRIVATE-SENTINEL-58a7"

    def fail_auth(_settings: object, _request: object) -> object:
        raise ValueError(sentinel)

    monkeypatch.setattr(main_module, "_resolve_authenticated_v1_user_id", fail_auth)  # type: ignore[attr-defined]
    with caplog.at_level(logging.ERROR, logger="alicebot_api.public_errors"):  # type: ignore[attr-defined]
        response = main_module.get_v1_provider(uuid4(), _request("/v1/providers/example"))

    _assert_private_error(
        response,
        caplog,
        status_code=400,
        code="invalid_request",
        message="The request is invalid",
        sentinel=sentinel,
    )


def test_runtime_handler_keeps_exception_sentinel_private(monkeypatch: object, caplog: object) -> None:
    from alicebot_api import main as main_module

    sentinel = "RUNTIME-PRIVATE-SENTINEL-3d91"

    def fail_auth(_settings: object, _request: object) -> object:
        raise ValueError(sentinel)

    monkeypatch.setattr(main_module, "_resolve_authenticated_v1_user_id", fail_auth)  # type: ignore[attr-defined]
    request = _request(
        "/v1/runtime/invoke",
        headers=[(b"idempotency-key", b"http-hygiene-test")],
    )
    body = main_module.RuntimeInvokeRequest(
        provider_id=uuid4(),
        thread_id=uuid4(),
        message="Hello",
    )
    with caplog.at_level(logging.ERROR, logger="alicebot_api.public_errors"):  # type: ignore[attr-defined]
        response = main_module.invoke_v1_runtime(request, body)

    _assert_private_error(
        response,
        caplog,
        status_code=400,
        code="invalid_request",
        message="The request is invalid",
        sentinel=sentinel,
    )


def test_runtime_provider_value_error_keeps_exception_sentinel_private(caplog: object) -> None:
    from alicebot_api import main as main_module

    sentinel = "RUNTIME-PROVIDER-PRIVATE-SENTINEL-1c72"

    class RejectingAdapter:
        def invoke(self, **_kwargs: object) -> object:
            raise ValueError(sentinel)

    with caplog.at_level(logging.ERROR, logger="alicebot_api.main"):  # type: ignore[attr-defined]
        outcome = main_module._attempt_runtime_provider_model(
            adapter=RejectingAdapter(),  # type: ignore[arg-type]
            runtime_provider=object(),  # type: ignore[arg-type]
            settings=object(),  # type: ignore[arg-type]
            model_request=object(),  # type: ignore[arg-type]
        )

    assert outcome.response is None
    assert outcome.error is not None
    assert outcome.error_detail == "An upstream service failed"
    assert str(outcome.error) == "An upstream service failed"
    assert sentinel not in outcome.error_detail
    assert sentinel not in str(outcome.error)
    assert sentinel in caplog.text  # type: ignore[attr-defined]
    assert "code=upstream_failure status=502" in caplog.text  # type: ignore[attr-defined]


def test_runtime_model_invocation_error_keeps_exception_sentinel_private(caplog: object) -> None:
    from alicebot_api import main as main_module
    from alicebot_api.response_generation import ModelInvocationError

    sentinel = "RUNTIME-MODEL-PRIVATE-SENTINEL-845d"

    class RejectingAdapter:
        def invoke(self, **_kwargs: object) -> object:
            raise ModelInvocationError(sentinel)

    with caplog.at_level(logging.ERROR, logger="alicebot_api.main"):  # type: ignore[attr-defined]
        outcome = main_module._attempt_runtime_provider_model(
            adapter=RejectingAdapter(),  # type: ignore[arg-type]
            runtime_provider=object(),  # type: ignore[arg-type]
            settings=object(),  # type: ignore[arg-type]
            model_request=object(),  # type: ignore[arg-type]
        )

    assert outcome.response is None
    assert outcome.error is not None
    assert outcome.error_detail == "An upstream service failed"
    assert str(outcome.error) == "An upstream service failed"
    assert sentinel not in outcome.error_detail
    assert sentinel not in str(outcome.error)
    assert sentinel in caplog.text  # type: ignore[attr-defined]
    assert "code=upstream_failure status=502" in caplog.text  # type: ignore[attr-defined]


def test_auth_middleware_keeps_exception_sentinel_private(monkeypatch: object, caplog: object) -> None:
    from alicebot_api import main as main_module

    sentinel = "AUTH-MIDDLEWARE-PRIVATE-SENTINEL-b6f2"

    def fail_auth(_settings: object, _request: object) -> object:
        raise ValueError(sentinel)

    async def unexpected_call_next(_request: Request) -> Response:
        raise AssertionError("call_next must not run after an authentication failure")

    monkeypatch.setattr(main_module, "_resolve_authenticated_user_id", fail_auth)  # type: ignore[attr-defined]
    with caplog.at_level(logging.ERROR, logger="alicebot_api.public_errors"):  # type: ignore[attr-defined]
        response = asyncio.run(
            main_module.enforce_authenticated_user_identity(
                _request("/v0/vnext/workspace"),
                unexpected_call_next,
            )
        )

    _assert_private_error(
        response,
        caplog,
        status_code=401,
        code="authentication_failed",
        message="Authentication failed",
        sentinel=sentinel,
    )


def test_flag_on_legacy_handler_keeps_exception_sentinel_private_in_isolated_process() -> None:
    sentinel = "FLAG-ON-LEGACY-PRIVATE-SENTINEL-c210"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "apps/api/src")
    env["ALICE_LEGACY_SURFACES"] = "1"
    script = f"""
from contextlib import contextmanager
import json
from uuid import uuid4
from alicebot_api import main
from alicebot_api.config import Settings
from alicebot_api.memory import OpenLoopValidationError

@contextmanager
def connection(*_args, **_kwargs):
    yield object()

def fail(*_args, **_kwargs):
    raise OpenLoopValidationError({sentinel!r})

assert main.LEGACY_SURFACES_ENABLED is True
assert '/v0/open-loops' in {{route.path for route in main.app.routes}}
main.get_settings = lambda: Settings(database_url='postgresql://app')
main.user_connection = connection
main.create_open_loop_record = fail
response = main.create_open_loop(main.CreateOpenLoopRequest(user_id=uuid4(), title='Open loop'))
print(json.dumps({{'status_code': response.status_code, 'body': json.loads(response.body)}}))
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {
        "status_code": 400,
        "body": {"detail": {"code": "invalid_request", "message": "The request is invalid"}},
    }
    assert sentinel not in completed.stdout
    assert sentinel in completed.stderr

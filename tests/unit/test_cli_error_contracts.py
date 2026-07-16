from __future__ import annotations

import ast
import json

import pytest

from alicebot_api import cli as cli_module
from alicebot_api import onramp as onramp_module


def _error_record(code: str, message: str) -> str:
    return json.dumps(
        {"error": {"code": code, "message": message}},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


@pytest.mark.parametrize("script_name", ["alice", "alicebot"])
def test_postgres_cli_unhandled_failure_is_static_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    script_name: str,
) -> None:
    sentinel = f"UNIQUE_{script_name.upper()}_EXCEPTION_DETAIL"

    class Parser:
        def parse_args(self, _argv: list[str] | None) -> object:
            def fail(_ctx: object, _args: object) -> str:
                raise KeyError(sentinel)

            return type("Args", (), {"handler": staticmethod(fail)})()

    monkeypatch.setattr(cli_module, "build_parser", lambda: Parser())
    monkeypatch.setattr(cli_module, "_validate_arguments", lambda _args: None)
    monkeypatch.setattr(cli_module, "_build_context", lambda _args: object())

    assert cli_module.main(["sentinel-command"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == _error_record(
        "command_failed",
        "The command could not be completed",
    )
    assert sentinel not in captured.err
    assert "KeyError" not in captured.err
    assert "Traceback" not in captured.err


def test_postgres_cli_parse_failure_is_static_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_module.main(["definitely-not-a-command"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == _error_record(
        "invalid_request",
        "The command request is invalid",
    )
    assert "definitely-not-a-command" not in captured.err
    assert "usage:" not in captured.err


def test_sqlite_cli_unhandled_failure_is_static_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sentinel = "UNIQUE_ALICE_MEMORY_EXCEPTION_DETAIL"

    def fail(_args: object) -> int:
        raise RuntimeError(sentinel)

    monkeypatch.setattr(onramp_module, "_run_mcp", fail)

    assert onramp_module.main(["mcp"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == _error_record(
        "alice_memory_failed",
        "The alice-memory command could not be completed",
    )
    assert sentinel not in captured.err
    assert "RuntimeError" not in captured.err
    assert "Traceback" not in captured.err


def test_sqlite_cli_parse_failure_is_static_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert onramp_module.main(["export", "--not-an-option"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == _error_record(
        "invalid_request",
        "The command request is invalid",
    )
    assert "--not-an-option" not in captured.err
    assert "usage:" not in captured.err


@pytest.mark.parametrize("module", [cli_module, onramp_module])
def test_cli_sources_do_not_serialize_caught_exceptions_to_stderr_or_result_payloads(module: object) -> None:
    source_path = module.__file__
    assert source_path is not None
    source = open(source_path, encoding="utf-8").read()  # noqa: PTH123
    tree = ast.parse(source)

    exception_names = {
        handler.name
        for handler in ast.walk(tree)
        if isinstance(handler, ast.ExceptHandler) and isinstance(handler.name, str)
    }
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            writes_stderr = any(
                keyword.arg == "file"
                and isinstance(keyword.value, ast.Attribute)
                and isinstance(keyword.value.value, ast.Name)
                and keyword.value.value.id == "sys"
                and keyword.value.attr == "stderr"
                for keyword in node.keywords
            )
            if writes_stderr and any(
                isinstance(descendant, ast.Name) and descendant.id in exception_names
                for argument in node.args
                for descendant in ast.walk(argument)
            ):
                violations.append(ast.unparse(node))
        if isinstance(node, ast.Dict):
            for value in node.values:
                if any(
                    isinstance(descendant, ast.Call)
                    and isinstance(descendant.func, ast.Name)
                    and descendant.func.id in {"str", "type"}
                    and descendant.args
                    and isinstance(descendant.args[0], ast.Name)
                    and descendant.args[0].id in exception_names
                    for descendant in ast.walk(value)
                ):
                    violations.append(ast.unparse(node))

    assert violations == []

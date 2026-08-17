"""Hermes snippets that name a full-surface core tool must set the flag.

If a shipped example or the smoke include-list names alice_open_loops
(or any of the other eight) and the same env map omits
ALICE_MCP_FULL_TOOLS, this test fails. Mutation: delete
ALICE_MCP_FULL_TOOLS from
docs/integrations/examples/hermes-config.provider-plus-mcp.yaml and
this test fails.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from alicebot_api.mcp.registry import _CORE_TOOL_NAMES, _DEFAULT_CORE_TOOL_NAMES
from alicebot_api.surface_flags import mcp_full_tools_enabled


REPO_ROOT = Path(__file__).resolve().parents[2]
HERMES_EXAMPLE_DIR = REPO_ROOT / "docs" / "integrations" / "examples"
SMOKE_PATH = REPO_ROOT / "scripts" / "run_hermes_mcp_smoke.py"
FULL_SURFACE_CORE_TOOLS = _CORE_TOOL_NAMES - _DEFAULT_CORE_TOOL_NAMES


@dataclass(frozen=True)
class _HermesServerSnippet:
    source: str
    env: dict[str, str]
    tool_names: tuple[str, ...]


def _unquote(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return stripped


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_comment(line: str) -> str:
    in_quote = False
    quote = ""
    for index, char in enumerate(line):
        if in_quote:
            if char == quote:
                in_quote = False
            continue
        if char in {"'", '"'}:
            in_quote = True
            quote = char
            continue
        if char == "#":
            return line[:index].rstrip()
    return line.rstrip()


def _collect_indented_map(
    lines: list[str], start: int, base_indent: int
) -> tuple[dict[str, str], int]:
    collected: dict[str, str] = {}
    index = start
    while index < len(lines):
        raw = lines[index]
        if not raw.strip():
            index += 1
            continue
        indent = _line_indent(raw)
        if indent <= base_indent:
            break
        key, separator, value = raw.strip().partition(":")
        if separator:
            collected[key.strip()] = _unquote(value)
        index += 1
    return collected, index


def _collect_indented_list(
    lines: list[str], start: int, base_indent: int
) -> tuple[list[str], int]:
    collected: list[str] = []
    index = start
    while index < len(lines):
        raw = lines[index]
        if not raw.strip():
            index += 1
            continue
        indent = _line_indent(raw)
        if indent <= base_indent:
            break
        stripped = raw.strip()
        if stripped.startswith("- "):
            collected.append(_unquote(stripped[2:]))
        index += 1
    return collected, index


def _yaml_server_snippets(path: Path) -> list[_HermesServerSnippet]:
    lines = [_strip_comment(line) for line in path.read_text(encoding="utf-8").splitlines()]
    snippets: list[_HermesServerSnippet] = []
    in_mcp_servers = False
    mcp_indent = -1
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        indent = _line_indent(line)
        stripped = line.strip()
        if stripped.rstrip(":") == "mcp_servers":
            in_mcp_servers = True
            mcp_indent = indent
            index += 1
            continue
        if in_mcp_servers and indent <= mcp_indent:
            in_mcp_servers = False
        if in_mcp_servers and stripped.endswith(":") and indent == mcp_indent + 2:
            server_indent = indent
            env: dict[str, str] = {}
            include: list[str] = []
            index += 1
            while index < len(lines):
                child = lines[index]
                if not child.strip():
                    index += 1
                    continue
                child_indent = _line_indent(child)
                if child_indent <= server_indent:
                    break
                child_key = child.strip()
                if child_key == "env:":
                    env, index = _collect_indented_map(lines, index + 1, child_indent)
                    continue
                if child_key == "tools:":
                    tools_indent = child_indent
                    index += 1
                    while index < len(lines):
                        tool_line = lines[index]
                        if not tool_line.strip():
                            index += 1
                            continue
                        tool_indent = _line_indent(tool_line)
                        if tool_indent <= tools_indent:
                            break
                        if tool_line.strip() == "include:":
                            include, index = _collect_indented_list(
                                lines, index + 1, tool_indent
                            )
                            continue
                        index += 1
                    continue
                index += 1
            snippets.append(
                _HermesServerSnippet(
                    source=str(path.relative_to(REPO_ROOT)),
                    env=env,
                    tool_names=tuple(include),
                )
            )
            continue
        index += 1
    return snippets


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _ast_str_dict(node: ast.Dict) -> dict[str, str]:
    collected: dict[str, str] = {}
    for key_node, value_node in zip(node.keys, node.values):
        key = _const_str(key_node) if key_node is not None else None
        value = _const_str(value_node)
        if key is not None and value is not None:
            collected[key] = value
    return collected


def _ast_str_list(node: ast.List | ast.Tuple) -> list[str]:
    names: list[str] = []
    for element in node.elts:
        value = _const_str(element)
        if value is not None:
            names.append(value)
    return names


def _dict_fields(node: ast.Dict) -> dict[str, ast.AST]:
    fields: dict[str, ast.AST] = {}
    for key_node, value_node in zip(node.keys, node.values):
        key = _const_str(key_node) if key_node is not None else None
        if key is not None:
            fields[key] = value_node
    return fields


def _smoke_server_snippets(path: Path) -> list[_HermesServerSnippet]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    required: list[str] = []
    snippets: list[_HermesServerSnippet] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == "REQUIRED_HERMES_TOOL_NAMES" and isinstance(
                node.value, (ast.Tuple, ast.List)
            ):
                required = _ast_str_list(node.value)

    prefix = "mcp_alice_core_"
    required_tools = [
        name.removeprefix(prefix) if name.startswith(prefix) else name for name in required
    ]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "server_config" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for server_node in _dict_fields(node.value).values():
            if not isinstance(server_node, ast.Dict):
                continue
            fields = _dict_fields(server_node)
            env_node = fields.get("env")
            env = _ast_str_dict(env_node) if isinstance(env_node, ast.Dict) else {}
            include: list[str] = []
            tools_node = fields.get("tools")
            if isinstance(tools_node, ast.Dict):
                include_node = _dict_fields(tools_node).get("include")
                if isinstance(include_node, ast.List):
                    include = _ast_str_list(include_node)
            snippets.append(
                _HermesServerSnippet(
                    source=str(path.relative_to(REPO_ROOT)),
                    env=env,
                    tool_names=tuple(dict.fromkeys([*include, *required_tools])),
                )
            )
    return snippets


def _shipped_hermes_mcp_snippets() -> list[_HermesServerSnippet]:
    snippets: list[_HermesServerSnippet] = []
    for path in sorted(HERMES_EXAMPLE_DIR.glob("hermes-config*.yaml")):
        snippets.extend(_yaml_server_snippets(path))
    snippets.extend(_smoke_server_snippets(SMOKE_PATH))
    return snippets


def test_hermes_env_maps_set_full_tools_when_include_lists_full_surface_core_tools() -> None:
    snippets = _shipped_hermes_mcp_snippets()
    checked = [
        snippet
        for snippet in snippets
        if FULL_SURFACE_CORE_TOOLS.intersection(snippet.tool_names)
    ]
    assert checked, (
        "parser found no Hermes snippet that names a full-surface core tool; "
        "the guard is vacuous"
    )
    missing = [
        f"{snippet.source} names {sorted(FULL_SURFACE_CORE_TOOLS.intersection(snippet.tool_names))}"
        for snippet in checked
        if not mcp_full_tools_enabled(environ=snippet.env)
    ]
    assert missing == [], (
        "Hermes env map names a full-surface core tool without "
        "ALICE_MCP_FULL_TOOLS: " + "; ".join(missing)
    )

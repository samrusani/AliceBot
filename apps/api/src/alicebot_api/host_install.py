"""Write host MCP config for ``alice-memory install``.

Install writes host files. It does not import a vault, start an agent
runtime, or call ``openclaw``. Import stays a source. Commit stays a fact.
"""

from __future__ import annotations

import json
import sys
import tempfile
import tomllib
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from alicebot_api import __version__

ALICE_MEMORY_DATA_DIR_ENV = "ALICE_MEMORY_DATA_DIR"
SESSION_START_COMMAND = "alice-memory-session-start"
MCP_COMMAND = "uvx"
MCP_ARGS_PREFIX = ("alice-memory", "mcp", "--data-dir")
DEFAULT_DATA_DIR = "~/.alice"
MCPB_SUFFIX = ".mcpb"
MCPB_MANIFEST_NAME = "manifest.json"
MCPB_HOMEPAGE = "https://www.alicememory.com"
MCPB_AUTHOR_NAME = "Sami Rusani"
BRIEF_HINT = (
    "Run alice-memory brief or alice-memory-session-start --format markdown"
)

INSTALL_HOSTS = (
    "claude-desktop",
    "claude-code",
    "cursor",
    "openclaw",
    "hermes",
)
DEFAULT_INSTALL_HOSTS = (
    "claude-desktop",
    "claude-code",
    "cursor",
    "openclaw",
)

_SESSION_START_HOSTS = frozenset({"claude-code", "cursor"})


class InstallError(ValueError):
    """A user-facing install failure with a static CLI error code."""


def resolve_home(home: str | None) -> Path:
    """Resolve ``--home``. Omit it to use the process home."""

    if home is None:
        return Path.home()
    if home.startswith("~"):
        return Path(home).expanduser().resolve()
    path = Path(home)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def resolve_user_path(raw: str, home: Path) -> Path:
    """Expand ``~`` against ``home``. Do not call ``Path.expanduser``."""

    text = str(raw)
    if text == "~":
        return home.resolve()
    if text.startswith("~/") or text.startswith("~\\"):
        return (home / text[2:]).resolve()
    path = Path(text)
    if path.is_absolute():
        return path.resolve()
    return (home / path).resolve()


def claude_desktop_config_path(home: Path, platform: str | None = None) -> Path:
    plat = sys.platform if platform is None else platform
    if plat == "darwin":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if plat == "win32":
        return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    return home / ".config" / "Claude" / "claude_desktop_config.json"


def host_file_map(home: Path, platform: str | None = None) -> dict[str, dict[str, Path]]:
    """Host config paths under ``home``."""

    return {
        "claude-desktop": {"mcp": claude_desktop_config_path(home, platform)},
        "claude-code": {
            "mcp": home / ".claude.json",
            "hooks": home / ".claude" / "settings.json",
        },
        "cursor": {
            "mcp": home / ".cursor" / "mcp.json",
            "hooks": home / ".cursor" / "hooks.json",
        },
        "openclaw": {"mcp": home / ".openclaw" / "openclaw.json"},
        "hermes": {"mcp": home / ".hermes" / "config.yaml"},
    }


def mcp_server_payload(data_dir: str, *, with_env: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "command": MCP_COMMAND,
        "args": [MCP_ARGS_PREFIX[0], MCP_ARGS_PREFIX[1], MCP_ARGS_PREFIX[2], data_dir],
    }
    if with_env:
        payload["env"] = {ALICE_MEMORY_DATA_DIR_ENV: data_dir}
    return payload


def openclaw_add_line(data_dir: str) -> str:
    return (
        "openclaw mcp add alice --command uvx --arg alice-memory "
        f"--arg mcp --arg --data-dir --arg {data_dir}"
    )


def session_start_hook_entry() -> dict[str, str]:
    return {"command": SESSION_START_COMMAND}


def _is_session_start_command(command: str) -> bool:
    for part in command.split():
        if Path(part).name == SESSION_START_COMMAND:
            return True
    return False


def _contains_session_start(node: object) -> bool:
    if isinstance(node, Mapping):
        command = node.get("command")
        if isinstance(command, str) and _is_session_start_command(command):
            return True
        return any(_contains_session_start(value) for value in node.values())
    if isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
        return any(_contains_session_start(value) for value in node)
    return False


def _require_mapping(value: object, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise InstallError(f"{label} is not an object")
    return value


def _set_nested(doc: dict[str, Any], keys: tuple[str, ...], value: object) -> None:
    current: dict[str, Any] = doc
    for key in keys[:-1]:
        existing = current.get(key)
        if existing is None:
            nested: dict[str, Any] = {}
            current[key] = nested
            current = nested
            continue
        current = _require_mapping(existing, key)
    current[keys[-1]] = value


def _alice_server_keys(host: str) -> tuple[str, ...]:
    if host == "openclaw":
        return ("mcp", "servers", "alice")
    if host == "hermes":
        return ("mcp_servers", "alice")
    return ("mcpServers", "alice")


def _load_json_document(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError("host config is not valid JSON") from exc
    return _require_mapping(loaded, str(path))


def _load_yaml_document(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        loaded = load_simple_yaml(path.read_text(encoding="utf-8"))
    except (OSError, InstallError) as exc:
        raise InstallError("host config is not valid YAML") from exc
    return _require_mapping(loaded, str(path))


def _dump_json(doc: Mapping[str, Any]) -> str:
    return json.dumps(doc, ensure_ascii=True, indent=2) + "\n"


def _ensure_private_parents(path: Path) -> None:
    missing: list[Path] = []
    cursor = path.parent
    while not cursor.exists():
        missing.append(cursor)
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    if not missing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    for directory in missing:
        directory.chmod(0o700)


def _write_text(path: Path, text: str) -> None:
    _ensure_private_parents(path)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".alice-install.tmp",
        delete=False,
    )
    tmp_path = Path(handle.name)
    try:
        handle.write(text)
        handle.close()
        tmp_path.replace(path)
    except Exception:
        handle.close()
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _merge_session_start(doc: dict[str, Any], host: str) -> bool:
    """Return True when a SessionStart hook was added."""

    hooks = _require_mapping(doc.get("hooks"), "hooks")
    doc["hooks"] = hooks
    key = "SessionStart" if host == "claude-code" else "sessionStart"
    existing = hooks.get(key)
    if _contains_session_start(existing):
        return False
    entry = session_start_hook_entry()
    if existing is None:
        hooks[key] = [entry]
        return True
    if isinstance(existing, list):
        existing.append(entry)
        return True
    raise InstallError("session start hook is not a list")


def _new_hooks_document(host: str) -> dict[str, Any]:
    if host == "cursor":
        return {
            "version": 1,
            "hooks": {"sessionStart": [session_start_hook_entry()]},
        }
    return {"hooks": {"SessionStart": [session_start_hook_entry()]}}


def _merge_mcp_document(doc: dict[str, Any], host: str, data_dir: str) -> dict[str, Any]:
    payload = mcp_server_payload(data_dir, with_env=(host == "hermes"))
    _set_nested(doc, _alice_server_keys(host), payload)
    return doc


def load_simple_yaml(text: str) -> object:
    """Parse the indented YAML subset this writer emits.

    No tags, anchors, or flow collections. Unknown syntax is a hard fail.
    """

    rows: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[:indent]:
            raise InstallError("host config is not valid YAML")
        rows.append((indent, raw[indent:]))
    if not rows:
        return {}
    value, index = _parse_yaml_block(rows, 0, rows[0][0])
    if index != len(rows):
        raise InstallError("host config is not valid YAML")
    return value


def _parse_yaml_block(
    rows: list[tuple[int, str]], start: int, indent: int
) -> tuple[object, int]:
    if start >= len(rows) or rows[start][0] != indent:
        raise InstallError("host config is not valid YAML")
    if rows[start][1].startswith("- "):
        return _parse_yaml_list(rows, start, indent)
    return _parse_yaml_mapping(rows, start, indent)


def _parse_yaml_mapping(
    rows: list[tuple[int, str]], start: int, indent: int
) -> tuple[dict[str, Any], int]:
    doc: dict[str, Any] = {}
    index = start
    while index < len(rows):
        current_indent, content = rows[index]
        if current_indent < indent:
            break
        if current_indent > indent or content.startswith("- "):
            raise InstallError("host config is not valid YAML")
        key, sep, rest = content.partition(":")
        if not sep or not key or key.startswith("- ") or key[0] in " \t":
            raise InstallError("host config is not valid YAML")
        key = _parse_yaml_scalar(key.strip())
        if not isinstance(key, str):
            raise InstallError("host config is not valid YAML")
        rest = rest.strip()
        index += 1
        if rest:
            doc[key] = _parse_yaml_scalar(rest)
            continue
        if index >= len(rows) or rows[index][0] <= indent:
            doc[key] = {}
            continue
        nested, index = _parse_yaml_block(rows, index, rows[index][0])
        doc[key] = nested
    return doc, index


def _parse_yaml_list(
    rows: list[tuple[int, str]], start: int, indent: int
) -> tuple[list[object], int]:
    items: list[object] = []
    index = start
    while index < len(rows):
        current_indent, content = rows[index]
        if current_indent < indent:
            break
        if current_indent != indent or not content.startswith("- "):
            raise InstallError("host config is not valid YAML")
        rest = content[2:].strip()
        index += 1
        if rest:
            items.append(_parse_yaml_scalar(rest))
            continue
        if index >= len(rows) or rows[index][0] <= indent:
            items.append({})
            continue
        nested, index = _parse_yaml_block(rows, index, rows[index][0])
        items.append(nested)
    return items, index


def _parse_yaml_scalar(text: str) -> object:
    if text == "{}":
        return {}
    if text == "[]":
        return []
    if text in {"null", "~"}:
        return None
    if text in {"true", "True"}:
        return True
    if text in {"false", "False"}:
        return False
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        inner = text[1:-1]
        if text[0] == '"':
            return (
                inner.replace("\\\\", "\\")
                .replace("\\n", "\n")
                .replace("\\\"", '"')
            )
        return inner
    if text.startswith(("'", '"')):
        raise InstallError("host config is not valid YAML")
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def dump_simple_yaml(data: object) -> str:
    body = _emit_yaml(data, indent=0)
    return body if body.endswith("\n") else body + "\n"


def _emit_yaml(data: object, indent: int) -> str:
    pad = "  " * indent
    if isinstance(data, dict):
        if not data:
            return "{}\n" if indent == 0 else ""
        chunks: list[str] = []
        for key, value in data.items():
            if not isinstance(key, str):
                raise InstallError("host config is not valid YAML")
            rendered_key = _format_yaml_scalar(key)
            chunks.append(_emit_yaml_item(pad, rendered_key, value, indent))
        return "".join(chunks)
    if isinstance(data, list):
        if not data:
            return "[]\n" if indent == 0 else ""
        chunks = []
        for item in data:
            if isinstance(item, (dict, list)):
                chunks.append(f"{pad}-\n{_emit_yaml(item, indent + 1)}")
            else:
                chunks.append(f"{pad}- {_format_yaml_scalar(item)}\n")
        return "".join(chunks)
    return f"{_format_yaml_scalar(data)}\n"


def _emit_yaml_item(pad: str, key: str, value: object, indent: int) -> str:
    if isinstance(value, dict):
        if not value:
            return f"{pad}{key}: {{}}\n"
        return f"{pad}{key}:\n{_emit_yaml(value, indent + 1)}"
    if isinstance(value, list):
        if not value:
            return f"{pad}{key}: []\n"
        return f"{pad}{key}:\n{_emit_yaml(value, indent + 1)}"
    return f"{pad}{key}: {_format_yaml_scalar(value)}\n"


def _format_yaml_scalar(value: object) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    text = str(value)
    if _yaml_needs_quotes(text):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return text


def _yaml_needs_quotes(text: str) -> bool:
    if text == "" or text in {
        "true",
        "false",
        "null",
        "True",
        "False",
        "yes",
        "no",
        "on",
        "off",
        "~",
    }:
        return True
    if text[0] in " \t-?:{}[]&*!|>'\"%@`":
        return True
    if any(marker in text for marker in (": ", " #", "\n", "\r", '"', "'", "\\")):
        return True
    try:
        float(text)
        return True
    except ValueError:
        return False


def _package_version() -> str:
    if __version__ and "+source" not in __version__:
        return __version__
    for parent in Path(__file__).resolve().parents:
        pyproject = parent / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            loaded = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            break
        version = loaded.get("project", {}).get("version")
        if isinstance(version, str) and version:
            return version
        break
    committed = committed_mcpb_manifest_path()
    if committed is not None:
        try:
            loaded_manifest = json.loads(committed.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded_manifest = None
        if isinstance(loaded_manifest, Mapping):
            version = loaded_manifest.get("version")
            if isinstance(version, str) and version:
                return version
    return "0.0.0"


def committed_mcpb_manifest_path() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "packaging" / "mcpb" / MCPB_MANIFEST_NAME
        if candidate.is_file():
            return candidate
    return None


def build_mcpb_manifest(version: str | None = None) -> dict[str, object]:
    resolved = version or _package_version()
    return {
        "manifest_version": "0.3",
        "name": "alice-memory",
        "display_name": "Alice Memory",
        "version": resolved,
        "description": (
            "Local-first memory for AI agents. Import is a source. Commit is a fact."
        ),
        "author": {"name": MCPB_AUTHOR_NAME, "url": MCPB_HOMEPAGE},
        "homepage": MCPB_HOMEPAGE,
        "server": {
            "type": "binary",
            "entry_point": "uvx",
            "mcp_config": {
                "command": "uvx",
                "args": [
                    "alice-memory",
                    "mcp",
                    "--data-dir",
                    "${user_config.data_dir}",
                ],
            },
        },
        "user_config": {
            "data_dir": {
                "type": "directory",
                "title": "Alice data directory",
                "description": "Local SQLite vault directory. Defaults to ~/.alice.",
                "default": "${HOME}/.alice",
                "required": False,
            }
        },
    }


def write_mcpb_bundle(path: Path, *, dry_run: bool) -> str:
    target = Path(path)
    if target.suffix != MCPB_SUFFIX:
        raise InstallError("mcpb path must end in .mcpb")
    if target.exists() and target.is_dir():
        raise InstallError("mcpb path is a directory")
    manifest = build_mcpb_manifest()
    snippet = _dump_json(manifest)
    if dry_run:
        return "\n".join(
            (
                f"mcpb: {target}",
                "action: dry-run",
                "snippet:",
                snippet.rstrip(),
            )
        )
    _ensure_private_parents(target)
    try:
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MCPB_MANIFEST_NAME, snippet)
    except OSError as exc:
        raise InstallError("mcpb zip could not be written") from exc
    return "\n".join((f"mcpb: {target}", "action: written"))


def _plan_hosts(hosts: Sequence[str] | None) -> list[str]:
    if not hosts:
        return list(DEFAULT_INSTALL_HOSTS)
    planned: list[str] = []
    seen: set[str] = set()
    for host in hosts:
        if host not in INSTALL_HOSTS:
            raise InstallError("unknown host")
        if host in seen:
            continue
        seen.add(host)
        planned.append(host)
    return planned


def _format_host_receipt(
    *,
    host: str,
    mcp_path: Path,
    hooks_path: Path | None,
    action: str,
    session_start: str,
    snippet: str | None,
    data_dir: str,
) -> str:
    lines = [
        f"host: {host}",
        f"path: {mcp_path}",
        f"action: {action}",
        f"session_start: {session_start}",
    ]
    if hooks_path is not None:
        lines.append(f"session_start_path: {hooks_path}")
    if host in {"openclaw", "hermes"}:
        lines.append(f"note: {BRIEF_HINT}")
    if snippet is not None:
        lines.append("snippet:")
        lines.append(snippet.rstrip())
    if host == "openclaw":
        lines.append(openclaw_add_line(data_dir))
    return "\n".join(lines)


def _write_host(
    host: str,
    *,
    home: Path,
    data_dir: str,
    dry_run: bool,
) -> str:
    files = host_file_map(home)[host]
    mcp_path = files["mcp"]
    hooks_path = files.get("hooks")
    loader = _load_yaml_document if host == "hermes" else _load_json_document
    dumper = dump_simple_yaml if host == "hermes" else _dump_json

    mcp_doc = loader(mcp_path)
    _merge_mcp_document(mcp_doc, host, data_dir)
    mcp_text = dumper(mcp_doc)

    session_start = "none"
    hooks_text: str | None = None
    if host in _SESSION_START_HOSTS and hooks_path is not None:
        hooks_doc = _load_json_document(hooks_path)
        if not hooks_doc:
            hooks_doc = _new_hooks_document(host)
            added = True
        else:
            added = _merge_session_start(hooks_doc, host)
        session_start = "planned" if dry_run else ("added" if added else "already-present")
        hooks_text = _dump_json(hooks_doc)

    action = "dry-run" if dry_run else "written"
    snippet = mcp_text if dry_run else None
    if dry_run and hooks_text is not None:
        snippet = f"{mcp_text.rstrip()}\n---\n{hooks_text.rstrip()}\n"

    if not dry_run:
        _write_text(mcp_path, mcp_text)
        if hooks_path is not None and hooks_text is not None:
            _write_text(hooks_path, hooks_text)

    return _format_host_receipt(
        host=host,
        mcp_path=mcp_path,
        hooks_path=hooks_path,
        action=action,
        session_start=session_start,
        snippet=snippet,
        data_dir=data_dir,
    )


def run_host_install(
    *,
    home: str | None,
    data_dir: str,
    hosts: Sequence[str] | None,
    dry_run: bool,
    write_mcpb: str | None,
) -> str:
    resolved_home = resolve_home(home)
    resolved_data_dir = str(resolve_user_path(data_dir, resolved_home))
    planned = _plan_hosts(hosts)
    blocks: list[str] = []
    try:
        for host in planned:
            blocks.append(
                _write_host(
                    host,
                    home=resolved_home,
                    data_dir=resolved_data_dir,
                    dry_run=dry_run,
                )
            )
        if write_mcpb:
            blocks.append(write_mcpb_bundle(Path(write_mcpb), dry_run=dry_run))
    except OSError as exc:
        raise InstallError("host config could not be written") from exc
    return "\n\n".join(blocks)


__all__ = [
    "ALICE_MEMORY_DATA_DIR_ENV",
    "BRIEF_HINT",
    "DEFAULT_INSTALL_HOSTS",
    "INSTALL_HOSTS",
    "InstallError",
    "SESSION_START_COMMAND",
    "build_mcpb_manifest",
    "claude_desktop_config_path",
    "committed_mcpb_manifest_path",
    "dump_simple_yaml",
    "host_file_map",
    "load_simple_yaml",
    "mcp_server_payload",
    "openclaw_add_line",
    "resolve_home",
    "resolve_user_path",
    "run_host_install",
    "write_mcpb_bundle",
]

"""Host session-start wrapper around ``alice-memory brief``.

Cursor ``sessionStart`` and Claude Code ``SessionStart`` both consume
this process. Stdout is JSON with ``additional_context`` (Cursor) and
``hookSpecificOutput.additionalContext`` (Claude Code). OpenClaw can
run the same command with ``--format markdown``, or call
``alice-memory brief`` and read the markdown on stdout.

Fail open: JSON writes ``{}`` and exits 0. After ``--format markdown``
is known, fail-open is a single blank line and exit 0. If argparse
fails before format is known, ``{}`` is still correct for the default
JSON host. Never failClosed. Never print MCP protocol on stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

ALICE_MEMORY_DATA_DIR_ENV = "ALICE_MEMORY_DATA_DIR"
DEFAULT_DATA_DIR = "~/.alice"
_BRIEF_TIMEOUT_SECONDS = 30


def _fail_open(output_format: str | None = None) -> None:
    if output_format == "markdown":
        sys.stdout.write("\n")
        sys.stdout.flush()
        return
    sys.stdout.write("{}\n")
    sys.stdout.flush()


def _emit_context(markdown: str, *, output_format: str) -> None:
    if output_format == "markdown":
        sys.stdout.write(markdown)
        if markdown and not markdown.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
        return
    payload = {
        "additional_context": markdown,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": markdown,
        },
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def _looks_like_mcp(text: str) -> bool:
    return "jsonrpc" in text or "Content-Length:" in text


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    output_format: str | None = None
    try:
        args = _parse_args(raw)
        output_format = args.format
        return _run(args)
    except SystemExit as exc:
        if exc.code in (0, None):
            raise
        _fail_open(output_format)
        return 0
    except Exception:
        _fail_open(output_format)
        return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="alice-memory-session-start",
        description=(
            "Read a host session-start payload on stdin and print a session "
            "brief for injection. JSON failures write {} and exit 0. "
            "Markdown failures write a blank line and exit 0."
        ),
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help=(
            f"Vault directory. Defaults to ${ALICE_MEMORY_DATA_DIR_ENV} or "
            f"{DEFAULT_DATA_DIR}."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="json for Cursor/Claude Code; markdown for hosts that want the brief text.",
    )
    return parser.parse_args(argv)


def _run(args: argparse.Namespace) -> int:
    try:
        sys.stdin.read()
    except Exception:
        pass

    data_dir = args.data_dir or os.environ.get(ALICE_MEMORY_DATA_DIR_ENV) or DEFAULT_DATA_DIR
    command = shutil.which("alice-memory")
    if command is None:
        _fail_open(args.format)
        return 0
    completed = subprocess.run(
        [command, "brief", "--data-dir", data_dir],
        check=False,
        capture_output=True,
        text=True,
        timeout=_BRIEF_TIMEOUT_SECONDS,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode != 0 or _looks_like_mcp(completed.stdout):
        _fail_open(args.format)
        return 0
    _emit_context(completed.stdout.rstrip("\n"), output_format=args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

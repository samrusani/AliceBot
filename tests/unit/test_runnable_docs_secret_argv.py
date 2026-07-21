from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL_FENCE_PATTERN = re.compile(r"```(?:bash|sh|shell|zsh)\s*\n(.*?)```", re.DOTALL)
SHELL_LINE_CONTINUATION_PATTERN = re.compile(r"\\\r?\n[ \t]*")
HEADER_ARGUMENT_PATTERN = re.compile(
    r"(?:^|[ \t])(?:-H|--header(?:[ \t]*=)?)[ \t]*"
    r"(?P<header>\"[^\"\n]*\"|'[^'\n]*'|[^ \t\n]+)",
)
AGENT_KEY_EXPANSION_PATTERN = re.compile(
    r"(?:\$ALICE_AGENT_API_KEY|\$\{ALICE_AGENT_API_KEY\})",
)


def _expands_agent_key_in_header_argument(block: str) -> bool:
    logical_block = SHELL_LINE_CONTINUATION_PATTERN.sub(" ", block)
    return any(
        AGENT_KEY_EXPANSION_PATTERN.search(match.group("header"))
        for match in HEADER_ARGUMENT_PATTERN.finditer(logical_block)
    )


def test_agent_key_header_detector_rejects_attached_and_continued_arguments() -> None:
    fail_on_old_blocks = (
        'curl -H"Authorization: Bearer $ALICE_AGENT_API_KEY" https://alice.example.com',
        'curl -H \\\n  "Authorization: Bearer ${ALICE_AGENT_API_KEY}" https://alice.example.com',
    )

    assert all(_expands_agent_key_in_header_argument(block) for block in fail_on_old_blocks)


def test_runnable_docs_do_not_expand_agent_keys_into_header_arguments() -> None:
    offenders: list[str] = []
    for path in sorted((REPO_ROOT / "docs").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for block in SHELL_FENCE_PATTERN.findall(text):
            if _expands_agent_key_in_header_argument(block):
                offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []

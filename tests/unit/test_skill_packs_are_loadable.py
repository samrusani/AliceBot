"""The skill packs must be in the shape their hosts actually load.

Verified against a real OpenClaw 2026.8.1 checkout on 2026-08-15 by putting three variants of
the same pack side by side in its managed skills directory and asking it what it loaded:

    DROPPED  alice-project-memory-skill.md   (the shape we had been shipping)
    DROPPED  SKILL.md, no frontmatter
    LOADED   SKILL.md + frontmatter          modelVisible=true

The drop is silent. A file whose name is not `SKILL.md` is never a candidate, and a file with
no frontmatter parses to an empty record with zero issues, so nothing is logged at any level.
We shipped two packs in the dropped shape and had no way to notice.

Hermes uses the same convention: its own bundled skills are `<skill-name>/SKILL.md` with
`name` and `description` in YAML frontmatter.

`description` is doubly load-bearing. The host puts only name and description in the system
prompt, so the model decides from the description alone whether to read the body. A pack that
loads but describes itself badly is invisible in practice.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]

SKILL_PACK_ROOT = REPO_ROOT / "agent-skills"

# Enough to be useful in a system prompt where it is the only thing the model sees.
MINIMUM_DESCRIPTION_LENGTH = 40


def _skill_files() -> list[Path]:
    return sorted(SKILL_PACK_ROOT.rglob("*.md"))


def _frontmatter(path: Path) -> dict[str, str] | None:
    body = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", body, re.S)
    if not match:
        return None
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def test_the_skill_pack_directory_is_not_empty() -> None:
    """Guards against the whole check quietly becoming vacuous."""

    assert _skill_files(), f"no skill packs found under {SKILL_PACK_ROOT}"


@pytest.mark.parametrize("path", _skill_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_every_shipped_skill_markdown_is_named_skill_md(path: Path) -> None:
    assert path.name == "SKILL.md", (
        f"{path.relative_to(REPO_ROOT)} will never be loaded. Hosts join the literal filename "
        "'SKILL.md' inside a skill directory; any other name is not a candidate and is dropped "
        "with no warning. Move it to <skill-name>/SKILL.md."
    )


@pytest.mark.parametrize("path", _skill_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_every_shipped_skill_has_loadable_frontmatter(path: Path) -> None:
    fields = _frontmatter(path)
    assert fields is not None, (
        f"{path.relative_to(REPO_ROOT)} has no YAML frontmatter. Without it the host parses an "
        "empty record, reports zero issues, and drops the skill silently."
    )
    for required in ("name", "description"):
        assert fields.get(required), (
            f"{path.relative_to(REPO_ROOT)} frontmatter is missing a non-empty {required!r}. "
            "Both are required for the skill to load."
        )


@pytest.mark.parametrize("path", _skill_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_skill_description_is_substantial_enough_to_be_chosen(path: Path) -> None:
    fields = _frontmatter(path) or {}
    description = fields.get("description", "")
    assert len(description) >= MINIMUM_DESCRIPTION_LENGTH, (
        f"{path.relative_to(REPO_ROOT)} description is {len(description)} chars. The host puts "
        "only name and description in the system prompt, so the model decides from the "
        "description alone whether to read the body. Say when to load it."
    )


@pytest.mark.parametrize("path", _skill_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_skill_directory_name_matches_the_declared_name(path: Path) -> None:
    """`name` falls back to the directory basename, so a mismatch is a silent rename."""

    fields = _frontmatter(path) or {}
    assert fields.get("name") == path.parent.name, (
        f"{path.relative_to(REPO_ROOT)} declares name={fields.get('name')!r} but sits in "
        f"{path.parent.name!r}. Hosts key skills by name and fall back to the directory "
        "basename, so a mismatch makes the pack answer to two different identities."
    )


@pytest.mark.parametrize("path", _skill_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_skill_does_not_instruct_an_impossible_open_loop_create(path: Path) -> None:
    """`alice_open_loops` reads and closes loops. It has never created one.

    The OpenClaw pack told agents to "create open loops for unresolved work with
    alice_open_loops". Its action enum is list/close/edit/reopen/snooze, so every attempt
    errors on the enum.
    """

    from alicebot_api.mcp.registry import _TOOL_DEFINITIONS_BY_NAME

    actions = set(
        (_TOOL_DEFINITIONS_BY_NAME["alice_open_loops"]["inputSchema"]["properties"]["action"])
        .get("enum")
        or []
    )
    assert "create" not in actions, (
        "alice_open_loops gained a create action; this guard and the skill packs should be "
        "revisited together."
    )

    body = " ".join(path.read_text(encoding="utf-8").replace("`", "").split()).lower()
    assert "create open loops" not in body, (
        f"{path.relative_to(REPO_ROOT)} tells an agent to create open loops with "
        f"alice_open_loops, whose actions are {sorted(actions)}. Commit the item with "
        "alice_memory_commit and memory_type 'open_loop' instead."
    )

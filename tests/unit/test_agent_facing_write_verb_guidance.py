"""The agent-facing docs must steer the write verbs the same way the tools do.

`v0.15.4` corrected the shipped `alice_memory_commit` and `alice_capture`
descriptions because the old wording told agents to wait to be asked before
recording anything, and pointed ambient writes at a review-gated tool whose
content `alice_recall` never returns. The correction landed in
`definitions.py`, but five agent-facing documents kept the retired steer for a
release. Skill packs are pasted straight into an agent's prompt, so a stale one
overrides the corrected tool description at the point it matters most.

This guard fails on the source of truth first, so a revert in `definitions.py`
is reported as the cause rather than as five doc failures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alicebot_api.mcp.definitions import _CORE_TOOL_DEFINITIONS


REPO_ROOT = Path(__file__).resolve().parents[2]

# Every file an agent may read and act on when deciding which write verb to use.
AGENT_FACING_WRITE_VERB_DOCS = (
    "docs/alpha/mcp-tools.md",
    "docs/alpha/agent-integration.md",
    "docs/alpha/hermes-skill.md",
    "docs/alpha/openclaw-skill.md",
    "agent-skills/hermes/alice-memory/SKILL.md",
    "agent-skills/openclaw/alice-project-memory/SKILL.md",
)

# Wording retired in v0.15.4. Each of these makes an explicit user instruction
# the precondition for committing, which is the behaviour the release fixed.
RETIRED_COMMIT_GATES = (
    "only when the user directly asks",
    "when the user explicitly says to remember",
    "only for explicit user-directed project facts",
    "write one explicit memory on the user's instruction",
)


def _read(relative_path: str) -> str:
    """Prose normalised for meaning, not formatting.

    These phrases are wrapped across lines and carry markdown emphasis, so a
    raw substring check would fail on a line break or a pair of backticks and
    pass once someone reflowed the paragraph. Strip both.
    """

    body = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    return " ".join(body.replace("`", "").replace("*", "").split()).lower()


def _description(tool_name: str) -> str:
    for tool in _CORE_TOOL_DEFINITIONS:
        if tool["name"] == tool_name:
            return str(tool["description"])
    raise AssertionError(f"{tool_name} is missing from the core tool definitions")


def test_shipped_descriptions_still_carry_the_v0154_correction() -> None:
    """The source of truth the docs are checked against."""

    commit = _description("alice_memory_commit").lower()
    assert "has not asked" in commit, "alice_memory_commit no longer permits an unasked commit"
    assert "immediately recallable" in commit

    capture = _description("alice_capture").lower()
    assert "alice_recall will not return it" in capture, "alice_capture no longer warns that recall skips it"


@pytest.mark.parametrize("relative_path", AGENT_FACING_WRITE_VERB_DOCS)
def test_agent_facing_docs_do_not_gate_commits_on_being_asked(relative_path: str) -> None:
    body = _read(relative_path)
    for retired in RETIRED_COMMIT_GATES:
        assert retired not in body, f"{relative_path} still gates alice_memory_commit on {retired!r}"


@pytest.mark.parametrize(
    "relative_path",
    (
        "docs/alpha/mcp-tools.md",
        "docs/alpha/hermes-skill.md",
        "docs/alpha/openclaw-skill.md",
        "agent-skills/hermes/alice-memory/SKILL.md",
        "agent-skills/openclaw/alice-project-memory/SKILL.md",
    ),
)
def test_agent_facing_docs_permit_the_unasked_commit(relative_path: str) -> None:
    body = _read(relative_path)
    assert "has not asked" in body, f"{relative_path} never tells an agent it may commit unasked"


@pytest.mark.parametrize(
    "relative_path",
    (
        "docs/alpha/mcp-tools.md",
        "docs/alpha/hermes-skill.md",
        "docs/alpha/openclaw-skill.md",
        "agent-skills/hermes/alice-memory/SKILL.md",
        "agent-skills/openclaw/alice-project-memory/SKILL.md",
    ),
)
def test_agent_facing_docs_warn_that_capture_is_not_recallable(relative_path: str) -> None:
    body = _read(relative_path)
    assert "alice_recall will not return it" in body, (
        f"{relative_path} describes alice_capture without warning that recall skips it"
    )

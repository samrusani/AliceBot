from __future__ import annotations

import json
from pathlib import Path

import pytest

from alicebot_api.chatgpt_import import ChatGPTImportValidationError, load_chatgpt_payload
from alicebot_api.markdown_import import MarkdownImportValidationError, load_markdown_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_FIXTURE = REPO_ROOT / "fixtures" / "importers" / "markdown" / "workspace_v1.md"
CHATGPT_FIXTURE = REPO_ROOT / "fixtures" / "importers" / "chatgpt" / "workspace_v1.json"


def test_markdown_adapter_loads_fixture_with_deterministic_mapping() -> None:
    first = load_markdown_payload(MARKDOWN_FIXTURE)
    second = load_markdown_payload(MARKDOWN_FIXTURE)

    assert first.context.fixture_id == "markdown-s37-workspace-v1"
    assert first.context.workspace_id == "markdown-workspace-demo-001"
    assert first.context.workspace_name == "Markdown Import Demo"
    assert len(first.items) == 5

    first_item = first.items[0]
    assert first_item.object_type == "Decision"
    assert first_item.status == "active"
    assert first_item.body["decision_text"] == "Keep markdown importer deterministic for baseline evidence."
    assert first_item.source_provenance["project"] == "Markdown Import Project"

    assert [item.dedupe_key for item in first.items] == [item.dedupe_key for item in second.items]


def test_markdown_adapter_rejects_unclosed_frontmatter(tmp_path: Path) -> None:
    source = tmp_path / "broken.md"
    source.write_text("---\nfixture_id: x\n- Decision: broken\n", encoding="utf-8")

    with pytest.raises(MarkdownImportValidationError, match="frontmatter"):
        load_markdown_payload(source)


def test_chatgpt_adapter_loads_fixture_with_deterministic_mapping() -> None:
    first = load_chatgpt_payload(CHATGPT_FIXTURE)
    second = load_chatgpt_payload(CHATGPT_FIXTURE)

    assert first.context.fixture_id == "chatgpt-s37-workspace-v1"
    assert first.context.workspace_id == "chatgpt-workspace-demo-001"
    assert first.context.workspace_name == "ChatGPT Import Demo"
    assert len(first.items) == 5

    first_item = first.items[0]
    assert first_item.object_type == "Decision"
    assert first_item.status == "active"
    assert first_item.body["decision_text"] == "Keep ChatGPT import provenance explicit for every message."
    assert first_item.source_provenance["project"] == "ChatGPT Import Project"

    assert [item.dedupe_key for item in first.items] == [item.dedupe_key for item in second.items]


def test_chatgpt_adapter_rejects_invalid_payload(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps({"workspace": {"id": "x"}}), encoding="utf-8")

    with pytest.raises(ChatGPTImportValidationError, match="must include one of"):
        load_chatgpt_payload(source)

from __future__ import annotations

import json
from pathlib import Path

import pytest

from alicebot_api.openclaw_adapter import OpenClawAdapterValidationError, load_openclaw_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "fixtures" / "openclaw" / "workspace_v1.json"


def test_openclaw_adapter_loads_fixture_with_deterministic_mapping() -> None:
    batch = load_openclaw_payload(FIXTURE_PATH)

    assert batch.context.fixture_id == "openclaw-s36-workspace-v1"
    assert batch.context.workspace_id == "openclaw-workspace-demo-001"
    assert batch.context.workspace_name == "OpenClaw Interop Demo"
    assert len(batch.items) == 5

    first = batch.items[0]
    assert first.source_item_id == "oc-memory-001"
    assert first.object_type == "Decision"
    assert first.status == "active"
    assert first.raw_content == "Decision: Keep MCP tool surface narrow during Phase 9 interop rollout."
    assert first.title == "Decision: Keep MCP tool surface narrow during Phase 9 interop rollout."
    assert first.body["decision_text"] == "Keep MCP tool surface narrow during Phase 9 interop rollout."
    assert first.source_provenance["thread_id"] == "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    assert first.source_provenance["task_id"] == "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    assert first.source_provenance["project"] == "Alice Public Core"
    assert first.source_provenance["person"] == "Interop Owner"
    assert first.source_provenance["source_event_ids"] == ["openclaw-event-0001"]
    assert first.confidence == 0.97
    assert len(first.dedupe_key) == 64


def test_openclaw_adapter_emits_stable_dedupe_keys() -> None:
    first = load_openclaw_payload(FIXTURE_PATH)
    second = load_openclaw_payload(FIXTURE_PATH)

    assert [item.dedupe_key for item in first.items] == [item.dedupe_key for item in second.items]


def test_openclaw_adapter_supports_directory_workspace_contract(tmp_path: Path) -> None:
    workspace_payload = {
        "workspace": {
            "id": "oc-ws-dir-1",
            "name": "Directory Workspace",
        }
    }
    memory_payload = {
        "durable_memory": [
            {
                "id": "oc-dir-001",
                "type": "next_action",
                "content": "Ship directory contract parsing.",
                "thread_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            }
        ]
    }

    (tmp_path / "workspace.json").write_text(json.dumps(workspace_payload), encoding="utf-8")
    (tmp_path / "durable_memory.json").write_text(json.dumps(memory_payload), encoding="utf-8")

    batch = load_openclaw_payload(tmp_path)

    assert batch.context.workspace_id == "oc-ws-dir-1"
    assert batch.context.workspace_name == "Directory Workspace"
    assert len(batch.items) == 1
    assert batch.items[0].object_type == "NextAction"


def test_openclaw_adapter_rejects_invalid_payload() -> None:
    with pytest.raises(OpenClawAdapterValidationError, match="invalid JSON"):
        load_openclaw_payload(REPO_ROOT / "pyproject.toml")


def test_openclaw_adapter_rejects_unknown_status_value(tmp_path: Path) -> None:
    payload = {
        "workspace": {
            "id": "oc-ws-status-1",
            "name": "Status Validation Workspace",
        },
        "durable_memory": [
            {
                "id": "oc-status-001",
                "type": "decision",
                "status": "paused",
                "content": "Do not silently coerce unknown statuses.",
            }
        ],
    }
    source = tmp_path / "workspace.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(OpenClawAdapterValidationError, match="status must be one of"):
        load_openclaw_payload(source)

from __future__ import annotations

from alicebot_api.vnext_project_scope import canonical_memory_metadata, memory_project_scope


def test_legacy_nested_agentic_scope_precedes_singular_project_fallbacks() -> None:
    memory = {
        "project_id": "stale-singular-project",
        "metadata_json": {
            "project_id": "stale-metadata-project",
            "agentic_memory": {
                "project_scope": [" alicebot ", "hermes", "alicebot"],
            },
        },
    }

    assert memory_project_scope(memory) == ("alicebot", "hermes")
    assert canonical_memory_metadata(memory)["project_scope"] == ["alicebot", "hermes"]


def test_canonical_top_level_scope_cannot_be_widened_by_stale_nested_scope() -> None:
    memory = {
        "project_id": "alicebot",
        "metadata_json": {
            "project_scope": ["alicebot"],
            "agentic_memory": {"project_scope": ["alicebot", "stale-other-project"]},
        },
    }

    assert memory_project_scope(memory) == ("alicebot",)


def test_explicit_empty_canonical_scope_suppresses_all_legacy_fallbacks() -> None:
    memory = {
        "project_scope": [],
        "project_id": "stale-singular-project",
        "metadata_json": {
            "project_scope": ["stale-metadata-project"],
            "project_id": "stale-metadata-project",
            "agentic_memory": {"project_scope": ["stale-nested-project"]},
        },
    }

    assert memory_project_scope(memory) == ()
    assert canonical_memory_metadata(memory)["project_scope"] == []


def test_explicit_empty_metadata_scope_suppresses_singular_and_nested_fallbacks() -> None:
    memory = {
        "project_id": "stale-singular-project",
        "metadata_json": {
            "project_scope": [],
            "project_id": "stale-metadata-project",
            "agentic_memory": {"project_scope": ["stale-nested-project"]},
        },
    }

    assert memory_project_scope(memory) == ()
    assert canonical_memory_metadata(memory)["project_scope"] == []

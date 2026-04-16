from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_reference_path_guide_links_major_integration_routes() -> None:
    guide = (REPO_ROOT / "docs" / "integrations" / "reference-paths.md").read_text(encoding="utf-8")

    assert "POST /v1/continuity/brief" in guide
    assert "scripts/run_hermes_bridge_demo.py" in guide
    assert "scripts/use_alice_with_openclaw.sh" in guide
    assert "phase14-provider-configuration.md" in guide
    assert "three major adoption paths in this sprint" in guide


def test_hermes_reference_doc_centers_provider_plus_mcp_and_one_call_continuity() -> None:
    hermes_doc = (REPO_ROOT / "docs" / "integrations" / "hermes.md").read_text(encoding="utf-8")

    assert "provider_plus_mcp" in hermes_doc
    assert "alice_brief" in hermes_doc
    assert "phase14-provider-configuration.md" in hermes_doc
    assert "phase11-model-pack-compatibility.md" in hermes_doc
    assert "scripts/run_hermes_bridge_demo.py" in hermes_doc


def test_openclaw_reference_doc_covers_import_augmentation_and_one_call_reuse() -> None:
    openclaw_doc = (REPO_ROOT / "docs" / "integrations" / "openclaw.md").read_text(encoding="utf-8")

    assert "import plus augmentation" in openclaw_doc
    assert "POST /v1/continuity/brief" in openclaw_doc
    assert "alice_brief" in openclaw_doc
    assert "scripts/use_alice_with_openclaw.sh" in openclaw_doc
    assert "generic_python_agent.py" in openclaw_doc
    assert "generic_typescript_agent.ts" in openclaw_doc


def test_reference_agent_examples_doc_points_to_both_runnable_examples_and_demo() -> None:
    examples_doc = (REPO_ROOT / "docs" / "examples" / "reference-agent-examples.md").read_text(encoding="utf-8")

    assert "generic_python_agent.py" in examples_doc
    assert "generic_typescript_agent.ts" in examples_doc
    assert "ALICE_SESSION_TOKEN" in examples_doc
    assert "scripts/run_reference_agent_examples_demo.py" in examples_doc
    assert "--experimental-strip-types" in examples_doc

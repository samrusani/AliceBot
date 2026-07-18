from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/store.py"
LEGACY_STORE_ROOT = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store"
PROVIDERS_KNOWLEDGE_PATH = LEGACY_STORE_ROOT / "providers_knowledge.py"
MODEL_PACK_MODULE = REPO_ROOT / "apps/api/src/alicebot_api/model_packs.py"
MODEL_PACK_MIGRATIONS = (
    REPO_ROOT
    / "apps/api/alembic/versions/20260412_0054_phase11_model_packs_tier1.py",
    REPO_ROOT
    / "apps/api/alembic/versions/20260412_0056_phase11_model_packs_tier2_families.py",
    REPO_ROOT
    / "apps/api/alembic/versions/20260416_0064_phase14_provider_model_pack_bindings.py",
    REPO_ROOT
    / "apps/api/alembic/versions/20260416_0066_hosted_control_plane_owner_writes.py",
)


def test_model_pack_runtime_is_retired_without_rewriting_schema_history() -> None:
    assert not MODEL_PACK_MODULE.exists()

    store_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (STORE_PATH, *sorted(LEGACY_STORE_ROOT.rglob("*.py")))
    )
    forbidden_markers = (
        "class ModelPackRow",
        "class WorkspaceModelPackBindingRow",
        "class WorkspaceModelPackBindingDetailRow",
        "INSERT_MODEL_PACK_SQL",
        "INSERT_MODEL_PACK_IF_ABSENT_SQL",
        "GET_MODEL_PACK_FOR_WORKSPACE_BY_ID_AND_VERSION_SQL",
        "GET_LATEST_MODEL_PACK_FOR_WORKSPACE_BY_ID_SQL",
        "GET_MODEL_PACK_FOR_WORKSPACE_BY_ROW_ID_SQL",
        "LIST_MODEL_PACKS_FOR_WORKSPACE_SQL",
        "INSERT_WORKSPACE_MODEL_PACK_BINDING_SQL",
        "GET_LATEST_WORKSPACE_MODEL_PACK_BINDING_SQL",
        "GET_RESOLVED_WORKSPACE_MODEL_PACK_BINDING_SQL",
        "def create_model_pack(",
        "def create_model_pack_if_absent_optional(",
        "def get_model_pack_for_workspace_optional(",
        "def get_model_pack_for_workspace_by_row_id_optional(",
        "def list_model_packs_for_workspace(",
        "def create_workspace_model_pack_binding(",
        "def get_latest_workspace_model_pack_binding_optional(",
        "def get_resolved_workspace_model_pack_binding_optional(",
    )
    assert not [marker for marker in forbidden_markers if marker in store_source]
    assert all(path.is_file() for path in MODEL_PACK_MIGRATIONS)


def test_task_brief_store_keeps_historical_model_pack_strategy_column() -> None:
    store_source = STORE_PATH.read_text(encoding="utf-8")
    providers_source = PROVIDERS_KNOWLEDGE_PATH.read_text(encoding="utf-8")

    assert "class TaskBriefRow(TypedDict):" in store_source
    assert "model_pack_strategy: str" in store_source
    assert "INSERT INTO task_briefs (" not in store_source
    assert "def create_task_brief(" not in store_source
    assert "INSERT INTO task_briefs (" in providers_source
    assert "model_pack_strategy," in providers_source
    assert "def create_task_brief(" in providers_source

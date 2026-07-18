from __future__ import annotations

import ast
from datetime import UTC, datetime
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tokenize
from uuid import UUID

import pytest

import alicebot_api.store as store
from alicebot_api.legacy_store import providers_knowledge as carrier


ModelProviderRow = object()


REPO_ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/store.py"
CARRIER_PATH = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/providers_knowledge.py"
INIT_PATH = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/__init__.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

CONSTANT_NAMES = (
    "INSERT_MODEL_PROVIDER_SQL",
    "GET_MODEL_PROVIDER_FOR_WORKSPACE_SQL",
    "LIST_MODEL_PROVIDERS_FOR_WORKSPACE_SQL",
    "UPDATE_MODEL_PROVIDER_SQL",
    "UPSERT_PROVIDER_CAPABILITY_IF_CURRENT_SQL",
    "GET_PROVIDER_CAPABILITY_FOR_PROVIDER_SQL",
    "IS_PROVIDER_SECRET_REFERENCE_IN_USE_SQL",
    "INSERT_PROVIDER_INVOCATION_TELEMETRY_SQL",
    "WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL",
    "INSERT_TASK_BRIEF_SQL",
    "GET_TASK_BRIEF_BY_ID_SQL",
    "INSERT_EMBEDDING_CONFIG_SQL",
    "GET_EMBEDDING_CONFIG_SQL",
    "GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL",
    "LIST_EMBEDDING_CONFIGS_SQL",
    "INSERT_MEMORY_EMBEDDING_SQL",
    "GET_MEMORY_EMBEDDING_SQL",
    "GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL",
    "LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL",
    "LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL",
    "UPDATE_MEMORY_EMBEDDING_SQL",
    "RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL",
    "RETRIEVE_SEMANTIC_MEMORY_MATCHES_FOR_PROFILE_SQL",
    "RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL",
    "RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL",
    "INSERT_ENTITY_SQL",
    "GET_ENTITY_SQL",
    "LIST_ENTITIES_SQL",
    "INSERT_ENTITY_EDGE_SQL",
    "LIST_ENTITY_EDGES_FOR_ENTITY_SQL",
    "LIST_ENTITY_EDGES_FOR_ENTITIES_SQL",
)
METHOD_NAMES = (
    "create_model_provider",
    "get_model_provider_for_workspace_optional",
    "list_model_providers_for_workspace",
    "update_model_provider",
    "upsert_provider_capability_if_current",
    "get_provider_capability_for_provider_optional",
    "is_provider_secret_reference_in_use",
    "record_provider_invocation_telemetry",
    "workspace_visible_to_user_account",
    "create_task_brief",
    "get_task_brief_optional",
    "create_embedding_config",
    "get_embedding_config_optional",
    "get_embedding_config_by_identity_optional",
    "list_embedding_configs",
    "create_memory_embedding",
    "get_memory_embedding_optional",
    "get_memory_embedding_by_memory_and_config_optional",
    "list_memory_embeddings_for_memory",
    "list_memory_embeddings_for_config",
    "update_memory_embedding",
    "retrieve_semantic_memory_matches",
    "retrieve_semantic_memory_matches_for_profile",
    "retrieve_task_scoped_semantic_artifact_chunk_matches",
    "retrieve_artifact_scoped_semantic_artifact_chunk_matches",
    "create_entity",
    "get_entity_optional",
    "list_entities",
    "create_entity_edge",
    "list_entity_edges_for_entity",
    "list_entity_edges_for_entities",
)

EXPECTED_CARRIER_SHA256 = "2fe039907f0e9fb983150cc8febdae88d4ce682cf70b99681ee474ef9b14cafa"
EXPECTED_INIT_SHA256 = "a37f75edba360fe16bbabad20ce130a57a2fa385e52a2842d6c7286a13dba744"
EXPECTED_CONSTANT_NAMES = "0c2859acbad6127b933f262647c0bf1dc18754b72d9aaf68f6ae40347b489dc1"
EXPECTED_CONSTANT_AST = "ec6cc48aacf77898730d150059b6aa901974814203dc4696390568378ebe8a49"
EXPECTED_CONSTANT_VALUES = "ee9ba134ce771c7d61158ea40139432c57b73c461993d6c0bd45ab69dc108c15"
EXPECTED_CONSTANT_SOURCE = "6eeaaf65c0118203dc2f920ebb80c0a6d1a13b7745d069a02f5b39aaf38531c7"
EXPECTED_METHOD_NAMES = "f3d8e7bd10e04d84a62ec23eb8b3b50598306ef34eafeeef634037162f89715d"
EXPECTED_METHOD_AST = "c611a5aea1dfe384c3548a2560be719107776044ebbcbf8d317d531abd0e5b70"
EXPECTED_ORIGINAL_METHOD_SOURCE = "fd0b1ed9e9f97e23c07e69d6ec05de1a8a3d26dfcb67d8f344d9b63716a1f005"
EXPECTED_RUNTIME = "358d3cae599676d8783b9d2cb70ce6954a2cc92f6adb98a7cb8b1c3293355530"
EXPECTED_SEMANTIC_CODE = "3a0f5160af84c698e70d513130a9fe34a2708635c6d2aa65bd0fc5e31dd739a0"
EXPECTED_ALL_SQL_VALUES = "15bc0da3acbef4a859bf8ae05ccdf60cd6c4549e9baafe236e025a46659d0892"
EXPECTED_PUBLIC_NAMES = "8d1a83dfff470bfe767781bebfb8004430ba410650ce71c51da072d8ae6a2ddb"
EXPECTED_METHOD_ORDER = "6934333f4e3186b6c1ccfc0fcb173cfda80d367548e23f0722d6067053db951d"
EXPECTED_NO_COMMENTS = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
EXPECTED_BINDER_AST = {
    "_clone_function_with_facade_globals": (
        "1b6bc682440de4e2d786c3d63d0f1d06da71a42496be29086f33f881b39ac2bb"
    ),
    "_bind_legacy_store_method": "9c62f06988219ecdd67ce0618eea49da595d56381b3b72b43a2e17c198e38949",
}


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _compact_sha(value: object) -> str:
    encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
    return _sha_bytes(encoded)


def _tree(path: Path, source: str | None = None) -> ast.Module:
    return ast.parse(source if source is not None else path.read_text(encoding="utf-8"))


def _carrier_nodes() -> tuple[dict[str, ast.Assign], dict[str, ast.FunctionDef]]:
    tree = _tree(CARRIER_PATH)
    constants = {
        node.targets[0].id: node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in CONSTANT_NAMES
    }
    methods = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in METHOD_NAMES
    }
    return constants, methods


def _class_node(source: str | None = None) -> ast.ClassDef:
    matches = [
        node
        for node in _tree(STORE_PATH, source).body
        if isinstance(node, ast.ClassDef) and node.name == "ContinuityStore"
    ]
    assert len(matches) == 1
    return matches[0]


def _assert_facade_grafts(source: str | None = None) -> None:
    class_node = _class_node(source)
    definitions = {
        node.name for node in class_node.body if isinstance(node, ast.FunctionDef)
    }
    assert definitions.isdisjoint(METHOD_NAMES)
    assignments = {
        node.targets[0].id: node.value
        for node in class_node.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in METHOD_NAMES
    }
    assert list(assignments) == list(METHOD_NAMES)
    for name, value in assignments.items():
        assert isinstance(value, ast.Call)
        assert isinstance(value.func, ast.Name) and value.func.id == "_bind_legacy_store_method"
        assert len(value.args) == 1 and not value.keywords
        source_method = value.args[0]
        assert isinstance(source_method, ast.Attribute) and source_method.attr == name
        assert isinstance(source_method.value, ast.Name)
        assert source_method.value.id == "_providers_knowledge"


def _runtime_manifest() -> list[list[object]]:
    rows: list[list[object]] = []
    for name in METHOD_NAMES:
        method = getattr(store.ContinuityStore, name)
        rows.append(
            [
                method.__name__,
                str(inspect.signature(method)),
                method.__module__,
                method.__qualname__,
                method.__doc__,
                repr(method.__defaults__),
                repr(method.__kwdefaults__),
                method.__annotations__,
            ]
        )
    return rows


def _semantic_code_manifest() -> list[list[object]]:
    rows: list[list[object]] = []
    for name in METHOD_NAMES:
        code = getattr(store.ContinuityStore, name).__code__
        rows.append(
            [
                name,
                code.co_code.hex(),
                repr(code.co_consts),
                list(code.co_names),
                list(code.co_varnames),
                list(code.co_freevars),
                list(code.co_cellvars),
                code.co_argcount,
                code.co_posonlyargcount,
                code.co_kwonlyargcount,
                code.co_flags,
            ]
        )
    return rows


def test_provider_knowledge_carrier_pins_exact_constants_methods_and_sources() -> None:
    carrier_source = CARRIER_PATH.read_bytes()
    assert _sha_bytes(carrier_source) == EXPECTED_CARRIER_SHA256
    assert _sha_bytes(INIT_PATH.read_bytes()) == EXPECTED_INIT_SHA256

    constants, methods = _carrier_nodes()
    assert list(constants) == list(CONSTANT_NAMES)
    assert list(methods) == list(METHOD_NAMES)
    assert _compact_sha(list(constants)) == EXPECTED_CONSTANT_NAMES
    assert _compact_sha(
        [ast.dump(constants[name], include_attributes=False) for name in CONSTANT_NAMES]
    ) == EXPECTED_CONSTANT_AST
    assert _compact_sha(
        [[name, ast.literal_eval(constants[name].value)] for name in CONSTANT_NAMES]
    ) == EXPECTED_CONSTANT_VALUES
    assert _compact_sha(list(methods)) == EXPECTED_METHOD_NAMES
    assert _compact_sha(
        [ast.dump(methods[name], include_attributes=False) for name in METHOD_NAMES]
    ) == EXPECTED_METHOD_AST

    source = carrier_source.decode()
    lines = source.splitlines(keepends=True)
    constant_slice = "".join(
        lines[constants[CONSTANT_NAMES[0]].lineno - 1 : constants[CONSTANT_NAMES[-1]].end_lineno]
    )
    assert len(constant_slice.encode()) == 26_274
    assert _sha_bytes(constant_slice.encode()) == EXPECTED_CONSTANT_SOURCE
    method_slice = "".join(
        lines[methods[METHOD_NAMES[0]].lineno - 1 : methods[METHOD_NAMES[-1]].end_lineno]
    )
    original_indentation = "".join(
        f"    {line}" if line.strip() else line for line in method_slice.splitlines(keepends=True)
    )
    assert len(original_indentation.encode()) == 13_920
    assert _sha_bytes(original_indentation.encode()) == EXPECTED_ORIGINAL_METHOD_SOURCE

    comments = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(method_slice).readline)
        if token.type == tokenize.COMMENT
    ]
    assert _compact_sha(comments) == EXPECTED_NO_COMMENTS


def test_provider_knowledge_facade_owns_exact_runtime_and_public_surfaces() -> None:
    _assert_facade_grafts()
    assert carrier.__all__ == list(CONSTANT_NAMES)
    for name in CONSTANT_NAMES:
        assert getattr(store, name) is getattr(carrier, name)

    store_tree = _tree(STORE_PATH)
    facade_assignments = {
        node.targets[0].id
        for node in store_tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    assert facade_assignments.isdisjoint(CONSTANT_NAMES)
    imports = [
        node
        for node in store_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "alicebot_api.legacy_store.providers_knowledge"
    ]
    assert len(imports) == 1
    assert [(alias.name, alias.asname) for alias in imports[0].names] == [
        (name, name) for name in CONSTANT_NAMES
    ]

    class_keys = list(store.ContinuityStore.__dict__)
    assert class_keys[133:164] == list(METHOD_NAMES)
    assert class_keys[132] == "count_memory_operations"
    assert class_keys[164] == "create_consent"
    method_names = [
        name for name, value in store.ContinuityStore.__dict__.items() if callable(value)
    ]
    assert len(method_names) == 249
    assert _sha_bytes("\n".join(method_names).encode()) == EXPECTED_METHOD_ORDER
    assert store.ContinuityStore.__bases__ == (object,)
    assert store.ContinuityStore.__mro__ == (store.ContinuityStore, object)

    public_names = [name for name in vars(store) if not name.startswith("_")]
    assert len(public_names) == 330
    assert _compact_sha(public_names) == EXPECTED_PUBLIC_NAMES
    namespace: dict[str, object] = {}
    exec("from alicebot_api.store import *", namespace)
    assert [name for name in namespace if name != "__builtins__"] == public_names
    all_sql_values = [
        [name, value]
        for name, value in vars(store).items()
        if name.isupper() and isinstance(value, str)
    ]
    assert len(all_sql_values) == 251
    assert _compact_sha(all_sql_values) == EXPECTED_ALL_SQL_VALUES


def test_provider_knowledge_rebound_methods_preserve_metadata_code_and_facade_globals() -> None:
    assert _compact_sha(_runtime_manifest()) == EXPECTED_RUNTIME
    assert _compact_sha(_semantic_code_manifest()) == EXPECTED_SEMANTIC_CODE
    for name in METHOD_NAMES:
        method = getattr(store.ContinuityStore, name)
        source = getattr(carrier, name)
        assert method is not source
        assert method.__globals__ is vars(store)
        assert method.__module__ == "alicebot_api.store"
        assert method.__qualname__ == f"ContinuityStore.{name}"
        assert method.__code__.co_qualname == f"ContinuityStore.{name}"
        assert Path(method.__code__.co_filename).resolve() == CARRIER_PATH.resolve()
        assert inspect.signature(method) == inspect.signature(source)

    store_functions = {
        node.name: node for node in _tree(STORE_PATH).body if isinstance(node, ast.FunctionDef)
    }
    for name, expected in EXPECTED_BINDER_AST.items():
        assert _sha_bytes(ast.dump(store_functions[name], include_attributes=False).encode()) == expected


def test_provider_knowledge_lazy_annotation_thunk_is_rebound_to_owner_globals_and_metadata() -> None:
    def source(self):
        del self

    def __annotate__(format):
        return {"return": ModelProviderRow, "format": format}

    source.__annotate__ = __annotate__
    source.__type_params__ = ("T",)
    rebound = store._bind_legacy_store_method(source)
    rebound_annotate = rebound.__annotate__

    assert rebound.__globals__ is vars(store)
    assert rebound.__type_params__ == ("T",)
    assert rebound_annotate is not __annotate__
    assert rebound_annotate.__globals__ is vars(store)
    assert rebound_annotate.__module__ == "alicebot_api.store"
    assert rebound_annotate.__qualname__ == "ContinuityStore.__annotate__"
    assert rebound_annotate.__code__.co_qualname == "ContinuityStore.__annotate__"
    assert rebound_annotate(1)["return"] is store.ModelProviderRow


def test_provider_knowledge_carrier_has_no_runtime_facade_cycle_and_imports_fresh() -> None:
    tree = _tree(CARRIER_PATH)
    runtime_import_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert runtime_import_modules.isdisjoint(
        {
            "alicebot_api.store",
            "alicebot_api.main",
            "alicebot_api.vnext_store",
            "alicebot_api.sqlite_store",
        }
    )
    type_checking_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Name)
        and node.test.id == "TYPE_CHECKING"
    ]
    assert len(type_checking_imports) == 1
    assert any(
        isinstance(node, ast.ImportFrom) and node.module == "alicebot_api.store"
        for node in type_checking_imports[0].body
    )

    code = """
import sys
from alicebot_api.legacy_store import providers_knowledge
assert 'alicebot_api.store' not in sys.modules
assert 'alicebot_api.main' not in sys.modules
assert 'alicebot_api.vnext_store' not in sys.modules
assert 'alicebot_api.sqlite_store' not in sys.modules
assert providers_knowledge.create_model_provider
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert len(CARRIER_PATH.read_text(encoding="utf-8").splitlines()) <= 1300
    assert len(STORE_PATH.read_text(encoding="utf-8").splitlines()) <= 8150


def test_provider_knowledge_scanners_protection_and_installed_wheel_proof_follow_carrier() -> None:
    model_pack_guard = (REPO_ROOT / "tests/unit/test_model_pack_retirement.py").read_text()
    removed_contracts = (REPO_ROOT / "tests/unit/test_removed_public_contracts.py").read_text()
    protected_script = (REPO_ROOT / "scripts/check_protected_paths.py").read_text()
    protected_docs = (REPO_ROOT / "PROTECTED_PATHS.md").read_text()
    workflow = WORKFLOW_PATH.read_text()

    assert model_pack_guard.count('LEGACY_STORE_ROOT.rglob("*.py")') == 1
    assert 'PROVIDERS_KNOWLEDGE_PATH = LEGACY_STORE_ROOT / "providers_knowledge.py"' in model_pack_guard
    assert '"INSERT INTO task_briefs (" not in store_source' in model_pack_guard
    assert '"def create_task_brief(" in providers_source' in model_pack_guard
    assert removed_contracts.count('LEGACY_STORE_ROOT.rglob("*.py")') == 1
    protected_pattern = "apps/api/src/alicebot_api/legacy_store/*.py"
    assert protected_pattern in protected_script
    assert f"`{protected_pattern}`" in protected_docs
    assert "from alicebot_api.legacy_store import providers_knowledge" in workflow
    assert "legacy store carrier resolved to checkout source" in workflow
    assert "moved store method resolved to checkout source" in workflow
    assert "inspect.get_annotations(moved_method, eval_str=False)" in workflow


def _fake_store() -> store.ContinuityStore:
    return object.__new__(store.ContinuityStore)


def test_provider_knowledge_methods_resolve_divergent_sql_and_jsonb_from_facade(monkeypatch) -> None:
    calls: list[tuple[str, str, tuple[object, ...] | None]] = []
    instance = _fake_store()
    instance._fetch_one = lambda operation, query, params=None: (
        calls.append((operation, query, params)) or {"id": "entity"}
    )

    monkeypatch.setattr(store, "INSERT_ENTITY_SQL", "facade entity SQL")
    monkeypatch.setattr(carrier, "INSERT_ENTITY_SQL", "carrier entity SQL")
    monkeypatch.setattr(store, "Jsonb", lambda value: ("facade-json", value))
    monkeypatch.setattr(carrier, "Jsonb", lambda value: ("carrier-json", value))

    row = instance.create_entity(
        entity_type="person",
        name="Ada",
        source_memory_ids=["memory"],
    )
    assert row == {"id": "entity"}
    assert calls == [
        (
            "create_entity",
            "facade entity SQL",
            ("person", "Ada", ("facade-json", ["memory"])),
        )
    ]


def test_provider_knowledge_vector_retrieval_tuple_orders_are_preserved() -> None:
    calls: list[tuple[str, tuple[object, ...] | None]] = []
    instance = _fake_store()
    instance._fetch_all = lambda query, params=None: calls.append((query, params)) or []
    config_id = UUID("00000000-0000-0000-0000-000000000001")
    scope_id = UUID("00000000-0000-0000-0000-000000000002")
    vector = [1.25, -2.5]
    literal = "[1.25,-2.5]"

    instance.retrieve_semantic_memory_matches(
        embedding_config_id=config_id,
        query_vector=vector,
        limit=3,
    )
    instance.retrieve_semantic_memory_matches_for_profile(
        embedding_config_id=config_id,
        query_vector=vector,
        agent_profile_id="profile",
        limit=4,
    )
    instance.retrieve_task_scoped_semantic_artifact_chunk_matches(
        task_id=scope_id,
        embedding_config_id=config_id,
        query_vector=vector,
        limit=5,
    )
    instance.retrieve_artifact_scoped_semantic_artifact_chunk_matches(
        task_artifact_id=scope_id,
        embedding_config_id=config_id,
        query_vector=vector,
        limit=6,
    )
    assert [params for _query, params in calls] == [
        (literal, config_id, 2, 3),
        (literal, config_id, 2, "profile", 4),
        (literal, config_id, 2, scope_id, 5),
        (literal, config_id, 2, scope_id, 6),
    ]


def test_provider_knowledge_empty_entity_edge_batch_does_not_fetch() -> None:
    instance = _fake_store()

    def fail_fetch(*_args, **_kwargs):
        raise AssertionError("empty entity list must not query")

    instance._fetch_all = fail_fetch
    assert instance.list_entity_edges_for_entities([]) == []


def test_provider_knowledge_workspace_visibility_preserves_cursor_boolean_and_params() -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []
    rows: list[object | None] = [{"visible": True}, None]

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, query, params):
            calls.append((query, params))

        def fetchone(self):
            return rows.pop(0)

    class Connection:
        def cursor(self):
            return Cursor()

    instance = _fake_store()
    instance.conn = Connection()
    workspace_id = UUID("00000000-0000-0000-0000-000000000001")
    user_id = UUID("00000000-0000-0000-0000-000000000002")
    assert instance.workspace_visible_to_user_account(
        workspace_id=workspace_id,
        user_account_id=user_id,
    ) is True
    assert instance.workspace_visible_to_user_account(
        workspace_id=workspace_id,
        user_account_id=user_id,
    ) is False
    assert calls == [
        (store.WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL, (workspace_id, user_id)),
        (store.WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL, (workspace_id, user_id)),
    ]


def test_provider_knowledge_provider_cas_telemetry_and_task_brief_params(monkeypatch) -> None:
    calls: list[tuple[str, str, tuple[object, ...] | None]] = []
    instance = _fake_store()
    instance._fetch_one = lambda operation, query, params=None: (
        calls.append((operation, query, params)) or {"id": operation}
    )
    instance._fetch_optional_one = lambda query, params=None: (
        calls.append(("optional", query, params)) or {"id": "optional"}
    )
    monkeypatch.setattr(store, "Jsonb", lambda value: ("json", value))
    one = UUID("00000000-0000-0000-0000-000000000001")
    two = UUID("00000000-0000-0000-0000-000000000002")

    instance.create_model_provider(
        workspace_id=one,
        created_by_user_account_id=two,
        provider_key="provider",
        model_provider="openai",
        display_name="Provider",
        base_url="https://example.invalid",
        api_key="secret",
        default_model="model",
        status="active",
        metadata={"a": 1},
        config_fingerprint_sha256="fingerprint",
    )
    assert calls[-1][2] == (
        one,
        two,
        "provider",
        "openai",
        "Provider",
        "https://example.invalid",
        "secret",
        "bearer",
        "model",
        "active",
        "",
        "",
        "",
        "",
        "",
        ("json", {"a": 1}),
        "fingerprint",
    )

    instance.upsert_provider_capability_if_current(
        workspace_id=one,
        provider_id=two,
        discovered_by_user_account_id=one,
        adapter_key="adapter",
        discovery_status="ready",
        capability_snapshot={"models": []},
        discovery_error=None,
        expected_config_revision=7,
        expected_config_fingerprint_sha256="expected",
    )
    assert calls[-1][2] == (
        two,
        one,
        7,
        "expected",
        one,
        "adapter",
        "ready",
        ("json", {"models": []}),
        None,
    )

    instance.record_provider_invocation_telemetry(
        workspace_id=one,
        provider_id=two,
        thread_id=None,
        invoked_by_user_account_id=one,
        invocation_kind="chat",
        adapter_key="adapter",
        runtime_provider="openai",
        requested_model="requested",
        response_model="response",
        response_id="id",
        status="ok",
        latency_ms=12,
        usage={"tokens": 4},
        error_detail=None,
    )
    assert calls[-1][2][-2:] == (("json", {"tokens": 4}), None)

    instance.create_task_brief(
        mode="brief",
        query_text="query",
        scope={"project": "alice"},
        provider_strategy="auto",
        model_pack_strategy="historical",
        token_budget=100,
        estimated_tokens=40,
        item_count=2,
        deterministic_key="key",
        payload={"ok": True},
    )
    assert calls[-1][2] == (
        "brief",
        "query",
        ("json", {"project": "alice"}),
        "auto",
        "historical",
        100,
        40,
        2,
        "key",
        ("json", {"ok": True}),
    )


@pytest.mark.parametrize(
    ("path", "old", "new"),
    (
        (CARRIER_PATH, "expected_config_fingerprint_sha256", "ignored_fingerprint"),
        (CARRIER_PATH, "len(query_vector)", "0"),
        (CARRIER_PATH, "if not entity_ids:", "if False:"),
        (CARRIER_PATH, "WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL", '"SELECT TRUE"'),
    ),
)
def test_provider_knowledge_receipt_rejects_weakened_carrier(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    assert old in source
    weakened = source.replace(old, new, 1)
    assert _sha_bytes(weakened.encode()) != EXPECTED_CARRIER_SHA256


def test_provider_knowledge_graft_guard_rejects_direct_alias_and_old_inline_method() -> None:
    source = STORE_PATH.read_text(encoding="utf-8")
    direct_alias = source.replace(
        "create_model_provider = _bind_legacy_store_method(_providers_knowledge.create_model_provider)",
        "create_model_provider = _providers_knowledge.create_model_provider",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(direct_alias)

    old_inline = source.replace(
        "    create_model_provider = _bind_legacy_store_method(_providers_knowledge.create_model_provider)",
        "    def create_model_provider(self):\n        raise NotImplementedError",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(old_inline)

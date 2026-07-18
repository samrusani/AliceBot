from __future__ import annotations

import ast
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
from alicebot_api.legacy_store import task_execution as carrier


TaskStepRow = object()


REPO_ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/store.py"
CARRIER_PATH = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/task_execution.py"
INIT_PATH = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/__init__.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EARLY_CONSTANT_NAMES = (
    "LOCK_TASK_STEPS_SQL",
    "LOCK_TASK_WORKSPACES_SQL",
    "LOCK_TASK_ARTIFACTS_SQL",
    "LOCK_TASK_RUNS_SQL",
)
MAIN_CONSTANT_NAMES = (
    "INSERT_TASK_WORKSPACE_SQL",
    "GET_TASK_WORKSPACE_SQL",
    "GET_ACTIVE_TASK_WORKSPACE_FOR_TASK_SQL",
    "LIST_TASK_WORKSPACES_SQL",
    "INSERT_TASK_ARTIFACT_SQL",
    "GET_TASK_ARTIFACT_SQL",
    "GET_TASK_ARTIFACT_BY_WORKSPACE_RELATIVE_PATH_SQL",
    "LIST_TASK_ARTIFACTS_SQL",
    "LIST_TASK_ARTIFACTS_FOR_TASK_SQL",
    "LOCK_TASK_ARTIFACT_INGESTION_SQL",
    "INSERT_TASK_ARTIFACT_CHUNK_SQL",
    "LIST_TASK_ARTIFACT_CHUNKS_SQL",
    "GET_TASK_ARTIFACT_CHUNK_SQL",
    "INSERT_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL",
    "GET_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL",
    "GET_TASK_ARTIFACT_CHUNK_EMBEDDING_BY_CHUNK_AND_CONFIG_SQL",
    "LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_CHUNK_SQL",
    "LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_ARTIFACT_SQL",
    "UPDATE_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL",
    "UPDATE_TASK_ARTIFACT_INGESTION_STATUS_SQL",
    "INSERT_TASK_STEP_SQL",
    "GET_TASK_STEP_SQL",
    "GET_TASK_STEP_FOR_TASK_SEQUENCE_SQL",
    "LIST_TASK_STEPS_FOR_TASK_SQL",
    "UPDATE_TASK_STEP_FOR_TASK_SEQUENCE_SQL",
    "UPDATE_TASK_STEP_SQL",
    "INSERT_TASK_RUN_SQL",
    "GET_TASK_RUN_SQL",
    "LIST_TASK_RUNS_FOR_TASK_SQL",
    "UPDATE_TASK_RUN_SQL",
    "ACQUIRE_NEXT_TASK_RUN_SQL",
    "INSERT_TOOL_EXECUTION_SQL",
    "GET_TOOL_EXECUTION_SQL",
    "LIST_TOOL_EXECUTIONS_SQL",
    "GET_TOOL_EXECUTION_BY_IDEMPOTENCY_SQL",
    "INSERT_EXECUTION_BUDGET_SQL",
    "GET_EXECUTION_BUDGET_SQL",
    "LIST_EXECUTION_BUDGETS_SQL",
    "DEACTIVATE_EXECUTION_BUDGET_SQL",
    "SUPERSEDE_EXECUTION_BUDGET_SQL",
)
CONSTANT_NAMES = EARLY_CONSTANT_NAMES + MAIN_CONSTANT_NAMES
METHOD_NAMES = (
    "lock_task_workspaces",
    "create_task_workspace",
    "get_task_workspace_optional",
    "get_active_task_workspace_for_task_optional",
    "list_task_workspaces",
    "lock_task_artifacts",
    "create_task_artifact",
    "get_task_artifact_optional",
    "get_task_artifact_by_workspace_relative_path_optional",
    "list_task_artifacts",
    "list_task_artifacts_for_task",
    "lock_task_artifact_ingestion",
    "create_task_artifact_chunk",
    "get_task_artifact_chunk_optional",
    "list_task_artifact_chunks",
    "create_task_artifact_chunk_embedding",
    "get_task_artifact_chunk_embedding_optional",
    "get_task_artifact_chunk_embedding_by_chunk_and_config_optional",
    "list_task_artifact_chunk_embeddings_for_chunk",
    "list_task_artifact_chunk_embeddings_for_artifact",
    "update_task_artifact_chunk_embedding",
    "update_task_artifact_ingestion_status",
    "lock_task_steps",
    "create_task_step",
    "get_task_step_optional",
    "get_task_step_for_task_sequence_optional",
    "list_task_steps_for_task",
    "update_task_step_for_task_sequence_optional",
    "update_task_step_optional",
    "lock_task_runs",
    "create_task_run",
    "get_task_run_optional",
    "list_task_runs_for_task",
    "update_task_run_optional",
    "acquire_next_task_run_optional",
    "create_tool_execution",
    "get_tool_execution_optional",
    "list_tool_executions",
    "get_tool_execution_by_idempotency_optional",
    "create_execution_budget",
    "get_execution_budget_optional",
    "list_execution_budgets",
    "deactivate_execution_budget_optional",
    "supersede_execution_budget_optional",
)
EXPECTED_PLACEHOLDER_COUNTS = (
    1,
    1,
    1,
    1,
    3,
    1,
    1,
    0,
    6,
    1,
    2,
    0,
    1,
    1,
    5,
    1,
    1,
    4,
    1,
    2,
    1,
    1,
    3,
    2,
    11,
    1,
    2,
    1,
    6,
    5,
    11,
    1,
    1,
    10,
    0,
    14,
    1,
    0,
    3,
    7,
    1,
    0,
    1,
    2,
)

EXPECTED_CARRIER_SHA256 = "6cde8c28ad55ec4a178bd71181b933893606e728edef54db82a9eaa2f1925aed"
EXPECTED_INIT_SHA256 = "a37f75edba360fe16bbabad20ce130a57a2fa385e52a2842d6c7286a13dba744"
EXPECTED_CONSTANT_NAMES = "efa361b5150c2d13bdaaf8d99ca78b201a07865728d194a1030f1e5221a7fe4c"
EXPECTED_CONSTANT_AST = "f3198cf0d62bcad40e0daa18689a6d8062e74d84327e05a9c734cbd6a5d3836b"
EXPECTED_CONSTANT_VALUES = "4b232e8d4b609f69a110731ffbb470b888ff6986dadd79bbd77c1559fa35678d"
EXPECTED_CONSTANT_NODE_SOURCE = "44eb5a6bafafa1ef00786eeb32b6bef06814734f1bba2fcec39dab3fc622a650"
EXPECTED_EARLY_CONSTANT_SOURCE = "24d9a5875e9bfbed9bd6144b7b76ec82a5614c0b50df630d95e2421bf61b2c4f"
EXPECTED_MAIN_CONSTANT_SOURCE = "3f835edf4460ea8c6b35b32dd9cfa4d1d098a0357f4b074bd7235dff37567825"
EXPECTED_COMBINED_CONSTANT_SOURCE = "ef6fed9f47c088bb87a7a3d8294fa3cc1e95d22b91f631e3f20f438340c103d0"
EXPECTED_METHOD_NAMES = "18b13bd54c39034011473453d6ba9d378257b06f7e266714b4a8d5a704299341"
EXPECTED_METHOD_AST = "51a8197ce13faad8a4f7b7d7531a126f0b910df8b5388c483f59f6809e3be32f"
EXPECTED_ORIGINAL_METHOD_SOURCE = "4dc5380a5ac5ba69a760b4a27ab9e8f30ae43e80a5e4894a7f88567cce59db4f"
EXPECTED_RUNTIME = "d9020e36bc81ee516d9191d43d4be1bcab5af906a36d32ae4602dd83600a8f76"
EXPECTED_SEMANTIC_CODE = "792b1a7d1e7362212f2994fe949dbaf3b19cc9304879734f6c4c83ae398d2411"
EXPECTED_STRING_VALUES = "0f74dc0ce5b3ea56c45d9af59203fffb59c8be6fd7e5bbcf1f3f28e5399dc6af"
EXPECTED_STRING_SOURCE = "92821308d0a8e6c2612b56fe2a1c5d857f62c9984e17211eed4e1f7311989a65"
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
    return _sha_bytes(
        json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
    )


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
        assert isinstance(value.func, ast.Name)
        assert value.func.id == "_bind_legacy_store_method"
        assert len(value.args) == 1 and not value.keywords
        source_method = value.args[0]
        assert isinstance(source_method, ast.Attribute) and source_method.attr == name
        assert isinstance(source_method.value, ast.Name)
        assert source_method.value.id == "_task_execution"


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


def test_task_execution_carrier_pins_exact_constants_methods_and_sources() -> None:
    carrier_source = CARRIER_PATH.read_bytes()
    assert _sha_bytes(carrier_source) == EXPECTED_CARRIER_SHA256
    assert _sha_bytes(INIT_PATH.read_bytes()) == EXPECTED_INIT_SHA256
    source = carrier_source.decode()
    lines = source.splitlines(keepends=True)
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
    assert _compact_sha(
        [[name, ast.get_source_segment(source, constants[name])] for name in CONSTANT_NAMES]
    ) == EXPECTED_CONSTANT_NODE_SOURCE

    early_source = "".join(
        lines[
            constants[EARLY_CONSTANT_NAMES[0]].lineno
            - 1 : constants[EARLY_CONSTANT_NAMES[-1]].end_lineno
        ]
    )
    main_source = "".join(
        lines[
            constants[MAIN_CONSTANT_NAMES[0]].lineno
            - 1 : constants[MAIN_CONSTANT_NAMES[-1]].end_lineno
        ]
    )
    assert len(early_source.encode()) == 344
    assert len(main_source.encode()) == 31_075
    assert _sha_bytes(early_source.encode()) == EXPECTED_EARLY_CONSTANT_SOURCE
    assert _sha_bytes(main_source.encode()) == EXPECTED_MAIN_CONSTANT_SOURCE
    assert _sha_bytes((early_source + main_source).encode()) == EXPECTED_COMBINED_CONSTANT_SOURCE

    assert _compact_sha(list(methods)) == EXPECTED_METHOD_NAMES
    assert _compact_sha(
        [ast.dump(methods[name], include_attributes=False) for name in METHOD_NAMES]
    ) == EXPECTED_METHOD_AST
    method_slice = "".join(
        lines[methods[METHOD_NAMES[0]].lineno - 1 : methods[METHOD_NAMES[-1]].end_lineno]
    )
    original_indentation = "".join(
        f"    {line}" if line.strip() else line for line in method_slice.splitlines(keepends=True)
    )
    assert len(original_indentation.encode()) == 14_411
    assert _sha_bytes(original_indentation.encode()) == EXPECTED_ORIGINAL_METHOD_SOURCE
    string_values = [
        [
            name,
            [
                node.value
                for node in ast.walk(methods[name])
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            ],
        ]
        for name in METHOD_NAMES
    ]
    string_sources = [
        [
            name,
            [
                ast.get_source_segment(source, node)
                for node in ast.walk(methods[name])
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            ],
        ]
        for name in METHOD_NAMES
    ]
    assert _compact_sha(string_values) == EXPECTED_STRING_VALUES
    assert _compact_sha(string_sources) == EXPECTED_STRING_SOURCE
    assert all(ast.get_docstring(methods[name], clean=False) is None for name in METHOD_NAMES)
    assert all("\n" not in value for _name, values in string_values for value in values)
    comments = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(method_slice).readline)
        if token.type == tokenize.COMMENT
    ]
    assert _compact_sha(comments) == EXPECTED_NO_COMMENTS


def test_task_execution_facade_preserves_two_constant_seams_and_public_surface() -> None:
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
        and node.module == "alicebot_api.legacy_store.task_execution"
    ]
    assert len(imports) == 2
    assert [(alias.name, alias.asname) for alias in imports[0].names] == [
        (name, name) for name in EARLY_CONSTANT_NAMES
    ]
    assert [(alias.name, alias.asname) for alias in imports[1].names] == [
        (name, name) for name in MAIN_CONSTANT_NAMES
    ]

    sql_names = [
        name
        for name, value in vars(store).items()
        if name.isupper() and isinstance(value, str)
    ]
    assert sql_names[9] == "LOCK_THREAD_EVENTS_SQL"
    assert sql_names[10:14] == list(EARLY_CONSTANT_NAMES)
    assert sql_names[14] == "INSERT_EVENT_SQL"
    assert sql_names[142] == "LIST_CALENDAR_ACCOUNTS_SQL"
    assert sql_names[143:183] == list(MAIN_CONSTANT_NAMES)
    assert sql_names[183] == "INSERT_CONTINUITY_CAPTURE_EVENT_SQL"

    public_names = [name for name in vars(store) if not name.startswith("_")]
    assert public_names[85] == "LOCK_THREAD_EVENTS_SQL"
    assert public_names[86:90] == list(EARLY_CONSTANT_NAMES)
    assert public_names[90] == "INSERT_EVENT_SQL"
    assert public_names[218] == "LIST_CALENDAR_ACCOUNTS_SQL"
    assert public_names[219:259] == list(MAIN_CONSTANT_NAMES)
    assert public_names[259] == "INSERT_CONTINUITY_CAPTURE_EVENT_SQL"
    assert len(public_names) == 330
    assert _compact_sha(public_names) == EXPECTED_PUBLIC_NAMES
    namespace: dict[str, object] = {}
    exec("from alicebot_api.store import *", namespace)
    assert [name for name in namespace if name != "__builtins__"] == public_names

    class_keys = list(store.ContinuityStore.__dict__)
    assert class_keys[201] == "list_calendar_accounts"
    assert class_keys[202:246] == list(METHOD_NAMES)
    assert class_keys[246] == "update_event"
    method_names = [
        name for name, value in store.ContinuityStore.__dict__.items() if callable(value)
    ]
    assert len(method_names) == 249
    assert _sha_bytes("\n".join(method_names).encode()) == EXPECTED_METHOD_ORDER
    assert store.ContinuityStore.__bases__ == (object,)
    assert store.ContinuityStore.__mro__ == (store.ContinuityStore, object)
    all_sql_values = [
        [name, value]
        for name, value in vars(store).items()
        if name.isupper() and isinstance(value, str)
    ]
    assert len(all_sql_values) == 251
    assert _compact_sha(all_sql_values) == EXPECTED_ALL_SQL_VALUES
    assert tuple(getattr(carrier, name).count("%s") for name in CONSTANT_NAMES) == (
        EXPECTED_PLACEHOLDER_COUNTS
    )


def test_task_execution_rebound_methods_preserve_metadata_code_and_facade_globals() -> None:
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
        assert inspect.get_annotations(method, eval_str=False) == inspect.get_annotations(
            source,
            eval_str=False,
        )
        source_annotate = getattr(source, "__annotate__", None)
        if source_annotate is not None:
            rebound_annotate = method.__annotate__
            assert rebound_annotate is not source_annotate
            assert rebound_annotate.__globals__ is vars(store)
            assert rebound_annotate.__module__ == "alicebot_api.store"
            assert rebound_annotate.__qualname__ == "ContinuityStore.__annotate__"
            assert rebound_annotate.__code__.co_qualname == "ContinuityStore.__annotate__"

    store_functions = {
        node.name: node for node in _tree(STORE_PATH).body if isinstance(node, ast.FunctionDef)
    }
    for name, expected in EXPECTED_BINDER_AST.items():
        assert _sha_bytes(ast.dump(store_functions[name], include_attributes=False).encode()) == expected


def test_task_execution_lazy_annotation_thunk_uses_facade_globals_and_metadata() -> None:
    def source(self):
        del self

    def __annotate__(format):
        return {"return": TaskStepRow, "format": format}

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
    assert rebound_annotate(1)["return"] is store.TaskStepRow


def test_task_execution_carrier_has_no_runtime_facade_cycle_and_imports_fresh() -> None:
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
from alicebot_api.legacy_store import task_execution
assert 'alicebot_api.store' not in sys.modules
assert 'alicebot_api.main' not in sys.modules
assert 'alicebot_api.vnext_store' not in sys.modules
assert 'alicebot_api.sqlite_store' not in sys.modules
assert task_execution.create_task_step
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
    assert len(CARRIER_PATH.read_text(encoding="utf-8").splitlines()) <= 1550
    assert len(STORE_PATH.read_text(encoding="utf-8").splitlines()) <= 5750


def test_task_execution_controls_and_installed_wheel_proof_follow_carrier() -> None:
    model_pack_guard = (REPO_ROOT / "tests/unit/test_model_pack_retirement.py").read_text()
    removed_contracts = (REPO_ROOT / "tests/unit/test_removed_public_contracts.py").read_text()
    protected_script = (REPO_ROOT / "scripts/check_protected_paths.py").read_text()
    protected_docs = (REPO_ROOT / "PROTECTED_PATHS.md").read_text()
    workflow = WORKFLOW_PATH.read_text()

    assert model_pack_guard.count('LEGACY_STORE_ROOT.rglob("*.py")') == 1
    assert removed_contracts.count('LEGACY_STORE_ROOT.rglob("*.py")') == 1
    protected_pattern = "apps/api/src/alicebot_api/legacy_store/*.py"
    assert protected_pattern in protected_script
    assert f"`{protected_pattern}`" in protected_docs
    assert "from alicebot_api.legacy_store import task_execution" in workflow
    assert "task execution legacy store carrier resolved to checkout source" in workflow
    assert "moved task execution store method resolved to checkout source" in workflow
    assert "store_module.ContinuityStore.create_task_step" in workflow
    assert "task_execution_moved_method.__globals__ is vars(store_module)" in workflow
    assert "task_execution_moved_method.__code__.co_qualname" in workflow


def _fake_store(monkeypatch) -> tuple[store.ContinuityStore, list[tuple[object, ...]]]:
    calls: list[tuple[object, ...]] = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, query, params):
            calls.append(("cursor", query, params))

    class Connection:
        def cursor(self):
            return Cursor()

    instance = object.__new__(store.ContinuityStore)
    instance.conn = Connection()
    instance._fetch_one = lambda operation, query, params=None: (
        calls.append(("one", operation, query, params)) or {"operation": operation}
    )
    instance._fetch_optional_one = lambda query, params=None: (
        calls.append(("optional", query, params)) or {"query": query}
    )
    instance._fetch_all = lambda query, params=None: (
        calls.append(("all", query, params)) or []
    )
    instance._acquire_advisory_lock = lambda query, key: calls.append(
        ("advisory", query, key)
    )
    instance._fetch_one_with_lock = lambda **kwargs: (
        calls.append(("locked", kwargs)) or {"operation": kwargs["operation_name"]}
    )
    monkeypatch.setattr(store, "Jsonb", lambda value: ("facade-json", value))
    monkeypatch.setattr(carrier, "Jsonb", lambda value: ("carrier-json", value))
    for name in CONSTANT_NAMES:
        monkeypatch.setattr(store, name, f"facade:{name}")
        monkeypatch.setattr(carrier, name, f"carrier:{name}")
    return instance, calls


def _assert_next(calls: list[tuple[object, ...]], expected: tuple[object, ...]) -> None:
    assert calls.pop(0) == expected


def _sql(name: str) -> str:
    return f"facade:{name}"


def _json(value: object) -> tuple[str, object]:
    return ("facade-json", value)


def test_task_execution_workspace_artifact_and_chunk_call_shapes(monkeypatch) -> None:
    instance, calls = _fake_store(monkeypatch)
    one = UUID("00000000-0000-0000-0000-000000000001")
    two = UUID("00000000-0000-0000-0000-000000000002")

    instance.lock_task_workspaces(one)
    _assert_next(calls, ("cursor", _sql("LOCK_TASK_WORKSPACES_SQL"), (str(one),)))
    instance.create_task_workspace(task_id=one, status="active", local_path="/tmp/task")
    _assert_next(
        calls,
        ("one", "create_task_workspace", _sql("INSERT_TASK_WORKSPACE_SQL"), (one, "active", "/tmp/task")),
    )
    instance.get_task_workspace_optional(two)
    _assert_next(calls, ("optional", _sql("GET_TASK_WORKSPACE_SQL"), (two,)))
    instance.get_active_task_workspace_for_task_optional(one)
    _assert_next(
        calls,
        ("optional", _sql("GET_ACTIVE_TASK_WORKSPACE_FOR_TASK_SQL"), (one,)),
    )
    instance.list_task_workspaces()
    _assert_next(calls, ("all", _sql("LIST_TASK_WORKSPACES_SQL"), None))
    instance.lock_task_artifacts(two)
    _assert_next(calls, ("cursor", _sql("LOCK_TASK_ARTIFACTS_SQL"), (str(two),)))
    instance.create_task_artifact(
        task_id=one,
        task_workspace_id=two,
        status="ready",
        ingestion_status="pending",
        relative_path="output.txt",
        media_type_hint=None,
    )
    _assert_next(
        calls,
        (
            "one",
            "create_task_artifact",
            _sql("INSERT_TASK_ARTIFACT_SQL"),
            (one, two, "ready", "pending", "output.txt", None),
        ),
    )
    instance.get_task_artifact_optional(two)
    _assert_next(calls, ("optional", _sql("GET_TASK_ARTIFACT_SQL"), (two,)))
    instance.get_task_artifact_by_workspace_relative_path_optional(
        task_workspace_id=one,
        relative_path="output.txt",
    )
    _assert_next(
        calls,
        (
            "optional",
            _sql("GET_TASK_ARTIFACT_BY_WORKSPACE_RELATIVE_PATH_SQL"),
            (one, "output.txt"),
        ),
    )
    instance.list_task_artifacts()
    _assert_next(calls, ("all", _sql("LIST_TASK_ARTIFACTS_SQL"), None))
    instance.list_task_artifacts_for_task(one)
    _assert_next(calls, ("all", _sql("LIST_TASK_ARTIFACTS_FOR_TASK_SQL"), (one,)))
    instance.lock_task_artifact_ingestion(two)
    _assert_next(
        calls,
        ("cursor", _sql("LOCK_TASK_ARTIFACT_INGESTION_SQL"), (str(two),)),
    )
    instance.create_task_artifact_chunk(
        task_artifact_id=one,
        sequence_no=2,
        char_start=10,
        char_end_exclusive=20,
        text="chunk",
    )
    _assert_next(
        calls,
        (
            "one",
            "create_task_artifact_chunk",
            _sql("INSERT_TASK_ARTIFACT_CHUNK_SQL"),
            (one, 2, 10, 20, "chunk"),
        ),
    )
    instance.get_task_artifact_chunk_optional(two)
    _assert_next(calls, ("optional", _sql("GET_TASK_ARTIFACT_CHUNK_SQL"), (two,)))
    instance.list_task_artifact_chunks(one)
    _assert_next(calls, ("all", _sql("LIST_TASK_ARTIFACT_CHUNKS_SQL"), (one,)))
    assert not calls


def test_task_execution_embedding_and_ingestion_call_shapes(monkeypatch) -> None:
    instance, calls = _fake_store(monkeypatch)
    one = UUID("00000000-0000-0000-0000-000000000001")
    two = UUID("00000000-0000-0000-0000-000000000002")
    vector = [1.5, -2.0]

    instance.create_task_artifact_chunk_embedding(
        task_artifact_chunk_id=one,
        embedding_config_id=two,
        dimensions=2,
        vector=vector,
    )
    _assert_next(
        calls,
        (
            "one",
            "create_task_artifact_chunk_embedding",
            _sql("INSERT_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL"),
            (one, two, 2, _json(vector)),
        ),
    )
    instance.get_task_artifact_chunk_embedding_optional(one)
    _assert_next(
        calls,
        ("optional", _sql("GET_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL"), (one,)),
    )
    instance.get_task_artifact_chunk_embedding_by_chunk_and_config_optional(
        task_artifact_chunk_id=one,
        embedding_config_id=two,
    )
    _assert_next(
        calls,
        (
            "optional",
            _sql("GET_TASK_ARTIFACT_CHUNK_EMBEDDING_BY_CHUNK_AND_CONFIG_SQL"),
            (one, two),
        ),
    )
    instance.list_task_artifact_chunk_embeddings_for_chunk(one)
    _assert_next(
        calls,
        ("all", _sql("LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_CHUNK_SQL"), (one,)),
    )
    instance.list_task_artifact_chunk_embeddings_for_artifact(two)
    _assert_next(
        calls,
        ("all", _sql("LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_ARTIFACT_SQL"), (two,)),
    )
    instance.update_task_artifact_chunk_embedding(
        task_artifact_chunk_embedding_id=one,
        dimensions=2,
        vector=vector,
    )
    _assert_next(
        calls,
        (
            "one",
            "update_task_artifact_chunk_embedding",
            _sql("UPDATE_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL"),
            (2, _json(vector), one),
        ),
    )
    instance.update_task_artifact_ingestion_status(
        task_artifact_id=two,
        ingestion_status="indexed",
    )
    _assert_next(
        calls,
        (
            "one",
            "update_task_artifact_ingestion_status",
            _sql("UPDATE_TASK_ARTIFACT_INGESTION_STATUS_SQL"),
            ("indexed", two),
        ),
    )
    assert not calls


def test_task_execution_step_and_run_call_shapes(monkeypatch) -> None:
    instance, calls = _fake_store(monkeypatch)
    one = UUID("00000000-0000-0000-0000-000000000001")
    two = UUID("00000000-0000-0000-0000-000000000002")
    three = UUID("00000000-0000-0000-0000-000000000003")

    instance.lock_task_steps(one)
    _assert_next(calls, ("advisory", _sql("LOCK_TASK_STEPS_SQL"), one))
    instance.create_task_step(
        task_id=one,
        sequence_no=3,
        kind="tool",
        status="pending",
        request={"r": 1},
        outcome={"o": 2},
        trace_id=two,
        trace_kind="task",
    )
    _assert_next(
        calls,
        (
            "locked",
            {
                "operation_name": "create_task_step",
                "lock_query": _sql("LOCK_TASK_STEPS_SQL"),
                "lock_key": one,
                "query": _sql("INSERT_TASK_STEP_SQL"),
                "params": (
                    one,
                    3,
                    None,
                    None,
                    None,
                    "tool",
                    "pending",
                    _json({"r": 1}),
                    _json({"o": 2}),
                    two,
                    "task",
                ),
            },
        ),
    )
    instance.get_task_step_optional(two)
    _assert_next(calls, ("optional", _sql("GET_TASK_STEP_SQL"), (two,)))
    instance.get_task_step_for_task_sequence_optional(task_id=one, sequence_no=3)
    _assert_next(
        calls,
        ("optional", _sql("GET_TASK_STEP_FOR_TASK_SEQUENCE_SQL"), (one, 3)),
    )
    instance.list_task_steps_for_task(one)
    _assert_next(calls, ("all", _sql("LIST_TASK_STEPS_FOR_TASK_SQL"), (one,)))
    instance.update_task_step_for_task_sequence_optional(
        task_id=one,
        sequence_no=3,
        status="complete",
        outcome={"done": True},
        trace_id=two,
        trace_kind="task",
    )
    _assert_next(
        calls,
        (
            "optional",
            _sql("UPDATE_TASK_STEP_FOR_TASK_SEQUENCE_SQL"),
            ("complete", _json({"done": True}), two, "task", one, 3),
        ),
    )
    instance.update_task_step_optional(
        task_step_id=three,
        status="failed",
        outcome={"error": True},
        trace_id=two,
        trace_kind="task",
    )
    _assert_next(
        calls,
        (
            "optional",
            _sql("UPDATE_TASK_STEP_SQL"),
            ("failed", _json({"error": True}), two, "task", three),
        ),
    )

    instance.lock_task_runs(one)
    _assert_next(calls, ("advisory", _sql("LOCK_TASK_RUNS_SQL"), one))
    instance.create_task_run(
        task_id=one,
        status="running",
        checkpoint={"cursor": 4},
        tick_count=1,
        step_count=2,
        max_ticks=10,
        retry_count=3,
        retry_cap=4,
        retry_posture="bounded",
        failure_class=None,
        stop_reason=None,
    )
    _assert_next(
        calls,
        (
            "one",
            "create_task_run",
            _sql("INSERT_TASK_RUN_SQL"),
            (one, "running", _json({"cursor": 4}), 1, 2, 10, 3, 4, "bounded", None, None),
        ),
    )
    instance.get_task_run_optional(two)
    _assert_next(calls, ("optional", _sql("GET_TASK_RUN_SQL"), (two,)))
    instance.list_task_runs_for_task(one)
    _assert_next(calls, ("all", _sql("LIST_TASK_RUNS_FOR_TASK_SQL"), (one,)))
    instance.update_task_run_optional(
        task_run_id=two,
        status="failed",
        checkpoint={"cursor": 5},
        tick_count=6,
        step_count=7,
        retry_count=8,
        retry_cap=9,
        retry_posture="retry",
        failure_class="transient",
        stop_reason="limit",
    )
    _assert_next(
        calls,
        (
            "optional",
            _sql("UPDATE_TASK_RUN_SQL"),
            ("failed", _json({"cursor": 5}), 6, 7, 8, 9, "retry", "transient", "limit", two),
        ),
    )
    instance.acquire_next_task_run_optional()
    _assert_next(calls, ("optional", _sql("ACQUIRE_NEXT_TASK_RUN_SQL"), None))
    assert not calls


def test_task_execution_tool_execution_and_budget_call_shapes(monkeypatch) -> None:
    instance, calls = _fake_store(monkeypatch)
    ids = [UUID(f"00000000-0000-0000-0000-{index:012d}") for index in range(1, 9)]
    one, two, three, four, five, six, seven, eight = ids

    instance.create_tool_execution(
        approval_id=one,
        task_step_id=two,
        thread_id=three,
        tool_id=four,
        trace_id=five,
        request_event_id=six,
        result_event_id=seven,
        status="complete",
        handler_key=None,
        request={"r": 1},
        tool={"t": 2},
        result={"o": 3},
    )
    _assert_next(
        calls,
        (
            "one",
            "create_tool_execution",
            _sql("INSERT_TOOL_EXECUTION_SQL"),
            (
                one,
                None,
                two,
                three,
                four,
                five,
                six,
                seven,
                "complete",
                None,
                None,
                _json({"r": 1}),
                _json({"t": 2}),
                _json({"o": 3}),
            ),
        ),
    )
    instance.get_tool_execution_optional(eight)
    _assert_next(calls, ("optional", _sql("GET_TOOL_EXECUTION_SQL"), (eight,)))
    instance.list_tool_executions()
    _assert_next(calls, ("all", _sql("LIST_TOOL_EXECUTIONS_SQL"), None))
    instance.get_tool_execution_by_idempotency_optional(
        task_run_id=one,
        approval_id=two,
        idempotency_key="key",
    )
    _assert_next(
        calls,
        (
            "optional",
            _sql("GET_TOOL_EXECUTION_BY_IDEMPOTENCY_SQL"),
            (one, two, "key"),
        ),
    )

    instance.create_execution_budget(
        tool_key=None,
        domain_hint=None,
        max_completed_executions=5,
    )
    _assert_next(
        calls,
        (
            "one",
            "create_execution_budget",
            _sql("INSERT_EXECUTION_BUDGET_SQL"),
            (None, None, None, None, 5, None, None),
        ),
    )
    instance.get_execution_budget_optional(one)
    _assert_next(calls, ("optional", _sql("GET_EXECUTION_BUDGET_SQL"), (one,)))
    instance.list_execution_budgets()
    _assert_next(calls, ("all", _sql("LIST_EXECUTION_BUDGETS_SQL"), None))
    instance.deactivate_execution_budget_optional(one)
    _assert_next(calls, ("optional", _sql("DEACTIVATE_EXECUTION_BUDGET_SQL"), (one,)))
    instance.supersede_execution_budget_optional(
        execution_budget_id=one,
        superseded_by_budget_id=two,
    )
    _assert_next(
        calls,
        ("optional", _sql("SUPERSEDE_EXECUTION_BUDGET_SQL"), (two, one)),
    )
    assert not calls


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("(str(task_id),)", "(task_id,)"),
        ("Jsonb(vector)", "vector"),
        ("lock_query=LOCK_TASK_STEPS_SQL", "lock_query=LOCK_TASK_RUNS_SQL"),
        (
            "Jsonb(checkpoint),\n            tick_count,",
            "tick_count,\n            Jsonb(checkpoint),",
        ),
        ("budget_id: UUID | None = None", "budget_id: UUID | None"),
    ),
)
def test_task_execution_receipt_rejects_weakened_carrier(old: str, new: str) -> None:
    source = CARRIER_PATH.read_text(encoding="utf-8")
    assert old in source
    weakened = source.replace(old, new, 1)
    assert _sha_bytes(weakened.encode()) != EXPECTED_CARRIER_SHA256


def test_task_execution_graft_guard_rejects_direct_alias_and_old_inline_method() -> None:
    source = STORE_PATH.read_text(encoding="utf-8")
    direct_alias = source.replace(
        "lock_task_workspaces = _bind_legacy_store_method(_task_execution.lock_task_workspaces)",
        "lock_task_workspaces = _task_execution.lock_task_workspaces",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(direct_alias)

    old_inline = source.replace(
        "    lock_task_workspaces = _bind_legacy_store_method(_task_execution.lock_task_workspaces)",
        "    def lock_task_workspaces(self):\n        raise NotImplementedError",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(old_inline)

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
from alicebot_api.legacy_store import conversation_memory as carrier


EventRow = object()


REPO_ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/store.py"
CARRIER_PATH = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/conversation_memory.py"
INIT_PATH = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/__init__.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

FIRST_CONSTANT_NAMES = tuple(
    """
    INSERT_USER_SQL GET_USER_SQL INSERT_THREAD_SQL GET_THREAD_SQL LIST_THREADS_SQL
    LIST_AGENT_PROFILES_SQL GET_AGENT_PROFILE_SQL INSERT_SESSION_SQL
    LIST_THREAD_SESSIONS_SQL LOCK_THREAD_EVENTS_SQL
    """.split()
)
SECOND_CONSTANT_NAMES = tuple(
    """
    INSERT_EVENT_SQL LIST_THREAD_EVENTS_SQL GET_THREAD_EVENT_TAIL_SQL
    LIST_EVENTS_BY_IDS_SQL INSERT_TRACE_SQL GET_TRACE_SQL LIST_TRACE_REVIEWS_SQL
    GET_TRACE_REVIEW_SQL INSERT_TRACE_EVENT_SQL LIST_TRACE_EVENTS_SQL
    INSERT_MEMORY_SQL GET_MEMORY_SQL LIST_MEMORIES_BY_IDS_SQL GET_MEMORY_BY_KEY_SQL
    GET_MEMORY_BY_KEY_AND_PROFILE_SQL LIST_MEMORIES_SQL COUNT_MEMORIES_SQL
    COUNT_MEMORIES_BY_STATUS_SQL COUNT_UNLABELED_REVIEW_MEMORIES_SQL
    LIST_REVIEW_MEMORIES_SQL LIST_REVIEW_MEMORIES_BY_STATUS_SQL
    LIST_UNLABELED_REVIEW_MEMORIES_SQL LIST_LIMITED_UNLABELED_REVIEW_MEMORIES_SQL
    LIST_CONTEXT_MEMORIES_SQL LIST_CONTEXT_MEMORIES_FOR_PROFILE_SQL
    UPDATE_MEMORY_SQL LOCK_MEMORY_REVISIONS_SQL INSERT_MEMORY_REVISION_SQL
    LIST_MEMORY_REVISIONS_SQL COUNT_MEMORY_REVISIONS_SQL
    LIST_LIMITED_MEMORY_REVISIONS_SQL UPSERT_FACT_PATTERN_SQL
    LIST_FACT_PATTERNS_SQL COUNT_FACT_PATTERNS_SQL GET_FACT_PATTERN_SQL
    DELETE_FACT_PATTERNS_NOT_IN_SQL DELETE_ALL_FACT_PATTERNS_SQL
    UPSERT_FACT_PLAYBOOK_SQL LIST_FACT_PLAYBOOKS_SQL COUNT_FACT_PLAYBOOKS_SQL
    GET_FACT_PLAYBOOK_SQL DELETE_FACT_PLAYBOOKS_NOT_IN_SQL
    DELETE_ALL_FACT_PLAYBOOKS_SQL INSERT_MEMORY_REVIEW_LABEL_SQL
    LIST_MEMORY_REVIEW_LABELS_SQL LIST_MEMORY_REVIEW_LABEL_COUNTS_SQL
    COUNT_LABELED_MEMORIES_SQL COUNT_UNLABELED_MEMORIES_SQL
    LIST_ALL_MEMORY_REVIEW_LABEL_COUNTS_SQL
    LIST_ACTIVE_MEMORY_REVIEW_LABEL_COUNTS_SQL INSERT_OPEN_LOOP_SQL
    GET_OPEN_LOOP_SQL LIST_OPEN_LOOPS_SQL LIST_OPEN_LOOPS_BY_STATUS_SQL
    LIST_LIMITED_OPEN_LOOPS_SQL LIST_LIMITED_OPEN_LOOPS_BY_STATUS_SQL
    COUNT_OPEN_LOOPS_SQL COUNT_OPEN_LOOPS_BY_STATUS_SQL UPDATE_OPEN_LOOP_STATUS_SQL
    """.split()
)
ERROR_CONSTANT_NAMES = (
    "UPDATE_EVENT_ERROR",
    "DELETE_EVENT_ERROR",
    "UPDATE_TRACE_EVENT_ERROR",
    "DELETE_TRACE_EVENT_ERROR",
)
CONSTANT_NAMES = FIRST_CONSTANT_NAMES + SECOND_CONSTANT_NAMES + ERROR_CONSTANT_NAMES
MAIN_METHOD_NAMES = tuple(
    """
    create_user get_user create_thread get_thread get_thread_optional list_threads
    list_agent_profiles get_agent_profile_optional create_session list_thread_sessions
    append_event append_event_if_tail list_thread_events list_events_by_ids
    create_trace get_trace get_trace_review_optional list_trace_reviews
    append_trace_event list_trace_events create_memory get_memory get_memory_optional
    list_memories_by_ids get_memory_by_key get_memory_by_key_and_profile list_memories
    count_memories count_unlabeled_review_memories list_review_memories
    list_unlabeled_review_memories list_context_memories
    list_context_memories_for_profile update_memory append_memory_revision
    count_memory_revisions list_memory_revisions upsert_fact_pattern
    list_fact_patterns count_fact_patterns get_fact_pattern_optional
    delete_fact_patterns_not_in upsert_fact_playbook list_fact_playbooks
    count_fact_playbooks get_fact_playbook_optional delete_fact_playbooks_not_in
    create_memory_review_label list_memory_review_labels
    list_memory_review_label_counts count_labeled_memories count_unlabeled_memories
    list_all_memory_review_label_counts list_active_memory_review_label_counts
    create_open_loop get_open_loop get_open_loop_optional list_open_loops
    count_open_loops update_open_loop_status_optional
    """.split()
)
TAIL_METHOD_NAMES = (
    "update_event",
    "delete_event",
    "update_trace_event",
    "delete_trace_event",
)
METHOD_NAMES = MAIN_METHOD_NAMES + TAIL_METHOD_NAMES

EXPECTED_CARRIER_SHA256 = "fc9c357413f66ca6312d03bc1ceb71267eb2b49a04f79dc62b5c55077cee7a48"
EXPECTED_INIT_SHA256 = "a37f75edba360fe16bbabad20ce130a57a2fa385e52a2842d6c7286a13dba744"
EXPECTED_CONSTANT_NAMES = "ba20e67b7bbd8d35916553cc410f6cfda8a2837325e3a5be3a94cce0c9fe115f"
EXPECTED_CONSTANT_AST = "82dd9faeceab019e8293c2c27ac4bfdfa5fdfb665f1b812f0d5b1c4cf0f1d1fc"
EXPECTED_CONSTANT_VALUES = "d84b4fd64fe1b8fcd60f9742a2260e0bf1b037f401db0dcde3c3e3c56c287e40"
EXPECTED_CONSTANT_NODE_SOURCE = "f01c7b6a6145010d58bbeee62709c7c9dc185c46e40fa01a47aee4e099ea5925"
EXPECTED_CONSTANT_SOURCES = (
    (2_003, "d07c1f84dc1964ae946bcc4c206c9370c6222d2522fce73e030ee953b43016c2"),
    (35_408, "c9307f5432acc67d2d753315b73147f134c08e01d8c7a8abc39667045faffa3f"),
    (350, "b7590d3b9c41163432960d54b39e0c99286bc9e094953be7c0f5fe7361e9a8b8"),
)
EXPECTED_COMBINED_CONSTANT_SOURCE = "385349c382a65028ae3cb97460a030e6edb5d2c1dd44d78b2f9849ec032f19bf"
EXPECTED_METHOD_NAMES = "da984e48ee2fda5e79747baeb75222efd9480dd05d694f9c03ddacadfc1ef322"
EXPECTED_METHOD_AST = "440e5a5019bbe87f9ee3dcc6bf2560185a4e2ce7aadae5a75d4c4862bc949bec"
EXPECTED_MAIN_METHOD_SOURCE = "ad9fbd24c8bfb66046784ee112c3de4bdd0aff6a39abf25e55e9b78dd410ee82"
EXPECTED_TAIL_METHOD_SOURCE = "800795f62689468c227f7a4201244db3968e28a2e4f62052b75811f9a377d6cc"
EXPECTED_METHOD_SOURCE = "8253840015da63d7f060b519d234d1654a50f31cd4d131318f95144330dcec5c"
EXPECTED_NORMALIZED_SOURCE = "10ccc24279b9db63b059d9962d96e8fa5a79181c8096a7140bf168d00feff845"
EXPECTED_STRING_VALUES = "81301e16959ad7b754b61fd303f6e525cc1edd4db54377af891f3afb22880312"
EXPECTED_STRING_SOURCE = "302d3be18359ec929179a1c4f3e4ead9f622fbf15a9333cbd07e2216ed4bc4e3"
EXPECTED_DOCS = "2fa22f516aa292e62d49b965a56a28a9fa04db4961ca09dd763c5e63337a23b6"
EXPECTED_DOC_LITERAL = "f8e66b03f577ca5e0332bb63b83c1def029a9cec52a330e6b00e379c65c0e0ec"
EXPECTED_RUNTIME = "10e87beb8ab8c462e789da82b23df965371e094e4627be1ccf3ceb530f9b15a0"
EXPECTED_SEMANTIC_CODE = "dce54959d2ddda7f966c24fa3fa9680f641077c989d1bda79d69a9ff4b83a073"
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
    return _sha_bytes(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode())


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
        method = value.args[0]
        assert isinstance(method, ast.Attribute) and method.attr == name
        assert isinstance(method.value, ast.Name) and method.value.id == "_conversation_memory"


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


def _semantic_manifest() -> list[list[object]]:
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


def _source_slice(source: str, first: ast.AST, last: ast.AST) -> str:
    lines = source.splitlines(keepends=True)
    return "".join(lines[first.lineno - 1 : last.end_lineno])


def _reconstruct_original(source: str, methods: list[ast.FunctionDef]) -> str:
    lines = source.splitlines(keepends=True)
    spans = [
        (node.lineno, node.end_lineno)
        for method in methods
        for node in ast.walk(method)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.end_lineno > node.lineno
    ]
    output: list[str] = []
    for number in range(methods[0].lineno, methods[-1].end_lineno + 1):
        line = lines[number - 1]
        continuation = any(start < number <= end for start, end in spans)
        if line.strip() and not continuation:
            line = f"    {line}"
        output.append(line)
    return "".join(output)


def test_conversation_carrier_pins_exact_sources_tokens_and_docstring() -> None:
    carrier_bytes = CARRIER_PATH.read_bytes()
    assert _sha_bytes(carrier_bytes) == EXPECTED_CARRIER_SHA256
    assert _sha_bytes(INIT_PATH.read_bytes()) == EXPECTED_INIT_SHA256
    source = carrier_bytes.decode()
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
    groups = (FIRST_CONSTANT_NAMES, SECOND_CONSTANT_NAMES, ERROR_CONSTANT_NAMES)
    constant_sources = [
        _source_slice(source, constants[group[0]], constants[group[-1]]) for group in groups
    ]
    assert [(len(item.encode()), _sha_bytes(item.encode())) for item in constant_sources] == list(
        EXPECTED_CONSTANT_SOURCES
    )
    assert _sha_bytes("".join(constant_sources).encode()) == EXPECTED_COMBINED_CONSTANT_SOURCE

    assert _compact_sha(list(methods)) == EXPECTED_METHOD_NAMES
    assert _compact_sha(
        [ast.dump(methods[name], include_attributes=False) for name in METHOD_NAMES]
    ) == EXPECTED_METHOD_AST
    main_nodes = [methods[name] for name in MAIN_METHOD_NAMES]
    tail_nodes = [methods[name] for name in TAIL_METHOD_NAMES]
    main_original = _reconstruct_original(source, main_nodes)
    tail_original = _reconstruct_original(source, tail_nodes)
    assert len(main_original.encode()) == 17_650
    assert len(tail_original.encode()) == 503
    assert _sha_bytes(main_original.encode()) == EXPECTED_MAIN_METHOD_SOURCE
    assert _sha_bytes(tail_original.encode()) == EXPECTED_TAIL_METHOD_SOURCE
    assert _sha_bytes((main_original + tail_original).encode()) == EXPECTED_METHOD_SOURCE

    normalized_rows = [
        [name, "".join(lines[methods[name].lineno - 1 : methods[name].end_lineno])]
        for name in METHOD_NAMES
    ]
    assert _compact_sha(normalized_rows) == EXPECTED_NORMALIZED_SOURCE
    string_nodes = {
        name: sorted(
            [
                node
                for node in ast.walk(methods[name])
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            ],
            key=lambda node: (
                node.lineno,
                node.col_offset,
                node.end_lineno,
                node.end_col_offset,
            ),
        )
        for name in METHOD_NAMES
    }
    assert _compact_sha(
        [[name, [node.value for node in string_nodes[name]]] for name in METHOD_NAMES]
    ) == EXPECTED_STRING_VALUES
    assert _compact_sha(
        [
            [name, [ast.get_source_segment(source, node) for node in string_nodes[name]]]
            for name in METHOD_NAMES
        ]
    ) == EXPECTED_STRING_SOURCE
    docs = [
        [name, ast.get_docstring(methods[name], clean=False)]
        for name in METHOD_NAMES
        if ast.get_docstring(methods[name], clean=False) is not None
    ]
    assert _compact_sha(docs) == EXPECTED_DOCS
    doc_node = methods["append_event_if_tail"].body[0]
    assert isinstance(doc_node, ast.Expr) and isinstance(doc_node.value, ast.Constant)
    literal = ast.get_source_segment(source, doc_node.value)
    assert literal is not None and len(literal.encode()) == 233
    assert _sha_bytes(literal.encode()) == EXPECTED_DOC_LITERAL
    assert "\n        The same transaction-scoped" in carrier.append_event_if_tail.__doc__
    comments = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(main_original + tail_original).readline)
        if token.type == tokenize.COMMENT
    ]
    assert _compact_sha(comments) == EXPECTED_NO_COMMENTS


def test_conversation_facade_preserves_three_seams_slots_and_hydration() -> None:
    _assert_facade_grafts()
    assert carrier.__all__ == list(CONSTANT_NAMES)
    for name in CONSTANT_NAMES:
        assert getattr(store, name) is getattr(carrier, name)
    tree = _tree(STORE_PATH)
    inline = {
        node.targets[0].id
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    assert inline.isdisjoint(CONSTANT_NAMES)
    imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "alicebot_api.legacy_store.conversation_memory"
    ]
    assert len(imports) == 3
    for node, expected in zip(
        imports,
        (FIRST_CONSTANT_NAMES, SECOND_CONSTANT_NAMES, ERROR_CONSTANT_NAMES),
        strict=True,
    ):
        assert [(alias.name, alias.asname) for alias in node.names] == [
            (name, name) for name in expected
        ]
    sql_names = [
        name
        for name, value in vars(store).items()
        if name.isupper() and isinstance(value, str)
    ]
    assert sql_names[:10] == list(FIRST_CONSTANT_NAMES)
    assert sql_names[10:14] == [
        "LOCK_TASK_STEPS_SQL",
        "LOCK_TASK_WORKSPACES_SQL",
        "LOCK_TASK_ARTIFACTS_SQL",
        "LOCK_TASK_RUNS_SQL",
    ]
    assert sql_names[14:73] == list(SECOND_CONSTANT_NAMES)
    assert sql_names[246] == "COUNT_MEMORY_OPERATIONS_SQL"
    assert sql_names[247:251] == list(ERROR_CONSTANT_NAMES)
    all_sql_values = [[name, getattr(store, name)] for name in sql_names]
    assert len(all_sql_values) == 251
    assert _compact_sha(all_sql_values) == EXPECTED_ALL_SQL_VALUES

    class_keys = list(store.ContinuityStore.__dict__)
    assert class_keys[11] == "_vector_literal"
    assert class_keys[12:72] == list(MAIN_METHOD_NAMES)
    assert class_keys[72] == "create_continuity_capture_event"
    assert class_keys[245] == "supersede_execution_budget_optional"
    assert class_keys[246:250] == list(TAIL_METHOD_NAMES)
    callable_names = [
        name for name, value in store.ContinuityStore.__dict__.items() if callable(value)
    ]
    assert len(callable_names) == 249
    assert _sha_bytes("\n".join(callable_names).encode()) == EXPECTED_METHOD_ORDER
    public_names = [name for name in vars(store) if not name.startswith("_")]
    assert len(public_names) == 330
    assert _compact_sha(public_names) == EXPECTED_PUBLIC_NAMES

    append_class = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AppendOnlyViolation"
    )
    continuity_class = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ContinuityStore"
    )
    hydration = [
        node
        for node in tree.body
        if append_class.end_lineno < node.lineno < continuity_class.lineno
        and isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "setattr"
    ]
    expected_hydration = (
        'setattr(_conversation_memory, "AppendOnlyViolation", AppendOnlyViolation)',
        'setattr(_continuity, "ContinuityStoreInvariantError", ContinuityStoreInvariantError)',
    )
    assert [ast.dump(node.value, include_attributes=False) for node in hydration] == [
        ast.dump(ast.parse(source).body[0].value, include_attributes=False)
        for source in expected_hydration
    ]
    assert carrier.AppendOnlyViolation is store.AppendOnlyViolation


def test_conversation_runtime_code_metadata_and_shared_binder_are_exact() -> None:
    assert _compact_sha(_runtime_manifest()) == EXPECTED_RUNTIME
    assert _compact_sha(_semantic_manifest()) == EXPECTED_SEMANTIC_CODE
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
        annotate = getattr(source, "__annotate__", None)
        if annotate is not None:
            rebound = method.__annotate__
            assert rebound is not annotate
            assert rebound.__globals__ is vars(store)
            assert rebound.__module__ == "alicebot_api.store"
            assert rebound.__qualname__ == "ContinuityStore.__annotate__"
            assert rebound.__code__.co_qualname == "ContinuityStore.__annotate__"
    functions = {
        node.name: node for node in _tree(STORE_PATH).body if isinstance(node, ast.FunctionDef)
    }
    for name, expected in EXPECTED_BINDER_AST.items():
        assert _sha_bytes(ast.dump(functions[name], include_attributes=False).encode()) == expected


def test_conversation_lazy_annotation_thunk_uses_facade_owner() -> None:
    def source(self):
        del self

    def __annotate__(format):
        return {"return": EventRow, "format": format}

    source.__annotate__ = __annotate__
    rebound = store._bind_legacy_store_method(source)
    assert rebound.__globals__ is vars(store)
    assert rebound.__annotate__.__globals__ is vars(store)
    assert rebound.__annotate__.__module__ == "alicebot_api.store"
    assert rebound.__annotate__.__qualname__ == "ContinuityStore.__annotate__"
    assert rebound.__annotate__(1)["return"] is store.EventRow


def test_conversation_carrier_imports_fresh_without_runtime_facade_cycle() -> None:
    tree = _tree(CARRIER_PATH)
    runtime_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert runtime_modules.isdisjoint(
        {
            "alicebot_api.store",
            "alicebot_api.main",
            "alicebot_api.vnext_store",
            "alicebot_api.sqlite_store",
        }
    )
    code = """
import sys
from alicebot_api.legacy_store import conversation_memory
assert 'alicebot_api.store' not in sys.modules
assert 'alicebot_api.main' not in sys.modules
assert 'alicebot_api.vnext_store' not in sys.modules
assert 'alicebot_api.sqlite_store' not in sys.modules
assert not hasattr(conversation_memory, 'AppendOnlyViolation')
assert conversation_memory.append_event_if_tail
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
    assert len(CARRIER_PATH.read_text().splitlines()) <= 1825
    assert len(STORE_PATH.read_text().splitlines()) <= 4350


def test_conversation_controls_and_installed_wheel_probe_follow_carrier() -> None:
    workflow = WORKFLOW_PATH.read_text()
    model_guard = (REPO_ROOT / "tests/unit/test_model_pack_retirement.py").read_text()
    removed_guard = (REPO_ROOT / "tests/unit/test_removed_public_contracts.py").read_text()
    protected_script = (REPO_ROOT / "scripts/check_protected_paths.py").read_text()
    assert model_guard.count('LEGACY_STORE_ROOT.rglob("*.py")') == 1
    assert removed_guard.count('LEGACY_STORE_ROOT.rglob("*.py")') == 1
    assert "apps/api/src/alicebot_api/legacy_store/*.py" in protected_script
    assert "from alicebot_api.legacy_store import conversation_memory" in workflow
    assert "conversation memory legacy store carrier resolved to checkout source" in workflow
    assert "moved conversation memory store method resolved to checkout source" in workflow
    assert "conversation_memory.AppendOnlyViolation is store_module.AppendOnlyViolation" in workflow
    assert "conversation_memory_moved_method.__globals__ is vars(store_module)" in workflow
    assert 'assert "The same transaction-scoped advisory lock" in (' in workflow
    assert 'assert "        The same transaction-scoped advisory lock" in (' not in workflow


class _FacadeJson:
    @staticmethod
    def dumps(value, *, sort_keys):
        assert sort_keys is True
        return f"facade-dumps:{json.dumps(value, sort_keys=True)}"


class _CarrierJson:
    @staticmethod
    def dumps(*_args, **_kwargs):
        raise AssertionError("carrier json global must not resolve")


def _fake_store(monkeypatch):
    calls: list[tuple[object, ...]] = []
    instance = object.__new__(store.ContinuityStore)
    instance._fetch_one = lambda operation, query, params=None: (
        calls.append(("one", operation, query, params)) or {"operation": operation}
    )
    instance._fetch_optional_one = lambda query, params=None: (
        calls.append(("optional", query, params)) or None
    )
    instance._fetch_all = lambda query, params=None: calls.append(("all", query, params)) or []
    instance._fetch_count = lambda query, params=None: calls.append(("count", query, params)) or 0
    instance._execute = lambda operation, query, params=None: calls.append(
        ("execute", operation, query, params)
    )
    instance._acquire_advisory_lock = lambda query, key: calls.append(
        ("advisory", query, key)
    )
    instance._fetch_one_with_lock = lambda **kwargs: calls.append(("locked", kwargs)) or {
        "operation": kwargs["operation_name"]
    }
    monkeypatch.setattr(store, "Jsonb", lambda value: ("facade-json", value))
    monkeypatch.setattr(carrier, "Jsonb", lambda value: ("carrier-json", value))
    monkeypatch.setattr(store, "json", _FacadeJson)
    monkeypatch.setattr(carrier, "json", _CarrierJson)
    for name in CONSTANT_NAMES:
        monkeypatch.setattr(store, name, f"facade:{name}")
        monkeypatch.setattr(carrier, name, f"carrier:{name}")
    return instance, calls


def _sql(name: str) -> str:
    return f"facade:{name}"


def _j(value: object) -> tuple[str, object]:
    return ("facade-json", value)


def test_conversation_append_lock_tail_comparison_and_empty_batches(monkeypatch) -> None:
    instance, calls = _fake_store(monkeypatch)
    thread = UUID("00000000-0000-0000-0000-000000000001")
    event = UUID("00000000-0000-0000-0000-000000000002")
    instance.append_event(thread, None, "user", {"text": "hello"})
    assert calls.pop(0) == (
        "locked",
        {
            "operation_name": "append_event",
            "lock_query": _sql("LOCK_THREAD_EVENTS_SQL"),
            "lock_key": thread,
            "query": _sql("INSERT_EVENT_SQL"),
            "params": (thread, thread, None, "user", _j({"text": "hello"})),
        },
    )

    for tail in (None, {"id": event, "sequence_no": 4}, {"id": thread, "sequence_no": 5}):
        calls.clear()

        def fetch_tail(query, params, *, value=tail):
            calls.append(("optional", query, params))
            return value

        instance._fetch_optional_one = fetch_tail
        result = instance.append_event_if_tail(
            thread,
            None,
            "assistant",
            {"text": "answer"},
            expected_event_id=event,
            expected_sequence_no=5,
        )
        assert result is None
        assert calls == [
            ("advisory", _sql("LOCK_THREAD_EVENTS_SQL"), thread),
            ("optional", _sql("GET_THREAD_EVENT_TAIL_SQL"), (thread,)),
        ]

    calls.clear()
    instance._fetch_optional_one = lambda query, params: (
        calls.append(("optional", query, params)) or {"id": event, "sequence_no": 5}
    )
    instance.append_event_if_tail(
        thread,
        None,
        "assistant",
        {"text": "answer"},
        expected_event_id=event,
        expected_sequence_no=5,
    )
    assert calls == [
        ("advisory", _sql("LOCK_THREAD_EVENTS_SQL"), thread),
        ("optional", _sql("GET_THREAD_EVENT_TAIL_SQL"), (thread,)),
        (
            "one",
            "append_event_if_tail",
            _sql("INSERT_EVENT_SQL"),
            (thread, thread, None, "assistant", _j({"text": "answer"})),
        ),
    ]
    calls.clear()
    assert instance.list_events_by_ids([]) == []
    assert instance.list_memories_by_ids([]) == []
    assert not calls


def test_conversation_memory_branch_sql_defaults_and_tuple_order(monkeypatch) -> None:
    instance, calls = _fake_store(monkeypatch)
    memory_id = UUID("00000000-0000-0000-0000-000000000001")
    instance.create_memory(
        memory_key="preference:theme",
        value={"theme": "dark"},
        status="active",
        source_event_ids=["event"],
    )
    assert calls.pop(0) == (
        "one",
        "create_memory",
        _sql("INSERT_MEMORY_SQL"),
        (
            "preference:theme",
            _j({"theme": "dark"}),
            "active",
            _j(["event"]),
            "preference",
            None,
            None,
            "unconfirmed",
            "deterministic",
            "promotable",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "assistant_default",
        ),
    )
    instance.update_memory(
        memory_id=memory_id,
        value="dark",
        status="superseded",
        source_event_ids=["event"],
    )
    assert calls.pop(0) == (
        "one",
        "update_memory",
        _sql("UPDATE_MEMORY_SQL"),
        (
            _j("dark"),
            "superseded",
            _j(["event"]),
            "preference",
            None,
            None,
            "unconfirmed",
            "deterministic",
            "promotable",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "superseded",
            memory_id,
        ),
    )
    instance.count_memories()
    instance.count_memories(status="active")
    instance.list_review_memories(status=None, limit=3)
    instance.list_review_memories(status="active", limit=4)
    instance.list_unlabeled_review_memories()
    instance.list_unlabeled_review_memories(limit=5)
    assert calls == [
        ("count", _sql("COUNT_MEMORIES_SQL"), None),
        ("count", _sql("COUNT_MEMORIES_BY_STATUS_SQL"), ("active",)),
        ("all", _sql("LIST_REVIEW_MEMORIES_SQL"), (3,)),
        ("all", _sql("LIST_REVIEW_MEMORIES_BY_STATUS_SQL"), ("active", 4)),
        ("all", _sql("LIST_UNLABELED_REVIEW_MEMORIES_SQL"), None),
        ("all", _sql("LIST_LIMITED_UNLABELED_REVIEW_MEMORIES_SQL"), (5,)),
    ]


def test_conversation_revision_json_fact_deletes_and_limit_branches(monkeypatch) -> None:
    instance, calls = _fake_store(monkeypatch)
    one = UUID("00000000-0000-0000-0000-000000000001")
    instance.append_memory_revision(
        memory_id=one,
        action="update",
        memory_key="key",
        previous_value=None,
        new_value=None,
        source_event_ids=["event"],
        candidate={"candidate": True},
    )
    assert calls.pop(0) == (
        "locked",
        {
            "operation_name": "append_memory_revision",
            "lock_query": _sql("LOCK_MEMORY_REVISIONS_SQL"),
            "lock_key": one,
            "query": _sql("INSERT_MEMORY_REVISION_SQL"),
            "params": (
                one,
                one,
                "update",
                "update",
                "key",
                _j(None),
                _j(None),
                _j(["event"]),
                _j({"candidate": True}),
                None,
                "{}",
            ),
        },
    )
    instance.append_memory_revision(
        memory_id=one,
        action="update",
        memory_key="key",
        previous_value={},
        new_value={},
        source_event_ids=[],
        candidate={},
    )
    assert calls.pop(0) == (
        "locked",
        {
            "operation_name": "append_memory_revision",
            "lock_query": _sql("LOCK_MEMORY_REVISIONS_SQL"),
            "lock_key": one,
            "query": _sql("INSERT_MEMORY_REVISION_SQL"),
            "params": (
                one,
                one,
                "update",
                "update",
                "key",
                _j({}),
                _j({}),
                _j([]),
                _j({}),
                "facade-dumps:{}",
                "facade-dumps:{}",
            ),
        },
    )
    instance.append_memory_revision(
        memory_id=one,
        action="update",
        memory_key="key",
        previous_value={"b": 2, "a": 1},
        new_value={"d": 4, "c": 3},
        source_event_ids=[],
        candidate={},
    )
    params = calls.pop(0)[1]["params"]
    assert params[-2:] == (
        'facade-dumps:{"a": 1, "b": 2}',
        'facade-dumps:{"c": 3, "d": 4}',
    )
    instance.list_memory_revisions(one)
    instance.list_memory_revisions(one, limit=2)
    instance.delete_fact_patterns_not_in([])
    instance.delete_fact_patterns_not_in([one])
    instance.delete_fact_playbooks_not_in([])
    instance.delete_fact_playbooks_not_in([one])
    assert calls == [
        ("all", _sql("LIST_MEMORY_REVISIONS_SQL"), (one,)),
        ("all", _sql("LIST_LIMITED_MEMORY_REVISIONS_SQL"), (one, 2)),
        ("execute", "delete_all_fact_patterns", _sql("DELETE_ALL_FACT_PATTERNS_SQL"), None),
        (
            "execute",
            "delete_fact_patterns_not_in",
            _sql("DELETE_FACT_PATTERNS_NOT_IN_SQL"),
            ([one],),
        ),
        ("execute", "delete_all_fact_playbooks", _sql("DELETE_ALL_FACT_PLAYBOOKS_SQL"), None),
        (
            "execute",
            "delete_fact_playbooks_not_in",
            _sql("DELETE_FACT_PLAYBOOKS_NOT_IN_SQL"),
            ([one],),
        ),
    ]


def test_conversation_trace_and_open_loop_exact_parameter_order(monkeypatch) -> None:
    instance, calls = _fake_store(monkeypatch)
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    thread_id = UUID("00000000-0000-0000-0000-000000000002")
    trace_id = UUID("00000000-0000-0000-0000-000000000003")
    open_loop_id = UUID("00000000-0000-0000-0000-000000000004")
    resolved_at = object()

    instance.create_trace(
        user_id=user_id,
        thread_id=thread_id,
        kind="context_compile",
        compiler_version="v1",
        status="complete",
        limits={"max_tokens": 512},
    )
    instance.append_trace_event(
        trace_id=trace_id,
        sequence_no=7,
        kind="candidate_selected",
        payload={"memory_id": "memory-1"},
    )
    instance.update_open_loop_status_optional(
        open_loop_id=open_loop_id,
        status="resolved",
        resolved_at=resolved_at,
        resolution_note="done",
    )

    assert calls == [
        (
            "one",
            "create_trace",
            _sql("INSERT_TRACE_SQL"),
            (
                user_id,
                thread_id,
                "context_compile",
                "v1",
                "complete",
                _j({"max_tokens": 512}),
            ),
        ),
        (
            "one",
            "append_trace_event",
            _sql("INSERT_TRACE_EVENT_SQL"),
            (trace_id, 7, "candidate_selected", _j({"memory_id": "memory-1"})),
        ),
        (
            "optional",
            _sql("UPDATE_OPEN_LOOP_STATUS_SQL"),
            (
                "resolved",
                "resolved",
                resolved_at,
                "resolved",
                "done",
                open_loop_id,
            ),
        ),
    ]


def test_conversation_open_loop_branches_and_append_only_exception_identity(monkeypatch) -> None:
    instance, calls = _fake_store(monkeypatch)
    instance.list_open_loops()
    instance.list_open_loops(limit=3)
    instance.list_open_loops(status="open")
    instance.list_open_loops(status="open", limit=4)
    instance.count_open_loops()
    instance.count_open_loops(status="open")
    assert calls == [
        ("all", _sql("LIST_OPEN_LOOPS_SQL"), None),
        ("all", _sql("LIST_LIMITED_OPEN_LOOPS_SQL"), (3,)),
        ("all", _sql("LIST_OPEN_LOOPS_BY_STATUS_SQL"), ("open",)),
        ("all", _sql("LIST_LIMITED_OPEN_LOOPS_BY_STATUS_SQL"), ("open", 4)),
        ("count", _sql("COUNT_OPEN_LOOPS_SQL"), None),
        ("count", _sql("COUNT_OPEN_LOOPS_BY_STATUS_SQL"), ("open",)),
    ]
    for name, error_name in zip(TAIL_METHOD_NAMES, ERROR_CONSTANT_NAMES, strict=True):
        monkeypatch.setattr(store, error_name, f"facade:{error_name}")
        monkeypatch.setattr(carrier, error_name, f"carrier:{error_name}")
        with pytest.raises(store.AppendOnlyViolation, match=f"facade:{error_name}"):
            getattr(instance, name)("ignored")


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("tail is None or tail[\"id\"] != expected_event_id", "tail is None"),
        ("tail[\"sequence_no\"] != expected_sequence_no", "False"),
        ("Jsonb(payload)", "payload"),
        ("json.dumps(previous_value, sort_keys=True)", "str(previous_value)"),
        ("if not pattern_ids:", "if False:"),
        ("if status is None and limit is None:", "if status is None:"),
        ("raise AppendOnlyViolation(UPDATE_EVENT_ERROR)", "return None"),
    ),
)
def test_conversation_receipt_rejects_behavior_weakening(old: str, new: str) -> None:
    source = CARRIER_PATH.read_text()
    assert old in source
    assert _sha_bytes(source.replace(old, new, 1).encode()) != EXPECTED_CARRIER_SHA256


def test_conversation_graft_guard_rejects_alias_inline_and_missing_hydration() -> None:
    source = STORE_PATH.read_text()
    alias = source.replace(
        "create_user = _bind_legacy_store_method(_conversation_memory.create_user)",
        "create_user = _conversation_memory.create_user",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(alias)
    inline = source.replace(
        "    create_user = _bind_legacy_store_method(_conversation_memory.create_user)",
        "    def create_user(self):\n        raise NotImplementedError",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(inline)
    assert 'setattr(_conversation_memory, "AppendOnlyViolation", AppendOnlyViolation)' in source

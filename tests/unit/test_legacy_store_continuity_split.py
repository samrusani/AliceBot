from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID

import pytest

import alicebot_api.store as store
from alicebot_api.legacy_store import continuity as carrier


REPO_ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/store.py"
CARRIER_PATH = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/continuity.py"
INIT_PATH = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/__init__.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

CONSTANT_NAMES = tuple(
    """
    INSERT_CONTINUITY_CAPTURE_EVENT_SQL GET_CONTINUITY_CAPTURE_EVENT_SQL
    LIST_CONTINUITY_CAPTURE_EVENTS_SQL COUNT_CONTINUITY_CAPTURE_EVENTS_SQL
    INSERT_CONTINUITY_OBJECT_SQL GET_CONTINUITY_OBJECT_BY_CAPTURE_EVENT_SQL
    GET_CONTINUITY_OBJECT_SQL GET_CONTINUITY_OBJECT_BY_COMMIT_FINGERPRINT_SQL
    LIST_CONTINUITY_OBJECTS_FOR_CAPTURE_EVENTS_SQL LIST_CONTINUITY_REVIEW_QUEUE_SQL
    COUNT_CONTINUITY_REVIEW_QUEUE_SQL LIST_CONTINUITY_RECALL_CANDIDATES_SQL
    INSERT_RETRIEVAL_RUN_SQL LIST_RETRIEVAL_RUNS_SQL GET_RETRIEVAL_RUN_SQL
    UPSERT_EVAL_SUITE_SQL LIST_EVAL_SUITES_SQL DELETE_EVAL_SUITES_NOT_IN_SQL
    UPSERT_EVAL_CASE_SQL LIST_EVAL_CASES_FOR_SUITE_SQL
    DELETE_EVAL_CASES_FOR_SUITE_NOT_IN_SQL INSERT_EVAL_RUN_SQL LIST_EVAL_RUNS_SQL
    GET_EVAL_RUN_SQL INSERT_EVAL_RESULT_SQL LIST_EVAL_RESULTS_FOR_RUN_SQL
    INSERT_RETRIEVAL_CANDIDATE_SQL LIST_RETRIEVAL_CANDIDATES_FOR_RUN_SQL
    UPSERT_CONTINUITY_ARTIFACT_SQL GET_CONTINUITY_ARTIFACT_SQL
    GET_CONTINUITY_ARTIFACT_BY_SOURCE_SQL UPSERT_CONTINUITY_ARTIFACT_COPY_SQL
    GET_CONTINUITY_ARTIFACT_COPY_SQL GET_CONTINUITY_ARTIFACT_COPY_BY_CHECKSUM_SQL
    LIST_CONTINUITY_ARTIFACT_COPIES_SQL UPSERT_CONTINUITY_ARTIFACT_SEGMENT_SQL
    GET_CONTINUITY_ARTIFACT_SEGMENT_SQL
    GET_CONTINUITY_ARTIFACT_SEGMENT_BY_SOURCE_ITEM_SQL
    LIST_CONTINUITY_ARTIFACT_SEGMENTS_SQL INSERT_CONTINUITY_OBJECT_EVIDENCE_LINK_SQL
    LIST_CONTINUITY_OBJECT_EVIDENCE_SQL UPDATE_CONTINUITY_OBJECT_SQL
    INSERT_CONTINUITY_CORRECTION_EVENT_SQL LIST_CONTINUITY_CORRECTION_EVENTS_SQL
    INSERT_CONTRADICTION_CASE_SQL UPDATE_CONTRADICTION_CASE_SQL
    GET_CONTRADICTION_CASE_SQL GET_CONTRADICTION_CASE_BY_CANONICAL_KEY_SQL
    LIST_CONTRADICTION_CASES_SQL COUNT_CONTRADICTION_CASES_SQL
    LIST_CONTRADICTION_CASES_FOR_OBJECTS_SQL UPSERT_TRUST_SIGNAL_SQL
    LIST_TRUST_SIGNALS_SQL COUNT_TRUST_SIGNALS_SQL
    INSERT_MEMORY_OPERATION_CANDIDATE_SQL GET_MEMORY_OPERATION_CANDIDATE_SQL
    GET_MEMORY_OPERATION_CANDIDATE_BY_SYNC_SOURCE_SQL
    LIST_MEMORY_OPERATION_CANDIDATES_SQL COUNT_MEMORY_OPERATION_CANDIDATES_SQL
    UPDATE_MEMORY_OPERATION_CANDIDATE_APPLICATION_SQL INSERT_MEMORY_OPERATION_SQL
    GET_MEMORY_OPERATION_SQL LIST_MEMORY_OPERATIONS_SQL COUNT_MEMORY_OPERATIONS_SQL
    """.split()
)
METHOD_NAMES = tuple(
    """
    create_continuity_capture_event get_continuity_capture_event_optional
    list_continuity_capture_events count_continuity_capture_events
    create_continuity_object get_continuity_object_by_capture_event_optional
    list_continuity_objects_for_capture_events get_continuity_object_optional
    get_continuity_object_by_commit_fingerprint_optional list_continuity_review_queue
    count_continuity_review_queue list_continuity_recall_candidates upsert_eval_suite
    list_eval_suites delete_eval_suites_not_in upsert_eval_case
    list_eval_cases_for_suite delete_eval_cases_for_suite_not_in create_eval_run
    list_eval_runs get_eval_run_optional create_eval_result list_eval_results_for_run
    create_retrieval_run list_retrieval_runs get_retrieval_run_optional
    create_retrieval_candidate list_retrieval_candidates_for_run
    upsert_continuity_artifact get_continuity_artifact_optional
    upsert_continuity_artifact_copy get_continuity_artifact_copy_optional
    list_continuity_artifact_copies upsert_continuity_artifact_segment
    get_continuity_artifact_segment_optional list_continuity_artifact_segments
    create_continuity_object_evidence_link list_continuity_object_evidence
    update_continuity_object_optional create_continuity_correction_event
    list_continuity_correction_events create_contradiction_case
    update_contradiction_case_optional get_contradiction_case_optional
    get_contradiction_case_by_canonical_key_optional list_contradiction_cases
    count_contradiction_cases list_contradiction_cases_for_objects
    upsert_trust_signal list_trust_signals count_trust_signals
    create_memory_operation_candidate get_memory_operation_candidate_optional
    get_memory_operation_candidate_by_sync_source_optional
    list_memory_operation_candidates count_memory_operation_candidates
    update_memory_operation_candidate_application create_memory_operation
    get_memory_operation_optional list_memory_operations count_memory_operations
    """.split()
)

EXPECTED_CARRIER_SHA256 = "a8ba55d165518a131c468872fc89fae4947329f33734ba660c955508d0da6780"
EXPECTED_INIT_SHA256 = "a37f75edba360fe16bbabad20ce130a57a2fa385e52a2842d6c7286a13dba744"
EXPECTED_CONSTANT_NAMES = "1c816f764a637855c25e8fe610dcd5e503fb534395755e9e72e4235913b14028"
EXPECTED_CONSTANT_AST = "b806a58f1957abea36e15b75b194cf1b9b320abdb97287e37d150058beac0a21"
EXPECTED_CONSTANT_VALUES = "1c3d59e965809ba83b5a43360b1a60432c5f8543307d968e05a44d7d01a789cd"
EXPECTED_METHOD_NAMES = "4a8d0f32e14d7837a89921cbf8524c3180c273ea872d89bed5dd65c736e1d116"
EXPECTED_METHOD_AST = "afd77c4b2d0206d75b40f2e2f660d5b26989808b472c63a13c6c6d4d0e41f7c0"
EXPECTED_RUNTIME = "14c0f6b1cbd3c8665439708d5640dd6cf8a92fa33aa6d0e2ba8754f762a03ecf"
EXPECTED_SEMANTIC_CODE = "acc0d7cbba4076f04037868d71581c88027724fd49bdb75197b410100a518b69"
EXPECTED_ALL_SQL_VALUES = "15bc0da3acbef4a859bf8ae05ccdf60cd6c4549e9baafe236e025a46659d0892"
EXPECTED_PUBLIC_NAMES = "8d1a83dfff470bfe767781bebfb8004430ba410650ce71c51da072d8ae6a2ddb"
EXPECTED_METHOD_ORDER = "6934333f4e3186b6c1ccfc0fcb173cfda80d367548e23f0722d6067053db951d"
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


def _class_members(node: ast.ClassDef) -> list[str]:
    result: list[str] = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append(child.name)
        elif isinstance(child, ast.Assign):
            result.extend(target.id for target in child.targets if isinstance(target, ast.Name))
    return result


def _assert_facade_grafts(source: str | None = None) -> None:
    class_node = _class_node(source)
    assert {
        node.name for node in class_node.body if isinstance(node, ast.FunctionDef)
    }.isdisjoint(METHOD_NAMES)
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
        assert isinstance(method.value, ast.Name) and method.value.id == "_continuity"


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


def _assert_carrier_receipts(source: str) -> None:
    assert _sha_bytes(source.encode()) == EXPECTED_CARRIER_SHA256
    constants, methods = _carrier_nodes()
    assert list(constants) == list(CONSTANT_NAMES)
    assert list(methods) == list(METHOD_NAMES)
    assert _compact_sha(list(CONSTANT_NAMES)) == EXPECTED_CONSTANT_NAMES
    assert _compact_sha(
        [ast.dump(constants[name], include_attributes=False) for name in CONSTANT_NAMES]
    ) == EXPECTED_CONSTANT_AST
    assert _compact_sha([[name, getattr(carrier, name)] for name in CONSTANT_NAMES]) == (
        EXPECTED_CONSTANT_VALUES
    )
    assert _compact_sha(list(METHOD_NAMES)) == EXPECTED_METHOD_NAMES
    assert _compact_sha(
        [ast.dump(methods[name], include_attributes=False) for name in METHOD_NAMES]
    ) == EXPECTED_METHOD_AST


def test_continuity_carrier_receipts_and_exact_ownership() -> None:
    source = CARRIER_PATH.read_text(encoding="utf-8")
    _assert_carrier_receipts(source)
    assert carrier.__all__ == list(CONSTANT_NAMES)
    assert _sha_bytes(INIT_PATH.read_bytes()) == EXPECTED_INIT_SHA256
    assert len(CONSTANT_NAMES) == 64
    assert len(METHOD_NAMES) == 61


def test_continuity_facade_preserves_constant_and_method_slots() -> None:
    _assert_facade_grafts()
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
        and node.module == "alicebot_api.legacy_store.continuity"
    ]
    assert len(imports) == 1
    assert [(alias.name, alias.asname) for alias in imports[0].names] == [
        (name, name) for name in CONSTANT_NAMES
    ]
    for name in CONSTANT_NAMES:
        assert getattr(store, name) is getattr(carrier, name)

    members = _class_members(_class_node())
    assert len(members) == 249
    assert members[71:132] == list(METHOD_NAMES)
    assert members[70] == "update_open_loop_status_optional"
    assert members[132] == "create_model_provider"
    assert _sha_bytes("\n".join(members).encode()) == EXPECTED_METHOD_ORDER

    public_names = [name for name in vars(store) if not name.startswith("_")]
    assert len(public_names) == 330
    assert _compact_sha(public_names) == EXPECTED_PUBLIC_NAMES
    sql_values = [
        [name, value]
        for name, value in vars(store).items()
        if name.isupper() and isinstance(value, str)
    ]
    assert len(sql_values) == 251
    assert _compact_sha(sql_values) == EXPECTED_ALL_SQL_VALUES


def test_continuity_runtime_metadata_globals_binder_and_hydration_are_exact() -> None:
    assert _compact_sha(_runtime_manifest()) == EXPECTED_RUNTIME
    assert _compact_sha(_semantic_manifest()) == EXPECTED_SEMANTIC_CODE
    assert store.ContinuityStore.__bases__ == (object,)
    assert store.ContinuityStore.__mro__ == (store.ContinuityStore, object)
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

    store_tree = _tree(STORE_PATH)
    functions = {
        node.name: node for node in store_tree.body if isinstance(node, ast.FunctionDef)
    }
    for name, expected in EXPECTED_BINDER_AST.items():
        assert _sha_bytes(ast.dump(functions[name], include_attributes=False).encode()) == expected

    invariant_class = next(
        node
        for node in store_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ContinuityStoreInvariantError"
    )
    continuity_class = next(
        node
        for node in store_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ContinuityStore"
    )
    hydration = [
        node.value
        for node in store_tree.body
        if invariant_class.end_lineno < node.lineno < continuity_class.lineno
        and isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "setattr"
    ]
    expected = ast.parse(
        'setattr(_continuity, "ContinuityStoreInvariantError", ContinuityStoreInvariantError)'
    ).body[0].value
    assert any(
        ast.dump(call, include_attributes=False) == ast.dump(expected, include_attributes=False)
        for call in hydration
    )
    assert carrier.ContinuityStoreInvariantError is store.ContinuityStoreInvariantError


def test_continuity_carrier_imports_without_facade_cycle_and_all_legacy_files_fit() -> None:
    tree = _tree(CARRIER_PATH)
    assert not any(
        isinstance(node, ast.ImportFrom) and node.module == "alicebot_api.store"
        for node in tree.body
    )
    code = """
import sys
from alicebot_api.legacy_store import continuity
assert 'alicebot_api.store' not in sys.modules
assert continuity.create_continuity_object
"""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    legacy_files = [STORE_PATH, *sorted(CARRIER_PATH.parent.glob("*.py"))]
    assert all(len(path.read_text(encoding="utf-8").splitlines()) < 4000 for path in legacy_files)
    assert len(CARRIER_PATH.read_text(encoding="utf-8").splitlines()) <= 2725


def test_continuity_installed_wheel_and_python314_probes_are_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for expected in (
        'python-version: ["3.13", "3.14"]',
        "from alicebot_api.legacy_store import continuity",
        "continuity_carrier_path = Path(continuity.__file__).resolve()",
        "store_module.ContinuityStore.create_continuity_object.__code__.co_filename",
        "continuity.ContinuityStoreInvariantError",
        "is store_module.ContinuityStoreInvariantError",
    ):
        assert expected in workflow


class _CreateObjectRecorder:
    def __init__(self, *, searchable: bool = True, promotable: bool = False) -> None:
        self.searchable = searchable
        self.promotable = promotable
        self.calls: list[tuple[object, ...]] = []
        self.default_calls: list[tuple[str, str]] = []

    def _default_continuity_searchable(self, object_type: str) -> bool:
        self.default_calls.append(("searchable", object_type))
        return self.searchable

    def _default_continuity_promotable(self, object_type: str) -> bool:
        self.default_calls.append(("promotable", object_type))
        return self.promotable

    def _fetch_one(self, operation: str, sql: str, params: tuple[object, ...]) -> object:
        self.calls.append((operation, sql, params))
        return {"ok": True}


def test_continuity_object_defaults_preserve_explicit_false_and_json_order(monkeypatch) -> None:
    monkeypatch.setattr(store, "Jsonb", lambda value: ("facade-json", value))
    monkeypatch.setattr(carrier, "Jsonb", lambda value: ("carrier-json", value))
    memory_id = UUID("00000000-0000-0000-0000-000000000001")
    recorder = _CreateObjectRecorder(searchable=True, promotable=True)
    result = store.ContinuityStore.create_continuity_object(
        recorder,
        capture_event_id=memory_id,
        object_type="decision",
        status="active",
        title="title",
        body={"body": 1},
        provenance={"source": 2},
        confidence=0.75,
        is_preserved=False,
        is_searchable=False,
        is_promotable=False,
    )
    assert result == {"ok": True}
    assert recorder.default_calls == []
    params = recorder.calls[0][2]
    assert params[3:6] == (False, False, False)
    assert params[7:9] == (("facade-json", {"body": 1}), ("facade-json", {"source": 2}))

    recorder = _CreateObjectRecorder(searchable=True, promotable=False)
    store.ContinuityStore.create_continuity_object(
        recorder,
        capture_event_id=memory_id,
        object_type="decision",
        status="active",
        title="title",
        body={},
        provenance={},
        confidence=1.0,
    )
    assert recorder.default_calls == [("searchable", "decision"), ("promotable", "decision")]
    assert recorder.calls[0][2][3:6] == (True, True, False)


class _NoFetch:
    def _fetch_all(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("empty batches must not query")


def test_continuity_empty_batches_short_circuit_but_eval_deletes_execute() -> None:
    no_fetch = _NoFetch()
    assert store.ContinuityStore.list_continuity_objects_for_capture_events(no_fetch, []) == []
    assert (
        store.ContinuityStore.list_contradiction_cases_for_objects(
            no_fetch,
            continuity_object_ids=[],
            statuses=("open",),
        )
        == []
    )

    calls: list[tuple[object, ...]] = []

    class ExecuteRecorder:
        def _execute(self, *args: object) -> None:
            calls.append(args)

    recorder = ExecuteRecorder()
    store.ContinuityStore.delete_eval_suites_not_in(recorder, [])
    suite_id = UUID("00000000-0000-0000-0000-000000000002")
    store.ContinuityStore.delete_eval_cases_for_suite_not_in(
        recorder,
        suite_id=suite_id,
        case_keys=[],
    )
    assert calls == [
        ("delete_eval_suites_not_in", store.DELETE_EVAL_SUITES_NOT_IN_SQL, ([],)),
        (
            "delete_eval_cases_for_suite_not_in",
            store.DELETE_EVAL_CASES_FOR_SUITE_NOT_IN_SQL,
            (suite_id, []),
        ),
    ]


class _OptionalRecorder:
    def __init__(self, results: list[object | None]) -> None:
        self.results = iter(results)
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def _fetch_optional_one(self, sql: str, params: tuple[object, ...]) -> object | None:
        self.calls.append((sql, params))
        return next(self.results)


@pytest.mark.parametrize("mode", ("created", "fallback", "missing"))
def test_continuity_artifact_upserts_keep_created_fallback_and_exact_error(
    monkeypatch, mode: str
) -> None:
    monkeypatch.setattr(store, "Jsonb", lambda value: ("facade-json", value))
    artifact_id = UUID("00000000-0000-0000-0000-000000000010")
    copy_id = UUID("00000000-0000-0000-0000-000000000011")
    created = {"created": True}
    existing = {"existing": True}
    results = [created] if mode == "created" else [None, existing if mode == "fallback" else None]
    recorder = _OptionalRecorder(results)
    if mode == "missing":
        with pytest.raises(
            store.ContinuityStoreInvariantError,
            match="upsert_continuity_artifact_segment did not return or reveal a segment row",
        ):
            store.ContinuityStore.upsert_continuity_artifact_segment(
                recorder,
                artifact_id=artifact_id,
                artifact_copy_id=copy_id,
                source_item_id="item",
                sequence_no=3,
                segment_kind="text",
                locator={"page": 2},
                raw_content="body",
                checksum_sha256="sha",
            )
        assert len(recorder.calls) == 2
        return
    result = store.ContinuityStore.upsert_continuity_artifact_segment(
        recorder,
        artifact_id=artifact_id,
        artifact_copy_id=copy_id,
        source_item_id="item",
        sequence_no=3,
        segment_kind="text",
        locator={"page": 2},
        raw_content="body",
        checksum_sha256="sha",
    )
    assert result == (created if mode == "created" else existing)
    assert len(recorder.calls) == (1 if mode == "created" else 2)
    assert recorder.calls[0][1][5] == ("facade-json", {"page": 2})


def test_continuity_optional_filters_remain_duplicated_in_exact_order() -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []

    class Recorder:
        def _fetch_all(self, sql: str, params: tuple[object, ...]) -> list[object]:
            calls.append((sql, params))
            return []

    recorder = Recorder()
    object_id = UUID("00000000-0000-0000-0000-000000000020")
    store.ContinuityStore.list_contradiction_cases(
        recorder,
        statuses=("open",),
        limit=5,
        continuity_object_id=object_id,
    )
    store.ContinuityStore.list_trust_signals(
        recorder,
        limit=6,
        continuity_object_id=object_id,
        signal_state="active",
        signal_type="evidence",
    )
    store.ContinuityStore.list_memory_operation_candidates(
        recorder,
        limit=7,
        policy_action="apply",
        operation_type="update",
        sync_fingerprint="fp",
    )
    store.ContinuityStore.list_memory_operations(recorder, limit=8, sync_fingerprint="fp")
    assert calls[0][1] == (("open",), object_id, object_id, object_id, 5)
    assert calls[1][1] == (object_id, object_id, "active", "active", "evidence", "evidence", 6)
    assert calls[2][1] == ("apply", "apply", "update", "update", "fp", "fp", 7)
    assert calls[3][1] == ("fp", "fp", 8)


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("if not capture_event_ids:", "if False:"),
        ("if not continuity_object_ids:", "if False:"),
        ("if created is not None:", "if created is None:"),
        ("Jsonb(locator)", "locator"),
        ("continuity_object_id,\n            continuity_object_id,", "continuity_object_id,"),
    ),
)
def test_continuity_receipt_rejects_old_or_weakened_carrier(old: str, new: str) -> None:
    source = CARRIER_PATH.read_text(encoding="utf-8")
    assert old in source
    weakened = source.replace(old, new, 1)
    with pytest.raises(AssertionError):
        _assert_carrier_receipts(weakened)


def test_continuity_guard_rejects_direct_alias_inline_method_and_missing_hydration() -> None:
    source = STORE_PATH.read_text(encoding="utf-8")
    _assert_facade_grafts(source)
    direct_alias = source.replace(
        "create_continuity_capture_event = _bind_legacy_store_method("
        "_continuity.create_continuity_capture_event)",
        "create_continuity_capture_event = _continuity.create_continuity_capture_event",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(direct_alias)
    inline = source.replace(
        "create_continuity_capture_event = _bind_legacy_store_method("
        "_continuity.create_continuity_capture_event)",
        "def create_continuity_capture_event(self):\n        return None",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(inline)
    assert (
        'setattr(_continuity, "ContinuityStoreInvariantError", ContinuityStoreInvariantError)'
        in source
    )

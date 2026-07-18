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
from alicebot_api.legacy_store import governance_integrations as carrier


ConsentRow = object()


REPO_ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/store.py"
CARRIER_PATH = (
    REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/governance_integrations.py"
)
INIT_PATH = REPO_ROOT / "apps/api/src/alicebot_api/legacy_store/__init__.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

CONSTANT_NAMES = (
    "INSERT_CONSENT_SQL",
    "GET_CONSENT_BY_KEY_SQL",
    "LIST_CONSENTS_SQL",
    "UPDATE_CONSENT_SQL",
    "INSERT_POLICY_SQL",
    "GET_POLICY_SQL",
    "LIST_POLICIES_SQL",
    "LIST_ACTIVE_POLICIES_SQL",
    "LIST_ACTIVE_POLICIES_FOR_PROFILE_SQL",
    "INSERT_TOOL_SQL",
    "GET_TOOL_SQL",
    "LIST_TOOLS_SQL",
    "LIST_ACTIVE_TOOLS_SQL",
    "INSERT_APPROVAL_SQL",
    "GET_APPROVAL_SQL",
    "LIST_APPROVALS_SQL",
    "UPDATE_APPROVAL_RESOLUTION_SQL",
    "UPDATE_APPROVAL_TASK_STEP_SQL",
    "UPDATE_APPROVAL_TASK_RUN_SQL",
    "INSERT_TASK_SQL",
    "GET_TASK_SQL",
    "GET_TASK_BY_APPROVAL_SQL",
    "LIST_TASKS_SQL",
    "UPDATE_TASK_STATUS_BY_APPROVAL_SQL",
    "UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL",
    "UPDATE_TASK_STATUS_SQL",
    "INSERT_GMAIL_ACCOUNT_SQL",
    "INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL",
    "GET_GMAIL_ACCOUNT_SQL",
    "GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL",
    "GET_GMAIL_ACCOUNT_CREDENTIAL_SQL",
    "UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL",
    "LIST_GMAIL_ACCOUNTS_SQL",
    "INSERT_CALENDAR_ACCOUNT_SQL",
    "INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL",
    "GET_CALENDAR_ACCOUNT_SQL",
    "GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL",
    "GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL",
    "LIST_CALENDAR_ACCOUNTS_SQL",
)
METHOD_NAMES = (
    "create_consent",
    "get_consent_by_key_optional",
    "list_consents",
    "update_consent",
    "create_policy",
    "get_policy_optional",
    "list_policies",
    "list_active_policies",
    "create_tool",
    "get_tool_optional",
    "list_tools",
    "list_active_tools",
    "create_approval",
    "get_approval_optional",
    "list_approvals",
    "resolve_approval_optional",
    "update_approval_task_step_optional",
    "update_approval_task_run_optional",
    "create_task",
    "get_task_optional",
    "get_task_by_approval_optional",
    "list_tasks",
    "update_task_status_by_approval_optional",
    "update_task_execution_by_approval_optional",
    "update_task_status_optional",
    "create_gmail_account",
    "create_gmail_account_credential",
    "get_gmail_account_optional",
    "get_gmail_account_credential_optional",
    "update_gmail_account_credential",
    "get_gmail_account_by_provider_account_id_optional",
    "list_gmail_accounts",
    "create_calendar_account",
    "create_calendar_account_credential",
    "get_calendar_account_optional",
    "get_calendar_account_credential_optional",
    "get_calendar_account_by_provider_account_id_optional",
    "list_calendar_accounts",
)
EXPECTED_PLACEHOLDER_COUNTS = (
    3,
    1,
    0,
    3,
    9,
    1,
    0,
    0,
    1,
    12,
    1,
    0,
    0,
    9,
    1,
    0,
    2,
    2,
    2,
    7,
    1,
    1,
    0,
    2,
    3,
    4,
    4,
    6,
    1,
    1,
    1,
    6,
    0,
    4,
    6,
    1,
    1,
    1,
    0,
)

EXPECTED_CARRIER_SHA256 = "cb81db01f1bde20e4ede553e82ddd8697617b25aac67be678871ead840523982"
EXPECTED_INIT_SHA256 = "a37f75edba360fe16bbabad20ce130a57a2fa385e52a2842d6c7286a13dba744"
EXPECTED_CONSTANT_NAMES = "6d680205e358c2c0f87b1da210819c45595643a0c049dadc052923785c3df5b3"
EXPECTED_CONSTANT_AST = "1988f4eee408b3a56d7f5aee1ebb82f85a7b701f08379153621274c8407eafe9"
EXPECTED_CONSTANT_VALUES = "bd1a19f6ecf9e4790c2c411e43c53c50c9903eaa6a61d4a69eba629f971e4c4e"
EXPECTED_CONSTANT_SOURCE = "d8f99e8cb8d6cdc8f82eef1e73fdda326b9701c347bab934f7ada401e76c5a7f"
EXPECTED_METHOD_NAMES = "80389f2025b56d7b175f988f8bcae4c387aa6b8cd0caf3d02f6f322a5f572abe"
EXPECTED_METHOD_AST = "4bc1b6f873182cef6d8cb83536db9d34b1b0d0f1fabfa821ec409b0d356680d3"
EXPECTED_ORIGINAL_METHOD_SOURCE = "1dbb632439d104413112783a806691afb6c0364fae1e4c1e165d0083a1905548"
EXPECTED_RUNTIME = "17cfcf42ea3072d2f5b498cb4d93af123a80e02dcecb85090c2719de73e73797"
EXPECTED_SEMANTIC_CODE = "0724948a5430f9a61259a07b7636a57bdec9e9a4bde2d5b9837ea8706a68730a"
EXPECTED_STRING_VALUES = "8ea9cd2d25a0c11b16aa007d279110351a361dee2009cc751bda7146e729f443"
EXPECTED_STRING_SOURCE = "b7d7db62d64aa21db8d08ed952ce1f452227de60ae432ae8c92b1b670c084001"
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
        assert isinstance(value.func, ast.Name)
        assert value.func.id == "_bind_legacy_store_method"
        assert len(value.args) == 1 and not value.keywords
        source_method = value.args[0]
        assert isinstance(source_method, ast.Attribute) and source_method.attr == name
        assert isinstance(source_method.value, ast.Name)
        assert source_method.value.id == "_governance_integrations"


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


def test_governance_carrier_pins_exact_constants_methods_and_sources() -> None:
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
    assert len(constant_slice.encode()) == 23_906
    assert _sha_bytes(constant_slice.encode()) == EXPECTED_CONSTANT_SOURCE
    method_slice = "".join(
        lines[methods[METHOD_NAMES[0]].lineno - 1 : methods[METHOD_NAMES[-1]].end_lineno]
    )
    original_indentation = "".join(
        f"    {line}" if line.strip() else line for line in method_slice.splitlines(keepends=True)
    )
    assert len(original_indentation.encode()) == 11_769
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


def test_governance_facade_owns_exact_runtime_and_public_surfaces() -> None:
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
        and node.module == "alicebot_api.legacy_store.governance_integrations"
    ]
    assert len(imports) == 1
    assert [(alias.name, alias.asname) for alias in imports[0].names] == [
        (name, name) for name in CONSTANT_NAMES
    ]

    class_keys = list(store.ContinuityStore.__dict__)
    assert class_keys[164:202] == list(METHOD_NAMES)
    assert class_keys[163] == "list_entity_edges_for_entities"
    assert class_keys[202] == "lock_task_workspaces"
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
    assert tuple(getattr(carrier, name).count("%s") for name in CONSTANT_NAMES) == (
        EXPECTED_PLACEHOLDER_COUNTS
    )


def test_governance_rebound_methods_preserve_metadata_code_and_facade_globals() -> None:
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


def test_governance_lazy_annotation_thunk_uses_facade_globals_and_metadata() -> None:
    def source(self):
        del self

    def __annotate__(format):
        return {"return": ConsentRow, "format": format}

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
    assert rebound_annotate(1)["return"] is store.ConsentRow


def test_governance_carrier_has_no_runtime_facade_cycle_and_imports_fresh() -> None:
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
from alicebot_api.legacy_store import governance_integrations
assert 'alicebot_api.store' not in sys.modules
assert 'alicebot_api.main' not in sys.modules
assert 'alicebot_api.vnext_store' not in sys.modules
assert 'alicebot_api.sqlite_store' not in sys.modules
assert governance_integrations.create_consent
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
    assert len(STORE_PATH.read_text(encoding="utf-8").splitlines()) <= 7000


def test_governance_scanners_protection_and_installed_wheel_proof_follow_carrier() -> None:
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
    assert "from alicebot_api.legacy_store import governance_integrations" in workflow
    assert "governance legacy store carrier resolved to checkout source" in workflow
    assert "moved governance store method resolved to checkout source" in workflow
    assert "store_module.ContinuityStore.create_consent" in workflow
    assert "inspect.get_annotations(\n              governance_moved_method" in workflow


def _fake_store(monkeypatch) -> tuple[store.ContinuityStore, list[tuple[object, ...]]]:
    calls: list[tuple[object, ...]] = []
    instance = object.__new__(store.ContinuityStore)

    def fetch_one(operation, query, params=None):
        calls.append(("one", operation, query, params))
        return {"operation": operation}

    def fetch_optional_one(query, params=None):
        calls.append(("optional", query, params))
        return {"query": query}

    def fetch_all(query, params=None):
        calls.append(("all", query, params))
        return []

    instance._fetch_one = fetch_one
    instance._fetch_optional_one = fetch_optional_one
    instance._fetch_all = fetch_all
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


def test_governance_consent_policy_and_tool_calls_preserve_branches_and_order(
    monkeypatch,
) -> None:
    instance, calls = _fake_store(monkeypatch)
    first = UUID("00000000-0000-0000-0000-000000000001")

    instance.create_consent(consent_key="mail", status="granted", metadata={"a": 1})
    _assert_next(
        calls,
        ("one", "create_consent", _sql("INSERT_CONSENT_SQL"), ("mail", "granted", _json({"a": 1}))),
    )
    instance.get_consent_by_key_optional("mail")
    _assert_next(calls, ("optional", _sql("GET_CONSENT_BY_KEY_SQL"), ("mail",)))
    instance.list_consents()
    _assert_next(calls, ("all", _sql("LIST_CONSENTS_SQL"), None))
    instance.update_consent(consent_id=first, status="revoked", metadata={"b": 2})
    _assert_next(
        calls,
        ("one", "update_consent", _sql("UPDATE_CONSENT_SQL"), ("revoked", _json({"b": 2}), first)),
    )

    instance.create_policy(
        name="policy",
        action="read",
        scope="workspace",
        effect="allow",
        priority=7,
        active=True,
        conditions={"c": 3},
        required_consents=["mail"],
    )
    _assert_next(
        calls,
        (
            "one",
            "create_policy",
            _sql("INSERT_POLICY_SQL"),
            (None, "policy", "read", "workspace", "allow", 7, True, _json({"c": 3}), _json(["mail"])),
        ),
    )
    instance.get_policy_optional(first)
    _assert_next(calls, ("optional", _sql("GET_POLICY_SQL"), (first,)))
    instance.list_policies()
    _assert_next(calls, ("all", _sql("LIST_POLICIES_SQL"), None))
    instance.list_active_policies()
    _assert_next(calls, ("all", _sql("LIST_ACTIVE_POLICIES_SQL"), None))
    instance.list_active_policies(agent_profile_id="profile")
    _assert_next(
        calls,
        ("all", _sql("LIST_ACTIVE_POLICIES_FOR_PROFILE_SQL"), ("profile",)),
    )

    instance.create_tool(
        tool_key="calendar.read",
        name="Calendar",
        description="Read calendar",
        version="1",
        metadata_version="2",
        active=False,
        tags=["calendar"],
        action_hints=["read"],
        scope_hints=["workspace"],
        domain_hints=["time"],
        risk_hints=["low"],
        metadata={"m": 4},
    )
    _assert_next(
        calls,
        (
            "one",
            "create_tool",
            _sql("INSERT_TOOL_SQL"),
            (
                "calendar.read",
                "Calendar",
                "Read calendar",
                "1",
                "2",
                False,
                _json(["calendar"]),
                _json(["read"]),
                _json(["workspace"]),
                _json(["time"]),
                _json(["low"]),
                _json({"m": 4}),
            ),
        ),
    )
    instance.get_tool_optional(first)
    _assert_next(calls, ("optional", _sql("GET_TOOL_SQL"), (first,)))
    instance.list_tools()
    _assert_next(calls, ("all", _sql("LIST_TOOLS_SQL"), None))
    instance.list_active_tools()
    _assert_next(calls, ("all", _sql("LIST_ACTIVE_TOOLS_SQL"), None))
    assert not calls


def test_governance_approval_and_task_calls_preserve_defaults_and_tuple_order(
    monkeypatch,
) -> None:
    instance, calls = _fake_store(monkeypatch)
    one = UUID("00000000-0000-0000-0000-000000000001")
    two = UUID("00000000-0000-0000-0000-000000000002")
    three = UUID("00000000-0000-0000-0000-000000000003")
    four = UUID("00000000-0000-0000-0000-000000000004")

    instance.create_approval(
        thread_id=one,
        tool_id=two,
        status="pending",
        request={"r": 1},
        tool={"t": 2},
        routing={"route": 3},
        routing_trace_id=three,
    )
    _assert_next(
        calls,
        (
            "one",
            "create_approval",
            _sql("INSERT_APPROVAL_SQL"),
            (one, two, None, None, "pending", _json({"r": 1}), _json({"t": 2}), _json({"route": 3}), three),
        ),
    )
    instance.get_approval_optional(one)
    _assert_next(calls, ("optional", _sql("GET_APPROVAL_SQL"), (one,)))
    instance.list_approvals()
    _assert_next(calls, ("all", _sql("LIST_APPROVALS_SQL"), None))
    instance.resolve_approval_optional(approval_id=one, status="accepted")
    _assert_next(
        calls,
        ("optional", _sql("UPDATE_APPROVAL_RESOLUTION_SQL"), ("accepted", one)),
    )
    instance.update_approval_task_step_optional(approval_id=one, task_step_id=two)
    _assert_next(
        calls,
        ("optional", _sql("UPDATE_APPROVAL_TASK_STEP_SQL"), (two, one)),
    )
    instance.update_approval_task_run_optional(approval_id=one, task_run_id=None)
    _assert_next(
        calls,
        ("optional", _sql("UPDATE_APPROVAL_TASK_RUN_SQL"), (None, one)),
    )

    instance.create_task(
        thread_id=one,
        tool_id=two,
        status="queued",
        request={"r": 1},
        tool={"t": 2},
        latest_approval_id=three,
        latest_execution_id=four,
    )
    _assert_next(
        calls,
        (
            "one",
            "create_task",
            _sql("INSERT_TASK_SQL"),
            (one, two, "queued", _json({"r": 1}), _json({"t": 2}), three, four),
        ),
    )
    instance.get_task_optional(one)
    _assert_next(calls, ("optional", _sql("GET_TASK_SQL"), (one,)))
    instance.get_task_by_approval_optional(two)
    _assert_next(calls, ("optional", _sql("GET_TASK_BY_APPROVAL_SQL"), (two,)))
    instance.list_tasks()
    _assert_next(calls, ("all", _sql("LIST_TASKS_SQL"), None))
    instance.update_task_status_by_approval_optional(approval_id=one, status="running")
    _assert_next(
        calls,
        ("optional", _sql("UPDATE_TASK_STATUS_BY_APPROVAL_SQL"), ("running", one)),
    )
    instance.update_task_execution_by_approval_optional(
        approval_id=one,
        latest_execution_id=four,
        status="complete",
    )
    _assert_next(
        calls,
        ("optional", _sql("UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL"), ("complete", four, one)),
    )
    instance.update_task_status_optional(
        task_id=one,
        status="failed",
        latest_approval_id=None,
        latest_execution_id=None,
    )
    _assert_next(
        calls,
        ("optional", _sql("UPDATE_TASK_STATUS_SQL"), ("failed", None, None, one)),
    )
    assert not calls


def test_governance_gmail_and_calendar_calls_preserve_jsonb_none_and_lookup_order(
    monkeypatch,
) -> None:
    instance, calls = _fake_store(monkeypatch)
    account_id = UUID("00000000-0000-0000-0000-000000000001")

    instance.create_gmail_account(
        provider_account_id="provider",
        email_address="alice@example.com",
        display_name=None,
        scope="mail.read",
    )
    _assert_next(
        calls,
        (
            "one",
            "create_gmail_account",
            _sql("INSERT_GMAIL_ACCOUNT_SQL"),
            ("provider", "alice@example.com", None, "mail.read"),
        ),
    )
    instance.create_gmail_account_credential(
        gmail_account_id=account_id,
        auth_kind="oauth",
        credential_kind="refresh",
        secret_manager_kind="local",
        secret_ref="ref",
        credential_blob={"token": "x"},
    )
    _assert_next(
        calls,
        (
            "one",
            "create_gmail_account_credential",
            _sql("INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL"),
            (account_id, "oauth", "refresh", "local", "ref", _json({"token": "x"})),
        ),
    )
    instance.create_gmail_account_credential(
        gmail_account_id=account_id,
        auth_kind="oauth",
        credential_kind="refresh",
        secret_manager_kind="external",
        secret_ref="ref",
        credential_blob=None,
    )
    _assert_next(
        calls,
        (
            "one",
            "create_gmail_account_credential",
            _sql("INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL"),
            (account_id, "oauth", "refresh", "external", "ref", None),
        ),
    )
    instance.get_gmail_account_optional(account_id)
    _assert_next(calls, ("optional", _sql("GET_GMAIL_ACCOUNT_SQL"), (account_id,)))
    instance.get_gmail_account_credential_optional(account_id)
    _assert_next(
        calls,
        ("optional", _sql("GET_GMAIL_ACCOUNT_CREDENTIAL_SQL"), (account_id,)),
    )
    instance.update_gmail_account_credential(
        gmail_account_id=account_id,
        auth_kind="oauth",
        credential_kind="access",
        secret_manager_kind="local",
        secret_ref=None,
        credential_blob={"token": "y"},
    )
    _assert_next(
        calls,
        (
            "one",
            "update_gmail_account_credential",
            _sql("UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL"),
            ("oauth", "access", "local", None, _json({"token": "y"}), account_id),
        ),
    )
    instance.get_gmail_account_by_provider_account_id_optional("provider")
    _assert_next(
        calls,
        ("optional", _sql("GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL"), ("provider",)),
    )
    instance.list_gmail_accounts()
    _assert_next(calls, ("all", _sql("LIST_GMAIL_ACCOUNTS_SQL"), None))

    instance.create_calendar_account(
        provider_account_id="calendar-provider",
        email_address="alice@example.com",
        display_name="Alice",
        scope="calendar.read",
    )
    _assert_next(
        calls,
        (
            "one",
            "create_calendar_account",
            _sql("INSERT_CALENDAR_ACCOUNT_SQL"),
            ("calendar-provider", "alice@example.com", "Alice", "calendar.read"),
        ),
    )
    instance.create_calendar_account_credential(
        calendar_account_id=account_id,
        auth_kind="oauth",
        credential_kind="refresh",
        secret_manager_kind="local",
        secret_ref="ref",
        credential_blob={"token": "z"},
    )
    _assert_next(
        calls,
        (
            "one",
            "create_calendar_account_credential",
            _sql("INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL"),
            (account_id, "oauth", "refresh", "local", "ref", _json({"token": "z"})),
        ),
    )
    instance.create_calendar_account_credential(
        calendar_account_id=account_id,
        auth_kind="oauth",
        credential_kind="refresh",
        secret_manager_kind="external",
        secret_ref="ref",
        credential_blob=None,
    )
    _assert_next(
        calls,
        (
            "one",
            "create_calendar_account_credential",
            _sql("INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL"),
            (account_id, "oauth", "refresh", "external", "ref", None),
        ),
    )
    instance.get_calendar_account_optional(account_id)
    _assert_next(calls, ("optional", _sql("GET_CALENDAR_ACCOUNT_SQL"), (account_id,)))
    instance.get_calendar_account_credential_optional(account_id)
    _assert_next(
        calls,
        ("optional", _sql("GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL"), (account_id,)),
    )
    instance.get_calendar_account_by_provider_account_id_optional("calendar-provider")
    _assert_next(
        calls,
        (
            "optional",
            _sql("GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL"),
            ("calendar-provider",),
        ),
    )
    instance.list_calendar_accounts()
    _assert_next(calls, ("all", _sql("LIST_CALENDAR_ACCOUNTS_SQL"), None))
    assert not calls


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("if agent_profile_id is None:", "if False:"),
        (
            "None if credential_blob is None else Jsonb(credential_blob)",
            "Jsonb(credential_blob)",
        ),
        (
            "(status, latest_execution_id, approval_id)",
            "(latest_execution_id, status, approval_id)",
        ),
        ("UPDATE_APPROVAL_RESOLUTION_SQL", '"UPDATE approvals"'),
    ),
)
def test_governance_receipt_rejects_weakened_carrier(old: str, new: str) -> None:
    source = CARRIER_PATH.read_text(encoding="utf-8")
    assert old in source
    weakened = source.replace(old, new, 1)
    assert _sha_bytes(weakened.encode()) != EXPECTED_CARRIER_SHA256


def test_governance_graft_guard_rejects_direct_alias_and_old_inline_method() -> None:
    source = STORE_PATH.read_text(encoding="utf-8")
    direct_alias = source.replace(
        "create_consent = _bind_legacy_store_method(_governance_integrations.create_consent)",
        "create_consent = _governance_integrations.create_consent",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(direct_alias)

    old_inline = source.replace(
        "    create_consent = _bind_legacy_store_method(_governance_integrations.create_consent)",
        "    def create_consent(self):\n        raise NotImplementedError",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_facade_grafts(old_inline)

from __future__ import annotations

import ast
import dataclasses
import hashlib
import inspect
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import typing
from uuid import UUID

from pydantic import TypeAdapter

import alicebot_api.contracts as contracts
from alicebot_api._contracts import execution
from alicebot_api._contracts import governance


REPO_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/contracts.py"
EXECUTION_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/execution.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EXPECTED_CARRIER_SHA256 = "0f35a9c77f4955ac4798aaa3f379ebda603e62fbf4ac99ab026fa7b1e0f5e38f"
EXPECTED_PUBLIC_NAMES = "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
EXPECTED_NAMES = "8258bf3229ca0ecdb9611b556c41db94b870b61d360a07ad45f533aa22ed950c"
EXPECTED_AST = "59d28a6a8628f8126f143d04450626e5163e4ea30a02183965b93a5f974f16c7"
EXPECTED_SOURCE = "a6ea2a9c672e9ab7f45b9efdd8d0764b8c757d1e1fb380a76c3c580229db71c1"
EXPECTED_METADATA = "0b628237666f51300ef36304093692d8d00578f0f4a63558f60356e91bfd66de"
EXPECTED_RAW_ANNOTATIONS = "50658182e6d131a273d0dd3eddb0f17d513318a9d5cda7ba27f76dabeba1d76c"
EXPECTED_TYPE_HINTS = "291ece6c366b31dd7ebd0fba9f53509c69e625e03a0521b3deb2d5398b17ebfc"
EXPECTED_DATACLASS_FIELDS = "4195c881b189d6f6fcb243c5a6bf3ae2b05dea6120ada0ec4a655e572311f2ce"
EXPECTED_TYPED_DICTS = "bd8d05c18a4906b76fb7444fefedaae7c3c387d6d88d74815db31e3de943484e"
EXPECTED_SCHEMAS = "6852f15eac3fea034cf75e4a401c0d96a6e0783d4f77ced0b5f0c9f930253dff"
EXPECTED_EXPLICIT_METHODS = "90ce64643ac3319dd3b3e5780bff7469186caf00ebb2f04645d18fbd3605b31c"
EXPECTED_GENERATED_METHODS = "720b64aaaffbc4f063e7670ad2425c5da3b799ee8fd689cd0635458a974d5fcf"
EXPECTED_EXPLICIT_SEMANTICS = "a5815ea53cbb1e2e25e0590f452f7972bc7b3dd5b755c2fa3b93bb783dd0721e"

EXPLICIT_METHODS = (
    ("ProxyExecutionRequestInput", "as_payload"),
    ("ExecutionBudgetCreateInput", "as_payload"),
    ("ExecutionBudgetDeactivateInput", "as_payload"),
    ("ExecutionBudgetSupersedeInput", "as_payload"),
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _compact_digest(value: object) -> str:
    return _digest(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _classes() -> list[ast.ClassDef]:
    return [
        node
        for node in _tree(EXECUTION_PATH).body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    ]


def _names() -> list[str]:
    return [node.name for node in _classes()]


def _literal_assignment(tree: ast.Module, name: str) -> object:
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == name
    ]
    assert len(matches) == 1
    return ast.literal_eval(matches[0].value)


def _signature(value: object) -> str:
    try:
        return str(inspect.signature(value))
    except (TypeError, ValueError) as exc:
        return f"!{type(exc).__name__}:{exc}"


def test_execution_source_scope_and_two_facade_slots_are_exact() -> None:
    source = EXECUTION_PATH.read_text(encoding="utf-8")
    nodes = _classes()
    names = _names()
    assert _digest(source) == EXPECTED_CARRIER_SHA256
    assert len(nodes) == len(names) == 35
    assert _digest("\n".join(names)) == EXPECTED_NAMES
    assert (
        _digest("\n".join(ast.dump(node, include_attributes=False) for node in nodes))
        == EXPECTED_AST
    )
    assert (
        _digest("\n".join(ast.get_source_segment(source, node) or "" for node in nodes))
        == EXPECTED_SOURCE
    )

    chunks = (names[:4], names[4:])
    facade_tree = _tree(FACADE_PATH)
    imports = [
        node
        for node in facade_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "alicebot_api._contracts.execution"
    ]
    assert len(imports) == 2
    assert [[alias.name for alias in node.names] for node in imports] == list(chunks)
    assert _literal_assignment(
        facade_tree, "_EXECUTION_CONTRACT_CLASS_NAMES"
    ) == tuple(names)
    assert _literal_assignment(
        facade_tree, "_EXECUTION_EXPLICIT_METHODS"
    ) == EXPLICIT_METHODS

    public_names = [name for name in vars(contracts) if not name.startswith("_")]
    assert len(public_names) == 875
    assert _digest("\n".join(public_names)) == EXPECTED_PUBLIC_NAMES
    assert public_names[458:464] == ["ApprovalRejectInput", *chunks[0], "PersistedMemoryRecord"]
    assert public_names[842:875] == [
        "ApprovalResolutionResponse",
        *chunks[1],
        "isoformat_or_none",
    ]
    local_names = [
        node.name
        for node in facade_tree.body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    ]
    assert local_names == []


def test_execution_runtime_receipts_and_payloads_are_exact() -> None:
    classes = [(name, getattr(contracts, name)) for name in _names()]
    metadata = []
    raw_annotations = []
    resolved_hints = []
    dataclass_fields = []
    typed_dicts = []
    schemas = []
    explicit_methods = []
    generated_methods = []
    semantics = []
    for name, contract_class in classes:
        assert contract_class is getattr(execution, name)
        assert contract_class.__module__ == "alicebot_api.contracts"
        assert contract_class.__qualname__ == name
        assert pickle.loads(pickle.dumps(contract_class)) is contract_class
        metadata.append(
            [
                name,
                contract_class.__module__,
                contract_class.__qualname__,
                _signature(contract_class),
                [[base.__module__, base.__qualname__] for base in contract_class.__bases__],
                list(getattr(contract_class, "__match_args__", ())),
            ]
        )
        annotations = getattr(contract_class, "__annotations__", {})
        raw_annotations.append(
            [name, [[key, repr(annotation)] for key, annotation in annotations.items()]]
        )
        resolved_hints.append(
            [
                name,
                [
                    [key, repr(annotation)]
                    for key, annotation in typing.get_type_hints(
                        contract_class, include_extras=True
                    ).items()
                ],
            ]
        )
        if dataclasses.is_dataclass(contract_class):
            fields = []
            for contract_field in dataclasses.fields(contract_class):
                factory = contract_field.default_factory
                factory_repr = (
                    "<MISSING>"
                    if factory is dataclasses.MISSING
                    else (
                        f"{getattr(factory, '__module__', '')}."
                        f"{getattr(factory, '__qualname__', repr(factory))}"
                    )
                )
                default_repr = (
                    "<MISSING>"
                    if contract_field.default is dataclasses.MISSING
                    else repr(contract_field.default)
                )
                fields.append(
                    [
                        contract_field.name,
                        repr(contract_field.type),
                        default_repr,
                        factory_repr,
                        contract_field.init,
                        contract_field.repr,
                        contract_field.hash,
                        contract_field.compare,
                        contract_field.kw_only,
                        repr(contract_field.metadata),
                    ]
                )
            dataclass_fields.append([name, fields])
        if typing.is_typeddict(contract_class):
            typed_dicts.append(
                [
                    name,
                    bool(contract_class.__total__),
                    sorted(contract_class.__required_keys__),
                    sorted(contract_class.__optional_keys__),
                ]
            )
        schemas.append([name, TypeAdapter(contract_class).json_schema()])
        for method_name, method in vars(contract_class).items():
            if not inspect.isfunction(method):
                continue
            row = [
                name,
                method_name,
                method.__module__,
                method.__qualname__,
                method.__globals__.get("__name__"),
                str(inspect.signature(method)),
                repr(method.__annotations__),
                method.__doc__,
            ]
            if method_name == "as_payload":
                assert method.__globals__ is vars(contracts)
                assert Path(method.__code__.co_filename).resolve() == EXECUTION_PATH.resolve()
                explicit_methods.append(row)
                code = method.__code__
                semantics.append(
                    [
                        f"{name}.{method_name}",
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
            else:
                generated_methods.append(row)

    assert len(dataclass_fields) == 5
    assert len(typed_dicts) == 30
    assert len(explicit_methods) == 4
    assert len(generated_methods) == 40
    assert _compact_digest(metadata) == EXPECTED_METADATA
    assert _compact_digest(raw_annotations) == EXPECTED_RAW_ANNOTATIONS
    assert _compact_digest(resolved_hints) == EXPECTED_TYPE_HINTS
    assert _compact_digest(dataclass_fields) == EXPECTED_DATACLASS_FIELDS
    assert _compact_digest(typed_dicts) == EXPECTED_TYPED_DICTS
    assert _compact_digest(schemas) == EXPECTED_SCHEMAS
    assert _compact_digest(explicit_methods) == EXPECTED_EXPLICIT_METHODS
    assert _compact_digest(generated_methods) == EXPECTED_GENERATED_METHODS
    assert _compact_digest(semantics) == EXPECTED_EXPLICIT_SEMANTICS

    assert execution.ApprovalRecord is governance.ApprovalRecord
    assert execution.ToolRecord is governance.ToolRecord
    assert execution.ToolRoutingRequestRecord is governance.ToolRoutingRequestRecord
    assert contracts.ProxyExecutionBudgetPrecheckTracePayload.__orig_bases__ == (
        contracts.ExecutionBudgetDecisionRecord,
    )
    assert execution.ProxyExecutionBudgetPrecheckTracePayload.__orig_bases__ == (
        execution.ExecutionBudgetDecisionRecord,
    )

    one = UUID(int=1)
    two = UUID(int=2)
    assert contracts.ProxyExecutionRequestInput(one).as_payload() == {
        "approval_id": str(one),
        "task_run_id": None,
    }
    assert contracts.ExecutionBudgetCreateInput(3).as_payload() == {
        "max_completed_executions": 3,
        "tool_key": None,
        "domain_hint": None,
        "rolling_window_seconds": None,
        "agent_profile_id": None,
    }
    assert contracts.ExecutionBudgetDeactivateInput(one, two).as_payload() == {
        "thread_id": str(one),
        "execution_budget_id": str(two),
        "requested_action": "deactivate",
    }
    assert contracts.ExecutionBudgetSupersedeInput(one, two, 4).as_payload() == {
        "thread_id": str(one),
        "execution_budget_id": str(two),
        "requested_action": "supersede",
        "max_completed_executions": 4,
    }


def test_execution_carrier_imports_fresh_and_both_orders_normalize() -> None:
    imports = {
        node.module
        for node in _tree(EXECUTION_PATH).body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imports == {
        "__future__",
        "dataclasses",
        "typing",
        "uuid",
        "alicebot_api._contracts.common",
        "alicebot_api._contracts.governance",
        "alicebot_api.store",
    }
    assert len(EXECUTION_PATH.read_text(encoding="utf-8").splitlines()) < 4_000
    assert len(FACADE_PATH.read_text(encoding="utf-8").splitlines()) < 4_000

    standalone = """
import dataclasses
import pickle
import sys
import typing
from alicebot_api._contracts import execution, governance
assert 'alicebot_api.contracts' not in sys.modules
names = __EXECUTION_NAMES__
classes = [getattr(execution, name) for name in names]
assert len(classes) == 35
assert sum(dataclasses.is_dataclass(value) for value in classes) == 5
assert sum(typing.is_typeddict(value) for value in classes) == 30
assert execution.ApprovalRecord is governance.ApprovalRecord
assert all(pickle.loads(pickle.dumps(value)) is value for value in classes)
""".replace("__EXECUTION_NAMES__", repr(tuple(_names())))
    result = subprocess.run(
        [sys.executable, "-c", standalone],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    checks = """
import dataclasses
import hashlib
import inspect
import pickle
import sys
import typing
names = contracts._EXECUTION_CONTRACT_CLASS_NAMES
classes = [getattr(execution, name) for name in names]
dataclass_contracts = [value for value in classes if dataclasses.is_dataclass(value)]
typed_dict_contracts = [value for value in classes if typing.is_typeddict(value)]
assert len(classes) == 35
assert len(dataclass_contracts) == 5
assert len(typed_dict_contracts) == 30
assert all(getattr(contracts, name) is getattr(execution, name) for name in names)
assert all(value.__init__.__globals__ is vars(contracts) for value in dataclass_contracts)
assert not [(value.__name__, name) for value in dataclass_contracts for name, method in vars(value).items() if inspect.isfunction(method) and method.__globals__ is vars(execution)]
assert all(pickle.loads(pickle.dumps(value)) is value for value in classes)
for value in classes:
    typing.get_type_hints(value, include_extras=True)
assert contracts.ProxyExecutionBudgetPrecheckTracePayload.__orig_bases__ == (contracts.ExecutionBudgetDecisionRecord,)
assert execution.ApprovalRecord is governance.ApprovalRecord
assert len(contracts._EXECUTION_EXPLICIT_METHODS) == 4
assert all(getattr(getattr(contracts, owner), method).__globals__ is vars(contracts) for owner, method in contracts._EXECUTION_EXPLICIT_METHODS)
assert hashlib.sha256('\\n'.join(name for name in vars(contracts) if not name.startswith('_')).encode()).hexdigest() == 'c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed'
if sys.version_info >= (3, 14):
    for value in typed_dict_contracts:
        annotate = value.__annotate__
        assert annotate.__module__ == 'typing'
        assert annotate.__globals__ is vars(typing)
        assert isinstance(annotate(1), dict)
    for value in dataclass_contracts:
        init_annotate = value.__init__.__annotate__
        assert init_annotate.__module__ == 'dataclasses'
        assert init_annotate.__globals__['__name__'] == 'dataclasses'
        assert value.__replace__.__module__ == 'dataclasses'
    for owner, method in contracts._EXECUTION_EXPLICIT_METHODS:
        annotate = getattr(getattr(getattr(contracts, owner), method), '__annotate__')
        assert annotate.__module__ == 'alicebot_api.contracts'
        assert annotate.__globals__ is vars(contracts)
"""
    import_orders = (
        "import alicebot_api.contracts as contracts\nfrom alicebot_api._contracts import execution, governance\n",
        "from alicebot_api._contracts import execution, governance\nimport alicebot_api.contracts as contracts\n",
    )
    for import_order in import_orders:
        result = subprocess.run(
            [sys.executable, "-c", import_order + checks],
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


def test_execution_installed_wheel_proofs_are_pinned_twice() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert workflow.count(
        "from alicebot_api._contracts import execution as contracts_execution"
    ) == 2
    for repeated in (
        "execution_classes = [",
        "assert len(execution_classes) == 35",
        "assert len(execution_dataclasses) == 5",
        "assert len(execution_typed_dicts) == 30",
        "assert len(contracts_module._EXECUTION_EXPLICIT_METHODS) == 4",
        "execution_precheck_orig_bases = (",
        "execution_init_annotate.__module__ == \"dataclasses\"",
        "execution_explicit_annotate.__globals__ is vars(contracts_module)",
    ):
        assert workflow.count(repeated) == 2
    assert workflow.count("execution contracts carrier resolved to checkout source") == 2

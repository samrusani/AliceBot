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

from pydantic import TypeAdapter

import alicebot_api.contracts as contracts
from alicebot_api._contracts import integrations
from alicebot_api._contracts import tasks


REPO_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/contracts.py"
INTEGRATIONS_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/integrations.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EXPECTED_CARRIER_SHA256 = "eeba1a8328bbbee3db57097ddffc721789f484b8ad72be0d4583848007fe9281"
EXPECTED_PUBLIC_NAMES = "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
EXPECTED_NAMES = "c3eba0cd5616a74abeabebd1732cbe8882030e8f32a91bcff64eb337dd2362d8"
EXPECTED_AST = "3e3536a53d094ee31c6f4b90a62d333748af86e00db4235d2a1cab63d1161f9c"
EXPECTED_SOURCE = "f4f9064bb357f4d7868cc38d56156e0b32961d7cb21571db20056597e6629d42"
EXPECTED_METADATA = "bc156f81c2c5638c9c2757f7f96f9068ba29f20872026c75dd4adf5ab0c0ab92"
EXPECTED_RAW_ANNOTATIONS = "5e2fbf53dea7a2b85afff99d5bd17a569052cfeaaddedcf6cc985fb6c8d89775"
EXPECTED_TYPE_HINTS = "97c9b4c3b2cbfe4b06642235c66714b7cf7a1ecaa86d27b27ea969c370b0991b"
EXPECTED_DATACLASS_FIELDS = "0083810515d126a5fd30a1afe6b0cead502cc26ca86f0f7f02bd923ecedf55ce"
EXPECTED_TYPED_DICTS = "ea55b1395342e6dfd6dfa5187913fdac1aff2cc17cfa19a0cc48159a1d61dd16"
EXPECTED_SCHEMAS = "fe3aa13be672a9194f7dc7f40f4af580e3b04f3dc3eab06a240dd3ab8573ce90"
EXPECTED_GENERATED_METHODS = "4325c50c6bbf471d3a2dbe6e7ac00dff945e7fac3ce0e17e76c738f9144d1edc"


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
        for node in _tree(INTEGRATIONS_PATH).body
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


def test_integrations_source_scope_and_facade_slot_are_exact() -> None:
    source = INTEGRATIONS_PATH.read_text(encoding="utf-8")
    nodes = _classes()
    names = _names()
    assert _digest(source) == EXPECTED_CARRIER_SHA256
    assert len(nodes) == len(names) == 22
    assert _digest("\n".join(names)) == EXPECTED_NAMES
    assert (
        _digest("\n".join(ast.dump(node, include_attributes=False) for node in nodes))
        == EXPECTED_AST
    )
    assert (
        _digest("\n".join(ast.get_source_segment(source, node) or "" for node in nodes))
        == EXPECTED_SOURCE
    )

    facade_tree = _tree(FACADE_PATH)
    imports = [
        node
        for node in facade_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "alicebot_api._contracts.integrations"
    ]
    assert len(imports) == 1
    assert [alias.name for alias in imports[0].names] == names
    assert _literal_assignment(
        facade_tree, "_INTEGRATION_CONTRACT_CLASS_NAMES"
    ) == tuple(names)

    public_names = [name for name in vars(contracts) if not name.startswith("_")]
    assert len(public_names) == 875
    assert _digest("\n".join(public_names)) == EXPECTED_PUBLIC_NAMES
    assert public_names[746:770] == [
        "TaskRunMutationResponse",
        *names,
        "TaskWorkspaceCreateInput",
    ]

    local_names = [
        node.name
        for node in facade_tree.body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    ]
    assert len(local_names) == 0
    assert _digest("\n".join(local_names)) == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert not set(local_names).intersection(names)
    assert "ExecutionBudgetRecord" not in local_names
    assert "ProxyExecutionRequestInput" not in local_names
    assert not hasattr(integrations, "ExecutionBudgetRecord")
    assert not hasattr(integrations, "ProxyExecutionRequestInput")


def test_integrations_runtime_metadata_hints_schemas_and_methods_are_exact() -> None:
    classes = [(name, getattr(contracts, name)) for name in _names()]
    metadata = []
    raw_annotations = []
    resolved_hints = []
    dataclass_fields = []
    typed_dicts = []
    schemas = []
    generated_methods = []
    for name, contract_class in classes:
        assert contract_class is getattr(integrations, name)
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
            if inspect.isfunction(method):
                generated_methods.append(
                    [
                        name,
                        method_name,
                        method.__module__,
                        method.__qualname__,
                        method.__globals__.get("__name__"),
                        str(inspect.signature(method)),
                        repr(method.__annotations__),
                        method.__doc__,
                    ]
                )

    assert len(dataclass_fields) == 5
    assert len(typed_dicts) == 17
    assert len(generated_methods) == 40
    assert _compact_digest(metadata) == EXPECTED_METADATA
    assert _compact_digest(raw_annotations) == EXPECTED_RAW_ANNOTATIONS
    assert _compact_digest(resolved_hints) == EXPECTED_TYPE_HINTS
    assert _compact_digest(dataclass_fields) == EXPECTED_DATACLASS_FIELDS
    assert _compact_digest(typed_dicts) == EXPECTED_TYPED_DICTS
    assert _compact_digest(schemas) == EXPECTED_SCHEMAS
    assert _compact_digest(generated_methods) == EXPECTED_GENERATED_METHODS

    assert integrations.TaskArtifactRecord is tasks.TaskArtifactRecord
    assert integrations.TaskArtifactChunkListSummary is tasks.TaskArtifactChunkListSummary
    gmail_hints = typing.get_type_hints(
        contracts.GmailMessageIngestionResponse, include_extras=True
    )
    calendar_hints = typing.get_type_hints(
        contracts.CalendarEventIngestionResponse, include_extras=True
    )
    assert gmail_hints["artifact"] is tasks.TaskArtifactRecord
    assert gmail_hints["summary"] is tasks.TaskArtifactChunkListSummary
    assert calendar_hints["artifact"] is tasks.TaskArtifactRecord
    assert calendar_hints["summary"] is tasks.TaskArtifactChunkListSummary
    assert inspect.signature(contracts.CalendarEventListInput).parameters[
        "limit"
    ].default == 20


def test_integrations_carrier_imports_fresh_and_contract_files_fit_cap() -> None:
    imports = {
        node.module
        for node in _tree(INTEGRATIONS_PATH).body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imports == {
        "__future__",
        "dataclasses",
        "datetime",
        "typing",
        "uuid",
        "alicebot_api._contracts.common",
        "alicebot_api._contracts.tasks",
    }
    assert len(INTEGRATIONS_PATH.read_text(encoding="utf-8").splitlines()) < 4_000
    assert len(FACADE_PATH.read_text(encoding="utf-8").splitlines()) < 4_000

    code = """
import dataclasses
import pickle
import sys
import typing
from alicebot_api._contracts import integrations, tasks
assert 'alicebot_api.contracts' not in sys.modules
names = __INTEGRATION_NAMES__
assert len(names) == 22
assert sum(dataclasses.is_dataclass(getattr(integrations, name)) for name in names) == 5
assert sum(typing.is_typeddict(getattr(integrations, name)) for name in names) == 17
assert integrations.TaskArtifactRecord is tasks.TaskArtifactRecord
assert integrations.TaskArtifactChunkListSummary is tasks.TaskArtifactChunkListSummary
assert all(pickle.loads(pickle.dumps(getattr(integrations, name))) is getattr(integrations, name) for name in names)
assert not hasattr(integrations, 'ExecutionBudgetRecord')
assert not hasattr(integrations, 'ProxyExecutionRequestInput')
""".replace("__INTEGRATION_NAMES__", repr(tuple(_names())))
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_integrations_facade_normalizes_both_import_orders() -> None:
    checks = """
import dataclasses
import hashlib
import inspect
import pickle
import sys
import typing
names = contracts._INTEGRATION_CONTRACT_CLASS_NAMES
classes = [getattr(integrations, name) for name in names]
dataclass_contracts = [value for value in classes if dataclasses.is_dataclass(value)]
typed_dict_contracts = [value for value in classes if typing.is_typeddict(value)]
assert len(classes) == 22
assert len(dataclass_contracts) == 5
assert len(typed_dict_contracts) == 17
assert all(getattr(contracts, name) is getattr(integrations, name) for name in names)
assert all(value.__init__.__globals__ is vars(contracts) for value in dataclass_contracts)
assert not [(value.__name__, name) for value in dataclass_contracts for name, method in vars(value).items() if inspect.isfunction(method) and method.__globals__ is vars(integrations)]
assert all(pickle.loads(pickle.dumps(value)) is value for value in classes)
for value in classes:
    typing.get_type_hints(value, include_extras=True)
assert integrations.TaskArtifactRecord is tasks.TaskArtifactRecord
assert integrations.TaskArtifactChunkListSummary is tasks.TaskArtifactChunkListSummary
assert typing.get_type_hints(contracts.GmailMessageIngestionResponse, include_extras=True)['artifact'] is tasks.TaskArtifactRecord
assert typing.get_type_hints(contracts.CalendarEventIngestionResponse, include_extras=True)['summary'] is tasks.TaskArtifactChunkListSummary
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
        replace = value.__replace__
        assert replace.__module__ == 'dataclasses'
        assert replace.__globals__['__name__'] == 'dataclasses'
"""
    import_orders = (
        "import alicebot_api.contracts as contracts\nfrom alicebot_api._contracts import integrations, tasks\n",
        "from alicebot_api._contracts import integrations, tasks\nimport alicebot_api.contracts as contracts\n",
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


def test_integrations_installed_wheel_proofs_are_pinned_twice() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert workflow.count(
        "from alicebot_api._contracts import integrations as contracts_integrations"
    ) == 2
    for repeated in (
        "integrations_classes = [",
        "assert len(integrations_classes) == 22",
        "assert len(integrations_dataclasses) == 5",
        "assert len(integrations_typed_dicts) == 17",
        "integrations_gmail_hints = typing.get_type_hints(",
        "integrations_init_annotate.__module__ == \"dataclasses\"",
    ):
        assert workflow.count(repeated) == 2
    assert workflow.count("integrations contracts carrier resolved to checkout source") == 2

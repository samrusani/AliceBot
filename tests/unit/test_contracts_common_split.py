from __future__ import annotations

import ast
import dataclasses
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import typing
from types import FunctionType

from pydantic import TypeAdapter

import alicebot_api.contracts as contracts
from alicebot_api._contracts import common


REPO_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/contracts.py"
COMMON_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/common.py"
INIT_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/__init__.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EXPECTED_PUBLIC_NAMES = "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
EXPECTED_COMMON_SHA256 = "9938e30678a99983dfd803b781190af816b43d600a030d060e4306ce1afd72ea"
EXPECTED_COMMON_NAMES = "2865b41bb271ffa30dddd5605ef77c0d33a9d714ec32ab82020960b9d77b652e"
EXPECTED_COMMON_AST = "1646f89f5ecf66cf1c42fae16d41ca4a9360f6a6c07310f85b829e00781a5bb0"
EXPECTED_COMMON_SOURCE = "50d1fb2ab27ac42b1e7280a61246fa57c4975b6a076a3f6c17e2bcbaabe028c3"
EXPECTED_COMMON_VALUES = "d93c7113fcbacf6288f7ae5112dd9bab3355f5ccd6a1f5e810a701bdbc3699cb"
EXPECTED_BINDER_AST = "bf890b5cc598a0397ffcc64e670899f490227d0357a963e6861ecbf00fc021da"
EXPECTED_CLASS_NAMES = "800efe279368c901919d54004a95a066efa8b18cf64ec080408e9c020a0df62d"
EXPECTED_CLASS_METADATA = "bfbe366edf6f3d7fe408727bfb4cd95078f7be6486c9e91bb2947fefad40de1a"
EXPECTED_RAW_ANNOTATIONS = "28f581472262d2d345790e3161bde62018a9c1e643ac28872aabf2c9fc2a7ea3"
EXPECTED_TYPE_HINTS = "dce4823bc83d2e3ed7acedb27ad25c7c2d453eedcf4f0a67598224cf73ce48ed"
EXPECTED_DATACLASS_FIELDS = "fcec1a6b160b0bb4f2794de9d61df60d0805629a6aab9c3d6f865ad6ac14cd3e"
EXPECTED_TYPED_DICTS = "6112e494ab98454d7e294df67ea2cceebc6e23f77c703e62f029f13d616da3f5"
EXPECTED_SCHEMAS = "b0a5b70cf4b3b929ad6c636356dd0a6ddce82cff2877b8ead1447c925d2a5e17"
EXPECTED_EXPLICIT_METHODS = "9e294b386330bdbaabca5b8e38416ce7fe435d99ab8dc18a99bd7533a7460f66"
EXPECTED_GENERATED_METHODS = "f983123691be1fc2e8911bcc754b2fdfdd98a7f5e938d5a2597c67c161767eba"
EXPECTED_EXPLICIT_SEMANTICS = "faf87ae2ba9dfe909c137e87627ff2841355e67dd57b47899a60b5cfa092f6ff"

EXPLICIT_METHOD_NAMES = {"as_payload", "to_trace_event", "to_trace_payload"}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _compact_digest(value: object) -> str:
    return _digest(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _definition_names(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return [node.name]
    if isinstance(node, ast.Assign):
        return [target.id for target in node.targets if isinstance(target, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def _common_nodes() -> list[ast.stmt]:
    return [node for node in _tree(COMMON_PATH).body if _definition_names(node)]


def _contract_classes() -> list[tuple[str, type[object]]]:
    return [
        (name, value)
        for name, value in vars(contracts).items()
        if isinstance(value, type) and value.__module__ == "alicebot_api.contracts"
    ]


def _signature(value: object) -> str:
    try:
        return str(inspect.signature(value))
    except (TypeError, ValueError) as exc:
        return f"!{type(exc).__name__}:{exc}"


def _method_row(owner_name: str, method_name: str, method: object) -> list[object]:
    assert inspect.isfunction(method)
    return [
        owner_name,
        method_name,
        method.__module__,
        method.__qualname__,
        method.__globals__.get("__name__"),
        str(inspect.signature(method)),
        repr(method.__annotations__),
        method.__doc__,
    ]


def test_common_definitions_are_exact_mechanical_carrier_moves() -> None:
    source = COMMON_PATH.read_text(encoding="utf-8")
    assert _digest(source) == EXPECTED_COMMON_SHA256
    nodes = _common_nodes()
    names = [name for node in nodes for name in _definition_names(node)]

    assert len(nodes) == 305
    assert len(names) == 305
    assert names[-1] == "isoformat_or_none"
    assert _digest("\n".join(names)) == EXPECTED_COMMON_NAMES
    assert (
        _digest("\n".join(ast.dump(node, include_attributes=False) for node in nodes))
        == EXPECTED_COMMON_AST
    )
    assert (
        _digest("\n".join(ast.get_source_segment(source, node) or "" for node in nodes))
        == EXPECTED_COMMON_SOURCE
    )

    facade_tree = _tree(FACADE_PATH)
    common_imports = [
        node
        for node in facade_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "alicebot_api._contracts.common"
    ]
    assert len(common_imports) == 2
    assert [alias.name for alias in common_imports[0].names] == names[:-1]
    assert [(alias.name, alias.asname) for alias in common_imports[1].names] == [
        ("isoformat_or_none", "_common_isoformat_or_none")
    ]

    locally_defined = {
        name
        for node in facade_tree.body
        for name in _definition_names(node)
        if name in set(names[:-1])
    }
    assert not locally_defined
    iso_assignments = [
        node
        for node in facade_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "isoformat_or_none"
            for target in node.targets
        )
    ]
    assert len(iso_assignments) == 1
    assert isinstance(iso_assignments[0].value, ast.Call)
    assert isinstance(iso_assignments[0].value.func, ast.Name)
    assert iso_assignments[0].value.func.id == "_clone_contract_function"

    binders = [
        node
        for node in facade_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_clone_contract_function"
    ]
    assert len(binders) == 1
    assert _digest(ast.dump(binders[0], include_attributes=False)) == EXPECTED_BINDER_AST


def test_common_reexports_preserve_public_surface_values_and_last_function_slot() -> None:
    public_names = [name for name in vars(contracts) if not name.startswith("_")]
    assert len(public_names) == 875
    assert public_names[0] == "annotations"
    assert public_names[-1] == "isoformat_or_none"
    assert _digest("\n".join(public_names)) == EXPECTED_PUBLIC_NAMES
    assert contracts.__doc__ is None
    assert not hasattr(contracts, "__all__")

    names = [name for node in _common_nodes() for name in _definition_names(node)]
    value_rows = []
    for name in names[:-1]:
        facade_value = getattr(contracts, name)
        carrier_value = getattr(common, name)
        assert facade_value is carrier_value
        value_rows.append(
            [
                name,
                f"{type(facade_value).__module__}.{type(facade_value).__qualname__}",
                getattr(facade_value, "__module__", None),
                getattr(facade_value, "__qualname__", None),
                repr(facade_value),
            ]
        )
    assert _compact_digest(value_rows) == EXPECTED_COMMON_VALUES

    function = contracts.isoformat_or_none
    assert function is not common.isoformat_or_none
    assert function.__globals__ is vars(contracts)
    assert function.__module__ == "alicebot_api.contracts"
    assert function.__qualname__ == "isoformat_or_none"
    assert function.__code__.co_qualname == "isoformat_or_none"
    assert Path(function.__code__.co_filename).resolve() == COMMON_PATH.resolve()
    assert inspect.signature(function) == inspect.signature(common.isoformat_or_none)
    assert function.__annotations__ == common.isoformat_or_none.__annotations__
    assert typing.get_type_hints(function) == {
        "value": datetime | None,
        "return": str | None,
    }
    assert pickle.loads(pickle.dumps(function)) is function
    assert function(None) is None
    value = datetime(2026, 7, 18, 10, 30, tzinfo=timezone.utc)
    assert function(value) == value.isoformat()


def test_contract_function_clone_preserves_python314_lazy_annotation_metadata() -> None:
    def source(value: object) -> object:
        return value

    def source_annotate(format: object) -> dict[str, object]:
        return {"return": datetime, "format": format}

    annotate = FunctionType(
        source_annotate.__code__.replace(
            co_name="__annotate__",
            co_qualname="__annotate__",
        ),
        source_annotate.__globals__,
        "__annotate__",
        source_annotate.__defaults__,
        source_annotate.__closure__,
    )
    annotate.__module__ = "alicebot_api._contracts.common"
    annotate.__qualname__ = "__annotate__"
    source.__annotate__ = annotate  # type: ignore[attr-defined]

    rebound = contracts._clone_contract_function(source, qualname="isoformat_or_none")
    rebound_annotate = rebound.__annotate__  # type: ignore[attr-defined]
    assert rebound_annotate is not annotate
    assert rebound_annotate.__globals__ is vars(contracts)
    assert rebound_annotate.__module__ == "alicebot_api.contracts"
    assert rebound_annotate.__qualname__ == "__annotate__"
    assert rebound_annotate.__code__.co_qualname == "__annotate__"
    assert rebound_annotate(1) == {"return": datetime, "format": 1}


def test_contract_class_annotations_schemas_pickle_and_metadata_are_unchanged() -> None:
    classes = _contract_classes()
    class_names = [name for name, _value in classes]
    assert len(classes) == 552
    assert _digest("\n".join(class_names)) == EXPECTED_CLASS_NAMES

    metadata = []
    raw_annotations = []
    resolved_hints = []
    dataclass_fields = []
    typed_dicts = []
    schemas = []
    for name, contract_class in classes:
        assert getattr(contracts, name) is contract_class
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
        for annotation in annotations.values():
            if isinstance(annotation, typing.ForwardRef):
                assert annotation.__forward_module__ == "alicebot_api.contracts"
        hints = typing.get_type_hints(contract_class, include_extras=True)
        resolved_hints.append(
            [name, [[key, repr(annotation)] for key, annotation in hints.items()]]
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

    assert _compact_digest(metadata) == EXPECTED_CLASS_METADATA
    assert _compact_digest(raw_annotations) == EXPECTED_RAW_ANNOTATIONS
    assert _compact_digest(resolved_hints) == EXPECTED_TYPE_HINTS
    assert len(dataclass_fields) == 94
    assert _compact_digest(dataclass_fields) == EXPECTED_DATACLASS_FIELDS
    assert len(typed_dicts) == 458
    assert _compact_digest(typed_dicts) == EXPECTED_TYPED_DICTS
    assert _compact_digest(schemas) == EXPECTED_SCHEMAS


def test_contract_explicit_and_generated_method_runtime_receipts_are_unchanged() -> None:
    explicit_rows = []
    generated_rows = []
    semantics = []
    for owner_name, contract_class in _contract_classes():
        for method_name, method in vars(contract_class).items():
            if not inspect.isfunction(method):
                continue
            row = _method_row(owner_name, method_name, method)
            if method_name in EXPLICIT_METHOD_NAMES:
                assert method.__globals__ is vars(contracts)
                explicit_rows.append(row)
                code = method.__code__
                semantics.append(
                    [
                        f"{owner_name}.{method_name}",
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
                generated_rows.append(row)

    assert len(explicit_rows) == 64
    assert len(generated_rows) == 752
    assert _compact_digest(explicit_rows) == EXPECTED_EXPLICIT_METHODS
    assert _compact_digest(generated_rows) == EXPECTED_GENERATED_METHODS
    assert _compact_digest(semantics) == EXPECTED_EXPLICIT_SEMANTICS


def test_common_carrier_is_private_cycle_free_and_under_the_phase_file_cap() -> None:
    imports = {
        node.module
        for node in _tree(COMMON_PATH).body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imports == {"__future__", "datetime", "typing"}
    assert INIT_PATH.read_text(encoding="utf-8") == "\n"
    assert len(COMMON_PATH.read_text(encoding="utf-8").splitlines()) < 4_000

    code = """
import sys
from alicebot_api._contracts import common
assert 'alicebot_api.contracts' not in sys.modules
assert 'alicebot_api.store' not in sys.modules
assert common.DEFAULT_MAX_SESSIONS == 3
assert common.isoformat_or_none(None) is None
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


def test_common_installed_wheel_and_python314_proofs_are_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for expected in (
        'python-version: ["3.13", "3.14"]',
        "import alicebot_api.contracts as contracts_module",
        "from alicebot_api._contracts import common as contracts_common",
        "contracts_common_carrier_path = Path(contracts_common.__file__).resolve()",
        "contracts_module.isoformat_or_none.__code__.co_filename",
        "common contracts carrier resolved to checkout source",
        "moved common contract function resolved to checkout source",
        "pickle.loads(pickle.dumps(isoformat_or_none)) is isoformat_or_none",
        "typing.get_type_hints(isoformat_or_none)",
        'isoformat_or_none.__module__ == "alicebot_api.contracts"',
        'facade_annotate.__name__ == "__annotate__"',
        "facade_annotate.__qualname__ == carrier_annotate.__qualname__",
        "carrier_annotate.__code__.co_qualname",
        'carrier_annotate.__module__ == "alicebot_api._contracts.common"',
    ):
        assert expected in workflow

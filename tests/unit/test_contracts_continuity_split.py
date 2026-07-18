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
from alicebot_api._contracts import continuity


REPO_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/contracts.py"
CONTINUITY_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/continuity.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EXPECTED_CONTINUITY_SHA256 = "72358ddcb2f7b8414a9a7ecb2462623f1a9a545d935cf991863873e019f4200e"
EXPECTED_PUBLIC_NAMES = "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
EXPECTED_PUBLIC_SLOTS = (
    (407, "RuntimeInvokeResponse", "EntityCreateInput"),
    (462, "ExecutionBudgetSupersedeInput", "RetrievalRunRecord"),
    (577, "RetrievalTraceResponse", "EntityRecord"),
)
EXPECTED_AGGREGATE_NAMES = "afeb94dcd00db01a857597b65418049ad7f731693f8a4efeed4f553d52f69393"
EXPECTED_AGGREGATE_AST = "f32a1c83b6b067686ad5e2c2c65d3d4c8f21d51c7f6ed04c1e87377f5b558c3a"
EXPECTED_AGGREGATE_SOURCE = "ae56bd2774c1d1c007ebe456cde6d8676dbdeb3fab5ff43200c45a79fe245403"
EXPECTED_CHUNKS = (
    (
        "OpenLoopCandidateInput",
        "ExtractedCommitmentCandidateRecord",
        31,
        "e26fb98e719b3f97966f4991392d5a585d7a729fbde0f122d5d8cef80c8c74f2",
        "4ab55a3e843995b493161bfd6b8554d3e416520b448f098b35ad083d60aeec44",
        "298e905eb99740f2cfaf58911d7b0e9d25435c0dca850fbe3722ced8eca06c34",
    ),
    (
        "PersistedMemoryRecord",
        "TaskBriefComparisonResponse",
        110,
        "d7b343003ed5e7dd261d7bbbc9938ce2702c45b22954e5557b40c101444e8388",
        "e6210269da7924902656a12c9ebaeff7f11b0660ce263b4a383d3d2f34a36e82",
        "6b6a584794ff707a12b1bbb7b639e89e12f4405e0d88ca38406f17f8edaa8946",
    ),
    (
        "ContinuityOpenLoopSectionSummary",
        "MemoryEvaluationSummaryResponse",
        51,
        "2571e2abda48afc806966243f2539496a235bf8d337a7a7dd8b32af58ce8c9fe",
        "0e80ab51cfabc8812b55c545457895e700a94331a98d2a476302883a23b80458",
        "c654ba93496a820894fa7ed943776440a920a15811c0d41e045050d79f031f23",
    ),
)
EXPECTED_METADATA = "d1f7b9b51d78255386b56cdbfe94d543b321da37dbe90a3fcb3178fae3394bac"
EXPECTED_RAW_ANNOTATIONS = "aad8766ccb4ffd492b2afac6759c2d66bb416600cb659def679ebd755b4f746e"
EXPECTED_TYPE_HINTS = "c76342e12c2daf4cb460dd70e4bad69561649a9269978b192d0f4b7c6b0ea11c"
EXPECTED_DATACLASS_FIELDS = "21337ba2b8cb04d49ec1a1d50ae9b16a33ae8291be9237b70ca6fdd529ca1ceb"
EXPECTED_TYPED_DICTS = "5ae2c88c86f6a45f5b17197d04eace01cc1d45d5a87c81ab268385d3ac7706c1"
EXPECTED_SCHEMAS = "3cdb7ed812a6212673465ef1f495d17590343d42c5015272e6bc57ac388e018a"
EXPECTED_EXPLICIT_METHODS = "d0bd0fd1f45f8c9cbe7447a19e91a770daa917ef199112c9bcbcd323ff900ef6"
EXPECTED_GENERATED_METHODS = "380ed1255b11305eee859ab7775194c98ad40128aead4dee066624304376dd8e"
EXPECTED_EXPLICIT_SEMANTICS = "29300e7bafba34f9388cd0f8e6df729ce367e41155e021c12dc84291fc84cca3"

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


def _continuity_nodes() -> list[ast.stmt]:
    return [
        node
        for node in _tree(CONTINUITY_PATH).body
        if any(not name.startswith("_") for name in _definition_names(node))
    ]


def _continuity_names() -> list[str]:
    return [
        name
        for node in _continuity_nodes()
        for name in _definition_names(node)
        if not name.startswith("_")
    ]


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


def test_continuity_source_and_three_facade_slots_are_exact() -> None:
    source = CONTINUITY_PATH.read_text(encoding="utf-8")
    nodes = _continuity_nodes()
    names = _continuity_names()
    classes = [node.name for node in nodes if isinstance(node, ast.ClassDef)]
    assert _digest(source) == EXPECTED_CONTINUITY_SHA256
    assert len(nodes) == len(names) == 192
    assert len(classes) == 190
    assert _digest("\n".join(names)) == EXPECTED_AGGREGATE_NAMES
    assert (
        _digest("\n".join(ast.dump(node, include_attributes=False) for node in nodes))
        == EXPECTED_AGGREGATE_AST
    )
    assert (
        _digest("\n".join(ast.get_source_segment(source, node) or "" for node in nodes))
        == EXPECTED_AGGREGATE_SOURCE
    )

    name_to_index = {name: index for index, name in enumerate(names)}
    expected_chunks: list[list[str]] = []
    for start, end, count, names_hash, ast_hash, source_hash in EXPECTED_CHUNKS:
        start_index = name_to_index[start]
        end_index = name_to_index[end] + 1
        chunk_nodes = nodes[start_index:end_index]
        chunk_names = names[start_index:end_index]
        assert len(chunk_nodes) == len(chunk_names) == count
        assert _digest("\n".join(chunk_names)) == names_hash
        assert (
            _digest("\n".join(ast.dump(node, include_attributes=False) for node in chunk_nodes))
            == ast_hash
        )
        assert (
            _digest(
                "\n".join(ast.get_source_segment(source, node) or "" for node in chunk_nodes)
            )
            == source_hash
        )
        expected_chunks.append(chunk_names)

    facade_tree = _tree(FACADE_PATH)
    imports = [
        node
        for node in facade_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "alicebot_api._contracts.continuity"
    ]
    assert len(imports) == 3
    assert [[alias.name for alias in node.names] for node in imports] == expected_chunks

    public_names = [name for name in vars(contracts) if not name.startswith("_")]
    assert len(public_names) == 875
    assert _digest("\n".join(public_names)) == EXPECTED_PUBLIC_NAMES
    for (before_index, before, after), chunk_names in zip(
        EXPECTED_PUBLIC_SLOTS,
        expected_chunks,
        strict=True,
    ):
        assert public_names[before_index : before_index + len(chunk_names) + 2] == [
            before,
            *chunk_names,
            after,
        ]

    assert _literal_assignment(facade_tree, "_CONTINUITY_CONTRACT_CLASS_NAMES") == tuple(classes)
    explicit_methods = _literal_assignment(facade_tree, "_CONTINUITY_EXPLICIT_METHODS")
    assert isinstance(explicit_methods, tuple)
    assert len(explicit_methods) == 29

    locally_defined = {
        name
        for node in facade_tree.body
        for name in _definition_names(node)
        if name in set(names)
    }
    assert not locally_defined


def test_continuity_runtime_metadata_hints_schemas_and_methods_are_exact() -> None:
    names = _continuity_names()
    classes = [
        (name, getattr(contracts, name))
        for name in names
        if isinstance(getattr(contracts, name), type)
    ]
    assert len(classes) == 190
    assert [name for name in names if not isinstance(getattr(contracts, name), type)] == [
        "MemoryHygienePosture",
        "MemoryHygieneFocusKind",
    ]
    assert contracts.MemoryHygienePosture is continuity.MemoryHygienePosture
    assert repr(contracts.MemoryHygienePosture) == (
        "typing.Literal['healthy', 'watch', 'critical']"
    )
    assert typing.get_args(contracts.MemoryHygienePosture) == (
        "healthy",
        "watch",
        "critical",
    )
    assert contracts.MemoryHygieneFocusKind is continuity.MemoryHygieneFocusKind
    assert repr(contracts.MemoryHygieneFocusKind) == (
        "typing.Literal['duplicates', 'stale_facts', 'unresolved_contradictions', "
        "'weak_trust', 'review_queue_pressure']"
    )
    assert typing.get_args(contracts.MemoryHygieneFocusKind) == (
        "duplicates",
        "stale_facts",
        "unresolved_contradictions",
        "weak_trust",
        "review_queue_pressure",
    )

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
        assert contract_class is getattr(continuity, name)
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
            if method_name in EXPLICIT_METHOD_NAMES:
                assert method.__globals__ is vars(contracts)
                assert Path(method.__code__.co_filename).resolve() == CONTINUITY_PATH.resolve()
                assert pickle.loads(pickle.dumps(method)) is method
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

    assert _compact_digest(metadata) == EXPECTED_METADATA
    assert _compact_digest(raw_annotations) == EXPECTED_RAW_ANNOTATIONS
    assert _compact_digest(resolved_hints) == EXPECTED_TYPE_HINTS
    assert len(dataclass_fields) == 30
    assert _compact_digest(dataclass_fields) == EXPECTED_DATACLASS_FIELDS
    assert len(typed_dicts) == 160
    assert _compact_digest(typed_dicts) == EXPECTED_TYPED_DICTS
    assert _compact_digest(schemas) == EXPECTED_SCHEMAS
    assert len(explicit_methods) == 29
    assert _compact_digest(explicit_methods) == EXPECTED_EXPLICIT_METHODS
    assert len(generated_methods) == 240
    assert _compact_digest(generated_methods) == EXPECTED_GENERATED_METHODS
    assert _compact_digest(semantics) == EXPECTED_EXPLICIT_SEMANTICS

    candidate = contracts.MemoryCandidateInput(
        memory_key="preference:editor",
        value={"name": "vim"},
        source_event_ids=(),
    )
    assert pickle.loads(pickle.dumps(candidate)) == candidate
    assert candidate.as_payload()["memory_key"] == "preference:editor"


def test_continuity_carrier_imports_fresh_and_all_contract_files_fit_cap() -> None:
    tree = _tree(CONTINUITY_PATH)
    top_level_imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "alicebot_api.contracts" not in top_level_imports
    assert len(CONTINUITY_PATH.read_text(encoding="utf-8").splitlines()) < 4_000
    assert len(FACADE_PATH.read_text(encoding="utf-8").splitlines()) < 4_000

    code = """
import sys
from pathlib import Path
from alicebot_api._contracts import continuity
assert continuity.__name__ == 'alicebot_api._contracts.continuity'
assert 'alicebot_api.contracts' not in sys.modules
assert continuity.MemoryCandidateInput.__module__ == 'alicebot_api.contracts'
assert continuity.MemoryCandidateInput.as_payload.__globals__ is vars(continuity)
assert Path(continuity.MemoryCandidateInput.as_payload.__code__.co_filename).resolve() == Path(continuity.__file__).resolve()
candidate = continuity.MemoryCandidateInput(memory_key='k', value=None, source_event_ids=())
assert candidate.as_payload()['memory_key'] == 'k'
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


def test_continuity_facade_normalizes_both_import_orders() -> None:
    checks = """
import inspect
import sys
import typing

continuity_classes = [
    value
    for value in vars(continuity).values()
    if isinstance(value, type) and value.__module__ == 'alicebot_api.contracts'
]
continuity_dataclasses = [
    value for value in continuity_classes if hasattr(value, '__dataclass_fields__')
]
continuity_typed_dicts = [value for value in continuity_classes if typing.is_typeddict(value)]
assert len(continuity_classes) == 190
assert len(continuity_dataclasses) == 30
assert len(continuity_typed_dicts) == 160
assert all(cls.__init__.__globals__ is vars(contracts) for cls in continuity_dataclasses)
assert not [
    (cls.__name__, name)
    for cls in continuity_dataclasses
    for name, method in vars(cls).items()
    if inspect.isfunction(method) and method.__globals__ is vars(continuity)
]
assert all(
    getattr(getattr(contracts, owner), method).__globals__ is vars(contracts)
    for owner, method in contracts._CONTINUITY_EXPLICIT_METHODS
)
assert len(contracts._CONTINUITY_EXPLICIT_METHODS) == 29
assert len([name for name in vars(contracts) if not name.startswith('_')]) == 875
assert contracts.ContextCompilerLimits.__init__.__globals__ is vars(contracts)
assert contracts.isoformat_or_none.__globals__ is vars(contracts)
if sys.version_info >= (3, 14):
    for typed_dict in continuity_typed_dicts:
        annotate = typed_dict.__annotate__
        assert annotate.__module__ == 'typing'
        assert annotate.__globals__ is vars(typing)
        assert isinstance(annotate(1), dict)
    for contract_class in continuity_dataclasses:
        init_annotate = contract_class.__init__.__annotate__
        assert init_annotate.__module__ == 'dataclasses'
        assert init_annotate.__globals__['__name__'] == 'dataclasses'
"""
    import_orders = (
        "import alicebot_api.contracts as contracts\n"
        "from alicebot_api._contracts import continuity\n",
        "from alicebot_api._contracts import continuity\n"
        "import alicebot_api.contracts as contracts\n",
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


def test_continuity_installed_wheel_and_python314_proofs_are_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for expected in (
        "from alicebot_api._contracts import continuity as contracts_continuity",
        "contracts_continuity_carrier_path = Path(contracts_continuity.__file__).resolve()",
        "contracts_module.MemoryCandidateInput.as_payload.__code__.co_filename",
        "continuity contracts carrier resolved to checkout source",
        "moved continuity contract method resolved to checkout source",
        "continuity_method.__globals__ is vars(contracts_module)",
        "assert len(continuity_dataclasses) == 30",
        "assert len(continuity_typed_dicts) == 160",
        "contracts_module._CONTINUITY_EXPLICIT_METHODS",
        "continuity_init_annotate.__module__ == \"dataclasses\"",
    ):
        assert expected in workflow

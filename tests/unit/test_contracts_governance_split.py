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
from alicebot_api._contracts import governance
from alicebot_api._contracts import tasks


REPO_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/contracts.py"
GOVERNANCE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/governance.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EXPECTED_GOVERNANCE_SHA256 = "0ac44e6ce8ffcc5ef2520e6bdf63b8849a83c269cb6717432449f4038e052f18"
EXPECTED_PUBLIC_NAMES = "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
EXPECTED_LOCAL_FUTURE_NAMES = (
    0,
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
)
EXPECTED_PUBLIC_SLOTS = (
    (449, "SemanticMemoryRetrievalRequestInput", "ProxyExecutionRequestInput"),
    (687, "PublicEvalRunDetailResponse", "TaskCreateInput"),
    (837, "TaskStepTransitionSummaryTracePayload", "ExecutionBudgetRecord"),
)
EXPECTED_CHUNKS = (
    (
        "ConsentUpsertInput",
        "ApprovalRejectInput",
        9,
        "df44f369eed7075b7045a0d8ae8fe86d51c9d3a437aa7d8f4854180e9535332b",
        "18b8b1f3f10d870d89c1f3c167e7652c0cd5fdc330a80d9d1ba698e513071bf4",
        "3662ead64d77ea661ab49262142fb2bd31afd4e5cf075c33dfb3513a67f49acb",
    ),
    (
        "ConsentRecord",
        "ApprovalResolutionSummaryTracePayload",
        38,
        "de625737d1f3d3e6b5f20aa62755b33f98dfa7c801992b7f3436f8f56573f9bf",
        "6dfb858beece370d1bb717b42511fdd8945fa5ee1d4b2abeceb4a3ada23b4088",
        "8a61f58ac624763ed86222406e50271825a5cae181a735f427b4464cd72551e8",
    ),
    (
        "ApprovalRequestCreateResponse",
        "ApprovalResolutionResponse",
        5,
        "87e9d926c027333d35647efebeb715c2c241a4a3326ec7ef4ad51b5b675f8d88",
        "c9407da0d3fdf4e9554d3dbda3c20da2f80f13750f8e5e87c6edd9f23a8cfce4",
        "f749fbead62a971a06c3361cb37840b44c036c337ff4d8a4e4ef99a3dffa39b8",
    ),
)
EXPECTED_AGGREGATE_NAMES = "72e4e54b757a24dd9d02fa59d1bbc7981a961baa56852b16ac0dd9c54426dcc3"
EXPECTED_AGGREGATE_AST = "3258b70337887e018d2b343c2206d669137000c9598cdb151fff6de96ef65e97"
EXPECTED_AGGREGATE_SOURCE = "fce3ecd8b2c11d024445d13fc343055d48fdd4f81a61d11655eee57ce1583201"
EXPECTED_METADATA = "ea012dac0e91913bbe5505b61bcca8888bb1b0c9b00fd2d85a2dcaef88031208"
EXPECTED_RAW_ANNOTATIONS = "5f7957ace1f9d2af085ae66200840b03eaba5012c9b227143ad2cea8c719078b"
EXPECTED_TYPE_HINTS = "ce0363304a6b0baaf066a41cdda03ee59ef6b3d044c877953bbcb328b87488ea"
EXPECTED_DATACLASS_FIELDS = "b24f5402678c1cdcea0eedd048d7edd8a42e4f9b114405800b535c305eb2fd57"
EXPECTED_TYPED_DICTS = "29e171ca62b395961170ee22f52dd98c6e942b7cf67e412155b4dee444ab3734"
EXPECTED_SCHEMAS = "f436c9e2509a047d34a1000c35a3985b684b86b6a537722ff1a395c735736efe"
EXPECTED_EXPLICIT_METHODS = "9b7fe93d2db189e6d9c373cbff9034ab8f5686dc1d6ca1468c0f6a33e2392de1"
EXPECTED_GENERATED_METHODS = "5a26ac7bc2c4a8fe74bb874021c88a36534d2f5c623e1517cc94fa91a3e58e16"
EXPECTED_EXPLICIT_SEMANTICS = "48dde21aa173362fcf76e7f4d79f5d2e7f16daa18e48de0fd6f70a5ba66ab4c0"

EXPLICIT_METHODS = (
    ("ConsentUpsertInput", "as_payload"),
    ("PolicyCreateInput", "as_payload"),
    ("PolicyEvaluationRequestInput", "as_payload"),
    ("ToolCreateInput", "as_payload"),
    ("ToolAllowlistEvaluationRequestInput", "as_payload"),
    ("ToolRoutingRequestInput", "as_payload"),
    ("ApprovalRequestCreateInput", "as_payload"),
    ("ApprovalApproveInput", "as_payload"),
    ("ApprovalRejectInput", "as_payload"),
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _compact_digest(value: object) -> str:
    return _digest(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
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


def _governance_nodes() -> list[ast.stmt]:
    return [
        node
        for node in _tree(GOVERNANCE_PATH).body
        if any(not name.startswith("_") for name in _definition_names(node))
    ]


def _governance_names() -> list[str]:
    return [
        name
        for node in _governance_nodes()
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


def test_governance_source_scope_and_three_facade_slots_are_exact() -> None:
    source = GOVERNANCE_PATH.read_text(encoding="utf-8")
    nodes = _governance_nodes()
    names = _governance_names()
    classes = [node.name for node in nodes if isinstance(node, ast.ClassDef)]
    assert _digest(source) == EXPECTED_GOVERNANCE_SHA256
    assert len(nodes) == len(names) == len(classes) == 52
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
        and node.module == "alicebot_api._contracts.governance"
    ]
    assert len(imports) == 3
    assert [[alias.name for alias in node.names] for node in imports] == expected_chunks
    assert _literal_assignment(facade_tree, "_GOVERNANCE_CONTRACT_CLASS_NAMES") == tuple(
        classes
    )
    assert _literal_assignment(facade_tree, "_GOVERNANCE_EXPLICIT_METHODS") == EXPLICIT_METHODS

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

    local_names = [
        node.name
        for node in facade_tree.body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    ]
    assert len(local_names) == EXPECTED_LOCAL_FUTURE_NAMES[0]
    assert _digest("\n".join(local_names)) == EXPECTED_LOCAL_FUTURE_NAMES[1]
    assert not set(local_names).intersection(names)
    assert "TaskRecord" not in local_names
    assert "GmailAccountConnectInput" not in local_names
    assert contracts.TaskRecord is tasks.TaskRecord
    assert not hasattr(governance, "TaskRecord")


def test_governance_runtime_metadata_hints_schemas_and_methods_are_exact() -> None:
    classes = [(name, getattr(contracts, name)) for name in _governance_names()]
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
        assert contract_class is getattr(governance, name)
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
        resolved_hints.append(
            [
                name,
                [
                    [key, repr(annotation)]
                    for key, annotation in typing.get_type_hints(
                        contract_class,
                        include_extras=True,
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
                assert Path(method.__code__.co_filename).resolve() == GOVERNANCE_PATH.resolve()
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

    assert len(dataclass_fields) == 9
    assert len(typed_dicts) == 43
    assert len(explicit_methods) == 9
    assert len(generated_methods) == 72
    assert _compact_digest(metadata) == EXPECTED_METADATA
    assert _compact_digest(raw_annotations) == EXPECTED_RAW_ANNOTATIONS
    assert _compact_digest(resolved_hints) == EXPECTED_TYPE_HINTS
    assert _compact_digest(dataclass_fields) == EXPECTED_DATACLASS_FIELDS
    assert _compact_digest(typed_dicts) == EXPECTED_TYPED_DICTS
    assert _compact_digest(schemas) == EXPECTED_SCHEMAS
    assert _compact_digest(explicit_methods) == EXPECTED_EXPLICIT_METHODS
    assert _compact_digest(generated_methods) == EXPECTED_GENERATED_METHODS
    assert _compact_digest(semantics) == EXPECTED_EXPLICIT_SEMANTICS

    task_annotation = contracts.ApprovalRequestCreateResponse.__annotations__["task"]
    assert isinstance(task_annotation, typing.ForwardRef)
    assert task_annotation.__forward_module__ == "alicebot_api.contracts"
    assert typing.get_type_hints(
        contracts.ApprovalRequestCreateResponse,
        include_extras=True,
    )["task"] is contracts.TaskRecord
    tool_id = UUID("10000000-0000-0000-0000-000000000001")
    request = contracts.ToolRoutingRequestInput(
        thread_id=tool_id,
        tool_id=tool_id,
        action="read",
        scope="workspace",
    )
    assert request.as_payload()["domain_hint"] is None
    assert request.as_payload()["risk_hint"] is None
    assert pickle.loads(pickle.dumps(request)) == request


def test_governance_carrier_imports_fresh_and_contract_files_fit_cap() -> None:
    tree = _tree(GOVERNANCE_PATH)
    top_level_imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "alicebot_api.contracts" not in top_level_imports
    assert top_level_imports == {
        "__future__",
        "dataclasses",
        "typing",
        "uuid",
        "alicebot_api._contracts.common",
        "alicebot_api.store",
    }
    assert len(GOVERNANCE_PATH.read_text(encoding="utf-8").splitlines()) < 4_000
    assert len(FACADE_PATH.read_text(encoding="utf-8").splitlines()) < 4_000

    code = """
import sys
from pathlib import Path
from alicebot_api._contracts import governance
assert governance.__name__ == 'alicebot_api._contracts.governance'
assert 'alicebot_api.contracts' not in sys.modules
assert governance.ToolRoutingRequestInput.__module__ == 'alicebot_api.contracts'
assert governance.ToolRoutingRequestInput.as_payload.__globals__ is vars(governance)
assert Path(governance.ToolRoutingRequestInput.as_payload.__code__.co_filename).resolve() == Path(governance.__file__).resolve()
assert not hasattr(governance, 'TaskRecord')
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


def test_governance_facade_normalizes_both_import_orders() -> None:
    checks = """
import dataclasses
import hashlib
import inspect
import pickle
import sys
import typing

governance_classes = [
    getattr(governance, name) for name in contracts._GOVERNANCE_CONTRACT_CLASS_NAMES
]
governance_dataclasses = [
    value for value in governance_classes if dataclasses.is_dataclass(value)
]
governance_typed_dicts = [
    value for value in governance_classes if typing.is_typeddict(value)
]
assert len(governance_classes) == 52
assert len(governance_dataclasses) == 9
assert len(governance_typed_dicts) == 43
assert all(
    getattr(contracts, name) is getattr(governance, name)
    for name in contracts._GOVERNANCE_CONTRACT_CLASS_NAMES
)
assert all(cls.__init__.__globals__ is vars(contracts) for cls in governance_dataclasses)
assert not [
    (cls.__name__, name)
    for cls in governance_dataclasses
    for name, method in vars(cls).items()
    if inspect.isfunction(method) and method.__globals__ is vars(governance)
]
assert len(contracts._GOVERNANCE_EXPLICIT_METHODS) == 9
assert all(
    getattr(getattr(contracts, owner), method).__globals__ is vars(contracts)
    for owner, method in contracts._GOVERNANCE_EXPLICIT_METHODS
)
assert all(pickle.loads(pickle.dumps(cls)) is cls for cls in governance_classes)
for contract_class in governance_classes:
    typing.get_type_hints(contract_class, include_extras=True)
task_annotation = contracts.ApprovalRequestCreateResponse.__annotations__["task"]
assert isinstance(task_annotation, typing.ForwardRef)
assert task_annotation.__forward_module__ == "alicebot_api.contracts"
assert typing.get_type_hints(
    contracts.ApprovalRequestCreateResponse,
    include_extras=True,
)["task"] is contracts.TaskRecord
assert not hasattr(governance, "TaskRecord")
assert hashlib.sha256(
    "\\n".join(name for name in vars(contracts) if not name.startswith("_")).encode()
).hexdigest() == "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
if sys.version_info >= (3, 14):
    for typed_dict in governance_typed_dicts:
        annotate = typed_dict.__annotate__
        assert annotate.__module__ == "typing"
        assert annotate.__globals__ is vars(typing)
        assert isinstance(annotate(1), dict)
    for contract_class in governance_dataclasses:
        init_annotate = contract_class.__init__.__annotate__
        assert init_annotate.__module__ == "dataclasses"
        assert init_annotate.__globals__["__name__"] == "dataclasses"
        replace = contract_class.__replace__
        assert replace.__module__ == "dataclasses"
        assert replace.__globals__["__name__"] == "dataclasses"
    for owner, method_name in contracts._GOVERNANCE_EXPLICIT_METHODS:
        explicit_annotate = getattr(
            getattr(getattr(contracts, owner), method_name),
            "__annotate__",
        )
        assert explicit_annotate.__module__ == "alicebot_api.contracts"
        assert explicit_annotate.__globals__ is vars(contracts)
        assert explicit_annotate.__qualname__.startswith(f"{owner}.")
        assert explicit_annotate.__qualname__.endswith("__annotate__")
        assert isinstance(explicit_annotate(1), dict)
"""
    import_orders = (
        "import alicebot_api.contracts as contracts\n"
        "from alicebot_api._contracts import governance\n",
        "from alicebot_api._contracts import governance\n"
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


def test_governance_installed_wheel_and_python314_proofs_are_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert (
        workflow.count(
            "from alicebot_api._contracts import governance as contracts_governance"
        )
        == 2
    )
    for repeated in (
        "governance_classes = [",
        "assert len(governance_classes) == 52",
        "assert len(governance_dataclasses) == 9",
        "assert len(governance_typed_dicts) == 43",
        "governance_task_annotation = (",
        "governance_init_annotate.__module__ == \"dataclasses\"",
        "governance_explicit_annotate.__globals__ is vars(contracts_module)",
    ):
        assert workflow.count(repeated) == 2
    for expected in (
        "contracts_governance_carrier_path = Path(contracts_governance.__file__).resolve()",
        "contracts_module.ToolRoutingRequestInput.as_payload.__code__.co_filename",
        "governance contracts carrier resolved to checkout source",
        "moved governance contract method resolved to checkout source",
        "contracts_module._GOVERNANCE_EXPLICIT_METHODS",
    ):
        assert expected in workflow

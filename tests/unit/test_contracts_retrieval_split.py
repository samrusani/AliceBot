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
from alicebot_api._contracts import retrieval
from alicebot_api._contracts import tasks


REPO_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/contracts.py"
RETRIEVAL_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/retrieval.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EXPECTED_RETRIEVAL_SHA256 = "53d5ac53c54a5c4ad62309d155170801694963f9a9550128dc2a3203b51001f6"
EXPECTED_PUBLIC_NAMES = "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
EXPECTED_PUBLIC_SLOTS = (
    (445, "TrustedFactPlaybookListQueryInput", "TaskArtifactChunkEmbeddingUpsertInput"),
    (448, "TaskArtifactChunkEmbeddingUpsertInput", "ConsentUpsertInput"),
    (572, "TaskBriefComparisonResponse", "ContinuityOpenLoopSectionSummary"),
    (666, "TrustedFactPlaybookExplainResponse", "ConsentRecord"),
)
EXPECTED_CHUNKS = (
    (
        "EmbeddingConfigCreateInput",
        "MemoryEmbeddingUpsertInput",
        2,
        "4b07086da946e66a7772812c3741d11c8906d57eb43d65e62a976e55117dd8a3",
        "03022764f6790e58f784bbcb912eab4530d47317ff893bb85fe9ee2bd9f313d9",
        "ffc647f5645eb3b8b3c36522ab14dca21e7cea290119f27bb8d42c19dfe37b7a",
    ),
    (
        "SemanticMemoryRetrievalRequestInput",
        "SemanticMemoryRetrievalRequestInput",
        1,
        "69780a4562c29e1f2962fc32d02eca40eb10faf523956f825ba8d1525bbf55b3",
        "b8bcdcc4ed32ccdb885d19041ed2e2ec5c45b867076069dba94f77b5e46a8e0d",
        "0d0ebdcff154f505d894df65fdd7cbb1d99b2861e5c068fc9d088f581feacac0",
    ),
    (
        "RetrievalRunRecord",
        "RetrievalTraceResponse",
        5,
        "0fef78b395fd565be659f1503bea7075a76cba0c3cbefd056210a4f0511d04e7",
        "0faf641f4cb843c225594cfb4a80718b26a06a1c46c6d40a3957270dcdd5ca7e",
        "fd742d66dcd56297b0bd8c62b921c04c16acfcfa2320ba42ca7891924af06639",
    ),
    (
        "EmbeddingConfigRecord",
        "PublicEvalRunDetailResponse",
        21,
        "f884ab5521c6fe9eb45e84c48c333a858189e2e5b9ee88c4dcd9ed32c443ca38",
        "c28b2da32f1ab96ad30d80fbee86dabb7941820cc21f4f999504cf154020af10",
        "677380f02dcdf364d25ddb2463cc5eeea0a20e232eb94452ff517244f92eca4c",
    ),
)
EXPECTED_AGGREGATE_NAMES = "1a0da8e17466f6e24b2af1da164a6b27132511134622907eec4a7f2432ef0641"
EXPECTED_AGGREGATE_AST = "bcff476fc4d8225106525032777893e01686c2c15c03d7922837e42f41d78d33"
EXPECTED_AGGREGATE_SOURCE = "7c3333375b3880ac5951d8395a4fb14b17c1c8c180a3f32f9267fd543464befc"
EXPECTED_METADATA = "08f8e589f4dcbb1642f7d57d03f666f6348f6b3c72d746fe1af1a4c5316536c0"
EXPECTED_RAW_ANNOTATIONS = "b74f800a6e17131d6e352ac4caa8f1c300a1d82775e1799f17d040bdf745e352"
EXPECTED_TYPE_HINTS = "f2a4b9c8339cff246e486ca1a1ed691a303fdc00d3c9c0f61625615cdbd90e62"
EXPECTED_DATACLASS_FIELDS = "3b594c4642edc1ca983d470301b0acb909c2e5fe5f3dcb548de2a298afdca272"
EXPECTED_TYPED_DICTS = "308063b6374ff5147f12ad694d5204b652d9d6ab43b12d160b2616c45367cd02"
EXPECTED_SCHEMAS = "4dfc7dfc1fbc918f37ef0175bb97fe3e74c4b9c29ab87a02dac2748b2c5f9432"
EXPECTED_EXPLICIT_METHODS = "042202172947efd65c7633e29942383675e1010f7525f8cb2346d78ea418563a"
EXPECTED_GENERATED_METHODS = "4259286aeb40f3cccc0d911555d0168414ca58b826024de9a3dfd11ba2241f82"
EXPECTED_EXPLICIT_SEMANTICS = "be051edc4cea1055e91851725435b018d72c6efe09cf5e1ec5c404cf2602047e"

EXPLICIT_METHODS = (
    ("EmbeddingConfigCreateInput", "as_payload"),
    ("MemoryEmbeddingUpsertInput", "as_payload"),
    ("SemanticMemoryRetrievalRequestInput", "as_payload"),
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


def _retrieval_nodes() -> list[ast.stmt]:
    return [
        node
        for node in _tree(RETRIEVAL_PATH).body
        if any(not name.startswith("_") for name in _definition_names(node))
    ]


def _retrieval_names() -> list[str]:
    return [
        name
        for node in _retrieval_nodes()
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


def test_retrieval_source_scope_and_four_facade_slots_are_exact() -> None:
    source = RETRIEVAL_PATH.read_text(encoding="utf-8")
    nodes = _retrieval_nodes()
    names = _retrieval_names()
    classes = [node.name for node in nodes if isinstance(node, ast.ClassDef)]
    assert _digest(source) == EXPECTED_RETRIEVAL_SHA256
    assert len(nodes) == len(names) == len(classes) == 29
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
        and node.module == "alicebot_api._contracts.retrieval"
    ]
    assert len(imports) == 4
    assert [[alias.name for alias in node.names] for node in imports] == expected_chunks
    assert _literal_assignment(facade_tree, "_RETRIEVAL_CONTRACT_CLASS_NAMES") == tuple(
        classes
    )
    assert _literal_assignment(facade_tree, "_RETRIEVAL_EXPLICIT_METHODS") == EXPLICIT_METHODS

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

    local_classes = {
        node.name for node in facade_tree.body if isinstance(node, ast.ClassDef)
    }
    assert not local_classes.intersection(names)
    assert "TaskArtifactChunkEmbeddingUpsertInput" not in local_classes
    assert (
        contracts.TaskArtifactChunkEmbeddingUpsertInput
        is tasks.TaskArtifactChunkEmbeddingUpsertInput
    )
    assert not hasattr(retrieval, "TaskArtifactChunkEmbeddingUpsertInput")


def test_retrieval_runtime_metadata_hints_schemas_and_methods_are_exact() -> None:
    classes = [(name, getattr(contracts, name)) for name in _retrieval_names()]
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
        assert contract_class is getattr(retrieval, name)
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
                assert Path(method.__code__.co_filename).resolve() == RETRIEVAL_PATH.resolve()
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

    assert len(dataclass_fields) == 3
    assert len(typed_dicts) == 26
    assert len(explicit_methods) == 3
    assert len(generated_methods) == 24
    assert _compact_digest(metadata) == EXPECTED_METADATA
    assert _compact_digest(raw_annotations) == EXPECTED_RAW_ANNOTATIONS
    assert _compact_digest(resolved_hints) == EXPECTED_TYPE_HINTS
    assert _compact_digest(dataclass_fields) == EXPECTED_DATACLASS_FIELDS
    assert _compact_digest(typed_dicts) == EXPECTED_TYPED_DICTS
    assert _compact_digest(schemas) == EXPECTED_SCHEMAS
    assert _compact_digest(explicit_methods) == EXPECTED_EXPLICIT_METHODS
    assert _compact_digest(generated_methods) == EXPECTED_GENERATED_METHODS
    assert _compact_digest(semantics) == EXPECTED_EXPLICIT_SEMANTICS

    config_id = UUID("10000000-0000-0000-0000-000000000001")
    request = contracts.SemanticMemoryRetrievalRequestInput(
        embedding_config_id=config_id,
        query_vector=(0.25, 0.75),
    )
    assert inspect.signature(contracts.SemanticMemoryRetrievalRequestInput).parameters[
        "limit"
    ].default == 5
    assert request.as_payload() == {
        "embedding_config_id": str(config_id),
        "query_vector": [0.25, 0.75],
        "limit": 5,
    }
    assert pickle.loads(pickle.dumps(request)) == request


def test_retrieval_carrier_imports_fresh_and_contract_files_fit_cap() -> None:
    tree = _tree(RETRIEVAL_PATH)
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
    assert len(RETRIEVAL_PATH.read_text(encoding="utf-8").splitlines()) < 4_000
    assert len(FACADE_PATH.read_text(encoding="utf-8").splitlines()) < 4_000

    code = """
import inspect
import sys
from pathlib import Path
from alicebot_api._contracts import retrieval
assert retrieval.__name__ == 'alicebot_api._contracts.retrieval'
assert 'alicebot_api.contracts' not in sys.modules
assert retrieval.SemanticMemoryRetrievalRequestInput.__module__ == 'alicebot_api.contracts'
assert retrieval.SemanticMemoryRetrievalRequestInput.as_payload.__globals__ is vars(retrieval)
assert Path(retrieval.SemanticMemoryRetrievalRequestInput.as_payload.__code__.co_filename).resolve() == Path(retrieval.__file__).resolve()
assert inspect.signature(retrieval.SemanticMemoryRetrievalRequestInput).parameters['limit'].default == 5
assert not hasattr(retrieval, 'TaskArtifactChunkEmbeddingUpsertInput')
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


def test_retrieval_facade_normalizes_both_import_orders() -> None:
    checks = """
import dataclasses
import hashlib
import inspect
import pickle
import sys
import typing

retrieval_classes = [
    getattr(retrieval, name) for name in contracts._RETRIEVAL_CONTRACT_CLASS_NAMES
]
retrieval_dataclasses = [
    value for value in retrieval_classes if dataclasses.is_dataclass(value)
]
retrieval_typed_dicts = [
    value for value in retrieval_classes if typing.is_typeddict(value)
]
assert len(retrieval_classes) == 29
assert len(retrieval_dataclasses) == 3
assert len(retrieval_typed_dicts) == 26
assert all(
    getattr(contracts, name) is getattr(retrieval, name)
    for name in contracts._RETRIEVAL_CONTRACT_CLASS_NAMES
)
assert all(cls.__init__.__globals__ is vars(contracts) for cls in retrieval_dataclasses)
assert not [
    (cls.__name__, name)
    for cls in retrieval_dataclasses
    for name, method in vars(cls).items()
    if inspect.isfunction(method) and method.__globals__ is vars(retrieval)
]
assert len(contracts._RETRIEVAL_EXPLICIT_METHODS) == 3
assert all(
    getattr(getattr(contracts, owner), method).__globals__ is vars(contracts)
    for owner, method in contracts._RETRIEVAL_EXPLICIT_METHODS
)
assert all(pickle.loads(pickle.dumps(cls)) is cls for cls in retrieval_classes)
for contract_class in retrieval_classes:
    typing.get_type_hints(contract_class, include_extras=True)
assert inspect.signature(
    contracts.SemanticMemoryRetrievalRequestInput
).parameters["limit"].default == 5
assert not hasattr(retrieval, "TaskArtifactChunkEmbeddingUpsertInput")
assert hashlib.sha256(
    "\\n".join(name for name in vars(contracts) if not name.startswith("_")).encode()
).hexdigest() == "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
if sys.version_info >= (3, 14):
    for typed_dict in retrieval_typed_dicts:
        annotate = typed_dict.__annotate__
        assert annotate.__module__ == "typing"
        assert annotate.__globals__ is vars(typing)
        assert isinstance(annotate(1), dict)
    for contract_class in retrieval_dataclasses:
        init_annotate = contract_class.__init__.__annotate__
        assert init_annotate.__module__ == "dataclasses"
        assert init_annotate.__globals__["__name__"] == "dataclasses"
        replace = contract_class.__replace__
        assert replace.__module__ == "dataclasses"
        assert replace.__globals__["__name__"] == "dataclasses"
    for owner, method_name in contracts._RETRIEVAL_EXPLICIT_METHODS:
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
        "from alicebot_api._contracts import retrieval\n",
        "from alicebot_api._contracts import retrieval\n"
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


def test_retrieval_installed_wheel_and_python314_proofs_are_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert (
        workflow.count(
            "from alicebot_api._contracts import retrieval as contracts_retrieval"
        )
        == 2
    )
    for expected in (
        "contracts_retrieval_carrier_path = Path(contracts_retrieval.__file__).resolve()",
        "contracts_module.SemanticMemoryRetrievalRequestInput.as_payload.__code__.co_filename",
        "retrieval contracts carrier resolved to checkout source",
        "moved retrieval contract method resolved to checkout source",
        "assert len(retrieval_classes) == 29",
        "assert len(retrieval_dataclasses) == 3",
        "assert len(retrieval_typed_dicts) == 26",
        "contracts_module._RETRIEVAL_EXPLICIT_METHODS",
        "retrieval_init_annotate.__module__ == \"dataclasses\"",
        "retrieval_explicit_annotate.__globals__ is vars(contracts_module)",
    ):
        assert expected in workflow

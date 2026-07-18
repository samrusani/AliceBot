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
from uuid import UUID

from pydantic import TypeAdapter

import alicebot_api.contracts as contracts
from alicebot_api._contracts import knowledge
from alicebot_api._contracts import tasks


REPO_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/contracts.py"
KNOWLEDGE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/knowledge.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EXPECTED_KNOWLEDGE_SHA256 = "b5681ad4c95871e2b300e7ac43a70241489a4e1d85442803d8207be9fa7e4599"
EXPECTED_PUBLIC_NAMES = "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
EXPECTED_PUBLIC_SLOTS = (
    (438, "ExtractedCommitmentCandidateRecord", "EmbeddingConfigCreateInput"),
    (628, "MemoryEvaluationSummaryResponse", "EmbeddingConfigRecord"),
)
EXPECTED_CHUNKS = (
    (
        "EntityCreateInput",
        "TrustedFactPlaybookListQueryInput",
        7,
        "dac9c8de1397648c3538c062eb972699025900ccb73897ad5995d3e6104fc524",
        "a892f07ca2c667ded63b6e9fff92292b3f150b645243c08ee59a4cce1838a5b5",
        "98ade437122bfe373806929942828126873773cf4ee869c0702f20a51273aa87",
    ),
    (
        "EntityRecord",
        "TrustedFactPlaybookExplainResponse",
        38,
        "5311986922bc37db986b44ba56fd1419300c5996e8740cf57ad106a32052c5ea",
        "47817ecf730e81633bdff7c09c891102e77bcffce355f901d709e35f820ea2bb",
        "8d6380c7bfa8ff94e6e7f122797d1dd040c1b524287f0c5a17491e2398eea236",
    ),
)
EXPECTED_AGGREGATE_NAMES = "587ef18a419f259fa3fb97af0c0392c8407d95b2b2605a58f7935077a900e079"
EXPECTED_AGGREGATE_AST = "02a2d59a3ff7abe2d5fadab3e3dfd07512e8dfa0a98937cf153914deb77fd096"
EXPECTED_AGGREGATE_SOURCE = "3a299c975b8a66da6768559a83a6d2d040ad76cf67111f22a832922546282f74"
EXPECTED_METADATA = "e7a5fed49a39197cfd0ab1c257799a096ebc17cbf962068130910c43d269e5d5"
EXPECTED_RAW_ANNOTATIONS = "a324b420252ce3250bd9f690746b8fad8d41fc3d7ae5e4a2454e462658b0edac"
EXPECTED_TYPE_HINTS = "0895c64f340012976f8322dad595dc21e579163b1614bf87fa855648c88ef0a5"
EXPECTED_DATACLASS_FIELDS = "32967963143b4a1942e49f47dae32dbfc29baab66697a5b37f5d8d2b54286db9"
EXPECTED_TYPED_DICTS = "58c2a5e4dcac124df287f3207af701d1c090f82aac4da67bb7a60a8c29ef027f"
EXPECTED_SCHEMAS = "37d248449fb641786c680210e293a8b3997a8cc0349068752027ff0b292dd1b4"
EXPECTED_EXPLICIT_METHODS = "8bab3cf377f1e0da74189bf8a4a3f1ca74845a6f92085a8ca48d3ba8695d6f7f"
EXPECTED_GENERATED_METHODS = "809f0ed5f385d29c6221baa2a0737bf4a8db45a2c81c591a202d562915c79357"
EXPECTED_EXPLICIT_SEMANTICS = "f3878d834b7bd1cc9f10c34fc4a301174a1a6db32c93bc2cddb719aa9bb9960e"

EXPLICIT_METHODS = (
    ("EntityCreateInput", "as_payload"),
    ("EntityEdgeCreateInput", "as_payload"),
    ("TemporalStateAtQueryInput", "as_payload"),
    ("TemporalTimelineQueryInput", "as_payload"),
    ("TemporalExplainQueryInput", "as_payload"),
    ("TrustedFactPatternListQueryInput", "as_payload"),
    ("TrustedFactPlaybookListQueryInput", "as_payload"),
)
RETRIEVAL_NAMES = (
    "EmbeddingConfigCreateInput",
    "MemoryEmbeddingUpsertInput",
    "SemanticMemoryRetrievalRequestInput",
    "RetrievalRunRecord",
    "RetrievalRunListSummary",
    "RetrievalRunListResponse",
    "RetrievalTraceSummary",
    "RetrievalTraceResponse",
    "EmbeddingConfigRecord",
    "EmbeddingConfigCreateResponse",
    "EmbeddingConfigListSummary",
    "EmbeddingConfigListResponse",
    "MemoryEmbeddingRecord",
    "MemoryEmbeddingUpsertResponse",
    "MemoryEmbeddingDetailResponse",
    "MemoryEmbeddingListSummary",
    "MemoryEmbeddingListResponse",
    "SemanticMemoryRetrievalResultItem",
    "SemanticMemoryRetrievalSummary",
    "SemanticMemoryRetrievalResponse",
    "RetrievalEvaluationFixtureResult",
    "RetrievalEvaluationSummary",
    "RetrievalEvaluationResponse",
    "PublicEvalSuiteDefinitionRecord",
    "PublicEvalSuiteDefinitionListResponse",
    "PublicEvalRunRecord",
    "PublicEvalResultRecord",
    "PublicEvalRunListResponse",
    "PublicEvalRunDetailResponse",
)


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


def _knowledge_nodes() -> list[ast.stmt]:
    return [
        node
        for node in _tree(KNOWLEDGE_PATH).body
        if any(not name.startswith("_") for name in _definition_names(node))
    ]


def _knowledge_names() -> list[str]:
    return [
        name
        for node in _knowledge_nodes()
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


def test_knowledge_source_scope_and_two_facade_slots_are_exact() -> None:
    source = KNOWLEDGE_PATH.read_text(encoding="utf-8")
    nodes = _knowledge_nodes()
    names = _knowledge_names()
    classes = [node.name for node in nodes if isinstance(node, ast.ClassDef)]
    assert _digest(source) == EXPECTED_KNOWLEDGE_SHA256
    assert len(nodes) == len(names) == len(classes) == 45
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
        and node.module == "alicebot_api._contracts.knowledge"
    ]
    assert len(imports) == 2
    assert [[alias.name for alias in node.names] for node in imports] == expected_chunks
    assert _literal_assignment(facade_tree, "_KNOWLEDGE_CONTRACT_CLASS_NAMES") == tuple(
        classes
    )
    assert _literal_assignment(facade_tree, "_KNOWLEDGE_EXPLICIT_METHODS") == EXPLICIT_METHODS

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
    assert set(RETRIEVAL_NAMES).isdisjoint(local_classes)
    assert "TaskArtifactChunkEmbeddingUpsertInput" not in local_classes
    assert (
        contracts.TaskArtifactChunkEmbeddingUpsertInput
        is tasks.TaskArtifactChunkEmbeddingUpsertInput
    )
    assert not hasattr(knowledge, "TaskArtifactChunkEmbeddingUpsertInput")


def test_knowledge_runtime_metadata_hints_schemas_and_methods_are_exact() -> None:
    names = _knowledge_names()
    classes = [(name, getattr(contracts, name)) for name in names]
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
        assert contract_class is getattr(knowledge, name)
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
            if method_name == "as_payload":
                assert method.__globals__ is vars(contracts)
                assert Path(method.__code__.co_filename).resolve() == KNOWLEDGE_PATH.resolve()
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

    assert len(dataclass_fields) == 7
    assert len(typed_dicts) == 38
    assert len(explicit_methods) == 7
    assert len(generated_methods) == 56
    assert _compact_digest(metadata) == EXPECTED_METADATA
    assert _compact_digest(raw_annotations) == EXPECTED_RAW_ANNOTATIONS
    assert _compact_digest(resolved_hints) == EXPECTED_TYPE_HINTS
    assert _compact_digest(dataclass_fields) == EXPECTED_DATACLASS_FIELDS
    assert _compact_digest(typed_dicts) == EXPECTED_TYPED_DICTS
    assert _compact_digest(schemas) == EXPECTED_SCHEMAS
    assert _compact_digest(explicit_methods) == EXPECTED_EXPLICIT_METHODS
    assert _compact_digest(generated_methods) == EXPECTED_GENERATED_METHODS
    assert _compact_digest(semantics) == EXPECTED_EXPLICIT_SEMANTICS

    assert contracts.EntityEdgeRecord.__orig_bases__ == (contracts.ContextPackEntityEdge,)
    assert knowledge.EntityEdgeRecord.__orig_bases__[0] is contracts.ContextPackEntityEdge
    entity_id = UUID("10000000-0000-0000-0000-000000000001")
    candidate = contracts.TemporalStateAtQueryInput(
        entity_id=entity_id,
        at=datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc),
    )
    assert pickle.loads(pickle.dumps(candidate)) == candidate
    assert candidate.as_payload() == {
        "entity_id": str(entity_id),
        "at": "2026-07-18T12:00:00+00:00",
    }


def test_knowledge_carrier_imports_fresh_and_contract_files_fit_cap() -> None:
    tree = _tree(KNOWLEDGE_PATH)
    top_level_imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "alicebot_api.contracts" not in top_level_imports
    assert top_level_imports == {
        "__future__",
        "dataclasses",
        "datetime",
        "typing",
        "uuid",
        "alicebot_api._contracts.common",
        "alicebot_api._contracts.runtime",
        "alicebot_api.store",
    }
    assert len(KNOWLEDGE_PATH.read_text(encoding="utf-8").splitlines()) < 4_000
    assert len(FACADE_PATH.read_text(encoding="utf-8").splitlines()) < 4_000

    code = """
import sys
from pathlib import Path
from alicebot_api._contracts import knowledge
assert knowledge.__name__ == 'alicebot_api._contracts.knowledge'
assert 'alicebot_api.contracts' not in sys.modules
assert knowledge.EntityCreateInput.__module__ == 'alicebot_api.contracts'
assert knowledge.EntityCreateInput.as_payload.__globals__ is vars(knowledge)
assert Path(knowledge.EntityCreateInput.as_payload.__code__.co_filename).resolve() == Path(knowledge.__file__).resolve()
assert knowledge.EntityEdgeRecord.__orig_bases__ == (knowledge.ContextPackEntityEdge,)
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


def test_knowledge_facade_normalizes_both_import_orders() -> None:
    checks = """
import dataclasses
import hashlib
import inspect
import pickle
import sys
import typing

knowledge_classes = [
    getattr(knowledge, name) for name in contracts._KNOWLEDGE_CONTRACT_CLASS_NAMES
]
knowledge_dataclasses = [
    value for value in knowledge_classes if dataclasses.is_dataclass(value)
]
knowledge_typed_dicts = [
    value for value in knowledge_classes if typing.is_typeddict(value)
]
assert len(knowledge_classes) == 45
assert len(knowledge_dataclasses) == 7
assert len(knowledge_typed_dicts) == 38
assert all(
    getattr(contracts, name) is getattr(knowledge, name)
    for name in contracts._KNOWLEDGE_CONTRACT_CLASS_NAMES
)
assert all(cls.__init__.__globals__ is vars(contracts) for cls in knowledge_dataclasses)
assert not [
    (cls.__name__, name)
    for cls in knowledge_dataclasses
    for name, method in vars(cls).items()
    if inspect.isfunction(method) and method.__globals__ is vars(knowledge)
]
assert len(contracts._KNOWLEDGE_EXPLICIT_METHODS) == 7
assert all(
    getattr(getattr(contracts, owner), method).__globals__ is vars(contracts)
    for owner, method in contracts._KNOWLEDGE_EXPLICIT_METHODS
)
assert contracts.EntityEdgeRecord.__orig_bases__ == (contracts.ContextPackEntityEdge,)
assert all(pickle.loads(pickle.dumps(cls)) is cls for cls in knowledge_classes)
assert all(typing.get_type_hints(cls, include_extras=True) for cls in knowledge_classes)
assert hashlib.sha256(
    "\\n".join(name for name in vars(contracts) if not name.startswith("_")).encode()
).hexdigest() == "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
if sys.version_info >= (3, 14):
    for typed_dict in knowledge_typed_dicts:
        annotate = typed_dict.__annotate__
        assert annotate.__module__ == "typing"
        assert annotate.__globals__ is vars(typing)
        assert isinstance(annotate(1), dict)
    for contract_class in knowledge_dataclasses:
        init_annotate = contract_class.__init__.__annotate__
        assert init_annotate.__module__ == "dataclasses"
        assert init_annotate.__globals__["__name__"] == "dataclasses"
        replace = contract_class.__replace__
        assert replace.__module__ == "dataclasses"
        assert replace.__globals__["__name__"] == "dataclasses"
    for owner, method_name in contracts._KNOWLEDGE_EXPLICIT_METHODS:
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
        "from alicebot_api._contracts import knowledge\n",
        "from alicebot_api._contracts import knowledge\n"
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


def test_knowledge_installed_wheel_and_python314_proofs_are_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert (
        workflow.count(
            "from alicebot_api._contracts import knowledge as contracts_knowledge"
        )
        == 2
    )
    for expected in (
        "contracts_knowledge_carrier_path = Path(contracts_knowledge.__file__).resolve()",
        "contracts_module.EntityCreateInput.as_payload.__code__.co_filename",
        "knowledge contracts carrier resolved to checkout source",
        "moved knowledge contract method resolved to checkout source",
        "assert len(knowledge_classes) == 45",
        "assert len(knowledge_dataclasses) == 7",
        "assert len(knowledge_typed_dicts) == 38",
        "contracts_module._KNOWLEDGE_EXPLICIT_METHODS",
        "knowledge_init_annotate.__module__ == \"dataclasses\"",
        "knowledge_explicit_annotate.__globals__ is vars(contracts_module)",
    ):
        assert expected in workflow

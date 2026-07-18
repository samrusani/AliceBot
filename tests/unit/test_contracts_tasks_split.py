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
from alicebot_api._contracts import continuity
from alicebot_api._contracts import governance
from alicebot_api._contracts import runtime
from alicebot_api._contracts import tasks


REPO_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/contracts.py"
TASKS_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/tasks.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EXPECTED_TASKS_SHA256 = "5446a48ad9a8cd75fd403c7b7a8513a472964821a8db27bfe14fbf6a9bcf5ad2"
EXPECTED_PUBLIC_NAMES = "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
EXPECTED_LOCAL_FUTURE_NAMES = (
    0,
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
)
EXPECTED_PUBLIC_SLOTS = (
    (447, "MemoryEmbeddingUpsertInput", "SemanticMemoryRetrievalRequestInput"),
    (725, "ApprovalResolutionSummaryTracePayload", "GmailAccountConnectInput"),
    (768, "CalendarEventListResponse", "ApprovalRequestCreateResponse"),
)
EXPECTED_CHUNKS = (
    (
        "TaskArtifactChunkEmbeddingUpsertInput",
        "TaskArtifactChunkEmbeddingUpsertInput",
        1,
        "c66f18a25184ab3483ff6e452896bf7efda419d395681214a3d51179eb55cccc",
        "6f9daa268fe1209215d836131f304006b91a4c615fc3a810ea4a465345d30f13",
        "659f342d67d867290d107529519c0623bdb900d8e1b7af8b68d17dbb535fa158",
    ),
    (
        "TaskCreateInput",
        "TaskRunMutationResponse",
        21,
        "e7ed2d1948c133dcad5352f5dda7bd45883e14deb7f7b7839d9d7e67fb6be04d",
        "d8e5e6d0113bd1ae7601d0dc55fa26b9e96e2b8c942abcaa0b834ebabba09bcf",
        "9e7fc3e3a362d6d3912527747bd07aa05a3c324fc015b7a1d320c7b4c1a3eb47",
    ),
    (
        "TaskWorkspaceCreateInput",
        "TaskStepTransitionSummaryTracePayload",
        69,
        "f87076c52f8a33d923f98941676afe1ca626551e3e1e90da646c71dffac7d03c",
        "20026bf2ae75f1d919fca4835826b0764ec3049bd1a1ffa6834dcdb338d33809",
        "2fb13fafce83f6997a4fa1e119e3785a48172e8de4c284512cfe5ea110243177",
    ),
)
EXPECTED_AGGREGATE_NAMES = "2c31193a8a78bd47d0d23dc18b62ce695dd77b4b1f419b7fb63d2eb0d2bdfe9b"
EXPECTED_AGGREGATE_AST = "86516fa472f30a6b7c04b86b7ac04ceef8ae334c0edb827d09784e104207d85d"
EXPECTED_AGGREGATE_SOURCE = "57ab6db402505b5144fe399219cca97c11035c1600a56918f79538991578cf1d"
EXPECTED_METADATA = "a7d109d80c03aa3e48ecf16c13bc19c74df0836eece0055288813bda2dcbe7e3"
EXPECTED_RAW_ANNOTATIONS = "4b0e28a0ae1e379470aeee1612b0ce72e0e31a2c5117e6c98bdfe615ae926438"
EXPECTED_TYPE_HINTS = "43921fb5666b41c30f0bb4e31ec5585614513a5732c0534f46009c5f5f4cb643"
EXPECTED_DATACLASS_FIELDS = "a6be74dedc60423b2db7b518bdb943a35062238736460ea98d7de5dac7a68e6a"
EXPECTED_TYPED_DICTS = "51aefbec40a494c09adb964b692a9e54790cb1d80c12c7b34b5d83c8d4b79921"
EXPECTED_SCHEMAS = "cfff55090f313b64a37ec19c622f6f6eab4e2af3219ded0b57b2e884c3a512f4"
EXPECTED_EXPLICIT_METHODS = "a5f03db37eb21851283eea4a7eef97d682330a251fc20883f793ca8d21509845"
EXPECTED_GENERATED_METHODS = "5d27a440c5b7255b581df82b69ca4043c745494847a0f60a25d6e9d54aba1ca2"
EXPECTED_EXPLICIT_SEMANTICS = "4353793206bee59236e88a5064e89923b322ca7235f809df74ffba350858cc36"

EXPLICIT_METHODS = (
    ("TaskArtifactChunkEmbeddingUpsertInput", "as_payload"),
    ("TaskScopedSemanticArtifactChunkRetrievalInput", "as_payload"),
    ("ArtifactScopedSemanticArtifactChunkRetrievalInput", "as_payload"),
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


def _tasks_nodes() -> list[ast.stmt]:
    return [
        node
        for node in _tree(TASKS_PATH).body
        if any(not name.startswith("_") for name in _definition_names(node))
    ]


def _tasks_names() -> list[str]:
    return [
        name
        for node in _tasks_nodes()
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


def test_tasks_source_scope_and_three_facade_slots_are_exact() -> None:
    source = TASKS_PATH.read_text(encoding="utf-8")
    nodes = _tasks_nodes()
    names = _tasks_names()
    classes = [node.name for node in nodes if isinstance(node, ast.ClassDef)]
    assert _digest(source) == EXPECTED_TASKS_SHA256
    assert len(nodes) == len(names) == len(classes) == 91
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
        and node.module == "alicebot_api._contracts.tasks"
    ]
    assert len(imports) == 3
    assert [[alias.name for alias in node.names] for node in imports] == expected_chunks
    assert _literal_assignment(facade_tree, "_TASK_CONTRACT_CLASS_NAMES") == tuple(
        classes
    )
    assert _literal_assignment(facade_tree, "_TASK_EXPLICIT_METHODS") == EXPLICIT_METHODS

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
    assert contracts.TaskRecord is tasks.TaskRecord
    assert "ExecutionBudgetRecord" not in local_names
    assert "GmailAccountConnectInput" not in local_names
    assert "ProxyExecutionRequestInput" not in local_names
    assert not hasattr(tasks, "ExecutionBudgetRecord")
    assert not hasattr(tasks, "GmailAccountConnectInput")
    assert not hasattr(tasks, "ProxyExecutionRequestInput")


def test_tasks_runtime_metadata_hints_schemas_and_methods_are_exact() -> None:
    classes = [(name, getattr(contracts, name)) for name in _tasks_names()]
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
        assert contract_class is getattr(tasks, name)
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
                assert Path(method.__code__.co_filename).resolve() == TASKS_PATH.resolve()
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

    assert len(dataclass_fields) == 18
    assert len(typed_dicts) == 73
    assert len(explicit_methods) == 3
    assert len(generated_methods) == 144
    assert _compact_digest(metadata) == EXPECTED_METADATA
    assert _compact_digest(raw_annotations) == EXPECTED_RAW_ANNOTATIONS
    assert _compact_digest(resolved_hints) == EXPECTED_TYPE_HINTS
    assert _compact_digest(dataclass_fields) == EXPECTED_DATACLASS_FIELDS
    assert _compact_digest(typed_dicts) == EXPECTED_TYPED_DICTS
    assert _compact_digest(schemas) == EXPECTED_SCHEMAS
    assert _compact_digest(explicit_methods) == EXPECTED_EXPLICIT_METHODS
    assert _compact_digest(generated_methods) == EXPECTED_GENERATED_METHODS
    assert _compact_digest(semantics) == EXPECTED_EXPLICIT_SEMANTICS

    assert contracts.TaskStepListSummary.__orig_bases__ == (
        contracts.TaskStepSequencingSummary,
    )
    assert tasks.TaskStepListSummary.__orig_bases__ == (
        tasks.TaskStepSequencingSummary,
    )
    assert contracts.ResumptionBriefConversationSummary.__orig_bases__ == (
        contracts.ResumptionBriefSectionSummary,
    )
    assert tasks.ResumptionBriefConversationSummary.__orig_bases__ == (
        tasks.ResumptionBriefSectionSummary,
    )

    assert tasks.ToolRecord is governance.ToolRecord
    assert tasks.ToolRoutingRequestRecord is governance.ToolRoutingRequestRecord
    task_record_hints = typing.get_type_hints(
        contracts.TaskRecord,
        include_extras=True,
    )
    assert task_record_hints["request"] is governance.ToolRoutingRequestRecord
    assert task_record_hints["tool"] is governance.ToolRecord
    conversation_hints = typing.get_type_hints(
        contracts.ResumptionBriefConversationSection,
        include_extras=True,
    )
    assert typing.get_args(conversation_hints["items"])[0] is runtime.ThreadEventRecord
    open_loop_hints = typing.get_type_hints(
        contracts.ResumptionBriefOpenLoopSection,
        include_extras=True,
    )
    assert typing.get_args(open_loop_hints["items"])[0] is continuity.OpenLoopRecord
    highlight_hints = typing.get_type_hints(
        contracts.ResumptionBriefMemoryHighlightSection,
        include_extras=True,
    )
    assert typing.get_args(highlight_hints["items"])[0] is runtime.ContextPackMemory
    record_hints = typing.get_type_hints(
        contracts.ResumptionBriefRecord,
        include_extras=True,
    )
    assert record_hints["thread"] is runtime.ThreadRecord
    runtime_provenance_hints = typing.get_type_hints(
        contracts.ContextPackArtifactChunkSourceProvenance,
        include_extras=True,
    )
    assert tasks.TaskArtifactChunkRetrievalMatch in typing.get_args(
        runtime_provenance_hints["lexical_match"]
    )
    runtime_summary_hints = typing.get_type_hints(
        contracts.ContextPackArtifactChunkSummary,
        include_extras=True,
    )
    assert tasks.TaskArtifactChunkRetrievalScope in typing.get_args(
        runtime_summary_hints["scope"]
    )
    assert typing.get_type_hints(
        contracts.ApprovalRequestCreateResponse,
        include_extras=True,
    )["task"] is tasks.TaskRecord
    assert typing.get_type_hints(
        contracts.ContinuityResumptionListSection,
        include_extras=True,
    )["summary"] is tasks.ResumptionBriefSectionSummary

    artifact_id = UUID("10000000-0000-0000-0000-000000000001")
    config_id = UUID("20000000-0000-0000-0000-000000000002")
    embedding = contracts.TaskArtifactChunkEmbeddingUpsertInput(
        task_artifact_chunk_id=artifact_id,
        embedding_config_id=config_id,
        vector=(0.25, 0.75),
    )
    assert embedding.as_payload() == {
        "task_artifact_chunk_id": str(artifact_id),
        "embedding_config_id": str(config_id),
        "vector": [0.25, 0.75],
    }
    task_run_one = contracts.TaskRunCreateInput(task_id=artifact_id)
    task_run_two = contracts.TaskRunCreateInput(task_id=artifact_id)
    assert task_run_one.checkpoint == {}
    assert task_run_one.checkpoint is not task_run_two.checkpoint
    semantic = contracts.TaskScopedSemanticArtifactChunkRetrievalInput(
        task_id=artifact_id,
        embedding_config_id=config_id,
        query_vector=(0.25, 0.75),
    )
    assert semantic.as_payload() == {
        "task_id": str(artifact_id),
        "embedding_config_id": str(config_id),
        "query_vector": [0.25, 0.75],
        "limit": 5,
    }
    assert pickle.loads(pickle.dumps(semantic)) == semantic


def test_tasks_carrier_imports_fresh_and_contract_files_fit_cap() -> None:
    tree = _tree(TASKS_PATH)
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
        "alicebot_api._contracts.continuity",
        "alicebot_api._contracts.governance",
        "alicebot_api._contracts.runtime",
        "alicebot_api.store",
    }
    assert len(TASKS_PATH.read_text(encoding="utf-8").splitlines()) < 4_000
    assert len(FACADE_PATH.read_text(encoding="utf-8").splitlines()) < 4_000

    code = """
import dataclasses
import inspect
import sys
from pathlib import Path
from alicebot_api._contracts import continuity, governance, runtime, tasks
assert tasks.__name__ == 'alicebot_api._contracts.tasks'
assert 'alicebot_api.contracts' not in sys.modules
assert tasks.TaskRecord.__module__ == 'alicebot_api.contracts'
assert tasks.TaskArtifactChunkEmbeddingUpsertInput.__module__ == 'alicebot_api.contracts'
assert tasks.TaskArtifactChunkEmbeddingUpsertInput.as_payload.__globals__ is vars(tasks)
assert Path(tasks.TaskArtifactChunkEmbeddingUpsertInput.as_payload.__code__.co_filename).resolve() == Path(tasks.__file__).resolve()
assert inspect.signature(tasks.TaskScopedSemanticArtifactChunkRetrievalInput).parameters['limit'].default == 5
assert tasks.TaskStepListSummary.__orig_bases__ == (tasks.TaskStepSequencingSummary,)
assert tasks.ResumptionBriefConversationSummary.__orig_bases__ == (tasks.ResumptionBriefSectionSummary,)
assert tasks.ToolRecord is governance.ToolRecord
assert tasks.ToolRoutingRequestRecord is governance.ToolRoutingRequestRecord
assert tasks.ThreadEventRecord is runtime.ThreadEventRecord
assert tasks.ThreadRecord is runtime.ThreadRecord
assert tasks.ContextPackMemory is runtime.ContextPackMemory
assert tasks.OpenLoopRecord is continuity.OpenLoopRecord
first = tasks.TaskRunCreateInput(task_id=__import__('uuid').UUID(int=1))
second = tasks.TaskRunCreateInput(task_id=__import__('uuid').UUID(int=1))
assert first.checkpoint == {}
assert first.checkpoint is not second.checkpoint
assert not hasattr(tasks, 'ExecutionBudgetRecord')
assert not hasattr(tasks, 'GmailAccountConnectInput')
assert not hasattr(tasks, 'ProxyExecutionRequestInput')
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


def test_tasks_facade_normalizes_both_import_orders() -> None:
    checks = """
import dataclasses
import hashlib
import inspect
import pickle
import sys
import typing

from alicebot_api._contracts import continuity as tasks_continuity
from alicebot_api._contracts import governance as tasks_governance
from alicebot_api._contracts import runtime as tasks_runtime

tasks_classes = [
    getattr(tasks, name) for name in contracts._TASK_CONTRACT_CLASS_NAMES
]
tasks_dataclasses = [
    value for value in tasks_classes if dataclasses.is_dataclass(value)
]
tasks_typed_dicts = [
    value for value in tasks_classes if typing.is_typeddict(value)
]
assert len(tasks_classes) == 91
assert len(tasks_dataclasses) == 18
assert len(tasks_typed_dicts) == 73
assert all(
    getattr(contracts, name) is getattr(tasks, name)
    for name in contracts._TASK_CONTRACT_CLASS_NAMES
)
assert all(cls.__init__.__globals__ is vars(contracts) for cls in tasks_dataclasses)
assert not [
    (cls.__name__, name)
    for cls in tasks_dataclasses
    for name, method in vars(cls).items()
    if inspect.isfunction(method) and method.__globals__ is vars(tasks)
]
assert len(contracts._TASK_EXPLICIT_METHODS) == 3
assert all(
    getattr(getattr(contracts, owner), method).__globals__ is vars(contracts)
    for owner, method in contracts._TASK_EXPLICIT_METHODS
)
assert all(pickle.loads(pickle.dumps(cls)) is cls for cls in tasks_classes)
for contract_class in tasks_classes:
    typing.get_type_hints(contract_class, include_extras=True)
assert typing.get_type_hints(
    contracts.ApprovalRequestCreateResponse,
    include_extras=True,
)["task"] is contracts.TaskRecord
assert typing.get_type_hints(
    contracts.ContinuityResumptionListSection,
    include_extras=True,
)["summary"] is contracts.ResumptionBriefSectionSummary
assert contracts.TaskStepListSummary.__orig_bases__ == (
    contracts.TaskStepSequencingSummary,
)
assert tasks.TaskStepListSummary.__orig_bases__ == (
    tasks.TaskStepSequencingSummary,
)
assert contracts.ResumptionBriefConversationSummary.__orig_bases__ == (
    contracts.ResumptionBriefSectionSummary,
)
assert tasks.ResumptionBriefConversationSummary.__orig_bases__ == (
    tasks.ResumptionBriefSectionSummary,
)
assert tasks.ToolRecord is tasks_governance.ToolRecord
assert tasks.ToolRoutingRequestRecord is tasks_governance.ToolRoutingRequestRecord
tasks_task_record_hints = typing.get_type_hints(
    contracts.TaskRecord,
    include_extras=True,
)
assert tasks_task_record_hints["request"] is tasks_governance.ToolRoutingRequestRecord
assert tasks_task_record_hints["tool"] is tasks_governance.ToolRecord
tasks_conversation_hints = typing.get_type_hints(
    contracts.ResumptionBriefConversationSection,
    include_extras=True,
)
assert typing.get_args(tasks_conversation_hints["items"])[0] is tasks_runtime.ThreadEventRecord
tasks_open_loop_hints = typing.get_type_hints(
    contracts.ResumptionBriefOpenLoopSection,
    include_extras=True,
)
assert typing.get_args(tasks_open_loop_hints["items"])[0] is tasks_continuity.OpenLoopRecord
tasks_highlight_hints = typing.get_type_hints(
    contracts.ResumptionBriefMemoryHighlightSection,
    include_extras=True,
)
assert typing.get_args(tasks_highlight_hints["items"])[0] is tasks_runtime.ContextPackMemory
tasks_record_hints = typing.get_type_hints(
    contracts.ResumptionBriefRecord,
    include_extras=True,
)
assert tasks_record_hints["thread"] is tasks_runtime.ThreadRecord
tasks_runtime_provenance_hints = typing.get_type_hints(
    contracts.ContextPackArtifactChunkSourceProvenance,
    include_extras=True,
)
assert tasks.TaskArtifactChunkRetrievalMatch in typing.get_args(
    tasks_runtime_provenance_hints["lexical_match"]
)
tasks_runtime_summary_hints = typing.get_type_hints(
    contracts.ContextPackArtifactChunkSummary,
    include_extras=True,
)
assert tasks.TaskArtifactChunkRetrievalScope in typing.get_args(
    tasks_runtime_summary_hints["scope"]
)
assert contracts.TaskRecord is tasks.TaskRecord
assert not hasattr(tasks, "ExecutionBudgetRecord")
assert not hasattr(tasks, "GmailAccountConnectInput")
assert not hasattr(tasks, "ProxyExecutionRequestInput")
assert hashlib.sha256(
    "\\n".join(name for name in vars(contracts) if not name.startswith("_")).encode()
).hexdigest() == "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
if sys.version_info >= (3, 14):
    for typed_dict in tasks_typed_dicts:
        annotate = typed_dict.__annotate__
        assert annotate.__module__ == "typing"
        assert annotate.__globals__ is vars(typing)
        assert isinstance(annotate(1), dict)
    for contract_class in tasks_dataclasses:
        init_annotate = contract_class.__init__.__annotate__
        assert init_annotate.__module__ == "dataclasses"
        assert init_annotate.__globals__["__name__"] == "dataclasses"
        replace = contract_class.__replace__
        assert replace.__module__ == "dataclasses"
        assert replace.__globals__["__name__"] == "dataclasses"
    for owner, method_name in contracts._TASK_EXPLICIT_METHODS:
        explicit_annotate = getattr(
            getattr(getattr(contracts, owner), method_name),
            "__annotate__",
        )
        assert explicit_annotate.__module__ == "alicebot_api.contracts"
        assert explicit_annotate.__globals__ is vars(contracts)
        assert explicit_annotate.__qualname__ == f"{owner}.__annotate__"
        assert isinstance(explicit_annotate(1), dict)
"""
    import_orders = (
        "import alicebot_api.contracts as contracts\n"
        "from alicebot_api._contracts import tasks\n",
        "from alicebot_api._contracts import tasks\n"
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


def test_tasks_installed_wheel_and_python314_proofs_are_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert (
        workflow.count(
            "from alicebot_api._contracts import tasks as contracts_tasks"
        )
        == 2
    )
    for repeated in (
        "tasks_classes = [",
        "assert len(tasks_classes) == 91",
        "assert len(tasks_dataclasses) == 18",
        "assert len(tasks_typed_dicts) == 73",
        "tasks_approval_task_annotation = (",
        "tasks_continuity_summary_hint = typing.get_type_hints(",
        "tasks_step_list_orig_bases = (",
        "tasks_resumption_orig_bases = (",
        "tasks_init_annotate.__module__ == \"dataclasses\"",
        "tasks_explicit_annotate.__globals__ is vars(contracts_module)",
    ):
        assert workflow.count(repeated) == 2
    for expected in (
        "contracts_tasks_carrier_path = Path(contracts_tasks.__file__).resolve()",
        "contracts_module.TaskArtifactChunkEmbeddingUpsertInput.as_payload.__code__.co_filename",
        "tasks contracts carrier resolved to checkout source",
        "moved tasks contract method resolved to checkout source",
        "contracts_module._TASK_EXPLICIT_METHODS",
        "assert not hasattr(contracts_tasks, \"GmailAccountConnectInput\")",
        "assert not hasattr(contracts_tasks, \"ExecutionBudgetRecord\")",
        "assert not hasattr(contracts_tasks, \"ProxyExecutionRequestInput\")",
    ):
        assert expected in workflow

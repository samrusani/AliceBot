from __future__ import annotations

import ast
import hashlib
import inspect
import os
from pathlib import Path
import pickle
import subprocess
import sys
import typing

import alicebot_api.contracts as contracts
from alicebot_api._contracts import runtime


REPO_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/contracts.py"
RUNTIME_PATH = REPO_ROOT / "apps/api/src/alicebot_api/_contracts/runtime.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/tests.yml"

EXPECTED_RUNTIME_SHA256 = "7ba8f9584d063767c7bb1382232d6eb85365197dc4e8ee0abec619ce699bbaa3"
EXPECTED_RUNTIME_NAMES = "edd6b6ad76d7b9ee0697c9f6e61594c7d451afd83de36f0c79f0ebf38adad016"
EXPECTED_RUNTIME_AST = "c05127060666f2a79a50c018e64cfdad0775b567f4a32dc8a83ceb57e0c669a3"
EXPECTED_RUNTIME_SOURCE = "0ae064b5dbf6df5ec295452825837f2a66c07a6a38b08f917957df5afc36ff7c"
EXPECTED_PUBLIC_NAMES = "c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed"
EXPECTED_GENERATED_CLONER_AST = "fce3a758098e9f064e8e93d687d1b6640fa5498756aebc575a08e18483f4910b"

EXPLICIT_METHODS = (
    ("ContextCompilerLimits", "as_payload"),
    ("CompileContextSemanticRetrievalInput", "as_payload"),
    ("CompileContextTaskScopedArtifactRetrievalInput", "as_payload"),
    ("CompileContextArtifactScopedArtifactRetrievalInput", "as_payload"),
    ("CompileContextTaskScopedSemanticArtifactRetrievalInput", "as_payload"),
    ("CompileContextArtifactScopedSemanticArtifactRetrievalInput", "as_payload"),
    ("CompilerDecision", "to_trace_event"),
    ("ModelInvocationRequest", "as_payload"),
    ("ModelInvocationResponse", "to_trace_payload"),
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


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


def _runtime_nodes() -> list[ast.stmt]:
    return [
        node
        for node in _tree(RUNTIME_PATH).body
        if any(not name.startswith("_") for name in _definition_names(node))
    ]


def _runtime_names() -> list[str]:
    return [
        name
        for node in _runtime_nodes()
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


def test_runtime_definitions_are_exact_contiguous_mechanical_moves() -> None:
    source = RUNTIME_PATH.read_text(encoding="utf-8")
    nodes = _runtime_nodes()
    names = _runtime_names()
    classes = [node.name for node in nodes if isinstance(node, ast.ClassDef)]

    assert _digest(source) == EXPECTED_RUNTIME_SHA256
    assert len(nodes) == len(names) == 93
    assert len(classes) == 88
    assert _digest("\n".join(names)) == EXPECTED_RUNTIME_NAMES
    assert (
        _digest("\n".join(ast.dump(node, include_attributes=False) for node in nodes))
        == EXPECTED_RUNTIME_AST
    )
    assert (
        _digest("\n".join(ast.get_source_segment(source, node) or "" for node in nodes))
        == EXPECTED_RUNTIME_SOURCE
    )

    facade_tree = _tree(FACADE_PATH)
    imports = [
        node
        for node in facade_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "alicebot_api._contracts.runtime"
    ]
    assert len(imports) == 1
    assert [alias.name for alias in imports[0].names] == names
    assert _literal_assignment(facade_tree, "_RUNTIME_CONTRACT_CLASS_NAMES") == tuple(classes)
    assert _literal_assignment(facade_tree, "_RUNTIME_EXPLICIT_METHODS") == EXPLICIT_METHODS
    generated_cloners = [
        node
        for node in facade_tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_clone_generated_contract_function"
    ]
    assert len(generated_cloners) == 1
    assert _digest(ast.dump(generated_cloners[0], include_attributes=False)) == (
        EXPECTED_GENERATED_CLONER_AST
    )

    locally_defined = {
        name
        for node in facade_tree.body
        for name in _definition_names(node)
        if name in set(names)
    }
    assert not locally_defined


def test_runtime_public_identity_forward_refs_pickle_and_methods_are_exact() -> None:
    names = _runtime_names()
    classes = [
        (name, getattr(contracts, name))
        for name in names
        if isinstance(getattr(contracts, name), type)
    ]
    aliases = [name for name in names if not isinstance(getattr(contracts, name), type)]
    assert len(classes) == 88
    assert len(aliases) == 5
    assert aliases == [
        "CompileContextArtifactRetrievalInput",
        "CompileContextSemanticArtifactRetrievalInput",
        "ThreadActivityPosture",
        "ThreadRiskPosture",
        "ThreadHealthPosture",
    ]

    typed_dict_count = 0
    dataclass_count = 0
    for name, contract_class in classes:
        assert contract_class is getattr(runtime, name)
        assert contract_class.__module__ == "alicebot_api.contracts"
        assert contract_class.__qualname__ == name
        assert pickle.loads(pickle.dumps(contract_class)) is contract_class
        annotations = getattr(contract_class, "__annotations__", {})
        for annotation in annotations.values():
            if isinstance(annotation, typing.ForwardRef):
                assert annotation.__forward_module__ == "alicebot_api.contracts"
        typing.get_type_hints(contract_class, include_extras=True)
        typed_dict_count += int(typing.is_typeddict(contract_class))
        dataclass_count += int(hasattr(contract_class, "__dataclass_fields__"))

    assert typed_dict_count == 71
    assert dataclass_count == 17
    assert _digest("\n".join(name for name in vars(contracts) if not name.startswith("_"))) == (
        EXPECTED_PUBLIC_NAMES
    )

    for owner_name, method_name in EXPLICIT_METHODS:
        method = getattr(getattr(contracts, owner_name), method_name)
        assert method.__globals__ is vars(contracts)
        assert method.__module__ == "alicebot_api.contracts"
        assert method.__qualname__ == f"{owner_name}.{method_name}"
        assert method.__code__.co_qualname == f"{owner_name}.{method_name}"
        assert Path(method.__code__.co_filename).resolve() == RUNTIME_PATH.resolve()
        assert pickle.loads(pickle.dumps(method)) is method

    limits = contracts.ContextCompilerLimits()
    assert limits.as_payload() == {
        "max_sessions": 3,
        "max_events": 8,
        "max_memories": 5,
        "max_entities": 5,
        "max_entity_edges": 10,
    }
    assert pickle.loads(pickle.dumps(limits)) == limits


def test_runtime_carrier_imports_fresh_without_a_facade_cycle_and_fits_cap() -> None:
    tree = _tree(RUNTIME_PATH)
    top_level_runtime_imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "alicebot_api.contracts" not in top_level_runtime_imports
    assert top_level_runtime_imports == {
        "__future__",
        "dataclasses",
        "typing",
        "uuid",
        "alicebot_api._contracts.common",
        "alicebot_api.store",
    }
    assert len(RUNTIME_PATH.read_text(encoding="utf-8").splitlines()) < 4_000

    code = """
import sys
from pathlib import Path
from alicebot_api._contracts import runtime
assert runtime.__name__ == 'alicebot_api._contracts.runtime'
assert 'alicebot_api.contracts' not in sys.modules
assert runtime.ContextCompilerLimits.__module__ == 'alicebot_api.contracts'
assert runtime.ContextCompilerLimits.as_payload.__globals__ is vars(runtime)
assert Path(runtime.ContextCompilerLimits.as_payload.__code__.co_filename).resolve() == Path(runtime.__file__).resolve()
assert runtime.ContextCompilerLimits().as_payload()['max_sessions'] == 3
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


def test_runtime_facade_normalizes_both_import_orders() -> None:
    checks = """
import hashlib
import inspect
import pickle
import sys
import typing

runtime_classes = [
    value
    for value in vars(runtime).values()
    if isinstance(value, type) and value.__module__ == 'alicebot_api.contracts'
]
runtime_dataclasses = [
    value for value in runtime_classes if hasattr(value, '__dataclass_fields__')
]
runtime_typed_dicts = [value for value in runtime_classes if typing.is_typeddict(value)]
assert len(runtime_classes) == 88
assert len(runtime_dataclasses) == 17
assert len(runtime_typed_dicts) == 71
assert all(cls.__init__.__globals__ is vars(contracts) for cls in runtime_dataclasses)
assert not [
    (cls.__name__, name)
    for cls in runtime_dataclasses
    for name, method in vars(cls).items()
    if inspect.isfunction(method) and method.__globals__ is vars(runtime)
]
assert all(
    getattr(getattr(contracts, owner), method).__globals__ is vars(contracts)
    for owner, method in contracts._RUNTIME_EXPLICIT_METHODS
)
assert contracts.DecisionKind is common.DecisionKind
assert contracts.isoformat_or_none.__globals__ is vars(contracts)
assert contracts.isoformat_or_none.__module__ == 'alicebot_api.contracts'
assert pickle.loads(pickle.dumps(contracts.isoformat_or_none)) is contracts.isoformat_or_none
assert hashlib.sha256(
    '\\n'.join(name for name in vars(contracts) if not name.startswith('_')).encode()
).hexdigest() == 'c0a3b796ae8ba267137ace2abf5ec8efcfa192a486b2fcd0fa787c3f0ab6f2ed'
if sys.version_info >= (3, 14):
    for typed_dict in runtime_typed_dicts:
        annotate = typed_dict.__annotate__
        assert annotate.__module__ == 'typing'
        assert annotate.__globals__ is vars(typing)
        assert isinstance(annotate(1), dict)
    init_annotate = runtime_dataclasses[0].__init__.__annotate__
    assert init_annotate.__module__ == 'dataclasses'
    assert init_annotate.__globals__['__name__'] == 'dataclasses'
"""
    import_orders = (
        "import alicebot_api.contracts as contracts\n"
        "from alicebot_api._contracts import common, runtime\n",
        "from alicebot_api._contracts import common, runtime\n"
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


def test_runtime_installed_wheel_and_python314_proofs_are_pinned() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for expected in (
        'python-version: ["3.13", "3.14"]',
        "from alicebot_api._contracts import runtime as contracts_runtime",
        "contracts_runtime_carrier_path = Path(contracts_runtime.__file__).resolve()",
        "contracts_module.ContextCompilerLimits.as_payload.__code__.co_filename",
        "runtime contracts carrier resolved to checkout source",
        "moved runtime contract method resolved to checkout source",
        "runtime_class is contracts_runtime.ContextCompilerLimits",
        "runtime_method.__globals__ is vars(contracts_module)",
        "pickle.loads(pickle.dumps(runtime_limits)) == runtime_limits",
        "scope_annotation.__forward_module__ == \"alicebot_api.contracts\"",
        "assert len(runtime_typed_dicts) == 71",
        'typed_dict_annotate.__module__ == "typing"',
        "typed_dict_annotate.__globals__ is vars(typing)",
        "isinstance(typed_dict_annotate(1), dict)",
        "runtime_method_annotate.__qualname__.startswith(",
        'runtime_method_annotate.__qualname__.endswith("__annotate__")',
        'runtime_init_annotate.__module__ == "dataclasses"',
        'runtime_init_annotate.__qualname__ == (',
        '"_make_annotate_function.<locals>.__annotate__"',
        'runtime_init_annotate.__globals__["__name__"] == "dataclasses"',
        "runtime_dataclasses = [",
        "contract_class.__init__.__globals__ is vars(contracts_module)",
        "method.__globals__ is vars(contracts_runtime)",
        "contracts_module._RUNTIME_EXPLICIT_METHODS",
    ):
        assert expected in workflow

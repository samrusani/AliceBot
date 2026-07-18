from __future__ import annotations

import ast
import hashlib
import inspect
import os
from pathlib import Path
import subprocess
import sys

import pytest

import alicebot_api.sqlite_store as sqlite_store
import alicebot_api.vnext_store as postgres_store
from alicebot_api.vnext_stores import memory_lifecycle_common as common
from alicebot_api.vnext_stores.postgres import columns as postgres_columns
from alicebot_api.vnext_stores.postgres import memory_lifecycle as postgres_lifecycle
from alicebot_api.vnext_stores.postgres import primitives as postgres_primitives
from alicebot_api.vnext_stores.sqlite import columns as sqlite_columns
from alicebot_api.vnext_stores.sqlite import memory_lifecycle as sqlite_lifecycle
from alicebot_api.vnext_stores.sqlite import primitives as sqlite_primitives


REPO_ROOT = Path(__file__).resolve().parents[2]
POSTGRES_FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/vnext_store.py"
SQLITE_FACADE_PATH = REPO_ROOT / "apps/api/src/alicebot_api/sqlite_store.py"
COMMON_PATH = REPO_ROOT / "apps/api/src/alicebot_api/vnext_stores/memory_lifecycle_common.py"
POSTGRES_CARRIER_PATH = REPO_ROOT / "apps/api/src/alicebot_api/vnext_stores/postgres/memory_lifecycle.py"
SQLITE_CARRIER_PATH = REPO_ROOT / "apps/api/src/alicebot_api/vnext_stores/sqlite/memory_lifecycle.py"

POSTGRES_METHODS = (
    "create_memory",
    "upsert_memory_by_key",
    "get_memory_for_update",
    "get_memory_for_redaction",
    "lock_project_update_artifacts_for_redaction",
    "memory_redaction_bundle_is_exact",
    "lock_graph_mutation",
    "list_memory_ids_with_embeddings",
    "update_memory_fact_keys",
    "list_memories_missing_fact_keys",
    "update_memory",
    "_redaction_mode",
    "redact_memory_bundle",
    "redact_memory_content",
    "redact_memory_revisions",
    "redact_memory_events",
    "create_provenance_link",
    "list_provenance_links",
    "list_provenance_links_for_targets",
)
SQLITE_METHODS = (
    "create_memory",
    "upsert_memory_by_key",
    "get_memory_for_update",
    "get_memory_for_redaction",
    "lock_project_update_artifacts_for_redaction",
    "memory_redaction_bundle_is_exact",
    "update_memory",
    "lock_graph_mutation",
    "list_memory_ids_with_embeddings",
    "update_memory_fact_keys",
    "list_memories_missing_fact_keys",
    "_redaction_mode",
    "redact_memory_bundle",
    "redact_memory_content",
    "redact_memory_revisions",
    "redact_memory_events",
    "create_provenance_link",
    "list_provenance_links",
    "list_provenance_links_for_targets",
)

SOURCE_RECEIPTS = {
    COMMON_PATH: "191f0ebd106cf757f5082af171da06e2e77eee518d17e80e5489e9e0d81493fe",
    POSTGRES_CARRIER_PATH: "1960ff3dd899c63c0f298e79b7e0ea13c9115ae7aacc91081967ce9473d92f92",
    SQLITE_CARRIER_PATH: "3d334607e5c207b6a01dbfe6aa2b209d82767bd46387cd5837a82ab439b02388",
}
EXPECTED_METHOD_AST_MANIFESTS = {
    "postgres": "538d5a18c0dfa01b368b409832738d5a25d7ff4bd063ba17062b01fefbb05d3b",
    "sqlite": "ea2dad84a804ac9b15c8815aec774c32d37e240a76145273b21dc61c76cb0922",
}
EXPECTED_METADATA_MANIFESTS = {
    "postgres": "af03955c805f720b8d3ec735f8202efeb5f405c8c7de1cc45cbfef3644867824",
    "sqlite": "9a5a4a9f0ae533652250a9e9854cd34a068392d71ffde98b012c9c620134d2c4",
}
EXPECTED_CLASS_ORDERS = {
    "PostgresVNextStore": (168, "00e1d9bab613f90665fb2f7666bfff3be1cdc3d96f925614b0bf7e04cecce638"),
    "SQLiteVNextStore": (121, "2c0b5694a015fe7939e91bb5572145b8bf82598edfcbb579e51b4175c392e2e5"),
}
EXPECTED_FACADE_COMMENT_DIGESTS = {
    POSTGRES_FACADE_PATH: "d8599a46ee26dc35a3ae52c1a98a416509add9ae4a42ece780c5c5ed7e132b93",
    SQLITE_FACADE_PATH: "882c008918b420414fb304c753552ba671bcb15b8c36ec3a9b4bb97a7b20eb14",
}
EXPECTED_SUPPORT_AST = {
    ("postgres_columns", "PROVENANCE_COLUMNS"): "99ad398896f00166f16ae70b6dd2713c5c3bd2d2d69a73c1b136b8f62acaf4a1",
    ("postgres_columns", "ARTIFACT_COLUMNS"): "c7081c47454a9100e144e997d0414d18dd7369a7e74673fb1c34a0cffd2e2e69",
    ("sqlite_columns", "PROVENANCE_COLUMNS"): "118bb257fd5165ad20c38794c9c4c444b09e2e3bf5df4b6a11dc8131ae337c77",
    ("postgres_primitives", "_sorted_field_names"): (
        "dfa6aeb9b7b9cb95ded740f952520dc52cd1ea1ec239ebcceacde00f0bf855cb"
    ),
    ("sqlite_primitives", "_sorted_field_names"): (
        "dfa6aeb9b7b9cb95ded740f952520dc52cd1ea1ec239ebcceacde00f0bf855cb"
    ),
}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _class_node(path: Path, name: str) -> ast.ClassDef:
    matches = [node for node in _tree(path).body if isinstance(node, ast.ClassDef) and node.name == name]
    assert len(matches) == 1
    return matches[0]


def _class_members(node: ast.ClassDef) -> list[str]:
    result: list[str] = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append(child.name)
        elif isinstance(child, ast.Assign):
            result.extend(target.id for target in child.targets if isinstance(target, ast.Name))
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            result.append(child.target.id)
    return result


def _assignment_map(node: ast.ClassDef) -> dict[str, str]:
    return {
        child.targets[0].id: child.value.id
        for child in node.body
        if isinstance(child, ast.Assign)
        and len(child.targets) == 1
        and isinstance(child.targets[0], ast.Name)
        and isinstance(child.value, ast.Name)
    }


def _method_nodes(path: Path) -> list[ast.FunctionDef]:
    return [node for node in _tree(path).body if isinstance(node, ast.FunctionDef) and node.name in POSTGRES_METHODS]


def _method_ast_manifest(path: Path) -> str:
    return _digest("\n".join(ast.dump(node, include_attributes=False) for node in _method_nodes(path)))


def _metadata_manifest(module: object, path: Path) -> str:
    rows: list[tuple[object, ...]] = []
    for node in _method_nodes(path):
        method = getattr(module, node.name)
        wrapped = getattr(method, "__wrapped__", None)
        rows.append(
            (
                node.name,
                str(inspect.signature(method)),
                method.__doc__,
                method.__module__,
                method.__qualname__,
                getattr(wrapped, "__module__", None),
                getattr(wrapped, "__qualname__", None),
            )
        )
    return _digest(repr(rows))


def _named_node(path: Path, name: str) -> ast.AST:
    matches: list[ast.AST] = []
    for node in _tree(path).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            matches.append(node)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            matches.append(node)
    assert len(matches) == 1
    return matches[0]


def _assert_source_receipts(texts: dict[Path, str]) -> None:
    assert set(texts) == set(SOURCE_RECEIPTS)
    for path, expected in SOURCE_RECEIPTS.items():
        assert _digest(texts[path]) == expected, path


def _lifecycle_comment_digest(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    start = source.index("    create_memory = _lifecycle_create_memory")
    end = source.index(
        "    list_provenance_links_for_targets = _lifecycle_list_provenance_links_for_targets"
    )
    end = source.index("\n", end)
    comments = "\n".join(
        line for line in source[start:end].splitlines() if line.lstrip().startswith("#")
    )
    return _digest(comments)


def test_lifecycle_carriers_pin_all_code_sql_parameters_and_comments() -> None:
    texts = {path: path.read_text(encoding="utf-8") for path in SOURCE_RECEIPTS}
    _assert_source_receipts(texts)
    assert _method_ast_manifest(POSTGRES_CARRIER_PATH) == EXPECTED_METHOD_AST_MANIFESTS["postgres"]
    assert _method_ast_manifest(SQLITE_CARRIER_PATH) == EXPECTED_METHOD_AST_MANIFESTS["sqlite"]


def test_lifecycle_methods_are_direct_native_order_grafts_with_exact_metadata() -> None:
    specs = (
        (
            POSTGRES_FACADE_PATH,
            "PostgresVNextStore",
            POSTGRES_METHODS,
            postgres_store.PostgresVNextStore,
            postgres_lifecycle,
            "alicebot_api.vnext_store",
        ),
        (
            SQLITE_FACADE_PATH,
            "SQLiteVNextStore",
            SQLITE_METHODS,
            sqlite_store.SQLiteVNextStore,
            sqlite_lifecycle,
            "alicebot_api.sqlite_store",
        ),
    )
    for path, class_name, names, facade_class, carrier, module_name in specs:
        class_node = _class_node(path, class_name)
        assert {node.name for node in class_node.body if isinstance(node, ast.FunctionDef)}.isdisjoint(names)
        assignments = _assignment_map(class_node)
        assert [name for name in _class_members(class_node) if name in names] == list(names)
        assert {name: assignments.get(name) for name in names} == {
            name: f"_lifecycle_{name}" for name in names
        }
        members = _class_members(class_node)
        expected_count, expected_digest = EXPECTED_CLASS_ORDERS[class_name]
        assert len(members) == expected_count
        assert _digest("\n".join(members)) == expected_digest
        assert facade_class.__bases__ == (object,)
        assert facade_class.__mro__ == (facade_class, object)
        for name in names:
            assert getattr(facade_class, name) is getattr(carrier, name)
            method = getattr(facade_class, name)
            assert method.__module__ == module_name
            assert method.__qualname__ == f"{class_name}.{name}"

    assert _metadata_manifest(postgres_lifecycle, POSTGRES_CARRIER_PATH) == EXPECTED_METADATA_MANIFESTS["postgres"]
    assert _metadata_manifest(sqlite_lifecycle, SQLITE_CARRIER_PATH) == EXPECTED_METADATA_MANIFESTS["sqlite"]
    for facade_class in (postgres_store.PostgresVNextStore, sqlite_store.SQLiteVNextStore):
        method = facade_class._redaction_mode
        assert method.__wrapped__.__module__ == method.__module__
        assert method.__wrapped__.__qualname__ == method.__qualname__


def test_lifecycle_support_reexports_are_the_same_objects() -> None:
    for module in (postgres_store, sqlite_store):
        assert module.REDACTION_MARKER is common.REDACTION_MARKER
        assert module.REDACTED_JSON_VALUE is common.REDACTED_JSON_VALUE
        assert module.redacted_memory_metadata is common.redacted_memory_metadata
        assert module.is_redacted_memory is common.is_redacted_memory
        assert module.is_prior_redacted_memory_marker is common.is_prior_redacted_memory_marker
    assert postgres_store.is_redacted_project_update_artifact is common.is_redacted_project_update_artifact
    assert postgres_store._is_redacted_memory_shape is common._is_redacted_memory_shape
    assert postgres_store.REDACTED_MEMORY_METADATA_KEYS is common.REDACTED_MEMORY_METADATA_KEYS
    assert postgres_store.PRIOR_REDACTED_MEMORY_METADATA_KEYS is common.PRIOR_REDACTED_MEMORY_METADATA_KEYS
    assert (
        postgres_store.PROJECT_UPDATE_REDACTED_METADATA_KEYS
        is common.PROJECT_UPDATE_REDACTED_METADATA_KEYS
    )
    assert postgres_store.PROVENANCE_COLUMNS is postgres_columns.PROVENANCE_COLUMNS
    assert postgres_store.ARTIFACT_COLUMNS is postgres_columns.ARTIFACT_COLUMNS
    assert sqlite_store.PROVENANCE_COLUMNS is sqlite_columns.PROVENANCE_COLUMNS
    assert postgres_store._sorted_field_names is postgres_primitives._sorted_field_names
    assert sqlite_store._sorted_field_names is sqlite_primitives._sorted_field_names
    for facade_helper, carrier_helper, module_name in (
        (
            postgres_store._sorted_field_names,
            postgres_primitives._sorted_field_names,
            "alicebot_api.vnext_store",
        ),
        (
            sqlite_store._sorted_field_names,
            sqlite_primitives._sorted_field_names,
            "alicebot_api.sqlite_store",
        ),
    ):
        assert facade_helper is carrier_helper
        assert str(inspect.signature(carrier_helper)) == "(record: 'JsonObject') -> 'list[str]'"
        assert carrier_helper.__doc__ is None
        assert carrier_helper.__module__ == module_name
        assert carrier_helper.__qualname__ == "_sorted_field_names"
    assert sqlite_store.__all__ == [
        "REDACTION_MARKER",
        "SQLiteVNextStore",
        "ensure_sqlite_user",
        "sqlite_user_connection",
    ]


def test_lifecycle_support_nodes_and_file_caps_are_pinned() -> None:
    paths = {
        "postgres_columns": REPO_ROOT / "apps/api/src/alicebot_api/vnext_stores/postgres/columns.py",
        "sqlite_columns": REPO_ROOT / "apps/api/src/alicebot_api/vnext_stores/sqlite/columns.py",
        "postgres_primitives": REPO_ROOT / "apps/api/src/alicebot_api/vnext_stores/postgres/primitives.py",
        "sqlite_primitives": REPO_ROOT / "apps/api/src/alicebot_api/vnext_stores/sqlite/primitives.py",
    }
    for (module_name, symbol), expected in EXPECTED_SUPPORT_AST.items():
        assert _digest(ast.dump(_named_node(paths[module_name], symbol), include_attributes=False)) == expected
    for path, expected in EXPECTED_FACADE_COMMENT_DIGESTS.items():
        assert _lifecycle_comment_digest(path) == expected
    assert len(POSTGRES_FACADE_PATH.read_text().splitlines()) <= 5100
    assert len(SQLITE_FACADE_PATH.read_text().splitlines()) <= 2700
    assert len(POSTGRES_CARRIER_PATH.read_text().splitlines()) < 4000
    assert len(SQLITE_CARRIER_PATH.read_text().splitlines()) < 4000


def test_lifecycle_carriers_import_standalone_without_facade_cycles() -> None:
    for path in (COMMON_PATH, POSTGRES_CARRIER_PATH, SQLITE_CARRIER_PATH):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        assert "alicebot_api.vnext_store" not in imports
        assert "alicebot_api.sqlite_store" not in imports

    code = """
import sys
from alicebot_api.vnext_stores.postgres import memory_lifecycle
from alicebot_api.vnext_stores.sqlite import memory_lifecycle as sqlite_lifecycle
assert 'alicebot_api.vnext_store' not in sys.modules
assert 'alicebot_api.sqlite_store' not in sys.modules
assert memory_lifecycle.create_memory
assert sqlite_lifecycle.create_memory
"""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("path", "old", "new"),
    (
        (POSTGRES_CARRIER_PATH, "FOR UPDATE", ""),
        (POSTGRES_CARRIER_PATH, "finally:", "if False:"),
        (POSTGRES_CARRIER_PATH, "SELECT pg_advisory_xact_lock", "SELECT 1 -- lock removed"),
        (SQLITE_CARRIER_PATH, "AND user_id = ?", ""),
        (SQLITE_CARRIER_PATH, "BEGIN IMMEDIATE", "BEGIN"),
        (SQLITE_CARRIER_PATH, "finally:", "if False:"),
        (COMMON_PATH, 'REDACTION_MARKER = "[REDACTED]"', 'REDACTION_MARKER = ""'),
    ),
)
def test_lifecycle_receipts_fail_on_old_or_weakened_sources(path: Path, old: str, new: str) -> None:
    texts = {candidate: candidate.read_text(encoding="utf-8") for candidate in SOURCE_RECEIPTS}
    assert old in texts[path]
    texts[path] = texts[path].replace(old, new, 1)
    with pytest.raises(AssertionError):
        _assert_source_receipts(texts)

from __future__ import annotations

import importlib
import sqlite3

import pytest

from alicebot_api import sqlite_schema
from alicebot_api.vnext_memory_commit import VNEXT_DOMAINS, VNEXT_SENSITIVITY_LEVELS


def test_pg_sqlite_and_runtime_classification_vocabularies_are_identical_and_canonical() -> None:
    pg_schema = importlib.import_module(
        "apps.api.alembic.versions.20260510_0067_vnext_memory_kernel_schema"
    )

    assert pg_schema.DOMAINS == sqlite_schema.DOMAINS == VNEXT_DOMAINS
    assert (
        pg_schema.SENSITIVITY_LEVELS
        == sqlite_schema.SENSITIVITY_LEVELS
        == VNEXT_SENSITIVITY_LEVELS
    )
    for vocabulary in (VNEXT_DOMAINS, VNEXT_SENSITIVITY_LEVELS):
        assert len(vocabulary) == len(set(vocabulary))
        assert all(value for value in vocabulary)
        assert all(value.isascii() for value in vocabulary)
        assert all(value == value.strip() for value in vocabulary)
        assert all(value == value.casefold() for value in vocabulary)


@pytest.mark.parametrize(
    ("column", "invalid_value", "constraint_name"),
    (
        ("domain", "", "sources_domain_check"),
        ("domain", " ", "sources_domain_check"),
        ("domain", "\u00a0", "sources_domain_check"),
        ("domain", "prøject", "sources_domain_check"),
        ("sensitivity", "", "sources_sensitivity_check"),
        ("sensitivity", " ", "sources_sensitivity_check"),
        ("sensitivity", "\u0085", "sources_sensitivity_check"),
        ("sensitivity", "prívate", "sources_sensitivity_check"),
    ),
)
def test_sqlite_source_constraints_reject_noncanonical_classifications(
    column: str,
    invalid_value: str,
    constraint_name: str,
) -> None:
    conn = sqlite3.connect(":memory:")
    sqlite_schema.bootstrap_sqlite_schema(conn)
    user_id = "00000000-0000-0000-0000-000000000401"
    conn.execute(
        "INSERT INTO users (id, email) VALUES (?, 'classification-sqlite@example.com')",
        (user_id,),
    )
    conn.commit()
    domain = invalid_value if column == "domain" else "project"
    sensitivity = invalid_value if column == "sensitivity" else "private"

    with pytest.raises(sqlite3.IntegrityError, match=constraint_name):
        conn.execute(
            """
            INSERT INTO sources (
              id, user_id, source_type, content_hash, domain, sensitivity
            ) VALUES (?, ?, 'manual_text', 'sha256:classification', ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000402",
                user_id,
                domain,
                sensitivity,
            ),
        )

    assert conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0

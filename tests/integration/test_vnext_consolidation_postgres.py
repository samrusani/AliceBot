"""Regression: consolidation's artifact write against a real migrated store.

The memory_consolidation artifact type was missing from
``generated_artifacts_type_check`` until migration 20260706_0080 — unit
tests use fakes and the SQLite on-ramp has no generated_artifacts table,
so only a live-Postgres run of the real service catches vocabulary drift
between the code and the CHECK constraints.
"""

from __future__ import annotations

from uuid import uuid4

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_consolidation import VNextConsolidationService
from alicebot_api.vnext_embeddings import pad_embedding_vector
from alicebot_api.vnext_store import PostgresVNextStore


def test_generate_memory_consolidation_persists_its_artifact(migrated_database_urls) -> None:
    user_id = uuid4()
    with user_connection(migrated_database_urls["app"], user_id) as conn:
        ContinuityStore(conn).create_user(user_id, "consolidation@example.invalid", "Consolidation")
        store = PostgresVNextStore(conn)
        for index in range(3):
            memory = store.create_memory(
                {
                    "memory_key": f"consolidation-regression-{index}",
                    "memory_type": "semantic",
                    "title": f"Launch window fact {index}",
                    "canonical_text": "The launch window moves to March after the review.",
                    "status": "active",
                    "value": {"text": "The launch window moves to March after the review."},
                }
            )
            store.update_memory_embedding(
                memory_id=str(memory["id"]),
                vector=pad_embedding_vector([0.5, 0.1, 0.2]),
            )

        artifact = VNextConsolidationService(store).generate_memory_consolidation()

        assert artifact.get("artifact_type") == "memory_consolidation"
        assert artifact.get("status") == "needs_review"
        stored = store.get_artifact(str(artifact["id"]))
        assert stored is not None
        assert stored["artifact_type"] == "memory_consolidation"

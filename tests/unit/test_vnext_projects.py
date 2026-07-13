from __future__ import annotations

import pytest

from alicebot_api.vnext_projects import ProjectAutomationRequest, VNextProjectService, VNextProjectValidationError


class InMemoryVNextProjectStore:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, object]] = {}
        self.sources: list[dict[str, object]] = []
        self.memories: dict[str, dict[str, object]] = {}
        self.open_loops: dict[str, dict[str, object]] = {}
        self.artifacts: dict[str, dict[str, object]] = {}
        self.revisions: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []
        self.cleared_embedding_ids: list[str] = []
        self.fact_key_updates: list[tuple[str, str | None]] = []
        self.artifact_lock_calls: list[str] = []

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def create_artifact(self, artifact: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**artifact, "id": f"artifact-{len(self.artifacts) + 1}"}
        self.artifacts[str(row["id"])] = row
        return row

    def get_artifact(self, artifact_id: str) -> dict[str, object] | None:
        return self.artifacts.get(artifact_id)

    def get_artifact_for_update(self, artifact_id: str) -> dict[str, object] | None:
        self.artifact_lock_calls.append(artifact_id)
        return self.artifacts.get(artifact_id)

    def update_artifact_status(
        self,
        *,
        artifact_id: str,
        status: str,
        expected_status: str | None = None,
        metadata_json: dict[str, object] | None = None,
        **_kwargs,
    ) -> dict[str, object] | None:
        artifact = self.artifacts[artifact_id]
        if expected_status is not None and artifact.get("status") != expected_status:
            return None
        artifact["status"] = status
        if metadata_json is not None:
            metadata = artifact.setdefault("metadata_json", {})
            assert isinstance(metadata, dict)
            metadata.update(metadata_json)
        return artifact

    def create_memory(self, memory: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**memory, "id": f"memory-{len(self.memories) + 1}"}
        self.memories[str(row["id"])] = row
        return row

    def update_memory(self, *, memory_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        memory = self.memories[memory_id]
        memory.update(patch)
        return memory

    def get_memory_for_update(self, memory_id: str) -> dict[str, object] | None:
        return self.memories.get(memory_id)

    def clear_memory_embedding(self, *, memory_id: str) -> dict[str, object] | None:
        memory = self.memories.get(memory_id)
        if memory is None:
            return None
        self.cleared_embedding_ids.append(memory_id)
        memory["embedding"] = None
        metadata = memory.get("metadata_json")
        if isinstance(metadata, dict):
            metadata.pop("_alice_embedding", None)
        return memory

    def update_memory_fact_keys(
        self,
        *,
        memory_id: str,
        fact_keys: str | None,
    ) -> dict[str, object] | None:
        memory = self.memories.get(memory_id)
        if memory is None:
            return None
        self.fact_key_updates.append((memory_id, fact_keys))
        memory["fact_keys"] = fact_keys
        return memory

    def append_revision(self, revision: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**revision, "id": f"revision-{len(self.revisions) + 1}"}
        self.revisions.append(row)
        return row

    def get_project(self, project_id: str) -> dict[str, object] | None:
        return self.projects.get(project_id)

    def get_project_for_update(self, project_id: str) -> dict[str, object] | None:
        return self.projects.get(project_id)

    def list_projects(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        rows = [row for row in self.projects.values() if status is None or row.get("status") == status]
        return _filter_rows(rows, domains=domains, sensitivity_allowed=sensitivity_allowed)[:limit]

    def update_project(self, *, project_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        project = self.projects[project_id]
        project.update(patch)
        return project

    def create_open_loop(self, loop: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**loop, "id": f"loop-{len(self.open_loops) + 1}", "status": loop.get("status", "open")}
        self.open_loops[str(row["id"])] = row
        return row

    def get_open_loop(self, loop_id: str) -> dict[str, object] | None:
        return self.open_loops.get(loop_id)

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        project_id: str | None = None,
        person_id: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        rows = [
            row
            for row in self.open_loops.values()
            if (status is None or row.get("status") == status)
            and (project_id is None or row.get("project_id") == project_id)
            and (person_id is None or row.get("person_id") == person_id)
        ]
        return _filter_rows(rows, domains=domains, sensitivity_allowed=sensitivity_allowed)[:limit]

    def update_open_loop(self, *, loop_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        loop = self.open_loops[loop_id]
        loop.update(patch)
        return loop

    def update_open_loop_status(
        self,
        *,
        loop_id: str,
        status: str,
        resolution_note: str | None = None,
        **_kwargs,
    ) -> dict[str, object]:
        loop = self.open_loops[loop_id]
        loop["status"] = status
        if resolution_note is not None:
            loop["resolution_note"] = resolution_note
        return loop

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
        scope_projects: tuple[str, ...] = (),
    ) -> list[dict[str, object]]:
        del query
        rows = _filter_rows(self.sources, domains=domains, sensitivity_allowed=sensitivity_allowed)
        if scope_projects:
            rows = [
                row
                for row in rows
                if set(row.get("metadata_json", {}).get("project_scope", [])) & set(scope_projects)  # type: ignore[union-attr]
            ]
        return rows[:limit]

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
        projects: tuple[str, ...] = (),
    ) -> list[dict[str, object]]:
        del query
        rows = _filter_rows(list(self.memories.values()), domains=domains, sensitivity_allowed=sensitivity_allowed)
        if projects:
            rows = [
                row
                for row in rows
                if set(row.get("metadata_json", {}).get("project_scope", [])) & set(projects)  # type: ignore[union-attr]
            ]
        return rows[:limit]

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
        scope_projects: tuple[str, ...] = (),
    ) -> list[dict[str, object]]:
        rows = [
            row for row in self.artifacts.values() if artifact_type is None or row.get("artifact_type") == artifact_type
        ]
        rows = _filter_rows(rows, domains=domains, sensitivity_allowed=sensitivity_allowed)
        if scope_projects:
            rows = [
                row
                for row in rows
                if set(row.get("metadata_json", {}).get("project_scope", [])) & set(scope_projects)  # type: ignore[union-attr]
            ]
        return rows[:limit]

    def find_artifact_by_workflow_digest(
        self,
        *,
        artifact_type: str,
        workflow: str,
        digest: str,
        scope_projects: tuple[str, ...] | None = None,
    ) -> dict[str, object] | None:
        for row in self.artifacts.values():
            metadata = row.get("metadata_json")
            if row.get("artifact_type") != artifact_type or not isinstance(metadata, dict):
                continue
            if metadata.get("workflow") != workflow:
                continue
            if metadata.get("automation_digest") != digest and metadata.get("consolidation_digest") != digest:
                continue
            if scope_projects and not set(metadata.get("project_scope", [])) & set(scope_projects):
                continue
            return row
        return None

    def find_open_loop_by_automation_digest(
        self,
        *,
        digest: str,
        project_id: str | None = None,
        person_id: str | None = None,
    ) -> dict[str, object] | None:
        for row in self.open_loops.values():
            metadata = row.get("metadata_json")
            if not isinstance(metadata, dict) or metadata.get("automation_digest") != digest:
                continue
            if project_id is not None and row.get("project_id") != project_id:
                continue
            if person_id is not None and row.get("person_id") != person_id:
                continue
            return row
        return None


def _filter_rows(
    rows: list[dict[str, object]],
    *,
    domains: list[str] | None,
    sensitivity_allowed: list[str] | None,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in rows:
        domain = row.get("domain")
        sensitivity = row.get("sensitivity")
        if domains is not None and isinstance(domain, str) and domain not in domains and domain != "unknown":
            continue
        if sensitivity_allowed is not None and isinstance(sensitivity, str) and sensitivity not in sensitivity_allowed:
            continue
        output.append(row)
    return output


def _seed_store() -> InMemoryVNextProjectStore:
    store = InMemoryVNextProjectStore()
    store.projects["project-1"] = {
        "id": "project-1",
        "name": "Alice vNext",
        "slug": "alice-vnext",
        "status": "active",
        "current_state": "Sprint 7 seed complete.",
        "domain": "project",
        "sensitivity": "private",
    }
    store.sources.append(
        {
            "id": "source-1",
            "source_type": "manual_text",
            "title": "Alice project note",
            "content_hash": "sha256:abc",
            "captured_at": "2026-05-10T09:00:00Z",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {
                "project_scope": ["project-1"],
                "raw_text": (
                    "Project: Alice vNext now needs project auto-update review.\n"
                    "TODO: validate project dashboard Owner: Samir\n"
                    "Waiting on: UI decision Owner: Designer"
                ),
            },
        }
    )
    store.memories["memory-existing"] = {
        "id": "memory-existing",
        "memory_type": "project_state",
        "canonical_text": "Alice vNext has project automation scope.",
        "status": "active",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"project_scope": ["project-1"]},
    }
    return store


def test_project_update_candidate_creates_reviewable_artifact_and_candidate_memory() -> None:
    store = _seed_store()

    artifact = VNextProjectService(store).generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",))
    )

    assert artifact["artifact_type"] == "project_update"
    assert artifact["status"] == "needs_review"
    assert artifact["metadata_json"]["project_id"] == "project-1"
    assert artifact["metadata_json"]["candidate_memory_id"] == "memory-2"
    assert "Project Update Candidate - Alice vNext" in artifact["content_markdown"]
    assert store.memories["memory-2"]["status"] == "candidate"
    assert store.events[-1]["event_type"] == "project.update_candidate_created"


def test_project_update_candidate_model_backed_mode_is_review_only_and_source_grounded() -> None:
    store = _seed_store()

    artifact = VNextProjectService(store).generate_project_update_candidate(
        ProjectAutomationRequest(
            project_id="project-1",
            domains=("project",),
            generation_mode="model_backed",
            model_route_mode="local_only",
        )
    )

    assert artifact["status"] == "needs_review"
    assert store.memories["memory-2"]["status"] == "candidate"
    assert artifact["metadata_json"]["workflow_type"] == "project_update_scan"
    assert artifact["metadata_json"]["generation_mode"] == "model_backed"
    assert artifact["model_info_json"]["provider"] == "deterministic_local"
    assert artifact["prompt_hash"].startswith("sha256:")
    assert "## Facts" in artifact["content_markdown"]
    assert "## Open Questions" in artifact["content_markdown"]
    assert "source:source-1" in artifact["content_markdown"]


def test_project_automation_and_dashboard_never_mix_same_domain_projects() -> None:
    store = _seed_store()
    store.projects["project-2"] = {
        **store.projects["project-1"],
        "id": "project-2",
        "name": "Hermes",
        "slug": "hermes",
    }
    store.sources.append(
        {
            "id": "source-project-2",
            "title": "Hermes private plan",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {
                "project_scope": ["project-2"],
                "raw_text": "Project: Hermes secret launch date.",
            },
        }
    )
    store.memories["memory-project-2"] = {
        "id": "memory-project-2",
        "memory_type": "project_state",
        "canonical_text": "Hermes secret launch date.",
        "status": "active",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"project_scope": ["project-2"]},
    }
    store.artifacts["artifact-project-2"] = {
        "id": "artifact-project-2",
        "artifact_type": "project_update",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"project_scope": ["project-2"]},
    }

    artifact = VNextProjectService(store).generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",))
    )
    dashboard = VNextProjectService(store).project_dashboard(project_id="project-1")

    assert "source-project-2" not in artifact["metadata_json"]["source_ids"]
    assert "memory-project-2" not in artifact["metadata_json"]["memory_ids"]
    assert all(row["id"] != "memory-project-2" for row in dashboard["memories"])
    assert all(row["id"] != "artifact-project-2" for row in dashboard["artifacts"])


def test_direct_project_workflows_are_idempotent_for_unchanged_evidence() -> None:
    store = _seed_store()
    service = VNextProjectService(store)
    request = ProjectAutomationRequest(project_id="project-1", domains=("project",))

    first_artifact = service.generate_project_update_candidate(request)
    first_loops = service.extract_open_loops(request)
    for index in range(150):
        store.artifacts[f"decoy-artifact-{index}"] = {
            "id": f"decoy-artifact-{index}",
            "artifact_type": "project_update",
            "metadata_json": {
                "workflow": "project_auto_update",
                "project_scope": ["project-1"],
                "automation_digest": f"decoy-{index}",
            },
        }
        store.open_loops[f"decoy-loop-{index}"] = {
            "id": f"decoy-loop-{index}",
            "project_id": "project-1",
            "metadata_json": {"automation_digest": f"decoy-{index}"},
        }
    second_artifact = service.generate_project_update_candidate(request)
    second_loops = service.extract_open_loops(request)

    assert second_artifact["id"] == first_artifact["id"]
    assert len([row for row in store.artifacts.values() if row.get("id") == first_artifact["id"]]) == 1
    assert len([row for row in store.memories.values() if row.get("status") == "candidate"]) == 1
    assert [row["id"] for row in second_loops] == [row["id"] for row in first_loops]
    assert len([row for row in store.open_loops.values() if row.get("title")]) == 2


def test_project_update_digest_changes_when_behavior_config_changes() -> None:
    store = _seed_store()
    service = VNextProjectService(store)

    first = service.generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",), max_items=8)
    )
    second = service.generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",), max_items=7)
    )

    assert second["id"] != first["id"]
    assert second["metadata_json"]["automation_digest"] != first["metadata_json"]["automation_digest"]


def test_accepting_project_update_updates_project_promotes_memory_and_appends_revision() -> None:
    store = _seed_store()
    service = VNextProjectService(store)
    artifact = service.generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",))
    )

    reviewed = service.review_project_update(
        artifact_id=str(artifact["id"]),
        action="edit",
        edited_current_state="Alice vNext project automation is under review.",
    )

    assert reviewed["status"] == "accepted"
    assert store.artifact_lock_calls == [str(artifact["id"])]
    assert store.projects["project-1"]["current_state"] == "Alice vNext project automation is under review."
    accepted_memory = store.memories["memory-2"]
    assert accepted_memory["status"] == "active"
    assert accepted_memory["canonical_text"] == "Alice vNext project automation is under review."
    assert accepted_memory["summary"] == "Alice vNext project automation is under review."
    assert accepted_memory["confirmation_status"] == "confirmed"
    assert accepted_memory["value"]["suggested_current_state"] == ("Alice vNext project automation is under review.")
    assert accepted_memory["metadata_json"]["candidate"] is False
    assert accepted_memory["metadata_json"]["review_status"] == "accepted"
    assert reviewed["metadata_json"]["accepted_current_state"] == ("Alice vNext project automation is under review.")
    assert store.revisions[0]["memory_id"] == "memory-2"
    assert store.revisions[0]["memory_key"] == store.memories["memory-2"]["memory_key"]
    assert store.revisions[0]["revision_type"] == "edited"
    assert store.events[-1]["event_type"] == "project.update_candidate_accepted"


def test_project_update_review_refreshes_content_derived_indexes() -> None:
    store = _seed_store()
    service = VNextProjectService(store)
    artifact = service.generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",))
    )
    memory_id = str(artifact["metadata_json"]["candidate_memory_id"])
    memory = store.memories[memory_id]
    memory["embedding"] = [0.1, 0.2]
    metadata = memory.setdefault("metadata_json", {})
    assert isinstance(metadata, dict)
    metadata["_alice_embedding"] = {"content_sha256": "stale"}

    service.review_project_update(
        artifact_id=str(artifact["id"]),
        action="edit",
        edited_current_state="Alice Bike-a-Thon raised $5,000 for the release fundraiser.",
    )

    assert store.cleared_embedding_ids == [memory_id]
    assert memory["embedding"] is None
    refreshed_metadata = memory["metadata_json"]
    assert isinstance(refreshed_metadata, dict)
    assert "_alice_embedding" not in refreshed_metadata
    assert store.fact_key_updates[-1][0] == memory_id
    assert "dollars" in str(memory["fact_keys"])


def test_project_update_review_can_defer_embedding_until_after_commit() -> None:
    store = _seed_store()
    service = VNextProjectService(store, defer_embeddings=True)
    artifact = service.generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",))
    )

    service.review_project_update(
        artifact_id=str(artifact["id"]),
        action="edit",
        edited_current_state="Deferred project-state embedding.",
    )

    assert len(service.deferred_embedding_inputs) == 1
    deferred = service.deferred_embedding_inputs[0]
    assert deferred.memory_id == artifact["metadata_json"]["candidate_memory_id"]
    assert deferred.canonical_text == "Deferred project-state embedding."


def test_rejecting_project_update_logs_rejection_without_updating_project() -> None:
    store = _seed_store()
    service = VNextProjectService(store)
    artifact = service.generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",))
    )

    reviewed = service.review_project_update(artifact_id=str(artifact["id"]), action="reject")

    assert reviewed["status"] == "rejected"
    assert store.projects["project-1"]["current_state"] == "Sprint 7 seed complete."
    assert store.memories["memory-2"]["status"] == "rejected"
    assert store.revisions[-1]["revision_type"] == "rejected"
    assert store.events[-1]["event_type"] == "project.update_candidate_rejected"

    assert service.review_project_update(artifact_id=str(artifact["id"]), action="reject") == reviewed
    with pytest.raises(VNextProjectValidationError, match="cannot be accepted"):
        service.review_project_update(artifact_id=str(artifact["id"]), action="accept")


def test_accepted_project_update_cannot_later_be_rejected() -> None:
    store = _seed_store()
    service = VNextProjectService(store)
    artifact = service.generate_project_update_candidate(
        ProjectAutomationRequest(project_id="project-1", domains=("project",))
    )

    accepted = service.review_project_update(artifact_id=str(artifact["id"]), action="accept")

    assert service.review_project_update(artifact_id=str(artifact["id"]), action="accept") == accepted
    with pytest.raises(VNextProjectValidationError, match="cannot be rejected"):
        service.review_project_update(artifact_id=str(artifact["id"]), action="reject")


def test_open_loop_extraction_and_review_support_source_owner_and_filters() -> None:
    store = _seed_store()
    service = VNextProjectService(store)

    loops = service.extract_open_loops(ProjectAutomationRequest(project_id="project-1", domains=("project",)))
    snoozed = service.review_open_loop(loop_id="loop-1", action="snooze", due_at="2026-05-12T09:00:00Z")
    closed = service.review_open_loop(loop_id="loop-2", action="close", resolution_note="Decision captured.")
    dashboard = service.project_dashboard(project_id="project-1")

    assert [loop["metadata_json"]["loop_type"] for loop in loops] == ["task", "waiting_on_person"]
    assert loops[0]["source_id"] == "source-1"
    assert loops[0]["metadata_json"]["source_captured_at"] == "2026-05-10T09:00:00Z"
    assert loops[0]["metadata_json"]["owner"] == "Samir"
    assert snoozed["due_at"] == "2026-05-12T09:00:00Z"
    assert closed["status"] == "resolved"
    assert dashboard["project"]["id"] == "project-1"
    assert dashboard["counts"]["open_loops"] == 1


def test_project_service_validation_errors() -> None:
    service = VNextProjectService(InMemoryVNextProjectStore())

    with pytest.raises(VNextProjectValidationError, match="max_items"):
        service.extract_open_loops(ProjectAutomationRequest(max_items=0))

    with pytest.raises(VNextProjectValidationError, match="no active project"):
        service.generate_project_update_candidate(ProjectAutomationRequest())

    store = _seed_store()
    service = VNextProjectService(store)
    artifact = service.generate_project_update_candidate(ProjectAutomationRequest(project_id="project-1"))
    with pytest.raises(VNextProjectValidationError, match="edited_current_state"):
        service.review_project_update(artifact_id=str(artifact["id"]), action="edit")

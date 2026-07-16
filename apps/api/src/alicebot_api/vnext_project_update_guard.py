from __future__ import annotations

from collections.abc import Mapping


PROJECT_UPDATE_WORKFLOW = "project_auto_update"
PROJECT_UPDATE_MEMORY_KEY_PREFIX = "project_update."
PENDING_PROJECT_UPDATE_MEMORY_MUTATION_MESSAGE = (
    "pending project update candidates must be reviewed through the project update workflow"
)


def is_project_update_artifact(artifact: Mapping[str, object]) -> bool:
    """Return whether an artifact belongs to the coupled project-update workflow.

    Classification intentionally accepts either the artifact type or workflow
    marker. A malformed coupled artifact must still route to the strict
    project-update validator and fail closed; requiring every linkage field
    here would let incomplete rows fall through to generic artifact review.
    """

    metadata = artifact.get("metadata_json")
    return artifact.get("artifact_type") == "project_update" or (
        isinstance(metadata, Mapping) and metadata.get("workflow") == PROJECT_UPDATE_WORKFLOW
    )


def is_project_update_memory(memory: Mapping[str, object]) -> bool:
    """Return whether a memory belongs to the coupled project-update workflow.

    Older or partially-corrupted candidates may have lost their workflow
    metadata while retaining the reserved project-update memory-key prefix.
    Treat either marker as authoritative so generic memory mutation paths fail
    closed instead of stranding the linked review artifact.
    """

    metadata = memory.get("metadata_json")
    memory_key = memory.get("memory_key")
    return (isinstance(metadata, Mapping) and metadata.get("workflow") == PROJECT_UPDATE_WORKFLOW) or (
        isinstance(memory_key, str) and memory_key.strip().startswith(PROJECT_UPDATE_MEMORY_KEY_PREFIX)
    )


def is_pending_project_update_memory(memory: Mapping[str, object]) -> bool:
    """Return whether a coupled project-update memory still awaits review.

    The project-update decision path writes ``candidate=False`` atomically
    with its terminal outcome. Any coupled row without that exact marker is
    conservatively pending, including legacy rows and malformed metadata.
    """

    if not is_project_update_memory(memory):
        return False
    metadata = memory.get("metadata_json")
    return not (isinstance(metadata, Mapping) and metadata.get("candidate") is False)


__all__ = [
    "PENDING_PROJECT_UPDATE_MEMORY_MUTATION_MESSAGE",
    "PROJECT_UPDATE_MEMORY_KEY_PREFIX",
    "PROJECT_UPDATE_WORKFLOW",
    "is_pending_project_update_memory",
    "is_project_update_artifact",
    "is_project_update_memory",
]

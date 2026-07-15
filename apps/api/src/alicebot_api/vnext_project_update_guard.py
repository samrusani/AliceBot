from __future__ import annotations

from collections.abc import Mapping


PROJECT_UPDATE_WORKFLOW = "project_auto_update"


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


__all__ = ["PROJECT_UPDATE_WORKFLOW", "is_project_update_artifact"]

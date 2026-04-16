from __future__ import annotations

from datetime import datetime
import re
from typing import Any, TypedDict
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


SLUG_SANITIZE_PATTERN = re.compile(r"[^a-z0-9-]+")
SLUG_COLLAPSE_PATTERN = re.compile(r"-+")

DEFAULT_ONBOARDING_CHECKLIST: dict[str, bool] = {
    "kickoff_complete": False,
    "workspace_linked": False,
    "instrumentation_ready": False,
    "success_criteria_confirmed": False,
    "support_channel_confirmed": False,
}
DEFAULT_SUPPORT_CHECKLIST: dict[str, bool] = {
    "owner_assigned": False,
    "weekly_review_scheduled": False,
    "feedback_loop_running": False,
    "escalation_path_confirmed": False,
}
CHECKLIST_LABELS = {
    "kickoff_complete": "Kickoff complete",
    "workspace_linked": "Workspace linked",
    "instrumentation_ready": "Instrumentation ready",
    "success_criteria_confirmed": "Success criteria confirmed",
    "support_channel_confirmed": "Support channel confirmed",
    "owner_assigned": "Owner assigned",
    "weekly_review_scheduled": "Weekly review scheduled",
    "feedback_loop_running": "Feedback loop running",
    "escalation_path_confirmed": "Escalation path confirmed",
}


class DesignPartnerNotFoundError(LookupError):
    """Raised when a design partner record cannot be found."""


class DesignPartnerWorkspaceConflictError(RuntimeError):
    """Raised when workspace linkage cannot be created or updated safely."""


class DesignPartnerFeedbackValidationError(ValueError):
    """Raised when feedback input does not align with partner linkage rules."""


class DesignPartnerRow(TypedDict):
    id: UUID
    partner_key: str
    name: str
    lifecycle_stage: str
    onboarding_status: str
    support_status: str
    instrumentation_status: str
    case_study_status: str
    target_outcome: str | None
    launch_notes: str | None
    onboarding_checklist: dict[str, object]
    support_checklist: dict[str, object]
    success_metrics: dict[str, object]
    created_by_user_account_id: UUID
    created_at: datetime
    updated_at: datetime


class DesignPartnerWorkspaceRow(TypedDict):
    id: UUID
    design_partner_id: UUID
    workspace_id: UUID
    linked_by_user_account_id: UUID
    linkage_status: str
    environment_label: str
    instrumentation_ready: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
    workspace_slug: str
    workspace_name: str
    workspace_bootstrap_status: str


class DesignPartnerFeedbackRow(TypedDict):
    id: UUID
    design_partner_id: UUID
    workspace_id: UUID | None
    captured_by_user_account_id: UUID
    source_kind: str
    category: str
    sentiment: str
    urgency: str
    feedback_status: str
    case_study_signal: bool
    summary: str
    detail: str | None
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime
    workspace_slug: str | None
    workspace_name: str | None


def slugify_partner_key(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "-")
    normalized = SLUG_SANITIZE_PATTERN.sub("-", normalized)
    normalized = SLUG_COLLAPSE_PATTERN.sub("-", normalized).strip("-")
    if normalized == "":
        return "design-partner"
    return normalized[:120]


def _normalize_checklist(
    default_items: dict[str, bool],
    raw_value: dict[str, object] | None,
) -> dict[str, bool]:
    normalized = dict(default_items)
    if raw_value is None:
        return normalized

    for key, value in raw_value.items():
        normalized[key] = bool(value)
    return normalized


def _checklist_items(checklist: dict[str, bool]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for key, completed in checklist.items():
        items.append(
            {
                "key": key,
                "label": CHECKLIST_LABELS.get(key, key.replace("_", " ").strip().title()),
                "completed": completed,
            }
        )
    return items


def _serialize_checklist(checklist: dict[str, bool]) -> dict[str, object]:
    completed_count = sum(1 for value in checklist.values() if value)
    return {
        "items": _checklist_items(checklist),
        "summary": {
            "total_count": len(checklist),
            "completed_count": completed_count,
            "remaining_count": max(0, len(checklist) - completed_count),
        },
    }


def _serialize_workspace_row(row: DesignPartnerWorkspaceRow) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "workspace_id": str(row["workspace_id"]),
        "workspace_slug": row["workspace_slug"],
        "workspace_name": row["workspace_name"],
        "workspace_bootstrap_status": row["workspace_bootstrap_status"],
        "linkage_status": row["linkage_status"],
        "environment_label": row["environment_label"],
        "instrumentation_ready": row["instrumentation_ready"],
        "notes": row["notes"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _serialize_feedback_row(row: DesignPartnerFeedbackRow) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "workspace_id": None if row["workspace_id"] is None else str(row["workspace_id"]),
        "workspace_slug": row["workspace_slug"],
        "workspace_name": row["workspace_name"],
        "captured_by_user_account_id": str(row["captured_by_user_account_id"]),
        "source_kind": row["source_kind"],
        "category": row["category"],
        "sentiment": row["sentiment"],
        "urgency": row["urgency"],
        "feedback_status": row["feedback_status"],
        "case_study_signal": row["case_study_signal"],
        "summary": row["summary"],
        "detail": row["detail"],
        "metadata": row["metadata"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _serialize_usage_summary(
    usage_row: dict[str, object] | None,
    *,
    linked_workspace_count: int,
) -> dict[str, object]:
    if usage_row is None:
        return {
            "linked_workspace_count": linked_workspace_count,
            "runtime_invocation_count": 0,
            "successful_invocation_count": 0,
            "failed_invocation_count": 0,
            "unique_invoker_count": 0,
            "last_invocation_at": None,
            "usage_visible": False,
        }

    last_invocation_at = usage_row["last_invocation_at"]
    runtime_invocation_count = int(usage_row["runtime_invocation_count"])
    return {
        "linked_workspace_count": linked_workspace_count,
        "runtime_invocation_count": runtime_invocation_count,
        "successful_invocation_count": int(usage_row["successful_invocation_count"]),
        "failed_invocation_count": int(usage_row["failed_invocation_count"]),
        "unique_invoker_count": int(usage_row["unique_invoker_count"]),
        "last_invocation_at": None if last_invocation_at is None else last_invocation_at.isoformat(),
        "usage_visible": runtime_invocation_count > 0,
    }


def _serialize_feedback_summary(
    feedback_rows: list[DesignPartnerFeedbackRow],
) -> dict[str, object]:
    open_statuses = {"new", "triaged"}
    last_feedback_at = feedback_rows[0]["created_at"] if feedback_rows else None
    return {
        "total_count": len(feedback_rows),
        "open_count": sum(1 for row in feedback_rows if row["feedback_status"] in open_statuses),
        "case_study_signal_count": sum(1 for row in feedback_rows if row["case_study_signal"]),
        "last_feedback_at": None if last_feedback_at is None else last_feedback_at.isoformat(),
    }


def _merge_operational_checklists(
    row: DesignPartnerRow,
    *,
    workspace_rows: list[DesignPartnerWorkspaceRow],
    feedback_rows: list[DesignPartnerFeedbackRow],
) -> tuple[dict[str, bool], dict[str, bool]]:
    onboarding = _normalize_checklist(DEFAULT_ONBOARDING_CHECKLIST, row["onboarding_checklist"])
    support = _normalize_checklist(DEFAULT_SUPPORT_CHECKLIST, row["support_checklist"])

    onboarding["workspace_linked"] = len(workspace_rows) > 0
    onboarding["instrumentation_ready"] = row["instrumentation_status"] == "ready" or any(
        workspace["instrumentation_ready"] for workspace in workspace_rows
    )
    support["feedback_loop_running"] = len(feedback_rows) > 0
    return onboarding, support


def _serialize_partner_row(
    row: DesignPartnerRow,
    *,
    workspace_rows: list[DesignPartnerWorkspaceRow],
    feedback_rows: list[DesignPartnerFeedbackRow],
    usage_row: dict[str, object] | None,
) -> dict[str, object]:
    onboarding_checklist, support_checklist = _merge_operational_checklists(
        row,
        workspace_rows=workspace_rows,
        feedback_rows=feedback_rows,
    )
    return {
        "id": str(row["id"]),
        "partner_key": row["partner_key"],
        "name": row["name"],
        "lifecycle_stage": row["lifecycle_stage"],
        "onboarding_status": row["onboarding_status"],
        "support_status": row["support_status"],
        "instrumentation_status": row["instrumentation_status"],
        "case_study_status": row["case_study_status"],
        "target_outcome": row["target_outcome"],
        "launch_notes": row["launch_notes"],
        "success_metrics": row["success_metrics"],
        "created_by_user_account_id": str(row["created_by_user_account_id"]),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "onboarding_checklist": _serialize_checklist(onboarding_checklist),
        "support_checklist": _serialize_checklist(support_checklist),
        "linked_workspaces": [_serialize_workspace_row(workspace) for workspace in workspace_rows],
        "feedback_summary": _serialize_feedback_summary(feedback_rows),
        "usage_summary": _serialize_usage_summary(usage_row, linked_workspace_count=len(workspace_rows)),
    }


def _fetch_design_partner_row(conn, *, design_partner_id: UUID) -> DesignPartnerRow | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,
                   partner_key,
                   name,
                   lifecycle_stage,
                   onboarding_status,
                   support_status,
                   instrumentation_status,
                   case_study_status,
                   target_outcome,
                   launch_notes,
                   onboarding_checklist,
                   support_checklist,
                   success_metrics,
                   created_by_user_account_id,
                   created_at,
                   updated_at
            FROM design_partners
            WHERE id = %s
            LIMIT 1
            """,
            (design_partner_id,),
        )
        return cur.fetchone()


def _fetch_workspace_rows(
    conn,
    *,
    design_partner_ids: list[UUID],
) -> dict[UUID, list[DesignPartnerWorkspaceRow]]:
    if len(design_partner_ids) == 0:
        return {}

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dpw.id,
                   dpw.design_partner_id,
                   dpw.workspace_id,
                   dpw.linked_by_user_account_id,
                   dpw.linkage_status,
                   dpw.environment_label,
                   dpw.instrumentation_ready,
                   dpw.notes,
                   dpw.created_at,
                   dpw.updated_at,
                   w.slug AS workspace_slug,
                   w.name AS workspace_name,
                   w.bootstrap_status AS workspace_bootstrap_status
            FROM design_partner_workspaces AS dpw
            JOIN workspaces AS w
              ON w.id = dpw.workspace_id
            WHERE dpw.design_partner_id = ANY(%s)
            ORDER BY dpw.created_at ASC, dpw.id ASC
            """,
            (design_partner_ids,),
        )
        rows = cur.fetchall()

    grouped: dict[UUID, list[DesignPartnerWorkspaceRow]] = {partner_id: [] for partner_id in design_partner_ids}
    for row in rows:
        grouped.setdefault(row["design_partner_id"], []).append(row)
    return grouped


def _fetch_feedback_rows(
    conn,
    *,
    design_partner_ids: list[UUID],
    per_partner_limit: int | None = None,
) -> dict[UUID, list[DesignPartnerFeedbackRow]]:
    if len(design_partner_ids) == 0:
        return {}

    if per_partner_limit is None:
        limit_sql = ""
        params: tuple[object, ...] = (design_partner_ids,)
    else:
        limit_sql = "WHERE ranked.row_number <= %s"
        params = (design_partner_ids, per_partner_limit)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            WITH ranked AS (
              SELECT dpf.id,
                     dpf.design_partner_id,
                     dpf.workspace_id,
                     dpf.captured_by_user_account_id,
                     dpf.source_kind,
                     dpf.category,
                     dpf.sentiment,
                     dpf.urgency,
                     dpf.feedback_status,
                     dpf.case_study_signal,
                     dpf.summary,
                     dpf.detail,
                     dpf.metadata,
                     dpf.created_at,
                     dpf.updated_at,
                     w.slug AS workspace_slug,
                     w.name AS workspace_name,
                     row_number() OVER (
                       PARTITION BY dpf.design_partner_id
                       ORDER BY dpf.created_at DESC, dpf.id DESC
                     ) AS row_number
              FROM design_partner_feedback AS dpf
              LEFT JOIN workspaces AS w
                ON w.id = dpf.workspace_id
              WHERE dpf.design_partner_id = ANY(%s)
            )
            SELECT id,
                   design_partner_id,
                   workspace_id,
                   captured_by_user_account_id,
                   source_kind,
                   category,
                   sentiment,
                   urgency,
                   feedback_status,
                   case_study_signal,
                   summary,
                   detail,
                   metadata,
                   created_at,
                   updated_at,
                   workspace_slug,
                   workspace_name
            FROM ranked
            {limit_sql}
            ORDER BY design_partner_id, created_at DESC, id DESC
            """,
            params,
        )
        rows = cur.fetchall()

    grouped: dict[UUID, list[DesignPartnerFeedbackRow]] = {partner_id: [] for partner_id in design_partner_ids}
    for row in rows:
        grouped.setdefault(row["design_partner_id"], []).append(row)
    return grouped


def _fetch_usage_rows(
    conn,
    *,
    design_partner_ids: list[UUID],
) -> dict[UUID, dict[str, object]]:
    if len(design_partner_ids) == 0:
        return {}

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dpw.design_partner_id,
                   count(*) FILTER (WHERE pit.invocation_kind = 'runtime_invoke') AS runtime_invocation_count,
                   count(*) FILTER (
                     WHERE pit.invocation_kind = 'runtime_invoke'
                       AND pit.status = 'succeeded'
                   ) AS successful_invocation_count,
                   count(*) FILTER (
                     WHERE pit.invocation_kind = 'runtime_invoke'
                       AND pit.status = 'failed'
                   ) AS failed_invocation_count,
                   count(DISTINCT pit.invoked_by_user_account_id) FILTER (
                     WHERE pit.invocation_kind = 'runtime_invoke'
                   ) AS unique_invoker_count,
                   max(pit.created_at) FILTER (WHERE pit.invocation_kind = 'runtime_invoke') AS last_invocation_at
            FROM design_partner_workspaces AS dpw
            LEFT JOIN provider_invocation_telemetry AS pit
              ON pit.workspace_id = dpw.workspace_id
            WHERE dpw.design_partner_id = ANY(%s)
            GROUP BY dpw.design_partner_id
            """,
            (design_partner_ids,),
        )
        rows = cur.fetchall()

    return {row["design_partner_id"]: row for row in rows}


def create_design_partner(
    conn,
    *,
    created_by_user_account_id: UUID,
    name: str,
    partner_key: str | None,
    lifecycle_stage: str,
    onboarding_status: str,
    support_status: str,
    instrumentation_status: str,
    case_study_status: str,
    target_outcome: str | None,
    launch_notes: str | None,
    onboarding_checklist: dict[str, object] | None,
    support_checklist: dict[str, object] | None,
    success_metrics: dict[str, object] | None,
) -> dict[str, object]:
    resolved_name = name.strip()
    if resolved_name == "":
        raise ValueError("design partner name is required")

    resolved_partner_key = slugify_partner_key(partner_key if partner_key is not None else resolved_name)
    normalized_onboarding = _normalize_checklist(DEFAULT_ONBOARDING_CHECKLIST, onboarding_checklist)
    normalized_support = _normalize_checklist(DEFAULT_SUPPORT_CHECKLIST, support_checklist)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO design_partners (
              partner_key,
              name,
              lifecycle_stage,
              onboarding_status,
              support_status,
              instrumentation_status,
              case_study_status,
              target_outcome,
              launch_notes,
              onboarding_checklist,
              support_checklist,
              success_metrics,
              created_by_user_account_id
            )
            VALUES (
              %s,
              %s,
              %s,
              %s,
              %s,
              %s,
              %s,
              %s,
              %s,
              %s,
              %s,
              %s,
              %s
            )
            RETURNING id,
                      partner_key,
                      name,
                      lifecycle_stage,
                      onboarding_status,
                      support_status,
                      instrumentation_status,
                      case_study_status,
                      target_outcome,
                      launch_notes,
                      onboarding_checklist,
                      support_checklist,
                      success_metrics,
                      created_by_user_account_id,
                      created_at,
                      updated_at
            """,
            (
                resolved_partner_key,
                resolved_name,
                lifecycle_stage,
                onboarding_status,
                support_status,
                instrumentation_status,
                case_study_status,
                target_outcome.strip() if isinstance(target_outcome, str) else target_outcome,
                launch_notes.strip() if isinstance(launch_notes, str) else launch_notes,
                Jsonb(normalized_onboarding),
                Jsonb(normalized_support),
                Jsonb(success_metrics or {}),
                created_by_user_account_id,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to create design partner")
    return {
        "design_partner": _serialize_partner_row(
            row,
            workspace_rows=[],
            feedback_rows=[],
            usage_row=None,
        )
    }


def update_design_partner(
    conn,
    *,
    design_partner_id: UUID,
    lifecycle_stage: str | None,
    onboarding_status: str | None,
    support_status: str | None,
    instrumentation_status: str | None,
    case_study_status: str | None,
    target_outcome: str | None,
    launch_notes: str | None,
    onboarding_checklist: dict[str, object] | None,
    support_checklist: dict[str, object] | None,
    success_metrics: dict[str, object] | None,
) -> dict[str, object]:
    row = _fetch_design_partner_row(conn, design_partner_id=design_partner_id)
    if row is None:
        raise DesignPartnerNotFoundError(f"design partner {design_partner_id} was not found")

    resolved_onboarding = _normalize_checklist(DEFAULT_ONBOARDING_CHECKLIST, row["onboarding_checklist"])
    resolved_support = _normalize_checklist(DEFAULT_SUPPORT_CHECKLIST, row["support_checklist"])
    if onboarding_checklist is not None:
        resolved_onboarding = _normalize_checklist(resolved_onboarding, onboarding_checklist)
    if support_checklist is not None:
        resolved_support = _normalize_checklist(resolved_support, support_checklist)

    resolved_success_metrics = dict(row["success_metrics"] or {})
    if success_metrics is not None:
        resolved_success_metrics = success_metrics

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE design_partners
            SET lifecycle_stage = %s,
                onboarding_status = %s,
                support_status = %s,
                instrumentation_status = %s,
                case_study_status = %s,
                target_outcome = %s,
                launch_notes = %s,
                onboarding_checklist = %s,
                support_checklist = %s,
                success_metrics = %s,
                updated_at = clock_timestamp()
            WHERE id = %s
            RETURNING id,
                      partner_key,
                      name,
                      lifecycle_stage,
                      onboarding_status,
                      support_status,
                      instrumentation_status,
                      case_study_status,
                      target_outcome,
                      launch_notes,
                      onboarding_checklist,
                      support_checklist,
                      success_metrics,
                      created_by_user_account_id,
                      created_at,
                      updated_at
            """,
            (
                lifecycle_stage or row["lifecycle_stage"],
                onboarding_status or row["onboarding_status"],
                support_status or row["support_status"],
                instrumentation_status or row["instrumentation_status"],
                case_study_status or row["case_study_status"],
                target_outcome if target_outcome is not None else row["target_outcome"],
                launch_notes if launch_notes is not None else row["launch_notes"],
                Jsonb(resolved_onboarding),
                Jsonb(resolved_support),
                Jsonb(resolved_success_metrics),
                design_partner_id,
            ),
        )
        updated_row = cur.fetchone()

    if updated_row is None:
        raise DesignPartnerNotFoundError(f"design partner {design_partner_id} was not found")

    workspace_rows = _fetch_workspace_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id, [])
    feedback_rows = _fetch_feedback_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id, [])
    usage_row = _fetch_usage_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id)
    return {
        "design_partner": _serialize_partner_row(
            updated_row,
            workspace_rows=workspace_rows,
            feedback_rows=feedback_rows,
            usage_row=usage_row,
        )
    }


def link_design_partner_workspace(
    conn,
    *,
    design_partner_id: UUID,
    workspace_id: UUID,
    linked_by_user_account_id: UUID,
    linkage_status: str,
    environment_label: str,
    instrumentation_ready: bool,
    notes: str | None,
) -> dict[str, object]:
    row = _fetch_design_partner_row(conn, design_partner_id=design_partner_id)
    if row is None:
        raise DesignPartnerNotFoundError(f"design partner {design_partner_id} was not found")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, design_partner_id
            FROM design_partner_workspaces
            WHERE workspace_id = %s
            LIMIT 1
            """,
            (workspace_id,),
        )
        existing = cur.fetchone()
        if existing is not None and existing["design_partner_id"] != design_partner_id:
            raise DesignPartnerWorkspaceConflictError(
                f"workspace {workspace_id} is already linked to design partner {existing['design_partner_id']}"
            )

        cur.execute(
            """
            INSERT INTO design_partner_workspaces (
              design_partner_id,
              workspace_id,
              linked_by_user_account_id,
              linkage_status,
              environment_label,
              instrumentation_ready,
              notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (design_partner_id, workspace_id) DO UPDATE
            SET linkage_status = EXCLUDED.linkage_status,
                environment_label = EXCLUDED.environment_label,
                instrumentation_ready = EXCLUDED.instrumentation_ready,
                notes = EXCLUDED.notes,
                updated_at = clock_timestamp()
            RETURNING id
            """,
            (
                design_partner_id,
                workspace_id,
                linked_by_user_account_id,
                linkage_status,
                environment_label.strip(),
                instrumentation_ready,
                notes.strip() if isinstance(notes, str) else notes,
            ),
        )
        if cur.fetchone() is None:
            raise RuntimeError("failed to link design partner workspace")

    workspace_rows = _fetch_workspace_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id, [])
    feedback_rows = _fetch_feedback_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id, [])
    usage_row = _fetch_usage_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id)
    return {
        "design_partner": _serialize_partner_row(
            row,
            workspace_rows=workspace_rows,
            feedback_rows=feedback_rows,
            usage_row=usage_row,
        )
    }


def record_design_partner_feedback(
    conn,
    *,
    design_partner_id: UUID,
    captured_by_user_account_id: UUID,
    workspace_id: UUID | None,
    source_kind: str,
    category: str,
    sentiment: str,
    urgency: str,
    feedback_status: str,
    case_study_signal: bool,
    summary: str,
    detail: str | None,
    metadata: dict[str, object] | None,
) -> dict[str, object]:
    partner = _fetch_design_partner_row(conn, design_partner_id=design_partner_id)
    if partner is None:
        raise DesignPartnerNotFoundError(f"design partner {design_partner_id} was not found")

    if workspace_id is not None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM design_partner_workspaces
                WHERE design_partner_id = %s
                  AND workspace_id = %s
                LIMIT 1
                """,
                (design_partner_id, workspace_id),
            )
            if cur.fetchone() is None:
                raise DesignPartnerFeedbackValidationError(
                    f"workspace {workspace_id} is not linked to design partner {design_partner_id}"
                )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO design_partner_feedback (
              design_partner_id,
              workspace_id,
              captured_by_user_account_id,
              source_kind,
              category,
              sentiment,
              urgency,
              feedback_status,
              case_study_signal,
              summary,
              detail,
              metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                design_partner_id,
                workspace_id,
                captured_by_user_account_id,
                source_kind,
                category,
                sentiment,
                urgency,
                feedback_status,
                case_study_signal,
                summary.strip(),
                detail.strip() if isinstance(detail, str) else detail,
                Jsonb(metadata or {}),
            ),
        )
        if cur.fetchone() is None:
            raise RuntimeError("failed to create design partner feedback")

    workspace_rows = _fetch_workspace_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id, [])
    feedback_rows = _fetch_feedback_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id, [])
    usage_row = _fetch_usage_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id)
    return {
        "design_partner": _serialize_partner_row(
            partner,
            workspace_rows=workspace_rows,
            feedback_rows=feedback_rows,
            usage_row=usage_row,
        ),
        "feedback": _serialize_feedback_row(feedback_rows[0]),
    }


def list_design_partners(
    conn,
    *,
    limit: int,
) -> dict[str, object]:
    bounded_limit = max(1, min(limit, 200))

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,
                   partner_key,
                   name,
                   lifecycle_stage,
                   onboarding_status,
                   support_status,
                   instrumentation_status,
                   case_study_status,
                   target_outcome,
                   launch_notes,
                   onboarding_checklist,
                   support_checklist,
                   success_metrics,
                   created_by_user_account_id,
                   created_at,
                   updated_at
            FROM design_partners
            ORDER BY updated_at DESC, id DESC
            LIMIT %s
            """,
            (bounded_limit,),
        )
        rows = cur.fetchall()

    partner_ids = [row["id"] for row in rows]
    workspace_rows = _fetch_workspace_rows(conn, design_partner_ids=partner_ids)
    feedback_rows = _fetch_feedback_rows(conn, design_partner_ids=partner_ids)
    usage_rows = _fetch_usage_rows(conn, design_partner_ids=partner_ids)

    items = [
        _serialize_partner_row(
            row,
            workspace_rows=workspace_rows.get(row["id"], []),
            feedback_rows=feedback_rows.get(row["id"], []),
            usage_row=usage_rows.get(row["id"]),
        )
        for row in rows
    ]

    active_or_pilot_count = sum(
        1 for item in items if item["lifecycle_stage"] in {"pilot", "active"}
    )
    candidate_case_study_count = sum(
        1
        for item in items
        if item["case_study_status"] in {"candidate", "drafting", "approved", "published"}
    )
    usage_visible_count = sum(
        1 for item in items if bool(item["usage_summary"]["usage_visible"])
    )
    open_feedback_count = sum(int(item["feedback_summary"]["open_count"]) for item in items)
    feedback_captured_count = sum(int(item["feedback_summary"]["total_count"]) for item in items)
    linked_workspace_count = sum(len(item["linked_workspaces"]) for item in items)

    return {
        "items": items,
        "summary": {
            "total_count": len(items),
            "active_or_pilot_count": active_or_pilot_count,
            "usage_visible_count": usage_visible_count,
            "linked_workspace_count": linked_workspace_count,
            "candidate_case_study_count": candidate_case_study_count,
            "feedback_captured_count": feedback_captured_count,
            "open_feedback_count": open_feedback_count,
            "order": ["updated_at_desc", "id_desc"],
        },
    }


def get_design_partner_detail(
    conn,
    *,
    design_partner_id: UUID,
) -> dict[str, object]:
    row = _fetch_design_partner_row(conn, design_partner_id=design_partner_id)
    if row is None:
        raise DesignPartnerNotFoundError(f"design partner {design_partner_id} was not found")

    workspace_rows = _fetch_workspace_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id, [])
    feedback_rows = _fetch_feedback_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id, [])
    usage_row = _fetch_usage_rows(conn, design_partner_ids=[design_partner_id]).get(design_partner_id)
    return {
        "design_partner": _serialize_partner_row(
            row,
            workspace_rows=workspace_rows,
            feedback_rows=feedback_rows,
            usage_row=usage_row,
        ),
        "feedback": [_serialize_feedback_row(feedback) for feedback in feedback_rows],
    }


def get_design_partner_dashboard(conn) -> dict[str, object]:
    payload = list_design_partners(conn, limit=200)
    items = payload["items"]

    stage_breakdown = {
        stage: sum(1 for item in items if item["lifecycle_stage"] == stage)
        for stage in ("onboarding", "pilot", "active", "paused", "completed")
    }
    support_breakdown = {
        posture: sum(1 for item in items if item["support_status"] == posture)
        for posture in ("green", "watch", "needs_attention", "blocked")
    }
    instrumentation_breakdown = {
        posture: sum(1 for item in items if item["instrumentation_status"] == posture)
        for posture in ("not_ready", "partial", "ready")
    }
    case_study_breakdown = {
        posture: sum(1 for item in items if item["case_study_status"] == posture)
        for posture in ("not_started", "candidate", "drafting", "approved", "published")
    }

    total_runtime_invocations = sum(
        int(item["usage_summary"]["runtime_invocation_count"]) for item in items
    )
    last_invocation_at = None
    for item in items:
        candidate = item["usage_summary"]["last_invocation_at"]
        if candidate is not None and (last_invocation_at is None or candidate > last_invocation_at):
            last_invocation_at = candidate

    launch_ready = (
        payload["summary"]["active_or_pilot_count"] >= 3
        and payload["summary"]["usage_visible_count"] >= 3
        and payload["summary"]["feedback_captured_count"] >= 1
        and payload["summary"]["candidate_case_study_count"] >= 1
    )

    return {
        "dashboard": {
            "summary": payload["summary"],
            "stage_breakdown": stage_breakdown,
            "support_breakdown": support_breakdown,
            "instrumentation_breakdown": instrumentation_breakdown,
            "case_study_breakdown": case_study_breakdown,
            "usage": {
                "runtime_invocation_count": total_runtime_invocations,
                "last_invocation_at": last_invocation_at,
            },
            "launch_readiness": {
                "status": "on_track" if launch_ready else "needs_attention",
                "acceptance_snapshot": {
                    "three_partners_active_or_pilot": payload["summary"]["active_or_pilot_count"] >= 3,
                    "usage_summaries_visible": payload["summary"]["usage_visible_count"] >= 3,
                    "structured_feedback_present": payload["summary"]["feedback_captured_count"] >= 1,
                    "candidate_case_study_underway": payload["summary"]["candidate_case_study_count"] >= 1,
                },
            },
            "partners": items,
        }
    }

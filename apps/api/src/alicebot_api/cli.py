from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
import os
import sys
from uuid import UUID

import psycopg

from alicebot_api.cli_formatting import (
    format_artifact_detail_output,
    format_capture_output,
    format_explain_output,
    format_lifecycle_detail_output,
    format_lifecycle_list_output,
    format_open_loops_output,
    format_recall_output,
    format_resume_output,
    format_review_apply_output,
    format_review_detail_output,
    format_review_queue_output,
    format_status_output,
    format_temporal_explain_output,
    format_temporal_state_output,
    format_temporal_timeline_output,
    format_trusted_fact_pattern_explain_output,
    format_trusted_fact_pattern_list_output,
    format_trusted_fact_playbook_explain_output,
    format_trusted_fact_playbook_list_output,
)
from alicebot_api.config import Settings, get_settings
from alicebot_api.continuity_capture import (
    ContinuityCaptureValidationError,
    capture_continuity_input,
)
from alicebot_api.continuity_evidence import (
    ContinuityEvidenceNotFoundError,
    build_continuity_explain,
    get_continuity_artifact_detail,
)
from alicebot_api.continuity_objects import (
    default_continuity_promotable,
    default_continuity_searchable,
)
from alicebot_api.continuity_lifecycle import (
    ContinuityLifecycleNotFoundError,
    ContinuityLifecycleValidationError,
    get_continuity_lifecycle_state,
    list_continuity_lifecycle_state,
)
from alicebot_api.continuity_open_loops import (
    ContinuityOpenLoopValidationError,
    compile_continuity_open_loop_dashboard,
)
from alicebot_api.continuity_recall import (
    ContinuityRecallValidationError,
    query_continuity_recall,
)
from alicebot_api.continuity_resumption import (
    ContinuityResumptionValidationError,
    compile_continuity_resumption_brief,
)
from alicebot_api.continuity_review import (
    ContinuityReviewNotFoundError,
    ContinuityReviewValidationError,
    apply_continuity_correction,
    get_continuity_review_detail,
    list_continuity_review_queue,
)
from alicebot_api.contracts import (
    CONTINUITY_CAPTURE_EXPLICIT_SIGNALS,
    CONTINUITY_CORRECTION_ACTIONS,
    DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
    DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_LIFECYCLE_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_CONTINUITY_REVIEW_LIMIT,
    MAX_TEMPORAL_TIMELINE_LIMIT,
    MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    ContinuityCaptureCreateInput,
    ContinuityCorrectionInput,
    ContinuityLifecycleQueryInput,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput,
    ContinuityReviewQueueQueryInput,
    TemporalExplainQueryInput,
    TemporalStateAtQueryInput,
    TemporalTimelineQueryInput,
    TrustedFactPatternListQueryInput,
    TrustedFactPlaybookListQueryInput,
)
from alicebot_api.db import ping_database, user_connection
from alicebot_api.retrieval_evaluation import get_retrieval_evaluation_summary
from alicebot_api.store import ContinuityStore, JsonObject
from alicebot_api.temporal_state import (
    TemporalStateValidationError,
    get_temporal_explain,
    get_temporal_state_at,
    get_temporal_timeline,
)
from alicebot_api.trusted_fact_promotions import (
    TrustedFactPromotionNotFoundError,
    get_trusted_fact_pattern,
    get_trusted_fact_playbook,
    list_trusted_fact_patterns,
    list_trusted_fact_playbooks,
)

DEFAULT_CLI_USER_ID = "00000000-0000-0000-0000-000000000001"
REVIEW_STATUS_CHOICES = ("correction_ready", "active", "stale", "superseded", "deleted", "all")


@dataclass(frozen=True, slots=True)
class CLIContext:
    settings: Settings
    database_url: str
    user_id: UUID


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID value: {value}") from exc


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid datetime value '{value}'. Use ISO-8601 format."
        ) from exc


def _parse_optional_json_object(raw_value: str | None, *, option_name: str) -> JsonObject | None:
    if raw_value is None:
        return None
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{option_name} must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{option_name} must be a JSON object")
    return payload


def _add_scope_filter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", default=None, help="Optional query text.")
    parser.add_argument("--thread-id", type=_parse_uuid, default=None, help="Optional thread UUID scope.")
    parser.add_argument("--task-id", type=_parse_uuid, default=None, help="Optional task UUID scope.")
    parser.add_argument("--project", default=None, help="Optional project scope.")
    parser.add_argument("--person", default=None, help="Optional person scope.")
    parser.add_argument("--since", type=_parse_datetime, default=None, help="Optional start time (ISO-8601).")
    parser.add_argument("--until", type=_parse_datetime, default=None, help="Optional end time (ISO-8601).")


def _resolve_user_id(settings: Settings, user_id_flag: str | None) -> UUID:
    if user_id_flag is not None:
        return _parse_uuid(user_id_flag)
    if settings.auth_user_id != "":
        return UUID(settings.auth_user_id)
    return UUID(os.getenv("ALICEBOT_AUTH_USER_ID", DEFAULT_CLI_USER_ID))


def _build_context(args: argparse.Namespace) -> CLIContext:
    settings = get_settings()
    database_url = args.database_url if args.database_url is not None else settings.database_url
    user_id = _resolve_user_id(settings, args.user_id)
    return CLIContext(settings=settings, database_url=database_url, user_id=user_id)


@contextmanager
def _store_context(ctx: CLIContext) -> Iterator[ContinuityStore]:
    with user_connection(ctx.database_url, ctx.user_id) as conn:
        yield ContinuityStore(conn)


def _run_capture(ctx: CLIContext, args: argparse.Namespace) -> str:
    raw_content = " ".join(args.raw_content).strip()
    with _store_context(ctx) as store:
        payload = capture_continuity_input(
            store,
            user_id=ctx.user_id,
            request=ContinuityCaptureCreateInput(
                raw_content=raw_content,
                explicit_signal=args.explicit_signal,
            ),
        )
    return format_capture_output(payload)


def _run_recall(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = query_continuity_recall(
            store,
            user_id=ctx.user_id,
            request=ContinuityRecallQueryInput(
                query=args.query,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                since=args.since,
                until=args.until,
                limit=args.limit,
            ),
        )
    return format_recall_output(payload)


def _run_state_at(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_temporal_state_at(
            store,
            user_id=ctx.user_id,
            request=TemporalStateAtQueryInput(
                entity_id=args.entity_id,
                at=args.at,
            ),
        )
    return format_temporal_state_output(payload)


def _run_timeline(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_temporal_timeline(
            store,
            user_id=ctx.user_id,
            request=TemporalTimelineQueryInput(
                entity_id=args.entity_id,
                since=args.since,
                until=args.until,
                limit=args.limit,
            ),
        )
    return format_temporal_timeline_output(payload)


def _run_lifecycle_list(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_continuity_lifecycle_state(
            store,
            user_id=ctx.user_id,
            request=ContinuityLifecycleQueryInput(limit=args.limit),
        )
    return format_lifecycle_list_output(payload)


def _run_lifecycle_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_continuity_lifecycle_state(
            store,
            user_id=ctx.user_id,
            continuity_object_id=args.continuity_object_id,
        )
    return format_lifecycle_detail_output(payload)


def _run_resume(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = compile_continuity_resumption_brief(
            store,
            user_id=ctx.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=args.query,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                since=args.since,
                until=args.until,
                max_recent_changes=args.max_recent_changes,
                max_open_loops=args.max_open_loops,
                include_non_promotable_facts=args.include_non_promotable_facts,
            ),
        )
    return format_resume_output(payload)


def _run_open_loops(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = compile_continuity_open_loop_dashboard(
            store,
            user_id=ctx.user_id,
            request=ContinuityOpenLoopDashboardQueryInput(
                query=args.query,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                since=args.since,
                until=args.until,
                limit=args.limit,
            ),
        )
    return format_open_loops_output(payload)


def _run_review_queue(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_continuity_review_queue(
            store,
            user_id=ctx.user_id,
            request=ContinuityReviewQueueQueryInput(
                status=args.status,
                limit=args.limit,
            ),
        )
    return format_review_queue_output(payload)


def _run_review_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_continuity_review_detail(
            store,
            user_id=ctx.user_id,
            continuity_object_id=args.continuity_object_id,
        )
    return format_review_detail_output(payload)


def _run_review_apply(ctx: CLIContext, args: argparse.Namespace) -> str:
    body = _parse_optional_json_object(args.body_json, option_name="--body-json")
    provenance = _parse_optional_json_object(args.provenance_json, option_name="--provenance-json")
    replacement_body = _parse_optional_json_object(
        args.replacement_body_json,
        option_name="--replacement-body-json",
    )
    replacement_provenance = _parse_optional_json_object(
        args.replacement_provenance_json,
        option_name="--replacement-provenance-json",
    )

    with _store_context(ctx) as store:
        payload = apply_continuity_correction(
            store,
            user_id=ctx.user_id,
            continuity_object_id=args.continuity_object_id,
            request=ContinuityCorrectionInput(
                action=args.action,
                reason=args.reason,
                title=args.title,
                body=body,
                provenance=provenance,
                confidence=args.confidence,
                replacement_title=args.replacement_title,
                replacement_body=replacement_body,
                replacement_provenance=replacement_provenance,
                replacement_confidence=args.replacement_confidence,
            ),
        )
    return format_review_apply_output(payload)


def _run_explain(ctx: CLIContext, args: argparse.Namespace) -> str:
    if args.entity_id is not None:
        with _store_context(ctx) as store:
            payload = get_temporal_explain(
                store,
                user_id=ctx.user_id,
                request=TemporalExplainQueryInput(
                    entity_id=args.entity_id,
                    at=args.at,
                ),
            )
        return format_temporal_explain_output(payload)

    if args.continuity_object_id is None:
        raise ValueError("explain requires either a continuity_object_id or --entity-id")

    with _store_context(ctx) as store:
        payload = build_continuity_explain(
            store,
            user_id=ctx.user_id,
            continuity_object_id=args.continuity_object_id,
        )
    return format_explain_output(payload)


def _run_evidence_artifact(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_continuity_artifact_detail(
            store,
            user_id=ctx.user_id,
            artifact_id=args.artifact_id,
        )
    return format_artifact_detail_output(payload)


def _run_pattern_list(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_trusted_fact_patterns(
            store,
            user_id=ctx.user_id,
            request=TrustedFactPatternListQueryInput(limit=args.limit),
        )
    return format_trusted_fact_pattern_list_output(payload)


def _run_pattern_explain(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_trusted_fact_pattern(
            store,
            user_id=ctx.user_id,
            pattern_id=args.pattern_id,
        )
    return format_trusted_fact_pattern_explain_output(payload)


def _run_playbook_list(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_trusted_fact_playbooks(
            store,
            user_id=ctx.user_id,
            request=TrustedFactPlaybookListQueryInput(limit=args.limit),
        )
    return format_trusted_fact_playbook_list_output(payload)


def _run_playbook_explain(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_trusted_fact_playbook(
            store,
            user_id=ctx.user_id,
            playbook_id=args.playbook_id,
        )
    return format_trusted_fact_playbook_explain_output(payload)


def _run_status(ctx: CLIContext, _args: argparse.Namespace) -> str:
    database_reachable = ping_database(
        ctx.database_url,
        timeout_seconds=ctx.settings.healthcheck_timeout_seconds,
    )

    status_payload: dict[str, object] = {
        "user_id": str(ctx.user_id),
        "database_status": "reachable" if database_reachable else "unreachable",
        "continuity_capture_events": 0,
        "continuity_objects_total": 0,
        "continuity_objects_active": 0,
        "continuity_objects_stale": 0,
        "continuity_objects_superseded": 0,
        "continuity_objects_deleted": 0,
        "continuity_objects_searchable": 0,
        "continuity_objects_non_searchable": 0,
        "continuity_objects_promotable": 0,
        "continuity_objects_non_promotable": 0,
        "review_correction_ready": 0,
        "review_active": 0,
        "review_stale": 0,
        "review_superseded": 0,
        "review_deleted": 0,
        "open_loops_total": 0,
        "open_loops_waiting_for": 0,
        "open_loops_blocker": 0,
        "open_loops_stale": 0,
        "open_loops_next_action": 0,
        "retrieval_eval_status": "unknown",
        "retrieval_precision_at_k_mean": "0.000",
        "retrieval_precision_at_1_mean": "0.000",
    }
    if not database_reachable:
        return format_status_output(status_payload)

    with _store_context(ctx) as store:
        review_counts = {
            "active": store.count_continuity_review_queue(statuses=["active"]),
            "stale": store.count_continuity_review_queue(statuses=["stale"]),
            "superseded": store.count_continuity_review_queue(statuses=["superseded"]),
            "deleted": store.count_continuity_review_queue(statuses=["deleted"]),
        }

        recall_candidates = store.list_continuity_recall_candidates()
        object_status_counts = {
            "active": 0,
            "stale": 0,
            "superseded": 0,
            "deleted": 0,
        }
        for candidate in recall_candidates:
            status = str(candidate["status"])
            if status in object_status_counts:
                object_status_counts[status] += 1

        open_loops = compile_continuity_open_loop_dashboard(
            store,
            user_id=ctx.user_id,
            request=ContinuityOpenLoopDashboardQueryInput(limit=0),
        )
        open_loop_dashboard = open_loops["dashboard"]

        retrieval_summary = get_retrieval_evaluation_summary(
            store,
            user_id=ctx.user_id,
        )["summary"]

        status_payload.update(
            {
                "continuity_capture_events": store.count_continuity_capture_events(),
                "continuity_objects_total": len(recall_candidates),
                "continuity_objects_active": object_status_counts["active"],
                "continuity_objects_stale": object_status_counts["stale"],
                "continuity_objects_superseded": object_status_counts["superseded"],
                "continuity_objects_deleted": object_status_counts["deleted"],
                "continuity_objects_searchable": sum(
                    1
                    for candidate in recall_candidates
                    if bool(
                        candidate.get(
                            "is_searchable",
                            default_continuity_searchable(str(candidate["object_type"])),
                        )
                    )
                ),
                "continuity_objects_non_searchable": sum(
                    1
                    for candidate in recall_candidates
                    if not bool(
                        candidate.get(
                            "is_searchable",
                            default_continuity_searchable(str(candidate["object_type"])),
                        )
                    )
                ),
                "continuity_objects_promotable": sum(
                    1
                    for candidate in recall_candidates
                    if bool(
                        candidate.get(
                            "is_promotable",
                            default_continuity_promotable(str(candidate["object_type"])),
                        )
                    )
                ),
                "continuity_objects_non_promotable": sum(
                    1
                    for candidate in recall_candidates
                    if not bool(
                        candidate.get(
                            "is_promotable",
                            default_continuity_promotable(str(candidate["object_type"])),
                        )
                    )
                ),
                "review_correction_ready": review_counts["active"] + review_counts["stale"],
                "review_active": review_counts["active"],
                "review_stale": review_counts["stale"],
                "review_superseded": review_counts["superseded"],
                "review_deleted": review_counts["deleted"],
                "open_loops_total": open_loop_dashboard["summary"]["total_count"],
                "open_loops_waiting_for": open_loop_dashboard["waiting_for"]["summary"]["total_count"],
                "open_loops_blocker": open_loop_dashboard["blocker"]["summary"]["total_count"],
                "open_loops_stale": open_loop_dashboard["stale"]["summary"]["total_count"],
                "open_loops_next_action": open_loop_dashboard["next_action"]["summary"]["total_count"],
                "retrieval_eval_status": retrieval_summary["status"],
                "retrieval_precision_at_k_mean": f"{retrieval_summary['precision_at_k_mean']:.3f}",
                "retrieval_precision_at_1_mean": f"{retrieval_summary['precision_at_1_mean']:.3f}",
            }
        )

    return format_status_output(status_payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alicebot",
        description="Deterministic local CLI for Alice continuity workflows.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override database URL. Defaults to settings/env DATABASE_URL.",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help=(
            "Override acting user UUID. Defaults to ALICEBOT_AUTH_USER_ID when set, "
            f"otherwise {DEFAULT_CLI_USER_ID}."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture", help="Capture continuity input.")
    capture_parser.add_argument("raw_content", nargs="+", help="Raw continuity text to capture.")
    capture_parser.add_argument(
        "--explicit-signal",
        choices=CONTINUITY_CAPTURE_EXPLICIT_SIGNALS,
        default=None,
        help="Optional explicit signal for deterministic derivation.",
    )
    capture_parser.set_defaults(handler=_run_capture)

    recall_parser = subparsers.add_parser("recall", help="Recall continuity objects.")
    _add_scope_filter_arguments(recall_parser)
    recall_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_RECALL_LIMIT,
        help=f"Max results (1-{MAX_CONTINUITY_RECALL_LIMIT}).",
    )
    recall_parser.set_defaults(handler=_run_recall)

    state_at_parser = subparsers.add_parser(
        "state-at",
        help="Show entity state reconstructed at a specific point in time.",
    )
    state_at_parser.add_argument("entity_id", type=_parse_uuid, help="Entity UUID.")
    state_at_parser.add_argument("--at", type=_parse_datetime, default=None, help="As-of time (ISO-8601).")
    state_at_parser.set_defaults(handler=_run_state_at)

    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Show chronological temporal history for one entity.",
    )
    timeline_parser.add_argument("entity_id", type=_parse_uuid, help="Entity UUID.")
    timeline_parser.add_argument("--since", type=_parse_datetime, default=None, help="Optional start time (ISO-8601).")
    timeline_parser.add_argument("--until", type=_parse_datetime, default=None, help="Optional end time (ISO-8601).")
    timeline_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_TEMPORAL_TIMELINE_LIMIT,
        help=f"Max timeline events (1-{MAX_TEMPORAL_TIMELINE_LIMIT}).",
    )
    timeline_parser.set_defaults(handler=_run_timeline)

    lifecycle_parser = subparsers.add_parser("lifecycle", help="Inspect continuity lifecycle state.")
    lifecycle_subparsers = lifecycle_parser.add_subparsers(dest="lifecycle_command", required=True)

    lifecycle_list_parser = lifecycle_subparsers.add_parser("list", help="List lifecycle states.")
    lifecycle_list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
        help=f"Max lifecycle results (1-{MAX_CONTINUITY_LIFECYCLE_LIMIT}).",
    )
    lifecycle_list_parser.set_defaults(handler=_run_lifecycle_list)

    lifecycle_show_parser = lifecycle_subparsers.add_parser("show", help="Show one lifecycle state.")
    lifecycle_show_parser.add_argument(
        "continuity_object_id",
        type=_parse_uuid,
        help="Continuity object UUID.",
    )
    lifecycle_show_parser.set_defaults(handler=_run_lifecycle_show)

    resume_parser = subparsers.add_parser("resume", help="Compile continuity resumption brief.")
    _add_scope_filter_arguments(resume_parser)
    resume_parser.add_argument(
        "--max-recent-changes",
        type=int,
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        help=f"Recent change limit (0-{MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT}).",
    )
    resume_parser.add_argument(
        "--max-open-loops",
        type=int,
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        help=f"Open loop limit (0-{MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT}).",
    )
    resume_parser.add_argument(
        "--include-non-promotable-facts",
        action="store_true",
        help="Include searchable but non-promotable facts in recent changes.",
    )
    resume_parser.set_defaults(handler=_run_resume)

    open_loops_parser = subparsers.add_parser(
        "open-loops",
        help="List open-loop dashboard grouped by posture.",
    )
    _add_scope_filter_arguments(open_loops_parser)
    open_loops_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
        help=f"Per-posture item limit (0-{MAX_CONTINUITY_OPEN_LOOP_LIMIT}).",
    )
    open_loops_parser.set_defaults(handler=_run_open_loops)

    review_parser = subparsers.add_parser("review", help="Review queue and correction commands.")
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)

    review_queue_parser = review_subparsers.add_parser("queue", help="List review queue.")
    review_queue_parser.add_argument(
        "--status",
        choices=REVIEW_STATUS_CHOICES,
        default="correction_ready",
        help="Queue status filter.",
    )
    review_queue_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        help=f"Max queue results (1-{MAX_CONTINUITY_REVIEW_LIMIT}).",
    )
    review_queue_parser.set_defaults(handler=_run_review_queue)

    review_show_parser = review_subparsers.add_parser("show", help="Show detail for one review object.")
    review_show_parser.add_argument("continuity_object_id", type=_parse_uuid, help="Continuity object UUID.")
    review_show_parser.set_defaults(handler=_run_review_show)

    review_apply_parser = review_subparsers.add_parser("apply", help="Apply a continuity correction.")
    review_apply_parser.add_argument("continuity_object_id", type=_parse_uuid, help="Continuity object UUID.")
    review_apply_parser.add_argument(
        "--action",
        required=True,
        choices=CONTINUITY_CORRECTION_ACTIONS,
        help="Correction action.",
    )
    review_apply_parser.add_argument("--reason", default=None, help="Optional correction reason.")
    review_apply_parser.add_argument("--title", default=None, help="Replacement title for edit.")
    review_apply_parser.add_argument(
        "--body-json",
        default=None,
        help="JSON object payload for body replacement on edit.",
    )
    review_apply_parser.add_argument(
        "--provenance-json",
        default=None,
        help="JSON object payload for provenance replacement on edit.",
    )
    review_apply_parser.add_argument(
        "--confidence",
        type=float,
        default=None,
        help="Updated confidence for edit/supersede.",
    )
    review_apply_parser.add_argument(
        "--replacement-title",
        default=None,
        help="Replacement title for supersede.",
    )
    review_apply_parser.add_argument(
        "--replacement-body-json",
        default=None,
        help="JSON object payload for supersede replacement body.",
    )
    review_apply_parser.add_argument(
        "--replacement-provenance-json",
        default=None,
        help="JSON object payload for supersede replacement provenance.",
    )
    review_apply_parser.add_argument(
        "--replacement-confidence",
        type=float,
        default=None,
        help="Replacement confidence for supersede.",
    )
    review_apply_parser.set_defaults(handler=_run_review_apply)

    explain_parser = subparsers.add_parser(
        "explain",
        help="Show continuity evidence or temporal explain output.",
    )
    explain_parser.add_argument(
        "continuity_object_id",
        nargs="?",
        type=_parse_uuid,
        help="Continuity object UUID.",
    )
    explain_parser.add_argument("--entity-id", type=_parse_uuid, default=None, help="Entity UUID.")
    explain_parser.add_argument("--at", type=_parse_datetime, default=None, help="As-of time (ISO-8601).")
    explain_parser.set_defaults(handler=_run_explain)

    evidence_parser = subparsers.add_parser("evidence", help="Inspect archived continuity artifacts.")
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command", required=True)
    evidence_artifact_parser = evidence_subparsers.add_parser("artifact", help="Show one archived artifact.")
    evidence_artifact_parser.add_argument("artifact_id", type=_parse_uuid, help="Continuity artifact UUID.")
    evidence_artifact_parser.set_defaults(handler=_run_evidence_artifact)

    patterns_parser = subparsers.add_parser("patterns", help="List and explain trusted fact patterns.")
    patterns_subparsers = patterns_parser.add_subparsers(dest="patterns_command", required=True)
    patterns_list_parser = patterns_subparsers.add_parser("list", help="List trusted fact patterns.")
    patterns_list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
        help=f"Max pattern results (1-{MAX_TRUSTED_FACT_PROMOTION_LIMIT}).",
    )
    patterns_list_parser.set_defaults(handler=_run_pattern_list)
    patterns_explain_parser = patterns_subparsers.add_parser("explain", help="Explain one trusted fact pattern.")
    patterns_explain_parser.add_argument("pattern_id", type=_parse_uuid, help="Pattern UUID.")
    patterns_explain_parser.set_defaults(handler=_run_pattern_explain)

    playbooks_parser = subparsers.add_parser("playbooks", help="List and explain trusted fact playbooks.")
    playbooks_subparsers = playbooks_parser.add_subparsers(dest="playbooks_command", required=True)
    playbooks_list_parser = playbooks_subparsers.add_parser("list", help="List trusted fact playbooks.")
    playbooks_list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
        help=f"Max playbook results (1-{MAX_TRUSTED_FACT_PROMOTION_LIMIT}).",
    )
    playbooks_list_parser.set_defaults(handler=_run_playbook_list)
    playbooks_explain_parser = playbooks_subparsers.add_parser("explain", help="Explain one trusted fact playbook.")
    playbooks_explain_parser.add_argument("playbook_id", type=_parse_uuid, help="Playbook UUID.")
    playbooks_explain_parser.set_defaults(handler=_run_playbook_explain)

    status_parser = subparsers.add_parser("status", help="Show local continuity runtime status.")
    status_parser.set_defaults(handler=_run_status)

    return parser


def _validate_limit(value: int, *, option_name: str, minimum: int, maximum: int) -> None:
    if value < minimum or value > maximum:
        raise ValueError(f"{option_name} must be between {minimum} and {maximum}")


def _validate_arguments(args: argparse.Namespace) -> None:
    if args.command == "recall":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_RECALL_LIMIT,
        )
    elif args.command == "timeline":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_TEMPORAL_TIMELINE_LIMIT,
        )
    elif args.command == "lifecycle" and args.lifecycle_command == "list":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_LIFECYCLE_LIMIT,
        )
    elif args.command == "resume":
        _validate_limit(
            args.max_recent_changes,
            option_name="--max-recent-changes",
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        )
        _validate_limit(
            args.max_open_loops,
            option_name="--max-open-loops",
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        )
    elif args.command == "open-loops":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=0,
            maximum=MAX_CONTINUITY_OPEN_LOOP_LIMIT,
        )
    elif args.command == "review" and args.review_command == "queue":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_REVIEW_LIMIT,
        )
    elif args.command == "patterns" and args.patterns_command == "list":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_TRUSTED_FACT_PROMOTION_LIMIT,
        )
    elif args.command == "playbooks" and args.playbooks_command == "list":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_TRUSTED_FACT_PROMOTION_LIMIT,
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        _validate_arguments(args)
        ctx = _build_context(args)
        handler = args.handler
        output = handler(ctx, args)
    except (
        ValueError,
        psycopg.Error,
        ContinuityCaptureValidationError,
        ContinuityLifecycleValidationError,
        ContinuityLifecycleNotFoundError,
        ContinuityRecallValidationError,
        ContinuityResumptionValidationError,
        ContinuityOpenLoopValidationError,
        ContinuityReviewValidationError,
        ContinuityReviewNotFoundError,
        ContinuityEvidenceNotFoundError,
        TemporalStateValidationError,
        TrustedFactPromotionNotFoundError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


__all__ = ["build_parser", "main"]

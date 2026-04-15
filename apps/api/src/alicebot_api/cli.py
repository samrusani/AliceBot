from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from uuid import UUID

import psycopg

from alicebot_api.cli_formatting import (
    format_artifact_detail_output,
    format_capture_output,
    format_continuity_brief_output,
    format_contradiction_case_detail_output,
    format_contradiction_case_list_output,
    format_contradiction_sync_output,
    format_explain_output,
    format_lifecycle_detail_output,
    format_lifecycle_list_output,
    format_memory_operation_candidates_output,
    format_memory_operation_commit_output,
    format_memory_operations_output,
    format_open_loops_output,
    format_recall_output,
    format_resume_output,
    format_review_apply_output,
    format_review_detail_output,
    format_review_queue_output,
    format_status_output,
    format_task_brief_comparison_output,
    format_task_brief_output,
    format_temporal_explain_output,
    format_temporal_state_output,
    format_temporal_timeline_output,
    format_trust_signals_output,
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
from alicebot_api.continuity_brief import (
    ContinuityBriefValidationError,
    compile_continuity_brief,
)
from alicebot_api.continuity_evidence import (
    ContinuityEvidenceNotFoundError,
    build_continuity_explain,
    get_continuity_artifact_detail,
)
from alicebot_api.continuity_contradictions import (
    ContinuityContradictionNotFoundError,
    ContinuityContradictionValidationError,
    get_contradiction_case,
    list_contradiction_cases,
    resolve_contradiction_case,
    sync_contradictions,
)
from alicebot_api.memory_mutations import (
    MemoryMutationValidationError,
    commit_memory_operations,
    generate_memory_operation_candidates,
    list_memory_operation_candidates,
    list_memory_operations,
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
from alicebot_api.continuity_trust import list_trust_signals
from alicebot_api.contracts import (
    CONTINUITY_CAPTURE_EXPLICIT_SIGNALS,
    CONTINUITY_CORRECTION_ACTIONS,
    CONTRADICTION_RESOLUTION_ACTIONS,
    CONTINUITY_BRIEF_TYPE_ORDER,
    DEFAULT_CONTINUITY_CAPTURE_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
    DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
    DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
    MAX_CONTINUITY_REVIEW_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    MAX_CONTINUITY_LIFECYCLE_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_TASK_BRIEF_TOKEN_BUDGET,
    MAX_TEMPORAL_TIMELINE_LIMIT,
    MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    ContradictionCaseListQueryInput,
    ContradictionResolveInput,
    ContradictionSyncInput,
    ContinuityCaptureCreateInput,
    ContinuityBriefRequestInput,
    ContinuityCorrectionInput,
    ContinuityLifecycleQueryInput,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput,
    ContinuityReviewQueueQueryInput,
    MemoryOperationCommitInput,
    MemoryOperationGenerateInput,
    MemoryOperationListInput,
    TaskBriefCompileRequestInput,
    TemporalExplainQueryInput,
    TemporalStateAtQueryInput,
    TemporalTimelineQueryInput,
    TrustSignalListQueryInput,
    TrustedFactPatternListQueryInput,
    TrustedFactPlaybookListQueryInput,
)
from alicebot_api.task_briefing import (
    TaskBriefNotFoundError,
    TaskBriefValidationError,
    compare_task_briefs,
    compile_and_persist_task_brief,
    get_persisted_task_brief,
)
from alicebot_api.db import ping_database, user_connection
from alicebot_api.public_evals import (
    get_public_eval_run,
    list_public_eval_runs,
    list_public_eval_suites,
    run_public_evals,
    write_public_eval_report,
)
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
MAINTENANCE_REPORT_PATH_ENV = "ALICEBOT_MAINTENANCE_REPORT_PATH"
DEFAULT_MAINTENANCE_REPORT_PATH = (
    Path(__file__).resolve().parents[4] / "artifacts" / "ops" / "maintenance_status_latest.json"
)
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


def _add_task_brief_arguments(parser: argparse.ArgumentParser) -> None:
    _add_scope_filter_arguments(parser)
    parser.add_argument(
        "--workspace-id",
        type=_parse_uuid,
        default=None,
        help="Optional workspace UUID used to resolve model-pack briefing defaults.",
    )
    parser.add_argument(
        "--pack-id",
        default=None,
        help="Optional model-pack id to resolve within the workspace.",
    )
    parser.add_argument(
        "--pack-version",
        default=None,
        help="Optional model-pack version to resolve within the workspace.",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=("user_recall", "resume", "worker_subtask", "agent_handoff"),
        help="Task brief mode.",
    )
    parser.add_argument(
        "--include-non-promotable-facts",
        action="store_true",
        help="Include searchable but non-promotable facts where the mode allows it.",
    )
    parser.add_argument(
        "--provider-strategy",
        default=None,
        help="Optional provider briefing strategy label.",
    )
    parser.add_argument(
        "--model-pack-strategy",
        default=None,
        help="Optional model-pack briefing strategy override.",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        help=f"Optional explicit token budget (1-{MAX_TASK_BRIEF_TOKEN_BUDGET}).",
    )


def _add_continuity_brief_arguments(parser: argparse.ArgumentParser) -> None:
    _add_scope_filter_arguments(parser)
    parser.add_argument(
        "--brief-type",
        choices=CONTINUITY_BRIEF_TYPE_ORDER,
        default="general",
        help="One-call continuity brief type.",
    )
    parser.add_argument(
        "--max-relevant-facts",
        type=int,
        default=DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
        help=f"Maximum relevant facts ({0}-{MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT}).",
    )
    parser.add_argument(
        "--max-recent-changes",
        type=int,
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        help=f"Maximum recent changes ({0}-{MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT}).",
    )
    parser.add_argument(
        "--max-open-loops",
        type=int,
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        help=f"Maximum open loops ({0}-{MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT}).",
    )
    parser.add_argument(
        "--max-conflicts",
        type=int,
        default=DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
        help=f"Maximum open conflicts ({0}-{MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT}).",
    )
    parser.add_argument(
        "--max-timeline-highlights",
        type=int,
        default=DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
        help=f"Maximum timeline highlights ({0}-{MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT}).",
    )
    parser.add_argument(
        "--include-non-promotable-facts",
        action="store_true",
        help="Include searchable but non-promotable facts where the brief type allows it.",
    )


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


def _parse_maintenance_status_payload(payload: object) -> dict[str, object]:
    default_snapshot: dict[str, object] = {
        "maintenance_status": "unknown",
        "maintenance_schedule": "unknown",
        "maintenance_last_run_at": "unknown",
        "maintenance_failure_count": 0,
        "maintenance_warning_count": 0,
        "maintenance_stale_fact_count": 0,
        "maintenance_reembedded_segment_count": 0,
        "maintenance_pattern_candidate_count": 0,
        "maintenance_benchmark_status": "unknown",
    }

    if not isinstance(payload, dict):
        return default_snapshot

    summary = payload.get("summary")
    if isinstance(summary, dict):
        status = summary.get("status")
        if isinstance(status, str):
            default_snapshot["maintenance_status"] = status
        schedule = summary.get("schedule")
        if isinstance(schedule, str):
            default_snapshot["maintenance_schedule"] = schedule
        completed_at = summary.get("run_completed_at")
        if isinstance(completed_at, str):
            default_snapshot["maintenance_last_run_at"] = completed_at
        failure_count = summary.get("failure_count")
        if isinstance(failure_count, int):
            default_snapshot["maintenance_failure_count"] = failure_count
        warning_count = summary.get("warning_count")
        if isinstance(warning_count, int):
            default_snapshot["maintenance_warning_count"] = warning_count

    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        return default_snapshot

    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_key = job.get("job_key")
        details = job.get("details")
        if not isinstance(job_key, str) or not isinstance(details, dict):
            continue
        if job_key == "stale_fact_marking":
            stale_fact_count = details.get("stale_fact_count")
            if isinstance(stale_fact_count, int):
                default_snapshot["maintenance_stale_fact_count"] = stale_fact_count
        elif job_key == "reembed_missing_segments":
            reembedded_segment_count = details.get("reembedded_segment_count")
            if isinstance(reembedded_segment_count, int):
                default_snapshot["maintenance_reembedded_segment_count"] = reembedded_segment_count
        elif job_key == "pattern_candidate_recompute":
            pattern_candidate_count = details.get("pattern_candidate_count")
            if isinstance(pattern_candidate_count, int):
                default_snapshot["maintenance_pattern_candidate_count"] = pattern_candidate_count
        elif job_key == "benchmark_regeneration":
            benchmark_status = details.get("benchmark_status")
            if isinstance(benchmark_status, str):
                default_snapshot["maintenance_benchmark_status"] = benchmark_status

    return default_snapshot


def _load_maintenance_status_snapshot() -> dict[str, object]:
    raw_path = os.getenv(MAINTENANCE_REPORT_PATH_ENV)
    if raw_path is None or raw_path.strip() == "":
        report_path = DEFAULT_MAINTENANCE_REPORT_PATH
    else:
        candidate = Path(raw_path.strip()).expanduser()
        report_path = candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve()

    if not report_path.exists():
        return _parse_maintenance_status_payload({})

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _parse_maintenance_status_payload({})

    return _parse_maintenance_status_payload(payload)


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


def _run_mutation_generate(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = generate_memory_operation_candidates(
            store,
            user_id=ctx.user_id,
            request=MemoryOperationGenerateInput(
                user_content=args.user_content or "",
                assistant_content=args.assistant_content or "",
                mode=args.mode,
                sync_fingerprint=args.sync_fingerprint,
                source_kind=args.source_kind,
                session_id=args.session_id,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                target_continuity_object_id=args.target_continuity_object_id,
            ),
        )
    return format_memory_operation_candidates_output(payload)


def _run_mutation_candidates(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_memory_operation_candidates(
            store,
            user_id=ctx.user_id,
            request=MemoryOperationListInput(
                limit=args.limit,
                policy_action=args.policy_action,
                operation_type=args.operation_type,
                sync_fingerprint=args.sync_fingerprint,
            ),
        )
    return format_memory_operation_candidates_output(payload)


def _run_mutation_commit(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = commit_memory_operations(
            store,
            user_id=ctx.user_id,
            request=MemoryOperationCommitInput(
                candidate_ids=args.candidate_ids,
                sync_fingerprint=args.sync_fingerprint,
                include_review_required=args.include_review_required,
            ),
        )
    return format_memory_operation_commit_output(payload)


def _run_mutation_operations(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_memory_operations(
            store,
            user_id=ctx.user_id,
            request=MemoryOperationListInput(
                limit=args.limit,
                sync_fingerprint=args.sync_fingerprint,
            ),
        )
    return format_memory_operations_output(payload)


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
                debug=args.debug,
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
                debug=args.debug,
            ),
        )
    return format_resume_output(payload)


def _run_brief(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = compile_continuity_brief(
            store,
            user_id=ctx.user_id,
            request=ContinuityBriefRequestInput(
                brief_type=args.brief_type,
                query=args.query,
                thread_id=args.thread_id,
                task_id=args.task_id,
                project=args.project,
                person=args.person,
                since=args.since,
                until=args.until,
                max_relevant_facts=args.max_relevant_facts,
                max_recent_changes=args.max_recent_changes,
                max_open_loops=args.max_open_loops,
                max_conflicts=args.max_conflicts,
                max_timeline_highlights=args.max_timeline_highlights,
                include_non_promotable_facts=args.include_non_promotable_facts,
            ),
        )
    return format_continuity_brief_output(payload)


def _task_brief_request_from_args(args: argparse.Namespace) -> TaskBriefCompileRequestInput:
    return TaskBriefCompileRequestInput(
        mode=args.mode,
        query=args.query,
        workspace_id=args.workspace_id,
        pack_id=args.pack_id,
        pack_version=args.pack_version,
        thread_id=args.thread_id,
        task_id=args.task_id,
        project=args.project,
        person=args.person,
        since=args.since,
        until=args.until,
        include_non_promotable_facts=args.include_non_promotable_facts,
        provider_strategy=args.provider_strategy,
        model_pack_strategy=args.model_pack_strategy,
        token_budget=args.token_budget,
    )


def _run_task_brief_compile(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = compile_and_persist_task_brief(
            store,
            user_id=ctx.user_id,
            request=_task_brief_request_from_args(args),
        )
    return format_task_brief_output(payload)


def _run_task_brief_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_persisted_task_brief(
            store,
            task_brief_id=args.task_brief_id,
        )
    return format_task_brief_output(payload)


def _run_task_brief_compare(ctx: CLIContext, args: argparse.Namespace) -> str:
    primary_request = _task_brief_request_from_args(args)
    secondary_request = TaskBriefCompileRequestInput(
        mode=args.compare_to_mode,
        query=args.query,
        workspace_id=args.workspace_id,
        pack_id=args.pack_id,
        pack_version=args.pack_version,
        thread_id=args.thread_id,
        task_id=args.task_id,
        project=args.project,
        person=args.person,
        since=args.since,
        until=args.until,
        include_non_promotable_facts=args.include_non_promotable_facts,
        provider_strategy=args.provider_strategy,
        model_pack_strategy=args.compare_model_pack_strategy or args.model_pack_strategy,
        token_budget=args.compare_token_budget,
    )
    with _store_context(ctx) as store:
        payload = compare_task_briefs(
            store,
            user_id=ctx.user_id,
            primary_request=primary_request,
            secondary_request=secondary_request,
        )
    return format_task_brief_comparison_output(payload)


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


def _run_contradictions_detect(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = sync_contradictions(
            store,
            user_id=ctx.user_id,
            request=ContradictionSyncInput(
                continuity_object_id=args.continuity_object_id,
                limit=args.limit,
            ),
        )
    return format_contradiction_sync_output(payload)


def _run_contradictions_list(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_contradiction_cases(
            store,
            user_id=ctx.user_id,
            request=ContradictionCaseListQueryInput(
                status=args.status,
                limit=args.limit,
                continuity_object_id=args.continuity_object_id,
            ),
        )
    return format_contradiction_case_list_output(payload)


def _run_contradictions_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_contradiction_case(
            store,
            user_id=ctx.user_id,
            contradiction_case_id=args.contradiction_case_id,
        )
    return format_contradiction_case_detail_output(payload)


def _run_contradictions_resolve(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = resolve_contradiction_case(
            store,
            user_id=ctx.user_id,
            contradiction_case_id=args.contradiction_case_id,
            request=ContradictionResolveInput(
                action=args.action,
                note=args.note,
            ),
        )
    return format_contradiction_case_detail_output(
        {"contradiction_case": payload["contradiction_case"]}
    )


def _run_trust_signals(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_trust_signals(
            store,
            user_id=ctx.user_id,
            request=TrustSignalListQueryInput(
                limit=args.limit,
                continuity_object_id=args.continuity_object_id,
                signal_state=args.signal_state,
                signal_type=args.signal_type,
            ),
        )
    return format_trust_signals_output(payload)


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
    maintenance_status = _load_maintenance_status_snapshot()

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
        "maintenance_status": maintenance_status["maintenance_status"],
        "maintenance_schedule": maintenance_status["maintenance_schedule"],
        "maintenance_last_run_at": maintenance_status["maintenance_last_run_at"],
        "maintenance_failure_count": maintenance_status["maintenance_failure_count"],
        "maintenance_warning_count": maintenance_status["maintenance_warning_count"],
        "maintenance_stale_fact_count": maintenance_status["maintenance_stale_fact_count"],
        "maintenance_reembedded_segment_count": maintenance_status["maintenance_reembedded_segment_count"],
        "maintenance_pattern_candidate_count": maintenance_status["maintenance_pattern_candidate_count"],
        "maintenance_benchmark_status": maintenance_status["maintenance_benchmark_status"],
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


def _run_eval_suites(ctx: CLIContext, _args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_public_eval_suites(
            store,
            user_id=ctx.user_id,
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def _run_eval_runs(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = list_public_eval_runs(
            store,
            user_id=ctx.user_id,
            limit=args.limit,
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def _run_eval_show(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = get_public_eval_run(
            store,
            user_id=ctx.user_id,
            eval_run_id=args.eval_run_id,
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def _run_eval_run(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _store_context(ctx) as store:
        payload = run_public_evals(
            store,
            user_id=ctx.user_id,
            suite_keys=args.suite_key,
        )
    if args.report_path is not None:
        written_path = write_public_eval_report(
            report=payload["report"],
            report_path=args.report_path,
        )
        payload["written_report_path"] = str(written_path)
    return json.dumps(payload, indent=2, sort_keys=True)


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

    mutations_parser = subparsers.add_parser("mutations", help="Generate, inspect, and apply memory operations.")
    mutations_subparsers = mutations_parser.add_subparsers(dest="mutations_command", required=True)

    mutation_generate_parser = mutations_subparsers.add_parser(
        "generate",
        help="Generate explicit mutation candidates from a turn pair.",
    )
    mutation_generate_parser.add_argument("--user-content", default="", help="User turn content.")
    mutation_generate_parser.add_argument("--assistant-content", default="", help="Assistant turn content.")
    mutation_generate_parser.add_argument(
        "--mode",
        choices=("manual", "assist", "auto"),
        default="assist",
        help="Mutation policy mode.",
    )
    mutation_generate_parser.add_argument("--sync-fingerprint", default=None, help="Optional sync fingerprint.")
    mutation_generate_parser.add_argument("--source-kind", default="sync_turn", help="Source kind label.")
    mutation_generate_parser.add_argument("--session-id", default=None, help="Optional session id.")
    mutation_generate_parser.add_argument("--thread-id", type=_parse_uuid, default=None, help="Optional thread UUID.")
    mutation_generate_parser.add_argument("--task-id", type=_parse_uuid, default=None, help="Optional task UUID.")
    mutation_generate_parser.add_argument("--project", default=None, help="Optional project scope.")
    mutation_generate_parser.add_argument("--person", default=None, help="Optional person scope.")
    mutation_generate_parser.add_argument(
        "--target-continuity-object-id",
        type=_parse_uuid,
        default=None,
        help="Optional explicit target continuity object UUID.",
    )
    mutation_generate_parser.set_defaults(handler=_run_mutation_generate)

    mutation_candidates_parser = mutations_subparsers.add_parser(
        "candidates",
        help="List generated mutation candidates.",
    )
    mutation_candidates_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_CAPTURE_LIMIT,
        help="Max candidates (1-100).",
    )
    mutation_candidates_parser.add_argument(
        "--policy-action",
        choices=("auto_apply", "review_required", "skip"),
        default=None,
        help="Optional policy filter.",
    )
    mutation_candidates_parser.add_argument(
        "--operation-type",
        choices=("ADD", "UPDATE", "SUPERSEDE", "DELETE", "NOOP"),
        default=None,
        help="Optional operation filter.",
    )
    mutation_candidates_parser.add_argument("--sync-fingerprint", default=None, help="Optional sync fingerprint.")
    mutation_candidates_parser.set_defaults(handler=_run_mutation_candidates)

    mutation_commit_parser = mutations_subparsers.add_parser(
        "commit",
        help="Apply generated mutation candidates.",
    )
    mutation_commit_parser.add_argument(
        "candidate_ids",
        nargs="*",
        type=_parse_uuid,
        help="Candidate UUIDs to apply.",
    )
    mutation_commit_parser.add_argument("--sync-fingerprint", default=None, help="Optional sync fingerprint.")
    mutation_commit_parser.add_argument(
        "--include-review-required",
        action="store_true",
        help="Allow review-required candidates to apply.",
    )
    mutation_commit_parser.set_defaults(handler=_run_mutation_commit)

    mutation_operations_parser = mutations_subparsers.add_parser(
        "operations",
        help="List committed memory operations.",
    )
    mutation_operations_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_CAPTURE_LIMIT,
        help="Max operations (1-100).",
    )
    mutation_operations_parser.add_argument("--sync-fingerprint", default=None, help="Optional sync fingerprint.")
    mutation_operations_parser.set_defaults(handler=_run_mutation_operations)

    brief_parser = subparsers.add_parser(
        "brief",
        help="Compile the primary one-call continuity brief.",
    )
    _add_continuity_brief_arguments(brief_parser)
    brief_parser.set_defaults(handler=_run_brief)

    recall_parser = subparsers.add_parser("recall", help="Recall continuity objects.")
    _add_scope_filter_arguments(recall_parser)
    recall_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_RECALL_LIMIT,
        help=f"Max results (1-{MAX_CONTINUITY_RECALL_LIMIT}).",
    )
    recall_parser.add_argument(
        "--debug",
        action="store_true",
        help="Include hybrid retrieval stage scores and exclusion reasons.",
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
    resume_parser.add_argument(
        "--debug",
        action="store_true",
        help="Include the underlying hybrid retrieval trace.",
    )
    resume_parser.set_defaults(handler=_run_resume)

    task_briefs_parser = subparsers.add_parser(
        "task-briefs",
        help="Compile, compare, and inspect task-adaptive briefs.",
    )
    task_briefs_subparsers = task_briefs_parser.add_subparsers(dest="task_briefs_command", required=True)

    task_briefs_compile_parser = task_briefs_subparsers.add_parser(
        "compile",
        help="Compile and persist one task-adaptive brief.",
    )
    _add_task_brief_arguments(task_briefs_compile_parser)
    task_briefs_compile_parser.set_defaults(handler=_run_task_brief_compile)

    task_briefs_show_parser = task_briefs_subparsers.add_parser(
        "show",
        help="Load one persisted task brief.",
    )
    task_briefs_show_parser.add_argument("task_brief_id", type=_parse_uuid, help="Task brief UUID.")
    task_briefs_show_parser.set_defaults(handler=_run_task_brief_show)

    task_briefs_compare_parser = task_briefs_subparsers.add_parser(
        "compare",
        help="Compare two task brief modes for the same scope.",
    )
    _add_task_brief_arguments(task_briefs_compare_parser)
    task_briefs_compare_parser.add_argument(
        "--compare-to-mode",
        required=True,
        choices=("user_recall", "resume", "worker_subtask", "agent_handoff"),
        help="Secondary mode for comparison.",
    )
    task_briefs_compare_parser.add_argument(
        "--compare-model-pack-strategy",
        default=None,
        help="Optional model-pack strategy override for the comparison brief.",
    )
    task_briefs_compare_parser.add_argument(
        "--compare-token-budget",
        type=int,
        default=None,
        help=f"Optional comparison token budget (1-{MAX_TASK_BRIEF_TOKEN_BUDGET}).",
    )
    task_briefs_compare_parser.set_defaults(handler=_run_task_brief_compare)

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

    contradictions_parser = subparsers.add_parser(
        "contradictions",
        help="Detect, inspect, and resolve continuity contradictions.",
    )
    contradictions_subparsers = contradictions_parser.add_subparsers(
        dest="contradictions_command",
        required=True,
    )

    contradictions_detect_parser = contradictions_subparsers.add_parser(
        "detect",
        help="Run contradiction detection and persist current cases.",
    )
    contradictions_detect_parser.add_argument(
        "--continuity-object-id",
        type=_parse_uuid,
        default=None,
        help="Optional continuity object UUID to scope detection.",
    )
    contradictions_detect_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        help=f"Max contradiction rows to print (1-{MAX_CONTINUITY_REVIEW_LIMIT}).",
    )
    contradictions_detect_parser.set_defaults(handler=_run_contradictions_detect)

    contradictions_list_parser = contradictions_subparsers.add_parser(
        "list",
        help="List contradiction cases.",
    )
    contradictions_list_parser.add_argument(
        "--status",
        choices=("open", "resolved", "dismissed"),
        default="open",
        help="Case status filter.",
    )
    contradictions_list_parser.add_argument(
        "--continuity-object-id",
        type=_parse_uuid,
        default=None,
        help="Optional continuity object UUID filter.",
    )
    contradictions_list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        help=f"Max contradiction rows (1-{MAX_CONTINUITY_REVIEW_LIMIT}).",
    )
    contradictions_list_parser.set_defaults(handler=_run_contradictions_list)

    contradictions_show_parser = contradictions_subparsers.add_parser(
        "show",
        help="Show one contradiction case.",
    )
    contradictions_show_parser.add_argument(
        "contradiction_case_id",
        type=_parse_uuid,
        help="Contradiction case UUID.",
    )
    contradictions_show_parser.set_defaults(handler=_run_contradictions_show)

    contradictions_resolve_parser = contradictions_subparsers.add_parser(
        "resolve",
        help="Resolve one contradiction case.",
    )
    contradictions_resolve_parser.add_argument(
        "contradiction_case_id",
        type=_parse_uuid,
        help="Contradiction case UUID.",
    )
    contradictions_resolve_parser.add_argument(
        "--action",
        required=True,
        choices=CONTRADICTION_RESOLUTION_ACTIONS,
        help="Resolution action.",
    )
    contradictions_resolve_parser.add_argument(
        "--note",
        default=None,
        help="Optional operator note.",
    )
    contradictions_resolve_parser.set_defaults(handler=_run_contradictions_resolve)

    trust_parser = subparsers.add_parser(
        "trust",
        help="Inspect stored trust signals.",
    )
    trust_subparsers = trust_parser.add_subparsers(dest="trust_command", required=True)
    trust_signals_parser = trust_subparsers.add_parser("signals", help="List trust signals.")
    trust_signals_parser.add_argument(
        "--continuity-object-id",
        type=_parse_uuid,
        default=None,
        help="Optional continuity object UUID filter.",
    )
    trust_signals_parser.add_argument(
        "--signal-state",
        choices=("active", "inactive"),
        default="active",
        help="Signal state filter.",
    )
    trust_signals_parser.add_argument(
        "--signal-type",
        choices=("correction", "corroboration", "contradiction", "weak_inference"),
        default=None,
        help="Optional signal type filter.",
    )
    trust_signals_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        help=f"Max trust signals (1-{MAX_CONTINUITY_REVIEW_LIMIT}).",
    )
    trust_signals_parser.set_defaults(handler=_run_trust_signals)

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

    evals_parser = subparsers.add_parser("evals", help="Run and inspect public eval suites.")
    evals_subparsers = evals_parser.add_subparsers(dest="evals_command", required=True)

    evals_suites_parser = evals_subparsers.add_parser("suites", help="List public eval suites.")
    evals_suites_parser.set_defaults(handler=_run_eval_suites)

    evals_run_parser = evals_subparsers.add_parser("run", help="Run the public eval harness.")
    evals_run_parser.add_argument(
        "--suite-key",
        action="append",
        default=None,
        help="Optional suite key filter. Repeat to run multiple suites.",
    )
    evals_run_parser.add_argument(
        "--report-path",
        default=None,
        help="Optional output path for the canonical JSON report artifact.",
    )
    evals_run_parser.set_defaults(handler=_run_eval_run)

    evals_runs_parser = evals_subparsers.add_parser("runs", help="List persisted public eval runs.")
    evals_runs_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of eval runs to list.",
    )
    evals_runs_parser.set_defaults(handler=_run_eval_runs)

    evals_show_parser = evals_subparsers.add_parser("show", help="Show one persisted public eval run.")
    evals_show_parser.add_argument("eval_run_id", type=_parse_uuid, help="Eval run UUID.")
    evals_show_parser.set_defaults(handler=_run_eval_show)

    return parser


def _validate_limit(value: int, *, option_name: str, minimum: int, maximum: int) -> None:
    if value < minimum or value > maximum:
        raise ValueError(f"{option_name} must be between {minimum} and {maximum}")


def _validate_arguments(args: argparse.Namespace) -> None:
    if args.command == "mutations" and args.mutations_command in {"candidates", "operations"}:
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=100,
        )
    elif args.command == "recall":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_RECALL_LIMIT,
        )
    elif args.command == "contradictions" and args.contradictions_command in {"detect", "list"}:
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_REVIEW_LIMIT,
        )
    elif args.command == "trust" and args.trust_command == "signals":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_CONTINUITY_REVIEW_LIMIT,
        )
    elif args.command == "evals" and args.evals_command == "runs":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=100,
        )
    elif args.command == "timeline":
        _validate_limit(
            args.limit,
            option_name="--limit",
            minimum=1,
            maximum=MAX_TEMPORAL_TIMELINE_LIMIT,
        )
    elif args.command == "brief":
        _validate_limit(
            args.max_relevant_facts,
            option_name="--max-relevant-facts",
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
        )
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
        _validate_limit(
            args.max_conflicts,
            option_name="--max-conflicts",
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
        )
        _validate_limit(
            args.max_timeline_highlights,
            option_name="--max-timeline-highlights",
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
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
    elif args.command == "task-briefs" and args.task_briefs_command in {"compile", "compare"}:
        if args.token_budget is not None:
            _validate_limit(
                args.token_budget,
                option_name="--token-budget",
                minimum=1,
                maximum=MAX_TASK_BRIEF_TOKEN_BUDGET,
            )
        if args.task_briefs_command == "compare" and args.compare_token_budget is not None:
            _validate_limit(
                args.compare_token_budget,
                option_name="--compare-token-budget",
                minimum=1,
                maximum=MAX_TASK_BRIEF_TOKEN_BUDGET,
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
        ContinuityBriefValidationError,
        ContinuityResumptionValidationError,
        ContinuityOpenLoopValidationError,
        ContinuityReviewValidationError,
        ContinuityReviewNotFoundError,
        ContinuityContradictionValidationError,
        ContinuityContradictionNotFoundError,
        ContinuityEvidenceNotFoundError,
        MemoryMutationValidationError,
        TaskBriefNotFoundError,
        TaskBriefValidationError,
        TemporalStateValidationError,
        TrustedFactPromotionNotFoundError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


__all__ = ["build_parser", "main"]

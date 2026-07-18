from __future__ import annotations

import argparse
from alicebot_api.cli_formatting import (
    format_artifact_detail_output,
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
from alicebot_api.continuity_brief import compile_continuity_brief
from alicebot_api.continuity_evidence import build_continuity_explain, get_continuity_artifact_detail
from alicebot_api.continuity_contradictions import (
    get_contradiction_case,
    list_contradiction_cases,
    resolve_contradiction_case,
    sync_contradictions,
)
from alicebot_api.memory_mutations import (
    commit_memory_operations,
    generate_memory_operation_candidates,
    list_memory_operation_candidates,
    list_memory_operations,
)
from alicebot_api.continuity_objects import default_continuity_promotable, default_continuity_searchable
from alicebot_api.continuity_lifecycle import get_continuity_lifecycle_state, list_continuity_lifecycle_state
from alicebot_api.continuity_open_loops import compile_continuity_open_loop_dashboard
from alicebot_api.conversation_health import get_thread_health_dashboard
from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.continuity_review import (
    apply_continuity_correction,
    get_continuity_review_detail,
    list_continuity_review_queue,
)
from alicebot_api.continuity_trust import list_trust_signals
from alicebot_api.memory import get_memory_hygiene_dashboard_summary
from alicebot_api.contracts import (
    ContradictionCaseListQueryInput,
    ContradictionResolveInput,
    ContradictionSyncInput,
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
from alicebot_api.task_briefing import compare_task_briefs, compile_and_persist_task_brief, get_persisted_task_brief
from alicebot_api.db import ping_database
from alicebot_api.retrieval_evaluation import get_retrieval_evaluation_summary
from alicebot_api.temporal_state import get_temporal_explain, get_temporal_state_at, get_temporal_timeline
from alicebot_api.trusted_fact_promotions import (
    get_trusted_fact_pattern,
    get_trusted_fact_playbook,
    list_trusted_fact_patterns,
    list_trusted_fact_playbooks,
)
from .models import CLIContext
from .arguments import _parse_optional_json_object
from .shared import _load_maintenance_status_snapshot, _store_context


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
        thread_id=args.thread_id,
        task_id=args.task_id,
        project=args.project,
        person=args.person,
        since=args.since,
        until=args.until,
        include_non_promotable_facts=args.include_non_promotable_facts,
        provider_strategy=args.provider_strategy,
        briefing_strategy=args.briefing_strategy,
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
        thread_id=args.thread_id,
        task_id=args.task_id,
        project=args.project,
        person=args.person,
        since=args.since,
        until=args.until,
        include_non_promotable_facts=args.include_non_promotable_facts,
        provider_strategy=args.provider_strategy,
        briefing_strategy=args.compare_briefing_strategy or args.briefing_strategy,
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
    return format_contradiction_case_detail_output({"contradiction_case": payload["contradiction_case"]})


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
            temporal_payload = get_temporal_explain(
                store,
                user_id=ctx.user_id,
                request=TemporalExplainQueryInput(
                    entity_id=args.entity_id,
                    at=args.at,
                ),
            )
        return format_temporal_explain_output(temporal_payload)

    if args.continuity_object_id is None:
        raise ValueError("explain requires either a continuity_object_id or --entity-id")

    with _store_context(ctx) as store:
        continuity_payload = build_continuity_explain(
            store,
            user_id=ctx.user_id,
            continuity_object_id=args.continuity_object_id,
        )
    return format_explain_output(continuity_payload)


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
        "memory_hygiene_posture": "unknown",
        "memory_duplicate_groups": 0,
        "memory_stale_facts": 0,
        "memory_unresolved_contradictions": 0,
        "memory_weak_trust": 0,
        "memory_review_queue_pressure": "unknown",
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
        "thread_health_posture": "unknown",
        "threads_recent": 0,
        "threads_stale": 0,
        "threads_risky": 0,
        "threads_watch": 0,
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
        memory_hygiene = get_memory_hygiene_dashboard_summary(
            store,
            user_id=ctx.user_id,
        )["dashboard"]
        thread_health = get_thread_health_dashboard(
            store,
            user_id=ctx.user_id,
        )["dashboard"]

        status_payload.update(
            {
                "memory_hygiene_posture": memory_hygiene["posture"],
                "memory_duplicate_groups": memory_hygiene["duplicate_group_count"],
                "memory_stale_facts": memory_hygiene["stale_fact_count"],
                "memory_unresolved_contradictions": memory_hygiene["unresolved_contradiction_count"],
                "memory_weak_trust": memory_hygiene["weak_trust_count"],
                "memory_review_queue_pressure": memory_hygiene["review_queue_pressure"]["posture"],
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
                "thread_health_posture": thread_health["posture"],
                "threads_recent": thread_health["recent_thread_count"],
                "threads_stale": thread_health["stale_thread_count"],
                "threads_risky": thread_health["risky_thread_count"],
                "threads_watch": thread_health["watch_thread_count"],
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

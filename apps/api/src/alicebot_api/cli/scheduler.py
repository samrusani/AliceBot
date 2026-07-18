from __future__ import annotations

import argparse
from pathlib import Path
from alicebot_api.vnext_agent_control import ensure_policy_allowed
from alicebot_api.vnext_scheduler import SchedulerRunRequest
from alicebot_api.vnext_scheduler_runtime import (
    SchedulerRuntimeConfig,
    daemon_status,
    run_due_workflows_durable,
    run_foreground_daemon,
    run_now_durable,
    start_background_daemon,
    stop_daemon,
)
from .errors import PartialCommandFailure
from .models import CLIContext
from .context import _model_generation_options_from_args
from .shared import _json_dumps, _scheduler_service, _vnext_policy_checked_for_args, _vnext_store_context


def _run_vnext_scheduler_status(ctx: CLIContext, _args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        payload = _scheduler_service(store).status()
    return _json_dumps(payload)


def _run_vnext_scheduler_runs(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        runs = store.list_scheduler_runs(workflow_type=args.workflow_type, limit=args.limit)
    return _json_dumps({"items": runs, "count": len(runs)})


def _run_vnext_scheduler_failures(ctx: CLIContext, args: argparse.Namespace) -> str:
    with _vnext_store_context(ctx) as store:
        runs = [
            run
            for run in store.list_scheduler_runs(
                workflow_type=args.workflow_type, limit=max(args.limit * 4, args.limit)
            )
            if run.get("status") == "failed"
        ][: args.limit]
    return _json_dumps({"items": runs, "count": len(runs)})


def _run_vnext_scheduler_run_now(ctx: CLIContext, args: argparse.Namespace) -> str:
    blocked_decision = None
    decision = None
    scheduler_request: SchedulerRunRequest | None = None
    with _vnext_store_context(ctx) as store:
        identity, actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="scheduler.run_now",
            domains=tuple(args.domain),
            workflow_type=args.workflow_type,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            scheduler_request = SchedulerRunRequest(
                workflow_type=args.workflow_type,
                domains=decision.effective_domains,
                projects=decision.effective_project_scope,
                sensitivity_allowed=decision.effective_sensitivity_allowed,
                generated_for=args.generated_for,
                triggered_by=actor_type,
                agent_identity=identity,
                policy_decision=decision,
                options=_model_generation_options_from_args(args),
            )
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if scheduler_request is None or decision is None:
        raise RuntimeError("scheduler run-now did not complete")
    payload = run_now_durable(
        database_url=ctx.database_url,
        user_id=ctx.user_id,
        request=scheduler_request,
    )
    output = _json_dumps({**payload, "policy_decision": decision.to_record()})
    run_record = payload.get("run")
    if isinstance(run_record, dict) and run_record.get("status") == "failed":
        raise PartialCommandFailure(output)
    return output


def _run_vnext_scheduler_run_due(ctx: CLIContext, args: argparse.Namespace) -> str:
    blocked_decision = None
    decision = None
    identity = None
    actor_type = "scheduler"
    with _vnext_store_context(ctx) as store:
        identity, actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="scheduler.run_due",
        )
        if decision.decision == "blocked":
            blocked_decision = decision
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if decision is None:
        raise RuntimeError("scheduler run-due did not complete")
    payload = run_due_workflows_durable(
        database_url=ctx.database_url,
        user_id=ctx.user_id,
        limit=args.limit,
        triggered_by=actor_type if identity is not None else "scheduler",
        agent_identity=identity,
        policy_decision=decision,
    )
    output = _json_dumps({**payload, "policy_decision": decision.to_record()})
    if payload.get("failed_count", 0):
        raise PartialCommandFailure(output)
    return output


def _scheduler_runtime_config(ctx: CLIContext, args: argparse.Namespace) -> SchedulerRuntimeConfig:
    return SchedulerRuntimeConfig(
        database_url=ctx.database_url,
        user_id=ctx.user_id,
        interval_seconds=args.interval_seconds,
        limit=args.limit,
        pid_file=Path(args.pid_file),
        status_file=Path(args.status_file),
        log_file=Path(args.log_file),
        once=getattr(args, "once", False),
    )


def _run_vnext_scheduler_daemon_start(ctx: CLIContext, args: argparse.Namespace) -> str:
    config = _scheduler_runtime_config(ctx, args)
    if args.foreground:
        payload = run_foreground_daemon(config)
        output = _json_dumps(payload)
        if payload.get("exit_code") not in {None, 0} or (config.once and payload.get("last_error") not in {None, ""}):
            raise PartialCommandFailure(output)
        return output
    return _json_dumps(start_background_daemon(config))


def _run_vnext_scheduler_daemon_status(_ctx: CLIContext, args: argparse.Namespace) -> str:
    return _json_dumps(daemon_status(pid_file=Path(args.pid_file), status_file=Path(args.status_file)))


def _run_vnext_scheduler_daemon_stop(_ctx: CLIContext, args: argparse.Namespace) -> str:
    return _json_dumps(stop_daemon(pid_file=Path(args.pid_file), status_file=Path(args.status_file)))


def _run_vnext_scheduler_pause(ctx: CLIContext, args: argparse.Namespace) -> str:
    blocked_decision = None
    payload = None
    decision = None
    with _vnext_store_context(ctx) as store:
        _identity, actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="scheduler.pause",
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = _scheduler_service(store).pause_all(actor_type=actor_type)
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if payload is None or decision is None:
        raise RuntimeError("scheduler pause did not complete")
    return _json_dumps({**payload, "policy_decision": decision.to_record()})


def _run_vnext_scheduler_resume(ctx: CLIContext, args: argparse.Namespace) -> str:
    blocked_decision = None
    payload = None
    decision = None
    with _vnext_store_context(ctx) as store:
        _identity, actor_type, _actor_id, decision = _vnext_policy_checked_for_args(
            store,
            args,
            action="scheduler.resume",
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = _scheduler_service(store).resume_all(actor_type=actor_type)
    if blocked_decision is not None:
        ensure_policy_allowed(blocked_decision)
    if payload is None or decision is None:
        raise RuntimeError("scheduler resume did not complete")
    return _json_dumps({**payload, "policy_decision": decision.to_record()})

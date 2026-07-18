from __future__ import annotations

import argparse
import json
from alicebot_api.public_evals import (
    get_public_eval_run,
    list_public_eval_runs,
    list_public_eval_suites,
    run_public_evals,
    write_public_eval_report,
)
from alicebot_api.vnext_evals import run_vnext_evals, write_vnext_benchmark_corpus, write_vnext_eval_report
from .errors import EvalGateFailure
from .models import CLIContext
from .shared import _store_context


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
        result: dict[str, object] = {**payload, "written_report_path": str(written_path)}
        return json.dumps(result, indent=2, sort_keys=True)
    return json.dumps(payload, indent=2, sort_keys=True)


def _run_vnext_eval_seed(_ctx: CLIContext, args: argparse.Namespace) -> str:
    written_path = write_vnext_benchmark_corpus(args.output_path)
    return json.dumps(
        {
            "status": "seeded",
            "written_corpus_path": str(written_path),
        },
        indent=2,
        sort_keys=True,
    )


def _run_vnext_eval_run(_ctx: CLIContext, args: argparse.Namespace) -> str:
    report = run_vnext_evals(
        suite=args.suite,
        corpus_path=args.corpus_path,
        release_gate=args.release_gate,
    )
    payload: dict[str, object] = {"report": report}
    if args.report_path is not None:
        payload["written_report_path"] = str(
            write_vnext_eval_report(
                report=report,
                report_path=args.report_path,
            )
        )
    output = json.dumps(payload, indent=2, sort_keys=True)
    # Propagate the report verdict to the process exit code. A release gate
    # must also fail when any requested suite skipped; otherwise a partially
    # unavailable store can turn incomplete evidence into a green release.
    # Non-release dev runs preserve the informational zero exit for an honestly
    # labelled skip.
    report_status = report.get("status")
    summary = report.get("summary")
    release_has_skips = args.release_gate and (not isinstance(summary, dict) or summary.get("skipped_suite_count") != 0)
    if report_status not in {"pass", "skipped"} or (
        args.release_gate and (report_status == "skipped" or release_has_skips)
    ):
        raise EvalGateFailure(output)
    return output


def _run_vnext_eval_report(_ctx: CLIContext, args: argparse.Namespace) -> str:
    report = run_vnext_evals(
        suite=args.suite,
        corpus_path=args.corpus_path,
    )
    written_path = write_vnext_eval_report(
        report=report,
        report_path=args.report_path,
    )
    return json.dumps(
        {
            "report": report,
            "written_report_path": str(written_path),
        },
        indent=2,
        sort_keys=True,
    )

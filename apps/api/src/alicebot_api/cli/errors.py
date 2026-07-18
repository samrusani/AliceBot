from __future__ import annotations

import json
import sys


def _emit_cli_error(*, code: str, message: str) -> None:
    """Write the versioned CLI failure contract without exception internals."""

    print(
        json.dumps(
            {"error": {"code": code, "message": message}},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ),
        file=sys.stderr,
        flush=True,
    )


class EvalGateFailure(Exception):
    """A handler produced a report whose status is not a pass.

    Carries the already-serialized JSON ``output`` so ``main()`` can still honor
    the output contract (JSON to stdout) while mapping the failure to a nonzero
    process exit code -- decoupling the eval verdict from a hard-coded exit 0.
    """

    def __init__(self, output: str) -> None:
        super().__init__("eval report status is not a pass")
        self.output = output


class EmbeddingBackfillFailure(Exception):
    """A backfill completed with failed rows and must exit nonzero."""

    def __init__(self, output: str) -> None:
        super().__init__("embedding backfill completed with failures")
        self.output = output


class PartialCommandFailure(Exception):
    """A batch command produced useful JSON output but did not fully succeed."""

    def __init__(self, output: str) -> None:
        super().__init__("command completed with failed items")
        self.output = output

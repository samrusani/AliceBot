#!/usr/bin/env python3
"""Score Alice on LongMemEval (Wu et al., ICLR 2025).

Thin entry point: puts ``eval/`` (the harness package) and ``apps/api/src``
(the alicebot_api package, for use outside the venv's editable install) on
``sys.path`` and delegates to ``longmemeval.runner``.

Quick start (see docs/plans/longmemeval.md for the full contract):

    .venv/bin/python eval/longmemeval/fetch.py --variant s
    .venv/bin/python scripts/run_longmemeval.py --dry-run
    ALICE_LME_MODEL_BASE_URL=https://api.openai.com/v1 \
    ALICE_LME_MODEL=gpt-4o-mini \
    ALICE_LME_MODEL_API_KEY=... \
      .venv/bin/python scripts/run_longmemeval.py --variant s --resume --workers 4
"""

from __future__ import annotations

from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _path in (_REPO_ROOT / "eval", _REPO_ROOT / "apps" / "api" / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from longmemeval.runner import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

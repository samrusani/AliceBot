from __future__ import annotations

import logging
import os
from uuid import UUID

from alicebot_api.config import get_settings
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore

from alicebot_worker.task_runs import acquire_and_tick_one_task_run


LOGGER = logging.getLogger("alicebot.worker")
WORKER_USER_ID_ENV = "ALICEBOT_WORKER_USER_ID"


def _read_worker_user_id() -> UUID | None:
    raw_value = os.getenv(WORKER_USER_ID_ENV)
    if not raw_value:
        LOGGER.info(
            "Worker tick skipped because %s is not configured.",
            WORKER_USER_ID_ENV,
        )
        return None

    try:
        return UUID(raw_value)
    except ValueError:
        LOGGER.error(
            "Worker tick skipped because %s is not a valid UUID.",
            WORKER_USER_ID_ENV,
        )
        return None


def run() -> None:
    worker_user_id = _read_worker_user_id()
    if worker_user_id is None:
        return

    settings = get_settings()
    with user_connection(settings.database_url, worker_user_id) as conn:
        outcome = acquire_and_tick_one_task_run(
            ContinuityStore(conn),
            user_id=worker_user_id,
        )

    if outcome is None:
        LOGGER.info("Worker tick completed with no runnable task runs.")
        return

    LOGGER.info(
        "Worker ticked task run %s from %s to %s (stop_reason=%s).",
        outcome.task_run_id,
        outcome.previous_status,
        outcome.status,
        outcome.stop_reason,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()

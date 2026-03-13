from __future__ import annotations

import logging


LOGGER = logging.getLogger("alicebot.worker")


def run() -> None:
    LOGGER.info("Worker scaffold initialized; no background jobs are in scope for this sprint.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()

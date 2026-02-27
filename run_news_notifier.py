#!/usr/bin/env python3
"""
Entrypoint for TradingEconomics news → Discord notifier.
Loads config from .env, runs fetch + notify + state persist.
Run once, in a loop, or via cron/launchd (e.g. every 5 minutes).
"""

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

from news_notifier import run

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 900  # 15 minutes


def main() -> None:
    parser = argparse.ArgumentParser(description="TradingEconomics news → Discord notifier.")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run in a loop: fetch + notify, then sleep for INTERVAL seconds, repeat.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("NOTIFIER_INTERVAL_SECONDS", DEFAULT_INTERVAL)),
        metavar="SECONDS",
        help="Loop interval in seconds (default: 900). Env: NOTIFIER_INTERVAL_SECONDS.",
    )
    args = parser.parse_args()

    if args.loop:
        if args.interval < 60:
            logger.warning("Interval %s is under 60s; using 60s to respect rate limits.", args.interval)
            args.interval = 60
        logger.info("Running in loop every %s seconds (Ctrl+C to stop).", args.interval)
        while True:
            run()
            time.sleep(args.interval)
    else:
        run()


if __name__ == "__main__":
    main()

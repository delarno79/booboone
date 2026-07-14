"""Booboone Auto-Blog — command-line entrypoint.

Examples
--------
    python main.py                 # generate + publish one article per category
    python main.py --dry-run       # generate articles but publish nothing
    python main.py --limit 3       # only publish 3 posts this run
    python main.py --category "Beauty & Fashion"
    python main.py --status        # show remaining keywords per category
"""

from __future__ import annotations

import argparse
import sys

from autoblog.config import Config, ConfigError
from autoblog.logging_setup import setup_logging
from autoblog.runner import run
from autoblog.tracker import KeywordTracker


def main() -> int:
    parser = argparse.ArgumentParser(description="Booboone Auto-Blog publisher")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate articles but do not upload or publish anything.",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max posts to publish this run."
    )
    parser.add_argument(
        "--category", default=None, help="Only process this single category."
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print remaining keyword counts per category and exit.",
    )
    args = parser.parse_args()

    cfg = Config.from_env()
    setup_logging(cfg.log_dir)

    if args.status:
        try:
            tracker = KeywordTracker(cfg.keywords_file, cfg.state_file)
        except FileNotFoundError as err:
            print(err)
            return 1
        remaining = tracker.remaining()
        print("Remaining keywords per category:")
        for category, count in remaining.items():
            total = len(tracker.keywords[category])
            print(f"  - {category}: {count} left of {total}")
        print(f"Total remaining: {tracker.total_remaining()}")
        return 0

    try:
        result = run(
            cfg,
            dry_run=args.dry_run,
            only_category=args.category,
            limit=args.limit,
        )
    except ConfigError as err:
        print(f"\n[CONFIG ERROR] {err}\n")
        print("Copy .env.example to .env and fill in the values.")
        return 1
    except FileNotFoundError as err:
        print(f"\n[ERROR] {err}\n")
        return 1

    return 0 if result["failed"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

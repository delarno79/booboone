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
from datetime import datetime, timezone
from pathlib import Path

from autoblog.config import Config, ConfigError
from autoblog.logging_setup import setup_logging
from autoblog.runner import run
from autoblog.tracker import KeywordTracker


def _write_status(log_dir: Path, published: int, failed: int, note: str) -> None:
    """Append one easy-to-read line per run to logs/status.log for at-a-glance
    monitoring (e.g. '2026-07-27 12:00 UTC | Published 13 | Failed 0 | OK')."""
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with open(log_dir / "status.log", "a", encoding="utf-8") as fh:
            fh.write(
                f"{stamp}  |  Published {published:>2}  |  Failed {failed:>2}  |  {note}\n"
            )
    except Exception:  # noqa: BLE001 - status logging must never break a run
        pass


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
        _write_status(cfg.log_dir, 0, 0, "FAIL (configuration)")
        return 1
    except FileNotFoundError as err:
        print(f"\n[ERROR] {err}\n")
        _write_status(cfg.log_dir, 0, 0, "FAIL (missing file)")
        return 1
    except Exception as err:  # noqa: BLE001 - record the failure, then surface it
        _write_status(cfg.log_dir, 0, 0, f"FAIL ({type(err).__name__})")
        raise

    published, failed = result["published"], result["failed"]
    note = "OK" if failed == 0 and published > 0 else (
        "PARTIAL" if published > 0 else "FAIL (nothing published)"
    )
    _write_status(cfg.log_dir, published, failed, note)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

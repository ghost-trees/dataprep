"""Command-line interface for running the fee scraping pipeline."""

import argparse
from pathlib import Path

from dataprep.shared.db import DEFAULT_DB_PATH

from .pipeline import run


def positive_int(value: str) -> int:
    """Parse and validate a positive integer CLI argument."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("Value must be >= 1.")
    return parsed


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for fee scraping."""
    parser = argparse.ArgumentParser(
        description="Scrape paid/outstanding fees for records from the geocoded_records table."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--limit", type=int, default=None, help="Only scrape the first N records.")
    parser.add_argument(
        "--workers",
        type=positive_int,
        default=5,
        help="Number of parallel worker processes (default: 5).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window (useful for debugging).",
    )
    return parser.parse_args()


def main() -> None:
    """Run the fee scraping pipeline using parsed CLI arguments."""
    args = parse_args()
    run(
        db_path=args.db,
        headless=not args.headed,
        limit=args.limit,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()

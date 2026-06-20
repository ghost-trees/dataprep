"""Command-line interface for running the fee scraping pipeline."""

import argparse
from pathlib import Path

from dataprep.shared.db import DEFAULT_DB_PATH

from .pipeline import run


class _HelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Render defaults and preserve multiline examples in help output."""


def positive_int(value: str) -> int:
    """Parse and validate a positive integer CLI argument."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("Value must be >= 1.")
    return parsed


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for fee scraping."""
    parser = argparse.ArgumentParser(
        description=(
            "Scrape paid/outstanding fee data for geocoded records and write/"
            "upsert rows into the scraped_fees SQLite table."
        ),
        epilog=(
            "Quickstart examples:\n"
            "  uv run python -m dataprep.pipelines.fees.cli\n"
            "  uv run python -m dataprep.pipelines.fees.cli --workers 8 --limit 200"
        ),
        formatter_class=_HelpFormatter,
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on the number of records to scrape.",
    )
    parser.add_argument(
        "--workers",
        type=positive_int,
        default=5,
        help="Number of parallel worker processes to run.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window. By default, browsers run headless.",
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

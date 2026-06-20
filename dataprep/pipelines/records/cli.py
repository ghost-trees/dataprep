"""CLI for record scraping pipeline."""

import argparse
from pathlib import Path

from dataprep.shared.db import DEFAULT_DB_PATH

from .pipeline import DEFAULT_END_DATE, DEFAULT_START_DATE, PERMIT_TYPE, run


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for record scraping."""
    parser = argparse.ArgumentParser(description="Scrape permit records from ACA portal.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--permit-type", default=PERMIT_TYPE)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: headed).",
    )
    return parser.parse_args()


def main() -> None:
    """Run record scraping pipeline from CLI args."""
    args = parse_args()
    run(
        db_path=args.db,
        permit_type=args.permit_type,
        start_date=args.start_date,
        end_date=args.end_date,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()

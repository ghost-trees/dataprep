"""CLI for record scraping pipeline."""

import argparse
from pathlib import Path

from dataprep.shared.db import DEFAULT_DB_PATH

from .pipeline import DEFAULT_END_DATE, DEFAULT_START_DATE, PERMIT_TYPE, run


class _HelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Render defaults and preserve multiline examples in help output."""


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for record scraping."""
    parser = argparse.ArgumentParser(
        description=(
            "Scrape permit records from the ACA portal and merge/upsert rows "
            "into the scraped_records SQLite table."
        ),
        epilog=(
            "Quickstart examples:\n"
            "  uv run python -m dataprep.pipelines.scrape_records.cli\n"
            "  uv run python -m dataprep.pipelines.scrape_records.cli --headless "
            "--start-date 01/01/2024 --end-date 12/31/2024"
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
        "--permit-type",
        default=PERMIT_TYPE,
        help="ACA permit type filter passed to the portal search form.",
    )
    parser.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help="Inclusive search start date in MM/DD/YYYY format.",
    )
    parser.add_argument(
        "--end-date",
        default=DEFAULT_END_DATE,
        help="Inclusive search end date in MM/DD/YYYY format.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode. By default, the browser is headed.",
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

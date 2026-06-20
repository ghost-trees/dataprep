"""CLI for geocode pipeline."""

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
    """Build and parse command-line arguments for geocoding.

    Returns:
        Parsed arguments including the database path, worker count, and
        whether to force a full rerun.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Geocode addresses from scraped_records and write/upsert rows into "
            "the geocoded_records SQLite table."
        ),
        epilog=(
            "Quickstart examples:\n"
            "  uv run python -m dataprep.pipelines.geocode.cli\n"
            "  uv run python -m dataprep.pipelines.geocode.cli --workers 4 --redo-all"
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
        "--workers",
        type=positive_int,
        default=1,
        help="Number of parallel worker processes to run.",
    )
    parser.add_argument(
        "--redo-all",
        action="store_true",
        help=(
            "Re-geocode every eligible input row. By default, successful prior "
            "results are reused when record_number and address are unchanged."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Run geocode pipeline from CLI args."""
    args = parse_args()
    updated_df = run(
        db_path=args.db,
        workers=args.workers,
        redo_all=args.redo_all,
    )
    print(f"Geocoded {len(updated_df)} records into the geocoded_records table.")


if __name__ == "__main__":
    main()

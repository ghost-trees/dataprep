"""CLI for geocode pipeline."""

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
    """Build and parse command-line arguments for geocoding.

    Returns:
        Parsed arguments including the database path, worker count, and
        whether to force a full rerun.
    """
    parser = argparse.ArgumentParser(
        description="Geocode record addresses from the scraped_records table."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--workers",
        type=positive_int,
        default=1,
        help="Number of parallel worker processes (default: 1).",
    )
    parser.add_argument(
        "--redo-all",
        action="store_true",
        help=(
            "Redo geocoding for every input record. By default, previously "
            "successful rows are reused when record_number and address are unchanged."
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

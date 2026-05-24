"""CLI for geocode pipeline."""

import argparse
from pathlib import Path

from dataprep.shared.paths import GEOCODED_RECORDS_PATH, SCRAPED_RECORDS_PATH

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
        Parsed arguments including input/output paths, worker count, and
        whether to force a full rerun.
    """
    parser = argparse.ArgumentParser(description="Geocode record addresses from scraped_records.csv.")
    parser.add_argument("--input", type=Path, default=SCRAPED_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=GEOCODED_RECORDS_PATH)
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
        input_csv_path=args.input,
        output_csv_path=args.output,
        workers=args.workers,
        redo_all=args.redo_all,
    )
    print(f"Geocoded {len(updated_df)} records and saved to {args.output.as_posix()}")


if __name__ == "__main__":
    main()

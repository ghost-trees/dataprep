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
    """Build and parse command-line arguments for geocoding."""
    parser = argparse.ArgumentParser(description="Geocode record addresses from scraped_records.csv.")
    parser.add_argument("--input", type=Path, default=SCRAPED_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=GEOCODED_RECORDS_PATH)
    parser.add_argument(
        "--workers",
        type=positive_int,
        default=1,
        help="Number of parallel worker processes (default: 1).",
    )
    return parser.parse_args()


def main() -> None:
    """Run geocode pipeline from CLI args."""
    args = parse_args()
    updated_df = run(input_csv_path=args.input, output_csv_path=args.output, workers=args.workers)
    print(f"Geocoded {len(updated_df)} records and saved to {args.output.as_posix()}")


if __name__ == "__main__":
    main()

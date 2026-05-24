"""CLI for parse-trees pipeline."""

import argparse
from pathlib import Path

from dataprep.shared.paths import PARSED_TREES_PATH, SCRAPED_RECORDS_PATH

from .pipeline import run


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for parse-trees extraction.

    Returns:
        Parsed CLI arguments containing input and output CSV paths.
    """
    parser = argparse.ArgumentParser(
        description="Parse and normalize tree types from scraped_records.csv text fields."
    )
    parser.add_argument("--input", type=Path, default=SCRAPED_RECORDS_PATH)
    parser.add_argument("--output", type=Path, default=PARSED_TREES_PATH)
    return parser.parse_args()


def main() -> None:
    """Run parse-trees pipeline from CLI args."""
    args = parse_args()
    updated_df = run(input_csv_path=args.input, output_csv_path=args.output)
    print(f"Parsed tree types for {len(updated_df)} records and saved to {args.output.as_posix()}")


if __name__ == "__main__":
    main()

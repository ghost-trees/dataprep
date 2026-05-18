"""Command-line interface for running the fee scraping pipeline."""

import argparse
from pathlib import Path

from .pipeline import run


def positive_int(value: str) -> int:
    """Parse and validate a positive integer CLI argument.

    Args:
        value: Raw CLI string value.

    Returns:
        Parsed integer value.

    Raises:
        argparse.ArgumentTypeError: If the parsed value is less than 1.
        ValueError: If the input cannot be parsed as an integer.
    """

    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("Value must be >= 1.")
    return parsed


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for fee scraping.

    Returns:
        Parsed argument namespace used by the pipeline entrypoint.
    """

    parser = argparse.ArgumentParser(
        description="Scrape paid/outstanding fees for records from geocoded_records.csv."
    )
    parser.add_argument("--input", type=Path, default=Path("geocoded_records.csv"))
    parser.add_argument("--output", type=Path, default=Path("fees_output.csv"))
    parser.add_argument(
        "--limit", type=int, default=None, help="Only scrape the first N records."
    )
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
        input_csv=args.input,
        output_csv=args.output,
        headless=not args.headed,
        limit=args.limit,
        workers=args.workers,
    )

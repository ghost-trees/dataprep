"""CLI entrypoint for full dataprep pipeline."""

import argparse
import sys
from pathlib import Path

from dataprep.orchestrator import run_pipeline
from dataprep.shared.paths import (
    GEOCODED_RECORDS_PATH,
    OUTPUT_PATH,
    SCRAPED_FEES_PATH,
    SCRAPED_RECORDS_PATH,
)


def positive_int(value: str) -> int:
    """Parse and validate a positive integer CLI argument."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("Value must be >= 1.")
    return parsed


def parse_args() -> argparse.Namespace:
    """Build and parse top-level pipeline CLI arguments."""
    parser = argparse.ArgumentParser(description="Run the full Ghost Trees dataprep pipeline.")
    parser.add_argument("--scraped-records", type=Path, default=SCRAPED_RECORDS_PATH)
    parser.add_argument("--geocoded-records", type=Path, default=GEOCODED_RECORDS_PATH)
    parser.add_argument("--scraped-fees", type=Path, default=SCRAPED_FEES_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--geocode-workers", type=positive_int, default=1)
    parser.add_argument("--fee-workers", type=positive_int, default=5)
    parser.add_argument("--fees-limit", type=int, default=None)
    parser.add_argument("--fees-headed", action="store_true")
    parser.add_argument("--records-headless", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Run full pipeline from CLI arguments."""
    args = parse_args()
    try:
        run_pipeline(
            scraped_records_path=args.scraped_records,
            geocoded_records_path=args.geocoded_records,
            scraped_fees_path=args.scraped_fees,
            output_path=args.output,
            geocode_workers=args.geocode_workers,
            fee_workers=args.fee_workers,
            fees_headless=not args.fees_headed,
            fees_limit=args.fees_limit,
            records_headless=args.records_headless,
        )
    except Exception as exc:
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

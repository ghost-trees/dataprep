"""CLI entrypoint for full dataprep pipeline."""

import argparse
import sys
from pathlib import Path

from dataprep.orchestrator import run_pipeline
from dataprep.shared.db import DB_PATH
from dataprep.shared.exports import CSV_EXPORT_END, CSV_EXPORT_START
from dataprep.shared.paths import DATA_GEOJSON_PATH


def positive_int(value: str) -> int:
    """Parse and validate a positive integer CLI argument."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("Value must be >= 1.")
    return parsed


def parse_args() -> argparse.Namespace:
    """Build and parse top-level pipeline CLI arguments."""
    parser = argparse.ArgumentParser(description="Run the full Ghost Trees dataprep pipeline.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--output-geojson", type=Path, default=DATA_GEOJSON_PATH)
    parser.add_argument(
        "--start", default=CSV_EXPORT_START, help="Inclusive ISO export window start."
    )
    parser.add_argument("--end", default=CSV_EXPORT_END, help="Inclusive ISO export window end.")
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
            db_path=args.db,
            output_geojson_path=args.output_geojson,
            export_start=args.start,
            export_end=args.end,
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

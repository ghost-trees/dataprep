"""CLI for exporting final GeoJSON output."""

import argparse
from pathlib import Path

from dataprep.shared.paths import (
    DATA_GEOJSON_PATH,
    GEOCODED_RECORDS_PATH,
    PARSED_TREES_PATH,
    SCRAPED_FEES_PATH,
    SCRAPED_RECORDS_PATH,
)

from .pipeline import run


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for GeoJSON export.

    Returns:
        Parsed CLI arguments for source CSV and output GeoJSON paths.
    """
    parser = argparse.ArgumentParser(description="Build data.geojson from pipeline CSV outputs.")
    parser.add_argument("--scraped-records", type=Path, default=SCRAPED_RECORDS_PATH)
    parser.add_argument("--geocoded-records", type=Path, default=GEOCODED_RECORDS_PATH)
    parser.add_argument("--scraped-fees", type=Path, default=SCRAPED_FEES_PATH)
    parser.add_argument("--parsed-trees", type=Path, default=PARSED_TREES_PATH)
    parser.add_argument("--output", type=Path, default=DATA_GEOJSON_PATH)
    return parser.parse_args()


def main() -> None:
    """Run GeoJSON export pipeline from CLI arguments."""
    args = parse_args()
    output_path = run(
        scraped_records_path=args.scraped_records,
        geocoded_records_path=args.geocoded_records,
        scraped_fees_path=args.scraped_fees,
        parsed_trees_path=args.parsed_trees,
        output_geojson_path=args.output,
    )
    print(f"GeoJSON export complete: {output_path.as_posix()}")


if __name__ == "__main__":
    main()

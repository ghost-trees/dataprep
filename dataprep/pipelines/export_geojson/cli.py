"""CLI for exporting final GeoJSON output."""

import argparse
from pathlib import Path

from dataprep.shared.db import DEFAULT_DB_PATH
from dataprep.shared.exports import CSV_EXPORT_END, CSV_EXPORT_START
from dataprep.shared.paths import DATA_GEOJSON_PATH

from .pipeline import run


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for GeoJSON export.

    Returns:
        Parsed CLI arguments for the database, output path, and date window.
    """
    parser = argparse.ArgumentParser(description="Build data.geojson from the SQLite database.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--output", type=Path, default=DATA_GEOJSON_PATH)
    parser.add_argument("--start", default=CSV_EXPORT_START, help="Inclusive ISO window start.")
    parser.add_argument("--end", default=CSV_EXPORT_END, help="Inclusive ISO window end.")
    return parser.parse_args()


def main() -> None:
    """Run GeoJSON export pipeline from CLI arguments."""
    args = parse_args()
    output_path = run(
        db_path=args.db,
        output_geojson_path=args.output,
        start=args.start,
        end=args.end,
    )
    print(f"GeoJSON export complete: {output_path.as_posix()}")


if __name__ == "__main__":
    main()

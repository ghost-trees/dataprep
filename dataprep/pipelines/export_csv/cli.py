"""CLI for re-exporting curated CSV snapshots from SQLite."""

import argparse
from pathlib import Path

from dataprep.shared.db import DEFAULT_DB_PATH
from dataprep.shared.exports import CSV_EXPORT_END, CSV_EXPORT_START

from .pipeline import run


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for CSV export."""
    parser = argparse.ArgumentParser(
        description="Re-export curated CSV snapshots from the SQLite database."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--start", default=CSV_EXPORT_START, help="Inclusive ISO window start.")
    parser.add_argument("--end", default=CSV_EXPORT_END, help="Inclusive ISO window end.")
    parser.add_argument(
        "--all",
        dest="export_all",
        action="store_true",
        help="Ignore the date window and dump full tables.",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated subset of export names to run.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the CSV export pipeline from CLI arguments."""
    args = parse_args()
    only = [name.strip() for name in args.only.split(",") if name.strip()] if args.only else None
    written = run(
        db_path=args.db,
        start=args.start,
        end=args.end,
        only=only,
        export_all=args.export_all,
    )
    print(f"CSV export complete. Wrote {len(written)} file(s).")


if __name__ == "__main__":
    main()

"""CLI for parse-trees pipeline."""

import argparse
from pathlib import Path

from dataprep.shared.db import DEFAULT_DB_PATH

from .pipeline import run


def parse_args() -> argparse.Namespace:
    """Build and parse command-line arguments for parse-trees extraction.

    Returns:
        Parsed CLI arguments containing the database path.
    """
    parser = argparse.ArgumentParser(
        description="Parse and normalize tree types from the scraped_records table text fields."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    return parser.parse_args()


def main() -> None:
    """Run parse-trees pipeline from CLI args."""
    args = parse_args()
    updated_df = run(db_path=args.db)
    print(f"Parsed tree types for {len(updated_df)} records into the parsed_trees table.")


if __name__ == "__main__":
    main()

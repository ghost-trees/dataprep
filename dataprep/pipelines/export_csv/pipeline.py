"""Export curated CSV snapshots from the SQLite source of truth.

Pipeline stages write only to SQLite. This step reads the configured tables
back out and writes the human-readable CSVs in ``data/``, defaulting to a
curated date window. The window can be overridden or disabled entirely.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from dataprep.shared.db import DEFAULT_DB_PATH, get_connection, read_table_if_exists
from dataprep.shared.exports import (
    CSV_EXPORT_END,
    CSV_EXPORT_START,
    CSV_EXPORTS,
    CsvExportSpec,
    filter_to_window,
    in_window_record_numbers,
)


def _select_specs(only: Iterable[str] | None) -> list[CsvExportSpec]:
    """Return the export specs to run, optionally filtered by name."""
    if not only:
        return list(CSV_EXPORTS)
    requested = set(only)
    selected = [spec for spec in CSV_EXPORTS if spec.name in requested]
    unknown = requested - {spec.name for spec in CSV_EXPORTS}
    if unknown:
        known = ", ".join(spec.name for spec in CSV_EXPORTS)
        raise ValueError(f"Unknown export name(s): {sorted(unknown)}. Known exports: {known}")
    return selected


def run(
    db_path: Path = DEFAULT_DB_PATH,
    start: str = CSV_EXPORT_START,
    end: str = CSV_EXPORT_END,
    only: Iterable[str] | None = None,
    export_all: bool = False,
) -> list[Path]:
    """Export configured tables from SQLite to their CSV snapshots.

    Args:
        db_path: Path to the SQLite database.
        start: Inclusive ISO (YYYY-MM-DD) window start.
        end: Inclusive ISO (YYYY-MM-DD) window end.
        only: Optional subset of export names to run.
        export_all: When True, ignore the window and dump full tables.

    Returns:
        The list of written CSV paths.
    """
    specs = _select_specs(only)
    written: list[Path] = []

    connection = get_connection(db_path)
    try:
        window_records = None if export_all else in_window_record_numbers(connection, start, end)

        for spec in specs:
            df = read_table_if_exists(connection, spec.table)
            if df is None:
                print(f"Skipping export '{spec.name}': table '{spec.table}' not found.")
                continue

            if not export_all:
                df = filter_to_window(
                    df,
                    date_column=spec.date_column,
                    window_records=window_records,
                    start=start,
                    end=end,
                )

            if spec.columns:
                df = df[[column for column in spec.columns if column in df.columns]]

            spec.output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(spec.output_path, index=False)
            written.append(spec.output_path)
            print(f"Exported {len(df)} rows to {spec.output_path}")
    finally:
        connection.close()

    return written

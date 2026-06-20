"""I/O and merge helpers for the records pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

import pandas as pd

from dataprep.shared.db import (
    apply_record_number_integrity,
    drop_unnamed_columns,
    normalize_columns,
    read_table_if_exists,
    write_table,
)
from dataprep.shared.normalize import derive_date_iso
from dataprep.shared.schema import RECORD_NUMBER_COLUMN, SCRAPED_RECORDS_TABLE


@dataclass
class RecordsIngestSummary:
    """Operational counts for one records ingest run."""

    downloaded_rows: int
    exact_duplicates_removed: int
    prior_records: int
    overlapping_records: int
    unchanged_records: int
    updated_records: int
    new_records: int
    preserved_records: int
    total_written: int


def prepare_scraped_records_df(csv_path: Path) -> pd.DataFrame:
    """Load and normalize downloaded records data."""
    df = pd.read_csv(csv_path)
    df = derive_date_iso(df)
    df = normalize_columns(df)
    df = drop_unnamed_columns(df)
    return apply_record_number_integrity(df, "scraped_records")


def read_existing_scraped_records(connection: sqlite3.Connection) -> pd.DataFrame | None:
    """Read existing scraped_records rows if the table exists."""
    existing_df = read_table_if_exists(connection, SCRAPED_RECORDS_TABLE)
    if existing_df is None:
        return None
    existing_df = normalize_columns(existing_df)
    existing_df = drop_unnamed_columns(existing_df)
    return apply_record_number_integrity(existing_df, "scraped_records")


def _rows_equal(left: pd.Series, right: pd.Series, columns: list[str]) -> bool:
    """Return True when two rows are value-equal for the selected columns."""
    for column in columns:
        left_value = left.get(column)
        right_value = right.get(column)
        if pd.isna(left_value) and pd.isna(right_value):
            continue
        if left_value != right_value:
            return False
    return True


def merge_scraped_records(
    existing_df: pd.DataFrame | None, scrape_df: pd.DataFrame
) -> tuple[pd.DataFrame, RecordsIngestSummary]:
    """Merge a scrape over existing rows while preserving record order."""
    if existing_df is None or existing_df.empty:
        summary = RecordsIngestSummary(
            downloaded_rows=len(scrape_df),
            exact_duplicates_removed=0,
            prior_records=0,
            overlapping_records=0,
            unchanged_records=0,
            updated_records=0,
            new_records=len(scrape_df),
            preserved_records=0,
            total_written=len(scrape_df),
        )
        return scrape_df.copy(), summary

    existing_by_record = {
        str(row[RECORD_NUMBER_COLUMN]): row for _, row in existing_df.iterrows()
    }
    scrape_records: set[str] = set()
    merged_rows: list[dict[str, object]] = []

    overlapping_records = 0
    unchanged_records = 0
    updated_records = 0
    new_records = 0

    shared_columns = [
        column for column in scrape_df.columns if column in existing_df.columns
    ]

    for _, scrape_row in scrape_df.iterrows():
        record_number = str(scrape_row[RECORD_NUMBER_COLUMN])
        scrape_records.add(record_number)
        existing_row = existing_by_record.get(record_number)
        if existing_row is None:
            new_records += 1
            merged_rows.append(scrape_row.to_dict())
            continue

        overlapping_records += 1
        if _rows_equal(existing_row, scrape_row, shared_columns):
            unchanged_records += 1
            merged_rows.append(existing_row.to_dict())
        else:
            updated_records += 1
            merged_rows.append(scrape_row.to_dict())

    preserved_records = 0
    for _, existing_row in existing_df.iterrows():
        record_number = str(existing_row[RECORD_NUMBER_COLUMN])
        if record_number in scrape_records:
            continue
        preserved_records += 1
        merged_rows.append(existing_row.to_dict())

    output_columns = list(scrape_df.columns)
    output_columns.extend(
        column for column in existing_df.columns if column not in output_columns
    )
    merged_df = pd.DataFrame(merged_rows)
    merged_df = merged_df.reindex(columns=output_columns)

    summary = RecordsIngestSummary(
        downloaded_rows=len(scrape_df),
        exact_duplicates_removed=0,
        prior_records=len(existing_df),
        overlapping_records=overlapping_records,
        unchanged_records=unchanged_records,
        updated_records=updated_records,
        new_records=new_records,
        preserved_records=preserved_records,
        total_written=len(merged_df),
    )
    return merged_df, summary


def ingest_scraped_records_csv(
    connection: sqlite3.Connection,
    csv_path: Path,
    *,
    exact_duplicates_removed: int,
) -> RecordsIngestSummary:
    """Load, merge, and write records CSV into the scraped_records table."""
    existing_df = read_existing_scraped_records(connection)
    scrape_df = prepare_scraped_records_df(csv_path)
    merged_df, summary = merge_scraped_records(existing_df, scrape_df)
    summary.exact_duplicates_removed = exact_duplicates_removed
    written_df = write_table(
        connection,
        SCRAPED_RECORDS_TABLE,
        merged_df,
        dataset_name="scraped_records",
    )
    summary.total_written = len(written_df)
    return summary

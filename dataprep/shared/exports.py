"""Declarative CSV export configuration and shared date-window helpers.

This is the single place that defines which SQLite tables are exported to the
human-readable CSV snapshots in ``data/`` and the default curated date window.
The window helpers are shared by both the CSV export step and the GeoJSON export
so all ``data/`` outputs stay mutually consistent.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .db import read_table_if_exists
from .paths import (
    GEOCODED_RECORDS_PATH,
    OUTPUT_PATH,
    PARSED_TREES_PATH,
    SCRAPED_FEES_PATH,
    SCRAPED_RECORDS_PATH,
)
from .schema import (
    DATE_ISO_COLUMN,
    GEOCODED_RECORDS_TABLE,
    OUTPUT_TABLE,
    PARSED_TREES_TABLE,
    RECORD_NUMBER_COLUMN,
    SCRAPED_FEES_TABLE,
    SCRAPED_RECORDS_TABLE,
)

CSV_EXPORT_START = "2023-01-01"
CSV_EXPORT_END = "2025-12-31"


@dataclass(frozen=True)
class CsvExportSpec:
    """Describe a single CSV export derived from a SQLite table."""

    name: str
    table: str
    output_path: Path
    date_column: str | None = None
    columns: list[str] | None = None


CSV_EXPORTS: list[CsvExportSpec] = [
    CsvExportSpec(
        "scraped_records", SCRAPED_RECORDS_TABLE, SCRAPED_RECORDS_PATH, date_column=DATE_ISO_COLUMN
    ),
    CsvExportSpec("geocoded_records", GEOCODED_RECORDS_TABLE, GEOCODED_RECORDS_PATH),
    CsvExportSpec("scraped_fees", SCRAPED_FEES_TABLE, SCRAPED_FEES_PATH),
    CsvExportSpec("parsed_trees", PARSED_TREES_TABLE, PARSED_TREES_PATH),
    CsvExportSpec("output", OUTPUT_TABLE, OUTPUT_PATH, date_column=DATE_ISO_COLUMN),
]


def _date_in_window_mask(values: pd.Series, start: str, end: str) -> pd.Series:
    """Build a boolean mask for ISO date values falling within [start, end]."""
    present = values.notna()
    as_text = values.astype(str)
    return present & (as_text >= start) & (as_text <= end)


def in_window_record_numbers(
    connection: sqlite3.Connection, start: str, end: str
) -> set[str] | None:
    """Return record numbers whose scraped_records.date_iso is within the window.

    Returns None when no date information is available (no ``scraped_records``
    table or no ``date_iso`` column), signaling that no windowing can be applied.
    """
    records = read_table_if_exists(connection, SCRAPED_RECORDS_TABLE)
    if records is None or DATE_ISO_COLUMN not in records.columns:
        return None
    mask = _date_in_window_mask(records[DATE_ISO_COLUMN], start, end)
    return set(records.loc[mask, RECORD_NUMBER_COLUMN].astype(str))


def filter_to_window(
    df: pd.DataFrame,
    *,
    date_column: str | None,
    window_records: set[str] | None,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Filter ``df`` to the curated window by date column or record-number join."""
    if date_column and date_column in df.columns:
        return df[_date_in_window_mask(df[date_column], start, end)].copy()
    if window_records is not None and RECORD_NUMBER_COLUMN in df.columns:
        return df[df[RECORD_NUMBER_COLUMN].astype(str).isin(window_records)].copy()
    return df.copy()

"""SQLite input/output helpers for fee scraping records and results."""

import sqlite3

import pandas as pd

from dataprep.shared.db import read_table_if_exists, write_table
from dataprep.shared.schema import (
    GEOCODED_RECORDS_TABLE,
    RECORD_NUMBER_COLUMN,
    SCRAPED_FEES_TABLE,
)

from .constants import STATUS_FAILED, STATUS_SUCCESS
from .types import FeeRow

FEE_RESULT_COLUMNS = ["record_number", "paid", "outstanding", "scrape_status"]


def _coerce_float(value: object) -> float:
    """Coerce a stored numeric/text value to float, defaulting to 0.0."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    text = str(value).strip()
    return float(text) if text else 0.0


def read_record_numbers(connection: sqlite3.Connection, limit: int | None = None) -> list[str]:
    """Read unique record numbers from the geocoded_records table."""
    df = read_table_if_exists(connection, GEOCODED_RECORDS_TABLE)
    if df is None or RECORD_NUMBER_COLUMN not in df.columns:
        return []

    records: list[str] = []
    seen: set[str] = set()
    for value in df[RECORD_NUMBER_COLUMN]:
        record_number = "" if value is None else str(value).strip()
        if not record_number or record_number in seen:
            continue
        seen.add(record_number)
        records.append(record_number)
        if limit and len(records) >= limit:
            break
    return records


def read_existing_results(
    connection: sqlite3.Connection,
) -> tuple[list[FeeRow], set[str], set[str]]:
    """Read existing scrape results from the scraped_fees table by status."""
    df = read_table_if_exists(connection, SCRAPED_FEES_TABLE)
    if df is None:
        return [], set(), set()

    rows: list[FeeRow] = []
    existing_records: set[str] = set()
    success_records: set[str] = set()
    failed_records: set[str] = set()
    for row in df.to_dict("records"):
        record_number = "" if row.get("record_number") is None else str(row["record_number"]).strip()
        if not record_number or record_number in existing_records:
            continue
        existing_records.add(record_number)
        scrape_status = str(row.get("scrape_status") or STATUS_FAILED).strip().lower()
        if scrape_status == STATUS_SUCCESS:
            success_records.add(record_number)
        else:
            scrape_status = STATUS_FAILED
            failed_records.add(record_number)
        rows.append(
            {
                "record_number": record_number,
                "paid": _coerce_float(row.get("paid")),
                "outstanding": _coerce_float(row.get("outstanding")),
                "scrape_status": scrape_status,
            }
        )
    return rows, success_records, failed_records


def merge_rows_by_input_order(
    input_records: list[str],
    existing_rows: list[FeeRow],
    new_rows: list[FeeRow],
) -> list[FeeRow]:
    """Merge existing and new rows while preserving input record order."""
    by_record: dict[str, FeeRow] = {}
    for row in existing_rows:
        by_record[str(row["record_number"])] = row
    for row in new_rows:
        by_record[str(row["record_number"])] = row

    merged: list[FeeRow] = []
    consumed_records: set[str] = set()
    for record_number in input_records:
        row = by_record.get(record_number)
        if row is not None:
            merged.append(row)
            consumed_records.add(record_number)
    for row in existing_rows:
        record_number = str(row["record_number"])
        if record_number not in consumed_records:
            merged.append(row)
    return merged


def write_results(connection: sqlite3.Connection, rows: list[FeeRow]) -> None:
    """Write scrape result rows to the scraped_fees table."""
    results_df = pd.DataFrame(rows, columns=FEE_RESULT_COLUMNS)
    write_table(connection, SCRAPED_FEES_TABLE, results_df, dataset_name="scraped_fees")

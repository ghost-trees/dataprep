"""CSV input/output helpers for fee scraping records and results."""

import csv
from pathlib import Path

from .constants import STATUS_FAILED, STATUS_SUCCESS
from .types import FeeRow


def read_record_numbers(input_csv: Path, limit: int | None = None) -> list[str]:
    """Read unique record numbers from the input CSV."""
    records: list[str] = []
    seen: set[str] = set()
    with input_csv.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            record_number = (
                row.get("record_number") or row.get("Record Number") or ""
            ).strip()
            if not record_number or record_number in seen:
                continue
            seen.add(record_number)
            records.append(record_number)
            if limit and len(records) >= limit:
                break
    return records


def read_existing_results(output_csv: Path) -> tuple[list[FeeRow], set[str], set[str]]:
    """Read existing scrape results and split record statuses."""
    if not output_csv.exists():
        return [], set(), set()

    rows: list[FeeRow] = []
    existing_records: set[str] = set()
    success_records: set[str] = set()
    failed_records: set[str] = set()
    with output_csv.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            record_number = (row.get("record_number") or "").strip()
            if not record_number or record_number in existing_records:
                continue
            existing_records.add(record_number)
            scrape_status = (row.get("scrape_status") or STATUS_FAILED).strip().lower()
            if not scrape_status:
                scrape_status = STATUS_FAILED
            if scrape_status == STATUS_SUCCESS:
                success_records.add(record_number)
            else:
                scrape_status = STATUS_FAILED
                failed_records.add(record_number)
            rows.append(
                {
                    "record_number": record_number,
                    "paid": float((row.get("paid") or "0").strip() or "0"),
                    "outstanding": float((row.get("outstanding") or "0").strip() or "0"),
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


def write_results(output_csv: Path, rows: list[FeeRow]) -> None:
    """Write scrape result rows to the output CSV file."""
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file, fieldnames=["record_number", "paid", "outstanding", "scrape_status"]
        )
        writer.writeheader()
        writer.writerows(rows)

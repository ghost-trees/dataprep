import csv
from pathlib import Path

import pytest

from dataprep.pipelines.records.pipeline import (
    _assert_unique_record_numbers,
    _deduplicate_exact_rows,
)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader)


def test_deduplicate_exact_rows_removes_only_identical_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "scraped_records.csv"
    fieldnames = ["record_number", "status", "address"]
    _write_csv(
        csv_path,
        fieldnames=fieldnames,
        rows=[
            {"record_number": "R1", "status": "Fine", "address": "123 Main"},
            {"record_number": "R1", "status": "Fine", "address": "123 Main"},
            {"record_number": "R2", "status": "Open", "address": "234 Pine"},
        ],
    )

    removed_rows = _deduplicate_exact_rows(csv_path)

    assert removed_rows == 1
    assert _read_rows(csv_path) == [
        {"record_number": "R1", "status": "Fine", "address": "123 Main"},
        {"record_number": "R2", "status": "Open", "address": "234 Pine"},
    ]
    _assert_unique_record_numbers(csv_path)


def test_duplicate_record_numbers_with_conflicting_values_still_raise(tmp_path: Path) -> None:
    csv_path = tmp_path / "scraped_records.csv"
    _write_csv(
        csv_path,
        fieldnames=["record_number", "status", "address"],
        rows=[
            {"record_number": "R1", "status": "Fine", "address": "123 Main"},
            {"record_number": "R1", "status": "Open", "address": "123 Main"},
        ],
    )

    removed_rows = _deduplicate_exact_rows(csv_path)

    assert removed_rows == 0
    with pytest.raises(ValueError, match="Duplicate record numbers found in scraped records CSV"):
        _assert_unique_record_numbers(csv_path)


def test_assert_unique_record_numbers_requires_record_number_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "scraped_records.csv"
    _write_csv(
        csv_path,
        fieldnames=["status", "address"],
        rows=[{"status": "Fine", "address": "123 Main"}],
    )

    with pytest.raises(ValueError, match="Missing 'record_number' column"):
        _assert_unique_record_numbers(csv_path)

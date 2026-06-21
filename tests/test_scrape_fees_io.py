from pathlib import Path

from db_helpers import seed_table

from dataprep.pipelines.scrape_fees.io import (
    merge_rows_by_input_order,
    read_existing_results,
    read_record_numbers,
)
from dataprep.shared.db import get_connection
from dataprep.shared.schema import GEOCODED_RECORDS_TABLE, SCRAPED_FEES_TABLE


def test_read_record_numbers_returns_unique_in_order(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(
        db_path,
        GEOCODED_RECORDS_TABLE,
        [
            {"record_number": "R1", "address": "a"},
            {"record_number": "R2", "address": "b"},
        ],
    )

    connection = get_connection(db_path)
    try:
        assert read_record_numbers(connection) == ["R1", "R2"]
        assert read_record_numbers(connection, limit=1) == ["R1"]
    finally:
        connection.close()


def test_read_record_numbers_empty_when_table_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"

    connection = get_connection(db_path)
    try:
        assert read_record_numbers(connection) == []
    finally:
        connection.close()


def test_read_existing_results_splits_success_and_failed(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(
        db_path,
        SCRAPED_FEES_TABLE,
        [
            {"record_number": "R1", "paid": 12.5, "outstanding": 0.0, "scrape_status": "success"},
            {"record_number": "R2", "paid": 0.0, "outstanding": 4.0, "scrape_status": "failed"},
        ],
    )

    connection = get_connection(db_path)
    try:
        rows, success, failed = read_existing_results(connection)
    finally:
        connection.close()

    assert len(rows) == 2
    assert success == {"R1"}
    assert failed == {"R2"}


def test_merge_rows_by_input_order_replaces_existing_rows() -> None:
    input_records = ["R1", "R2", "R3"]
    existing_rows = [
        {"record_number": "R1", "paid": 1.0, "outstanding": 0.0, "scrape_status": "success"},
        {"record_number": "R2", "paid": 0.0, "outstanding": 2.0, "scrape_status": "failed"},
        {"record_number": "R9", "paid": 9.0, "outstanding": 0.0, "scrape_status": "success"},
    ]
    new_rows = [
        {"record_number": "R2", "paid": 20.0, "outstanding": 1.0, "scrape_status": "success"},
        {"record_number": "R3", "paid": 30.0, "outstanding": 3.0, "scrape_status": "success"},
    ]

    merged = merge_rows_by_input_order(input_records, existing_rows, new_rows)
    merged_records = [row["record_number"] for row in merged]

    assert merged_records == ["R1", "R2", "R3", "R9"]
    assert merged[1]["paid"] == 20.0

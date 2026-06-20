import csv
import json
from pathlib import Path

import pandas as pd
import pytest

from dataprep.pipelines.records.io import ingest_scraped_records_csv
from dataprep.shared.db import get_connection, write_table
from dataprep.shared.schema import (
    SCRAPED_RECORDS_ACA_COLUMNS,
    SCRAPED_RECORDS_TABLE,
    assert_aca_export_schema,
)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _seed_scraped_records_table(db_path: Path, rows: list[dict[str, object]]) -> None:
    connection = get_connection(db_path)
    try:
        write_table(
            connection,
            SCRAPED_RECORDS_TABLE,
            pd.DataFrame(rows),
            dataset_name="scraped_records",
        )
    finally:
        connection.close()


def _read_scraped_records_table(db_path: Path) -> pd.DataFrame:
    connection = get_connection(db_path)
    try:
        return pd.read_sql_query(f'SELECT * FROM "{SCRAPED_RECORDS_TABLE}"', connection)
    finally:
        connection.close()


def test_assert_aca_export_schema_accepts_fixture_columns() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "aca_export_columns.json"
    fixture_columns = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert tuple(fixture_columns) == SCRAPED_RECORDS_ACA_COLUMNS
    assert_aca_export_schema(fixture_columns)


def test_assert_aca_export_schema_raises_on_missing_columns() -> None:
    with pytest.raises(ValueError, match="Missing: \\['status'\\]"):
        assert_aca_export_schema(
            [
                "date",
                "record_number",
                "record_type",
                "address",
                "description",
                "permit_name",
                "short_notes",
            ]
        )


def test_assert_aca_export_schema_raises_on_unexpected_columns() -> None:
    with pytest.raises(ValueError, match="Unexpected: \\['new_field'\\]"):
        assert_aca_export_schema([*SCRAPED_RECORDS_ACA_COLUMNS, "new_field"])


def test_ingest_first_run_writes_all_rows_as_new(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    csv_path = tmp_path / "scraped_records.csv"
    _write_csv(
        csv_path,
        list(SCRAPED_RECORDS_ACA_COLUMNS),
        [
            {
                "date": "01/05/2025",
                "record_number": "R1",
                "record_type": "Arborist",
                "address": "123 Main",
                "description": "Removed tree",
                "permit_name": "Illegal",
                "status": "Open",
                "short_notes": "Note",
            },
            {
                "date": "01/06/2025",
                "record_number": "R2",
                "record_type": "Arborist",
                "address": "234 Pine",
                "description": "Trimmed tree",
                "permit_name": "Illegal",
                "status": "Closed",
                "short_notes": "",
            },
        ],
    )

    connection = get_connection(db_path)
    try:
        summary = ingest_scraped_records_csv(connection, csv_path, exact_duplicates_removed=1)
    finally:
        connection.close()

    assert summary.downloaded_rows == 2
    assert summary.exact_duplicates_removed == 1
    assert summary.prior_records == 0
    assert summary.new_records == 2
    assert summary.overlapping_records == 0
    assert summary.total_written == 2


def test_ingest_marks_identical_overlap_as_unchanged(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    _seed_scraped_records_table(
        db_path,
        [
            {
                "date": "01/05/2025",
                "record_number": "R1",
                "record_type": "Arborist",
                "address": "123 Main",
                "description": "Removed tree",
                "permit_name": "Illegal",
                "status": "Open",
                "short_notes": "Note",
                "date_iso": "2025-01-05",
            }
        ],
    )
    csv_path = tmp_path / "scraped_records.csv"
    _write_csv(
        csv_path,
        list(SCRAPED_RECORDS_ACA_COLUMNS),
        [
            {
                "date": "01/05/2025",
                "record_number": "R1",
                "record_type": "Arborist",
                "address": "123 Main",
                "description": "Removed tree",
                "permit_name": "Illegal",
                "status": "Open",
                "short_notes": "Note",
            }
        ],
    )

    connection = get_connection(db_path)
    try:
        summary = ingest_scraped_records_csv(connection, csv_path, exact_duplicates_removed=0)
    finally:
        connection.close()

    assert summary.prior_records == 1
    assert summary.overlapping_records == 1
    assert summary.unchanged_records == 1
    assert summary.updated_records == 0
    assert summary.new_records == 0
    assert summary.preserved_records == 0


def test_ingest_uses_scrape_row_when_overlap_changes(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    _seed_scraped_records_table(
        db_path,
        [
            {
                "date": "01/05/2025",
                "record_number": "R1",
                "record_type": "Arborist",
                "address": "123 Main",
                "description": "Removed tree",
                "permit_name": "Illegal",
                "status": "Open",
                "short_notes": "Note",
                "date_iso": "2025-01-05",
            }
        ],
    )
    csv_path = tmp_path / "scraped_records.csv"
    _write_csv(
        csv_path,
        list(SCRAPED_RECORDS_ACA_COLUMNS),
        [
            {
                "date": "01/05/2025",
                "record_number": "R1",
                "record_type": "Arborist",
                "address": "123 Main",
                "description": "Removed tree",
                "permit_name": "Illegal",
                "status": "Closed",
                "short_notes": "Note",
            }
        ],
    )

    connection = get_connection(db_path)
    try:
        summary = ingest_scraped_records_csv(connection, csv_path, exact_duplicates_removed=0)
    finally:
        connection.close()

    output_df = _read_scraped_records_table(db_path)
    assert summary.updated_records == 1
    assert output_df.loc[0, "status"] == "Closed"


def test_ingest_preserves_prior_rows_not_in_scrape(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    _seed_scraped_records_table(
        db_path,
        [
            {
                "date": "01/01/2025",
                "record_number": "R-OLD",
                "record_type": "Arborist",
                "address": "100 Old St",
                "description": "Old",
                "permit_name": "Illegal",
                "status": "Open",
                "short_notes": "",
                "date_iso": "2025-01-01",
            }
        ],
    )
    csv_path = tmp_path / "scraped_records.csv"
    _write_csv(
        csv_path,
        list(SCRAPED_RECORDS_ACA_COLUMNS),
        [
            {
                "date": "01/05/2025",
                "record_number": "R-NEW",
                "record_type": "Arborist",
                "address": "200 New St",
                "description": "New",
                "permit_name": "Illegal",
                "status": "Open",
                "short_notes": "",
            }
        ],
    )

    connection = get_connection(db_path)
    try:
        summary = ingest_scraped_records_csv(connection, csv_path, exact_duplicates_removed=0)
    finally:
        connection.close()

    output_df = _read_scraped_records_table(db_path)
    assert summary.new_records == 1
    assert summary.preserved_records == 1
    assert output_df["record_number"].tolist() == ["R-NEW", "R-OLD"]

from pathlib import Path

import pandas as pd
import pytest

from dataprep.shared.db import (
    get_connection,
    init_db,
    read_table,
    read_table_if_exists,
    table_exists,
    write_table,
)


def test_init_db_creates_database_file(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"

    init_db(db_path)

    assert db_path.exists()


def test_write_and_read_table_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    df = pd.DataFrame({"record_number": ["R1", "R2"], "value": [1, 2]})

    connection = get_connection(db_path)
    try:
        write_table(connection, "scraped_records", df, dataset_name="scraped_records")
        result = read_table(connection, "scraped_records")
    finally:
        connection.close()

    assert list(result.columns) == ["record_number", "value"]
    assert result["record_number"].tolist() == ["R1", "R2"]


def test_write_table_enforces_record_number_and_dedupes(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    df = pd.DataFrame({"record_number": ["R1", "R1", " R2 "], "value": [1, 2, 3]})

    connection = get_connection(db_path)
    try:
        written = write_table(connection, "scraped_records", df, dataset_name="scraped_records")
    finally:
        connection.close()

    assert written["record_number"].tolist() == ["R1", "R2"]


def test_write_table_requires_record_number(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    df = pd.DataFrame({"value": [1]})

    connection = get_connection(db_path)
    try:
        with pytest.raises(ValueError, match="Expected 'record_number'"):
            write_table(connection, "scraped_records", df, dataset_name="scraped_records")
    finally:
        connection.close()


def test_read_table_if_exists_returns_none_for_missing_table(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"

    connection = get_connection(db_path)
    try:
        assert not table_exists(connection, "scraped_fees")
        assert read_table_if_exists(connection, "scraped_fees") is None
    finally:
        connection.close()

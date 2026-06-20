"""Shared helpers for seeding and reading SQLite tables in tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dataprep.shared.db import get_connection, write_table


def seed_table(db_path: Path, table: str, rows: list[dict[str, object]]) -> None:
    """Write rows to a table using the production integrity-enforcing writer."""
    connection = get_connection(db_path)
    try:
        write_table(connection, table, pd.DataFrame(rows), dataset_name=table)
    finally:
        connection.close()


def read_table_df(db_path: Path, table: str) -> pd.DataFrame:
    """Read a full table into a DataFrame."""
    connection = get_connection(db_path)
    try:
        return pd.read_sql_query(f'SELECT * FROM "{table}"', connection)
    finally:
        connection.close()

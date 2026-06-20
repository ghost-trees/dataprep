"""SQLite persistence layer shared across dataprep pipelines.

The database file is the canonical source of truth for every pipeline stage.
Tables are created lazily on first write via :func:`pandas.DataFrame.to_sql`,
because the ``scraped_records`` schema is defined by the upstream portal export
rather than a fixed column list.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .normalize import drop_unnamed_columns, normalize_columns
from .paths import DB_PATH
from .schema import (
    GEOCODED_RECORDS_TABLE,
    OUTPUT_TABLE,
    PARSED_TREES_TABLE,
    RECORD_NUMBER_COLUMN,
    SCRAPED_FEES_TABLE,
    SCRAPED_RECORDS_TABLE,
)

DEFAULT_DB_PATH = DB_PATH

ALL_TABLES = (
    SCRAPED_RECORDS_TABLE,
    GEOCODED_RECORDS_TABLE,
    SCRAPED_FEES_TABLE,
    PARSED_TREES_TABLE,
    OUTPUT_TABLE,
)


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection, creating the parent directory if needed."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(db_path: Path = DEFAULT_DB_PATH) -> Path:
    """Ensure the database file exists and is reachable.

    Tables are created on first write, so this simply opens (and thereby
    creates) the database file at ``db_path``.
    """
    connection = get_connection(db_path)
    connection.close()
    return Path(db_path)


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    """Return True when ``table`` exists in the connected database."""
    cursor = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    )
    return cursor.fetchone() is not None


def apply_record_number_integrity(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Enforce record_number integrity: required, stripped, and deduplicated."""
    if RECORD_NUMBER_COLUMN not in df.columns:
        raise ValueError(
            f"Expected '{RECORD_NUMBER_COLUMN}' column in {dataset_name}, "
            f"found: {list(df.columns)}"
        )

    df = df.copy()
    df[RECORD_NUMBER_COLUMN] = df[RECORD_NUMBER_COLUMN].astype(str).str.strip()
    df = df[df[RECORD_NUMBER_COLUMN] != ""].copy()

    duplicate_mask = df.duplicated(subset=[RECORD_NUMBER_COLUMN], keep="first")
    duplicate_count = int(duplicate_mask.sum())
    if duplicate_count:
        print(
            f"{dataset_name}: dropping {duplicate_count} duplicate rows by "
            f"'{RECORD_NUMBER_COLUMN}'"
        )
        df = df[~duplicate_mask].copy()

    return df


def write_table(
    connection: sqlite3.Connection,
    table: str,
    df: pd.DataFrame,
    *,
    dataset_name: str | None = None,
    enforce_integrity: bool = True,
) -> pd.DataFrame:
    """Normalize, validate, and write ``df`` to ``table`` (replacing contents).

    Returns the prepared DataFrame that was persisted.
    """
    dataset_name = dataset_name or table
    prepared = normalize_columns(df)
    prepared = drop_unnamed_columns(prepared)
    if enforce_integrity:
        prepared = apply_record_number_integrity(prepared, dataset_name)

    prepared.to_sql(table, connection, if_exists="replace", index=False)
    connection.commit()
    return prepared


def read_table(connection: sqlite3.Connection, table: str) -> pd.DataFrame:
    """Read an entire table into a DataFrame, raising if it does not exist."""
    if not table_exists(connection, table):
        raise ValueError(f"Table '{table}' does not exist in the database.")
    return pd.read_sql_query(f'SELECT * FROM "{table}"', connection)


def read_table_if_exists(connection: sqlite3.Connection, table: str) -> pd.DataFrame | None:
    """Read a table into a DataFrame, returning None when it does not exist."""
    if not table_exists(connection, table):
        return None
    return pd.read_sql_query(f'SELECT * FROM "{table}"', connection)

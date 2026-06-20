"""Normalization helpers for column naming and dataframe cleanup."""

import re

import pandas as pd

from .schema import DATE_COLUMN, DATE_ISO_COLUMN

SOURCE_DATE_FORMAT = "%m/%d/%Y"


def to_snake_case(value: str) -> str:
    """Convert free-form column names to snake_case."""
    normalized = re.sub(r"[^0-9A-Za-z]+", "_", value.strip().lower())
    return normalized.strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with snake_case column names."""
    normalized_columns = [to_snake_case(str(column_name)) for column_name in df.columns]
    return df.rename(columns=dict(zip(df.columns, normalized_columns, strict=False)))


def drop_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop auto-generated unnamed columns from CSV round-trips."""
    unnamed_columns = [name for name in df.columns if name.startswith("unnamed")]
    if not unnamed_columns:
        return df
    return df.drop(columns=unnamed_columns)


def derive_date_iso(
    df: pd.DataFrame,
    source_column: str = DATE_COLUMN,
    target_column: str = DATE_ISO_COLUMN,
) -> pd.DataFrame:
    """Return a copy with a normalized ``date_iso`` (YYYY-MM-DD) column.

    The source ``date`` column is expected in ``MM/DD/YYYY`` form. Unparseable or
    empty values become null so they fall outside any date window. When the
    source column is absent the frame is returned unchanged.
    """
    if source_column not in df.columns:
        return df
    df = df.copy()
    parsed = pd.to_datetime(df[source_column], format=SOURCE_DATE_FORMAT, errors="coerce")
    df[target_column] = parsed.dt.strftime("%Y-%m-%d")
    return df

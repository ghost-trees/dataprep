"""Normalization helpers for column naming and dataframe cleanup."""

import re

import pandas as pd


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

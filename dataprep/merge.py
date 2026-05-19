"""Dataset merge and validation utilities for final output."""

from pathlib import Path

import pandas as pd

from dataprep.shared.csv_utils import load_dataset
from dataprep.shared.schema import RECORD_NUMBER_COLUMN


def prepare_join_frame(
    source_df: pd.DataFrame,
    existing_columns: set[str],
    source_prefix: str,
) -> pd.DataFrame:
    """Prepare a join-safe projection by prefixing conflicting column names."""
    rename_map: dict[str, str] = {}
    selected_columns = [RECORD_NUMBER_COLUMN]

    for column_name in source_df.columns:
        if column_name == RECORD_NUMBER_COLUMN:
            continue

        output_column_name = column_name
        if output_column_name in existing_columns:
            output_column_name = f"{source_prefix}_{column_name}"
        while output_column_name in existing_columns:
            output_column_name = f"{source_prefix}_{output_column_name}"

        rename_map[column_name] = output_column_name
        selected_columns.append(column_name)
        existing_columns.add(output_column_name)

    return source_df[selected_columns].rename(columns=rename_map)


def merge_output(
    records_path: Path,
    geocoded_path: Path,
    fees_path: Path,
) -> pd.DataFrame:
    """Load stage outputs and merge them by record_number."""
    records_df = load_dataset(records_path, "scraped_records")
    geocoded_df = load_dataset(geocoded_path, "geocoded_records")
    fees_df = load_dataset(fees_path, "scraped_fees")

    output_df = records_df.copy()
    used_columns = set(output_df.columns)

    geocoded_join_df = prepare_join_frame(geocoded_df, used_columns, source_prefix="geo")
    output_df = output_df.merge(geocoded_join_df, on=RECORD_NUMBER_COLUMN, how="left")

    fees_join_df = prepare_join_frame(fees_df, used_columns, source_prefix="fees")
    output_df = output_df.merge(fees_join_df, on=RECORD_NUMBER_COLUMN, how="left")

    return output_df


def validate_no_nulls(output_df: pd.DataFrame) -> None:
    """Fail fast when merged output contains null values."""
    null_counts = output_df.isnull().sum()
    null_counts = null_counts[null_counts > 0]

    if null_counts.empty:
        return

    rows_with_nulls = int(output_df.isnull().any(axis=1).sum())
    column_details = ", ".join(f"{column}={count}" for column, count in null_counts.items())
    raise ValueError(
        "Null values found in output.csv. "
        f"Rows with nulls: {rows_with_nulls}. "
        f"Columns with null counts: {column_details}"
    )

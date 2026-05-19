"""CSV/dataframe utilities shared across pipeline stages."""

from pathlib import Path

import pandas as pd

from .normalize import normalize_columns
from .schema import RECORD_NUMBER_COLUMN


def load_dataset(path: Path, dataset_name: str) -> pd.DataFrame:
    """Load and normalize a dataset with record_number integrity checks."""
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    df = pd.read_csv(path)
    df = normalize_columns(df)

    if RECORD_NUMBER_COLUMN not in df.columns:
        raise ValueError(
            f"Expected '{RECORD_NUMBER_COLUMN}' column in {dataset_name} ({path}), "
            f"found: {list(df.columns)}"
        )

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

from pathlib import Path

import pandas as pd
import pytest

from dataprep.merge import merge_output, prepare_join_frame, validate_no_nulls


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def test_prepare_join_frame_prefixes_conflicting_columns() -> None:
    source_df = pd.DataFrame(
        {
            "record_number": ["1"],
            "address": ["123 Main"],
            "status": ["open"],
        }
    )
    existing_columns = {"record_number", "address"}

    prepared = prepare_join_frame(source_df, existing_columns, source_prefix="geo")

    assert list(prepared.columns) == ["record_number", "geo_address", "status"]


def test_merge_output_preserves_unique_rows_and_prefixes(tmp_path: Path) -> None:
    records = tmp_path / "scraped_records.csv"
    geocoded = tmp_path / "geocoded_records.csv"
    fees = tmp_path / "scraped_fees.csv"

    _write_csv(
        records,
        [
            {"record_number": "R1", "address": "123 Main", "tree_type": "Oak"},
            {"record_number": "R1", "address": "123 Main", "tree_type": "Oak Duplicate"},
            {"record_number": "R2", "address": "234 Pine", "tree_type": "Maple"},
        ],
    )
    _write_csv(
        geocoded,
        [
            {"record_number": "R1", "address": "123 Main", "latitude": 33.1, "longitude": -84.1},
            {"record_number": "R2", "address": "234 Pine", "latitude": 33.2, "longitude": -84.2},
        ],
    )
    _write_csv(
        fees,
        [
            {"record_number": "R1", "address": "123 Main", "paid": 10.0, "outstanding": 1.0},
            {"record_number": "R2", "address": "234 Pine", "paid": 20.0, "outstanding": 2.0},
        ],
    )

    merged = merge_output(records, geocoded, fees)

    assert len(merged) == 2
    assert {"geo_address", "fees_address", "paid", "latitude"}.issubset(set(merged.columns))


def test_validate_no_nulls_raises_with_column_details() -> None:
    df = pd.DataFrame({"record_number": ["R1"], "latitude": [None]})
    with pytest.raises(ValueError, match="Null values found in output.csv"):
        validate_no_nulls(df)

"""Build a GeoJSON FeatureCollection from final pipeline CSV outputs.

This module reads canonical datasets keyed by record number, joins them into one
feature frame, writes `data.geojson`, and emits a warning when fee details are
missing for some records.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pandas as pd

from dataprep.shared.paths import (
    DATA_GEOJSON_PATH,
    GEOCODED_RECORDS_PATH,
    PARSED_TREES_PATH,
    SCRAPED_FEES_PATH,
    SCRAPED_RECORDS_PATH,
)
from dataprep.shared.schema import (
    GEOCODED_ADDRESS_COLUMN,
    LATITUDE_COLUMN,
    LONGITUDE_COLUMN,
    OUTSTANDING_COLUMN,
    PAID_COLUMN,
    RECORD_NUMBER_COLUMN,
    TREE_TYPES_COLUMN,
)

DATE_COLUMN = "date"
RECORD_TYPE_COLUMN = "record_type"
PERMIT_NAME_COLUMN = "permit_name"
STATUS_COLUMN = "status"
DESCRIPTION_COLUMN = "description"
TREE_TYPES_DELIMITER = "|"


def _validate_required_columns(df: pd.DataFrame, required_columns: list[str], source_name: str) -> None:
    """Validate required columns exist in a source DataFrame.

    Args:
        df: Source DataFrame loaded from a pipeline CSV.
        required_columns: Required columns expected in the source dataset.
        source_name: Friendly source label included in error messages.

    Raises:
        ValueError: If one or more required columns are missing.
    """
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Expected columns {required_columns} in {source_name}, "
            f"but missing: {missing_columns}. Found: {list(df.columns)}"
        )


def _to_json_value(value: object) -> object:
    """Convert pandas/NumPy values into JSON-safe Python primitives.

    Args:
        value: Scalar value from a DataFrame row.

    Returns:
        JSON-safe value with null-like values normalized to None.
    """
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _tree_types_to_array(value: object) -> list[str]:
    """Convert stored tree-types value to an array for GeoJSON output."""
    normalized_value = _to_json_value(value)
    if normalized_value is None:
        return []

    text = str(normalized_value).strip()
    if not text:
        return []

    return [part.strip() for part in text.split(TREE_TYPES_DELIMITER) if part.strip()]


def _build_feature_collection(merged_df: pd.DataFrame) -> dict[str, object]:
    """Build a GeoJSON FeatureCollection from a merged DataFrame.

    Args:
        merged_df: Joined DataFrame containing all required GeoJSON columns.

    Returns:
        GeoJSON FeatureCollection dictionary.
    """
    features: list[dict[str, object]] = []

    for row in merged_df.itertuples(index=False):
        longitude = _to_json_value(getattr(row, LONGITUDE_COLUMN))
        latitude = _to_json_value(getattr(row, LATITUDE_COLUMN))
        feature = {
            "type": "Feature",
            "id": _to_json_value(getattr(row, RECORD_NUMBER_COLUMN)),
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude],
            },
            "properties": {
                "record_number": _to_json_value(getattr(row, RECORD_NUMBER_COLUMN)),
                "date": _to_json_value(getattr(row, DATE_COLUMN)),
                "record_type": _to_json_value(getattr(row, RECORD_TYPE_COLUMN)),
                "permit_name": _to_json_value(getattr(row, PERMIT_NAME_COLUMN)),
                "status": _to_json_value(getattr(row, STATUS_COLUMN)),
                "description": _to_json_value(getattr(row, DESCRIPTION_COLUMN)),
                "paid": _to_json_value(getattr(row, PAID_COLUMN)),
                "outstanding": _to_json_value(getattr(row, OUTSTANDING_COLUMN)),
                "tree_types": _tree_types_to_array(getattr(row, TREE_TYPES_COLUMN)),
                "address": _to_json_value(getattr(row, GEOCODED_ADDRESS_COLUMN)),
            },
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def run(
    scraped_records_path: Path = SCRAPED_RECORDS_PATH,
    geocoded_records_path: Path = GEOCODED_RECORDS_PATH,
    scraped_fees_path: Path = SCRAPED_FEES_PATH,
    parsed_trees_path: Path = PARSED_TREES_PATH,
    output_geojson_path: Path = DATA_GEOJSON_PATH,
) -> Path:
    """Generate a final GeoJSON dataset from pipeline CSV outputs.

    Args:
        scraped_records_path: Path to scraped records CSV.
        geocoded_records_path: Path to geocoded records CSV.
        scraped_fees_path: Path to scraped fees CSV.
        parsed_trees_path: Path to parsed trees CSV.
        output_geojson_path: Destination path for GeoJSON output.

    Returns:
        The written GeoJSON output path.

    Raises:
        ValueError: If any required source columns are missing.
    """
    records_df = pd.read_csv(scraped_records_path)
    geocoded_df = pd.read_csv(geocoded_records_path)
    parsed_trees_df = pd.read_csv(parsed_trees_path)
    fees_df = pd.read_csv(scraped_fees_path)

    _validate_required_columns(
        records_df,
        [
            RECORD_NUMBER_COLUMN,
            DATE_COLUMN,
            RECORD_TYPE_COLUMN,
            PERMIT_NAME_COLUMN,
            STATUS_COLUMN,
            DESCRIPTION_COLUMN,
        ],
        source_name=str(scraped_records_path),
    )
    _validate_required_columns(
        geocoded_df,
        [RECORD_NUMBER_COLUMN, LATITUDE_COLUMN, LONGITUDE_COLUMN, GEOCODED_ADDRESS_COLUMN],
        source_name=str(geocoded_records_path),
    )
    _validate_required_columns(
        parsed_trees_df,
        [RECORD_NUMBER_COLUMN, TREE_TYPES_COLUMN],
        source_name=str(parsed_trees_path),
    )
    _validate_required_columns(
        fees_df,
        [RECORD_NUMBER_COLUMN, PAID_COLUMN, OUTSTANDING_COLUMN],
        source_name=str(scraped_fees_path),
    )

    merged_df = records_df.merge(
        geocoded_df[
            [
                RECORD_NUMBER_COLUMN,
                LATITUDE_COLUMN,
                LONGITUDE_COLUMN,
                GEOCODED_ADDRESS_COLUMN,
            ]
        ],
        on=RECORD_NUMBER_COLUMN,
        how="left",
    )
    merged_df = merged_df.merge(
        parsed_trees_df[[RECORD_NUMBER_COLUMN, TREE_TYPES_COLUMN]],
        on=RECORD_NUMBER_COLUMN,
        how="left",
    )
    merged_df = merged_df.merge(
        fees_df[[RECORD_NUMBER_COLUMN, PAID_COLUMN, OUTSTANDING_COLUMN]],
        on=RECORD_NUMBER_COLUMN,
        how="left",
    )

    missing_fees_count = int(merged_df[[PAID_COLUMN, OUTSTANDING_COLUMN]].isna().all(axis=1).sum())
    if missing_fees_count:
        warnings.warn(
            f"Missing fee information for {missing_fees_count} of {len(merged_df)} records.",
            stacklevel=2,
        )

    feature_collection = _build_feature_collection(merged_df)
    output_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    output_geojson_path.write_text(json.dumps(feature_collection, indent=2), encoding="utf-8")
    print(f"Wrote {len(feature_collection['features'])} features to {output_geojson_path}")
    return output_geojson_path

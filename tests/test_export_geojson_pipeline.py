import json
from pathlib import Path

import pytest
from db_helpers import seed_table

from dataprep.pipelines.export_geojson import pipeline as export_geojson_pipeline
from dataprep.shared.schema import (
    GEOCODED_RECORDS_TABLE,
    PARSED_TREES_TABLE,
    SCRAPED_FEES_TABLE,
    SCRAPED_RECORDS_TABLE,
)

WINDOW_START = "2026-01-01"
WINDOW_END = "2026-12-31"


def test_run_writes_feature_collection_with_expected_mapping(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    output_geojson_path = tmp_path / "data.geojson"

    seed_table(
        db_path,
        SCRAPED_RECORDS_TABLE,
        [
            {
                "record_number": "R1",
                "date": "05/01/2026",
                "date_iso": "2026-05-01",
                "record_type": "Arborist Illegal Activity",
                "permit_name": "Illegal Removal",
                "status": "Fine",
                "description": "Removed two trees",
            }
        ],
    )
    seed_table(
        db_path,
        GEOCODED_RECORDS_TABLE,
        [
            {
                "record_number": "R1",
                "latitude": 33.1,
                "longitude": -84.1,
                "geocoded_address": "123 Main St, Atlanta, GA",
            }
        ],
    )
    seed_table(db_path, SCRAPED_FEES_TABLE, [{"record_number": "R1", "paid": 150.0, "outstanding": 25.0}])
    seed_table(db_path, PARSED_TREES_TABLE, [{"record_number": "R1", "tree_types": "hardwood|pine"}])

    written_path = export_geojson_pipeline.run(
        db_path=db_path,
        output_geojson_path=output_geojson_path,
        start=WINDOW_START,
        end=WINDOW_END,
    )

    assert written_path == output_geojson_path
    payload = json.loads(output_geojson_path.read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1
    feature = payload["features"][0]
    assert feature["id"] == "R1"
    assert feature["geometry"] == {"type": "Point", "coordinates": [-84.1, 33.1]}
    assert feature["properties"] == {
        "record_number": "R1",
        "date": "05/01/2026",
        "record_type": "Arborist Illegal Activity",
        "permit_name": "Illegal Removal",
        "status": "Fine",
        "description": "Removed two trees",
        "paid": 150.0,
        "outstanding": 25.0,
        "tree_types": ["hardwood", "pine"],
        "address": "123 Main St, Atlanta, GA",
    }
    assert "geocoded_address" not in feature["properties"]


def test_run_filters_records_to_curated_window(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    output_geojson_path = tmp_path / "data.geojson"

    seed_table(
        db_path,
        SCRAPED_RECORDS_TABLE,
        [
            {
                "record_number": "R1",
                "date": "05/01/2026",
                "date_iso": "2026-05-01",
                "record_type": "Type A",
                "permit_name": "Permit A",
                "status": "Fine",
                "description": "In window",
            },
            {
                "record_number": "R2",
                "date": "05/01/2024",
                "date_iso": "2024-05-01",
                "record_type": "Type B",
                "permit_name": "Permit B",
                "status": "Fine",
                "description": "Out of window",
            },
        ],
    )
    seed_table(
        db_path,
        GEOCODED_RECORDS_TABLE,
        [
            {"record_number": "R1", "latitude": 33.1, "longitude": -84.1, "geocoded_address": "Addr 1"},
            {"record_number": "R2", "latitude": 33.2, "longitude": -84.2, "geocoded_address": "Addr 2"},
        ],
    )
    seed_table(
        db_path,
        SCRAPED_FEES_TABLE,
        [
            {"record_number": "R1", "paid": 10.0, "outstanding": 1.0},
            {"record_number": "R2", "paid": 20.0, "outstanding": 2.0},
        ],
    )
    seed_table(
        db_path,
        PARSED_TREES_TABLE,
        [
            {"record_number": "R1", "tree_types": "oak"},
            {"record_number": "R2", "tree_types": "pine"},
        ],
    )

    export_geojson_pipeline.run(
        db_path=db_path,
        output_geojson_path=output_geojson_path,
        start=WINDOW_START,
        end=WINDOW_END,
    )

    payload = json.loads(output_geojson_path.read_text(encoding="utf-8"))
    feature_ids = [feature["id"] for feature in payload["features"]]
    assert feature_ids == ["R1"]


def test_run_emits_warning_and_uses_nulls_for_missing_fee_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    output_geojson_path = tmp_path / "data.geojson"

    seed_table(
        db_path,
        SCRAPED_RECORDS_TABLE,
        [
            {
                "record_number": "R1",
                "date": "05/01/2026",
                "date_iso": "2026-05-01",
                "record_type": "Type A",
                "permit_name": "Permit A",
                "status": "Fine",
                "description": "Desc A",
            },
            {
                "record_number": "R2",
                "date": "05/02/2026",
                "date_iso": "2026-05-02",
                "record_type": "Type B",
                "permit_name": "Permit B",
                "status": "Assigned",
                "description": "Desc B",
            },
        ],
    )
    seed_table(
        db_path,
        GEOCODED_RECORDS_TABLE,
        [
            {"record_number": "R1", "latitude": 33.1, "longitude": -84.1, "geocoded_address": "Addr 1"},
            {"record_number": "R2", "latitude": 33.2, "longitude": -84.2, "geocoded_address": "Addr 2"},
        ],
    )
    seed_table(db_path, SCRAPED_FEES_TABLE, [{"record_number": "R1", "paid": 10.0, "outstanding": 1.0}])
    seed_table(
        db_path,
        PARSED_TREES_TABLE,
        [
            {"record_number": "R1", "tree_types": "oak"},
            {"record_number": "R2", "tree_types": ""},
        ],
    )

    with pytest.warns(UserWarning, match="Missing fee information for 1 of 2 records"):
        export_geojson_pipeline.run(
            db_path=db_path,
            output_geojson_path=output_geojson_path,
            start=WINDOW_START,
            end=WINDOW_END,
        )

    payload = json.loads(output_geojson_path.read_text(encoding="utf-8"))
    feature_by_id = {feature["id"]: feature for feature in payload["features"]}
    assert feature_by_id["R2"]["properties"]["paid"] is None
    assert feature_by_id["R2"]["properties"]["outstanding"] is None
    assert feature_by_id["R1"]["properties"]["tree_types"] == ["oak"]
    assert feature_by_id["R2"]["properties"]["tree_types"] == []
    assert feature_by_id["R1"]["properties"]["address"] == "Addr 1"
    assert "geocoded_address" not in feature_by_id["R1"]["properties"]


def test_run_raises_when_required_columns_are_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    output_geojson_path = tmp_path / "data.geojson"

    seed_table(
        db_path,
        SCRAPED_RECORDS_TABLE,
        [{"record_number": "R1", "date": "05/01/2026", "date_iso": "2026-05-01"}],
    )
    seed_table(
        db_path,
        GEOCODED_RECORDS_TABLE,
        [{"record_number": "R1", "latitude": 33.1, "longitude": -84.1, "geocoded_address": "Addr"}],
    )
    seed_table(db_path, SCRAPED_FEES_TABLE, [{"record_number": "R1", "paid": 10.0, "outstanding": 1.0}])
    seed_table(db_path, PARSED_TREES_TABLE, [{"record_number": "R1", "tree_types": "oak"}])

    with pytest.raises(ValueError, match="Expected columns"):
        export_geojson_pipeline.run(
            db_path=db_path,
            output_geojson_path=output_geojson_path,
            start=WINDOW_START,
            end=WINDOW_END,
        )

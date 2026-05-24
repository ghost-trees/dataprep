import json
from pathlib import Path

import pandas as pd
import pytest

from dataprep.pipelines.export_geojson import pipeline as export_geojson_pipeline


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def test_run_writes_feature_collection_with_expected_mapping(tmp_path: Path) -> None:
    scraped_records_path = tmp_path / "scraped_records.csv"
    geocoded_records_path = tmp_path / "geocoded_records.csv"
    scraped_fees_path = tmp_path / "scraped_fees.csv"
    parsed_trees_path = tmp_path / "parsed_trees.csv"
    output_geojson_path = tmp_path / "data.geojson"

    _write_csv(
        scraped_records_path,
        [
            {
                "record_number": "R1",
                "date": "05/01/2026",
                "record_type": "Arborist Illegal Activity",
                "permit_name": "Illegal Removal",
                "status": "Fine",
                "description": "Removed two trees",
            }
        ],
    )
    _write_csv(
        geocoded_records_path,
        [
            {
                "record_number": "R1",
                "latitude": 33.1,
                "longitude": -84.1,
                "geocoded_address": "123 Main St, Atlanta, GA",
            }
        ],
    )
    _write_csv(scraped_fees_path, [{"record_number": "R1", "paid": 150.0, "outstanding": 25.0}])
    _write_csv(parsed_trees_path, [{"record_number": "R1", "tree_types": "hardwood|pine"}])

    written_path = export_geojson_pipeline.run(
        scraped_records_path=scraped_records_path,
        geocoded_records_path=geocoded_records_path,
        scraped_fees_path=scraped_fees_path,
        parsed_trees_path=parsed_trees_path,
        output_geojson_path=output_geojson_path,
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
        "tree_types": "hardwood|pine",
        "geocoded_address": "123 Main St, Atlanta, GA",
    }


def test_run_emits_warning_and_uses_nulls_for_missing_fee_rows(tmp_path: Path) -> None:
    scraped_records_path = tmp_path / "scraped_records.csv"
    geocoded_records_path = tmp_path / "geocoded_records.csv"
    scraped_fees_path = tmp_path / "scraped_fees.csv"
    parsed_trees_path = tmp_path / "parsed_trees.csv"
    output_geojson_path = tmp_path / "data.geojson"

    _write_csv(
        scraped_records_path,
        [
            {
                "record_number": "R1",
                "date": "05/01/2026",
                "record_type": "Type A",
                "permit_name": "Permit A",
                "status": "Fine",
                "description": "Desc A",
            },
            {
                "record_number": "R2",
                "date": "05/02/2026",
                "record_type": "Type B",
                "permit_name": "Permit B",
                "status": "Assigned",
                "description": "Desc B",
            },
        ],
    )
    _write_csv(
        geocoded_records_path,
        [
            {"record_number": "R1", "latitude": 33.1, "longitude": -84.1, "geocoded_address": "Addr 1"},
            {"record_number": "R2", "latitude": 33.2, "longitude": -84.2, "geocoded_address": "Addr 2"},
        ],
    )
    _write_csv(scraped_fees_path, [{"record_number": "R1", "paid": 10.0, "outstanding": 1.0}])
    _write_csv(
        parsed_trees_path,
        [
            {"record_number": "R1", "tree_types": "oak"},
            {"record_number": "R2", "tree_types": ""},
        ],
    )

    with pytest.warns(UserWarning, match="Missing fee information for 1 of 2 records"):
        export_geojson_pipeline.run(
            scraped_records_path=scraped_records_path,
            geocoded_records_path=geocoded_records_path,
            scraped_fees_path=scraped_fees_path,
            parsed_trees_path=parsed_trees_path,
            output_geojson_path=output_geojson_path,
        )

    payload = json.loads(output_geojson_path.read_text(encoding="utf-8"))
    feature_by_id = {feature["id"]: feature for feature in payload["features"]}
    assert feature_by_id["R2"]["properties"]["paid"] is None
    assert feature_by_id["R2"]["properties"]["outstanding"] is None


def test_run_raises_when_required_columns_are_missing(tmp_path: Path) -> None:
    scraped_records_path = tmp_path / "scraped_records.csv"
    geocoded_records_path = tmp_path / "geocoded_records.csv"
    scraped_fees_path = tmp_path / "scraped_fees.csv"
    parsed_trees_path = tmp_path / "parsed_trees.csv"
    output_geojson_path = tmp_path / "data.geojson"

    _write_csv(scraped_records_path, [{"record_number": "R1", "date": "05/01/2026"}])
    _write_csv(
        geocoded_records_path,
        [{"record_number": "R1", "latitude": 33.1, "longitude": -84.1, "geocoded_address": "Addr"}],
    )
    _write_csv(scraped_fees_path, [{"record_number": "R1", "paid": 10.0, "outstanding": 1.0}])
    _write_csv(parsed_trees_path, [{"record_number": "R1", "tree_types": "oak"}])

    with pytest.raises(ValueError, match="Expected columns"):
        export_geojson_pipeline.run(
            scraped_records_path=scraped_records_path,
            geocoded_records_path=geocoded_records_path,
            scraped_fees_path=scraped_fees_path,
            parsed_trees_path=parsed_trees_path,
            output_geojson_path=output_geojson_path,
        )

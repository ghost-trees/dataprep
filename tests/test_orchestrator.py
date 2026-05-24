from pathlib import Path

import pandas as pd

from dataprep import orchestrator


def test_run_pipeline_executes_stages_in_order_and_writes_output(
    tmp_path: Path, monkeypatch
) -> None:
    records_path = tmp_path / "scraped_records.csv"
    geocoded_path = tmp_path / "geocoded_records.csv"
    fees_path = tmp_path / "scraped_fees.csv"
    parsed_trees_output_path = tmp_path / "parsed_trees.csv"
    output_path = tmp_path / "output.csv"
    output_geojson_path = tmp_path / "data.geojson"
    call_order: list[str] = []

    def fake_run_records(output_csv: Path, headless: bool) -> Path:
        call_order.append("records")
        pd.DataFrame(
            {
                "record_number": ["R1"],
                "address": ["123 Main"],
                "status": ["Open"],
            }
        ).to_csv(output_csv, index=False)
        return output_csv

    def fake_run_geocode(input_csv_path: Path, output_csv_path: Path, workers: int):
        call_order.append("geocode")
        assert input_csv_path == records_path
        pd.DataFrame(
            {
                "record_number": ["R1"],
                "address": ["123 Main"],
                "latitude": [33.1],
                "longitude": [-84.1],
            }
        ).to_csv(output_csv_path, index=False)
        return pd.read_csv(output_csv_path)

    def fake_run_parse_trees(input_csv_path: Path, output_csv_path: Path) -> pd.DataFrame:
        call_order.append("parse_trees")
        assert input_csv_path == records_path
        tree_df = pd.DataFrame({"record_number": ["R1"], "tree_types": ["oak"]})
        tree_df.to_csv(output_csv_path, index=False)
        return tree_df

    def fake_run_fees(
        input_csv: Path,
        output_csv: Path,
        headless: bool,
        limit: int | None,
        workers: int,
    ) -> Path:
        call_order.append("fees")
        assert input_csv == geocoded_path
        pd.DataFrame(
            {
                "record_number": ["R1"],
                "paid": [10.0],
                "outstanding": [0.0],
                "scrape_status": ["success"],
            }
        ).to_csv(output_csv, index=False)
        return output_csv

    def fake_run_export_geojson(
        scraped_records_path: Path,
        geocoded_records_path: Path,
        scraped_fees_path: Path,
        parsed_trees_path: Path,
        output_geojson_path: Path,
    ) -> Path:
        call_order.append("export_geojson")
        assert scraped_records_path == records_path
        assert geocoded_records_path == geocoded_path
        assert scraped_fees_path == fees_path
        assert parsed_trees_path == parsed_trees_output_path
        output_geojson_path.write_text("{}", encoding="utf-8")
        return output_geojson_path

    monkeypatch.setattr(orchestrator, "run_records", fake_run_records)
    monkeypatch.setattr(orchestrator, "run_geocode", fake_run_geocode)
    monkeypatch.setattr(orchestrator, "run_parse_trees", fake_run_parse_trees)
    monkeypatch.setattr(orchestrator, "run_fees", fake_run_fees)
    monkeypatch.setattr(orchestrator, "run_export_geojson", fake_run_export_geojson)

    written_path = orchestrator.run_pipeline(
        scraped_records_path=records_path,
        geocoded_records_path=geocoded_path,
        scraped_fees_path=fees_path,
        parsed_trees_path=parsed_trees_output_path,
        output_path=output_path,
        output_geojson_path=output_geojson_path,
    )

    assert call_order == ["records", "parse_trees", "geocode", "fees", "export_geojson"]
    assert written_path == output_path
    output_df = pd.read_csv(output_path)
    assert output_df.loc[0, "record_number"] == "R1"
    assert output_df.loc[0, "paid"] == 10.0
    assert output_geojson_path.exists()

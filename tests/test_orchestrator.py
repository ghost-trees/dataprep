from pathlib import Path

from db_helpers import read_table_df, seed_table

from dataprep import orchestrator
from dataprep.shared.schema import (
    GEOCODED_RECORDS_TABLE,
    OUTPUT_TABLE,
    PARSED_TREES_TABLE,
    SCRAPED_FEES_TABLE,
    SCRAPED_RECORDS_TABLE,
)


def test_run_pipeline_executes_stages_in_order_and_writes_output(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    output_geojson_path = tmp_path / "data.geojson"
    call_order: list[str] = []

    def fake_run_scrape_records(db_path: Path, headless: bool) -> Path:
        call_order.append("records")
        seed_table(
            db_path,
            SCRAPED_RECORDS_TABLE,
            [
                {
                    "record_number": "R1",
                    "address": "123 Main",
                    "status": "Open",
                    "date": "05/01/2026",
                    "date_iso": "2026-05-01",
                }
            ],
        )
        return db_path

    def fake_run_parse_trees(db_path: Path):
        call_order.append("parse_trees")
        seed_table(db_path, PARSED_TREES_TABLE, [{"record_number": "R1", "tree_types": "oak"}])

    def fake_run_geocode_records(db_path: Path, workers: int):
        call_order.append("geocode")
        seed_table(
            db_path,
            GEOCODED_RECORDS_TABLE,
            [
                {
                    "record_number": "R1",
                    "address": "123 Main",
                    "latitude": 33.1,
                    "longitude": -84.1,
                    "geocoded_address": "123 Main St, Atlanta, GA",
                }
            ],
        )

    def fake_run_scrape_fees(db_path: Path, headless: bool, limit: int | None, workers: int) -> Path:
        call_order.append("fees")
        seed_table(
            db_path,
            SCRAPED_FEES_TABLE,
            [
                {
                    "record_number": "R1",
                    "paid": 10.0,
                    "outstanding": 0.0,
                    "scrape_status": "success",
                }
            ],
        )
        return db_path

    def fake_run_export_csv(db_path: Path, start: str, end: str) -> list[Path]:
        call_order.append("export_csv")
        return []

    def fake_run_export_geojson(
        db_path: Path, output_geojson_path: Path, start: str, end: str
    ) -> Path:
        call_order.append("export_geojson")
        output_geojson_path.write_text("{}", encoding="utf-8")
        return output_geojson_path

    monkeypatch.setattr(orchestrator, "run_scrape_records", fake_run_scrape_records)
    monkeypatch.setattr(orchestrator, "run_geocode_records", fake_run_geocode_records)
    monkeypatch.setattr(orchestrator, "run_parse_trees", fake_run_parse_trees)
    monkeypatch.setattr(orchestrator, "run_scrape_fees", fake_run_scrape_fees)
    monkeypatch.setattr(orchestrator, "run_export_csv", fake_run_export_csv)
    monkeypatch.setattr(orchestrator, "run_export_geojson", fake_run_export_geojson)

    returned_path = orchestrator.run_pipeline(
        db_path=db_path,
        output_geojson_path=output_geojson_path,
        export_start="2026-01-01",
        export_end="2026-12-31",
    )

    assert call_order == ["records", "parse_trees", "geocode", "fees", "export_csv", "export_geojson"]
    assert returned_path == db_path

    output_df = read_table_df(db_path, OUTPUT_TABLE)
    assert output_df.loc[0, "record_number"] == "R1"
    assert output_df.loc[0, "paid"] == 10.0
    assert output_geojson_path.exists()

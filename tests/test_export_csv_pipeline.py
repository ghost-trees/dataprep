from pathlib import Path

import pandas as pd
from db_helpers import seed_table

from dataprep.pipelines.export_csv import pipeline as export_csv_pipeline
from dataprep.shared.exports import CsvExportSpec
from dataprep.shared.schema import (
    DATE_ISO_COLUMN,
    GEOCODED_RECORDS_TABLE,
    SCRAPED_RECORDS_TABLE,
)


def _seed_two_window_records(db_path: Path) -> None:
    seed_table(
        db_path,
        SCRAPED_RECORDS_TABLE,
        [
            {"record_number": "R1", "address": "in", "date": "06/01/2025", "date_iso": "2025-06-01"},
            {"record_number": "R2", "address": "out", "date": "06/01/2024", "date_iso": "2024-06-01"},
        ],
    )
    seed_table(
        db_path,
        GEOCODED_RECORDS_TABLE,
        [
            {"record_number": "R1", "latitude": 33.1, "longitude": -84.1},
            {"record_number": "R2", "latitude": 33.2, "longitude": -84.2},
        ],
    )


def _tmp_specs(tmp_path: Path) -> list[CsvExportSpec]:
    return [
        CsvExportSpec(
            "scraped_records",
            SCRAPED_RECORDS_TABLE,
            tmp_path / "scraped_records.csv",
            date_column=DATE_ISO_COLUMN,
        ),
        CsvExportSpec(
            "geocoded_records",
            GEOCODED_RECORDS_TABLE,
            tmp_path / "geocoded_records.csv",
        ),
    ]


def test_default_window_subsets_rows_and_semijoins_undated_tables(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    _seed_two_window_records(db_path)
    monkeypatch.setattr(export_csv_pipeline, "CSV_EXPORTS", _tmp_specs(tmp_path))

    export_csv_pipeline.run(db_path=db_path, start="2025-01-01", end="2025-12-31")

    records_csv = pd.read_csv(tmp_path / "scraped_records.csv")
    geocoded_csv = pd.read_csv(tmp_path / "geocoded_records.csv")

    assert records_csv["record_number"].tolist() == ["R1"]
    assert geocoded_csv["record_number"].tolist() == ["R1"]


def test_export_all_dumps_full_tables(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    _seed_two_window_records(db_path)
    monkeypatch.setattr(export_csv_pipeline, "CSV_EXPORTS", _tmp_specs(tmp_path))

    export_csv_pipeline.run(db_path=db_path, start="2025-01-01", end="2025-12-31", export_all=True)

    records_csv = pd.read_csv(tmp_path / "scraped_records.csv")
    geocoded_csv = pd.read_csv(tmp_path / "geocoded_records.csv")

    assert sorted(records_csv["record_number"].tolist()) == ["R1", "R2"]
    assert sorted(geocoded_csv["record_number"].tolist()) == ["R1", "R2"]


def test_only_filters_exports(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    _seed_two_window_records(db_path)
    monkeypatch.setattr(export_csv_pipeline, "CSV_EXPORTS", _tmp_specs(tmp_path))

    export_csv_pipeline.run(
        db_path=db_path, start="2025-01-01", end="2025-12-31", only=["scraped_records"]
    )

    assert (tmp_path / "scraped_records.csv").exists()
    assert not (tmp_path / "geocoded_records.csv").exists()

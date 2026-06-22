from pathlib import Path

import pandas as pd
import pytest
from db_helpers import read_table_df, seed_table
from geopy.exc import GeocoderServiceError, GeocoderTimedOut

from dataprep.pipelines.geocode_records import pipeline as geocode_pipeline
from dataprep.shared.db import get_connection, table_exists
from dataprep.shared.schema import GEOCODED_RECORDS_TABLE, SCRAPED_RECORDS_TABLE

FIXTURE_OVERRIDES_PATH = Path(__file__).parent / "fixtures" / "geocode_overrides.csv"


def test_geocode_address_raises_timeout() -> None:
    def raise_timeout(_address: str):
        raise GeocoderTimedOut("timeout")

    with pytest.raises(GeocoderTimedOut, match="timeout"):
        geocode_pipeline.geocode_address(raise_timeout, "123 Main")


def test_run_raises_when_required_columns_are_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(db_path, SCRAPED_RECORDS_TABLE, [{"record_number": "R1"}])

    with pytest.raises(ValueError, match="Expected columns"):
        geocode_pipeline.run(db_path=db_path, workers=1)


def test_run_writes_expected_columns_with_mock_parallel(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(
        db_path,
        SCRAPED_RECORDS_TABLE,
        [
            {"record_number": "R1", "address": "123 Main"},
            {"record_number": "R2", "address": "234 Pine"},
        ],
    )

    def fake_geocode_in_parallel(addresses, workers):
        assert addresses == ["123 Main", "234 Pine"]
        assert workers == 2
        return [
            (33.1, -84.1, "123 Main St, City, State"),
            (33.2, -84.2, "234 Pine Rd, City, State"),
        ], 2

    monkeypatch.setattr(geocode_pipeline, "preflight_geocode_check", lambda _addresses: None)
    monkeypatch.setattr(geocode_pipeline, "geocode_in_parallel", fake_geocode_in_parallel)

    result_df = geocode_pipeline.run(db_path=db_path, workers=2)

    assert list(result_df.columns) == [
        "record_number",
        "address",
        "latitude",
        "longitude",
        "geocoded_address",
    ]
    assert result_df["geocoded_address"].tolist() == [
        "123 Main St, City, State",
        "234 Pine Rd, City, State",
    ]

    connection = get_connection(db_path)
    try:
        assert table_exists(connection, GEOCODED_RECORDS_TABLE)
    finally:
        connection.close()


def test_run_aborts_on_preflight_tls_failure(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(db_path, SCRAPED_RECORDS_TABLE, [{"record_number": "R1", "address": "123 Main"}])

    def raise_tls_error(_address: str):
        raise GeocoderServiceError("CERTIFICATE_VERIFY_FAILED")

    monkeypatch.setattr(geocode_pipeline, "build_geocode_callable", lambda: raise_tls_error)
    monkeypatch.setattr(
        geocode_pipeline,
        "geocode_in_parallel",
        lambda _addresses, _workers: pytest.fail("geocode_in_parallel should not run on preflight failure"),
    )

    with pytest.raises(RuntimeError, match="preflight check"):
        geocode_pipeline.run(db_path=db_path, workers=1)

    connection = get_connection(db_path)
    try:
        assert not table_exists(connection, GEOCODED_RECORDS_TABLE)
    finally:
        connection.close()


def test_run_applies_override_when_geocode_fails(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(db_path, SCRAPED_RECORDS_TABLE, [{"record_number": "R1", "address": "123 Main"}])

    monkeypatch.setattr(geocode_pipeline, "preflight_geocode_check", lambda _addresses: None)
    monkeypatch.setattr(
        geocode_pipeline,
        "geocode_in_parallel",
        lambda _addresses, _workers: ([(None, None, None)], 0),
    )

    geocode_pipeline.run(db_path=db_path, workers=1, overrides_path=FIXTURE_OVERRIDES_PATH)

    output_df = read_table_df(db_path, GEOCODED_RECORDS_TABLE)
    row = output_df.set_index("record_number").loc["R1"]
    assert row["latitude"] == 33.5
    assert row["longitude"] == -84.5
    assert row["geocoded_address"] == "100 Override St, Atlanta GA"


def test_run_prefers_geocode_result_over_override(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(db_path, SCRAPED_RECORDS_TABLE, [{"record_number": "R1", "address": "123 Main"}])

    monkeypatch.setattr(geocode_pipeline, "preflight_geocode_check", lambda _addresses: None)
    monkeypatch.setattr(
        geocode_pipeline,
        "geocode_in_parallel",
        lambda _addresses, _workers: ([(33.1, -84.1, "123 Main St, City, State")], 1),
    )

    geocode_pipeline.run(db_path=db_path, workers=1, overrides_path=FIXTURE_OVERRIDES_PATH)

    output_df = read_table_df(db_path, GEOCODED_RECORDS_TABLE)
    row = output_df.set_index("record_number").loc["R1"]
    assert row["latitude"] == 33.1
    assert row["longitude"] == -84.1
    assert row["geocoded_address"] == "123 Main St, City, State"


def test_run_without_overrides_file_leaves_failures_null(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(db_path, SCRAPED_RECORDS_TABLE, [{"record_number": "R1", "address": "123 Main"}])

    monkeypatch.setattr(geocode_pipeline, "preflight_geocode_check", lambda _addresses: None)
    monkeypatch.setattr(
        geocode_pipeline,
        "geocode_in_parallel",
        lambda _addresses, _workers: ([(None, None, None)], 0),
    )

    geocode_pipeline.run(
        db_path=db_path, workers=1, overrides_path=tmp_path / "missing_overrides.csv"
    )

    output_df = read_table_df(db_path, GEOCODED_RECORDS_TABLE)
    row = output_df.set_index("record_number").loc["R1"]
    assert pd.isna(row["latitude"])
    assert pd.isna(row["longitude"])

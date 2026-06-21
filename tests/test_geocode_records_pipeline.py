from pathlib import Path

import pytest
from db_helpers import seed_table
from geopy.exc import GeocoderServiceError, GeocoderTimedOut

from dataprep.pipelines.geocode_records import pipeline as geocode_pipeline
from dataprep.shared.db import get_connection, table_exists
from dataprep.shared.schema import GEOCODED_RECORDS_TABLE, SCRAPED_RECORDS_TABLE


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

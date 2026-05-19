from pathlib import Path

import pandas as pd
import pytest
from geopy.exc import GeocoderTimedOut

from dataprep.pipelines.geocode import pipeline as geocode_pipeline


def test_geocode_address_handles_timeout() -> None:
    def raise_timeout(_address: str):
        raise GeocoderTimedOut("timeout")

    lat, lon = geocode_pipeline.geocode_address(raise_timeout, "123 Main")
    assert (lat, lon) == (None, None)


def test_run_raises_when_required_columns_are_missing(tmp_path: Path) -> None:
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"
    pd.DataFrame({"record_number": ["R1"]}).to_csv(input_csv, index=False)

    with pytest.raises(ValueError, match="Expected columns"):
        geocode_pipeline.run(input_csv_path=input_csv, output_csv_path=output_csv, workers=1)


def test_run_writes_expected_columns_with_mock_parallel(tmp_path: Path, monkeypatch) -> None:
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"
    pd.DataFrame(
        {
            "record_number": ["R1", "R2"],
            "address": ["123 Main", "234 Pine"],
        }
    ).to_csv(input_csv, index=False)

    def fake_geocode_in_parallel(addresses, workers):
        assert addresses == ["123 Main", "234 Pine"]
        assert workers == 2
        return [(33.1, -84.1), (33.2, -84.2)], 2

    monkeypatch.setattr(geocode_pipeline, "geocode_in_parallel", fake_geocode_in_parallel)

    result_df = geocode_pipeline.run(input_csv_path=input_csv, output_csv_path=output_csv, workers=2)

    assert list(result_df.columns) == ["record_number", "address", "latitude", "longitude"]
    assert output_csv.exists()

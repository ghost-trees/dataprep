from dataprep.shared.paths import (
    DATA_DIR,
    GEOCODED_RECORDS_PATH,
    OUTPUT_PATH,
    SCRAPED_FEES_PATH,
    SCRAPED_RECORDS_PATH,
)


def test_default_outputs_are_under_data_dir() -> None:
    assert SCRAPED_RECORDS_PATH.parent == DATA_DIR
    assert GEOCODED_RECORDS_PATH.parent == DATA_DIR
    assert SCRAPED_FEES_PATH.parent == DATA_DIR
    assert OUTPUT_PATH.parent == DATA_DIR


def test_default_output_filenames_are_stable() -> None:
    assert SCRAPED_RECORDS_PATH.name == "scraped_records.csv"
    assert GEOCODED_RECORDS_PATH.name == "geocoded_records.csv"
    assert SCRAPED_FEES_PATH.name == "scraped_fees.csv"
    assert OUTPUT_PATH.name == "output.csv"

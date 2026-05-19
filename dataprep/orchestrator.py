"""Top-level pipeline orchestration."""

from pathlib import Path

from dataprep.pipelines.fees.pipeline import run as run_fees
from dataprep.pipelines.geocode.pipeline import run as run_geocode
from dataprep.pipelines.records.pipeline import run as run_records
from dataprep.shared.paths import (
    GEOCODED_RECORDS_PATH,
    OUTPUT_PATH,
    SCRAPED_FEES_PATH,
    SCRAPED_RECORDS_PATH,
)

from .merge import merge_output, validate_no_nulls


def run_pipeline(
    scraped_records_path: Path = SCRAPED_RECORDS_PATH,
    geocoded_records_path: Path = GEOCODED_RECORDS_PATH,
    scraped_fees_path: Path = SCRAPED_FEES_PATH,
    output_path: Path = OUTPUT_PATH,
    geocode_workers: int = 1,
    fee_workers: int = 5,
    fees_headless: bool = True,
    fees_limit: int | None = None,
    records_headless: bool = False,
) -> Path:
    """Run records, geocode, fees, merge, and validation."""
    print("Starting pipeline...")
    run_records(output_csv=scraped_records_path, headless=records_headless)
    run_geocode(
        input_csv_path=scraped_records_path,
        output_csv_path=geocoded_records_path,
        workers=geocode_workers,
    )
    run_fees(
        input_csv=geocoded_records_path,
        output_csv=scraped_fees_path,
        headless=fees_headless,
        limit=fees_limit,
        workers=fee_workers,
    )

    print("Merging datasets...")
    output_df = merge_output(scraped_records_path, geocoded_records_path, scraped_fees_path)
    print("Validating output for null values...")
    validate_no_nulls(output_df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    print(
        "Pipeline finished successfully. "
        f"Wrote {len(output_df)} rows and {len(output_df.columns)} columns to {output_path}"
    )
    return output_path

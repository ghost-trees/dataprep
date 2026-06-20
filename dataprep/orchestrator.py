"""Top-level pipeline orchestration."""

from pathlib import Path

from dataprep.pipelines.export_csv.pipeline import run as run_export_csv
from dataprep.pipelines.export_geojson.pipeline import run as run_export_geojson
from dataprep.pipelines.fees.pipeline import run as run_fees
from dataprep.pipelines.geocode.pipeline import run as run_geocode
from dataprep.pipelines.parse_trees.pipeline import run as run_parse_trees
from dataprep.pipelines.records.pipeline import run as run_records
from dataprep.shared.db import DB_PATH, get_connection, init_db, write_table
from dataprep.shared.exports import CSV_EXPORT_END, CSV_EXPORT_START
from dataprep.shared.paths import DATA_GEOJSON_PATH
from dataprep.shared.schema import OUTPUT_TABLE

from .merge import merge_output, validate_no_nulls


def run_pipeline(
    db_path: Path = DB_PATH,
    output_geojson_path: Path = DATA_GEOJSON_PATH,
    export_start: str = CSV_EXPORT_START,
    export_end: str = CSV_EXPORT_END,
    geocode_workers: int = 1,
    fee_workers: int = 5,
    fees_headless: bool = True,
    fees_limit: int | None = None,
    records_headless: bool = False,
) -> Path:
    """Run the full dataprep workflow through final GeoJSON export.

    Pipeline stages write to the SQLite database as the source of truth. The
    merged ``output`` table is then exported, along with curated CSV snapshots
    and a windowed `data.geojson` artifact.
    """
    print("Starting pipeline...")
    init_db(db_path)
    run_records(db_path=db_path, headless=records_headless)
    run_parse_trees(db_path=db_path)
    run_geocode(db_path=db_path, workers=geocode_workers)
    run_fees(
        db_path=db_path,
        headless=fees_headless,
        limit=fees_limit,
        workers=fee_workers,
    )

    print("Merging datasets...")
    output_df = merge_output(db_path)
    print("Validating output for null values...")
    validate_no_nulls(output_df)

    connection = get_connection(db_path)
    try:
        write_table(connection, OUTPUT_TABLE, output_df, dataset_name="output")
    finally:
        connection.close()

    print("Exporting curated CSV snapshots...")
    run_export_csv(db_path=db_path, start=export_start, end=export_end)
    run_export_geojson(
        db_path=db_path,
        output_geojson_path=output_geojson_path,
        start=export_start,
        end=export_end,
    )
    print(
        "Pipeline finished successfully. "
        f"Wrote {len(output_df)} rows and {len(output_df.columns)} columns to "
        f"'{OUTPUT_TABLE}' in {db_path}. GeoJSON output: {output_geojson_path}"
    )
    return Path(db_path)

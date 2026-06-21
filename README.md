# Ghost Trees (ghost-trees/dataprep)
Data pipeline for Ghost Trees web application.

## CLI Commands

- Run all: runs the full dataprep workflow end-to-end through GeoJSON export with `uv run python -m dataprep` (args in [`dataprep/cli.py`](dataprep/cli.py)).
- Scrape records: scrapes permit records from the ACA portal into the `scraped_records` table with `uv run python -m dataprep.pipelines.scrape_records.cli` (args in [`dataprep/pipelines/scrape_records/cli.py`](dataprep/pipelines/scrape_records/cli.py)).
- Parse trees: parses tree mentions from scraped record text into the `parsed_trees` table with `uv run python -m dataprep.pipelines.parse_trees.cli` (args in [`dataprep/pipelines/parse_trees/cli.py`](dataprep/pipelines/parse_trees/cli.py)).
- Geocode records: geocodes record addresses into the `geocoded_records` table with `uv run python -m dataprep.pipelines.geocode_records.cli` (args in [`dataprep/pipelines/geocode_records/cli.py`](dataprep/pipelines/geocode_records/cli.py)).
- Scrape fees: scrapes paid/outstanding fee data into the `scraped_fees` table with `uv run python -m dataprep.pipelines.scrape_fees.cli` (args in [`dataprep/pipelines/scrape_fees/cli.py`](dataprep/pipelines/scrape_fees/cli.py)).
- Export CSV: re-exports curated CSV snapshots from SQLite into `data/` with `uv run python -m dataprep.pipelines.export_csv` (args in [`dataprep/pipelines/export_csv/cli.py`](dataprep/pipelines/export_csv/cli.py)).
- Export GeoJSON: builds `data.geojson` from the output table for a date window with `uv run python -m dataprep.pipelines.export_geojson.cli` (args in [`dataprep/pipelines/export_geojson/cli.py`](dataprep/pipelines/export_geojson/cli.py)).

## Code Documentation Standards

Documentation and docstring conventions are in [`docs_style.md`](docs_style.md).

## Contributing

See [`contributing guide`](CONTRIBUTING.md) to get started.

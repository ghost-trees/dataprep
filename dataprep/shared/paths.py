"""Common filesystem paths for dataprep outputs."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

DB_PATH = DATA_DIR / "dataprep.sqlite3"

SCRAPED_RECORDS_PATH = DATA_DIR / "scraped_records.csv"
GEOCODED_RECORDS_PATH = DATA_DIR / "geocoded_records.csv"
SCRAPED_FEES_PATH = DATA_DIR / "scraped_fees.csv"
PARSED_TREES_PATH = DATA_DIR / "parsed_trees.csv"
OUTPUT_PATH = DATA_DIR / "output.csv"
DATA_GEOJSON_PATH = DATA_DIR / "data.geojson"

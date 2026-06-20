"""Canonical dataset schema used across dataprep pipelines."""

from collections.abc import Sequence

RECORD_NUMBER_COLUMN = "record_number"
ADDRESS_COLUMN = "address"
LATITUDE_COLUMN = "latitude"
LONGITUDE_COLUMN = "longitude"
GEOCODED_ADDRESS_COLUMN = "geocoded_address"
PAID_COLUMN = "paid"
OUTSTANDING_COLUMN = "outstanding"
SCRAPE_STATUS_COLUMN = "scrape_status"
TREE_TYPES_COLUMN = "tree_types"
DATE_COLUMN = "date"
DATE_ISO_COLUMN = "date_iso"
RECORD_TYPE_COLUMN = "record_type"
PERMIT_NAME_COLUMN = "permit_name"
STATUS_COLUMN = "status"
DESCRIPTION_COLUMN = "description"
SHORT_NOTES_COLUMN = "short_notes"

SCRAPED_RECORDS_TABLE = "scraped_records"
GEOCODED_RECORDS_TABLE = "geocoded_records"
SCRAPED_FEES_TABLE = "scraped_fees"
PARSED_TREES_TABLE = "parsed_trees"
OUTPUT_TABLE = "output"

SCRAPED_RECORDS_ACA_COLUMNS: tuple[str, ...] = (
    DATE_COLUMN,
    RECORD_NUMBER_COLUMN,
    RECORD_TYPE_COLUMN,
    ADDRESS_COLUMN,
    DESCRIPTION_COLUMN,
    PERMIT_NAME_COLUMN,
    STATUS_COLUMN,
    SHORT_NOTES_COLUMN,
)

GEOCODE_OUTPUT_COLUMNS = [
    RECORD_NUMBER_COLUMN,
    ADDRESS_COLUMN,
    LATITUDE_COLUMN,
    LONGITUDE_COLUMN,
    GEOCODED_ADDRESS_COLUMN,
]

FEE_OUTPUT_COLUMNS = [
    RECORD_NUMBER_COLUMN,
    PAID_COLUMN,
    OUTSTANDING_COLUMN,
    SCRAPE_STATUS_COLUMN,
]

PARSE_TREES_OUTPUT_COLUMNS = [
    RECORD_NUMBER_COLUMN,
    TREE_TYPES_COLUMN,
]


def assert_aca_export_schema(columns: Sequence[str]) -> None:
    """Validate the normalized ACA export schema before ingest.

    Empty header values are ignored. ACA downloads can include a trailing comma,
    which appears as an empty CSV field name.
    """
    found_columns = [column.strip() for column in columns if str(column).strip()]
    expected_set = set(SCRAPED_RECORDS_ACA_COLUMNS)
    found_set = set(found_columns)
    missing_columns = sorted(expected_set - found_set)
    unexpected_columns = sorted(found_set - expected_set)
    if missing_columns or unexpected_columns:
        raise ValueError(
            "ACA export schema mismatch. "
            f"Expected columns: {list(SCRAPED_RECORDS_ACA_COLUMNS)}. "
            f"Missing: {missing_columns}. "
            f"Unexpected: {unexpected_columns}. "
            f"Found: {found_columns}"
        )

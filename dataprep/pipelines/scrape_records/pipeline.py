"""Record scraping pipeline."""

import csv
import tempfile
from collections import Counter
from pathlib import Path

from playwright.sync_api import Download, Playwright, sync_playwright

from dataprep.shared.db import DEFAULT_DB_PATH, get_connection
from dataprep.shared.normalize import to_snake_case
from dataprep.shared.portal import (
    ACA_FRAME_NAME,
    ACA_FRAME_SELECTOR,
    PORTAL_URL,
    click_find_application_link,
)
from dataprep.shared.schema import SCRAPED_RECORDS_TABLE, assert_aca_export_schema

from .io import RecordsIngestSummary, ingest_scraped_records_csv

PERMIT_TYPE = "Building/Arborist/Illegal Activity/NA"
START_DATE_SELECTOR = "#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate"
END_DATE_SELECTOR = "#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate"
DEFAULT_START_DATE = "01/01/2023"
DEFAULT_END_DATE = "12/31/2025"


def _normalize_csv_headers_to_snake_case(csv_path: str | Path) -> None:
    csv_file_path = Path(csv_path)
    with csv_file_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        original_fieldnames = reader.fieldnames or []
        snake_case_fieldnames = [to_snake_case(fieldname) for fieldname in original_fieldnames]
        rows = list(reader)

    with csv_file_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=snake_case_fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({to_snake_case(column_name): value for column_name, value in row.items()})


def _assert_unique_record_numbers(csv_path: str | Path) -> None:
    with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if "record_number" not in (reader.fieldnames or []):
            raise ValueError("Missing 'record_number' column in scraped records CSV.")

        record_numbers = [
            row["record_number"].strip() for row in reader if row.get("record_number", "").strip()
        ]

    duplicate_record_numbers = [
        record_number for record_number, count in Counter(record_numbers).items() if count > 1
    ]
    if duplicate_record_numbers:
        preview = ", ".join(sorted(duplicate_record_numbers)[:10])
        if len(duplicate_record_numbers) > 10:
            preview = f"{preview}, ..."
        raise ValueError(
            "Duplicate record numbers found in scraped records CSV "
            f"({len(duplicate_record_numbers)} duplicated values): {preview}"
        )


def _deduplicate_exact_rows(csv_path: str | Path) -> int:
    csv_file_path = Path(csv_path)
    with csv_file_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    seen_rows: set[tuple[str, ...]] = set()
    deduplicated_rows: list[dict[str, str]] = []
    for row in rows:
        row_key = tuple(row.get(column_name, "") for column_name in fieldnames)
        if row_key in seen_rows:
            continue
        seen_rows.add(row_key)
        deduplicated_rows.append(row)

    removed_rows = len(rows) - len(deduplicated_rows)
    if removed_rows > 0:
        with csv_file_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(deduplicated_rows)

    return removed_rows


def _read_csv_fieldnames(csv_path: str | Path) -> list[str]:
    with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return reader.fieldnames or []


def run(
    db_path: Path = DEFAULT_DB_PATH,
    permit_type: str = PERMIT_TYPE,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    playwright: Playwright | None = None,
    headless: bool = False,
) -> Path:
    """Scrape records from ACA and merge/upsert into the scraped_records table."""
    if playwright is None:
        with sync_playwright() as managed_playwright:
            return run(
                db_path=db_path,
                permit_type=permit_type,
                start_date=start_date,
                end_date=end_date,
                playwright=managed_playwright,
                headless=headless,
            )

    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    try:
        page = context.new_page()
        page.goto(PORTAL_URL)
        page.wait_for_selector(ACA_FRAME_SELECTOR, timeout=20_000)

        frame_locator = page.frame_locator(ACA_FRAME_SELECTOR)
        click_find_application_link(frame_locator)

        frame = page.frame(name=ACA_FRAME_NAME)
        if frame is None:
            raise RuntimeError("ACAFrame iframe not found.")

        frame.get_by_label("Permit Type:").select_option(permit_type)

        start_date_input = frame.locator(START_DATE_SELECTOR)
        start_date_input.click()
        start_date_input.fill(start_date)

        end_date_input = frame.locator(END_DATE_SELECTOR)
        end_date_input.click()
        end_date_input.fill(end_date)

        frame.get_by_role("link", name="Search", exact=True).click()

        with page.expect_download() as downloaded_data:
            frame.get_by_role("link", name="Download results").click()

        download: Download = downloaded_data.value
        with tempfile.TemporaryDirectory() as temp_dir:
            download_csv = Path(temp_dir) / "scraped_records.csv"
            download.save_as(str(download_csv))
            _normalize_csv_headers_to_snake_case(download_csv)
            assert_aca_export_schema(_read_csv_fieldnames(download_csv))
            exact_duplicates_removed = _deduplicate_exact_rows(download_csv)
            _assert_unique_record_numbers(download_csv)
            connection = get_connection(db_path)
            try:
                summary = ingest_scraped_records_csv(
                    connection,
                    download_csv,
                    exact_duplicates_removed=exact_duplicates_removed,
                )
            finally:
                connection.close()

        _print_summary(permit_type, start_date, end_date, summary)
        return Path(db_path)
    finally:
        context.close()
        browser.close()


def _print_summary(
    permit_type: str,
    start_date: str,
    end_date: str,
    summary: RecordsIngestSummary,
) -> None:
    print("Starting record scrape")
    print(f"- Permit type: {permit_type}")
    print(f"- Date range: {start_date} to {end_date}")
    print(f"- Downloaded rows: {summary.downloaded_rows}")
    print(f"- Exact duplicate rows removed: {summary.exact_duplicates_removed}")
    print(f"- Prior records in database: {summary.prior_records}")
    print(f"- Overlapping record numbers: {summary.overlapping_records}")
    print(f"  - Unchanged: {summary.unchanged_records}")
    print(f"  - Updated from scrape: {summary.updated_records}")
    print(f"- New record numbers: {summary.new_records}")
    print(f"- Prior records preserved (not in scrape): {summary.preserved_records}")
    print("Finished record scrape")
    print(f"- Rows written: {summary.total_written}")
    print(f"- Output table: {SCRAPED_RECORDS_TABLE}")

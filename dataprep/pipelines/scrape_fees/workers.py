"""Worker process logic for queue-driven fee scraping."""

import multiprocessing as mp

from playwright.sync_api import Page, TimeoutError, sync_playwright

from dataprep.shared.portal import initialize_search

from .constants import STATUS_FAILED, STATUS_SUCCESS
from .portal import open_fees_page, scrape_fee_totals
from .types import FeeRow, WorkerResult


def failed_result_row(record_number: str) -> FeeRow:
    """Build a standardized failed result row."""
    return {
        "record_number": record_number,
        "paid": 0.0,
        "outstanding": 0.0,
        "scrape_status": STATUS_FAILED,
    }


def scrape_single_record(page: Page, record_number: str, worker_id: int) -> WorkerResult:
    """Scrape fees for one record and build a queue-ready result."""
    print(f"[worker-{worker_id}] Scraping {record_number}...")
    paid = 0.0
    outstanding = 0.0
    scrape_status = STATUS_FAILED

    try:
        try:
            frame = open_fees_page(page, record_number)
        except TimeoutError:
            print(f"[worker-{worker_id}] Search timed out, reinitializing and retrying...")
            initialize_search(page)
            frame = open_fees_page(page, record_number)
        paid, outstanding = scrape_fee_totals(frame)
        scrape_status = STATUS_SUCCESS
        print(
            f"[worker-{worker_id}] Success {record_number}: paid={paid}, outstanding={outstanding}"
        )
    except Exception as exc:
        print(f"[worker-{worker_id}] Warning: failed to scrape {record_number}: {exc}")

    row: FeeRow = {
        "record_number": record_number,
        "paid": paid,
        "outstanding": outstanding,
        "scrape_status": scrape_status,
    }
    return row, scrape_status == STATUS_SUCCESS


def worker_loop(
    worker_id: int,
    headless: bool,
    record_queue: mp.Queue,
    result_queue: mp.Queue,
) -> None:
    """Consume record IDs from a queue and emit scrape results."""
    print(f"[worker-{worker_id}] Worker online")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()
            initialize_search(page)

            while True:
                record_number = record_queue.get()
                if record_number is None:
                    break
                row, success = scrape_single_record(page, record_number, worker_id)
                result_queue.put((row, success))

            context.close()
            browser.close()
    except Exception as exc:
        print(f"[worker-{worker_id}] Worker startup failed: {exc}")
        while True:
            record_number = record_queue.get()
            if record_number is None:
                break
            result_queue.put((failed_result_row(record_number), False))

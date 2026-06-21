"""Pipeline orchestration for parallel fee scraping jobs."""

import multiprocessing as mp
from pathlib import Path

from dataprep.shared.db import DEFAULT_DB_PATH, get_connection
from dataprep.shared.schema import SCRAPED_FEES_TABLE

from .io import (
    merge_rows_by_input_order,
    read_existing_results,
    read_record_numbers,
    write_results,
)
from .types import FeeRow
from .workers import worker_loop


def run(
    db_path: Path = DEFAULT_DB_PATH,
    headless: bool = True,
    limit: int | None = None,
    workers: int = 5,
) -> Path:
    """Run the end-to-end fee scraping workflow against the SQLite database."""
    connection = get_connection(db_path)
    try:
        records = read_record_numbers(connection, limit=limit)
        existing_rows, success_records, failed_records = read_existing_results(connection)
        pending_records = [record for record in records if record not in success_records]
        retry_records = [record for record in records if record in failed_records]

        print("Starting fee scrape")
        print(f"- Input records: {len(records)}")
        print(
            f"- Prior successful records (will skip): "
            f"{len(success_records.intersection(records))}"
        )
        print(f"- Prior failed records (will retry): {len(retry_records)}")
        print(f"- Pending scrape: {len(pending_records)}")

        if not pending_records:
            print("No pending records to scrape. Output already up to date.")
            return Path(db_path)

        new_results: list[FeeRow] = []
        scraped_count = 0
        failed_count = 0
        skipped_count = len(success_records.intersection(records))
        worker_count = min(workers, len(pending_records))

        print(f"- Workers: {worker_count}")
        context = mp.get_context("spawn")
        record_queue: mp.Queue = context.Queue()
        result_queue: mp.Queue = context.Queue()

        for record_number in pending_records:
            record_queue.put(record_number)
        for _ in range(worker_count):
            record_queue.put(None)

        processes: list[mp.Process] = []
        for worker_id in range(1, worker_count + 1):
            process = context.Process(
                target=worker_loop,
                args=(worker_id, headless, record_queue, result_queue),
            )
            process.start()
            processes.append(process)

        for _ in range(len(pending_records)):
            row, success = result_queue.get()
            new_results.append(row)
            if success:
                scraped_count += 1
            else:
                failed_count += 1

        for process in processes:
            process.join()
            if process.exitcode not in (0, None):
                print(f"Worker pid={process.pid} exited with code {process.exitcode}")

        merged_results = merge_rows_by_input_order(records, existing_rows, new_results)
        write_results(connection, merged_results)
    finally:
        connection.close()

    print("Finished fee scrape")
    print(f"- Scraped this run: {scraped_count}")
    print(f"- Skipped this run: {skipped_count}")
    print(f"- Failed this run: {failed_count}")
    print(f"- Total rows written: {len(merged_results)}")
    print(f"- Output table: {SCRAPED_FEES_TABLE}")
    return Path(db_path)

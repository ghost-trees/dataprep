"""Pipeline orchestration for parallel fee scraping jobs."""

import multiprocessing as mp
from pathlib import Path

from .io import (
    merge_rows_by_input_order,
    read_existing_results,
    read_record_numbers,
    write_results,
)
from .types import FeeRow
from .workers import worker_loop


def run(
    input_csv: Path, output_csv: Path, headless: bool, limit: int | None, workers: int
) -> None:
    """Run the end-to-end fee scraping workflow.

    This function reads input records, skips already successful records, retries
    prior failures, dispatches pending records to multiprocessing workers, and
    writes merged results back to the output CSV in input order.

    Args:
        input_csv: Path to the CSV file containing source record numbers.
        output_csv: Path to the CSV file used to read/write scrape results.
        headless: Whether browser workers run in headless mode.
        limit: Optional maximum number of input records to process.
        workers: Maximum number of worker processes to launch.
    """

    records = read_record_numbers(input_csv, limit=limit)
    existing_rows, success_records, failed_records = read_existing_results(output_csv)
    pending_records = [record for record in records if record not in success_records]
    retry_records = [record for record in records if record in failed_records]

    print("Starting fee scrape")
    print(f"- Input records: {len(records)}")
    print(
        f"- Prior successful records (will skip): {len(success_records.intersection(records))}"
    )
    print(f"- Prior failed records (will retry): {len(retry_records)}")
    print(f"- Pending scrape: {len(pending_records)}")

    if not pending_records:
        print("No pending records to scrape. Output already up to date.")
        return

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
    write_results(output_csv, merged_results)
    print("Finished fee scrape")
    print(f"- Scraped this run: {scraped_count}")
    print(f"- Skipped this run: {skipped_count}")
    print(f"- Failed this run: {failed_count}")
    print(f"- Total rows written: {len(merged_results)}")
    print(f"- Output file: {output_csv}")

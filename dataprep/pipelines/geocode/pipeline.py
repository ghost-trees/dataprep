"""Geocoding pipeline."""

import multiprocessing as mp
from pathlib import Path

import pandas as pd
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from dataprep.shared.paths import GEOCODED_RECORDS_PATH, SCRAPED_RECORDS_PATH
from dataprep.shared.schema import (
    ADDRESS_COLUMN,
    GEOCODE_OUTPUT_COLUMNS,
    LATITUDE_COLUMN,
    LONGITUDE_COLUMN,
    RECORD_NUMBER_COLUMN,
)


def build_geocode_callable():
    """Build a rate-limited geocoding callable."""
    geolocator = Nominatim(user_agent="ghost_trees_geocoder")
    return RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1,
        max_retries=2,
        error_wait_seconds=3,
        swallow_exceptions=True,
    )


def geocode_address(geocode_callable, address: object) -> tuple[float | None, float | None]:
    """Geocode one address and return (lat, lon)."""
    if pd.isna(address):
        return None, None

    try:
        location = geocode_callable(str(address))
    except (GeocoderTimedOut, GeocoderServiceError):
        return None, None

    if not location:
        return None, None
    return location.latitude, location.longitude


def worker_loop(worker_id: int, address_queue: mp.Queue, result_queue: mp.Queue) -> None:
    """Worker loop that geocodes addresses from queue input."""
    print(f"[worker-{worker_id}] Worker online")
    try:
        geocode_callable = build_geocode_callable()
        while True:
            item = address_queue.get()
            if item is None:
                break
            row_index, address = item
            latitude, longitude = geocode_address(geocode_callable, address)
            result_queue.put(
                (row_index, latitude, longitude, latitude is not None and longitude is not None)
            )
    except Exception as exc:
        print(f"[worker-{worker_id}] Worker failed: {exc}")
        while True:
            item = address_queue.get()
            if item is None:
                break
            row_index, _ = item
            result_queue.put((row_index, None, None, False))


def geocode_in_parallel(
    addresses: list[object],
    workers: int,
) -> tuple[list[tuple[float | None, float | None]], int]:
    """Geocode address values with worker multiprocessing."""
    total_records = len(addresses)
    if total_records == 0:
        return [], 0

    worker_count = min(workers, total_records)
    print(f"Using {worker_count} worker(s)")

    context = mp.get_context("spawn")
    address_queue: mp.Queue = context.Queue()
    result_queue: mp.Queue = context.Queue()

    for row_index, address in enumerate(addresses):
        address_queue.put((row_index, address))
    for _ in range(worker_count):
        address_queue.put(None)

    processes: list[mp.Process] = []
    for worker_id in range(1, worker_count + 1):
        process = context.Process(target=worker_loop, args=(worker_id, address_queue, result_queue))
        process.start()
        processes.append(process)

    geocoded_results: list[tuple[float | None, float | None]] = [(None, None)] * total_records
    geocoded_count = 0
    for completed in range(1, total_records + 1):
        row_index, latitude, longitude, success = result_queue.get()
        geocoded_results[row_index] = (latitude, longitude)
        if success:
            geocoded_count += 1
        remaining = total_records - completed
        print(
            f"[{completed}/{total_records}] Geocoded: {geocoded_count} | "
            f"Not geocoded: {completed - geocoded_count} | Remaining: {remaining}"
        )

    for process in processes:
        process.join()
        if process.exitcode not in (0, None):
            print(f"Worker pid={process.pid} exited with code {process.exitcode}")

    return geocoded_results, geocoded_count


def run(
    input_csv_path: Path = SCRAPED_RECORDS_PATH,
    output_csv_path: Path = GEOCODED_RECORDS_PATH,
    workers: int = 1,
) -> pd.DataFrame:
    """Geocode addresses from scraped records and write output CSV."""
    df = pd.read_csv(input_csv_path)

    required_columns = [RECORD_NUMBER_COLUMN, ADDRESS_COLUMN]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Expected columns {required_columns} in {input_csv_path}, "
            f"but missing: {missing_columns}. Found: {list(df.columns)}"
        )

    total_records = len(df)
    print(f"Starting geocoding for {total_records} records...")
    geocoded_results, geocoded_count = geocode_in_parallel(df[ADDRESS_COLUMN].tolist(), workers)

    df[LATITUDE_COLUMN] = [row[0] for row in geocoded_results]
    df[LONGITUDE_COLUMN] = [row[1] for row in geocoded_results]

    output_df = df[GEOCODE_OUTPUT_COLUMNS].copy()
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_csv_path, index=False)

    print(
        f"Finished geocoding. Total: {total_records}, "
        f"Geocoded: {geocoded_count}, Not geocoded: {total_records - geocoded_count}"
    )
    return output_df

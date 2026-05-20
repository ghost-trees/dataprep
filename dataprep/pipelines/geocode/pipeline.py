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
    GEOCODED_ADDRESS_COLUMN,
    GEOCODE_OUTPUT_COLUMNS,
    LATITUDE_COLUMN,
    LONGITUDE_COLUMN,
    RECORD_NUMBER_COLUMN,
)


def _build_geocode_failure_error(exc: Exception, *, context: str) -> RuntimeError:
    """Build a fail-fast runtime error with actionable geocoder guidance."""
    message = str(exc)
    lowered = message.lower()
    is_tls_error = "certificate_verify_failed" in lowered or "ssl" in lowered
    if is_tls_error:
        hint = (
            "TLS certificate verification failed when calling Nominatim. "
            "On macOS with python.org builds, run the bundled "
            "'Install Certificates.command' script (or configure your CA trust store), then retry."
        )
    else:
        hint = (
            "Geocoder service appears unreachable or timed out. "
            "Check internet connectivity and retry later."
        )

    error = RuntimeError(f"Geocoding failed during {context}: {message}. {hint}")
    error.__cause__ = exc
    return error


def build_geocode_callable():
    """Build a rate-limited geocoding callable."""
    geolocator = Nominatim(user_agent="ghost_trees_geocoder")
    return RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1,
        max_retries=2,
        error_wait_seconds=3,
        swallow_exceptions=False,
    )


def geocode_address(
    geocode_callable, address: object
) -> tuple[float | None, float | None, str | None]:
    """Geocode one address and return (lat, lon, geocoded_address)."""
    if pd.isna(address):
        return None, None, None

    location = geocode_callable(str(address))
    if not location:
        return None, None, None
    return location.latitude, location.longitude, location.address


def preflight_geocode_check(addresses: list[object]) -> None:
    """Fail early if the geocoding service cannot be reached reliably."""
    for address in addresses:
        if pd.isna(address):
            continue
        geocode_callable = build_geocode_callable()
        try:
            geocode_address(geocode_callable, address)
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            raise _build_geocode_failure_error(exc, context="preflight check")
        return


def _stop_processes(processes: list[mp.Process]) -> None:
    """Terminate workers and ensure all processes have exited."""
    for process in processes:
        if process.is_alive():
            process.terminate()
    for process in processes:
        process.join()


def worker_loop(worker_id: int, address_queue: mp.Queue, result_queue: mp.Queue) -> None:
    """Worker loop that geocodes addresses from queue input."""
    print(f"[worker-{worker_id}] Worker online")
    geocode_callable = build_geocode_callable()
    while True:
        item = address_queue.get()
        if item is None:
            break
        row_index, address = item
        try:
            latitude, longitude, geocoded_address = geocode_address(geocode_callable, address)
            result_queue.put(
                (
                    "result",
                    row_index,
                    latitude,
                    longitude,
                    geocoded_address,
                    latitude is not None and longitude is not None,
                    None,
                )
            )
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            result_queue.put(("error", None, None, None, None, False, f"[worker-{worker_id}] {exc}"))
            break


def geocode_in_parallel(
    addresses: list[object],
    workers: int,
) -> tuple[list[tuple[float | None, float | None, str | None]], int]:
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

    geocoded_results: list[tuple[float | None, float | None, str | None]] = [
        (None, None, None)
    ] * total_records
    geocoded_count = 0
    for completed in range(1, total_records + 1):
        message_type, row_index, latitude, longitude, geocoded_address, success, error_message = (
            result_queue.get()
        )
        if message_type == "error":
            _stop_processes(processes)
            raise _build_geocode_failure_error(
                GeocoderServiceError(str(error_message)), context="worker execution"
            )
        geocoded_results[row_index] = (latitude, longitude, geocoded_address)
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
            raise RuntimeError(f"Worker pid={process.pid} exited with code {process.exitcode}.")

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
    addresses = df[ADDRESS_COLUMN].tolist()
    preflight_geocode_check(addresses)
    geocoded_results, geocoded_count = geocode_in_parallel(addresses, workers)

    df[LATITUDE_COLUMN] = [row[0] for row in geocoded_results]
    df[LONGITUDE_COLUMN] = [row[1] for row in geocoded_results]
    df[GEOCODED_ADDRESS_COLUMN] = [row[2] for row in geocoded_results]

    output_df = df[GEOCODE_OUTPUT_COLUMNS].copy()
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_csv_path, index=False)

    print(
        f"Finished geocoding. Total: {total_records}, "
        f"Geocoded: {geocoded_count}, Not geocoded: {total_records - geocoded_count}"
    )
    return output_df

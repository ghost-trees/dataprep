"""Geocoding pipeline."""

import multiprocessing as mp
import sqlite3
from pathlib import Path

import pandas as pd
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from dataprep.shared.db import (
    DEFAULT_DB_PATH,
    get_connection,
    read_table,
    read_table_if_exists,
    write_table,
)
from dataprep.shared.schema import (
    ADDRESS_COLUMN,
    GEOCODED_ADDRESS_COLUMN,
    GEOCODE_OUTPUT_COLUMNS,
    GEOCODED_RECORDS_TABLE,
    LATITUDE_COLUMN,
    LONGITUDE_COLUMN,
    RECORD_NUMBER_COLUMN,
    SCRAPED_RECORDS_TABLE,
)


GeocodeResult = tuple[float | None, float | None, str | None]
ExistingGeocode = tuple[str | None, float, float, str | None]


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


def _addresses_match(left: object, right: object) -> bool:
    """Return True when two address values should be treated as equivalent."""
    if pd.isna(left) and pd.isna(right):
        return True
    if pd.isna(left) or pd.isna(right):
        return False
    return str(left) == str(right)


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
) -> tuple[list[GeocodeResult], int]:
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

    geocoded_results: list[GeocodeResult] = [(None, None, None)] * total_records
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


def read_existing_successful_geocodes(
    connection: sqlite3.Connection,
) -> dict[str, ExistingGeocode]:
    """Read prior successful geocode rows keyed by record number.

    Args:
        connection: Open SQLite connection.

    Returns:
        Mapping of record number to reusable geocode data:
        `(address, latitude, longitude, geocoded_address)`.

    Raises:
        ValueError: If an existing geocoded_records table is missing columns.
    """
    existing_df = read_table_if_exists(connection, GEOCODED_RECORDS_TABLE)
    if existing_df is None:
        return {}

    required_columns = [
        RECORD_NUMBER_COLUMN,
        ADDRESS_COLUMN,
        LATITUDE_COLUMN,
        LONGITUDE_COLUMN,
        GEOCODED_ADDRESS_COLUMN,
    ]
    missing_columns = [column for column in required_columns if column not in existing_df.columns]
    if missing_columns:
        raise ValueError(
            f"Expected columns {required_columns} in '{GEOCODED_RECORDS_TABLE}', "
            f"but missing: {missing_columns}. Found: {list(existing_df.columns)}"
        )

    successful_by_record: dict[str, ExistingGeocode] = {}
    for row in existing_df.itertuples(index=False):
        record_number = getattr(row, RECORD_NUMBER_COLUMN)
        latitude = getattr(row, LATITUDE_COLUMN)
        longitude = getattr(row, LONGITUDE_COLUMN)
        if pd.isna(record_number) or pd.isna(latitude) or pd.isna(longitude):
            continue
        successful_by_record[str(record_number)] = (
            getattr(row, ADDRESS_COLUMN),
            float(latitude),
            float(longitude),
            getattr(row, GEOCODED_ADDRESS_COLUMN),
        )
    return successful_by_record


def run(
    db_path: Path = DEFAULT_DB_PATH,
    workers: int = 1,
    redo_all: bool = False,
) -> pd.DataFrame:
    """Geocode addresses from the scraped_records table and write geocoded_records.

    The pipeline calls the external Nominatim service for pending addresses. By
    default, it reuses prior successful geocode rows from the existing
    ``geocoded_records`` table when record number and address are unchanged. Use
    `redo_all=True` to force a full rerun.

    Args:
        db_path: Path to the SQLite database.
        workers: Maximum worker process count for parallel geocoding.
        redo_all: When True, geocode all records regardless of prior output.

    Returns:
        DataFrame containing geocode output columns in input order.

    Raises:
        ValueError: If input or existing output columns are missing.
        RuntimeError: If geocoding workers fail due to geocoder connectivity.
    """
    connection = get_connection(db_path)
    try:
        df = read_table(connection, SCRAPED_RECORDS_TABLE)

        required_columns = [RECORD_NUMBER_COLUMN, ADDRESS_COLUMN]
        missing_columns = [column for column in required_columns if column not in df.columns]
        if missing_columns:
            raise ValueError(
                f"Expected columns {required_columns} in '{SCRAPED_RECORDS_TABLE}', "
                f"but missing: {missing_columns}. Found: {list(df.columns)}"
            )

        existing_successful = read_existing_successful_geocodes(connection)
        return _geocode_dataframe(
            connection, df, existing_successful, workers=workers, redo_all=redo_all
        )
    finally:
        connection.close()


def _geocode_dataframe(
    connection: sqlite3.Connection,
    df: pd.DataFrame,
    existing_successful: dict[str, ExistingGeocode],
    *,
    workers: int,
    redo_all: bool,
) -> pd.DataFrame:
    """Geocode pending rows and write the geocoded_records table."""
    total_records = len(df)
    print(f"Starting geocoding for {total_records} records...")

    geocoded_results: list[GeocodeResult] = [(None, None, None)] * total_records
    pending_indices: list[int] = []
    pending_addresses: list[object] = []
    skipped_count = 0
    reprocess_due_to_address_change = 0

    for row_index, row in enumerate(df.itertuples(index=False)):
        record_number = getattr(row, RECORD_NUMBER_COLUMN)
        current_address = getattr(row, ADDRESS_COLUMN)
        record_key = "" if pd.isna(record_number) else str(record_number)
        existing = existing_successful.get(record_key)

        should_reuse = False
        if not redo_all and existing is not None:
            existing_address = existing[0]
            if _addresses_match(current_address, existing_address):
                should_reuse = True
            else:
                reprocess_due_to_address_change += 1

        if should_reuse:
            _, latitude, longitude, geocoded_address = existing
            geocoded_results[row_index] = (latitude, longitude, geocoded_address)
            skipped_count += 1
        else:
            pending_indices.append(row_index)
            pending_addresses.append(current_address)

    pending_count = len(pending_addresses)
    print(f"Prior successful rows reused: {skipped_count}")
    print(f"Rows pending geocode this run: {pending_count}")
    if reprocess_due_to_address_change:
        print(f"Rows re-geocoded due to address changes: {reprocess_due_to_address_change}")

    geocoded_count = 0
    if pending_count:
        preflight_geocode_check(pending_addresses)
        pending_results, geocoded_count = geocode_in_parallel(pending_addresses, workers)
        for pending_index, result in zip(pending_indices, pending_results, strict=True):
            geocoded_results[pending_index] = result
    else:
        print("No pending rows to geocode. Output already up to date.")

    df[LATITUDE_COLUMN] = [row[0] for row in geocoded_results]
    df[LONGITUDE_COLUMN] = [row[1] for row in geocoded_results]
    df[GEOCODED_ADDRESS_COLUMN] = [row[2] for row in geocoded_results]

    output_df = df[GEOCODE_OUTPUT_COLUMNS].copy()
    output_df = write_table(
        connection, GEOCODED_RECORDS_TABLE, output_df, dataset_name="geocoded_records"
    )

    total_success = sum(
        1 for latitude, longitude, _ in geocoded_results if latitude is not None and longitude is not None
    )
    failed_this_run = pending_count - geocoded_count

    print(f"Finished geocoding. Total input: {total_records}")
    print(f"- Reused prior success: {skipped_count}")
    print(f"- Re-geocoded due to address changes: {reprocess_due_to_address_change}")
    print(f"- Geocoded this run: {geocoded_count}")
    print(f"- Not geocoded this run: {failed_this_run}")
    print(f"- Total successfully geocoded in output: {total_success}")
    return output_df

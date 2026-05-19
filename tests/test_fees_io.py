from pathlib import Path

from dataprep.pipelines.fees.io import (
    merge_rows_by_input_order,
    read_existing_results,
    read_record_numbers,
)


def test_read_record_numbers_accepts_snake_or_title_case_headers(tmp_path: Path) -> None:
    snake_input = tmp_path / "snake.csv"
    snake_input.write_text("record_number\nR1\nR2\nR1\n", encoding="utf-8")

    title_input = tmp_path / "title.csv"
    title_input.write_text("Record Number\nT1\nT2\n", encoding="utf-8")

    assert read_record_numbers(snake_input) == ["R1", "R2"]
    assert read_record_numbers(title_input) == ["T1", "T2"]


def test_read_existing_results_splits_success_and_failed(tmp_path: Path) -> None:
    output = tmp_path / "fees.csv"
    output.write_text(
        "record_number,paid,outstanding,scrape_status\n"
        "R1,12.5,0,success\n"
        "R2,0,4.0,failed\n",
        encoding="utf-8",
    )

    rows, success, failed = read_existing_results(output)

    assert len(rows) == 2
    assert success == {"R1"}
    assert failed == {"R2"}


def test_merge_rows_by_input_order_replaces_existing_rows() -> None:
    input_records = ["R1", "R2", "R3"]
    existing_rows = [
        {"record_number": "R1", "paid": 1.0, "outstanding": 0.0, "scrape_status": "success"},
        {"record_number": "R2", "paid": 0.0, "outstanding": 2.0, "scrape_status": "failed"},
        {"record_number": "R9", "paid": 9.0, "outstanding": 0.0, "scrape_status": "success"},
    ]
    new_rows = [
        {"record_number": "R2", "paid": 20.0, "outstanding": 1.0, "scrape_status": "success"},
        {"record_number": "R3", "paid": 30.0, "outstanding": 3.0, "scrape_status": "success"},
    ]

    merged = merge_rows_by_input_order(input_records, existing_rows, new_rows)
    merged_records = [row["record_number"] for row in merged]

    assert merged_records == ["R1", "R2", "R3", "R9"]
    assert merged[1]["paid"] == 20.0

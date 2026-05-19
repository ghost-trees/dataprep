import pandas as pd

from dataprep.shared.normalize import drop_unnamed_columns, normalize_columns, to_snake_case


def test_to_snake_case_normalizes_symbols_and_spacing() -> None:
    assert to_snake_case(" Record Number ") == "record_number"
    assert to_snake_case("Total Paid Fees ($)") == "total_paid_fees"


def test_normalize_columns_and_drop_unnamed() -> None:
    df = pd.DataFrame(
        {
            "Record Number": ["A-1"],
            "Unnamed: 0": [0],
            "Permit Type": ["Tree"],
        }
    )
    normalized = normalize_columns(df)
    cleaned = drop_unnamed_columns(normalized)

    assert list(cleaned.columns) == ["record_number", "permit_type"]

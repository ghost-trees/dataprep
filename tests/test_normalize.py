import pandas as pd

from dataprep.shared.normalize import (
    derive_date_iso,
    drop_unnamed_columns,
    normalize_columns,
    to_snake_case,
)


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


def test_derive_date_iso_normalizes_and_nulls_unparseable() -> None:
    df = pd.DataFrame({"record_number": ["R1", "R2", "R3"], "date": ["12/31/2025", "", "not-a-date"]})

    result = derive_date_iso(df)

    assert result.loc[0, "date_iso"] == "2025-12-31"
    assert pd.isna(result.loc[1, "date_iso"])
    assert pd.isna(result.loc[2, "date_iso"])


def test_derive_date_iso_no_op_when_date_column_absent() -> None:
    df = pd.DataFrame({"record_number": ["R1"], "address": ["123 Main"]})

    result = derive_date_iso(df)

    assert "date_iso" not in result.columns

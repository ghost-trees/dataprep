from pathlib import Path

import pandas as pd
import pytest

from dataprep.pipelines.parse_trees import pipeline as parse_trees_pipeline


def test_extract_tree_types_matches_multiple_aliases() -> None:
    matched = parse_trees_pipeline.extract_tree_types(
        'Removed one 12" HW and one 18" PN near driveway.',
        None,
    )

    assert matched == ["hardwood", "pine"]


def test_extract_tree_types_handles_variants_and_misspelling_aliases() -> None:
    matched = parse_trees_pipeline.extract_tree_types(
        "Removed sweet gum, tulip-poplar, and a gingko specimen.",
        "Also observed bois d'arc debris.",
    )

    assert matched == ["sweetgum", "poplar", "ginkgo", "bois darc"]


def test_extract_tree_types_matches_new_species_aliases() -> None:
    matched = parse_trees_pipeline.extract_tree_types(
        "Removed one black walnut, one ailanthus, and one mimosa.",
        "Also removed one catalpa, paper mulberry, and one ash.",
    )

    assert matched == ["ailanthus", "walnut", "mimosa", "catalpa", "mulberry", "ash"]


def test_extract_tree_types_normalizes_plural_tokens_and_hwd_abbreviation() -> None:
    matched = parse_trees_pipeline.extract_tree_types(
        "Removed oaks, hickories, maples, cherries, myrtles, and one HWD specimen.",
        None,
    )

    assert matched == ["oak", "hardwood", "hickory", "maple", "cherry", "crape myrtle"]


def test_extract_tree_types_matches_willow_oak_and_standalone_willow() -> None:
    matched_willow_oak = parse_trees_pipeline.extract_tree_types(
        'Removed one 12" willow oak from front yard.',
        None,
    )
    matched_standalone_willow = parse_trees_pipeline.extract_tree_types(
        'Removed one 12" willow from front yard.',
        None,
    )

    assert matched_willow_oak == ["oak"]
    assert matched_standalone_willow == ["oak"]


def test_extract_tree_types_returns_empty_when_no_match() -> None:
    matched = parse_trees_pipeline.extract_tree_types(
        "Fence repair and driveway resurfacing only.",
        "No trees referenced.",
    )

    assert matched == []


def test_run_raises_when_required_columns_are_missing(tmp_path: Path) -> None:
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"
    pd.DataFrame({"record_number": ["R1"], "description": ["Oak tree"]}).to_csv(input_csv, index=False)

    with pytest.raises(ValueError, match="Expected columns"):
        parse_trees_pipeline.run(input_csv_path=input_csv, output_csv_path=output_csv)


def test_run_writes_expected_columns_and_normalized_values(tmp_path: Path) -> None:
    input_csv = tmp_path / "scraped_records.csv"
    output_csv = tmp_path / "parsed_trees.csv"
    pd.DataFrame(
        {
            "record_number": ["R1", "R2", "R3"],
            "description": [
                'Illegal removal: 16" HW and 20" PN.',
                "Removed 31 Magnolia tree and one sweet gum.",
                "No tree mention present.",
            ],
            "short_notes": [
                "",
                "Also noted leland cypress",
                "",
            ],
        }
    ).to_csv(input_csv, index=False)

    result_df = parse_trees_pipeline.run(input_csv_path=input_csv, output_csv_path=output_csv)

    assert list(result_df.columns) == ["record_number", "tree_types"]
    assert result_df["tree_types"].tolist() == [
        "hardwood|pine",
        "magnolia|sweetgum|cypress",
        "",
    ]
    assert output_csv.exists()

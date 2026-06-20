from pathlib import Path

import pytest
from db_helpers import seed_table

from dataprep.pipelines.parse_trees import pipeline as parse_trees_pipeline
from dataprep.shared.schema import SCRAPED_RECORDS_TABLE


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
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(
        db_path, SCRAPED_RECORDS_TABLE, [{"record_number": "R1", "description": "Oak tree"}]
    )

    with pytest.raises(ValueError, match="Expected columns"):
        parse_trees_pipeline.run(db_path=db_path)


def test_run_writes_expected_columns_and_normalized_values(tmp_path: Path) -> None:
    db_path = tmp_path / "dataprep.sqlite3"
    seed_table(
        db_path,
        SCRAPED_RECORDS_TABLE,
        [
            {
                "record_number": "R1",
                "description": 'Illegal removal: 16" HW and 20" PN.',
                "short_notes": "",
            },
            {
                "record_number": "R2",
                "description": "Removed 31 Magnolia tree and one sweet gum.",
                "short_notes": "Also noted leland cypress",
            },
            {
                "record_number": "R3",
                "description": "No tree mention present.",
                "short_notes": "",
            },
        ],
    )

    result_df = parse_trees_pipeline.run(db_path=db_path)

    assert list(result_df.columns) == ["record_number", "tree_types"]
    assert result_df["tree_types"].tolist() == [
        "hardwood|pine",
        "magnolia|sweetgum|cypress",
        "",
    ]

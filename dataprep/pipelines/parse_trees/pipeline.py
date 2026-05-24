"""Parse tree species/types from scraped records into normalized labels.

This pipeline reads scraped record text fields and writes a compact CSV
containing per-record normalized tree type matches.
"""

import re
from pathlib import Path

import pandas as pd

from dataprep.shared.paths import PARSED_TREES_PATH, SCRAPED_RECORDS_PATH
from dataprep.shared.schema import PARSE_TREES_OUTPUT_COLUMNS, RECORD_NUMBER_COLUMN, TREE_TYPES_COLUMN

DESCRIPTION_COLUMN = "description"
SHORT_NOTES_COLUMN = "short_notes"
TREE_TYPES_DELIMITER = "|"

TREE_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "oak": ("oak", "water oak", "white oak", "red oak", "southern red oak", "post oak", "willow oak", "willow"),
    "hardwood": ("hardwood", "HW", "HWD"),
    "pine": ("pine", "pines", "PN"),
    "magnolia": ("magnolia",),
    "sweetgum": ("sweetgum", "sweet gum"),
    "hackberry": ("hackberry",),
    "poplar": ("poplar", "tulip poplar", "tulip-poplar"),
    "pecan": ("pecan",),
    "hickory": ("hickory",),
    "maple": ("maple", "red maple", "japanese maple", "boxelder maple"),
    "cherry": ("cherry", "black cherry", "flowering cherry", "native cherry"),
    "dogwood": ("dogwood", "kousa dogwood"),
    "holly": ("holly", "american holly", "chinese holly"),
    "crape myrtle": ("crape myrtle", "crepe myrtle", "myrtle"),
    "elm": ("elm",),
    "birch": ("birch", "river birch"),
    "hemlock": ("hemlock",),
    "beech": ("beech",),
    "cryptomeria": ("cryptomeria",),
    "ginkgo": ("ginkgo", "gingko"),
    "laurel": ("laurel", "cherry laurel"),
    "cypress": ("cypress", "leyland cypress", "leland cypress"),
    "cedar": ("cedar",),
    "sourwood": ("sourwood",),
    "sycamore": ("sycamore",),
    "bois darc": ("bois darc", "bois d'arc"),
    "ailanthus": ("ailanthus",),
    "walnut": ("walnut", "black walnut"),
    "mimosa": ("mimosa",),
    "catalpa": ("catalpa",),
    "mulberry": ("mulberry", "white mulberry", "paper mulberry"),
    "ash": ("ash",),
}

TOKEN_ABBREVIATIONS: dict[str, str] = {
    "hw": "hardwood",
    "hwd": "hardwood",
    "pn": "pine",
}


def _tokenize_text(value: object) -> list[str]:
    """Tokenize free text into normalized lowercase words.

    Args:
        value: Free-text source value.

    Returns:
        Ordered lowercase tokens stripped of punctuation.
    """
    if pd.isna(value):
        return []
    text = str(value).lower().replace("’", "").replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return text.split(" ")


def _build_alias_token_index() -> dict[str, tuple[tuple[str, ...], ...]]:
    """Compile alias strings into normalized token tuples keyed by tree type.

    Returns:
        Mapping from normalized tree type label to alias token tuples.
    """
    alias_token_index: dict[str, tuple[tuple[str, ...], ...]] = {}
    for normalized_name, aliases in TREE_TYPE_ALIASES.items():
        alias_token_index[normalized_name] = tuple(tuple(_tokenize_text(alias)) for alias in aliases)
    return alias_token_index


ALIAS_TOKEN_INDEX = _build_alias_token_index()
ALIAS_VOCABULARY: set[str] = {
    token
    for aliases in ALIAS_TOKEN_INDEX.values()
    for alias_tokens in aliases
    for token in alias_tokens
}


def _normalize_token_for_matching(token: str) -> str:
    """Normalize one token for matching against alias vocabulary.

    Args:
        token: Lowercase token from free-text input.

    Returns:
        Token rewritten with abbreviation and conservative plural normalization.
    """
    normalized_token = TOKEN_ABBREVIATIONS.get(token, token)
    if normalized_token in ALIAS_VOCABULARY:
        return normalized_token

    if normalized_token.endswith("ies"):
        singular_candidate = f"{normalized_token[:-3]}y"
        if singular_candidate in ALIAS_VOCABULARY:
            return singular_candidate

    if normalized_token.endswith("s") and not normalized_token.endswith("ss"):
        singular_candidate = normalized_token[:-1]
        if singular_candidate in ALIAS_VOCABULARY:
            return singular_candidate

    return normalized_token


def _normalize_text_for_matching(value: object) -> list[str]:
    """Normalize free text into keyword-matching tokens.

    Args:
        value: Source text value from description/notes fields.

    Returns:
        Ordered tokens with abbreviation and plural normalization applied.
    """
    return [_normalize_token_for_matching(token) for token in _tokenize_text(value)]


def _contains_phrase(tokens: list[str], phrase_tokens: tuple[str, ...]) -> bool:
    """Return True when phrase_tokens appear contiguously in tokens."""
    phrase_length = len(phrase_tokens)
    if phrase_length == 0 or phrase_length > len(tokens):
        return False
    if phrase_length == 1:
        return phrase_tokens[0] in tokens
    for start_index in range(0, len(tokens) - phrase_length + 1):
        if tuple(tokens[start_index : start_index + phrase_length]) == phrase_tokens:
            return True
    return False


def extract_tree_types(description: object, short_notes: object) -> list[str]:
    """Extract normalized tree type labels from description and short notes.

    Args:
        description: Record description text value.
        short_notes: Optional short notes text value.

    Returns:
        Ordered normalized tree type labels found in the record text.
    """
    tokens = _normalize_text_for_matching(description) + _normalize_text_for_matching(short_notes)
    if not tokens:
        return []

    matched_tree_types: list[str] = []
    for normalized_name, aliases in ALIAS_TOKEN_INDEX.items():
        if any(_contains_phrase(tokens, alias_tokens) for alias_tokens in aliases):
            matched_tree_types.append(normalized_name)
    return matched_tree_types


def run(
    input_csv_path: Path = SCRAPED_RECORDS_PATH,
    output_csv_path: Path = PARSED_TREES_PATH,
) -> pd.DataFrame:
    """Parse and normalize tree type mentions from scraped records CSV text.

    Args:
        input_csv_path: Source scraped records CSV path.
        output_csv_path: Destination parse-trees CSV path.

    Returns:
        DataFrame containing parse-trees output columns.

    Raises:
        ValueError: If required source columns are missing from the input CSV.
    """
    df = pd.read_csv(input_csv_path)

    required_columns = [RECORD_NUMBER_COLUMN, DESCRIPTION_COLUMN, SHORT_NOTES_COLUMN]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Expected columns {required_columns} in {input_csv_path}, "
            f"but missing: {missing_columns}. Found: {list(df.columns)}"
        )

    print(f"Starting parse-trees extraction for {len(df)} records...")
    parsed_tree_types = [
        TREE_TYPES_DELIMITER.join(
            extract_tree_types(
                getattr(row, DESCRIPTION_COLUMN),
                getattr(row, SHORT_NOTES_COLUMN),
            )
        )
        for row in df.itertuples(index=False)
    ]

    output_df = pd.DataFrame(
        {
            RECORD_NUMBER_COLUMN: df[RECORD_NUMBER_COLUMN],
            TREE_TYPES_COLUMN: parsed_tree_types,
        }
    )[PARSE_TREES_OUTPUT_COLUMNS].copy()

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_csv_path, index=False)

    records_with_matches = sum(bool(value) for value in parsed_tree_types)
    print(f"Finished parse-trees extraction. Total input: {len(df)}")
    print(f"- Records with matches: {records_with_matches}")
    print(f"- Records without matches: {len(df) - records_with_matches}")
    print(f"- Output file: {output_csv_path}")
    return output_df

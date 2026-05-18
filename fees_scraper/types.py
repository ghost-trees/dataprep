"""Type aliases used across fee scraping modules."""

from collections.abc import Mapping

FeeRow = dict[str, float | str]
FeeRowMapping = Mapping[str, float | str]
WorkerResult = tuple[FeeRow, bool]

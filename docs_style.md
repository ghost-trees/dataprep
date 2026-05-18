# Python Documentation Style Guide

This project uses a single documentation style for Python code:

- Google-style docstrings for modules and public APIs
- Type hints for function signatures and key variables
- PEP-aligned comments and formatting

## PEP Mapping

- [PEP 257](https://peps.python.org/pep-0257/): Docstring conventions for modules, classes, and functions.
- [PEP 8](https://peps.python.org/pep-0008/): Comment style and general readability rules.
- [PEP 484](https://peps.python.org/pep-0484/): Type hints for function parameters and return types.
- [PEP 526](https://peps.python.org/pep-0526/): Variable annotations.
- [PEP 585](https://peps.python.org/pep-0585/): Built-in generic types (`list[str]`, `dict[str, int]`, etc.).
- [PEP 604](https://peps.python.org/pep-0604/): Union operator syntax (`int | None`).

## Why Both Type Hints And Docstrings

Type hints describe the shape of values.  
Docstrings describe behavior and operational context.

Use docstrings to capture details that types cannot express well, such as:

- retry behavior
- external system assumptions
- side effects (network I/O, file writes)
- fallback behavior and error handling choices

## Required vs Optional

Required:

- Module docstrings for maintained modules.
- Docstrings for public functions and classes.
- `Args`, `Returns`, and `Raises` sections when they add clarity.

Optional:

- Tiny private helpers with obvious behavior.
- Very small constants/types-only modules may use short module docstrings without per-symbol docstrings.

## Module Docstring Template

```python
"""Short summary of the module's responsibility.

Longer context when needed, including major side effects or external dependencies.
"""
```

## Function Docstring Template (Google Style)

```python
def example(input_csv: Path, limit: int | None = None) -> list[str]:
    """Extract unique record IDs from an input CSV file.

    Args:
        input_csv: Path to the source CSV file.
        limit: Maximum number of unique records to return. When None, process all.

    Returns:
        Ordered unique record numbers.

    Raises:
        OSError: If the file cannot be read.
    """
```

## Project-Specific Examples

Pipeline orchestration functions should document queue/process behavior and side effects:

```python
def run(input_csv: Path, output_csv: Path, headless: bool, limit: int | None, workers: int) -> None:
    """Run the end-to-end fee scraping workflow.

    Args:
        input_csv: Path to the CSV file containing source record numbers.
        output_csv: Path to the CSV file used to read/write scrape results.
        headless: Whether browser workers run in headless mode.
        limit: Optional maximum number of input records to process.
        workers: Maximum number of worker processes to launch.
    """
```

Portal/browser helper functions should describe retry assumptions and automation scope:

```python
def initialize_search(page: Page) -> None:
    """Open the portal and ensure the search box is available.

    Args:
        page: Active Playwright page instance.

    Raises:
        TimeoutError: If search initialization fails across retry attempts.
    """
```

## Do and Do Not

Do:

- Document the reason for retries, defaults, and fallback flows.
- Mention when code talks to external services or writes files.
- Keep summaries short and direct.

Do not:

- Repeat obvious type details already present in annotations.
- Use docstrings as change logs.
- Add comments that restate straightforward code.

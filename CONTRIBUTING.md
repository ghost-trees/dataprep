# Contributing

This project uses [`uv`](https://github.com/astral-sh/uv) for environment and dependency management.

## Prerequisites

- Python 3.14
- `uv` installed (`pip install uv`)

## Install Dependencies

From the project root:

- Python dependencies

    ```
    uv sync --extra dev
    ```
    Note: This command creates/updates a local .venv virtual environment

- Playwright browser binaries

    ```
    uv run playwright install
    ```

## Dependency & Lock Workflow

When dependencies change in [`pyproject.toml`](pyproject.toml):

- Sync development environment

    ```
    uv sync --extra dev
    ```

- Update lockfile

    ```
    uv lock
    ```

## Common Commands

- Tests

    ```
    uv run pytest
    ```

- Lint

    ```
    uv run ruff check .
    ```

- Format

    ```
    uv run ruff format .
    ```





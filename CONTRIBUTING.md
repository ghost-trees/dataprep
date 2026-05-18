# Contributing

This project uses [`uv`](https://github.com/astral-sh/uv) for environment and dependency management.
It is an application/data-pipeline repository, not a package intended for build/publish/install.

## Prerequisites

- Python 3.14
- `uv` installed (`pip install uv`)

## Set Up Local Environment

From the project root:

- Python dependencies

    ```
    uv sync --extra dev
    ```
    Note: This command creates/updates a local `.venv` virtual environment for local development and does not install this repo as a package.

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





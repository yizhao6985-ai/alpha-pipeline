from __future__ import annotations

from pathlib import Path


class DataFetchError(RuntimeError):
    """Raised when data fetching fails (provider/validation)."""


class EmptyDataError(DataFetchError):
    """Raised when a required dataset is empty after standardization."""


def write_csv(data, path: Path) -> Path:
    data.to_csv(path, index=False, encoding="utf-8-sig")
    return path

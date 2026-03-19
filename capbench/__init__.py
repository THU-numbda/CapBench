"""Public CapBench library API."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .cache import get_cache_dir
from .datasets import (
    ensure_dataset,
    get_dataset_info,
    list_datasets,
    materialize_dataset,
    preprocess_dataset,
    resolve_dataset_path,
)

try:
    __version__ = version("capbench")
except PackageNotFoundError:  # pragma: no cover - local source tree fallback
    __version__ = "0.2.0"

__all__ = [
    "__version__",
    "ensure_dataset",
    "get_cache_dir",
    "get_dataset_info",
    "list_datasets",
    "materialize_dataset",
    "preprocess_dataset",
    "resolve_dataset_path",
]


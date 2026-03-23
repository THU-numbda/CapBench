"""Public CapBench library API."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .cache import get_cache_dir
from .datasets import (
    get_dataset_info,
    get_dataset_infos,
    install_dataset,
    list_datasets,
    resolve_dataset_path,
)

try:
    __version__ = version("capbench")
except PackageNotFoundError:  # pragma: no cover - local source tree fallback
    __version__ = "0.2.0"

__all__ = [
    "__version__",
    "get_cache_dir",
    "get_dataset_info",
    "get_dataset_infos",
    "install_dataset",
    "list_datasets",
    "resolve_dataset_path",
]

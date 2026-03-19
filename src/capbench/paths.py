"""Filesystem paths used by the public CapBench library."""

from __future__ import annotations

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = PACKAGE_ROOT / "resources"
TECH_ROOT = RESOURCE_ROOT / "tech"
OPENRCX_ROOT = RESOURCE_ROOT / "openrcx"


def get_cache_dir(*, create: bool = False) -> Path:
    """Return the shared CapBench cache directory."""
    raw = os.environ.get("CAPBENCH_CACHE_DIR", "~/.cache/capbench")
    path = Path(raw).expanduser().resolve()
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path

def get_resource_root(*, create: bool = False) -> Path:
    """Return the root directory that contains packaged non-Python assets."""
    path = RESOURCE_ROOT.resolve()
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path

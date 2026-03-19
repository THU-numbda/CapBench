"""Filesystem paths used by the public CapBench library."""

from __future__ import annotations

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
TECH_ROOT = REPO_ROOT / "tech"


def get_cache_dir(*, create: bool = False) -> Path:
    """Return the shared CapBench cache directory."""
    raw = os.environ.get("CAPBENCH_CACHE_DIR", "~/.cache/capbench")
    path = Path(raw).expanduser().resolve()
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_workspace_root(*, create: bool = False) -> Path:
    """Return the default materialization root for symlinked datasets."""
    raw = os.environ.get("CAPBENCH_WORKSPACE_ROOT")
    if raw:
        path = Path(raw).expanduser().resolve()
    else:
        path = (Path.cwd() / "datasets").resolve()
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


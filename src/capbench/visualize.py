"""Standardized CAP3D visualization entrypoints for cache-backed CapBench datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .datasets import resolve_dataset_path


def _strip_passthrough(extra_args: Sequence[str]) -> list[str]:
    cleaned = list(extra_args)
    if cleaned and cleaned[0] == "--":
        cleaned = cleaned[1:]
    return cleaned


def visualize_cap3d(dataset: str | Path, *, window_id: str, extra_args: Sequence[str] = ()) -> None:
    from .visualization import viewer_cap3d

    dataset_root = resolve_dataset_path(dataset, artifacts=["cap3d"])
    cap3d_file = dataset_root / "cap3d" / f"{window_id}.cap3d"
    if not cap3d_file.exists():
        raise FileNotFoundError(f"CAP3D file not found: {cap3d_file}")
    cmd = [str(cap3d_file), *_strip_passthrough(extra_args)]
    viewer_cap3d.main(cmd)

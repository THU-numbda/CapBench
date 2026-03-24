"""Standardized dataloader accessors backed by the CapBench dataset cache."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from .datasets import resolve_dataset_path
from .window_density_dataset import WindowCapDataset
from .window_id_map_dataset import IdMapWindowDataset


def _resolve_label_dir(dataset_root: Path, solver_preference: str) -> Path:
    rwcap = dataset_root / "labels_rwcap"
    raphael = dataset_root / "labels_raphael"
    order = ["rwcap", "raphael"] if solver_preference in {"auto", "rwcap"} else ["raphael", "rwcap"]
    for solver in order:
        candidate = rwcap if solver == "rwcap" else raphael
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No label directory found under {dataset_root}. Expected one of: {rwcap}, {raphael}"
    )


def resolve_cached_dataset(dataset: str | Path, *, artifacts: Sequence[str] = ()) -> Path:
    return resolve_dataset_path(dataset, artifacts=artifacts)


def load_density_window_dataset(
    dataset: str | Path,
    *,
    goal: str = "self",
    solver_preference: str = "auto",
    window_ids: Optional[Sequence[str]] = None,
    build_workers: int = 0,
    highlight_scale: float = 1.0,
):
    dataset_root = resolve_cached_dataset(dataset, artifacts=["density_maps"])
    spef_dir = _resolve_label_dir(dataset_root, solver_preference)
    return WindowCapDataset(
        window_dir=dataset_root / "density_maps",
        spef_dir=spef_dir,
        window_ids=window_ids,
        goal=goal,
        highlight_scale=highlight_scale,
        solver_preference=solver_preference,
        build_workers=build_workers,
    )


def load_density_id_window_dataset(
    dataset: str | Path,
    *,
    goal: str = "self",
    solver_preference: str = "auto",
    window_ids: Optional[Sequence[str]] = None,
    build_workers: int = 0,
    highlight_scale: float = 1.0,
):
    dataset_root = resolve_cached_dataset(dataset, artifacts=["density_maps"])
    spef_dir = _resolve_label_dir(dataset_root, solver_preference)
    return IdMapWindowDataset(
        window_dir=dataset_root / "density_maps",
        spef_dir=spef_dir,
        window_ids=window_ids,
        goal=goal,
        highlight_scale=highlight_scale,
        solver_preference=solver_preference,
        build_workers=build_workers,
    )

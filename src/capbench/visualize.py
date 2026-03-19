"""Standardized visualization entrypoints for cache-backed CapBench datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .datasets import resolve_dataset_path


def _strip_passthrough(extra_args: Sequence[str]) -> list[str]:
    cleaned = list(extra_args)
    if cleaned and cleaned[0] == "--":
        cleaned = cleaned[1:]
    return cleaned


def visualize_density(dataset: str | Path, *, window_id: str, extra_args: Sequence[str] = ()) -> None:
    from .visualization import viewer_density_maps

    dataset_root = resolve_dataset_path(dataset, artifacts=["density_maps"])
    density_map = dataset_root / "density_maps" / f"{window_id}.npz"
    if not density_map.exists():
        raise FileNotFoundError(f"Density map not found: {density_map}")

    cmd = [str(density_map)]
    cap3d_file = dataset_root / "cap3d" / f"{window_id}.cap3d"
    if cap3d_file.exists():
        cmd.extend(["--cap3d", str(cap3d_file)])
    cmd.extend(_strip_passthrough(extra_args))
    viewer_density_maps.main(viewer_density_maps.parse_args(cmd))


def visualize_point_cloud(dataset: str | Path, *, window_id: str, extra_args: Sequence[str] = ()) -> None:
    from .visualization import viewer_point_cloud

    dataset_root = resolve_dataset_path(dataset, artifacts=["point_clouds", "cap3d"])
    point_cloud = dataset_root / "point_clouds" / f"{window_id}.npz"
    if not point_cloud.exists():
        raise FileNotFoundError(f"Point cloud not found: {point_cloud}")

    cap3d_file = dataset_root / "cap3d" / f"{window_id}.cap3d"
    if not cap3d_file.exists():
        raise FileNotFoundError(f"CAP3D file not found for point-cloud visualization: {cap3d_file}")

    cmd = [str(point_cloud), "--cap3d", str(cap3d_file)]
    cmd.extend(_strip_passthrough(extra_args))
    viewer_point_cloud.main(cmd)


def visualize_cap3d(dataset: str | Path, *, window_id: str, extra_args: Sequence[str] = ()) -> None:
    from .visualization import viewer_cap3d

    dataset_root = resolve_dataset_path(dataset, artifacts=["cap3d"])
    cap3d_file = dataset_root / "cap3d" / f"{window_id}.cap3d"
    if not cap3d_file.exists():
        raise FileNotFoundError(f"CAP3D file not found: {cap3d_file}")
    cmd = [str(cap3d_file), *_strip_passthrough(extra_args)]
    viewer_cap3d.main(cmd)

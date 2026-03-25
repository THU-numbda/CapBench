"""Shared helpers for CapBench density-window bundle artifacts."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple

import numpy as np


BUNDLE_FORMAT_VERSION = 1
META_FILENAME = "meta.json"
DENSITY_FILENAME = "density.npy"
ID_FILENAME = "id.npy"
CONDUCTOR_IDS_FILENAME = "conductor_ids.npy"
CONDUCTOR_NAMES_FILENAME = "conductor_names.json"


@dataclass(frozen=True)
class DensityWindowMeta:
    """Metadata for one lazily-loaded density-window bundle."""

    path: Path
    window_id: str
    layer_names: tuple[str, ...]
    layer_has_density: tuple[bool, ...]
    shape: tuple[int, int, int]
    pixel_resolution: float
    window_bounds: tuple[float, float, float, float, float, float]
    raster_trim_applied: bool
    source_window_bounds: Optional[tuple[float, float, float, float, float, float]]


def density_window_bundle_path(window_root: Path | str, window_id: str) -> Path:
    return Path(window_root) / str(window_id)


def is_density_window_bundle(path: Path | str) -> bool:
    bundle_dir = Path(path)
    return bundle_dir.is_dir() and (bundle_dir / META_FILENAME).exists()


def discover_density_window_ids(window_root: Path | str) -> list[str]:
    root = Path(window_root)
    if not root.exists():
        return []
    return sorted(path.name for path in root.iterdir() if is_density_window_bundle(path))


def load_density_window_meta(bundle_dir: Path | str) -> DensityWindowMeta:
    bundle_dir = Path(bundle_dir)
    meta_path = bundle_dir / META_FILENAME
    if not meta_path.exists():
        raise FileNotFoundError(f"Density window metadata not found: {meta_path}")

    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    format_version = int(payload.get("format_version", 0))
    if format_version != BUNDLE_FORMAT_VERSION:
        raise ValueError(
            f"Unsupported density bundle format in {meta_path}: "
            f"expected {BUNDLE_FORMAT_VERSION}, got {format_version}"
        )
    layer_names = tuple(str(layer) for layer in payload.get("layer_names", []))
    layer_has_density = tuple(bool(item) for item in payload.get("layer_has_density", []))
    shape = tuple(int(v) for v in payload.get("shape", []))
    window_bounds = tuple(float(v) for v in payload.get("window_bounds", []))
    raw_source_bounds = payload.get("source_window_bounds")
    source_window_bounds = (
        tuple(float(v) for v in raw_source_bounds)
        if raw_source_bounds is not None
        else None
    )

    if len(shape) != 3:
        raise ValueError(f"Invalid density bundle shape in {meta_path}: {shape}")
    if len(window_bounds) != 6:
        raise ValueError(f"Invalid density bundle window_bounds in {meta_path}: {window_bounds}")
    if len(layer_names) != shape[0]:
        raise ValueError(
            f"Layer count mismatch in {meta_path}: {len(layer_names)} names for shape {shape}"
        )
    if len(layer_has_density) != len(layer_names):
        raise ValueError(
            f"layer_has_density mismatch in {meta_path}: "
            f"{len(layer_has_density)} flags for {len(layer_names)} layers"
        )
    if source_window_bounds is not None and len(source_window_bounds) != 6:
        raise ValueError(
            f"Invalid density bundle source_window_bounds in {meta_path}: {source_window_bounds}"
        )

    return DensityWindowMeta(
        path=bundle_dir,
        window_id=str(payload.get("window_id") or bundle_dir.name),
        layer_names=layer_names,
        layer_has_density=layer_has_density,
        shape=(int(shape[0]), int(shape[1]), int(shape[2])),
        pixel_resolution=float(payload["pixel_resolution"]),
        window_bounds=(
            float(window_bounds[0]),
            float(window_bounds[1]),
            float(window_bounds[2]),
            float(window_bounds[3]),
            float(window_bounds[4]),
            float(window_bounds[5]),
        ),
        raster_trim_applied=bool(payload.get("raster_trim_applied", False)),
        source_window_bounds=(
            None
            if source_window_bounds is None
            else (
                float(source_window_bounds[0]),
                float(source_window_bounds[1]),
                float(source_window_bounds[2]),
                float(source_window_bounds[3]),
                float(source_window_bounds[4]),
                float(source_window_bounds[5]),
            )
        ),
    )


def load_density_window_conductor_map(bundle_dir: Path | str) -> dict[str, int]:
    bundle_dir = Path(bundle_dir)
    ids_path = bundle_dir / CONDUCTOR_IDS_FILENAME
    names_path = bundle_dir / CONDUCTOR_NAMES_FILENAME
    if not ids_path.exists() or not names_path.exists():
        return {}

    conductor_ids = np.load(ids_path, allow_pickle=False)
    conductor_names = json.loads(names_path.read_text(encoding="utf-8"))
    if len(conductor_ids) != len(conductor_names):
        raise ValueError(
            f"Conductor lookup mismatch in {bundle_dir}: "
            f"{len(conductor_ids)} ids vs {len(conductor_names)} names"
        )

    return {
        str(name): int(cid)
        for name, cid in zip(conductor_names, conductor_ids.tolist())
    }


def load_density_window_density(bundle_dir: Path | str, *, mmap_mode: str | None = "r") -> np.ndarray:
    return np.load(Path(bundle_dir) / DENSITY_FILENAME, mmap_mode=mmap_mode, allow_pickle=False)


def load_density_window_ids(bundle_dir: Path | str, *, mmap_mode: str | None = "r") -> np.ndarray:
    return np.load(Path(bundle_dir) / ID_FILENAME, mmap_mode=mmap_mode, allow_pickle=False)


def save_density_window_bundle(
    bundle_dir: Path | str,
    *,
    window_id: str,
    layer_names: Sequence[str],
    layer_has_density: Sequence[bool],
    density: np.ndarray,
    id_maps: np.ndarray,
    conductor_id_map: Mapping[str, int],
    window_bounds: Sequence[float],
    pixel_resolution: float,
    raster_trim_applied: bool,
    source_window_bounds: Optional[Sequence[float]] = None,
) -> Path:
    bundle_dir = Path(bundle_dir)
    layer_names = [str(layer) for layer in layer_names]
    layer_has_density = [bool(item) for item in layer_has_density]
    window_bounds = [float(v) for v in window_bounds]
    source_bounds = None if source_window_bounds is None else [float(v) for v in source_window_bounds]

    density = np.asarray(density, dtype=np.float32)
    id_maps = np.asarray(id_maps, dtype=np.int32)

    if density.ndim != 3 or id_maps.ndim != 3:
        raise ValueError(
            f"density and id_maps must be rank-3 tensors, got {density.shape} and {id_maps.shape}"
        )
    if density.shape != id_maps.shape:
        raise ValueError(
            f"density and id_maps shapes must match, got {density.shape} and {id_maps.shape}"
        )
    if len(layer_names) != density.shape[0]:
        raise ValueError(
            f"Layer name count mismatch: {len(layer_names)} names for tensor shape {density.shape}"
        )
    if len(layer_has_density) != len(layer_names):
        raise ValueError(
            f"Layer density-flag mismatch: {len(layer_has_density)} flags for {len(layer_names)} layers"
        )
    if len(window_bounds) != 6:
        raise ValueError(f"window_bounds must have 6 values, got {window_bounds}")
    if source_bounds is not None and len(source_bounds) != 6:
        raise ValueError(f"source_window_bounds must have 6 values, got {source_bounds}")

    ordered_conductors = sorted(
        ((str(name), int(cid)) for name, cid in conductor_id_map.items()),
        key=lambda item: item[1],
    )

    tmp_dir = bundle_dir.with_name(bundle_dir.name + ".tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    np.save(tmp_dir / DENSITY_FILENAME, density, allow_pickle=False)
    np.save(tmp_dir / ID_FILENAME, id_maps, allow_pickle=False)
    np.save(
        tmp_dir / CONDUCTOR_IDS_FILENAME,
        np.asarray([cid for _, cid in ordered_conductors], dtype=np.int32),
        allow_pickle=False,
    )
    (tmp_dir / CONDUCTOR_NAMES_FILENAME).write_text(
        json.dumps([name for name, _ in ordered_conductors], indent=2),
        encoding="utf-8",
    )

    meta = {
        "format_version": BUNDLE_FORMAT_VERSION,
        "window_id": str(window_id),
        "layer_names": layer_names,
        "layer_has_density": layer_has_density,
        "shape": [int(v) for v in density.shape],
        "pixel_resolution": float(pixel_resolution),
        "window_bounds": window_bounds,
        "raster_trim_applied": bool(raster_trim_applied),
        "source_window_bounds": source_bounds,
    }
    (tmp_dir / META_FILENAME).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    tmp_dir.rename(bundle_dir)
    return bundle_dir

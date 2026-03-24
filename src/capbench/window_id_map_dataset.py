"""
ID-map-backed window dataset loader for CAP3D-backed or compact window artifacts.

This loader reads window NPZ files that store `{layer}_idx` conductor ID maps
(`0` = empty/background, `1..N` = conductors present in the window). It reuses
the existing WindowCapDataset label parsing and grouped-case logic, but
synthesizes binary occupancy features from the ID maps instead of loading
legacy float density grids from disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from capbench._internal.common.datasets import DENSITY_MAPS_DIR
from .window_density_dataset import (
    WindowCapDataset,
    _WindowData,
)


class IdMapWindowDataset(WindowCapDataset):
    """
    Drop-in replacement for WindowCapDataset on the U-Net path, backed by
    window NPZ files that contain conductor ID maps and metadata.

    When `trim_margin=True`, the loader crops each window to the occupied
    conductor bounding box and resizes it back to the original grid. This is
    useful for CAP3D-backed `density_maps/` artifacts that still include the
    older CAP3D window margins.
    """

    def __init__(
        self,
        window_dir: Path | str = DENSITY_MAPS_DIR,
        spef_dir: Optional[Path | str] = None,
        window_ids: Optional[Sequence[str]] = None,
        goal: str = "self",
        highlight_scale: float = 1.0,
        dtype: np.dtype = np.float32,
        solver_preference: str = "auto",
        required_layers: Optional[Sequence[str]] = None,
        build_workers: int = 0,
        trim_margin: bool = False,
    ):
        self._trim_margin = bool(trim_margin)
        super().__init__(
            window_dir=window_dir,
            spef_dir=spef_dir,
            window_ids=window_ids,
            goal=goal,
            highlight_scale=highlight_scale,
            dtype=dtype,
            solver_preference=solver_preference,
            required_layers=required_layers,
            build_workers=build_workers,
        )

    @staticmethod
    def _find_content_bbox(id_maps: Sequence[np.ndarray]) -> Optional[tuple[int, int, int, int]]:
        if not id_maps:
            return None

        occupied = np.zeros(id_maps[0].shape, dtype=bool)
        for id_map in id_maps:
            occupied |= id_map > 0

        if not bool(np.any(occupied)):
            return None

        ys, xs = np.nonzero(occupied)
        return int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1

    @staticmethod
    def _resize_id_map_nearest(id_map: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
        target_h, target_w = int(target_shape[0]), int(target_shape[1])
        if id_map.shape == (target_h, target_w):
            return id_map.astype(np.int32, copy=False)

        src_h, src_w = id_map.shape
        if src_h <= 0 or src_w <= 0:
            raise ValueError(f"Invalid source ID-map shape: {id_map.shape}")

        y_idx = np.floor(np.arange(target_h, dtype=np.float64) * (src_h / target_h)).astype(np.int64)
        x_idx = np.floor(np.arange(target_w, dtype=np.float64) * (src_w / target_w)).astype(np.int64)
        y_idx = np.clip(y_idx, 0, src_h - 1)
        x_idx = np.clip(x_idx, 0, src_w - 1)
        return id_map[y_idx[:, None], x_idx[None, :]].astype(np.int32, copy=False)

    def _trim_and_resize_id_maps(self, id_maps: Sequence[np.ndarray]) -> List[np.ndarray]:
        bbox = self._find_content_bbox(id_maps)
        if bbox is None:
            return [id_map.astype(np.int32, copy=False) for id_map in id_maps]

        y0, y1, x0, x1 = bbox
        trimmed: List[np.ndarray] = []
        for id_map in id_maps:
            cropped = id_map[y0:y1, x0:x1]
            trimmed.append(self._resize_id_map_nearest(cropped, id_map.shape))
        return trimmed

    def _load_window(self, npz_path: Path) -> _WindowData:
        with np.load(npz_path, allow_pickle=True) as data:
            raw_layers = [str(layer) for layer in data["layers"]]
            layer_names: List[str] = []
            id_maps: List[np.ndarray] = []

            for layer in raw_layers:
                id_map = data[f"{layer}_idx"].astype(np.int32, copy=False)
                layer_names.append(layer)
                id_maps.append(id_map)

            if not layer_names:
                raise ValueError(f"Window {npz_path.stem} has no layers")

            if self._trim_margin:
                id_maps = self._trim_and_resize_id_maps(id_maps)

            densities: List[np.ndarray] = [
                (id_map > 0).astype(np.float32, copy=False)
                for id_map in id_maps
            ]

            conductor_ids: Dict[str, int] = {}
            if "conductor_names" in data and "conductor_ids" in data:
                for name, cid in zip(data["conductor_names"], data["conductor_ids"]):
                    actual = str(name)
                    conductor_ids[actual] = int(cid)

        return _WindowData(
            name=npz_path.stem,
            layer_names=layer_names,
            densities=densities,
            id_maps=id_maps,
            conductor_ids=conductor_ids,
        )

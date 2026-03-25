"""
ID-map-backed window dataset loader for CAP3D-backed or compact window artifacts.

This variant reuses the lazy density-window indexing in ``WindowCapDataset`` but
materializes binary occupancy features from the conductor ID maps instead of the
stored density tensor. It is intended for U-Net style segmentation pipelines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from capbench._internal.common.datasets import DENSITY_MAPS_DIR
from .window_density_dataset import _CachedWindowData, _WindowSpec, WindowCapDataset


class IdMapWindowDataset(WindowCapDataset):
    """
    Drop-in replacement for ``WindowCapDataset`` on the U-Net path, backed by
    `id.npy` conductor maps from density-window bundles.

    When ``trim_margin=True``, the loader crops each window to the occupied
    conductor bounding box and resizes it back to the original grid. This keeps
    the previous CAP3D margin-trimming behavior while remaining lazy.
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
        window_cache_size: int = 4,
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
            window_cache_size=window_cache_size,
        )

    @staticmethod
    def _find_content_bbox(id_maps: np.ndarray) -> Optional[tuple[int, int, int, int]]:
        if id_maps.ndim != 3 or id_maps.size == 0:
            return None

        occupied = np.any(id_maps > 0, axis=0)
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

    def _trim_and_resize_id_maps(self, id_maps: np.ndarray) -> np.ndarray:
        bbox = self._find_content_bbox(id_maps)
        if bbox is None:
            return id_maps.astype(np.int32, copy=False)

        y0, y1, x0, x1 = bbox
        trimmed = np.zeros_like(id_maps, dtype=np.int32)
        for layer_idx in range(id_maps.shape[0]):
            cropped = id_maps[layer_idx, y0:y1, x0:x1]
            trimmed[layer_idx] = self._resize_id_map_nearest(cropped, id_maps[layer_idx].shape)
        return trimmed

    def _transform_id_maps(self, window: _WindowSpec, id_maps: np.ndarray) -> np.ndarray:
        transformed = id_maps.astype(np.int32, copy=False)
        if self._trim_margin:
            return self._trim_and_resize_id_maps(transformed)
        return transformed

    def _load_density_for_cache(self, window: _WindowSpec) -> Optional[np.ndarray]:
        return None

    def _fill_base_features(
        self,
        features: np.ndarray,
        window: _WindowSpec,
        cached: _CachedWindowData,
    ) -> None:
        for local_idx, layer_name in enumerate(window.layer_names):
            global_idx = self._layer_index.get(layer_name)
            if global_idx is None:
                continue
            layer_density = (cached.id_maps[local_idx] > 0).astype(np.float32, copy=False)
            h, w = layer_density.shape
            features[global_idx, :h, :w] = layer_density

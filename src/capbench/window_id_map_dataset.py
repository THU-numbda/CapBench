"""
ID-map-backed window dataset loader for the newer U-Net flow.

This loader reads `binary-masks/*.npz`, where each layer stores only compact
conductor IDs (`0` = empty/background, `1..N` = conductors present in the
window). It reuses the existing WindowCapDataset label parsing and grouped-case
logic, but synthesizes binary occupancy features from the ID maps instead of
loading legacy float density grids from disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from capbench._internal.common.datasets import BINARY_MASKS_DIR
from .window_density_dataset import (
    WindowCapDataset,
    _WindowData,
    _is_via_layer,
)


class IdMapWindowDataset(WindowCapDataset):
    """
    Drop-in replacement for WindowCapDataset on the U-Net path, backed by
    `binary-masks/` files that only contain conductor ID maps and metadata.
    """

    def __init__(
        self,
        window_dir: Path | str = BINARY_MASKS_DIR,
        spef_dir: Optional[Path | str] = None,
        window_ids: Optional[Sequence[str]] = None,
        goal: str = "self",
        highlight_scale: float = 1.0,
        dtype: np.dtype = np.float32,
        solver_preference: str = "auto",
        required_layers: Optional[Sequence[str]] = None,
        build_workers: int = 0,
    ):
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

    def _load_window(self, npz_path: Path) -> _WindowData:
        with np.load(npz_path, allow_pickle=True) as data:
            raw_layers = [str(layer) for layer in data["layers"]]
            layer_names: List[str] = []
            densities: List[np.ndarray] = []
            id_maps: List[np.ndarray] = []

            for layer in raw_layers:
                if _is_via_layer(layer):
                    continue

                id_map = data[f"{layer}_idx"].astype(np.int32, copy=False)
                layer_names.append(layer)
                id_maps.append(id_map)
                densities.append((id_map > 0).astype(np.float32, copy=False))

            if not layer_names:
                raise ValueError(f"Window {npz_path.stem} has no non-VIA layers")

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

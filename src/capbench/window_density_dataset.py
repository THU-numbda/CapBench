"""
CapBench window dataset loader for cached density-window bundles.

The dataset indexes per-window density bundles and SPEF labels up front, but it
loads dense tensors lazily on first sample access. This keeps initialization
memory bounded while preserving the existing sample semantics:

* self-capacitance: one sample per conductor
* coupling-capacitance: one sample per unordered conductor pair
"""

from __future__ import annotations

import os
from bisect import bisect_right
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset
from tqdm import tqdm

from capbench._internal.common.datasets import (
    DENSITY_MAPS_DIR,
    LABELS_RAPHAEL_DIR,
    LABELS_RWCAP_DIR,
)
from capbench._internal.common.density_window_bundle import (
    density_window_bundle_path,
    discover_density_window_ids,
    load_density_window_conductor_map,
    load_density_window_density,
    load_density_window_ids,
    load_density_window_meta,
)
from capbench.formats.spef.openrcx_to_simple_spef import parse_spef_components
from capbench.formats.spef.python_parser import load_dnet_totals


@dataclass(frozen=True)
class _WindowSpec:
    name: str
    bundle_dir: Path
    layer_names: tuple[str, ...]
    layer_has_density: tuple[bool, ...]
    shape: tuple[int, int, int]
    conductor_ids: Dict[str, int]


@dataclass
class _CachedWindowData:
    density: Optional[np.ndarray]
    id_maps: np.ndarray
    conductor_coords: Dict[int, List[Tuple[int, np.ndarray, np.ndarray]]] = field(
        default_factory=dict
    )


class _SampleView:
    """Lightweight per-sample view over a compact window-local sample store."""

    __slots__ = ("_store", "_sample_idx")

    def __init__(self, store: "_WindowSampleStore", sample_idx: int):
        self._store = store
        self._sample_idx = int(sample_idx)

    @property
    def window_index(self) -> int:
        return self._store.window_index

    @property
    def window_id(self) -> str:
        return self._store.window_id

    @property
    def positive_ids(self) -> Tuple[int, ...]:
        conductor_id = int(self._store.positive_ids[self._sample_idx])
        return () if conductor_id <= 0 else (conductor_id,)

    @property
    def negative_ids(self) -> Tuple[int, ...]:
        conductor_id = int(self._store.negative_ids[self._sample_idx])
        return () if conductor_id <= 0 else (conductor_id,)

    @property
    def target_value(self) -> float:
        return float(self._store.targets[self._sample_idx])

    @property
    def label(self) -> str:
        return self._store.build_label(self._sample_idx)

    @property
    def spef_source(self) -> str:
        return self._store.spef_source

    @property
    def sample_type(self) -> str:
        return "self" if int(self._store.negative_ids[self._sample_idx]) <= 0 else "coupling"


class _WindowSampleStore:
    """Compact per-window sample metadata backed by NumPy arrays."""

    def __init__(
        self,
        *,
        window_index: int,
        window_id: str,
        spef_source: str,
        id_to_name: Dict[int, str],
        positive_ids: np.ndarray,
        negative_ids: np.ndarray,
        targets: np.ndarray,
    ) -> None:
        self.window_index = int(window_index)
        self.window_id = str(window_id)
        self.spef_source = str(spef_source)
        self.id_to_name = {
            int(conductor_id): str(name)
            for conductor_id, name in id_to_name.items()
            if int(conductor_id) > 0
        }

        self.positive_ids = np.asarray(positive_ids, dtype=np.int32)
        self.negative_ids = np.asarray(negative_ids, dtype=np.int32)
        self.targets = np.asarray(targets, dtype=np.float32)

        if self.positive_ids.shape != self.negative_ids.shape or self.positive_ids.shape != self.targets.shape:
            raise ValueError(
                "Window sample arrays must share the same shape, got "
                f"{self.positive_ids.shape}, {self.negative_ids.shape}, {self.targets.shape}"
            )

        self.positive_ids.setflags(write=False)
        self.negative_ids.setflags(write=False)
        self.targets.setflags(write=False)

    def __len__(self) -> int:
        return int(self.targets.shape[0])

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[idx] for idx in range(*index.indices(len(self)))]

        idx = int(index)
        if idx < 0:
            idx += len(self)
        if idx < 0 or idx >= len(self):
            raise IndexError(f"Sample index {index} out of range for store with {len(self)} items")
        return _SampleView(self, idx)

    def __iter__(self):
        for idx in range(len(self)):
            yield _SampleView(self, idx)

    def clone_for_window(self, window_index: int, window_id: str) -> "_WindowSampleStore":
        return _WindowSampleStore(
            window_index=window_index,
            window_id=window_id,
            spef_source=self.spef_source,
            id_to_name=self.id_to_name,
            positive_ids=self.positive_ids,
            negative_ids=self.negative_ids,
            targets=self.targets,
        )

    def build_label(self, sample_idx: int) -> str:
        positive_id = int(self.positive_ids[sample_idx])
        positive_name = self.id_to_name.get(positive_id, str(positive_id))
        negative_id = int(self.negative_ids[sample_idx])
        if negative_id <= 0:
            return f"{self.window_id}:{positive_name}"
        negative_name = self.id_to_name.get(negative_id, str(negative_id))
        return f"{self.window_id}:{positive_name}|{negative_name}"


class _GroupedCouplingStore:
    """Compact grouped coupling index backed by flat arrays plus offsets."""

    def __init__(
        self,
        *,
        window_case_ranges: Sequence[Tuple[int, int]],
        case_window_indices: np.ndarray,
        master_ids: np.ndarray,
        case_offsets: np.ndarray,
        slave_ids: np.ndarray,
        targets: np.ndarray,
        valid: np.ndarray,
    ) -> None:
        self.window_case_ranges = tuple((int(start), int(end)) for start, end in window_case_ranges)
        self.case_window_indices = np.asarray(case_window_indices, dtype=np.int32)
        self.master_ids = np.asarray(master_ids, dtype=np.int32)
        self.case_offsets = np.asarray(case_offsets, dtype=np.int64)
        self.slave_ids = np.asarray(slave_ids, dtype=np.int32)
        self.targets = np.asarray(targets, dtype=np.float32)
        self.valid = np.asarray(valid, dtype=np.uint8)

        if self.case_window_indices.shape != self.master_ids.shape:
            raise ValueError(
                "Grouped coupling case arrays must align, got "
                f"{self.case_window_indices.shape} and {self.master_ids.shape}"
            )
        if self.case_offsets.shape != (len(self.master_ids) + 1,):
            raise ValueError(
                "case_offsets must have len(master_ids) + 1 entries, got "
                f"{self.case_offsets.shape} for {len(self.master_ids)} cases"
            )
        if self.slave_ids.shape != self.targets.shape or self.slave_ids.shape != self.valid.shape:
            raise ValueError(
                "Grouped coupling flat arrays must align, got "
                f"{self.slave_ids.shape}, {self.targets.shape}, {self.valid.shape}"
            )

        self.case_window_indices.setflags(write=False)
        self.master_ids.setflags(write=False)
        self.case_offsets.setflags(write=False)
        self.slave_ids.setflags(write=False)
        self.targets.setflags(write=False)
        self.valid.setflags(write=False)

    @classmethod
    def empty(cls, num_windows: int) -> "_GroupedCouplingStore":
        return cls(
            window_case_ranges=[(0, 0) for _ in range(int(num_windows))],
            case_window_indices=np.zeros((0,), dtype=np.int32),
            master_ids=np.zeros((0,), dtype=np.int32),
            case_offsets=np.zeros((1,), dtype=np.int64),
            slave_ids=np.zeros((0,), dtype=np.int32),
            targets=np.zeros((0,), dtype=np.float32),
            valid=np.zeros((0,), dtype=np.uint8),
        )

    def __len__(self) -> int:
        return int(self.master_ids.shape[0])

    def get_window_sample_ranges(self) -> List[Tuple[int, int]]:
        return list(self.window_case_ranges)

    def get_case(self, index: int) -> Tuple[int, int, np.ndarray, np.ndarray, np.ndarray]:
        idx = int(index)
        if idx < 0:
            idx += len(self)
        if idx < 0 or idx >= len(self):
            raise IndexError(f"Grouped case index {index} out of range for store with {len(self)} items")

        start = int(self.case_offsets[idx])
        end = int(self.case_offsets[idx + 1])
        return (
            int(self.case_window_indices[idx]),
            int(self.master_ids[idx]),
            self.slave_ids[start:end].copy(),
            self.targets[start:end].copy(),
            self.valid[start:end].astype(np.float32, copy=False),
        )

    def select_windows(self, selected_indices: Sequence[int]) -> "_GroupedCouplingStore":
        window_case_ranges: List[Tuple[int, int]] = []
        case_window_indices: List[int] = []
        master_ids: List[int] = []
        case_offsets: List[int] = [0]
        slave_chunks: List[np.ndarray] = []
        target_chunks: List[np.ndarray] = []
        valid_chunks: List[np.ndarray] = []

        for new_window_idx, old_window_idx in enumerate(selected_indices):
            start_case = len(master_ids)
            old_start, old_end = self.window_case_ranges[int(old_window_idx)]
            for case_idx in range(old_start, old_end):
                slave_start = int(self.case_offsets[case_idx])
                slave_end = int(self.case_offsets[case_idx + 1])
                slave_chunks.append(self.slave_ids[slave_start:slave_end])
                target_chunks.append(self.targets[slave_start:slave_end])
                valid_chunks.append(self.valid[slave_start:slave_end])
                case_window_indices.append(new_window_idx)
                master_ids.append(int(self.master_ids[case_idx]))
                case_offsets.append(case_offsets[-1] + (slave_end - slave_start))
            window_case_ranges.append((start_case, len(master_ids)))

        flat_slave_ids = (
            np.concatenate(slave_chunks).astype(np.int32, copy=False)
            if slave_chunks
            else np.zeros((0,), dtype=np.int32)
        )
        flat_targets = (
            np.concatenate(target_chunks).astype(np.float32, copy=False)
            if target_chunks
            else np.zeros((0,), dtype=np.float32)
        )
        flat_valid = (
            np.concatenate(valid_chunks).astype(np.uint8, copy=False)
            if valid_chunks
            else np.zeros((0,), dtype=np.uint8)
        )

        return _GroupedCouplingStore(
            window_case_ranges=window_case_ranges,
            case_window_indices=np.asarray(case_window_indices, dtype=np.int32),
            master_ids=np.asarray(master_ids, dtype=np.int32),
            case_offsets=np.asarray(case_offsets, dtype=np.int64),
            slave_ids=flat_slave_ids,
            targets=flat_targets,
            valid=flat_valid,
        )


class WindowCapDataset(Dataset):
    """
    Dataset that produces CNN input tensors and capacitance targets from
    lazily-loaded density-window bundles.

    Args:
        window_dir: Directory containing `<window>/meta.json`, `density.npy`, and `id.npy`.
        spef_dir: Directory containing matching SPEF files per window.
        window_ids: Iterable of window IDs (for example `["W0", "W1"]`); discovers automatically if None.
        goal: `"self"` for self-capacitance or `"coupling"` for conductor pairs.
        highlight_scale: Deprecated compatibility flag (highlight now always adds +1 / flips sign).
        dtype: Numpy dtype for tensors prior to conversion to torch.
        solver_preference: Which SPEF solver to prefer when both RWCap and Raphael labels are available.
        build_workers: Number of workers for metadata/sample indexing (0 => automatic parallelism).
        window_cache_size: Number of windows to keep open in the per-process LRU cache.
    """

    @staticmethod
    def discover_limited_windows(
        window_dir: Path,
        max_windows: Optional[int] = None,
        spef_dir: Optional[Path] = None,
    ) -> List[str]:
        all_windows = discover_density_window_ids(window_dir)
        if max_windows is None or max_windows <= 0:
            if spef_dir is None:
                return all_windows
            valid_windows: List[str] = []
            for window_id in all_windows:
                spef_path = WindowCapDataset._find_spef_in_directory_static(window_id, spef_dir)
                if spef_path.exists():
                    valid_windows.append(window_id)
            return valid_windows

        valid_windows: List[str] = []
        for window_id in all_windows:
            if spef_dir is not None:
                spef_path = WindowCapDataset._find_spef_in_directory_static(window_id, spef_dir)
                if not spef_path.exists():
                    continue
            valid_windows.append(window_id)
            if len(valid_windows) >= max_windows:
                break
        return valid_windows

    @staticmethod
    def _find_spef_in_directory_static(window_id: str, directory: Path) -> Path:
        for suffix in (".spef", ".spef.gz"):
            candidate = directory / f"{window_id}{suffix}"
            if candidate.exists():
                return candidate
        return directory / f"{window_id}.spef"

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
        window_cache_size: int = 4,
    ):
        super().__init__()

        self.window_dir = Path(window_dir).resolve()
        if not self.window_dir.exists():
            raise FileNotFoundError(f"Window directory not found: {self.window_dir}")

        self.spef_dir = Path(spef_dir).resolve() if spef_dir is not None else None
        self.goal = goal.lower()
        if self.goal not in {"self", "coupling"}:
            raise ValueError("goal must be 'self' or 'coupling'")

        self.highlight_scale = float(highlight_scale)
        self.dtype = dtype
        self.solver_preference = solver_preference.lower()
        if self.solver_preference not in {"auto", "rwcap", "raphael"}:
            raise ValueError("solver_preference must be 'auto', 'rwcap', or 'raphael'")
        if build_workers < 0:
            raise ValueError("build_workers must be >= 0")
        if window_cache_size < 0:
            raise ValueError("window_cache_size must be >= 0")

        self._build_workers = build_workers if build_workers > 0 else max(1, os.cpu_count() or 1)
        self._window_cache_size = int(window_cache_size)
        self._window_cache: OrderedDict[str, _CachedWindowData] = OrderedDict()
        self._required_layers_override = [str(layer) for layer in required_layers] if required_layers else None

        if window_ids is None:
            window_ids = discover_density_window_ids(self.window_dir)
        else:
            window_ids = [str(window_id) for window_id in window_ids]

        if not window_ids:
            raise ValueError("No window IDs provided or discovered in window_dir")

        self._windows: List[_WindowSpec] = []
        self._window_samples: List[_WindowSampleStore] = []
        self._window_ids: List[str] = []
        self._window_spef_paths: Dict[str, Path] = {}
        self._layer_catalog: List[str] = []
        self._layer_has_data: Dict[str, bool] = {}
        self._max_height = 0
        self._max_width = 0

        entries = self._build_window_entries(window_ids)
        for _, win_id, window_spec, window_samples, spef_path in entries:
            for layer_name, has_density in zip(window_spec.layer_names, window_spec.layer_has_density):
                if layer_name not in self._layer_catalog:
                    self._layer_catalog.append(layer_name)
                self._layer_has_data[layer_name] = self._layer_has_data.get(layer_name, False) or bool(has_density)

            self._max_height = max(self._max_height, int(window_spec.shape[1]))
            self._max_width = max(self._max_width, int(window_spec.shape[2]))
            self._windows.append(window_spec)
            self._window_samples.append(window_samples)
            self._window_ids.append(win_id)
            self._window_spef_paths[win_id] = spef_path

        if self._required_layers_override:
            for layer_name in self._required_layers_override:
                if layer_name not in self._layer_catalog:
                    self._layer_catalog.append(layer_name)

        if not self._windows:
            raise RuntimeError("No window data loaded")

        if self._required_layers_override is not None:
            self._active_layers = list(self._required_layers_override)
        else:
            self._active_layers = [
                name for name in self._layer_catalog if self._layer_has_data.get(name, False)
            ]
            if not self._active_layers:
                raise RuntimeError("No active conductor layers with density data found in dataset")

        self._layer_index: Dict[str, int] = {name: idx for idx, name in enumerate(self._active_layers)}
        self._num_layers = len(self._active_layers)
        self._tensor_shape = (self._num_layers, self._max_height, self._max_width)

        self._window_sample_offsets: List[int] = []
        offset = 0
        for samples in self._window_samples:
            self._window_sample_offsets.append(offset)
            offset += len(samples)
        self._total_samples = offset

        self._grouped_coupling_store = (
            self._build_grouped_coupling_store() if self.goal == "coupling" else _GroupedCouplingStore.empty(len(self._windows))
        )

    # ------------------------------------------------------------------
    # Dataset API
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return self._total_samples

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, torch.Tensor, Dict]:
        window_idx, sample_idx = self._get_sample_indices(index)
        return self._materialize_item(window_idx, sample_idx, include_extended_meta=False)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def num_layers(self) -> int:
        return self._num_layers

    @property
    def active_layers(self) -> List[str]:
        return self._active_layers.copy()

    @property
    def tensor_shape(self) -> Tuple[int, int, int]:
        return self._tensor_shape

    def get_window_ids(self) -> List[str]:
        return self._window_ids.copy()

    def get_window_sample_ranges(self) -> List[Tuple[int, int]]:
        ranges: List[Tuple[int, int]] = []
        for start, samples in zip(self._window_sample_offsets, self._window_samples):
            ranges.append((start, start + len(samples)))
        return ranges

    def _get_window_and_cache(self, window_idx: int) -> Tuple[_WindowSpec, _CachedWindowData]:
        window = self._windows[window_idx]
        return window, self._load_cached_window_data(window)

    def _build_window_features(self, window_idx: int) -> np.ndarray:
        window, cached = self._get_window_and_cache(window_idx)
        return self._build_feature_tensor(window, cached)

    def _build_window_conductor_masks(self, window_idx: int, conductor_ids: Sequence[int]) -> np.ndarray:
        masks = np.zeros((len(conductor_ids), *self._tensor_shape), dtype=np.float32)
        if not conductor_ids:
            return masks

        _window, cached = self._get_window_and_cache(window_idx)
        for slot, conductor_id in enumerate(conductor_ids):
            for global_idx, ys, xs in cached.conductor_coords.get(int(conductor_id), ()):
                masks[slot, global_idx, ys, xs] = 1.0
        return masks

    def _build_window_local_state(
        self,
        window_idx: int,
    ) -> Tuple[np.ndarray, np.ndarray, Dict[int, int]]:
        local_map = np.zeros(self._tensor_shape, dtype=np.int64)
        window, cached = self._get_window_and_cache(window_idx)

        present_cids = sorted(cid for cid in cached.conductor_coords.keys() if int(cid) > 0)
        actual_to_local = {int(cid): idx + 1 for idx, cid in enumerate(present_cids)}
        local_counts = np.zeros((len(present_cids) + 1,), dtype=np.int64)

        for conductor_id, coord_triplets in cached.conductor_coords.items():
            local_idx = actual_to_local.get(int(conductor_id))
            if local_idx is None:
                continue
            for global_idx, ys, xs in coord_triplets:
                local_map[global_idx, ys, xs] = local_idx
                local_counts[local_idx] += int(len(ys))

        local_counts[0] = 1
        return local_map, local_counts, actual_to_local

    def get_grouped_coupling_case_count(self) -> int:
        return len(self._grouped_coupling_store)

    def get_grouped_coupling_case_ranges(self) -> List[Tuple[int, int]]:
        return self._grouped_coupling_store.get_window_sample_ranges()

    def get_grouped_coupling_case(self, index: int) -> Tuple[int, int, np.ndarray, np.ndarray, np.ndarray]:
        return self._grouped_coupling_store.get_case(index)

    def get_grouped_coupling_cases(self) -> List[Tuple[int, int, List[int], np.ndarray, np.ndarray]]:
        return [
            (
                window_index,
                master_id,
                slave_ids.tolist(),
                targets,
                valid,
            )
            for window_index, master_id, slave_ids, targets, valid in (
                self._grouped_coupling_store.get_case(idx)
                for idx in range(len(self._grouped_coupling_store))
            )
        ]

    def dump_layer_debug_visuals(
        self,
        output_dir: Path,
        num_conductors: int = 5,
        num_layers: int = 8,
    ) -> None:
        if not self._windows:
            print("Skipping debug visualization: dataset has no windows loaded")
            return

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("Skipping debug visualization: matplotlib not available")
            return

        window = self._windows[0]
        cached = self._load_cached_window_data(window)
        conductor_items = sorted(window.conductor_ids.items(), key=lambda item: item[0])
        if not conductor_items:
            print(f"Skipping debug visualization: window {window.name} has no conductor metadata")
            return

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        selected_conductors = conductor_items[: max(1, num_conductors)]
        selected_layers = self._active_layers[: max(1, min(num_layers, len(self._active_layers)))]
        if num_layers > len(self._active_layers):
            print(f"Note: Limiting debug layers to {len(self._active_layers)} (all active layers)")

        print(
            f"Generating debug density plots for window '{window.name}' "
            f"(conductors: {len(selected_conductors)}, layers per conductor: {len(selected_layers)})"
        )

        for conductor_name, conductor_id in selected_conductors:
            features = self._build_feature_tensor(window, cached)
            self._apply_highlight(features, cached, conductor_id, positive=True)

            n_layers = len(selected_layers)
            n_cols = min(4, n_layers)
            n_rows = (n_layers + n_cols - 1) // n_cols
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3.5 * n_rows))
            fig.suptitle(f"{window.name} | {conductor_name} | All Layers", fontsize=14)

            if n_rows == 1 and n_cols == 1:
                axes_list = [axes]
            elif n_rows == 1:
                axes_list = list(axes)
            elif n_cols == 1:
                axes_list = [axes[i, 0] for i in range(n_rows)]
            else:
                axes_list = list(axes.flatten())

            image = None
            for idx, layer_name in enumerate(selected_layers):
                ax = axes_list[idx]
                global_idx = self._layer_index[layer_name]
                image = ax.imshow(
                    features[global_idx],
                    cmap="coolwarm",
                    origin="lower",
                    vmin=0.0,
                    vmax=2.0,
                )
                ax.set_title(layer_name)
                ax.set_xlabel("X (tiles)")
                ax.set_ylabel("Y (tiles)")

            for idx in range(n_layers, len(axes_list)):
                axes_list[idx].axis("off")

            if image is not None:
                cbar = fig.colorbar(image, ax=axes_list, shrink=0.8, pad=0.04)
                cbar.set_label("Density", rotation=270, labelpad=15)

            safe_name = conductor_name.replace("/", "_").replace(":", "_")
            out_path = output_dir / f"{window.name}_{safe_name}_all_layers.png"
            plt.tight_layout()
            fig.savefig(out_path, dpi=200, bbox_inches="tight")
            plt.close(fig)

    def create_window_subset(self, window_ids: List[str]) -> "WindowCapDataset":
        invalid_windows = [window_id for window_id in window_ids if window_id not in self._window_ids]
        if invalid_windows:
            raise ValueError(f"Invalid window IDs: {invalid_windows}")

        idx_by_id = {window_id: idx for idx, window_id in enumerate(self._window_ids)}
        selected_indices = [idx_by_id[window_id] for window_id in window_ids]

        subset = self.__class__.__new__(self.__class__)
        subset.window_dir = self.window_dir
        subset.spef_dir = self.spef_dir
        subset.goal = self.goal
        subset.highlight_scale = self.highlight_scale
        subset.dtype = self.dtype
        subset.solver_preference = self.solver_preference
        subset._required_layers_override = (
            list(self._required_layers_override) if self._required_layers_override else None
        )
        subset._build_workers = self._build_workers
        subset._window_cache_size = self._window_cache_size
        subset._window_cache = OrderedDict()
        if hasattr(self, "_trim_margin"):
            subset._trim_margin = self._trim_margin

        subset._windows = [self._windows[idx] for idx in selected_indices]
        subset._window_ids = [self._window_ids[idx] for idx in selected_indices]
        subset._window_samples = [
            self._window_samples[idx].clone_for_window(new_idx, subset._window_ids[new_idx])
            for new_idx, idx in enumerate(selected_indices)
        ]
        subset._window_spef_paths = {window_id: self._window_spef_paths[window_id] for window_id in subset._window_ids}
        subset._layer_catalog = list(self._layer_catalog)
        subset._layer_has_data = dict(self._layer_has_data)
        subset._max_height = self._max_height
        subset._max_width = self._max_width
        subset._active_layers = list(self._active_layers)
        subset._layer_index = dict(self._layer_index)
        subset._num_layers = self._num_layers
        subset._tensor_shape = self._tensor_shape

        subset._window_sample_offsets = []
        offset = 0
        for samples in subset._window_samples:
            subset._window_sample_offsets.append(offset)
            offset += len(samples)
        subset._total_samples = offset

        subset._grouped_coupling_store = self._grouped_coupling_store.select_windows(selected_indices)

        return subset

    # ------------------------------------------------------------------
    # Build helpers
    # ------------------------------------------------------------------

    def _build_window_entries(
        self,
        window_ids: Sequence[str],
    ) -> List[Tuple[int, str, _WindowSpec, _WindowSampleStore, Path]]:
        entries: List[Tuple[int, str, _WindowSpec, _WindowSampleStore, Path]] = []
        total_windows = len(window_ids)

        if self._build_workers == 1 or total_windows <= 1:
            for idx, win_id in tqdm(
                enumerate(window_ids),
                total=total_windows,
                desc="Indexing windows",
                unit="win",
            ):
                entry = self._build_single_window_entry(idx, win_id)
                if entry is not None:
                    entries.append(entry)
            return entries

        with ThreadPoolExecutor(max_workers=min(self._build_workers, total_windows)) as executor:
            futures = {
                executor.submit(self._build_single_window_entry, idx, win_id): (idx, win_id)
                for idx, win_id in enumerate(window_ids)
            }
            for future in tqdm(
                as_completed(futures),
                total=total_windows,
                desc="Indexing windows",
                unit="win",
            ):
                entry = future.result()
                if entry is not None:
                    entries.append(entry)

        entries.sort(key=lambda item: item[0])
        return entries

    def _build_single_window_entry(
        self,
        idx: int,
        win_id: str,
    ) -> Optional[Tuple[int, str, _WindowSpec, _WindowSampleStore, Path]]:
        bundle_dir = density_window_bundle_path(self.window_dir, win_id)
        if not bundle_dir.exists():
            raise FileNotFoundError(f"Missing density bundle for window {win_id}: {bundle_dir}")

        try:
            window_spec = self._load_window_spec(bundle_dir)
        except ValueError:
            return None

        try:
            spef_path = self._find_spef_for_window(win_id)
        except FileNotFoundError:
            return None

        self_caps, coupling_map = self._load_capacitances(spef_path)
        centroids = self._compute_conductor_centroids(window_spec) if self.goal == "coupling" else None
        window_samples = self._generate_samples(
            idx,
            win_id,
            window_spec,
            self_caps,
            coupling_map,
            str(spef_path),
            centroids=centroids,
        )
        if not window_samples:
            return None

        return idx, win_id, window_spec, window_samples, spef_path

    # ------------------------------------------------------------------
    # Lazy window loading
    # ------------------------------------------------------------------

    def _load_window_spec(self, bundle_dir: Path) -> _WindowSpec:
        meta = load_density_window_meta(bundle_dir)
        if not meta.layer_names:
            raise ValueError(f"Window {bundle_dir.name} has no layers")
        return _WindowSpec(
            name=meta.window_id,
            bundle_dir=bundle_dir,
            layer_names=meta.layer_names,
            layer_has_density=meta.layer_has_density,
            shape=meta.shape,
            conductor_ids=load_density_window_conductor_map(bundle_dir),
        )

    def _load_id_maps(self, window: _WindowSpec, *, mmap_mode: str | None = "r") -> np.ndarray:
        id_maps = load_density_window_ids(window.bundle_dir, mmap_mode=mmap_mode)
        if tuple(int(v) for v in id_maps.shape) != window.shape:
            raise ValueError(
                f"ID-map shape mismatch for {window.bundle_dir}: expected {window.shape}, got {id_maps.shape}"
            )
        return self._transform_id_maps(window, id_maps)

    def _transform_id_maps(self, window: _WindowSpec, id_maps: np.ndarray) -> np.ndarray:
        return id_maps.astype(np.int32, copy=False)

    def _load_density_for_cache(self, window: _WindowSpec) -> Optional[np.ndarray]:
        density = load_density_window_density(window.bundle_dir, mmap_mode="r")
        if tuple(int(v) for v in density.shape) != window.shape:
            raise ValueError(
                f"Density shape mismatch for {window.bundle_dir}: expected {window.shape}, got {density.shape}"
            )
        return density

    def _load_cached_window_data(self, window: _WindowSpec) -> _CachedWindowData:
        cached = self._window_cache.get(window.name)
        if cached is not None:
            self._window_cache.move_to_end(window.name)
            return cached

        id_maps = self._load_id_maps(window, mmap_mode="r")
        cached = _CachedWindowData(
            density=self._load_density_for_cache(window),
            id_maps=id_maps,
            conductor_coords=self._build_conductor_coords(window, id_maps),
        )

        if self._window_cache_size > 0:
            self._window_cache[window.name] = cached
            self._window_cache.move_to_end(window.name)
            while len(self._window_cache) > self._window_cache_size:
                self._window_cache.popitem(last=False)
        return cached

    def _build_conductor_coords(
        self,
        window: _WindowSpec,
        id_maps: np.ndarray,
    ) -> Dict[int, List[Tuple[int, np.ndarray, np.ndarray]]]:
        coords_by_cid: Dict[int, List[Tuple[int, np.ndarray, np.ndarray]]] = defaultdict(list)
        for local_idx, layer_name in enumerate(window.layer_names):
            global_idx = self._layer_index.get(layer_name)
            if global_idx is None:
                continue

            layer_id_map = id_maps[local_idx]
            ys, xs = np.nonzero(layer_id_map)
            if ys.size == 0:
                continue
            ids = layer_id_map[ys, xs]
            for cid in np.unique(ids):
                cid_int = int(cid)
                if cid_int <= 0:
                    continue
                mask = ids == cid
                coords_by_cid[cid_int].append(
                    (
                        global_idx,
                        ys[mask].astype(np.int32, copy=False),
                        xs[mask].astype(np.int32, copy=False),
                    )
                )
        return dict(coords_by_cid)

    # ------------------------------------------------------------------
    # Sample materialization
    # ------------------------------------------------------------------

    def _materialize_item(
        self,
        window_idx: int,
        sample_idx: int,
        *,
        include_extended_meta: bool,
    ) -> Tuple[torch.Tensor, torch.Tensor, Dict]:
        sample = self._window_samples[window_idx][sample_idx]
        window = self._windows[window_idx]
        cached = self._load_cached_window_data(window)

        features = self._build_feature_tensor(window, cached)
        for pos_id in sample.positive_ids:
            self._apply_highlight(features, cached, pos_id, positive=True)
        for neg_id in sample.negative_ids:
            self._apply_highlight(features, cached, neg_id, positive=False)

        tensor = torch.from_numpy(features.astype(self.dtype, copy=False))
        target = torch.tensor([sample.target_value], dtype=torch.float32)
        meta = {
            "window": window.name,
            "label": sample.label,
            "positive_conductors": sample.positive_ids,
            "negative_conductors": sample.negative_ids,
        }
        if include_extended_meta:
            meta["sample_type"] = sample.sample_type
            meta["spef_source"] = sample.spef_source
        return tensor, target, meta

    def _build_feature_tensor(self, window: _WindowSpec, cached: _CachedWindowData) -> np.ndarray:
        features = np.zeros(self._tensor_shape, dtype=np.float32)
        self._fill_base_features(features, window, cached)
        return features

    def _fill_base_features(
        self,
        features: np.ndarray,
        window: _WindowSpec,
        cached: _CachedWindowData,
    ) -> None:
        if cached.density is None:
            raise RuntimeError("Density tensors are not available for this dataset variant")
        for local_idx, layer_name in enumerate(window.layer_names):
            global_idx = self._layer_index.get(layer_name)
            if global_idx is None:
                continue
            layer_density = cached.density[local_idx]
            h, w = layer_density.shape
            features[global_idx, :h, :w] = layer_density

    def _apply_highlight(
        self,
        features: np.ndarray,
        cached: _CachedWindowData,
        conductor_id: int,
        *,
        positive: bool,
    ) -> None:
        coords = cached.conductor_coords.get(int(conductor_id))
        if not coords:
            return

        for global_idx, ys, xs in coords:
            if positive:
                features[global_idx, ys, xs] = features[global_idx, ys, xs] + 1.0
            else:
                features[global_idx, ys, xs] = -features[global_idx, ys, xs]

    def _get_sample_indices(self, global_index: int) -> Tuple[int, int]:
        if global_index < 0 or global_index >= self._total_samples:
            raise IndexError(f"Index {global_index} out of range for dataset with {self._total_samples} samples")

        window_idx = bisect_right(self._window_sample_offsets, global_index) - 1
        sample_idx = global_index - self._window_sample_offsets[window_idx]
        return window_idx, sample_idx

    def _get_item_window_level(self, window_idx: int, sample_idx: int) -> Tuple[torch.Tensor, torch.Tensor, Dict]:
        return self._materialize_item(window_idx, sample_idx, include_extended_meta=True)

    # ------------------------------------------------------------------
    # SPEF + sample indexing
    # ------------------------------------------------------------------

    def _solver_priority(self) -> List[str]:
        if self.solver_preference == "raphael":
            return ["raphael", "rwcap"]
        return ["rwcap", "raphael"]

    def _find_spef_in_directory(self, window_id: str, directory: Path) -> Path:
        for suffix in (".spef", ".spef.gz"):
            candidate = directory / f"{window_id}{suffix}"
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"No SPEF file named {window_id}.spef found in {directory}")

    def _label_directories(self) -> List[Tuple[str, Path]]:
        return [("rwcap", LABELS_RWCAP_DIR), ("raphael", LABELS_RAPHAEL_DIR)]

    def _find_spef_for_window(self, window_id: str) -> Path:
        if self.spef_dir is not None:
            return self._find_spef_in_directory(window_id, self.spef_dir)

        for solver, directory in self._label_directories():
            if not directory.exists():
                continue
            try:
                return self._find_spef_in_directory(window_id, directory)
            except FileNotFoundError:
                continue

        raise FileNotFoundError(
            f"No SPEF file found for window {window_id}. "
            f"Checked {[str(directory) for _, directory in self._label_directories()]}"
        )

    def _load_capacitances(
        self,
        spef_path: Path,
    ) -> Tuple[Dict[str, float], Dict[Tuple[str, str], float]]:
        pair_caps: Dict[Tuple[str, str], float] = {}
        if self.goal == "self":
            total_caps = load_dnet_totals(str(spef_path))
            self_caps = {str(name): float(value) for name, value in total_caps.items()}
            return self_caps, pair_caps

        _, adjacency, _ = parse_spef_components(str(spef_path))
        for name_a, neighbors in adjacency.items():
            neighbor_iter = neighbors.items() if isinstance(neighbors, dict) else neighbors
            for name_b, value in neighbor_iter:
                raw_a = str(name_a)
                raw_b = str(name_b)
                if raw_a == raw_b:
                    continue
                pair = tuple(sorted((raw_a, raw_b)))
                if pair in pair_caps:
                    pair_caps[pair] = 0.5 * (pair_caps[pair] + value)
                else:
                    pair_caps[pair] = value
        return {}, pair_caps

    def _generate_samples(
        self,
        window_index: int,
        window_id: str,
        window: _WindowSpec,
        self_caps: Dict[str, float],
        pair_caps: Dict[Tuple[str, str], float],
        spef_path: str,
        *,
        centroids: Optional[Dict[int, Tuple[float, float, float]]] = None,
    ) -> _WindowSampleStore:
        id_to_name = {int(conductor_id): str(name) for name, conductor_id in window.conductor_ids.items()}
        positive_ids: List[int] = []
        negative_ids: List[int] = []
        targets: List[float] = []

        if self.goal == "self":
            seen_conductor_ids: set[int] = set()
            for spef_name, cap in self_caps.items():
                conductor_id = window.conductor_ids.get(str(spef_name))
                if conductor_id is None or conductor_id in seen_conductor_ids:
                    continue
                seen_conductor_ids.add(conductor_id)
                positive_ids.append(int(conductor_id))
                negative_ids.append(0)
                targets.append(float(cap) * 1e15)
            return _WindowSampleStore(
                window_index=window_index,
                window_id=window_id,
                spef_source=spef_path,
                id_to_name=id_to_name,
                positive_ids=np.asarray(positive_ids, dtype=np.int32),
                negative_ids=np.asarray(negative_ids, dtype=np.int32),
                targets=np.asarray(targets, dtype=np.float32),
            )

        centroid_map = centroids or {}
        seen_pairs: set[tuple[int, int]] = set()
        for (name_a, name_b), value in pair_caps.items():
            id_a = window.conductor_ids.get(str(name_a))
            id_b = window.conductor_ids.get(str(name_b))
            if id_a is None or id_b is None or value <= 1e-20:
                continue

            pair_ids = tuple(sorted((id_a, id_b)))
            if pair_ids in seen_pairs:
                continue
            seen_pairs.add(pair_ids)

            dist_a = self._coordinate_distance_sq(centroid_map.get(id_a))
            dist_b = self._coordinate_distance_sq(centroid_map.get(id_b))
            if dist_a <= dist_b:
                master_id, slave_id = id_a, id_b
            else:
                master_id, slave_id = id_b, id_a
            positive_ids.append(int(master_id))
            negative_ids.append(int(slave_id))
            targets.append(float(value) * 1e15)

        return _WindowSampleStore(
            window_index=window_index,
            window_id=window_id,
            spef_source=spef_path,
            id_to_name=id_to_name,
            positive_ids=np.asarray(positive_ids, dtype=np.int32),
            negative_ids=np.asarray(negative_ids, dtype=np.int32),
            targets=np.asarray(targets, dtype=np.float32),
        )

    def _compute_conductor_centroids(
        self,
        window: _WindowSpec,
    ) -> Dict[int, Tuple[float, float, float]]:
        id_maps = self._load_id_maps(window, mmap_mode="r")
        accum: Dict[int, np.ndarray] = defaultdict(lambda: np.zeros(3, dtype=np.float64))
        counts: Dict[int, int] = defaultdict(int)

        for layer_idx, id_map in enumerate(id_maps):
            ys, xs = np.nonzero(id_map)
            if ys.size == 0:
                continue
            ids = id_map[ys, xs]
            layer_coords = np.full(len(ids), layer_idx, dtype=np.float64)
            coords = np.stack((layer_coords, ys.astype(np.float64), xs.astype(np.float64)), axis=1)
            for idx, cid in enumerate(ids):
                cid_int = int(cid)
                if cid_int <= 0:
                    continue
                accum[cid_int] += coords[idx]
                counts[cid_int] += 1

        centroids: Dict[int, Tuple[float, float, float]] = {}
        for cid, total in accum.items():
            count = counts[cid]
            if count > 0:
                centroids[cid] = tuple(total / count)
        return centroids

    def _build_grouped_coupling_store(self) -> _GroupedCouplingStore:
        window_case_ranges: List[Tuple[int, int]] = []
        case_window_indices: List[int] = []
        master_ids: List[int] = []
        case_offsets: List[int] = [0]
        slave_chunks: List[np.ndarray] = []
        target_chunks: List[np.ndarray] = []
        valid_chunks: List[np.ndarray] = []

        for window_idx, samples in enumerate(self._window_samples):
            pair_values: Dict[Tuple[int, int], List[float]] = defaultdict(list)
            present_ids: set[int] = {
                int(conductor_id)
                for conductor_id in self._windows[window_idx].conductor_ids.values()
                if int(conductor_id) > 0
            }

            start_case = len(master_ids)
            for positive_id, negative_id, target_value in zip(
                samples.positive_ids,
                samples.negative_ids,
                samples.targets,
            ):
                if int(positive_id) <= 0 or int(negative_id) <= 0:
                    continue
                a = int(positive_id)
                b = int(negative_id)
                present_ids.add(a)
                present_ids.add(b)
                pair_values[tuple(sorted((a, b)))].append(float(target_value))

            if len(present_ids) < 2:
                window_case_ranges.append((start_case, start_case))
                continue

            pair_targets = {
                pair: float(np.mean(values))
                for pair, values in pair_values.items()
                if values
            }

            for master_id in sorted(present_ids):
                slave_ids = np.asarray(
                    [cid for cid in sorted(present_ids) if cid != master_id],
                    dtype=np.int32,
                )
                if slave_ids.size == 0:
                    continue

                targets = np.zeros((len(slave_ids),), dtype=np.float32)
                valid = np.zeros((len(slave_ids),), dtype=np.uint8)
                for idx, slave_id in enumerate(slave_ids):
                    cap = pair_targets.get(tuple(sorted((master_id, slave_id))))
                    if cap is None:
                        continue
                    targets[idx] = cap
                    valid[idx] = 1

                case_window_indices.append(window_idx)
                master_ids.append(int(master_id))
                slave_chunks.append(slave_ids)
                target_chunks.append(targets)
                valid_chunks.append(valid)
                case_offsets.append(case_offsets[-1] + int(len(slave_ids)))

            window_case_ranges.append((start_case, len(master_ids)))

        flat_slave_ids = (
            np.concatenate(slave_chunks).astype(np.int32, copy=False)
            if slave_chunks
            else np.zeros((0,), dtype=np.int32)
        )
        flat_targets = (
            np.concatenate(target_chunks).astype(np.float32, copy=False)
            if target_chunks
            else np.zeros((0,), dtype=np.float32)
        )
        flat_valid = (
            np.concatenate(valid_chunks).astype(np.uint8, copy=False)
            if valid_chunks
            else np.zeros((0,), dtype=np.uint8)
        )

        return _GroupedCouplingStore(
            window_case_ranges=window_case_ranges,
            case_window_indices=np.asarray(case_window_indices, dtype=np.int32),
            master_ids=np.asarray(master_ids, dtype=np.int32),
            case_offsets=np.asarray(case_offsets, dtype=np.int64),
            slave_ids=flat_slave_ids,
            targets=flat_targets,
            valid=flat_valid,
        )

    @staticmethod
    def _coordinate_distance_sq(coord: Optional[Tuple[float, float, float]]) -> float:
        if coord is None:
            return float("inf")
        z, y, x = coord
        return float(z * z + y * y + x * x)

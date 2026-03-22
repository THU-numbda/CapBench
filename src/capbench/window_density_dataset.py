"""
CapBench window dataset loader for cached density-map artifacts.

This loader ingests the per-window density map NPZ produced by cap3d_to_cnncap.py
and pairs it with capacitance targets parsed from corresponding SPEF reports.
It expands each window into many training samples:
  * self-capacitance: one sample per conductor
  * coupling-capacitance: one sample per unordered conductor pair

Each sample uses the 3D density tensor for the window and boosts/suppresses the
densities of the conductors of interest so the network can focus on them.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset
from tqdm import tqdm

from capbench.formats.spef.openrcx_to_simple_spef import parse_spef_components
from capbench.formats.spef.python_parser import load_dnet_totals
from capbench._internal.common.datasets import (
    DENSITY_MAPS_DIR,
    LABELS_RAPHAEL_DIR,
    LABELS_RWCAP_DIR,
)

def _is_via_layer(layer_name: str) -> bool:
    """Treat VIA layers as non-trainable channels and skip them entirely."""
    upper = layer_name.upper()
    return "VIA" in upper


@dataclass
class _WindowData:
    name: str
    layer_names: List[str]
    densities: List[np.ndarray]  # length L, each entry shape (H, W), float32
    id_maps: List[np.ndarray]  # length L, int32
    conductor_ids: Dict[str, int]  # actual name -> id
    base_features: Optional[np.ndarray] = None
    conductor_coords: Dict[int, List[Tuple[int, np.ndarray, np.ndarray]]] = field(default_factory=dict)
    conductor_local_map: Optional[np.ndarray] = None  # shape (L, H, W), 0 = background, >0 = local conductor index
    local_counts: Optional[np.ndarray] = None  # shape (num_local + 1,), pixel counts by local index
    actual_to_local: Dict[int, int] = field(default_factory=dict)


@dataclass
class _SampleMeta:
    window_index: int
    window_id: str
    positive_ids: Tuple[int, ...]
    negative_ids: Tuple[int, ...]
    target_value: float
    label: str
    spef_source: str  # MANDATORY: SPEF file reference

    @property
    def sample_type(self) -> str:
        return "self" if len(self.negative_ids) == 0 else "coupling"


@dataclass
class _GroupedCouplingCase:
    window_index: int
    master_id: int
    slave_ids: Tuple[int, ...]
    targets: np.ndarray
    valid: np.ndarray


class WindowCapDataset(Dataset):
    """
    Dataset that produces CNN input tensors and capacitance targets from window data.

    Args:
        window_dir: Directory containing <window>.npz (and optional <window>.yaml).
        spef_dir: Directory containing matching SPEF files per window.
        window_ids: Iterable of window IDs (e.g. ["W0", "W1"]); discovers automatically if None.
        goal: "self" for self-capacitance or "coupling" for coupling capacitance pairs.
        highlight_scale: Deprecated compatibility flag (highlight now always adds +1 / flips sign).
        dtype: Numpy dtype for tensors prior to conversion to torch.
        solver_preference: Which SPEF solver to prefer when both RWCap and Raphael labels are available.
        build_workers: Number of workers for window preprocessing (0 => automatic parallelism).
    """

    @staticmethod
    def discover_limited_windows(window_dir: Path, max_windows: Optional[int] = None, spef_dir: Optional[Path] = None) -> List[str]:
        """
        Discover window IDs with early stopping for performance, ensuring SPEF availability.

        Args:
            window_dir: Directory containing NPZ files
            max_windows: Maximum number of valid windows to discover (None = all)
            spef_dir: Directory containing SPEF files for validation

        Returns:
            List of window IDs that have both NPZ and SPEF files
        """
        if max_windows is None or max_windows <= 0:
            all_npes = sorted(p.stem for p in window_dir.glob("*.npz"))
            if spef_dir:
                valid_windows = []
                for window_id in all_npes:
                    spef_path = WindowCapDataset._find_spef_in_directory_static(window_id, spef_dir)
                    if spef_path and spef_path.exists():
                        valid_windows.append(window_id)
                return valid_windows
            return all_npes

        valid_windows = []

        for npz_path in sorted(window_dir.glob("*.npz")):
            window_id = npz_path.stem

            if spef_dir:
                spef_path = WindowCapDataset._find_spef_in_directory_static(window_id, spef_dir)
                if not spef_path or not spef_path.exists():
                    continue

            valid_windows.append(window_id)

            if len(valid_windows) >= max_windows:
                break

        return valid_windows

    @staticmethod
    def _find_spef_in_directory_static(window_id: str, directory: Path) -> Path:
        """Static version of SPEF finding for use in discovery."""
        # Try common SPEF naming patterns
        potential_names = [
            f"{window_id}.spef",
            f"{window_id}.spef.gz",
        ]

        for potential_name in potential_names:
            spef_path = directory / potential_name
            if spef_path.exists():
                return spef_path

        # Return non-existent path if not found
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
        self._build_workers = build_workers if build_workers > 0 else max(1, os.cpu_count() or 1)

        if required_layers:
            filtered_required = [str(layer) for layer in required_layers if not _is_via_layer(str(layer))]
            self._required_layers_override = filtered_required or None
        else:
            self._required_layers_override = None

        if window_ids is None:
            window_ids = sorted(p.stem for p in self.window_dir.glob("*.npz"))

        if not window_ids:
            raise ValueError("No window IDs provided or discovered in window_dir")

        self._windows: List[_WindowData] = []
        self._window_samples: List[List[_SampleMeta]] = []  # Per-window sample arrays
        self._window_ids: List[str] = []
        self._window_spef_paths: Dict[str, Path] = {}
        self._layer_catalog: List[str] = []
        self._layer_has_data: Dict[str, bool] = {}
        self._max_height = 0
        self._max_width = 0

        entries = self._build_window_entries(window_ids)
        for idx, win_id, window_data, window_samples, spef_path in entries:
            for local_idx, layer_name in enumerate(window_data.layer_names):
                if layer_name not in self._layer_catalog:
                    self._layer_catalog.append(layer_name)
                if layer_name not in self._layer_has_data:
                    self._layer_has_data[layer_name] = False
                if np.any(window_data.densities[local_idx]):
                    self._layer_has_data[layer_name] = True

            for layer_density in window_data.densities:
                self._max_height = max(self._max_height, layer_density.shape[0])
                self._max_width = max(self._max_width, layer_density.shape[1])
            self._windows.append(window_data)
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
        self._prepare_window_tensors()
        self._grouped_coupling_cases: List[_GroupedCouplingCase] = (
            self._build_grouped_coupling_cases() if self.goal == "coupling" else []
        )

    # ------------------------------------------------------------------
    # Dataset API
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        """Total number of samples across all windows."""
        return sum(len(window_samples) for window_samples in self._window_samples)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, torch.Tensor, Dict]:
        """Get sample by index using window-level storage."""
        window_idx, sample_idx = self._get_sample_indices(index)
        sample = self._window_samples[window_idx][sample_idx]
        window = self._windows[window_idx]
        if window.base_features is not None:
            features = window.base_features.copy()
        else:
            features = np.zeros(self._tensor_shape, dtype=np.float32)
            for local_idx, layer_name in enumerate(window.layer_names):
                global_idx = self._layer_index.get(layer_name)
                if global_idx is None:
                    continue
                layer_density = window.densities[local_idx]
                h, w = layer_density.shape
                features[global_idx, :h, :w] = layer_density

        for pos_id in sample.positive_ids:
            self._apply_highlight(features, window, pos_id, positive=True)
        for neg_id in sample.negative_ids:
            self._apply_highlight(features, window, neg_id, positive=False)

        tensor = torch.from_numpy(features.astype(self.dtype, copy=False))
        target = torch.tensor([sample.target_value], dtype=torch.float32)
        meta = {
            "window": window.name,
            "label": sample.label,
            "positive_conductors": sample.positive_ids,
            "negative_conductors": sample.negative_ids,
        }
        return tensor, target, meta

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
        """Return list of all window IDs in the dataset."""
        return self._window_ids.copy()

    def get_grouped_coupling_cases(self) -> List[Tuple[int, int, List[int], np.ndarray, np.ndarray]]:
        """Return prebuilt (window, master, slave-list, targets, valid-mask) grouped coupling cases."""
        return [
            (
                case.window_index,
                case.master_id,
                list(case.slave_ids),
                case.targets.copy(),
                case.valid.copy(),
            )
            for case in self._grouped_coupling_cases
        ]

    def dump_layer_debug_visuals(
        self,
        output_dir: Path,
        num_conductors: int = 5,
        num_layers: int = 8,
    ) -> None:
        """Generate per-layer density heatmaps for the first window and selected conductors."""
        if not self._windows:
            print("Skipping debug visualization: dataset has no windows loaded")
            return

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("Skipping debug visualization: matplotlib not available")
            return

        window = self._windows[0]
        conductor_items = sorted(window.conductor_ids.items(), key=lambda kv: kv[0])
        if not conductor_items:
            print(f"Skipping debug visualization: window {window.name} has no conductor metadata")
            return

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        selected_conductors = conductor_items[: max(1, num_conductors)]
        # Use the same layers as training for consistency
        selected_layers = self._active_layers[: max(1, min(num_layers, len(self._active_layers)))]

        # Provide feedback if user requested more layers than available
        if num_layers > len(self._active_layers):
            print(f"Note: Limiting debug layers to {len(self._active_layers)} (all active layers)")

        print(
            f"Generating debug density plots for window '{window.name}' "
            f"(conductors: {len(selected_conductors)}, layers per conductor: {len(selected_layers)})"
        )

        # Create subplot images - one per conductor with all layers
        for cname, cid in selected_conductors:
            safe_conductor = cname.replace("/", "_").replace(":", "_")

            # Calculate subplot grid dimensions
            n_layers = len(selected_layers)
            n_cols = min(4, n_layers)  # Max 4 columns
            n_rows = (n_layers + n_cols - 1) // n_cols

            # Create figure with subplots
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3.5 * n_rows))
            fig.suptitle(f"{window.name} | {cname} | All Layers", fontsize=14)

            # Handle the case where we have only 1 row or 1 column
            if n_rows == 1 and n_cols == 1:
                axes = [axes]
            elif n_rows == 1:
                axes = axes
            elif n_cols == 1:
                axes = axes.reshape(-1, 1)
            else:
                axes = axes.flatten()

            for i, layer_name in enumerate(selected_layers):
                if layer_name not in window.layer_names:
                    continue

                layer_idx = window.layer_names.index(layer_name)
                # Apply the legacy density-map highlighting used for focused-query samples.
                density = window.densities[layer_idx].copy()  # Start with raw density

                # Use same highlighting logic as _apply_highlight() function
                layer_name = selected_layers[i]
                if layer_name in self._layer_index:
                    global_idx = self._layer_index[layer_name]
                    id_map = window.id_maps[layer_idx]

                    # Apply correct conductor highlighting (same as training)
                    mask = (id_map == cid)  # cid is the correct conductor ID from window.conductor_ids
                    if np.any(mask):
                        # Handle padding like in training
                        h, w = id_map.shape
                        if h != self._max_height or w != self._max_width:
                            padded_density = np.zeros((self._max_height, self._max_width), dtype=density.dtype)
                            padded_density[:h, :w] = density
                            density = padded_density

                            padded_mask = np.zeros((self._max_height, self._max_width), dtype=bool)
                            padded_mask[:h, :w] = mask
                            mask = padded_mask

                        # Apply same +1.0 boost as training
                        density[mask] = density[mask] + 1.0

                # Select appropriate subplot
                if n_rows == 1:
                    ax = axes[i] if n_cols > 1 else axes[0]
                elif n_cols == 1:
                    ax = axes[i, 0]
                else:
                    ax = axes[i]

                # Plot density map with 0-2 scale range (normal: 0-1, highlighted: 1-2)
                im = ax.imshow(density, cmap="coolwarm", origin="lower", vmin=0.0, vmax=2.0)
                ax.set_title(f"{layer_name}")
                ax.set_xlabel("X (tiles)")
                ax.set_ylabel("Y (tiles)")

            # Hide unused subplots
            for i in range(n_layers, len(axes)):
                if hasattr(axes[i], 'axis'):
                    axes[i].axis('off')

            # Add colorbar
            if n_layers > 0:
                cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.8, pad=0.04)
                cbar.set_label("Density", rotation=270, labelpad=15)

            # Save the combined figure
            out_path = output_dir / f"{window.name}_{safe_conductor}_all_layers.png"
            plt.tight_layout()
            fig.savefig(out_path, dpi=200, bbox_inches='tight')
            plt.close(fig)

    def create_window_subset(self, window_ids: List[str]) -> 'WindowCapDataset':
        """Create lightweight subset containing only specified windows."""
        invalid_windows = [wid for wid in window_ids if wid not in self._window_ids]
        if invalid_windows:
            raise ValueError(f"Invalid window IDs: {invalid_windows}")

        idx_by_id = {wid: i for i, wid in enumerate(self._window_ids)}
        selected_indices = [idx_by_id[wid] for wid in window_ids]

        subset = WindowCapDataset.__new__(WindowCapDataset)
        subset.window_dir = self.window_dir
        subset.spef_dir = self.spef_dir
        subset.goal = self.goal
        subset.highlight_scale = self.highlight_scale
        subset.dtype = self.dtype
        subset.solver_preference = self.solver_preference
        subset._required_layers_override = list(self._required_layers_override) if self._required_layers_override else None
        subset._build_workers = self._build_workers

        subset._windows = [self._windows[i] for i in selected_indices]
        subset._window_samples = [self._window_samples[i] for i in selected_indices]
        subset._window_ids = [self._window_ids[i] for i in selected_indices]
        subset._window_spef_paths = {wid: self._window_spef_paths[wid] for wid in subset._window_ids}
        subset._layer_catalog = list(self._layer_catalog)
        subset._layer_has_data = dict(self._layer_has_data)
        subset._max_height = self._max_height
        subset._max_width = self._max_width
        subset._active_layers = list(self._active_layers)
        subset._layer_index = dict(self._layer_index)
        subset._num_layers = self._num_layers
        subset._tensor_shape = self._tensor_shape
        old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(selected_indices)}
        subset._grouped_coupling_cases = []
        for case in self._grouped_coupling_cases:
            new_idx = old_to_new.get(case.window_index)
            if new_idx is None:
                continue
            subset._grouped_coupling_cases.append(
                _GroupedCouplingCase(
                    window_index=new_idx,
                    master_id=case.master_id,
                    slave_ids=case.slave_ids,
                    targets=case.targets.copy(),
                    valid=case.valid.copy(),
                )
            )

        return subset

    def _get_sample_indices(self, global_index: int) -> Tuple[int, int]:
        """Convert global sample index to (window_idx, sample_idx)."""
        cumulative_count = 0
        for window_idx, window_samples in enumerate(self._window_samples):
            if global_index < cumulative_count + len(window_samples):
                sample_idx = global_index - cumulative_count
                return window_idx, sample_idx
            cumulative_count += len(window_samples)

        raise IndexError(f"Index {global_index} out of range for dataset with {len(self)} samples")

    def _get_item_window_level(self, window_idx: int, sample_idx: int) -> Tuple[torch.Tensor, torch.Tensor, Dict]:
        """Get sample using window-level indexing (for WindowSubsetDataset)."""
        sample = self._window_samples[window_idx][sample_idx]
        window = self._windows[window_idx]
        if window.base_features is not None:
            features = window.base_features.copy()
        else:
            features = np.zeros(self._tensor_shape, dtype=np.float32)
            for local_idx, layer_name in enumerate(window.layer_names):
                global_idx = self._layer_index.get(layer_name)
                if global_idx is None:
                    continue
                layer_density = window.densities[local_idx]
                h, w = layer_density.shape
                features[global_idx, :h, :w] = layer_density

        for pos_id in sample.positive_ids:
            self._apply_highlight(features, window, pos_id, positive=True)
        for neg_id in sample.negative_ids:
            self._apply_highlight(features, window, neg_id, positive=False)

        tensor = torch.from_numpy(features.astype(self.dtype, copy=False))
        target = torch.tensor([sample.target_value], dtype=torch.float32)
        meta = {
            "window": window.name,
            "label": sample.label,
            "positive_conductors": sample.positive_ids,
            "negative_conductors": sample.negative_ids,
            "sample_type": sample.sample_type,
            "spef_source": sample.spef_source,
        }
        return tensor, target, meta

    # ------------------------------------------------------------------
    # Build helpers
    # ------------------------------------------------------------------

    def _build_window_entries(
        self,
        window_ids: Sequence[str],
    ) -> List[Tuple[int, str, _WindowData, List[_SampleMeta], Path]]:
        entries: List[Tuple[int, str, _WindowData, List[_SampleMeta], Path]] = []
        total_windows = len(window_ids)

        if self._build_workers == 1 or total_windows <= 1:
            for idx, win_id in tqdm(
                enumerate(window_ids),
                total=total_windows,
                desc="Loading windows",
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
                desc="Loading windows",
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
    ) -> Optional[Tuple[int, str, _WindowData, List[_SampleMeta], Path]]:
        npz_path = self.window_dir / f"{win_id}.npz"
        if not npz_path.exists():
            raise FileNotFoundError(f"Missing NPZ for window {win_id}: {npz_path}")

        try:
            window_data = self._load_window(npz_path)
        except ValueError:
            return None
        try:
            spef_path = self._find_spef_for_window(win_id)
        except FileNotFoundError:
            return None

        self_caps, coupling_map = self._load_capacitances(spef_path)
        window_samples = self._generate_samples(idx, win_id, window_data, self_caps, coupling_map, str(spef_path))
        if not window_samples:
            return None

        return idx, win_id, window_data, window_samples, spef_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_window(self, npz_path: Path) -> _WindowData:
        with np.load(npz_path, allow_pickle=True) as data:
            raw_layers = [str(layer) for layer in data["layers"]]
            layer_names: List[str] = []
            densities: List[np.ndarray] = []
            id_maps: List[np.ndarray] = []
            for layer in raw_layers:
                if _is_via_layer(layer):
                    continue
                layer_names.append(layer)
                densities.append(data[f"{layer}_img"].astype(np.float32, copy=False))
                id_maps.append(data[f"{layer}_idx"].astype(np.int32, copy=False))

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

    def _prepare_window_tensors(self) -> None:
        """Precompute per-window feature tensor and sparse conductor coordinates."""
        max_local_len = 1
        for window in self._windows:
            features = np.zeros(self._tensor_shape, dtype=np.float32)
            coords_by_cid: Dict[int, List[Tuple[int, np.ndarray, np.ndarray]]] = defaultdict(list)

            for local_idx, layer_name in enumerate(window.layer_names):
                global_idx = self._layer_index.get(layer_name)
                if global_idx is None:
                    continue

                density = window.densities[local_idx]
                h, w = density.shape
                features[global_idx, :h, :w] = density

                id_map = window.id_maps[local_idx]
                ys, xs = np.nonzero(id_map)
                if ys.size == 0:
                    continue
                ids = id_map[ys, xs]
                for cid in np.unique(ids):
                    cid_int = int(cid)
                    if cid_int <= 0:
                        continue
                    mask = ids == cid
                    if not np.any(mask):
                        continue
                    coords_by_cid[cid_int].append(
                        (
                            global_idx,
                            ys[mask].astype(np.int32, copy=False),
                            xs[mask].astype(np.int32, copy=False),
                        )
                    )

            window.base_features = features
            window.conductor_coords = dict(coords_by_cid)
            present_cids = sorted(cid for cid in window.conductor_coords.keys() if cid > 0)
            actual_to_local = {cid: i + 1 for i, cid in enumerate(present_cids)}
            local_map = np.zeros(self._tensor_shape, dtype=np.int32)
            local_counts = np.zeros((len(present_cids) + 1,), dtype=np.float32)
            for cid, coord_triplets in window.conductor_coords.items():
                local_idx = actual_to_local.get(cid)
                if local_idx is None:
                    continue
                for global_idx, ys, xs in coord_triplets:
                    local_map[global_idx, ys, xs] = local_idx
                    local_counts[local_idx] += float(len(ys))

            # Keep background count non-zero to avoid divide-by-zero in padded gather slots.
            local_counts[0] = 1.0
            window.conductor_local_map = local_map
            window.local_counts = local_counts
            window.actual_to_local = actual_to_local
            max_local_len = max(max_local_len, int(local_counts.shape[0]))

        # Pad local-count vectors to a fixed global size for more stable batch memory usage.
        for window in self._windows:
            if window.local_counts is None:
                continue
            cur_len = int(window.local_counts.shape[0])
            if cur_len >= max_local_len:
                continue
            padded = np.ones((max_local_len,), dtype=np.float32)
            padded[:cur_len] = window.local_counts
            window.local_counts = padded

    def _present_conductor_ids(self, window: _WindowData) -> List[int]:
        if window.conductor_coords:
            return sorted(cid for cid in window.conductor_coords.keys() if cid > 0)

        present: set[int] = set()
        for id_map in window.id_maps:
            ids = np.unique(id_map)
            for cid in ids:
                cid_int = int(cid)
                if cid_int > 0:
                    present.add(cid_int)
        return sorted(present)

    def _build_grouped_coupling_cases(self) -> List[_GroupedCouplingCase]:
        cases: List[_GroupedCouplingCase] = []
        for window_idx, window in enumerate(self._windows):
            present_ids = self._present_conductor_ids(window)
            if len(present_ids) < 2:
                continue

            pair_values: Dict[Tuple[int, int], List[float]] = defaultdict(list)
            for sample in self._window_samples[window_idx]:
                if len(sample.positive_ids) != 1 or len(sample.negative_ids) != 1:
                    continue
                a = int(sample.positive_ids[0])
                b = int(sample.negative_ids[0])
                pair = tuple(sorted((a, b)))
                pair_values[pair].append(float(sample.target_value))

            pair_targets = {pair: float(np.mean(vals)) for pair, vals in pair_values.items() if vals}

            for master_id in present_ids:
                slave_ids = [cid for cid in present_ids if cid != master_id]
                if not slave_ids:
                    continue
                targets = np.zeros((len(slave_ids),), dtype=np.float32)
                valid = np.zeros((len(slave_ids),), dtype=np.float32)
                for i, slave_id in enumerate(slave_ids):
                    pair = tuple(sorted((master_id, slave_id)))
                    cap = pair_targets.get(pair)
                    if cap is None:
                        continue
                    targets[i] = cap
                    valid[i] = 1.0

                cases.append(
                    _GroupedCouplingCase(
                        window_index=window_idx,
                        master_id=master_id,
                        slave_ids=tuple(slave_ids),
                        targets=targets,
                        valid=valid,
                    )
                )

        return cases

    def _solver_priority(self) -> List[str]:
        if self.solver_preference == "auto":
            return ["rwcap", "raphael"]
        if self.solver_preference == "rwcap":
            return ["rwcap", "raphael"]
        return ["raphael", "rwcap"]

    
    def _find_spef_in_directory(self, window_id: str, directory: Path) -> Path:
        candidate = directory / f"{window_id}.spef"
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"No SPEF file named {window_id}.spef found in {directory}")

    def _label_directories(self) -> List[Tuple[str, Path]]:
        return [("rwcap", LABELS_RWCAP_DIR), ("raphael", LABELS_RAPHAEL_DIR)]

    def _find_spef_for_window(self, window_id: str) -> Path:
        if self.spef_dir is not None:
            return self._find_spef_in_directory(window_id, self.spef_dir)

        # SPEF manifest resolution removed - use direct directory scanning

        for solver, directory in self._label_directories():
            if not directory.exists():
                continue
            candidate = directory / f"{window_id}.spef"
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            f"No SPEF file found for window {window_id}. Checked manifests and directories {[str(d[1]) for d in self._label_directories()]}"
        )

    def _load_capacitances(
        self, spef_path: Path
    ) -> Tuple[Dict[str, float], Dict[Tuple[str, str], float]]:
        pair_caps: Dict[Tuple[str, str], float] = {}
        if self.goal == "self":
            total_caps = load_dnet_totals(str(spef_path))
            self_caps: Dict[str, float] = {
                str(name): float(value) for name, value in total_caps.items()
            }
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
        window: _WindowData,
        self_caps: Dict[str, float],
        pair_caps: Dict[Tuple[str, str], float],
        spef_path: str,
    ) -> List[_SampleMeta]:
        samples: List[_SampleMeta] = []

        if self.goal == "self":
            seen_conductor_ids: set[int] = set()
            for spef_name, cap in self_caps.items():
                actual = str(spef_name)
                conductor_id = window.conductor_ids.get(actual)
                if conductor_id is None:
                    continue
                if conductor_id in seen_conductor_ids:
                    continue
                seen_conductor_ids.add(conductor_id)
                label = f"{window.name}:{actual}"

                cap_value = float(cap) * 1e15

                samples.append(
                    _SampleMeta(
                        window_index=window_index,
                        window_id=window_id,
                        positive_ids=(conductor_id,),
                        negative_ids=(),
                        target_value=cap_value,
                        label=label,
                        spef_source=spef_path,
                    )
                )
        else:  # coupling
            centroids = self._compute_conductor_centroids(window)
            seen_pairs: set[tuple[int, int]] = set()
            for (name_a, name_b), value in pair_caps.items():
                actual_a = str(name_a)
                actual_b = str(name_b)
                id_a = window.conductor_ids.get(actual_a)
                id_b = window.conductor_ids.get(actual_b)
                if id_a is None or id_b is None:
                    continue

                if value <= 1e-20:
                    continue

                pair_ids = tuple(sorted((id_a, id_b)))
                if pair_ids in seen_pairs:
                    continue
                seen_pairs.add(pair_ids)
                centroid_a = centroids.get(id_a)
                centroid_b = centroids.get(id_b)
                dist_a = self._coordinate_distance_sq(centroid_a)
                dist_b = self._coordinate_distance_sq(centroid_b)

                if dist_a <= dist_b:
                    master_id, master_name, slave_id, slave_name = id_a, actual_a, id_b, actual_b
                else:
                    master_id, master_name, slave_id, slave_name = id_b, actual_b, id_a, actual_a

                label = f"{window.name}:{master_name}|{slave_name}"
                cap_value = float(value) * 1e15

                samples.append(
                    _SampleMeta(
                        window_index=window_index,
                        window_id=window_id,
                        positive_ids=(master_id,),
                        negative_ids=(slave_id,),
                        target_value=cap_value,
                        label=label,
                        spef_source=spef_path,
                    )
                )

        return samples

    def _apply_highlight(
        self,
        features: np.ndarray,
        window: _WindowData,
        conductor_id: int,
        *,
        positive: bool,
    ) -> None:
        coords = window.conductor_coords.get(int(conductor_id))
        if coords:
            for global_idx, ys, xs in coords:
                if positive:
                    features[global_idx, ys, xs] = features[global_idx, ys, xs] + 1.0
                else:
                    features[global_idx, ys, xs] = -features[global_idx, ys, xs]
            return

        for local_idx, (layer_name, id_map) in enumerate(zip(window.layer_names, window.id_maps)):
            mask = id_map == conductor_id
            if not np.any(mask):
                continue

            global_idx = self._layer_index.get(layer_name)
            if global_idx is None:
                continue
            h, w = id_map.shape
            if h != self._max_height or w != self._max_width:
                padded_mask = np.zeros((self._max_height, self._max_width), dtype=bool)
                padded_mask[:h, :w] = mask
                mask = padded_mask

            layer_values = features[global_idx]
            if positive:
                layer_values[mask] = layer_values[mask] + 1.0
            else:
                layer_values[mask] = -layer_values[mask]

    def _compute_conductor_centroids(self, window: _WindowData) -> Dict[int, Tuple[float, float, float]]:
        """Compute per-conductor centroid in (layer, y, x) coordinates."""
        accum: Dict[int, np.ndarray] = defaultdict(lambda: np.zeros(3, dtype=np.float64))
        counts: Dict[int, int] = defaultdict(int)

        for layer_idx, id_map in enumerate(window.id_maps):
            ys, xs = np.nonzero(id_map)
            if not len(ys):
                continue
            ids = id_map[ys, xs]
            layer_coords = np.full(len(ids), layer_idx, dtype=np.float64)
            coords = np.stack(
                (layer_coords, ys.astype(np.float64), xs.astype(np.float64)),
                axis=1,
            )

            for idx, cid in enumerate(ids):
                accum[cid] += coords[idx]
                counts[cid] += 1

        centroids: Dict[int, Tuple[float, float, float]] = {}
        for cid, total in accum.items():
            count = counts[cid]
            if count > 0:
                centroids[cid] = tuple(total / count)
        return centroids

    @staticmethod
    def _coordinate_distance_sq(coord: Optional[Tuple[float, float, float]]) -> float:
        if coord is None:
            return float("inf")
        z, y, x = coord
        return float(z * z + y * y + x * x)

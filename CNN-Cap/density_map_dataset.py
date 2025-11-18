#!/usr/bin/env python3
"""
CNN-Cap window dataset loader.

This loader ingests the per-window density map NPZ produced by cap3d_to_cnncap.py
and pairs it with capacitance targets parsed from corresponding SPEF reports.
It expands each window into many training samples:
  * self-capacitance: one sample per conductor
  * coupling-capacitance: one sample per unordered conductor pair

Each sample uses the 3D density tensor for the window and boosts/suppresses the
densities of the conductors of interest so the network can focus on them.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset

# Ensure project packages are importable when running from CNN-Cap/
from spef_tools.spef_to_simple import parse_spef_components
from spef_tools.python_parser import load_dnet_totals
from common.datasets import (
    DATASET_ROOT,
    DENSITY_MAPS_DIR,
    LABELS_RAPHAEL_DIR,
    LABELS_RWCAP_DIR,
    load_manifest,
    WindowManifest,
)


_SPECIAL_CHARS = re.compile(r"[\/\\\[\]\{\}\$]")


def _sanitize_net_name(name: str) -> str:
    """Normalize net names to ease matching between NPZ metadata and SPEF."""
    return _SPECIAL_CHARS.sub("", name).lower()


@dataclass
class _WindowData:
    name: str
    layer_names: List[str]
    densities: np.ndarray  # shape (L, H, W), float32
    id_maps: List[np.ndarray]  # length L, int32
    conductor_ids: Dict[str, int]  # actual name -> id
    sanitized_to_actual: Dict[str, str]


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
            # Discover all windows without SPEF validation (for backward compatibility)
            all_npes = sorted(p.stem for p in window_dir.glob("*.npz"))
            if spef_dir:
                # Filter out windows without SPEF files for better user experience
                valid_windows = []
                for window_id in all_npes:
                    spef_path = WindowCapDataset._find_spef_in_directory_static(window_id, spef_dir)
                    if spef_path and spef_path.exists():
                        valid_windows.append(window_id)
                print(f"Found {len(valid_windows)} windows with SPEF files out of {len(all_npes)} NPZ files")
                return valid_windows
            return all_npes

        # Discover with SPEF validation to ensure we get the requested number of valid windows
        valid_windows = []
        total_checked = 0
        print(f"Discovering windows with SPEF validation (target: {max_windows})...")

        for npz_path in window_dir.glob("*.npz"):
            window_id = npz_path.stem
            total_checked += 1

            # Check if SPEF file exists
            if spef_dir:
                spef_path = WindowCapDataset._find_spef_in_directory_static(window_id, spef_dir)
                if not spef_path or not spef_path.exists():
                    continue  # Skip this window, look for next one

            valid_windows.append(window_id)
            print(f"  Found valid window {len(valid_windows)}/{max_windows}: {window_id}")

            if len(valid_windows) >= max_windows:
                break

        print(f"Discovery complete: found {len(valid_windows)} valid windows after checking {total_checked} NPZ files")
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

        self._required_layers_override = list(required_layers) if required_layers else None

        if window_ids is None:
            window_ids = sorted(p.stem for p in self.window_dir.glob("*.npz"))

        if not window_ids:
            raise ValueError("No window IDs provided or discovered in window_dir")

        print("Loading all available windows without PDK filtering")

        self._windows: List[_WindowData] = []
        self._window_samples: List[List[_SampleMeta]] = []  # Per-window sample arrays
        self._window_ids: List[str] = []
        self._window_spef_paths: Dict[str, Path] = {}
        self._layer_catalog: List[str] = []
        self._layer_has_data: Dict[str, bool] = {}
        self._max_height = 0
        self._max_width = 0

        for idx, win_id in enumerate(window_ids):
            npz_path = self.window_dir / f"{win_id}.npz"
            if not npz_path.exists():
                raise FileNotFoundError(f"Missing NPZ for window {win_id}: {npz_path}")

            window_data = self._load_window(npz_path)
            try:
                spef_path = self._find_spef_for_window(win_id)
            except FileNotFoundError as exc:
                print(f"Warning: {exc} - skipping window {win_id}")
                continue
            self_caps, coupling_map = self._load_capacitances(spef_path)
            window_samples = self._generate_samples(idx, win_id, window_data, self_caps, coupling_map, str(spef_path))

            if not window_samples:
                print(f"Warning: No samples generated for window {win_id} (goal={self.goal}), skipping...")
                continue

            for local_idx, layer_name in enumerate(window_data.layer_names):
                if layer_name not in self._layer_catalog:
                    self._layer_catalog.append(layer_name)
                if layer_name not in self._layer_has_data:
                    self._layer_has_data[layer_name] = False
                layer_density = window_data.densities[local_idx]
                if np.any(layer_density):
                    self._layer_has_data[layer_name] = True

            self._max_height = max(self._max_height, window_data.densities.shape[1])
            self._max_width = max(self._max_width, window_data.densities.shape[2])

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

            pruned_layers = [name for name in self._layer_catalog if name not in self._active_layers]
            if pruned_layers:
                print(
                    f"Pruning {len(pruned_layers)} inactive layer(s) with zero density across all windows: "
                    f"{', '.join(pruned_layers)}"
                )

        self._layer_index: Dict[str, int] = {name: idx for idx, name in enumerate(self._active_layers)}
        self._num_layers = len(self._active_layers)
        self._tensor_shape = (self._num_layers, self._max_height, self._max_width)

        # Report comprehensive statistics
        self._report_dataset_statistics()

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
                # Apply CNN-Cap highlighting using the exact same logic as training
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
        """Create dataset subset containing only specified windows."""
        # Validate window IDs
        invalid_windows = [wid for wid in window_ids if wid not in self._window_ids]
        if invalid_windows:
            raise ValueError(f"Invalid window IDs: {invalid_windows}")

        # Create subset dataset with same configuration
        subset = WindowCapDataset(
            window_dir=self.window_dir,
            spef_dir=self.spef_dir,
            window_ids=window_ids,
            goal=self.goal,
            highlight_scale=self.highlight_scale,
            dtype=self.dtype,
            solver_preference=self.solver_preference,
            required_layers=self._active_layers,
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
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_window(self, npz_path: Path) -> _WindowData:
        data = np.load(npz_path, allow_pickle=True)
        layer_names = [str(layer) for layer in data["layers"]]
        densities: List[np.ndarray] = []
        id_maps: List[np.ndarray] = []
        for layer in layer_names:
            densities.append(data[f"{layer}_img"].astype(np.float32, copy=True))
            id_maps.append(data[f"{layer}_idx"].astype(np.int32, copy=True))

        density_stack = np.stack(densities, axis=0).astype(np.float32, copy=False)

        conductor_ids: Dict[str, int] = {}
        sanitized_to_actual: Dict[str, str] = {}
        if "conductor_names" in data and "conductor_ids" in data:
            for name, cid in zip(data["conductor_names"], data["conductor_ids"]):
                actual = str(name)
                conductor_ids[actual] = int(cid)
                for variant in _name_variants(actual):
                    sanitized_to_actual.setdefault(variant, actual)

        window_data = _WindowData(
            name=npz_path.stem,
            layer_names=layer_names,
            densities=density_stack,
            id_maps=id_maps,
            conductor_ids=conductor_ids,
            sanitized_to_actual=sanitized_to_actual,
        )
        return window_data

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
        _, adjacency, _ = parse_spef_components(str(spef_path))
        total_caps = load_dnet_totals(str(spef_path))

        self_caps: Dict[str, float] = {
            _sanitize_net_name(name): value for name, value in total_caps.items()
        }

        pair_caps: Dict[Tuple[str, str], float] = {}
        for name_a, neighbors in adjacency.items():
            norm_a = _sanitize_net_name(name_a)
            for name_b, value in neighbors.items():
                norm_b = _sanitize_net_name(name_b)
                if norm_a == norm_b:
                    continue
                pair = tuple(sorted((norm_a, norm_b)))
                # Average duplicates if they appear from both directions
                if pair in pair_caps:
                    pair_caps[pair] = 0.5 * (pair_caps[pair] + value)
                else:
                    pair_caps[pair] = value

        return self_caps, pair_caps

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
        highlight_desc = "master+=1, slave*=-1"

        
        if self.goal == "self":
            for sanitized, actual in window.sanitized_to_actual.items():
                cap = self_caps.get(sanitized)
                if cap is None:
                    continue
                conductor_id = window.conductor_ids[actual]
                label = f"{window.name}:{actual}"

                # Convert to femtoFarads
                cap_value = float(cap) * 1e15

                # Debug: Log zero capacitance values with window ID and show raw cap value
                if cap_value == 0.0:
                    print(f"ZERO TARGET: Window: {window_id}, Conductor: {actual}, Original: {cap:.2e}F, Scaled: {cap_value:.6f}fF")
                elif cap_value < 0:
                    print(f"NEGATIVE TARGET: Window: {window_id}, Conductor: {actual}, Original: {cap:.2e}F, Scaled: {cap_value:.6f}fF")

                # Debug: Show non-zero values for key windows to verify parsing
                if window_id == "W35" and actual == "Net.1":
                    print(f"PARSING DEBUG: Window {window_id}, Conductor {actual}")
                    print(f"  Raw cap from parser: {cap:.2e}F")
                    print(f"  Scaled cap_value: {cap_value:.6f}fF")

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
            for (san_a, san_b), value in pair_caps.items():
                actual_a = window.sanitized_to_actual.get(san_a)
                actual_b = window.sanitized_to_actual.get(san_b)
                if actual_a is None or actual_b is None:
                    continue

                # MANDATORY SPEF VALIDATION: Check if coupling exists and is positive
                if value <= 1e-20:  # Skip very small/negative couplings
                    continue

                id_a = window.conductor_ids[actual_a]
                id_b = window.conductor_ids[actual_b]
                centroid_a = centroids.get(id_a)
                centroid_b = centroids.get(id_b)
                dist_a = self._coordinate_distance_sq(centroid_a)
                dist_b = self._coordinate_distance_sq(centroid_b)

                if dist_a <= dist_b:
                    master_id, master_name, slave_id, slave_name = id_a, actual_a, id_b, actual_b
                else:
                    master_id, master_name, slave_id, slave_name = id_b, actual_b, id_a, actual_a

                label = f"{window.name}:{master_name}|{slave_name}"

                # Convert to femtoFarads
                cap_value = float(value) * 1e15

                # Debug: Log zero coupling capacitance values with window ID
                if cap_value == 0.0:
                    print(
                        f"ZERO COUPLING: Window: {window_id}, Conductors: {actual_a} & {actual_b}, "
                        f"Original: {value:.2e}F, Scaled: {cap_value:.6f}fF"
                    )
                elif cap_value < 0:
                    print(
                        f"NEGATIVE COUPLING: Window: {window_id}, Conductors: {actual_a} & {actual_b}, "
                        f"Original: {value:.2e}F, Scaled: {cap_value:.6f}fF"
                    )

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

        if not samples:
            print(f"WARNING: No capacitance entries matched for window {window.name}")
        else:
            n_self = len([s for s in samples if s.sample_type == "self"])
            n_coupling = len([s for s in samples if s.sample_type == "coupling"])
            print(
                f"Window {window.name}: {n_self} self, {n_coupling} coupling, {len(samples)} total samples "
                f"(goal={self.goal}, highlight={highlight_desc})"
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

    def _report_dataset_statistics(self):
        """Report comprehensive dataset statistics."""
        # Window statistics
        total_windows = len(self._windows)
        windows_with_spef = len(self._window_spef_paths)

        # Sample statistics
        total_self_samples = 0
        total_coupling_samples = 0
        process_node_counts = {}

        for window_samples in self._window_samples:
            for sample in window_samples:
                if sample.sample_type == "self":
                    total_self_samples += 1
                else:
                    total_coupling_samples += 1

                
        total_samples = total_self_samples + total_coupling_samples

        # SPEF coverage statistics
        spef_coverage = windows_with_spef / total_windows * 100 if total_windows > 0 else 0

        print(f"\n=== CNN-Cap Dataset Statistics ===")
        print(f"Total windows: {total_windows}")
        print(f"Windows with SPEF files: {windows_with_spef} ({spef_coverage:.1f}%)")
        print(f"Self-capacitance samples: {total_self_samples}")
        print(f"Coupling-capacitance samples: {total_coupling_samples}")
        print(f"Total samples: {total_samples}")
        print(f"Goal: {self.goal}")

        # Per-window breakdown
        print(f"\n=== Per-Window Sample Distribution ===")
        for window_id, window_samples in zip(self._window_ids, self._window_samples):
            n_self = len([s for s in window_samples if s.sample_type == "self"])
            n_coupling = len([s for s in window_samples if s.sample_type == "coupling"])
            print(f"{window_id}: {n_self} self, {n_coupling} coupling, {len(window_samples)} total")

        print(f"\nDataset tensor shape: {self.tensor_shape}")
        print(f"Number of active layers: {self.num_layers}")
        print(f"Active layers: {', '.join(self._active_layers)}")


def _name_variants(name: str) -> List[str]:
    base = _sanitize_net_name(name)
    variants = {base}
    if '.' in base:
        variants.add(base.replace('.', ''))
        variants.add(base.split('.', 1)[0])
    variants.add(base.replace(':', ''))
    variants.add(base.replace('.', '').replace(':', ''))
    return [v for v in variants if v]

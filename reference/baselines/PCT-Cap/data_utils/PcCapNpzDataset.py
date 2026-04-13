# ***************************************************************************************
# Copyright (c) 2023-2025 Peng Cheng Laboratory
# Copyright (c) 2023-2025 Institute of Computing Technology, Chinese Academy of Sciences
# Copyright (c) 2023-2025 Beijing Institute of Open Source Chip
#
# iEDA is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
# http://license.coscl.org.cn/MulanPSL2
#
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
#
# See the Mulan PSL v2 for more details.
# ***************************************************************************************

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from tqdm import tqdm

try:
    from torch.utils.data import Dataset  # type: ignore
except ImportError:  # pragma: no cover - optional torch dependency
    class Dataset:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            pass

import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from .sampler import PcCapSampler, RandomSampler
from .transform import PcCapTransform, NormalizeTransform
from capbench.formats.spef.python_parser import load_coupling_pairs, load_dnet_totals

try:  # Optional dependency; only required when iterating the dataset.
    import torch  # type: ignore
except ImportError:  # pragma: no cover - lazy torch requirement
    torch = None  # type: ignore[assignment]

_SPECIAL_CHARS = re.compile(r"[\/\\\[\]\{\}\$\s]")


def _sanitize_net_name(name: str) -> str:
    """Normalize net names to ease matching between NPZ metadata and SPEF."""
    return _SPECIAL_CHARS.sub("", name).lower()


@dataclass
class _WindowPointCloud:
    window_id: str
    display_name: str
    npz_path: Path
    base_features: np.ndarray  # (N, 7) -> xyz, normals, dielectric
    net_ids: np.ndarray        # (N,)
    id_to_name: Dict[int, str]
    name_to_id: Dict[str, int]
    sanitized_to_ids: Dict[str, List[int]]


@dataclass
class _SampleSpec:
    window_index: int
    window_id: str
    master_id: int
    target_id: Optional[int]
    label_value: float
    label_type: str  # 'self' or 'coupling'
    spef_source: str  # MANDATORY: SPEF file reference
    process_node: Optional[str] = None

    @property
    def sample_type(self) -> str:
        return self.label_type


class PcCapNpzDataset(Dataset):
    """
    Point cloud dataset for PCT-Cap that pairs NPZ point clouds with SPEF labels.

    Each NPZ window is expanded into multiple samples:
      * Self-capacitance (Cii): master conductor i vs environment
      * Coupling capacitance (Cik): master conductor i vs target conductor k

    The `goal` parameter selects which capacitance type to expose.
    """

    def __init__(
        self,
        point_cloud_dir: Path | str,
        spef_dir: Path | str,
        *,
        goal: str = "self",
        npoints: int = 1024,
        sampler: Optional[PcCapSampler] = None,
        transform: Optional[PcCapTransform] = None,
        window_ids: Optional[Sequence[str]] = None,
        spef_suffix: str = ".spef",
        return_metadata: bool = False,
        process_node: Optional[str] = None,
    ) -> None:
        super().__init__()

        self.point_cloud_dir = Path(point_cloud_dir).resolve()
        self.spef_dir = Path(spef_dir).resolve()
        self.goal = goal.lower()
        if self.goal not in {"self", "coupling"}:
            raise ValueError("goal must be 'self' or 'coupling'")
        self.npoints = int(npoints)
        self.spef_suffix = spef_suffix
        self.return_metadata = return_metadata
        self.process_node = process_node

        self.sampler: PcCapSampler = sampler or RandomSampler()
        self.transform: PcCapTransform = transform or NormalizeTransform()
        # The legacy sampler/transform expect an annotation DataFrame; set to None safely.
        self.sampler.set_ann(None)
        self.transform.set_ann(None)

        if window_ids is None:
            window_ids = sorted(p.stem for p in self.point_cloud_dir.glob("*.npz"))
        if not window_ids:
            raise ValueError(f"No NPZ point clouds found in {self.point_cloud_dir}")

        # Filter by process node if specified
        if self.process_node is not None:
            window_ids = self._filter_by_process_node(window_ids)

        self._windows: List[_WindowPointCloud] = []
        self._window_samples_self: List[List[_SampleSpec]] = []  # Per-window sample arrays
        self._window_samples_coupling: List[List[_SampleSpec]] = []  # Per-window sample arrays
        self._window_ids: List[str] = []
        self._window_spef_paths: Dict[str, Path] = {}
        self.window_stats: Dict[str, Dict[str, int]] = {}

        for idx, win_id in tqdm(
            enumerate(window_ids),
            total=len(window_ids),
            desc="Loading point clouds",
            unit="win",
        ):
            npz_path = self.point_cloud_dir / f"{win_id}.npz"
            if not npz_path.exists():
                raise FileNotFoundError(f"Point cloud missing for window {win_id}: {npz_path}")

            window = self._load_window(npz_path)
            try:
                spef_path = self._find_spef_for_window(win_id)
            except FileNotFoundError as exc:
                print(f"Warning: {exc} - skipping window {win_id}")
                continue
            total_map = load_dnet_totals(str(spef_path))
            pair_caps = load_coupling_pairs(str(spef_path))
            samples_self, samples_coupling = self._build_samples(
                idx,
                win_id,
                window,
                total_map,
                pair_caps,
                str(spef_path)
            )

            if not samples_self and not samples_coupling:
                print(f"Warning: No samples generated for window {win_id} (goal={self.goal}), skipping...")
                continue

            self._windows.append(window)
            self._window_samples_self.append(samples_self)
            self._window_samples_coupling.append(samples_coupling)
            self._window_ids.append(win_id)
            self._window_spef_paths[win_id] = spef_path

            stats_key = window.window_id
            self.window_stats[stats_key] = {
                "self": len(samples_self),
                "coupling": len(samples_coupling),
            }

        # Flatten samples based on goal
        self._samples_self: List[_SampleSpec] = []
        self._samples_coupling: List[_SampleSpec] = []
        for window_samples_self in self._window_samples_self:
            self._samples_self.extend(window_samples_self)
        for window_samples_coupling in self._window_samples_coupling:
            self._samples_coupling.extend(window_samples_coupling)

        self.sample_counts: Dict[str, int] = {
            "self": len(self._samples_self),
            "coupling": len(self._samples_coupling),
        }
        self._samples: List[_SampleSpec]
        if self.goal == "self":
            self._samples = self._samples_self
        else:
            self._samples = self._samples_coupling

        if not self._samples:
            raise RuntimeError(
                f"No samples generated for goal '{self.goal}'. "
                "Check that the SPEF files contain matching conductors."
            )

    # ------------------------------------------------------------------
    # Dataset API
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        """Total number of samples across all windows."""
        return len(self._samples)

    def __getitem__(self, index: int):
        sample = self._samples[index]
        window = self._windows[sample.window_index]

        flux = np.zeros_like(window.net_ids, dtype=np.float32)
        flux[window.net_ids == sample.master_id] = 1.0
        if sample.target_id is not None:
            flux[window.net_ids == sample.target_id] = -1.0

        features = np.concatenate([window.base_features, flux[:, np.newaxis]], axis=1)

        sampled = self.sampler(features, sample.window_index, self.npoints)
        if self.transform:
            sampled = self.transform(sampled, sample.window_index)

        if torch is None:
            raise RuntimeError(
                "PyTorch is required to materialize point cloud samples. "
                "Install torch to iterate over PcCapNpzDataset."
            )

        data_tensor = torch.from_numpy(sampled[:, :8].astype(np.float32, copy=False))
        label_tensor = torch.tensor([sample.label_value], dtype=torch.float32)

        if not self.return_metadata:
            return data_tensor, label_tensor

        metadata = {
            "window": window.display_name,
            "window_id": window.window_id,
            "master_id": sample.master_id,
            "master_name": window.id_to_name.get(sample.master_id, f"id_{sample.master_id}"),
            "target_id": sample.target_id if sample.target_id is not None else -1,
            "target_name": (
                window.id_to_name.get(sample.target_id, f"id_{sample.target_id}")
                if sample.target_id is not None
                else ""
            ),
            "label_type": sample.label_type,
            "label_value": sample.label_value,
            "sample_type": sample.sample_type,
            "spef_source": sample.spef_source,
            "process_node": sample.process_node,
        }
        return data_tensor, label_tensor, metadata

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_window_ids(self) -> List[str]:
        """Return list of all window IDs in the dataset."""
        return self._window_ids.copy()

    def create_window_subset(self, window_ids: List[str]) -> 'PcCapNpzDataset':
        """Create dataset subset containing only specified windows."""
        # Validate window IDs
        invalid_windows = [wid for wid in window_ids if wid not in self._window_ids]
        if invalid_windows:
            raise ValueError(f"Invalid window IDs: {invalid_windows}")

        # Create subset dataset with same configuration
        subset = PcCapNpzDataset(
            point_cloud_dir=self.point_cloud_dir,
            spef_dir=self.spef_dir,
            goal=self.goal,
            npoints=self.npoints,
            sampler=self.sampler,
            transform=self.transform,
            window_ids=window_ids,
            spef_suffix=self.spef_suffix,
            return_metadata=self.return_metadata,
            process_node=self.process_node
        )

        return subset

    def _get_item_window_level(self, window_idx: int, sample_idx: int, sample_type: str):
        """Get sample using window-level indexing (for WindowSubsetDataset)."""
        if sample_type == "self":
            sample = self._window_samples_self[window_idx][sample_idx]
        else:
            sample = self._window_samples_coupling[window_idx][sample_idx]

        window = self._windows[window_idx]

        flux = np.zeros_like(window.net_ids, dtype=np.float32)
        flux[window.net_ids == sample.master_id] = 1.0
        if sample.target_id is not None:
            flux[window.net_ids == sample.target_id] = -1.0

        features = np.concatenate([window.base_features, flux[:, np.newaxis]], axis=1)

        sampled = self.sampler(features, sample.window_index, self.npoints)
        if self.transform:
            sampled = self.transform(sampled, sample.window_index)

        if torch is None:
            raise RuntimeError(
                "PyTorch is required to materialize point cloud samples. "
                "Install torch to iterate over PcCapNpzDataset."
            )

        data_tensor = torch.from_numpy(sampled[:, :8].astype(np.float32, copy=False))
        label_tensor = torch.tensor([sample.label_value], dtype=torch.float32)

        if not self.return_metadata:
            return data_tensor, label_tensor

        metadata = {
            "window": window.display_name,
            "window_id": window.window_id,
            "master_id": sample.master_id,
            "master_name": window.id_to_name.get(sample.master_id, f"id_{sample.master_id}"),
            "target_id": sample.target_id if sample.target_id is not None else -1,
            "target_name": (
                window.id_to_name.get(sample.target_id, f"id_{sample.target_id}")
                if sample.target_id is not None
                else ""
            ),
            "label_type": sample.label_type,
            "label_value": sample.label_value,
            "sample_type": sample.sample_type,
            "spef_source": sample.spef_source,
            "process_node": sample.process_node,
        }
        return data_tensor, label_tensor, metadata

    def _filter_by_process_node(self, window_ids: List[str]) -> List[str]:
        """Keep all windows (metadata lacks reliable process-node annotations)."""
        return list(window_ids)

    def _extract_process_node_from_window(self, npz_path: Path) -> str:
        """Extract process node from window file."""
        # Try to get process node from NPZ metadata first
        try:
            data = np.load(npz_path, allow_pickle=True)
            if 'process_node' in data:
                return str(data['process_node'])
            if 'metadata' in data:
                metadata = data['metadata'].item()
                if isinstance(metadata, dict) and 'process_node' in metadata:
                    return str(metadata['process_node'])
        except Exception as e:
            print(f"Warning: Could not extract process node from {npz_path}: {e}")

        # Return None to skip process node filtering and process all windows
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_window(self, npz_path: Path) -> _WindowPointCloud:
        data = np.load(npz_path, allow_pickle=True)
        points = data["points"].astype(np.float32, copy=False)

        base_features = points[:, :7].astype(np.float32, copy=True)
        net_ids = points[:, 8].astype(np.int32, copy=True)

        conductor_ids = data.get("conductor_ids", np.unique(net_ids)).astype(np.int32)
        metadata_str = str(data.get("conductor_metadata_str", ""))

        id_to_name: Dict[int, str] = {}
        name_to_id: Dict[str, int] = {}
        sanitized_to_ids: Dict[str, List[int]] = {}

        entries = [entry for entry in metadata_str.split(";") if entry]
        for cid, entry in zip(conductor_ids, entries):
            name, *_layer = entry.split("|", maxsplit=1)
            self._register_conductor(cid, name, id_to_name, name_to_id, sanitized_to_ids)

        # Fallback: use point_net_names if metadata incomplete
        if len(id_to_name) < len(conductor_ids):
            point_names = data.get("point_net_names")
            if point_names is not None:
                point_names = np.asarray(point_names)
                for cid in conductor_ids:
                    if cid in id_to_name:
                        continue
                    matches = np.where(net_ids == cid)[0]
                    if matches.size == 0:
                        continue
                    name = str(point_names[matches[0]])
                    self._register_conductor(cid, name, id_to_name, name_to_id, sanitized_to_ids)

        window_name = str(data.get("window_name_str", npz_path.stem)) or npz_path.stem

        return _WindowPointCloud(
            window_id=npz_path.stem,
            display_name=window_name,
            npz_path=npz_path,
            base_features=base_features,
            net_ids=net_ids,
            id_to_name=id_to_name,
            name_to_id=name_to_id,
            sanitized_to_ids=sanitized_to_ids,
        )

    def _register_conductor(
        self,
        cid: int,
        name: str,
        id_to_name: Dict[int, str],
        name_to_id: Dict[str, int],
        sanitized_to_ids: Dict[str, List[int]],
    ) -> None:
        actual = name.strip()
        if not actual:
            actual = f"conductor_{cid}"
        id_to_name[cid] = actual
        lower = actual.lower()
        name_to_id[lower] = cid

        sanitized = _sanitize_net_name(actual)
        sanitized_to_ids.setdefault(sanitized, []).append(cid)

    def _find_spef_for_window(self, window_id: str) -> Path:
        candidates: List[Path] = []

        primary = self.point_cloud_dir / f"{window_id}{self.spef_suffix}"
        if primary.exists():
            candidates.append(primary)

        exact = self.spef_dir / f"{window_id}{self.spef_suffix}"
        if exact.exists():
            candidates.append(exact)

        if not candidates:
            raise FileNotFoundError(
                f"No SPEF file matching window '{window_id}' in {self.spef_dir} "
                f"or {self.point_cloud_dir}"
            )
        return candidates[0]

    def _build_samples(
        self,
        window_index: int,
        window_id: str,
        window: _WindowPointCloud,
        total_map: Dict[str, float],
        pair_caps_by_name: Dict[Tuple[str, str], float],
        spef_path: str,
    ) -> Tuple[List[_SampleSpec], List[_SampleSpec]]:
        samples_self: List[_SampleSpec] = []
        samples_coupling: List[_SampleSpec] = []
        centroids = self._compute_conductor_centroids(window)

        # Get process node for this window
        process_node = self._extract_process_node_from_window(self.point_cloud_dir / f"{window_id}.npz")

        # Self-capacitance samples
        for net_name, value in total_map.items():
            master_id = self._lookup_conductor(window, net_name)
            if master_id is None:
                continue
            samples_self.append(
                _SampleSpec(
                    window_index=window_index,
                    window_id=window_id,
                    master_id=master_id,
                    target_id=None,
                    label_value=float(value) * 1e15,
                    label_type="self",
                    spef_source=spef_path,
                    process_node=process_node,
                )
            )

        # Coupling-capacitance samples with mandatory SPEF validation
        pair_caps: Dict[Tuple[int, int], float] = {}
        for (master_name, neighbor_name), value in pair_caps_by_name.items():
            if value <= 1e-20:  # Skip very small/negative couplings
                continue

            master_id = self._lookup_conductor(window, master_name)
            target_id = self._lookup_conductor(window, neighbor_name)
            if master_id is None or target_id is None:
                continue

            pair = tuple(sorted((master_id, target_id)))
            pair_caps[pair] = float(value)

        for (id_a, id_b), value in pair_caps.items():
            centroid_a = centroids.get(id_a)
            centroid_b = centroids.get(id_b)
            dist_a = self._coordinate_distance_sq(centroid_a)
            dist_b = self._coordinate_distance_sq(centroid_b)

            if dist_a <= dist_b:
                master_id, target_id = id_a, id_b
            else:
                master_id, target_id = id_b, id_a

            samples_coupling.append(
                _SampleSpec(
                    window_index=window_index,
                    window_id=window_id,
                    master_id=master_id,
                    target_id=target_id,
                    label_value=float(value) * 1e15,
                    label_type="coupling",
                    spef_source=spef_path,
                    process_node=process_node,
                )
            )

        return samples_self, samples_coupling

    def _lookup_conductor(self, window: _WindowPointCloud, net_name: str) -> Optional[int]:
        candidate = net_name.strip()
        if not candidate:
            return None

        lower = candidate.lower()
        if lower in window.name_to_id:
            return window.name_to_id[lower]

        sanitized = _sanitize_net_name(candidate)
        candidates = window.sanitized_to_ids.get(sanitized)
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        # Attempt to disambiguate by exact lower-case match.
        for cid in candidates:
            actual = window.id_to_name.get(cid, "")
            if actual.lower() == lower:
                return cid
        return candidates[0]

    def _compute_conductor_centroids(self, window: _WindowPointCloud) -> Dict[int, Tuple[float, float, float]]:
        """Compute average XYZ for each conductor based on window point cloud."""
        if window.base_features.size == 0:
            return {}

        coords = window.base_features[:, :3].astype(np.float64, copy=False)
        net_ids = window.net_ids.astype(np.int64, copy=False)
        unique_ids, inverse = np.unique(net_ids, return_inverse=True)

        sums = np.zeros((len(unique_ids), 3), dtype=np.float64)
        counts = np.zeros(len(unique_ids), dtype=np.int64)

        np.add.at(sums, inverse, coords)
        np.add.at(counts, inverse, 1)

        centroids: Dict[int, Tuple[float, float, float]] = {}
        for idx, cid in enumerate(unique_ids):
            count = counts[idx]
            if count <= 0:
                continue
            centroids[int(cid)] = tuple((sums[idx] / count).tolist())
        return centroids

    @staticmethod
    def _coordinate_distance_sq(coord: Optional[Tuple[float, float, float]]) -> float:
        if coord is None:
            return float("inf")
        x, y, z = coord
        return float(x * x + y * y + z * z)

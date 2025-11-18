"""
Data Loader for GNN-Cap

Loads graph data (.pt files) and corresponding labels for training/validation/testing.
Supports .pt label tensors or capacitance totals parsed from SPEF using the
pure-Python parser in :mod:`spef.python_parser`.
Implements an 80/20 train/validation split (consistent with other models in the codebase).
"""

import torch
from torch.utils.data import Dataset, DataLoader, random_split
from torch_geometric.data import Data
from pathlib import Path
import json
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from collections import defaultdict
import numpy as np

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root.parent) not in sys.path:
    sys.path.insert(0, str(repo_root.parent))

from spef.python_parser import load_dnet_totals, load_coupling_pairs
from common.datasets import (
    DATASET_ROOT,
    LABELS_RAPHAEL_DIR,
    LABELS_RWCAP_DIR,
    load_manifest,
    WindowManifest,
)

_CANONICAL_TRANSLATION = str.maketrans("", "", "[]/\\{}$")


class CapacitanceDataset(Dataset):
    """
    Dataset for GNN-Cap capacitance prediction

    Loads pre-processed graph chunks (.pt files) with corresponding labels.
    Supports both total and coupling capacitance labels.
    """

    def __init__(
        self,
        data_dir: str,
        label_type: str = 'total',  # 'total' or 'coupling'
        load_labels: bool = True,
        transform=None,
        min_coupling_ratio: float = 0.01,  # Ignore coupling caps < 1% of total
        graph_files: Optional[Sequence[str]] = None,
        spef_dir: Optional[str] = None,
        spef_files: Optional[Sequence[str]] = None,
        spef_suffix: str = '.spef',
        solver_preference: str = 'auto',
    ):
        """
        Initialize dataset

        Args:
            data_dir: Directory containing .pt graph files
            label_type: Type of labels to load ('total' or 'coupling')
            load_labels: Whether to load labels (False for inference)
            transform: Optional transform to apply to data
            min_coupling_ratio: Minimum coupling capacitance ratio (filter small caps)
            graph_files: Optional explicit list of graph file paths (overrides data_dir scan)
            spef_dir: Optional directory containing SPEF files for labels
            spef_files: Optional explicit list of SPEF file paths (overrides spef_dir scan)
            spef_suffix: Filename suffix to filter SPEF files when scanning directories
            solver_preference: Preferred SPEF solver ('rwcap', 'raphael', or 'auto')
        """
        super(CapacitanceDataset, self).__init__()

        self.data_dir = Path(data_dir) if data_dir is not None else None
        self.label_type = label_type
        self.load_labels = load_labels
        self.transform = transform
        self.min_coupling_ratio = min_coupling_ratio

        # Gather graph files
        if graph_files:
            self.graph_files = sorted(Path(p).resolve() for p in graph_files)
        else:
            if self.data_dir is None:
                raise ValueError("Either data_dir or graph_files must be provided")
            self.graph_files = sorted(list(self.data_dir.glob("*.pt")))

        # Filter out files ending in '_labels.pt'
        self.graph_files = [f for f in self.graph_files if not f.name.endswith('_labels.pt')]

        if len(self.graph_files) == 0:
            source_desc = graph_files if graph_files else data_dir
            raise ValueError(f"No graph files (.pt) found in {source_desc}")

        print(f"Found {len(self.graph_files)} graph files for dataset")

        self.spef_suffix = spef_suffix
        self.solver_preference = solver_preference.lower()
        if self.solver_preference not in {'auto', 'rwcap', 'raphael'}:
            raise ValueError(f"Unsupported solver preference: {self.solver_preference}")

        self._spef_cache: Dict[Path, Tuple[Dict[str, float], Dict[str, float]]] = {}
        self._coupling_cache: Dict[Path, Dict[Tuple[str, str], float]] = {}
        self._graph_to_spef: Dict[Path, Optional[Path]] = {}
        self._graph_solver: Dict[Path, Optional[str]] = {}

        # Optional manual SPEF sources for legacy compatibility
        self.spef_files: List[Path] = []
        if spef_files:
            self.spef_files = sorted(Path(p).resolve() for p in spef_files)
        elif spef_dir:
            spef_dir_path = Path(spef_dir)
            if not spef_dir_path.exists():
                raise FileNotFoundError(f"SPEF directory not found: {spef_dir}")
            self.spef_files = sorted(spef_dir_path.glob(f"*{spef_suffix}"))
        else:
            # Default legacy fallback: look alongside graph files
            if self.data_dir is not None:
                self.spef_files = sorted(self.data_dir.glob(f"*{spef_suffix}"))

        # Discover dataset-local label directories (e.g., out_openrcx, labels_rwcap)
        self._extend_with_neighbor_label_dirs()

        # Include standardized dataset label directories
        for directory in (LABELS_RWCAP_DIR, LABELS_RAPHAEL_DIR):
            if directory.exists():
                self.spef_files.extend(directory.glob(f"*{spef_suffix}"))

        # Deduplicate and normalize
        self.spef_files = sorted({path.resolve() for path in self.spef_files})

        self._spef_key_cache: List[Tuple[Path, List[str]]] = [
            (path, self._spef_keys(path)) for path in self.spef_files
        ]

        matched = 0
        for graph_file in self.graph_files:
            spef_path, solver_used = self._resolve_label_path(graph_file)
            self._graph_to_spef[graph_file] = spef_path
            self._graph_solver[graph_file] = solver_used
            if spef_path is not None:
                matched += 1
        print(
            f"Resolved labels for {matched}/{len(self.graph_files)} graphs "
            f"(solver preference: {self.solver_preference})"
        )

        # Load metadata if available
        self.metadata = []
        for graph_file in self.graph_files:
            metadata_file = graph_file.parent / f"{graph_file.stem}_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    self.metadata.append(json.load(f))
            else:
                self.metadata.append({})

    def __len__(self) -> int:
        return len(self.graph_files)

    def __getitem__(self, idx: int) -> Tuple[Data, torch.Tensor]:
        """
        Load a single graph and its labels

        Returns:
            data: PyTorch Geometric Data object with graph structure
            labels: Labels tensor (node-level for total, edge-level for coupling)

        Raises:
            FileNotFoundError: If no SPEF file is found for the graph
            ValueError: If the graph cannot be loaded or is invalid
        """
        # Load graph
        graph_file = self.graph_files[idx]
        data = torch.load(graph_file, weights_only=False)

        # Add window ID from filename (remove .pt extension)
        data.window_id = graph_file.stem

        # Validate that the loaded data has the required attributes
        if not hasattr(data, 'x') or not hasattr(data, 'edge_index'):
            raise ValueError(f"Invalid graph file {graph_file.name} - missing required attributes")

        # Ensure node-to-net mapping metadata exists for attention pooling
        node_net_index = self._ensure_node_net_index(data)
        if node_net_index is not None:
            data.node_net_index = node_net_index
            net_names = getattr(data, 'net_names', [])
            if net_names:
                data.num_nets = len(net_names)
            else:
                valid = node_net_index[node_net_index >= 0]
                data.num_nets = int(valid.max().item()) + 1 if valid.numel() > 0 else 0

        # Filter out virtual edges for simplified training
        if hasattr(data, 'edge_is_virtual') and data.edge_is_virtual is not None:
            # Keep only regular (non-virtual) edges
            regular_edge_mask = ~data.edge_is_virtual
            data.edge_index = data.edge_index[:, regular_edge_mask]
            data.edge_attr = data.edge_attr[regular_edge_mask]
            # Remove virtual edge attribute
            delattr(data, 'edge_is_virtual')

            # Also filter edge labels if they exist
            if hasattr(data, 'edge_y') and data.edge_y is not None:
                data.edge_y = data.edge_y[regular_edge_mask]
            if hasattr(data, 'edge_label_mask') and data.edge_label_mask is not None:
                data.edge_label_mask = data.edge_label_mask[regular_edge_mask]

        # Load labels (required - will raise exception if not found)
        if not self.load_labels:
            raise ValueError("Labels must be loaded for training - set load_labels=True")

        labels = self._load_labels_for_graph(graph_file, data)
        if labels is None:
            raise FileNotFoundError(f"No SPEF labels found for graph {graph_file.name}")

        # Apply transform if provided
        if self.transform is not None:
            data = self.transform(data)

        # Add labels to data object for convenience
        if self.label_type == 'total':
            net_labels: Optional[torch.Tensor] = None
            node_labels: Optional[torch.Tensor] = None
            if isinstance(labels, dict):
                net_labels = labels.get('net')
                node_labels = labels.get('node')
            else:
                net_labels = labels

            if net_labels is None:
                raise ValueError(f"Missing net-level labels for {graph_file.name}")

            data.net_y = net_labels
            data.y = net_labels  # training will default to net predictions
            data.num_nets = int(net_labels.shape[0])
            if node_labels is not None:
                data.node_y = node_labels
            labels = net_labels
        else:
            data.edge_y = labels  # Edge labels

        return data, labels

    def get_metadata(self, idx: int) -> Dict:
        """Get metadata for a specific graph"""
        return self.metadata[idx]

    @staticmethod
    def _canonical_net_name(name: str) -> str:
        """Canonicalize net names for robust matching."""
        return name.translate(_CANONICAL_TRANSLATION).lower()

    @staticmethod
    def _graph_keys(graph_path: Path) -> List[str]:
        """Generate candidate identifiers that can be used to match graph to SPEF."""
        stem = graph_path.stem.lower()
        keys: List[str] = []

        def add(val: str) -> None:
            if val and val not in keys:
                keys.append(val)

        add(stem)

        for suffix in ('_graph', '_graphs', '_metadata', '_labels', '_label'):
            if stem.endswith(suffix):
                add(stem[:-len(suffix)])

        return keys

    def _solver_priority(self) -> List[str]:
        if self.solver_preference == 'auto':
            return ['rwcap', 'raphael']
        if self.solver_preference == 'rwcap':
            return ['rwcap', 'raphael']
        return ['raphael', 'rwcap']

    
    def _resolve_label_path(self, graph_file: Path) -> Tuple[Optional[Path], Optional[str]]:
        # SPEF manifest resolution removed - use direct SPEF file lookup
        if self.spef_files:
            spef_path = self._find_matching_spef(graph_file)
            if spef_path is not None:
                # Guess solver from parent directory name if possible
                solver = None
                parent_name = spef_path.parent.name.lower()
                if 'rwcap' in parent_name:
                    solver = 'rwcap'
                elif 'raphael' in parent_name:
                    solver = 'raphael'
                return spef_path, solver

        return None, None

        if '_chunk' in stem:
            add(stem.split('_chunk')[0])

        if '_' in stem:
            add(stem.split('_')[0])

        return keys

    def _extend_with_neighbor_label_dirs(self) -> None:
        """Append SPEF files from dataset-local label directories if available."""
        if self.data_dir is None:
            return

        dataset_root: Optional[Path] = None
        if self.data_dir.name == 'graphs':
            dataset_root = self.data_dir.parent
        else:
            parent = self.data_dir.parent
            if parent and parent.name == 'graphs':
                dataset_root = parent.parent

        if dataset_root is None:
            return

        for dirname in ('out_openrcx', 'labels_rwcap', 'labels_raphael'):
            candidate = dataset_root / dirname
            if candidate.exists():
                self.spef_files.extend(candidate.glob(f"*{self.spef_suffix}"))

    @staticmethod
    def _spef_keys(spef_path: Path) -> List[str]:
        """Generate candidate identifiers derived from a SPEF filename."""
        stem = spef_path.stem.lower()
        keys: List[str] = []

        def add(val: str) -> None:
            if val and val not in keys:
                keys.append(val)

        add(stem)
        if '_' in stem:
            add(stem.split('_')[0])
        if stem.endswith('.spef'):
            add(stem[:-5])
        return keys

    def _find_matching_spef(self, graph_path: Path) -> Optional[Path]:
        """Find the best SPEF file match for a graph path."""
        graph_keys = self._graph_keys(graph_path)
        for key in graph_keys:
            for spef_path, spef_keys in self._spef_key_cache:
                if key in spef_keys:
                    return spef_path
        return None

    def _load_labels_for_graph(self, graph_file: Path, data: Data) -> Optional[torch.Tensor]:
        """Load labels for a graph, preferring SPEF totals when available."""
        # Prefer SPEF-derived labels if configured and available
        spef_path = self._graph_to_spef.get(graph_file)
        solver_used = self._graph_solver.get(graph_file)
        if spef_path is not None:
            if self.label_type == 'total':
                labels = self._load_total_labels_from_spef(spef_path, data)
            else:
                labels = self._load_coupling_labels_from_spef(spef_path, data)

            if labels is not None:
                data.label_source = 'spef'
                data.spef_path = str(spef_path)
                if solver_used:
                    data.label_solver = solver_used
                return labels

        # Fallback: existing .pt label tensors
        label_file = graph_file.parent / f"{graph_file.stem}_labels.pt"
        if not label_file.exists():
            return None

        all_labels = torch.load(label_file, weights_only=False)

        if self.label_type == 'total':
            labels = (
                all_labels.get('total_capacitances')
                or all_labels.get('net_capacitances')
                or all_labels.get('node_capacitances')
            )
            if labels is not None:
                if not isinstance(labels, torch.Tensor):
                    labels = torch.tensor(labels, dtype=torch.float32)
                else:
                    labels = labels.clone().detach().float()
                data.label_source = 'tensor'
                data.label_tensor_path = str(label_file)
                return {'net': labels, 'node': None}
        else:  # coupling
            labels = all_labels.get('coupling_capacitances', None)
            if labels is None:
                labels = all_labels.get('edge_capacitances', None)

            # Filter small coupling capacitances if requested
            if labels is not None and self.min_coupling_ratio > 0:
                total_caps = all_labels.get('total_capacitances', None)
                if total_caps is not None:
                    edge_index = data.edge_index
                    node_total_caps = total_caps[edge_index[0]]  # Source node total cap
                    valid_mask = labels > (self.min_coupling_ratio * node_total_caps)
                    labels = labels * valid_mask.float()
                    data.edge_label_mask = valid_mask

        if labels is not None:
            data.label_source = 'tensor'
            data.label_tensor_path = str(label_file)
            if self.label_type == 'coupling' and not hasattr(data, 'edge_label_mask'):
                data.edge_label_mask = torch.ones(labels.shape[0], dtype=torch.bool)
        return labels

    def _load_total_labels_from_spef(self, spef_path: Path, data: Data) -> Optional[torch.Tensor]:
        """Load per-node total capacitance labels from a SPEF file."""
        try:
            totals, canonical_totals = self._get_spef_totals(spef_path)
        except RuntimeError as exc:
            print(f"WARNING: Failed to parse SPEF '{spef_path}': {exc}")
            return None

        node_net_names: Iterable[str] = getattr(data, 'node_net_names', [])
        if not node_net_names:
            print(f"WARNING: Graph {spef_path.name} lacks node_net_names; cannot assign labels.")
            return None

        net_names: List[str] = getattr(data, 'net_names', None)
        if not net_names:
            net_names = sorted(set(node_net_names))
            data.net_names = net_names

        labels = torch.zeros(len(net_names), dtype=torch.float32)
        missing_nets: List[str] = []

        for idx, net_name in enumerate(net_names):
            value = totals.get(net_name)
            if value is None:
                canonical = self._canonical_net_name(net_name)
                value = canonical_totals.get(canonical)
            if value is None:
                missing_nets.append(net_name)
                value = 0.0
            labels[idx] = float(value)

        if missing_nets:
            unique_missing = sorted(set(missing_nets))
            print(f"WARNING: {len(unique_missing)} nets missing capacitance labels in "
                  f"{spef_path.name}: {', '.join(unique_missing[:10])}"
                  f"{' ...' if len(unique_missing) > 10 else ''}")

        node_labels: Optional[torch.Tensor] = None
        node_net_index = self._ensure_node_net_index(data)
        if node_net_index is not None:
            node_labels = torch.zeros_like(node_net_index, dtype=torch.float32)
            valid = node_net_index >= 0
            if torch.any(valid):
                node_labels[valid] = labels[node_net_index[valid]]

        data.num_nets = len(net_names)
        return {'net': labels, 'node': node_labels}

    def _load_coupling_labels_from_spef(self, spef_path: Path, data: Data) -> Optional[torch.Tensor]:
        """Load per-edge coupling capacitance labels from a SPEF file."""
        try:
            pair_caps = self._get_spef_couplings(spef_path)
        except RuntimeError as exc:
            print(f"WARNING: Failed to parse SPEF '{spef_path}': {exc}")
            return None

        node_net_names: Iterable[str] = getattr(data, 'node_net_names', [])
        if not node_net_names:
            print(f"WARNING: Graph {spef_path.name} lacks node_net_names; cannot assign coupling labels.")
            return None

        edge_index: Optional[torch.Tensor] = getattr(data, 'edge_index', None)
        if edge_index is None:
            print(f"WARNING: Graph {spef_path.name} lacks edge_index; cannot assign coupling labels.")
            return None

        node_net_index = self._ensure_node_net_index(data)
        edge_net_index = self._ensure_edge_net_index(data, node_net_index)
        canonical_edge_mask = self._ensure_canonical_edge_mask(data)

        if node_net_index is None or edge_net_index is None or canonical_edge_mask is None:
            print(f"WARNING: Graph {spef_path.name} missing net index metadata; cannot assign coupling labels.")
            return None

        net_names: List[str] = getattr(data, 'net_names', None)
        if not net_names:
            net_names = sorted(set(node_net_names))
            data.net_names = net_names

        net_index = {name: idx for idx, name in enumerate(net_names)}
        canonical_net_index: Dict[str, int] = {}
        for name, idx in net_index.items():
            canonical = self._canonical_net_name(name)
            canonical_net_index.setdefault(canonical, idx)

        def resolve_net(name: str) -> Optional[int]:
            if name in net_index:
                return net_index[name]
            return canonical_net_index.get(self._canonical_net_name(name))

        num_edges = edge_index.shape[1]
        edge_labels = torch.zeros(num_edges, dtype=torch.float32)
        label_mask = torch.zeros(num_edges, dtype=torch.bool)

        pair_to_edges: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        canonical_indices = torch.nonzero(canonical_edge_mask, as_tuple=False).flatten().tolist()
        edge_net_index_cpu = edge_net_index.cpu()

        for edge_id in canonical_indices:
            src_net = int(edge_net_index_cpu[0, edge_id])
            dst_net = int(edge_net_index_cpu[1, edge_id])
            if src_net < 0 or dst_net < 0 or src_net == dst_net:
                continue
            key = (src_net, dst_net) if src_net < dst_net else (dst_net, src_net)
            pair_to_edges[key].append(edge_id)

        stats = {
            'total_pairs': len(pair_caps),
            'mapped_pairs': 0,
            'missing_net_pairs': 0,
            'missing_edge_pairs': 0,
            'missing_net_names': set(),
            'assigned_edges': 0,
            'total_coupling_f': float(sum(pair_caps.values())),
            'assigned_coupling_f': 0.0,
        }

        for (net_a_name, net_b_name), cap_value in pair_caps.items():
            idx_a = resolve_net(net_a_name)
            idx_b = resolve_net(net_b_name)
            if idx_a is None or idx_b is None:
                stats['missing_net_pairs'] += 1
                stats['missing_net_names'].update(
                    [
                        net_a_name if idx_a is None else None,
                        net_b_name if idx_b is None else None,
                    ]
                )
                continue

            if idx_a == idx_b:
                continue

            key = (idx_a, idx_b) if idx_a < idx_b else (idx_b, idx_a)
            edge_ids = pair_to_edges.get(key)
            if not edge_ids:
                stats['missing_edge_pairs'] += 1
                continue

            share = float(cap_value) / len(edge_ids)
            stats['mapped_pairs'] += 1
            stats['assigned_edges'] += len(edge_ids)
            stats['assigned_coupling_f'] += float(cap_value)

            for edge_id in edge_ids:
                edge_labels[edge_id] += share
                label_mask[edge_id] = True

        # Clean up missing net tracking (remove None placeholders)
        missing_names = {name for name in stats['missing_net_names'] if name}
        stats['missing_net_names'] = sorted(missing_names)

        if stats['missing_net_pairs']:
            print(
                f"WARNING: {spef_path.name}: {stats['missing_net_pairs']} coupling pairs "
                f"reference nets absent from the graph."
            )
        if stats['missing_edge_pairs']:
            print(
                f"WARNING: {spef_path.name}: {stats['missing_edge_pairs']} coupling pairs "
                f"had no matching graph edges."
            )

        if label_mask.any() and self.min_coupling_ratio > 0:
            label_mask = self._apply_coupling_threshold(label_mask, edge_labels, data, spef_path)

        data.edge_label_mask = label_mask
        data.coupling_label_stats = stats

        return edge_labels if label_mask.any() else edge_labels

    def _apply_coupling_threshold(
        self,
        label_mask: torch.Tensor,
        edge_labels: torch.Tensor,
        data: Data,
        spef_path: Path,
    ) -> torch.Tensor:
        """Filter coupling labels below the configured ratio threshold."""
        try:
            totals, canonical_totals = self._get_spef_totals(spef_path)
        except RuntimeError as exc:
            print(f"WARNING: Unable to apply coupling threshold for '{spef_path}': {exc}")
            return label_mask

        node_net_names: Iterable[str] = getattr(data, 'node_net_names', [])
        if not node_net_names:
            return label_mask

        node_totals = torch.zeros(len(node_net_names), dtype=torch.float32)
        for idx, net_name in enumerate(node_net_names):
            value = totals.get(net_name)
            if value is None:
                value = canonical_totals.get(self._canonical_net_name(net_name), 0.0)
            node_totals[idx] = float(value)

        edge_index: Optional[torch.Tensor] = getattr(data, 'edge_index', None)
        if edge_index is None:
            return label_mask

        source_totals = node_totals[edge_index[0]]

        new_mask = label_mask.clone()
        candidates = torch.nonzero(label_mask, as_tuple=False).flatten()
        if candidates.numel() == 0:
            return label_mask

        thresholds = self.min_coupling_ratio * source_totals[candidates]
        keep = edge_labels[candidates] > thresholds
        to_disable = candidates[~keep]
        if to_disable.numel() > 0:
            new_mask[to_disable] = False
            edge_labels[to_disable] = 0.0
            print(
                f"[CapacitanceDataset] Dropped {to_disable.numel()} coupling labels "
                f"below {self.min_coupling_ratio:.2%} threshold in {spef_path.name}"
            )

        return new_mask

    def _get_spef_totals(self, spef_path: Path) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Load and cache SPEF capacitance totals."""
        cached = self._spef_cache.get(spef_path)
        if cached is not None:
            return cached

        totals = load_dnet_totals(str(spef_path))
        canonical = {
            self._canonical_net_name(name): value for name, value in totals.items()
        }
        result = (totals, canonical)
        self._spef_cache[spef_path] = result
        return result

    def _get_spef_couplings(self, spef_path: Path) -> Dict[Tuple[str, str], float]:
        """Load and cache SPEF coupling capacitances."""
        cached = self._coupling_cache.get(spef_path)
        if cached is not None:
            return cached

        p = Path(spef_path)
        if not p.exists():
            raise RuntimeError(f"SPEF file not found: {spef_path}")

        couplings = load_coupling_pairs(p)
        self._coupling_cache[spef_path] = couplings
        return couplings

    def _ensure_node_net_index(self, data: Data) -> Optional[torch.Tensor]:
        """Ensure node_net_index exists on the graph and return it."""
        node_net_index = getattr(data, 'node_net_index', None)
        if node_net_index is not None:
            return node_net_index

        node_net_names: Iterable[str] = getattr(data, 'node_net_names', [])
        if not node_net_names:
            return None

        net_names: List[str] = getattr(data, 'net_names', None)
        if not net_names:
            net_names = sorted(set(node_net_names))
            data.net_names = net_names

        net_index = {name: idx for idx, name in enumerate(net_names)}
        tensor = torch.tensor([net_index.get(name, -1) for name in node_net_names], dtype=torch.long)
        data.node_net_index = tensor
        return tensor

    def _ensure_edge_net_index(
        self,
        data: Data,
        node_net_index: Optional[torch.Tensor] = None,
    ) -> Optional[torch.Tensor]:
        """Ensure edge_net_index exists on the graph and return it."""
        edge_net_index = getattr(data, 'edge_net_index', None)
        if edge_net_index is not None:
            return edge_net_index

        edge_index: Optional[torch.Tensor] = getattr(data, 'edge_index', None)
        if edge_index is None:
            return None

        if node_net_index is None:
            node_net_index = self._ensure_node_net_index(data)
        if node_net_index is None:
            return None

        tensor = torch.stack(
            (
                node_net_index[edge_index[0]],
                node_net_index[edge_index[1]],
            ),
            dim=0,
        )
        data.edge_net_index = tensor
        return tensor

    @staticmethod
    def _ensure_canonical_edge_mask(data: Data) -> Optional[torch.Tensor]:
        """Ensure canonical_edge_mask exists on the graph and return it."""
        mask = getattr(data, 'canonical_edge_mask', None)
        if mask is not None:
            return mask

        edge_index: Optional[torch.Tensor] = getattr(data, 'edge_index', None)
        if edge_index is None:
            return None

        mask = edge_index[0] <= edge_index[1]
        data.canonical_edge_mask = mask
        return mask


def create_filtered_dataset(
    data_dir: str,
    label_type: str = 'total',
    spef_dir: Optional[str] = None,
    spef_files: Optional[Sequence[str]] = None,
    spef_suffix: str = '.spef',
    solver_preference: str = 'auto',
    min_coupling_ratio: float = 0.01,
) -> CapacitanceDataset:
    """
    Create a dataset that only includes graphs with available SPEF files

    This follows the same approach as CNN-Cap and PCT-Cap by filtering out
    graphs that don't have corresponding SPEF files for labels.

    Args:
        data_dir: Directory containing .pt graph files
        label_type: Type of labels to load ('total' or 'coupling')
        spef_dir: Optional directory containing SPEF files for labels
        spef_files: Optional explicit list of SPEF file paths (overrides spef_dir)
        spef_suffix: Filename suffix to filter SPEF files when scanning directories
        solver_preference: Preferred SPEF solver ('rwcap', 'raphael', or 'auto')
        min_coupling_ratio: Minimum coupling capacitance ratio (filter small caps)

    Returns:
        Filtered CapacitanceDataset containing only graphs with SPEF labels
    """
    # Create full dataset first
    full_dataset = CapacitanceDataset(
        data_dir=data_dir,
        label_type=label_type,
        load_labels=True,  # Always load labels for training
        min_coupling_ratio=min_coupling_ratio,
        spef_dir=spef_dir,
        spef_files=spef_files,
        spef_suffix=spef_suffix,
        solver_preference=solver_preference,
    )

    # Filter out graphs without SPEF files
    valid_graph_files = []
    valid_metadata = []

    print(f"Filtering graphs with available SPEF files...")

    for i, graph_file in enumerate(full_dataset.graph_files):
        spef_path = full_dataset._graph_to_spef.get(graph_file)
        if spef_path is not None:
            valid_graph_files.append(graph_file)
            if i < len(full_dataset.metadata):
                valid_metadata.append(full_dataset.metadata[i])
        else:
            print(f"  Excluding {graph_file.name} - no SPEF file found")

    print(f"Filtered dataset: {len(valid_graph_files)}/{len(full_dataset.graph_files)} graphs have SPEF labels")

    # Create filtered dataset
    filtered_dataset = CapacitanceDataset.__new__(CapacitanceDataset)
    filtered_dataset.data_dir = full_dataset.data_dir
    filtered_dataset.label_type = full_dataset.label_type
    filtered_dataset.load_labels = True
    filtered_dataset.transform = full_dataset.transform
    filtered_dataset.min_coupling_ratio = full_dataset.min_coupling_ratio
    filtered_dataset.graph_files = valid_graph_files
    filtered_dataset.metadata = valid_metadata
    filtered_dataset.spef_suffix = full_dataset.spef_suffix
    filtered_dataset.solver_preference = full_dataset.solver_preference
    filtered_dataset._spef_cache = full_dataset._spef_cache
    filtered_dataset._coupling_cache = full_dataset._coupling_cache
    filtered_dataset._graph_to_spef = full_dataset._graph_to_spef
    filtered_dataset._graph_solver = full_dataset._graph_solver
    filtered_dataset.spef_files = full_dataset.spef_files
    filtered_dataset._spef_key_cache = full_dataset._spef_key_cache

    return filtered_dataset


def create_data_splits(
    dataset: CapacitanceDataset,
    train_ratio: float = 0.8,
    val_ratio: float = 0.2,
    test_ratio: float = 0.0,
    random_seed: int = 42
) -> Tuple[Dataset, Dataset, Dataset]:
    """
    Split dataset into train/validation/test sets

    Args:
        dataset: Full dataset
        train_ratio: Fraction for training (default: 0.8 for 80/20 split)
        val_ratio: Fraction for validation (default: 0.2 for 80/20 split)
        test_ratio: Fraction for testing (default: 0.0, no test set)
        random_seed: Random seed for reproducibility

    Returns:
        train_dataset, val_dataset, test_dataset
    """
    # Ensure ratios sum to 1
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        "Train/val/test ratios must sum to 1.0"

    # Calculate split sizes
    total_size = len(dataset)
    train_size = int(train_ratio * total_size)
    val_size = int(val_ratio * total_size)
    test_size = total_size - train_size - val_size  # Remaining

    # Perform split
    generator = torch.Generator().manual_seed(random_seed)
    train_dataset, val_dataset, test_dataset = random_split(
        dataset,
        [train_size, val_size, test_size],
        generator=generator
    )

    print(f"Dataset split: {train_size} train, {val_size} val, {test_size} test")
    print(f"Split ratios: {train_size/total_size:.2%} train, {val_size/total_size:.2%} val, {test_size/total_size:.2%} test")

    return train_dataset, val_dataset, test_dataset


def get_data_loader(
    dataset: Dataset,
    shuffle: bool = True,
    num_workers: int = 8,  # Optimized for performance (8 workers as requested)
    **kwargs
) -> DataLoader:
    """
    Create DataLoader for graph data using PyTorch Geometric standards.

    Simplified implementation with batch_size fixed at 1 for stable training of
    variable-sized graphs. Each graph contains hundreds of capacitance predictions,
    providing sufficient training signal per sample.

    Args:
        dataset: Dataset to load from
        shuffle: Whether to shuffle data
        num_workers: Number of worker processes (8 for optimal performance)
        **kwargs: Additional arguments for DataLoader

    Returns:
        PyTorch Geometric DataLoader instance with batch_size=1
    """
    try:
        from torch_geometric.loader import DataLoader as GeometricDataLoader

        # Use PyG's DataLoader with batch_size fixed at 1 for stable training
        loader = GeometricDataLoader(
            dataset,
            1,  # batch_size=1 fixed for variable-sized graphs
            shuffle=shuffle,
            num_workers=num_workers,
            follow_batch=['edge_attr'],  # Handle edge attributes properly
            exclude_keys=[],  # Include all attributes
            **kwargs
        )
        print(f"Using PyTorch Geometric DataLoader (batch_size=1, num_workers={num_workers})")

    except ImportError:
        # Fallback to standard DataLoader
        print("PyTorch Geometric DataLoader not available, using standard DataLoader")
        loader = DataLoader(
            dataset,
            1,  # batch_size=1 Conservative fallback
            shuffle=shuffle,
            num_workers=0,
            **kwargs
        )

    return loader


def collate_graph_data(batch: List[Tuple[Data, torch.Tensor]]):
    """
    Custom collate function for batching graphs

    Args:
        batch: List of (data, labels) tuples

    Returns:
        Batched data and labels
    """
    from torch_geometric.data import Batch

    # Separate data and labels
    data_list = [item[0] for item in batch]
    labels_list = [item[1] for item in batch if item[1] is not None]

    # Batch graphs
    batched_data = Batch.from_data_list(data_list)

    # Batch labels if available
    if len(labels_list) > 0:
        batched_labels = torch.cat(labels_list, dim=0)
    else:
        batched_labels = None

    return batched_data, batched_labels


def load_label_csv(
    label_csv_path: str,
    net_names: List[str]
) -> Dict[str, torch.Tensor]:
    """
    Load ground truth labels from CSV file

    CSV format: net1_name, net2_name, capacitance_value
    For total capacitance: net_name, net_name, total_capacitance
    For coupling: net1_name, net2_name, coupling_capacitance

    Args:
        label_csv_path: Path to CSV file
        net_names: List of net names in the graph

    Returns:
        Dictionary with 'total' and 'coupling' tensors
    """
    import csv

    # Create net name to index mapping
    net_to_idx = {name: idx for idx, name in enumerate(net_names)}
    num_nets = len(net_names)

    # Initialize capacitance matrix
    cap_matrix = np.zeros((num_nets, num_nets), dtype=np.float32)

    # Read CSV
    with open(label_csv_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header if exists

        for row in reader:
            if len(row) < 3:
                continue

            net1, net2, cap_value = row[0].strip(), row[1].strip(), float(row[2])

            # Get indices
            if net1 not in net_to_idx or net2 not in net_to_idx:
                continue

            idx1, idx2 = net_to_idx[net1], net_to_idx[net2]

            # Store in matrix (symmetric)
            cap_matrix[idx1, idx2] = cap_value
            cap_matrix[idx2, idx1] = cap_value

    # Extract total capacitances (diagonal)
    total_caps = torch.from_numpy(np.diag(cap_matrix))

    # Extract coupling capacitances (off-diagonal)
    coupling_caps = []
    coupling_indices = []
    for i in range(num_nets):
        for j in range(i+1, num_nets):
            if cap_matrix[i, j] > 0:
                coupling_caps.append(cap_matrix[i, j])
                coupling_indices.append([i, j])

    coupling_caps = torch.tensor(coupling_caps, dtype=torch.float32)
    coupling_indices = torch.tensor(coupling_indices, dtype=torch.long).t()

    return {
        'total_capacitances': total_caps,
        'coupling_capacitances': coupling_caps,
        'coupling_edge_index': coupling_indices,
        'capacitance_matrix': torch.from_numpy(cap_matrix)
    }


if __name__ == '__main__':
    # Test dataset loading
    print("Testing CapacitanceDataset...")

    # This is a placeholder test
    # In practice, you would have actual .pt files in a directory

    import sys
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]

        # Create dataset
        dataset_total = CapacitanceDataset(
            data_dir=data_dir,
            label_type='total',
            load_labels=False
        )

        dataset_coupling = CapacitanceDataset(
            data_dir=data_dir,
            label_type='coupling',
            load_labels=False
        )

        print(f"\nTotal capacitance dataset: {len(dataset_total)} samples")
        print(f"Coupling capacitance dataset: {len(dataset_coupling)} samples")

        # Load first sample
        if len(dataset_total) > 0:
            data, labels = dataset_total[0]
            print(f"\nFirst sample:")
            print(f"  Nodes: {data.x.shape}")
            print(f"  Edges: {data.edge_index.shape}")
            print(f"  Edge features: {data.edge_attr.shape}")
            if hasattr(data, 'edge_is_virtual'):
                print(f"  Virtual edges: {data.edge_is_virtual.sum().item()}")

        # Create data splits
        train_data, val_data, test_data = create_data_splits(dataset_total)

        # Create data loader (batch_size fixed at 1)
        train_loader = get_data_loader(train_data, shuffle=True)
        print(f"\nTrain loader created with {len(train_loader)} samples (batch_size=1)")

    else:
        print("Usage: python dataloader.py <data_dir>")
        print("Example: python dataloader.py ../../cap3d/graph_outputs/")

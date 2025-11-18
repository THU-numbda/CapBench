#!/usr/bin/env python3
"""
CAP3D to GNN-Cap Graph Converter

Converts CAP3D files into graph representations for GNN-based capacitance extraction.
Implements the graph construction algorithm from:
"GNN-Cap: Chip-Scale Interconnect Capacitance Extraction Using Graph Neural Network"
IEEE TCAD 2024

Features:
- Simple cuboid decomposition without overlap handling (fast, lightweight)
- Graph construction with regular and virtual edges
- Optional mesh visualization and debugging

Requirements:
    - torch, torch-geometric: conda run -n modern_nlp pip install torch torch-geometric

Usage:
    # Basic usage
    conda run -n klayout-net python cap3d_to_gnncap.py ../windows/cap3d/W0.cap3d --tech ../designs/tech/nangate45/nangate45_stack.yaml --output-dir data/

    # With chunking for training data
    conda run -n klayout-net python cap3d_to_gnncap.py ../designs/cap3d/gcd.cap3d --tech ../designs/tech/nangate45/nangate45_stack.yaml --window-size 20.0 --chunk-layout

    """

import sys
import argparse
import logging
import heapq
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
import time
from tqdm import tqdm

try:
    import yaml
except ImportError as exc:
    raise ImportError("PyYAML is required to parse technology stacks. Install with: pip install pyyaml") from exc

# Import existing CAP3D parser
from window_tools.cap3d_parser import StreamingCap3DParser
from window_tools.cap3d_models import Block, ParsedCap3DData
from common.datasets import (
    DATASET_ROOT,
    GRAPHS_DIR,
    WindowManifest,
    to_dataset_relative,
    repo_relative,
    get_dataset_subdirs,
    load_manifest,
    extract_process_node_from_path,
)

try:
    import torch
    from torch_geometric.data import Data
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    raise ImportError(
        "PyTorch and PyTorch Geometric are required. "
        "Install with: conda run -n modern_nlp pip install torch torch-geometric"
    )

# GMSH dependency removed - using simple block decomposition instead

logger = logging.getLogger(__name__)

# Graph construction defaults (μm) and per-process overrides
Z_EXTENSION_EPS = 1e-6
DEFAULT_GRAPH_PARAMS = {
    'cuboid_max_length': 2.0,
    'edge_threshold': 1.0,
    'virtual_edge_threshold': 4.0,
}

PROCESS_NODE_GRAPH_PARAMS: Dict[str, Dict[str, float]] = {
    'asap7': {
        'cuboid_max_length': 0.5,
        'edge_threshold': 0.25,
        'virtual_edge_threshold': 1.0,
    },
    'nangate45': {
        'cuboid_max_length': 3.0,
        'edge_threshold': 1.5,
        'virtual_edge_threshold': 6.0,
    },
    'sky130hd': {
        'cuboid_max_length': 8.0,
        'edge_threshold': 4.0,
        'virtual_edge_threshold': 16.0,
    },
}


@dataclass
class GraphNode:
    """Represents a node in the graph (cuboid)"""
    node_id: int
    cuboid_id: str  # Unique identifier for the cuboid
    net_name: str   # Net name this cuboid belongs to
    center: Tuple[float, float, float]  # Center coordinates (x, y, z)
    dimensions: Tuple[float, float, float]  # (x_len, y_len, z_len)
    layer: Optional[int] = None  # Metal layer number
    block_type: str = 'conductor'  # 'conductor' or 'medium'


@dataclass
class GraphEdge:
    """Represents an edge in the graph"""
    source_id: int
    target_id: int
    distance: float
    coord_diff: Tuple[float, float, float, float, float, float]  # dx1, dx2, dy1, dy2, dz1, dz2
    is_virtual: bool = False  # Whether this is a virtual edge


@dataclass
class TechLayerInfo:
    """Technology stack metadata for a single conductor layer"""
    name: str
    canonical_name: str
    z_min: float
    z_max: float
    thickness: float


def _vec_norm(v: Tuple[float, float, float]) -> float:
    """Calculate vector norm"""
    return np.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])


def aabb_intersect(
    bbox_a: Tuple[float, float, float, float, float, float],
    bbox_b: Tuple[float, float, float, float, float, float],
    pad: float = 0.0
) -> bool:
    """Check if two AABBs intersect (with optional padding)"""
    ax0, ay0, az0, ax1, ay1, az1 = bbox_a
    bx0, by0, bz0, bx1, by1, bz1 = bbox_b
    return not (
        ax1 <= bx0 - pad or bx1 <= ax0 - pad or
        ay1 <= by0 - pad or by1 <= ay0 - pad or
        az1 <= bz0 - pad or bz1 <= az0 - pad
    )


def bbox_eq(
    bbox_a: Tuple[float, float, float, float, float, float],
    bbox_b: Tuple[float, float, float, float, float, float],
    tol: float = 1e-12
) -> bool:
    """Check if two AABBs are equal within tolerance"""
    return all(abs(a - b) <= tol for a, b in zip(bbox_a, bbox_b))




class GNNCapGraphBuilder:
    """Build graph representation from CAP3D layout"""

    def __init__(
        self,
        cuboid_max_length: float = 2.0,
        edge_threshold: float = 1.0,
        virtual_edge_threshold: float = 4.0,
        window_size: float = 20.0,
        use_virtual_edges: bool = True,
        output_dir: Optional[Path] = None,
        tech_stack_path: Optional[Path] = None,
    ):
        """
        Initialize graph builder with parameters from GNN-Cap paper

        Args:
            cuboid_max_length: Maximum cuboid length (lm) in μm
            edge_threshold: Distance threshold (de) for regular edges in μm
            virtual_edge_threshold: Distance threshold (devir) for virtual edges in μm
            window_size: Size of layout chunks for training in μm
            use_virtual_edges: Whether to add virtual edges
            output_dir: Output directory for mesh files
            tech_stack_path: Path to technology stack YAML (required)
        """
        self.cuboid_max_length = cuboid_max_length
        self.edge_threshold = edge_threshold
        self.virtual_edge_threshold = virtual_edge_threshold
        self.window_size = window_size
        self.use_virtual_edges = use_virtual_edges
        self.output_dir = output_dir

        if tech_stack_path is None:
            raise ValueError("Technology stack path is required")
        self.tech_stack_path = Path(tech_stack_path)
        self.cap3d_path: Optional[Path] = None

        # Internal state
        self.nodes: List[GraphNode] = []
        self.edges: List[GraphEdge] = []
        self.node_id_counter = 0
        self.layer_bounds: Dict[int, Tuple[float, float]] = {}
        self.layer_order: List[int] = []
        self.layer_index_map: Dict[int, int] = {}
        self.adjacent_layer_gaps: Dict[Tuple[int, int], float] = {}
        self.cap3d_layers: Dict[int, 'Layer'] = {}
        self.layer_canonical_names: Dict[int, Optional[str]] = {}
        self.layer_category_map: Dict[int, str] = {}
        self.layer_connection_map: Dict[Optional[int], Set[int]] = {}

        # Technology metadata
        self.tech_conductors: List[TechLayerInfo] = []
        self.tech_layer_lookup: Dict[str, TechLayerInfo] = {}
        self.tech_layer_indices: Dict[str, int] = {}
        self.tech_adjacent_gaps: Dict[Tuple[str, str], float] = {}
        self._load_tech_stack()

    @staticmethod
    def _canonical_layer_name(name: Optional[str]) -> Optional[str]:
        if name is None:
            return None
        return name.strip().lower()

    @staticmethod
    def _categorize_layer_type(layer_type: Optional[str]) -> str:
        """Map CAP3D layer types to coarse categories."""
        if layer_type is None:
            return 'other'
        lt = layer_type.lower()
        if lt in {'via', 'contact'}:
            return 'via'
        if lt in {'interconnect', 'metal', 'poly', 'diffusion', 'conductor'}:
            return 'metal'
        return 'other'

    def _load_tech_stack(self) -> None:
        """Load conductor layer metadata from technology stack YAML"""
        if not self.tech_stack_path.exists():
            raise FileNotFoundError(f"Technology stack file not found: {self.tech_stack_path}")

        with self.tech_stack_path.open('r', encoding='utf-8') as f:
            tech_data = yaml.safe_load(f)

        if not tech_data or 'stack' not in tech_data:
            raise ValueError(f"Invalid technology stack format in {self.tech_stack_path} - missing 'stack' key")

        entries = tech_data['stack']
        if not isinstance(entries, list):
            raise ValueError(f"'stack' must be a list in {self.tech_stack_path}")

        z_cursor = 0.0
        previous_conductor: Optional[TechLayerInfo] = None

        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid layer entry {entry} in {self.tech_stack_path}")

            name = entry.get('name')
            layer_type = entry.get('type')
            thickness = entry.get('thickness_um', 0.0)

            if not name or not layer_type:
                raise ValueError(f"Invalid layer entry: missing name or type: {entry}")

            # Update cumulative z-height
            z_cursor += thickness

            # Add conductor layers only (type: 'metal')
            if layer_type == 'metal':
                z_min = z_cursor - thickness  # Bottom of this layer
                z_max = z_cursor              # Top of this layer
                canonical = self._canonical_layer_name(name)
                if canonical is None:
                    raise ValueError(f"Invalid layer name '{name}' in {self.tech_stack_path}")

                info = TechLayerInfo(
                    name=name,
                    canonical_name=canonical,
                    z_min=z_min,
                    z_max=z_max,
                    thickness=thickness,
                )
                self.tech_layer_indices[canonical] = len(self.tech_conductors)
                self.tech_conductors.append(info)
                self.tech_layer_lookup[canonical] = info

                if previous_conductor is not None:
                    # Calculate gap between this conductor and previous conductor
                    # In the new format, we need to account for dielectric layers between them
                    gap = z_min - previous_conductor.z_max
                    gap = max(0.0, gap)  # Ensure non-negative
                    lower = previous_conductor.canonical_name
                    upper = canonical
                    self.tech_adjacent_gaps[(lower, upper)] = gap
                    self.tech_adjacent_gaps[(upper, lower)] = gap

                previous_conductor = info

        if not self.tech_conductors:
            raise ValueError(f"No conductor layers found in technology stack {self.tech_stack_path}")

    def parse_cap3d(self, cap3d_file: str) -> ParsedCap3DData:
        """Parse CAP3D file using existing parser"""
        self.cap3d_path = Path(cap3d_file)
        parser = StreamingCap3DParser(cap3d_file)
        parsed_data = parser.parse_complete()
        return parsed_data

    def _build_blocks_from_bboxes(
        self,
        blocks: List[Block],
        net_name: str,
        bounding_boxes: List[Tuple[float, float, float, float, float, float]],
    ) -> List[Block]:
        """
        Build cuboid blocks from bounding boxes.
        """
        tolerance = 1e-6
        decomposed_blocks: List[Block] = []
        seen_boxes: Set[Tuple[int, int, int, int, int, int]] = set()

        # Cache block bounds for fast membership checks
        block_bounds: List[Tuple[np.ndarray, np.ndarray, Block]] = []
        for block in blocks:
            bmin, bmax = block.bounds
            block_bounds.append((bmin.astype(np.float64), bmax.astype(np.float64), block))

        def cell_volume_intersection(x0, y0, z0, x1, y1, z1) -> Optional[Block]:
            half_x = 0.5 * (x0 + x1)
            half_y = 0.5 * (y0 + y1)
            half_z = 0.5 * (z0 + z1)

            for bmin, bmax, block in block_bounds:
                if (
                    bmin[0] <= half_x <= bmax[0] and
                    bmin[1] <= half_y <= bmax[1] and
                    bmin[2] <= half_z <= bmax[2]
                ):
                    return block
            return None

        def cell_surface_overlap(x0, y0, z0, x1, y1, z1) -> Optional[Block]:
            tol = 1e-6
            for bmin, bmax, block in block_bounds:
                overlap_x = max(0.0, min(x1, bmax[0]) - max(x0, bmin[0]))
                overlap_y = max(0.0, min(y1, bmax[1]) - max(y0, bmin[1]))
                overlap_z = max(0.0, min(z1, bmax[2]) - max(z0, bmin[2]))
                overlap_volume = overlap_x * overlap_y * overlap_z
                if overlap_volume > tol:
                    return block

                face_area_xy = overlap_x * overlap_y
                if face_area_xy > tol and (abs(z0 - bmax[2]) < tol or abs(z1 - bmin[2]) < tol):
                    return block

                face_area_xz = overlap_x * overlap_z
                if face_area_xz > tol and (abs(y0 - bmax[1]) < tol or abs(y1 - bmin[1]) < tol):
                    return block

                face_area_yz = overlap_y * overlap_z
                if face_area_yz > tol and (abs(x0 - bmax[0]) < tol or abs(x1 - bmin[0]) < tol):
                    return block
            return None

        for bbox in bounding_boxes:
            x0, y0, z0, x1, y1, z1 = bbox
            x_len = x1 - x0
            y_len = y1 - y0
            z_len = z1 - z0
            if x_len <= tolerance or y_len <= tolerance or z_len <= tolerance:
                continue

            key = (
                int(round(x0 * 1e6)),
                int(round(y0 * 1e6)),
                int(round(z0 * 1e6)),
                int(round(x1 * 1e6)),
                int(round(y1 * 1e6)),
                int(round(z1 * 1e6)),
            )
            if key in seen_boxes:
                continue
            seen_boxes.add(key)

            covering_block = cell_volume_intersection(x0, y0, z0, x1, y1, z1)
            if covering_block is None:
                covering_block = cell_surface_overlap(x0, y0, z0, x1, y1, z1)

            if covering_block is None:
                continue

            base = np.array([x0, y0, z0], dtype=np.float32)
            v1 = np.array([x_len, 0.0, 0.0], dtype=np.float32)
            v2 = np.array([0.0, y_len, 0.0], dtype=np.float32)
            hvec = np.array([0.0, 0.0, z_len], dtype=np.float32)

            new_block = Block(
                name=f"{net_name}_cell_{len(decomposed_blocks)}",
                type=covering_block.type,
                parent_name=covering_block.parent_name,
                base=base,
                v1=v1,
                v2=v2,
                hvec=hvec,
                diel=covering_block.diel,
                layer=covering_block.layer,
            )
            decomposed_blocks.append(new_block)

        return decomposed_blocks

    def decompose_net_simple(
        self,
        blocks: List[Block],
        net_name: str
    ) -> List[Block]:
        """
        Decompose blocks into simple cuboids using subdivision without overlap handling.

        Args:
            blocks: List of blocks belonging to the same conductor/net
            net_name: Name of the net (for output block naming)

        Returns:
            List of cuboid blocks with max dimension <= cuboid_max_length
        """
        if not blocks:
            return []

        decomposed_blocks = []
        for i, block in enumerate(blocks):
            # Get block dimensions and bounds
            bp = block.base
            v1 = block.v1
            v2 = block.v2

            # Calculate bounds
            x_min, x_max = min(bp[0], bp[0] + v1[0]), max(bp[0], bp[0] + v1[0])
            y_min, y_max = min(bp[1], bp[1] + v2[1]), max(bp[1], bp[1] + v2[1])
            z_min, z_max = min(bp[2], bp[2] + block.hvec[2]), max(bp[2], bp[2] + block.hvec[2])

            # Subdivide if block exceeds maximum dimension
            x_len = x_max - x_min
            y_len = y_max - y_min
            z_len = z_max - z_min

            # Determine subdivision counts
            x_subdiv = max(1, int(np.ceil(x_len / self.cuboid_max_length)))
            y_subdiv = max(1, int(np.ceil(y_len / self.cuboid_max_length)))
            z_subdiv = max(1, int(np.ceil(z_len / self.cuboid_max_length)))

            # Create subdivided blocks
            for xi in range(x_subdiv):
                for yi in range(y_subdiv):
                    for zi in range(z_subdiv):
                        # Calculate sub-block bounds
                        x0 = x_min + (xi * x_len / x_subdiv)
                        x1 = x_min + ((xi + 1) * x_len / x_subdiv)
                        y0 = y_min + (yi * y_len / y_subdiv)
                        y1 = y_min + ((yi + 1) * y_len / y_subdiv)
                        z0 = z_min + (zi * z_len / z_subdiv)
                        z1 = z_min + ((zi + 1) * z_len / z_subdiv)

                        # Create new block
                        new_base = (x0, y0, z0)
                        new_v1 = (x1 - x0, 0, 0)
                        new_v2 = (0, y1 - y0, 0)
                        new_hvec = (0, 0, z1 - z0)

                        sub_block = Block(
                            name=f"{block.name}_sub{i}_{xi}{yi}{zi}",
                            parent_name=block.parent_name,
                            base=new_base,
                            v1=new_v1,
                            v2=new_v2,
                            hvec=new_hvec,
                            type=block.type,
                            layer=block.layer
                        )
                        decomposed_blocks.append(sub_block)

        return decomposed_blocks
    def block_to_node(self, block: Block) -> GraphNode:
        """Convert a Block to a GraphNode with features"""
        # Calculate center
        center = tuple(block.center)

        # Extract dimensions (node features as per paper Fig. 4)
        x_len = abs(block.v1[0])
        y_len = abs(block.v2[1])
        z_len = abs(block.hvec[2])
        dimensions = (x_len, y_len, z_len)

        # Create node
        node = GraphNode(
            node_id=self.node_id_counter,
            cuboid_id=block.name,
            net_name=block.parent_name or "unknown_net",
            center=center,
            dimensions=dimensions,
            layer=block.layer,
            block_type=block.type,
        )

        self.node_id_counter += 1
        return node

    @staticmethod
    def _node_bbox(node: GraphNode) -> Tuple[float, float, float, float, float, float]:
        """Axis-aligned bounding box (xmin, xmax, ymin, ymax, zmin, zmax)"""
        cx, cy, cz = node.center
        dx, dy, dz = node.dimensions
        half_dx, half_dy, half_dz = dx / 2.0, dy / 2.0, dz / 2.0
        return (
            cx - half_dx,
            cx + half_dx,
            cy - half_dy,
            cy + half_dy,
            cz - half_dz,
            cz + half_dz,
        )

    @staticmethod
    def _node_xy_bbox(node: GraphNode) -> Tuple[float, float, float, float]:
        """Axis-aligned XY bounding box (xmin, xmax, ymin, ymax)"""
        xmin, xmax, ymin, ymax, _, _ = GNNCapGraphBuilder._node_bbox(node)
        return xmin, xmax, ymin, ymax

    @staticmethod
    def _planar_distance(node_a: GraphNode, node_b: GraphNode) -> float:
        """Euclidean distance in the XY plane"""
        xa, ya, _ = node_a.center
        xb, yb, _ = node_b.center
        return float(np.hypot(xb - xa, yb - ya))

    @staticmethod
    def _xy_overlap(
        bbox_a: Tuple[float, float, float, float],
        bbox_b: Tuple[float, float, float, float],
        tol: float = 1e-12,
    ) -> Optional[Tuple[float, float, float, float]]:
        """Return intersection of two XY rectangles, or None if they do not overlap"""
        ax0, ax1, ay0, ay1 = bbox_a
        bx0, bx1, by0, by1 = bbox_b
        ix0 = max(ax0, bx0)
        ix1 = min(ax1, bx1)
        iy0 = max(ay0, by0)
        iy1 = min(ay1, by1)
        if ix1 - ix0 <= tol or iy1 - iy0 <= tol:
            return None
        return (ix0, ix1, iy0, iy1)

    def _prepare_layer_metadata(self) -> None:
        """Collect per-layer z bounds and adjacency information using tech stack"""
        geom_bounds: Dict[int, Tuple[float, float]] = {}

        # Aggregate bounds from node AABBs for fallback/comparison
        for node in self.nodes:
            if node.layer is None:
                continue
            xmin, xmax, ymin, ymax, zmin, zmax = self._node_bbox(node)
            if node.layer not in geom_bounds:
                geom_bounds[node.layer] = (zmin, zmax)
            else:
                cur_min, cur_max = geom_bounds[node.layer]
                geom_bounds[node.layer] = (min(cur_min, zmin), max(cur_max, zmax))

        layer_bounds: Dict[int, Tuple[float, float]] = {}
        centroids: Dict[int, float] = {}
        self.layer_canonical_names = {}
        layer_sources: Dict[int, str] = {}

        for layer_id, bounds in geom_bounds.items():
            layer_name = None
            if layer_id in self.cap3d_layers:
                layer_name = self.cap3d_layers[layer_id].name
            canonical = self._canonical_layer_name(layer_name)
            self.layer_canonical_names[layer_id] = canonical

            tech_info = self.tech_layer_lookup.get(canonical) if canonical else None
            if tech_info:
                layer_bounds[layer_id] = (tech_info.z_min, tech_info.z_max)
                centroids[layer_id] = 0.5 * (tech_info.z_min + tech_info.z_max)
                layer_sources[layer_id] = 'tech'
            else:
                layer_bounds[layer_id] = bounds
                centroids[layer_id] = 0.5 * (bounds[0] + bounds[1])
                layer_sources[layer_id] = 'geometry'

        self.layer_bounds = layer_bounds
        self.layer_order = sorted(layer_bounds.keys(), key=lambda lid: centroids[lid])
        self.layer_index_map = {layer: idx for idx, layer in enumerate(self.layer_order)}

        # Compute adjacent gaps, preferring tech stack values where available
        gaps: Dict[Tuple[int, int], float] = {}
        for lower, upper in zip(self.layer_order, self.layer_order[1:]):
            lower_name = self.layer_canonical_names.get(lower)
            upper_name = self.layer_canonical_names.get(upper)
            gap: Optional[float] = None

            if lower_name and upper_name:
                idx_lower = self.tech_layer_indices.get(lower_name)
                idx_upper = self.tech_layer_indices.get(upper_name)
                if (
                    idx_lower is not None
                    and idx_upper is not None
                    and abs(idx_lower - idx_upper) == 1
                ):
                    gap = self.tech_adjacent_gaps.get((lower_name, upper_name))

            if gap is None:
                lower_geom = geom_bounds.get(lower)
                upper_geom = geom_bounds.get(upper)
                if lower_geom and upper_geom:
                    gap = max(0.0, upper_geom[0] - lower_geom[1])
                else:
                    gap = 0.0

            gaps[(lower, upper)] = gap
            gaps[(upper, lower)] = gap

        self.adjacent_layer_gaps = gaps

        # Determine layer categories and connection policy
        self.layer_category_map: Dict[int, str] = {}
        self.layer_connection_map: Dict[int, Set[int]] = {layer: {layer} for layer in self.layer_order}

        for layer in self.layer_order:
            cap_layer = self.cap3d_layers.get(layer)
            layer_type = cap_layer.type if cap_layer else None
            self.layer_category_map[layer] = self._categorize_layer_type(layer_type)

        total_layers = len(self.layer_order)
        for idx, layer in enumerate(self.layer_order):
            category = self.layer_category_map.get(layer, 'other')

            if category == 'via':
                for neighbor_idx in (idx - 1, idx + 1):
                    if 0 <= neighbor_idx < total_layers:
                        neighbor_layer = self.layer_order[neighbor_idx]
                        self.layer_connection_map[layer].add(neighbor_layer)
                        self.layer_connection_map.setdefault(neighbor_layer, {neighbor_layer}).add(layer)

            elif category == 'metal':
                # Connect to immediate via layers (if any)
                for neighbor_idx in (idx - 1, idx + 1):
                    if 0 <= neighbor_idx < total_layers:
                        neighbor_layer = self.layer_order[neighbor_idx]
                        if self.layer_category_map.get(neighbor_layer) == 'via':
                            self.layer_connection_map[layer].add(neighbor_layer)
                            self.layer_connection_map.setdefault(neighbor_layer, {neighbor_layer}).add(layer)

                # Connect to the next metal layer in each direction
                for offset in (-1, 1):
                    search_idx = idx + offset
                    while 0 <= search_idx < total_layers:
                        candidate_layer = self.layer_order[search_idx]
                        candidate_category = self.layer_category_map.get(candidate_layer, 'other')
                        if candidate_category == 'metal' and candidate_layer != layer:
                            self.layer_connection_map[layer].add(candidate_layer)
                            self.layer_connection_map.setdefault(candidate_layer, {candidate_layer}).add(layer)
                            break
                        elif candidate_category == 'via':
                            search_idx += offset
                            continue
                        else:
                            break

        # Ensure we have a default bucket for nodes without layer attribution
        self.layer_connection_map.setdefault(None, {None})

        # Diagnostics
        if self.layer_order:
            for layer in self.layer_order:
                z0, z1 = self.layer_bounds[layer]
                layer_obj = self.cap3d_layers.get(layer)
                layer_name = layer_obj.name if layer_obj else f"id={layer}"
                source = layer_sources.get(layer, 'unknown')
            for (layer_a, layer_b), gap in sorted(self.adjacent_layer_gaps.items()):
                if self.layer_index_map.get(layer_b) != self.layer_index_map.get(layer_a, -2) + 1:
                    continue
                name_a = self.cap3d_layers.get(layer_a).name if layer_a in self.cap3d_layers else f"id={layer_a}"
                name_b = self.cap3d_layers.get(layer_b).name if layer_b in self.cap3d_layers else f"id={layer_b}"

    def _exceeds_layer_hops(self, layer_a: Optional[int], layer_b: Optional[int]) -> bool:
        """Return True if a layer pair violates the configured layer-connection policy."""
        if layer_a is None or layer_b is None:
            return False
        allowed = self.layer_connection_map.get(layer_a)
        if allowed is None:
            return False
        return layer_b not in allowed

    def _has_same_layer_blocker(
        self,
        node_a: GraphNode,
        node_b: GraphNode,
        layer_nodes: List[GraphNode],
        tol: float = 1e-12,
    ) -> bool:
        """Check if any other node on the same layer blocks the corridor between two nodes."""
        ax0, ax1, ay0, ay1 = self._node_xy_bbox(node_a)
        bx0, bx1, by0, by1 = self._node_xy_bbox(node_b)
        rx0, rx1 = min(ax0, bx0), max(ax1, bx1)
        ry0, ry1 = min(ay0, by0), max(ay1, by1)

        for node in layer_nodes:
            if node.node_id in (node_a.node_id, node_b.node_id):
                continue
            nx0, nx1, ny0, ny1 = self._node_xy_bbox(node)
            if nx1 <= rx0 + tol or nx0 >= rx1 - tol or ny1 <= ry0 + tol or ny0 >= ry1 - tol:
                continue
            return True
        return False

    def _check_xy_overlap_after_extension(
        self,
        node_a: GraphNode,
        node_b: GraphNode,
        xy_extension: float,
    ) -> bool:
        """Check if two cuboids overlap in XY after applying planar extension."""
        ax0, ax1, ay0, ay1 = self._node_xy_bbox(node_a)
        bx0, bx1, by0, by1 = self._node_xy_bbox(node_b)

        ax0 -= xy_extension
        ax1 += xy_extension
        ay0 -= xy_extension
        ay1 += xy_extension

        bx0 -= xy_extension
        bx1 += xy_extension
        by0 -= xy_extension
        by1 += xy_extension

        x_overlap = not (ax1 < bx0 or bx1 < ax0)
        y_overlap = not (ay1 < by0 or by1 < ay0)
        return x_overlap and y_overlap

    def _required_z_extension(
        self,
        lower_layer: Optional[int],
        upper_layer: Optional[int],
        fallback_gap: float,
    ) -> float:
        """Return extension needed (per cuboid) to bridge a dielectric gap."""
        if fallback_gap <= 0:
            return 0.0

        gap = fallback_gap
        if lower_layer is not None and upper_layer is not None:
            key = (lower_layer, upper_layer)
            if key not in self.adjacent_layer_gaps:
                key = (upper_layer, lower_layer)
            layer_gap = self.adjacent_layer_gaps.get(key)
            if layer_gap is not None and layer_gap > 0:
                gap = max(gap, layer_gap)

        return (gap / 2.0) + Z_EXTENSION_EPS

    def _check_z_overlap_after_extension(
        self,
        node_a: GraphNode,
        node_b: GraphNode,
    ) -> bool:
        """Check if cuboids overlap along Z after applying dielectric extensions."""
        _, _, _, _, az0, az1 = self._node_bbox(node_a)
        _, _, _, _, bz0, bz1 = self._node_bbox(node_b)

        if az1 >= bz0 and bz1 >= az0:
            return True

        if az1 < bz0:
            gap = bz0 - az1
            extension = self._required_z_extension(node_a.layer, node_b.layer, gap)
            return (az1 + extension) >= (bz0 - extension)

        if bz1 < az0:
            gap = az0 - bz1
            extension = self._required_z_extension(node_b.layer, node_a.layer, gap)
            return (bz1 + extension) >= (az0 - extension)

        return False

    def _cuboids_overlap_with_extension(self, node_a: GraphNode, node_b: GraphNode) -> bool:
        """Return True if cuboids intersect after planar + vertical extension."""
        xy_extension = self.edge_threshold / 2.0
        if not self._check_xy_overlap_after_extension(node_a, node_b, xy_extension):
            return False
        return self._check_z_overlap_after_extension(node_a, node_b)

    def _prepare_sweep_entries(
        self,
        nodes: List[GraphNode],
        xy_extension: float,
    ) -> List[Tuple[float, float, float, float, GraphNode]]:
        """Precompute expanded XY intervals for sweeping."""
        entries: List[Tuple[float, float, float, float, GraphNode]] = []
        for node in nodes:
            xmin, xmax, ymin, ymax = self._node_xy_bbox(node)
            entries.append(
                (
                    xmin - xy_extension,
                    xmax + xy_extension,
                    ymin - xy_extension,
                    ymax + xy_extension,
                    node,
                )
            )
        entries.sort(key=lambda entry: entry[0])
        return entries

    def _verify_decomposed_block_dimensions(self, blocks_by_net: Dict[str, List[Block]]):
        """
        Verify all decomposed cuboids satisfy the maximum length constraint
        """
        if not blocks_by_net:
            return

        tolerance = 1e-5
        total_blocks = 0
        max_dimension = 0.0
        violations: List[Tuple[str, str, Tuple[float, float, float]]] = []

        for net_name, blocks in blocks_by_net.items():
            for block in blocks:
                total_blocks += 1
                dx = float(np.linalg.norm(block.v1))
                dy = float(np.linalg.norm(block.v2))
                dz = float(np.linalg.norm(block.hvec))
                dims = (dx, dy, dz)
                block_max = max(dims)
                max_dimension = max(max_dimension, block_max)
                if block_max > self.cuboid_max_length + tolerance:
                    violations.append((net_name, block.name, dims))

        if violations:
            first_net, first_block, dims = violations[0]
            raise RuntimeError(
                f"{len(violations)} cuboids exceed cuboid_max_length "
                f"({self.cuboid_max_length}μm). Example: {first_net}/{first_block} "
                f"dimensions ({dims[0]:.4f}, {dims[1]:.4f}, {dims[2]:.4f}) μm."
            )


    def calculate_edge_features(self, node_a: GraphNode, node_b: GraphNode) -> Tuple[float, Tuple]:
        """
        Calculate edge features as described in paper Fig. 4

        Returns:
            distance: Distance between centers (dAB)
            coord_diff: (dx1, dx2, dy1, dy2, dz1, dz2)
        """
        # Centers
        xa, ya, za = node_a.center
        xb, yb, zb = node_b.center

        # Distance between centers
        distance = np.sqrt((xb - xa)**2 + (yb - ya)**2 + (zb - za)**2)

        # Coordinate differences (always choose node with smaller coordinate as reference)
        # This ensures same features for edges regardless of direction
        def axis_deltas(coord_a: float, coord_b: float) -> Tuple[float, float]:
            delta = coord_b - coord_a
            if coord_a <= coord_b:
                return 0.0, delta
            return 0.0, -delta

        dx1, dx2 = axis_deltas(xa, xb)
        dy1, dy2 = axis_deltas(ya, yb)
        dz1, dz2 = axis_deltas(za, zb)

        coord_diff = (dx1, dx2, dy1, dy2, dz1, dz2)

        return distance, coord_diff

    def build_edges_regular(self):
        """
        Build regular edges based on cuboid extension algorithm (Fig. 2)

        From paper: "Two nodes will have an edge connecting them if they are
        in close proximity" within threshold de.
        """
        edge_count = 0

        nodes_by_layer: Dict[Optional[int], List[GraphNode]] = defaultdict(list)
        for node in self.nodes:
            nodes_by_layer[node.layer].append(node)

        layer_sequence: List[Optional[int]] = [
            layer for layer in self.layer_order if layer in nodes_by_layer
        ]
        if None in nodes_by_layer:
            layer_sequence.append(None)

        def layer_index(layer_id: Optional[int]) -> int:
            if layer_id is None:
                return -1
            return self.layer_index_map.get(layer_id, -1)

        xy_extension = self.edge_threshold / 2.0
        processed_pairs: Set[Tuple[int, int]] = set()
        sweep_cache: Dict[Optional[int], List[Tuple[float, float, float, float, GraphNode]]] = {}

        def get_entries(layer_id: Optional[int]) -> List[Tuple[float, float, float, float, GraphNode]]:
            if layer_id not in sweep_cache:
                sweep_cache[layer_id] = self._prepare_sweep_entries(
                    nodes_by_layer.get(layer_id, []),
                    xy_extension,
                )
            return sweep_cache[layer_id]

        def add_edge(node_a: GraphNode, node_b: GraphNode) -> None:
            nonlocal edge_count
            if node_a.node_id == node_b.node_id:
                return
            pair_key = (
                min(node_a.node_id, node_b.node_id),
                max(node_a.node_id, node_b.node_id),
            )
            if pair_key in processed_pairs:
                return
            if self._exceeds_layer_hops(node_a.layer, node_b.layer):
                return
            if not self._check_z_overlap_after_extension(node_a, node_b):
                return

            distance, coord_diff = self.calculate_edge_features(node_a, node_b)
            edge = GraphEdge(
                source_id=node_a.node_id,
                target_id=node_b.node_id,
                distance=distance,
                coord_diff=coord_diff,
                is_virtual=False,
            )
            self.edges.append(edge)
            processed_pairs.add(pair_key)
            edge_count += 1

        def connect_same_layer(entries: List[Tuple[float, float, float, float, GraphNode]]) -> None:
            if not entries:
                return
            active_heap: List[Tuple[float, int]] = []
            active_entries: Dict[int, Tuple[float, float, float, GraphNode]] = {}

            for x0, x1, y0, y1, node in entries:
                while active_heap and active_heap[0][0] < x0:
                    _, expired_id = heapq.heappop(active_heap)
                    active_entries.pop(expired_id, None)

                for _, ay0, ay1, other in active_entries.values():
                    if ay1 < y0 or y1 < ay0:
                        continue
                    add_edge(node, other)

                active_entries[node.node_id] = (x1, y0, y1, node)
                heapq.heappush(active_heap, (x1, node.node_id))

        def connect_cross_layer(
            entries_a: List[Tuple[float, float, float, float, GraphNode]],
            entries_b: List[Tuple[float, float, float, float, GraphNode]],
        ) -> None:
            if not entries_a or not entries_b:
                return

            if len(entries_a) > len(entries_b):
                entries_a, entries_b = entries_b, entries_a

            active_heap: List[Tuple[float, int]] = []
            active_entries: Dict[int, Tuple[float, float, float, GraphNode]] = {}
            b_idx = 0

            for ax0, ax1, ay0, ay1, node_a in entries_a:
                while active_heap and active_heap[0][0] < ax0:
                    _, expired_id = heapq.heappop(active_heap)
                    active_entries.pop(expired_id, None)

                while b_idx < len(entries_b) and entries_b[b_idx][0] <= ax1:
                    bx0, bx1, by0, by1, node_b = entries_b[b_idx]
                    heapq.heappush(active_heap, (bx1, node_b.node_id))
                    active_entries[node_b.node_id] = (bx1, by0, by1, node_b)
                    b_idx += 1

                if not active_entries:
                    continue

                for _, by0, by1, node_b in active_entries.values():
                    if by1 < ay0 or ay1 < by0:
                        continue
                    add_edge(node_a, node_b)

        for layer in layer_sequence:
            layer_nodes = nodes_by_layer.get(layer, [])
            if not layer_nodes:
                continue

            candidate_layers = self.layer_connection_map.get(layer, {layer})
            for target_layer in sorted(candidate_layers, key=layer_index):
                target_nodes = nodes_by_layer.get(target_layer)
                if not target_nodes:
                    continue

                if layer is not None and target_layer is not None:
                    if layer_index(layer) > layer_index(target_layer):
                        continue

                entries_layer = get_entries(layer)
                if layer == target_layer:
                    connect_same_layer(entries_layer)
                else:
                    entries_target = get_entries(target_layer)
                    connect_cross_layer(entries_layer, entries_target)


    def build_edges_virtual(self):
        """
        Build virtual edges to capture long-distance coupling (Section IV)

        Virtual edges are added between nodes on the same layer whose planar
        distance exceeds the regular edge threshold but lies within the
        virtual edge threshold and have no blocking conductors between them.
        """
        if not self.use_virtual_edges:
            return

        virtual_edge_count = 0

        # Group nodes by layer
        nodes_by_layer = defaultdict(list)
        for node in self.nodes:
            nodes_by_layer[node.layer].append(node)

        regular_pairs = {
            tuple(sorted((edge.source_id, edge.target_id)))
            for edge in self.edges
            if not edge.is_virtual
        }
        existing_pairs = set(regular_pairs)

        # Layer-aware same-layer virtual edges (Fig. 10)
        for layer, nodes in nodes_by_layer.items():
            if layer is None:
                continue
            for i, node_a in enumerate(nodes):
                for node_b in nodes[i+1:]:
                    pair_key = tuple(sorted((node_a.node_id, node_b.node_id)))
                    if pair_key in existing_pairs:
                        continue

                    planar_distance = self._planar_distance(node_a, node_b)
                    if not (self.edge_threshold < planar_distance <= self.virtual_edge_threshold):
                        continue

                    if self._has_same_layer_blocker(node_a, node_b, nodes):
                        continue

                    distance, coord_diff = self.calculate_edge_features(node_a, node_b)
                    edge = GraphEdge(
                        source_id=node_a.node_id,
                        target_id=node_b.node_id,
                        distance=distance,
                        coord_diff=coord_diff,
                        is_virtual=True,
                    )
                    self.edges.append(edge)
                    existing_pairs.add(pair_key)
                    virtual_edge_count += 1


    def _validate_no_skip_layer_edges(self) -> None:
        """Remove any edges that violate the cross-layer hop policy"""
        bad_edges = [
            edge for edge in self.edges
            if self._exceeds_layer_hops(
                self.nodes[edge.source_id].layer,
                self.nodes[edge.target_id].layer,
            )
        ]
        if not bad_edges:
            return

        self.edges = [
            edge for edge in self.edges
            if not self._exceeds_layer_hops(
                self.nodes[edge.source_id].layer,
                self.nodes[edge.target_id].layer,
            )
        ]

    def build_graph_from_parsed_data(self, parsed_data: ParsedCap3DData):
        """Build graph from parsed CAP3D data"""

        # Reset state
        self.nodes = []
        self.edges = []
        self.node_id_counter = 0
        self.cap3d_layers = {idx: layer for idx, layer in enumerate(parsed_data.layers)}

        # Process blocks (only conductors for capacitance extraction)
        conductor_blocks = [b for b in parsed_data.blocks if b.type == 'conductor']

        # Identify ground conductor as the one with the lowest Z coordinate
        ground_net_name = None
        lowest_z = float('inf')

        for block in conductor_blocks:
            try:
                # Get the Z coordinate of the block base (bottom of the block)
                base_z = float(block.base[2])
                if base_z < lowest_z:
                    lowest_z = base_z
                    ground_net_name = block.parent_name
            except Exception:
                continue

        if ground_net_name:
            logger.debug("Identified ground conductor %s at Z=%s", ground_net_name, lowest_z)

        # Group blocks by net (parent_name) to handle overlaps properly, skipping ground conductor
        blocks_by_net = defaultdict(list)
        skipped_ground_blocks = 0
        for block in conductor_blocks:
            net_name = block.parent_name or "unknown_net"
            if net_name == ground_net_name:
                skipped_ground_blocks += 1
                continue
            blocks_by_net[net_name].append(block)

        if skipped_ground_blocks > 0:
            logger.debug("Skipped %s ground conductor blocks", skipped_ground_blocks)


        total_blocks_before = sum(len(blocks) for blocks in blocks_by_net.values())
        processed_nets = 0

        # Track decomposed blocks for visualization
        decomposed_blocks_by_net = {}

        for net_name, net_blocks in blocks_by_net.items():
            processed_nets += 1
            # Decompose this net's blocks using simple subdivision
            sub_cuboids = self.decompose_net_simple(net_blocks, net_name)

            # Store decomposed blocks for visualization
            decomposed_blocks_by_net[net_name] = sub_cuboids

            # Create nodes from decomposed cuboids
            for sub_block in sub_cuboids:
                node = self.block_to_node(sub_block)
                self.nodes.append(node)


        # Prepare per-layer metadata for edge construction
        self._prepare_layer_metadata()

        # Verify dimensions
        self._verify_decomposed_block_dimensions(decomposed_blocks_by_net)

        # Build edges
        self.build_edges_regular()
        self.build_edges_virtual()
        self._validate_no_skip_layer_edges()

        # Statistics
        regular_edges = sum(1 for e in self.edges if not e.is_virtual)
        virtual_edges = sum(1 for e in self.edges if e.is_virtual)

    def to_pytorch_geometric(self) -> Optional['Data']:
        """
        Convert graph to PyTorch Geometric Data object

        Returns:
            PyTorch Geometric Data object with:
            - x: Node features [num_nodes, 3] (x_len, y_len, z_len)
            - edge_index: Edge connectivity [2, num_edges]
            - edge_attr: Edge features [num_edges, 7]
            - edge_is_virtual: Boolean mask [num_edges]
            - node_net_names: List of net names for each node
            - node_cuboid_ids: List of cuboid IDs
            - net_names: Sorted unique net names present in the graph
            - node_net_index: Net index per node (aligned with node ordering)
            - edge_net_index: Net indices for each directed edge (2, num_edges)
            - canonical_edge_mask: Boolean mask of undirected/canonical edges
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available. Cannot create Data object.")

        # Node features: (x_len, y_len, z_len)
        x = torch.tensor(
            [list(node.dimensions) for node in self.nodes],
            dtype=torch.float32
        )

        # Edge index and attributes (duplicate entries for undirected graph)
        edge_pairs = []
        edge_features = []
        edge_virtual_flags = []
        for edge in self.edges:
            attr = [edge.distance] + list(edge.coord_diff)
            edge_pairs.append((edge.source_id, edge.target_id))
            edge_pairs.append((edge.target_id, edge.source_id))
            edge_features.append(attr)
            edge_features.append(attr)
            edge_virtual_flags.extend([edge.is_virtual, edge.is_virtual])

        if edge_pairs:
            edge_index = torch.tensor(edge_pairs, dtype=torch.long).t().contiguous()
            edge_attr = torch.tensor(edge_features, dtype=torch.float32)
            edge_is_virtual = torch.tensor(edge_virtual_flags, dtype=torch.bool)
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)
            edge_attr = torch.empty((0, 7), dtype=torch.float32)
            edge_is_virtual = torch.empty((0,), dtype=torch.bool)

        # Net metadata for downstream label alignment
        net_names = sorted({node.net_name for node in self.nodes})
        net_index = {name: idx for idx, name in enumerate(net_names)}
        node_net_index = torch.tensor([net_index[node.net_name] for node in self.nodes], dtype=torch.long)

        if edge_index.numel():
            edge_net_index = torch.stack(
                (
                    node_net_index[edge_index[0]],
                    node_net_index[edge_index[1]],
                ),
                dim=0,
            )
            canonical_edge_mask = edge_index[0] <= edge_index[1]
        else:
            edge_net_index = torch.empty((2, 0), dtype=torch.long)
            canonical_edge_mask = torch.empty((0,), dtype=torch.bool)

        # Create Data object
        data = Data(
            x=x,
            edge_index=edge_index,
            edge_attr=edge_attr,
            edge_is_virtual=edge_is_virtual,
        )

        # Store additional metadata as attributes
        data.node_net_names = [node.net_name for node in self.nodes]
        data.node_cuboid_ids = [node.cuboid_id for node in self.nodes]
        data.node_centers = torch.tensor([list(node.center) for node in self.nodes], dtype=torch.float32)
        data.node_layers = [node.layer for node in self.nodes]
        data.net_names = net_names
        data.node_net_index = node_net_index
        data.edge_net_index = edge_net_index
        data.canonical_edge_mask = canonical_edge_mask

        return data

    def save_graph(self, data: 'Data', output_path: str, metadata: Optional[Dict] = None) -> Dict:
        """Save graph to .pt file and return aggregated metadata."""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available. Cannot save graph.")

        # Save torch data
        torch.save(data, output_path)

        enriched = dict(metadata or {})
        enriched.update({
            'num_nodes': len(self.nodes),
            'num_edges': len(self.edges),
            'num_regular_edges': sum(1 for e in self.edges if not e.is_virtual),
            'num_virtual_edges': sum(1 for e in self.edges if e.is_virtual),
            'node_feature_dim': 3,
            'edge_feature_dim': 7,
            'cuboid_max_length': self.cuboid_max_length,
            'edge_threshold': self.edge_threshold,
            'virtual_edge_threshold': self.virtual_edge_threshold,
        })
        return enriched


def chunk_layout(
    parsed_data: ParsedCap3DData,
    window_size: float = 20.0
) -> List[Tuple[float, float, List[Block]]]:
    """
    Chunk layout into windows for training data generation

    Returns:
        List of (x_center, y_center, blocks_in_window)
    """
    if not parsed_data.window:
        return []

    # Get window bounds
    x_min = min(parsed_data.window.v1[0], parsed_data.window.v2[0])
    x_max = max(parsed_data.window.v1[0], parsed_data.window.v2[0])
    y_min = min(parsed_data.window.v1[1], parsed_data.window.v2[1])
    y_max = max(parsed_data.window.v1[1], parsed_data.window.v2[1])

    # Calculate number of windows
    n_x = int((x_max - x_min) / window_size)
    n_y = int((y_max - y_min) / window_size)


    chunks = []
    for i in range(n_x):
        for j in range(n_y):
            # Window boundaries
            wx_min = x_min + i * window_size
            wx_max = wx_min + window_size
            wy_min = y_min + j * window_size
            wy_max = wy_min + window_size

            # Find blocks in this window
            blocks_in_window = []
            for block in parsed_data.blocks:
                if block.type != 'conductor':
                    continue

                # Check if block intersects window
                bx, by, bz = block.center
                if wx_min <= bx <= wx_max and wy_min <= by <= wy_max:
                    blocks_in_window.append(block)

            if blocks_in_window:  # Only add non-empty chunks
                center_x = (wx_min + wx_max) / 2
                center_y = (wy_min + wy_max) / 2
                chunks.append((center_x, center_y, blocks_in_window))

    return chunks


def convert_window(
    cap3d_path: Path,
    tech_path: Path,
    *,
    output_dir: Optional[Path] = None,
    window_size: float = 20.0,
    cuboid_max_length: Optional[float] = None,
    edge_threshold: Optional[float] = None,
    virtual_edge_threshold: Optional[float] = None,
    use_virtual_edges: bool = True,
    chunk_windows: bool = False,
    num_chunks: Optional[int] = None,
    dataset_dirs: Optional[Dict[str, Path]] = None,
) -> List[Path]:
    """
    Convert a CAP3D window into GNN-Cap graph representation(s).

    Args:
        cap3d_path: Input CAP3D file.
        tech_path: Technology stack YAML describing conductor/dielectric order.
        output_dir: Destination directory for generated PT files (defaults to datasets/graphs).
        window_size: Chunk window size (μm) when chunking is enabled.
        cuboid_max_length: Maximum cuboid length (μm). Defaults to process-node presets.
        edge_threshold: Regular edge threshold (μm). Defaults to process-node presets.
        virtual_edge_threshold: Virtual edge threshold (μm). Defaults to process-node presets.
        use_virtual_edges: Enable/disable virtual edges.
        chunk_windows: If True, generate chunked graphs instead of a single full layout.
        num_chunks: Optional limit on number of chunks when chunking is enabled.

    Returns:
        List of generated graph paths.
    """
    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch and PyTorch Geometric are required for GNN conversion.")

    cap3d_path = Path(cap3d_path)
    tech_path = Path(tech_path)
    process_node: Optional[str] = None

    try:
        process_node = extract_process_node_from_path(tech_path).lower()
    except ValueError as exc:
        process_node = None
        logger.debug("Process node detection failed for %s: %s", tech_path, exc)

    # Auto-detect process node and use dataset-specific directories if no output specified
    if output_dir is None:
        if dataset_dirs is None:
            if process_node:
                dataset_dirs = get_dataset_subdirs(DATASET_ROOT / f"{process_node}/small")
                output_dir = dataset_dirs['graphs']
            else:
                # Fallback to old behavior
                dataset_dirs = get_dataset_subdirs()
                output_dir = GRAPHS_DIR
        else:
            # Use passed dataset_dirs to determine output directory
            output_dir = dataset_dirs['graphs']

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    resolved_params = dict(DEFAULT_GRAPH_PARAMS)
    if process_node and process_node in PROCESS_NODE_GRAPH_PARAMS:
        resolved_params.update(PROCESS_NODE_GRAPH_PARAMS[process_node])
    elif process_node:
        logger.debug(
            "No process-specific graph parameters found for '%s'; using defaults",
            process_node,
        )

    if cuboid_max_length is not None:
        resolved_params['cuboid_max_length'] = cuboid_max_length
    if edge_threshold is not None:
        resolved_params['edge_threshold'] = edge_threshold
    if virtual_edge_threshold is not None:
        resolved_params['virtual_edge_threshold'] = virtual_edge_threshold

    builder = GNNCapGraphBuilder(
        cuboid_max_length=resolved_params['cuboid_max_length'],
        edge_threshold=resolved_params['edge_threshold'],
        virtual_edge_threshold=resolved_params['virtual_edge_threshold'],
        window_size=window_size,
        use_virtual_edges=use_virtual_edges,
        output_dir=output_dir,
        tech_stack_path=tech_path,
    )

    parsed_data = builder.parse_cap3d(str(cap3d_path))
    base_name = cap3d_path.stem
    generated_paths: List[Path] = []

    if chunk_windows:
        chunks = chunk_layout(parsed_data, window_size)
        if num_chunks and num_chunks < len(chunks):
            import random
            random.seed(42)
            chunks = random.sample(chunks, num_chunks)
        for idx, (cx, cy, blocks) in enumerate(chunks):
            chunk_data = ParsedCap3DData(
                blocks=blocks,
                poly_elements=[],
                layers=parsed_data.layers,
                plate_mediums=parsed_data.plate_mediums,
                window=parsed_data.window,
                task=parsed_data.task,
                stats={'total_blocks': len(blocks)},
            )
            builder.build_graph_from_parsed_data(chunk_data)
            data = builder.to_pytorch_geometric()
            if data is None:
                continue
            output_path = output_dir / f"{base_name}_chunk_{idx}.pt"
            metadata = {
                'chunk_id': idx,
                'window_center': (cx, cy),
                'window_size': window_size,
                'source_file': str(cap3d_path),
            }
            enriched_metadata = builder.save_graph(data, str(output_path), metadata)
            manifest_id = f"{base_name}_chunk_{idx}"
            # Load existing manifest (chunks won't have manifests from window extraction)
            if dataset_dirs and 'manifests' in dataset_dirs:
                manifest_path = dataset_dirs['manifests'] / f"{manifest_id}.yaml"
                if manifest_path.exists():
                    with manifest_path.open("r", encoding="utf-8") as fh:
                        data = yaml.safe_load(fh) or {}
                    manifest = WindowManifest.from_dict(data)
                    logger.debug("Loaded manifest for chunk %s", manifest_id)
                else:
                    logger.debug("Manifest not found for chunk %s (expected for chunks)", manifest_id)
                    manifest = None
            else:
                manifest = load_manifest(manifest_id)

            # GNN metadata validation removed - converter no longer checks manifest metadata
            # Chunk processing simplified - no manifest validation required
            generated_paths.append(output_path)
    else:
        builder.build_graph_from_parsed_data(parsed_data)
        data = builder.to_pytorch_geometric()
        if data is not None:
            output_path = output_dir / f"{base_name}.pt"
            metadata = {
                'source_file': str(cap3d_path),
                'full_layout': True,
            }
            enriched_metadata = builder.save_graph(data, str(output_path), metadata)
            manifest_id = base_name
            # Load existing manifest (should have been created by window extraction)
            if dataset_dirs and 'manifests' in dataset_dirs:
                manifest_path = dataset_dirs['manifests'] / f"{manifest_id}.yaml"
                if manifest_path.exists():
                    with manifest_path.open("r", encoding="utf-8") as fh:
                        data = yaml.safe_load(fh) or {}
                    manifest = WindowManifest.from_dict(data)
                else:
                    logger.debug("Manifest not found for %s (expected at %s)", manifest_id, manifest_path)
                    manifest = None
            else:
                manifest = load_manifest(manifest_id)

            # GNN metadata validation removed - converter no longer checks manifest metadata
            # Main window processing simplified - no manifest validation required
            generated_paths.append(output_path)

    return generated_paths


def main():
    parser = argparse.ArgumentParser(
        description='Convert CAP3D files to GNN-Cap graph format',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('inputs', nargs='+', help='Input .cap3d file(s)')
    parser.add_argument('-o', '--output-dir', default=str(GRAPHS_DIR),
                        help='Output directory for graph files')
    parser.add_argument('--window-size', type=float, default=20.0,
                        help='Window size in micrometers for chunking')
    parser.add_argument('--cuboid-max-length', type=float, default=None,
                        help='Override cuboid max length (μm); defaults to process-node preset')
    parser.add_argument('--edge-threshold', type=float, default=None,
                        help='Override regular edge threshold (μm); defaults to process-node preset')
    parser.add_argument('--virtual-edge-threshold', type=float, default=None,
                        help='Override virtual edge threshold (μm); defaults to process-node preset')
    parser.add_argument('--no-virtual-edges', action='store_true',
                        help='Disable virtual edge construction')
    parser.add_argument('--chunk-layout', action='store_true',
                        help='Chunk layout into sub-windows for training data')
    parser.add_argument('--num-chunks', type=int, default=None,
                        help='Number of random chunks to generate (if chunking)')
    parser.add_argument('--tech', required=True,
                        help='Technology stack YAML describing conductor/dielectric order')

    args = parser.parse_args()

    # Auto-detect process node from tech file and determine dataset directories
    try:
        process_node = extract_process_node_from_path(Path(args.tech))
        dataset_dirs = get_dataset_subdirs(DATASET_ROOT / f"{process_node}/small")
    except ValueError as exc:
        logger.error("Could not determine process node from tech file: %s", exc)
        return 1

    # Initialize progress tracking
    successful_conversions = 0
    failed_conversions = []

    # Process files with progress bar
    pbar = tqdm(args.inputs, desc="Converting CAP3D → GNN Graphs", unit="file",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')

    for cap3d_file in pbar:
        cap3d_path = Path(cap3d_file)
        pbar.set_postfix_str(f"File: {cap3d_path.name}")

        try:
            if not cap3d_path.exists():
                failed_conversions.append((cap3d_file, "File not found"))
                continue

            convert_window(
                cap3d_path,
                Path(args.tech),
                output_dir=Path(args.output_dir) if args.output_dir != str(GRAPHS_DIR) else dataset_dirs['graphs'],
                window_size=args.window_size,
                cuboid_max_length=args.cuboid_max_length,
                edge_threshold=args.edge_threshold,
                virtual_edge_threshold=args.virtual_edge_threshold,
                use_virtual_edges=not args.no_virtual_edges,
                chunk_windows=args.chunk_layout,
                num_chunks=args.num_chunks,
            )
            successful_conversions += 1

        except Exception as exc:
            failed_conversions.append((cap3d_file, str(exc)))
            continue

    # Final status report
    if failed_conversions:
        for filename, error in failed_conversions:
            logger.error("Conversion failed for %s: %s", filename, error)

    return 0 if not failed_conversions else 1


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
CAP3D to CNNCap Density Map Converter

Converts CAP3D files into density maps compatible with CNNCap 3D models.
Creates separate 2D density maps for conductor layers specified in tech file.
Matches CAP3D layers to tech file layers by z-height.

Usage:
    python cap3d_to_cnncap.py ../windows/cap3d/W0.cap3d --tech ../designs/tech/nangate45/nangate45_stack.yaml
    python cap3d_to_cnncap.py input.cap3d --tech tech.yaml --resolution 0.005

Output: one shard-backed density_maps root per dataset split.

Shard structure:
    index.json: split-wide metadata and window->shard mapping
    shards/shard-00000.npz: compressed stacked tensors for 64 windows
"""

import sys
import argparse
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Sequence, Set
from collections import defaultdict
import yaml
from tqdm import tqdm

from capbench._internal.common.density_window_bundle import (
    DensityWindowShardWriter,
    save_density_window_bundle,
    save_density_window_shards,
)
from capbench.preprocess.cap3d_parser import StreamingCap3DParser
from capbench.preprocess.cap3d_models import Block, Layer, Window, ParsedCap3DData
from capbench._internal.common.tech_parser import get_conductor_layers, match_layers_by_height
from capbench._internal.common.datasets import get_dataset_subdirs


DEFAULT_TARGET_SIZE = 224
SCALED_TARGET_SIZES = {
    "small": 128,
    "medium": 256,
    "large": 512,
}
DEFAULT_WINDOWS_PER_SHARD = 64
DEFAULT_SHARD_SHUFFLE_SEED = 0


class DensityMapGenerator:
    """Generate CNNCap-compatible density maps from CAP3D files"""

    def __init__(self, cap3d_file: str, tech_file: str, pixel_resolution: float = None, target_size: int = 224):
        """
        Initialize density map generator

        Args:
            cap3d_file: Path to CAP3D file
            tech_file: Path to technology stack YAML file
            pixel_resolution: Microns per pixel (auto-computed for the selected grid size)
            target_size: Square output grid size in pixels
        """
        self.cap3d_file = Path(cap3d_file)
        self.tech_file = Path(tech_file)
        self.target_size = int(target_size)
        if self.target_size <= 0:
            raise ValueError(f"target_size must be positive, got {self.target_size}")
        self.pixel_resolution = pixel_resolution

        # Tech file data
        self.tech_conductor_layers: List[str] = []
        self.tech_z_heights: Dict[str, float] = {}

        # Parsed data
        self.window: Optional[Window] = None
        self.layers: Dict[int, Layer] = {}  # layer_id -> Layer
        self.layer_order: List[str] = []  # Ordered list of layer names (from CAP3D)
        self.matched_layers: List[str] = []  # Matched conductor layers to process
        self.blocks_by_layer: Dict[str, List[Block]] = defaultdict(list)
        self.conductor_names: Dict[str, str] = {}  # conductor_name -> actual name

        # Grid parameters (computed after parsing)
        self.x_min: float = 0.0
        self.y_min: float = 0.0
        self.x_max: float = 0.0
        self.y_max: float = 0.0
        self.width_pixels: int = 0
        self.height_pixels: int = 0
        self.source_window_bounds: Optional[Tuple[float, float, float, float, float, float]] = None
        self.raster_trim_applied: bool = False

        # Density maps: layer_name -> (density_map, id_map)
        self.density_maps: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}

        # Conductor metadata for YAML output
        self.conductor_metadata: List[Dict] = []

        # Conductor ID mapping (populated during density map generation)
        self.conductor_id_map: Dict[str, int] = {}
        self.via_layers: List[str] = []
        self.layer_z_tops: Dict[str, float] = {}

    def parse_tech_file(self):
        """Parse technology file to extract conductor layers"""
        self.tech_conductor_layers, self.tech_z_heights = get_conductor_layers(str(self.tech_file))

    def parse_cap3d(self):
        """Parse CAP3D file and extract structure"""
        parser = StreamingCap3DParser(str(self.cap3d_file))
        parsed_data = parser.parse_complete()

        # Extract window bounds
        if parsed_data.window:
            self.window = parsed_data.window
            # Set grid bounds from window
            self.x_min = min(self.window.v1[0], self.window.v2[0])
            self.y_min = min(self.window.v1[1], self.window.v2[1])
            self.x_max = max(self.window.v1[0], self.window.v2[0])
            self.y_max = max(self.window.v1[1], self.window.v2[1])

        # CAP3D block.layer stores the explicit <layer> id, not the list position.
        self.layers = {
            int(getattr(layer, "id", idx)): layer
            for idx, layer in enumerate(parsed_data.layers)
        }

        # Maintain layer order
        self.layer_order = [layer.name for layer in parsed_data.layers]

        # Identify ground conductor as the conductor with the lowest Z coordinate
        conductor_blocks = [b for b in parsed_data.blocks if b.type == 'conductor']
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

        # Store ground conductor name for use in other methods
        self.ground_net_name = ground_net_name

        # Extract blocks and organize by layer
        for block in parsed_data.blocks:
            # Determine layer name from layer attribute
            if block.layer is not None and block.layer in self.layers:
                layer_name = self.layers[block.layer].name
            else:
                # For blocks without layer ID, use parent name
                layer_name = block.parent_name or "unknown"

            self.blocks_by_layer[layer_name].append(block)

            # Track conductor names (skip ground conductor)
            if block.parent_name and block.parent_name != ground_net_name:
                self.conductor_names[block.parent_name] = block.parent_name

        # If no window was defined, compute bounds from blocks
        if not self.window:
            self._compute_bounds_from_blocks()

        # Compute grid dimensions for the selected square output size
        width_um = self.x_max - self.x_min
        height_um = self.y_max - self.y_min

        # Auto-compute pixel resolution to fit the chosen grid
        if self.pixel_resolution is None:
            # Use max dimension to determine resolution
            max_dim = max(width_um, height_um)
            self.pixel_resolution = max_dim / self.target_size

        self.width_pixels = self.target_size
        self.height_pixels = self.target_size

    def tighten_raster_bounds_to_conductors(
        self,
        selected_layers: Optional[Sequence[str]] = None,
    ) -> bool:
        """Remove legacy CAP3D window margins by rasterizing around conductor geometry."""
        try:
            x_min, y_min, x_max, y_max = self.compute_conductor_bounds(selected_layers=selected_layers)
        except ValueError:
            return False

        width_um = float(x_max - x_min)
        height_um = float(y_max - y_min)
        max_dim = max(width_um, height_um)
        if max_dim <= 0.0:
            return False

        if self.window is not None:
            self.source_window_bounds = (
                float(min(self.window.v1[0], self.window.v2[0])),
                float(min(self.window.v1[1], self.window.v2[1])),
                float(min(self.window.v1[2], self.window.v2[2])),
                float(max(self.window.v1[0], self.window.v2[0])),
                float(max(self.window.v1[1], self.window.v2[1])),
                float(max(self.window.v1[2], self.window.v2[2])),
            )
        else:
            self.source_window_bounds = None

        if width_um < max_dim:
            pad_x = 0.5 * (max_dim - width_um)
            x_min -= pad_x
            x_max += pad_x
        if height_um < max_dim:
            pad_y = 0.5 * (max_dim - height_um)
            y_min -= pad_y
            y_max += pad_y

        self.set_raster_bounds(x_min, y_min, x_max, y_max, pixel_resolution=None)
        self.raster_trim_applied = True
        return True

    def set_raster_bounds(
        self,
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
        *,
        pixel_resolution: float | None = None,
    ) -> None:
        if not np.isfinite([x_min, y_min, x_max, y_max]).all():
            raise ValueError("Raster bounds must be finite.")
        if x_max <= x_min or y_max <= y_min:
            raise ValueError(f"Invalid raster bounds: {(x_min, y_min, x_max, y_max)}")

        self.x_min = float(x_min)
        self.y_min = float(y_min)
        self.x_max = float(x_max)
        self.y_max = float(y_max)

        width_um = self.x_max - self.x_min
        height_um = self.y_max - self.y_min
        if pixel_resolution is None:
            max_dim = max(width_um, height_um)
            self.pixel_resolution = max_dim / self.target_size
        else:
            self.pixel_resolution = float(pixel_resolution)

        self.width_pixels = self.target_size
        self.height_pixels = self.target_size

    def compute_conductor_bounds(self, selected_layers: Optional[Sequence[str]] = None) -> Tuple[float, float, float, float]:
        layer_filter = set(selected_layers) if selected_layers is not None else None
        x_coords: List[float] = []
        y_coords: List[float] = []

        for layer_name, blocks in self.blocks_by_layer.items():
            if layer_filter is not None and layer_name not in layer_filter:
                continue
            for block in blocks:
                if not block.parent_name or block.parent_name not in self.conductor_names:
                    continue

                bp = block.base
                v1 = block.v1
                v2 = block.v2
                x_coords.extend([
                    bp[0],
                    bp[0] + v1[0],
                    bp[0] + v2[0],
                    bp[0] + v1[0] + v2[0],
                ])
                y_coords.extend([
                    bp[1],
                    bp[1] + v1[1],
                    bp[1] + v2[1],
                    bp[1] + v1[1] + v2[1],
                ])

        if not x_coords or not y_coords:
            raise ValueError(f"No conductor geometry found in {self.cap3d_file} for selected layers {selected_layers}")
        return min(x_coords), min(y_coords), max(x_coords), max(y_coords)

    def match_layers(self):
        """Match CAP3D layers to tech file layers by z-height"""
        cap3d_conductor_layers: List[str] = []
        cap3d_z_heights: Dict[str, float] = {}
        self.layer_z_tops: Dict[str, float] = {}

        excluded_types = {'dielectric', 'substrate'}
        tech_layer_keys = {_normalize_layer_name(name): name for name in self.tech_conductor_layers}
        seen_layer_names: Set[str] = set()

        # Pre-compute z-top for every layer we encounter
        for layer in self.layers.values():
            blocks = self.blocks_by_layer.get(layer.name, [])
            z_top = None
            if blocks:
                try:
                    z_top = blocks[0].base[2] + blocks[0].hvec[2]
                except Exception:
                    z_top = None
            self.layer_z_tops[layer.name] = z_top

        for layer in self.layers.values():
            layer_type = (layer.type or "").lower()
            if layer_type in excluded_types:
                continue

            normalized_name = _normalize_layer_name(layer.name)
            if normalized_name not in tech_layer_keys:
                continue

            if layer.name in seen_layer_names:
                continue

            if self.ground_net_name and layer.name == self.ground_net_name:
                continue

            z_top = self.layer_z_tops.get(layer.name)
            if z_top is None:
                tech_ref = tech_layer_keys.get(normalized_name)
                z_top = self.tech_z_heights.get(tech_ref, 0.0)

            cap3d_conductor_layers.append(layer.name)
            cap3d_z_heights[layer.name] = z_top
            seen_layer_names.add(layer.name)

        matched_pairs, warnings = match_layers_by_height(
            self.tech_conductor_layers,
            self.tech_z_heights,
            cap3d_conductor_layers,
            cap3d_z_heights,
            tolerance=1e-4
        )

        if not matched_pairs:
            raise ValueError("No layers matched between tech file and CAP3D file!")

        seen_layers = set()
        unique_layers: List[str] = []
        for _, cap3d_name in matched_pairs:
            if cap3d_name not in seen_layers:
                unique_layers.append(cap3d_name)
                seen_layers.add(cap3d_name)

        def layer_sort_key(layer_name: str) -> Tuple[float, str]:
            z_top = cap3d_z_heights.get(layer_name)
            if z_top is None:
                z_top = float('inf')
            return (z_top, layer_name.lower())

        self.matched_layers = sorted(unique_layers, key=layer_sort_key)

        if not self.matched_layers:
            raise ValueError("No layers matched between tech file and CAP3D file!")

        via_layers: List[str] = []
        seen_vias: Set[str] = set()
        for layer in self.layers.values():
            layer_type = (layer.type or "").lower()
            lname = layer.name
            if lname in seen_vias:
                continue
            if "via" not in layer_type and not lname.lower().startswith("via"):
                continue
            if lname not in self.blocks_by_layer:
                continue
            via_layers.append(lname)
            seen_vias.add(lname)

        def via_sort_key(layer_name: str) -> Tuple[float, str]:
            z_top = self.layer_z_tops.get(layer_name)
            if z_top is None:
                z_top = float('inf')
            return (z_top, layer_name.lower())

        self.via_layers = sorted(via_layers, key=via_sort_key)

    def _compute_bounds_from_blocks(self):
        """Compute bounding box from all blocks"""
        x_coords = []
        y_coords = []

        for blocks in self.blocks_by_layer.values():
            for block in blocks:
                # Get all corners of the block
                bp = block.base
                v1 = block.v1
                v2 = block.v2

                corners = [
                    (bp[0], bp[1]),
                    (bp[0] + v1[0], bp[1] + v1[1]),
                    (bp[0] + v2[0], bp[1] + v2[1]),
                    (bp[0] + v1[0] + v2[0], bp[1] + v1[1] + v2[1]),
                ]

                for x, y in corners:
                    x_coords.append(x)
                    y_coords.append(y)

        self.x_min = min(x_coords)
        self.y_min = min(y_coords)
        self.x_max = max(x_coords)
        self.y_max = max(y_coords)

    def generate_density_maps(self):
        """Generate density and ID maps for matched conductor layers"""
        # Use tech file layer order which already includes interleaved vias
        layer_order = self.tech_conductor_layers  # This now contains interleaved metal+via layers

        for layer_name in layer_order:
            density_map = np.zeros((self.height_pixels, self.width_pixels), dtype=np.float64)
            id_map = np.zeros((self.height_pixels, self.width_pixels), dtype=np.int32)
            self.density_maps[layer_name] = (density_map, id_map)

        # Skip GROUND layer (same as SUBSTRATE, always full)

        # Assign conductor IDs (store as instance variable for NPZ export)
        self.conductor_id_map = {}
        next_id = 1

        for conductor_name in sorted(self.conductor_names.keys()):
            self.conductor_id_map[conductor_name] = next_id
            next_id += 1

        # Rasterize blocks onto density maps
        total_blocks = sum(len(blocks) for blocks in self.blocks_by_layer.values())
        processed = 0

        for layer_name, blocks in self.blocks_by_layer.items():
            if layer_name not in self.density_maps:
                continue

            density_map, id_map = self.density_maps[layer_name]

            for block in blocks:
                self._rasterize_block(block, density_map, id_map, self.conductor_id_map)
                processed += 1

        # Generate conductor metadata
        self._generate_conductor_metadata(self.conductor_id_map)

    def _rasterize_block(
        self,
        block: Block,
        density_map: np.ndarray,
        id_map: np.ndarray,
        conductor_id_map: Dict[str, int]
    ):
        """
        Rasterize a single block onto the density and ID maps

        Args:
            block: Block to rasterize
            density_map: Density map array to fill
            id_map: ID map array to fill
            conductor_id_map: Mapping from conductor names to IDs
        """
        # Get block bounds in world coordinates
        bp = block.base
        v1 = block.v1
        v2 = block.v2

        # Calculate block corners (2D projection, ignoring Z)
        x_coords = [
            bp[0],
            bp[0] + v1[0],
            bp[0] + v2[0],
            bp[0] + v1[0] + v2[0]
        ]
        y_coords = [
            bp[1],
            bp[1] + v1[1],
            bp[1] + v2[1],
            bp[1] + v1[1] + v2[1]
        ]

        block_x_min = min(x_coords)
        block_x_max = max(x_coords)
        block_y_min = min(y_coords)
        block_y_max = max(y_coords)

        # Convert to pixel coordinates
        px_min = int(np.floor((block_x_min - self.x_min) / self.pixel_resolution))
        px_max = int(np.ceil((block_x_max - self.x_min) / self.pixel_resolution))
        py_min = int(np.floor((block_y_min - self.y_min) / self.pixel_resolution))
        py_max = int(np.ceil((block_y_max - self.y_min) / self.pixel_resolution))

        # Clamp to grid bounds
        px_min = max(0, px_min)
        px_max = min(self.width_pixels, px_max)
        py_min = max(0, py_min)
        py_max = min(self.height_pixels, py_max)

        # Get conductor ID
        conductor_id = 0
        if block.parent_name and block.parent_name in conductor_id_map:
            conductor_id = conductor_id_map[block.parent_name]

        # Fill density map (set to 1.0 for occupied pixels)
        # Use y as first index (row), x as second index (col) for numpy convention
        density_map[py_min:py_max, px_min:px_max] = 1.0

        # Fill ID map (only if conductor ID is non-zero)
        if conductor_id > 0:
            id_map[py_min:py_max, px_min:px_max] = conductor_id

    def _generate_conductor_metadata(self, conductor_id_map: Dict[str, int]):
        """Generate conductor metadata with sample positions"""
        for conductor_name, conductor_id in sorted(conductor_id_map.items(), key=lambda x: x[1]):
            # Find a sample position for this conductor in any layer
            sample_pos = None
            sample_layer = None

            for layer_name, (density_map, id_map) in self.density_maps.items():
                # Find first pixel with this conductor ID
                positions = np.argwhere(id_map == conductor_id)
                if len(positions) > 0:
                    # Use centroid as sample position
                    centroid = positions.mean(axis=0).astype(int)
                    sample_pos = [int(centroid[1]), int(centroid[0])]  # [x, y] in pixel coords
                    sample_layer = layer_name
                    break

            if sample_pos and sample_layer:
                self.conductor_metadata.append({
                    'name': conductor_name,
                    'conductor_id': int(conductor_id),
                    'layer': sample_layer,
                    'sample_position': sample_pos
                })

    def save_bundle(self, output_dir: str | Path) -> Path:
        """Write one single-window shard-backed density dataset."""
        output_path = Path(output_dir)
        payload = self.build_bundle_data()
        return save_density_window_bundle(output_path, **payload)

    def build_bundle_data(self) -> Dict[str, object]:
        """Build one window payload without writing it to disk."""
        layer_list = list(self.tech_conductor_layers)
        density = np.zeros((len(layer_list), self.height_pixels, self.width_pixels), dtype=np.float32)
        id_maps = np.zeros((len(layer_list), self.height_pixels, self.width_pixels), dtype=np.int32)
        layer_has_density: List[bool] = []

        for layer_idx, layer_name in enumerate(layer_list):
            layer_payload = self.density_maps.get(layer_name)
            if layer_payload is None:
                layer_has_density.append(False)
                continue

            density_map, id_map = layer_payload
            density[layer_idx] = np.asarray(density_map, dtype=np.float32)
            id_maps[layer_idx] = np.asarray(id_map, dtype=np.int32)
            layer_has_density.append(bool(np.any(density_map)))

        z_min = self.window.v1[2] if self.window else 0.0
        z_max = self.window.v2[2] if self.window else 0.0

        return {
            "window_id": self.window.name if self.window else self.cap3d_file.stem,
            "layer_names": layer_list,
            "layer_has_density": layer_has_density,
            "density": density,
            "id_maps": id_maps,
            "conductor_id_map": dict(self.conductor_id_map),
            "window_bounds": [
                float(self.x_min),
                float(self.y_min),
                float(z_min),
                float(self.x_max),
                float(self.y_max),
                float(z_max),
            ],
            "pixel_resolution": float(self.pixel_resolution),
            "raster_trim_applied": bool(self.raster_trim_applied),
            "source_window_bounds": (
                None
                if self.source_window_bounds is None
                else [float(v) for v in self.source_window_bounds]
            ),
        }

    def save_metadata_yaml(self, output_file: str):
        """Save conductor metadata to YAML file"""
        output_path = Path(output_file)
        metadata = self.build_metadata_dict()

        with output_path.open('w') as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

    # CNN metadata validation function removed - converter no longer checks manifest metadata

    def build_metadata_dict(self) -> Dict:
        """Build metadata dictionary without writing to disk."""
        layers_list = list(self.matched_layers)

        metadata = {
            'window_name': self.window.name if self.window else self.cap3d_file.stem,
            'pixel_resolution': float(self.pixel_resolution),
            'raster_trim_applied': bool(self.raster_trim_applied),
            'grid_size': {
                'width': int(self.width_pixels),
                'height': int(self.height_pixels)
            },
            'window_bounds': {
                'x_min': float(self.x_min),
                'y_min': float(self.y_min),
                'x_max': float(self.x_max),
                'y_max': float(self.y_max)
            },
            'layers': layers_list,
            'conductors': self.conductor_metadata
        }

        if self.source_window_bounds is not None:
            metadata['source_window_bounds'] = {
                'x_min': float(self.source_window_bounds[0]),
                'y_min': float(self.source_window_bounds[1]),
                'z_min': float(self.source_window_bounds[2]),
                'x_max': float(self.source_window_bounds[3]),
                'y_max': float(self.source_window_bounds[4]),
                'z_max': float(self.source_window_bounds[5]),
            }

        return metadata


def _coarsen_density_map(density_map: np.ndarray, target_size: int) -> np.ndarray:
    """Down-sample a density map to a coarse grid using averaging."""
    height, width = density_map.shape
    target_size = max(1, int(target_size))

    y_bins = np.linspace(0, height, target_size + 1, dtype=int)
    x_bins = np.linspace(0, width, target_size + 1, dtype=int)
    coarse = np.zeros((target_size, target_size), dtype=np.float64)

    for yi in range(target_size):
        y0, y1 = y_bins[yi], y_bins[yi + 1]
        if y0 == y1:
            continue
        for xi in range(target_size):
            x0, x1 = x_bins[xi], x_bins[xi + 1]
            if x0 == x1:
                continue
            tile = density_map[y0:y1, x0:x1]
            coarse[yi, xi] = tile.mean() if tile.size > 0 else 0.0

    return coarse


def generate_coarse_plot(
    window_label: str,
    generator: DensityMapGenerator,
    output_path: Path,
    coarse_size: int,
    dpi: int
):
    """Generate a coarse-grid visualization for all layers in the generator."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        from matplotlib import pyplot as plt
    except ImportError:
        return

    layers = [layer for layer in generator.matched_layers if layer in generator.density_maps]
    if not layers:
        return

    n_layers = len(layers)
    n_cols = min(4, n_layers)
    n_rows = (n_layers + n_cols - 1) // n_cols

    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(4.5 * n_cols, 4.5 * n_rows),
        constrained_layout=True
    )
    axes = np.atleast_2d(axes)

    last_image = None
    for idx, layer_name in enumerate(layers):
        ax = axes[idx // n_cols, idx % n_cols]
        density_map, _ = generator.density_maps[layer_name]
        coarse_map = _coarsen_density_map(density_map, coarse_size)

        im = ax.imshow(
            coarse_map,
            cmap='Greys_r',
            vmin=0.0,
            vmax=1.0,
            origin='lower',
            interpolation='nearest'
        )
        last_image = im

        ax.set_xticks(np.arange(-0.5, coarse_size, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, coarse_size, 1), minor=True)
        ax.grid(which='minor', color='black', linewidth=0.3, alpha=0.25)
        ax.tick_params(which='both', bottom=False, left=False, labelbottom=False, labelleft=False)
        ax.set_title(layer_name)

    for idx in range(n_layers, n_rows * n_cols):
        axes[idx // n_cols, idx % n_cols].axis('off')

    if last_image is not None:
        fig.colorbar(
            last_image,
            ax=axes[:n_rows, :n_cols].ravel().tolist(),
            shrink=0.85,
            pad=0.04,
            label='Average density (darker = higher)'
        )

    fig.suptitle(f'{window_label} - CNNCap Coarse Density Grid', fontsize=14, y=1.02)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description='Convert CAP3D files to CNNCap density maps',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cap3d_to_cnncap.py windows/W0.cap3d --tech designs/tech/nangate45/nangate45_stack.yaml
  python cap3d_to_cnncap.py windows/W0.cap3d windows/W1.cap3d --tech designs/tech/nangate45/nangate45_stack.yaml --plot
  python cap3d_to_cnncap.py windows/W0.cap3d windows/W1.cap3d ... windows/W9.cap3d --tech tech.yaml --output batch_density_maps
        """
    )

    parser.add_argument('inputs', nargs='+', help='Input CAP3D file(s)')
    parser.add_argument('-t', '--tech', required=True, help='Technology stack YAML file (required)')
    parser.add_argument(
        '-o',
        '--output',
        help='Output density_maps root (single input may also point at <root>/<window_id>)',
    )
    parser.add_argument('-r', '--resolution', type=float, default=None,
                       help='Pixel resolution in microns (auto-computed for the selected grid size)')
    parser.add_argument(
        '--target-size',
        type=int,
        default=None,
        help='Explicit square output grid size in pixels (default: 224, or size-aware with --scaled-output)',
    )
    parser.add_argument(
        '--scaled-output',
        action='store_true',
        help='Write size-aware grids to density_maps_scaled/ using small=128, medium=256, large=512',
    )
    parser.add_argument('--plot', action='store_true', help='Generate coarse-grid plots for each processed window')
    parser.add_argument('--plot-dir', help='Directory to write plot PNGs (default: output directory)')
    parser.add_argument('--coarse-size', type=int, default=30,
                       help='Coarse grid size for visualization (default: 30)')
    parser.add_argument('--dpi', type=int, default=150,
                       help='DPI for generated plots (default: 150)')

    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs]
    missing = [str(p) for p in input_paths if not p.exists()]
    if missing:
        print(f"ERROR: Input file(s) not found: {', '.join(missing)}", file=sys.stderr)
        return 1

    tech_path = Path(args.tech)
    if not tech_path.exists():
        print(f"ERROR: Tech file not found: {args.tech}", file=sys.stderr)
        return 1

    try:
        tech_layers, tech_z_heights = get_conductor_layers(str(tech_path))
    except Exception as exc:
        print(f"ERROR: Failed to parse tech file: {exc}", file=sys.stderr)
        return 1

    ordered_input_paths = sorted(input_paths, key=lambda path: path.stem)
    if len(ordered_input_paths) > 1:
        rng = np.random.default_rng(DEFAULT_SHARD_SHUFFLE_SEED)
        order = rng.permutation(len(ordered_input_paths))
        ordered_input_paths = [ordered_input_paths[int(idx)] for idx in order]

    # Initialize progress tracking
    successful_conversions = 0
    failed_conversions = []
    output_root: Optional[Path] = None
    shuffle_seed = DEFAULT_SHARD_SHUFFLE_SEED if len(ordered_input_paths) > 1 else None

    for cap3d_path in ordered_input_paths:
        if args.output:
            if len(ordered_input_paths) == 1 and Path(args.output).name == cap3d_path.stem:
                candidate_root = Path(args.output).parent
            else:
                candidate_root = Path(args.output)
        else:
            window_dirs = _resolve_dataset_dirs(cap3d_path)
            output_key = 'density_maps_scaled' if args.scaled_output else 'density_maps'
            candidate_root = window_dirs[output_key]

        candidate_root = Path(candidate_root)
        if output_root is None:
            output_root = candidate_root
        elif output_root.resolve() != candidate_root.resolve():
            print(
                f"ERROR: All inputs must target the same output root; got both "
                f"{output_root} and {candidate_root}",
                file=sys.stderr,
            )
            return 1

    if output_root is None:
        print("ERROR: No output root resolved for CNN conversion", file=sys.stderr)
        return 1

    # Process windows with progress bar
    pbar = tqdm(
        ordered_input_paths,
        desc="Converting CAP3D → Density Maps",
        unit="window",
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]',
    )

    with DensityWindowShardWriter(
        output_root,
        windows_per_shard=DEFAULT_WINDOWS_PER_SHARD,
        window_shuffle_seed=shuffle_seed,
    ) as shard_writer:
        for cap3d_path in pbar:
            window_key = cap3d_path.stem
            pbar.set_postfix_str(f"Window: {window_key}")

            try:
                payload = build_window_bundle_data(
                    cap3d_path,
                    tech_path,
                    pixel_resolution=args.resolution,
                    target_size=args.target_size,
                    scaled_output=args.scaled_output,
                )
                shard_writer.add_window_payload(payload)

                if args.plot:
                    resolved_target_size = _resolve_target_size(
                        cap3d_path,
                        target_size=args.target_size,
                        scaled_output=args.scaled_output,
                    )
                    generator = DensityMapGenerator(
                        str(cap3d_path),
                        str(tech_path),
                        pixel_resolution=args.resolution,
                        target_size=resolved_target_size,
                    )
                    generator.tech_conductor_layers = list(tech_layers)
                    generator.tech_z_heights = dict(tech_z_heights)
                    generator.parse_cap3d()
                    generator.match_layers()
                    generator.tighten_raster_bounds_to_conductors(selected_layers=generator.matched_layers)
                    generator.generate_density_maps()

                    plot_dir = Path(args.plot_dir) if args.plot_dir else output_root
                    plot_dir.mkdir(parents=True, exist_ok=True)
                    plot_path = plot_dir / f'{window_key}_visualization.png'
                    generate_coarse_plot(window_key, generator, plot_path, args.coarse_size, args.dpi)

                successful_conversions += 1

            except Exception as exc:
                failed_conversions.append((window_key, str(exc)))
                continue

        if successful_conversions > 0:
            try:
                shard_writer.finalize()
            except Exception as exc:
                print(f"ERROR: Failed to write shard-backed density maps: {exc}", file=sys.stderr)
                return 1

    # Final status report
    if failed_conversions:
        for window_key, error in failed_conversions:
            print(f"ERROR: Conversion failed for {window_key}: {error}", file=sys.stderr)

    return 0 if not failed_conversions else 1


def _infer_dataset_base(cap3d_path: Path) -> Path:
    """Return the dataset directory that contains the CAP3D file."""
    cap3d_path = Path(cap3d_path)
    cap3d_dir = cap3d_path.parent
    if cap3d_dir.name.lower() == 'cap3d':
        return cap3d_dir.parent
    return cap3d_dir


def _resolve_dataset_dirs(cap3d_path: Path, dataset_dirs: Optional[Dict[str, Path]] = None) -> Dict[str, Path]:
    """
    Return dataset subdirectories for the given CAP3D file.

    Prefers the provided dataset_dirs but falls back to auto-detecting based on the
    CAP3D location (sibling of the cap3d/ directory).
    """
    if dataset_dirs:
        return dataset_dirs
    dataset_base = _infer_dataset_base(cap3d_path)
    return get_dataset_subdirs(dataset_base)


def _infer_window_size_bucket(cap3d_path: Path) -> Optional[str]:
    """Infer the window size bucket from the dataset path."""
    for part in reversed(Path(cap3d_path).parts):
        normalized = str(part).lower()
        if normalized in SCALED_TARGET_SIZES:
            return normalized
    return None


def _resolve_target_size(
    cap3d_path: Path,
    *,
    target_size: Optional[int],
    scaled_output: bool,
) -> int:
    if target_size is not None:
        size = int(target_size)
        if size <= 0:
            raise ValueError(f"target_size must be positive, got {size}")
        return size

    if scaled_output:
        size_bucket = _infer_window_size_bucket(cap3d_path)
        if size_bucket is None:
            raise ValueError(
                f"Could not infer size bucket from path '{cap3d_path}'. "
                f"Expected one of {sorted(SCALED_TARGET_SIZES)} in the dataset path."
            )
        return SCALED_TARGET_SIZES[size_bucket]

    return DEFAULT_TARGET_SIZE


def _normalize_layer_name(name: str) -> str:
    """Normalize layer names for tolerant matching."""
    return ''.join(ch for ch in str(name).lower() if ch.isalnum())


def build_window_bundle_data(
    cap3d_path: Path,
    tech_path: Path,
    *,
    pixel_resolution: Optional[float] = None,
    dataset_dirs: Optional[Dict[str, Path]] = None,
    target_size: Optional[int] = None,
    scaled_output: bool = False,
    selected_layers: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Generate one in-memory window payload without writing it to disk."""
    cap3d_path = Path(cap3d_path)
    tech_path = Path(tech_path)

    _dataset_dirs = _resolve_dataset_dirs(cap3d_path, dataset_dirs)
    resolved_target_size = _resolve_target_size(
        cap3d_path,
        target_size=target_size,
        scaled_output=scaled_output,
    )

    generator = DensityMapGenerator(
        str(cap3d_path),
        str(tech_path),
        pixel_resolution=pixel_resolution,
        target_size=resolved_target_size,
    )
    tech_layers, tech_z_heights = get_conductor_layers(str(tech_path))
    if selected_layers is not None:
        requested = {_normalize_layer_name(layer) for layer in selected_layers}
        tech_layers = [layer for layer in tech_layers if _normalize_layer_name(layer) in requested]
        tech_z_heights = {layer: tech_z_heights[layer] for layer in tech_layers}
    generator.tech_conductor_layers = list(tech_layers)
    generator.tech_z_heights = dict(tech_z_heights)

    generator.parse_cap3d()
    generator.match_layers()
    generator.tighten_raster_bounds_to_conductors(selected_layers=generator.matched_layers)
    generator.generate_density_maps()
    return generator.build_bundle_data()


def save_window_bundle_data(
    output_root: Path | str,
    window_payloads: Sequence[Dict[str, object]],
    *,
    windows_per_shard: int = DEFAULT_WINDOWS_PER_SHARD,
    shuffle_windows: bool = True,
    shuffle_seed: int = DEFAULT_SHARD_SHUFFLE_SEED,
) -> Path:
    """Write one shard-backed density_maps root from precomputed window payloads."""
    return save_density_window_shards(
        output_root,
        window_payloads,
        windows_per_shard=windows_per_shard,
        shuffle_windows=shuffle_windows,
        shuffle_seed=shuffle_seed,
    )


def convert_window(
    cap3d_path: Path,
    tech_path: Path,
    *,
    pixel_resolution: Optional[float] = None,
    output_bundle: Optional[Path] = None,
    plot: bool = False,
    plot_dir: Optional[Path] = None,
    coarse_size: int = 30,
    dpi: int = 150,
    dataset_dirs: Optional[Dict[str, Path]] = None,
    target_size: Optional[int] = None,
    scaled_output: bool = False,
    selected_layers: Optional[Sequence[str]] = None,
) -> Path:
    """
    Generate one single-window shard-backed density dataset (and optional plot).

    Args:
        cap3d_path: Input CAP3D file.
        tech_path: Technology stack YAML describing conductor order.
        pixel_resolution: Microns per pixel for generated density maps.
        output_bundle: Optional override for the output root or virtual window path.
        plot: Whether to emit a coarse visualization.
        plot_dir: Directory for visualization PNGs (default: alongside the density_maps root).
        coarse_size: Coarse grid resolution for visualization.
        dpi: DPI for visualization PNGs.
        target_size: Optional explicit square output grid size.
        scaled_output: Whether to infer 128/256/512 by size bucket and default to density_maps_scaled/.

    Returns:
        Virtual path to the generated window inside the shard-backed root.

    """
    cap3d_path = Path(cap3d_path)
    tech_path = Path(tech_path)

    # Determine dataset directories, defaulting to the CAP3D file's dataset
    dataset_dirs = _resolve_dataset_dirs(cap3d_path, dataset_dirs)
    if output_bundle is None:
        output_key = "density_maps_scaled" if scaled_output else "density_maps"
        output_bundle = dataset_dirs[output_key] / cap3d_path.stem
    output_bundle = Path(output_bundle)
    output_root = output_bundle.parent if output_bundle.name == cap3d_path.stem else output_bundle

    payload = build_window_bundle_data(
        cap3d_path,
        tech_path,
        pixel_resolution=pixel_resolution,
        dataset_dirs=dataset_dirs,
        target_size=target_size,
        scaled_output=scaled_output,
        selected_layers=selected_layers,
    )
    saved_bundle = save_density_window_bundle(output_bundle, **payload)

    if plot:
        resolved_plot_dir = plot_dir or output_root
        resolved_plot_dir.mkdir(parents=True, exist_ok=True)
        plot_path = resolved_plot_dir / f"{cap3d_path.stem}_visualization.png"
        plot_generator = DensityMapGenerator(
            str(cap3d_path),
            str(tech_path),
            pixel_resolution=pixel_resolution,
            target_size=_resolve_target_size(
                cap3d_path,
                target_size=target_size,
                scaled_output=scaled_output,
            ),
        )
        tech_layers, tech_z_heights = get_conductor_layers(str(tech_path))
        if selected_layers is not None:
            requested = {_normalize_layer_name(layer) for layer in selected_layers}
            tech_layers = [layer for layer in tech_layers if _normalize_layer_name(layer) in requested]
            tech_z_heights = {layer: tech_z_heights[layer] for layer in tech_layers}
        plot_generator.tech_conductor_layers = list(tech_layers)
        plot_generator.tech_z_heights = dict(tech_z_heights)
        plot_generator.parse_cap3d()
        plot_generator.match_layers()
        plot_generator.tighten_raster_bounds_to_conductors(selected_layers=plot_generator.matched_layers)
        plot_generator.generate_density_maps()
        generate_coarse_plot(cap3d_path.stem, plot_generator, plot_path, coarse_size, dpi)

    return saved_bundle




if __name__ == '__main__':
    sys.exit(main())

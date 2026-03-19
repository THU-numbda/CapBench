#!/usr/bin/env python3
"""
Batch convert CAP3D window files (W0…W9) into PCT-Cap NPZ point clouds.

Each output follows the native PCT-Cap schema while adding a companion
`layer_ids` array and lookup table so downstream tooling can colorize
points per metal/via layer without relying on Z height heuristics.

Typical usage (inside klayout-net env):
    conda run -n klayout-net python PCT-Cap/pct_cap_prepare_windows.py \\
        --windows-dir windows/cap3d \\
        --output-dir datasets/point_clouds \\
        --start 0 --end 9 \\
        --points-per-window 10000
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from common.datasets import (
    DATASET_ROOT,
    POINT_CLOUDS_DIR,
    to_dataset_relative,
)

import numpy as np

# Repository-relative imports
PCT_CAP_ROOT = Path(__file__).resolve().parent
# Ensure module import path includes the PCT-Cap package when invoked from repo root
if str(PCT_CAP_ROOT) not in sys.path:
    sys.path.insert(0, str(PCT_CAP_ROOT))

try:
    from cap3d_to_pct import PointCloudGenerator
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "Unable to import PointCloudGenerator from PCT-Cap/cap3d_to_pct.py. "
        "Please run this script from the repository root.\n"
        f"Original error: {exc}"
    ) from exc

from window_tools.cap3d_models import Block


class LayerAwarePointCloudGenerator(PointCloudGenerator):
    """Extends the baseline generator to keep per-point layer metadata."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.point_layers: List[int] = []
        self.layer_id_to_name: Dict[int, str] = {}
        self._layer_name_to_id: Dict[str, int] = {}
        self._unknown_layer_name_to_id: Dict[str, int] = {}
        self._next_unknown_id: int = 0

    # ------------------------------------------------------------------
    # CAP3D parsing overrides
    # ------------------------------------------------------------------
    def parse_cap3d(self) -> None:
        """Parse CAP3D file and cache layer lookups."""
        super().parse_cap3d()

        self.layer_id_to_name = {
            int(idx): layer.name for idx, layer in self.layers.items()
        }
        self._layer_name_to_id = {
            layer.name: int(idx) for idx, layer in self.layers.items()
        }
        existing_ids = list(self.layer_id_to_name.keys())
        self._next_unknown_id = (max(existing_ids) + 1) if existing_ids else 0
        self._unknown_layer_name_to_id = {}
        self.point_layers = []

    # ------------------------------------------------------------------
    # Point cloud sampling with layer tracking
    # ------------------------------------------------------------------
    def generate_point_clouds(self) -> None:
        """Generate point clouds while recording the layer for each sample."""
        if not self.blocks_by_layer:
            raise RuntimeError(
                "parse_cap3d() must be called before generate_point_clouds()."
            )

        print(f"\nGenerating point cloud for {self.cap3d_file.name}...")
        print(f"  Target samples: {self.total_points}")

        self.points = []
        self.point_net_names = []
        self.point_layers = []

        block_entries: List[Tuple[str, Block]] = []
        block_areas: List[float] = []

        for layer_name, blocks in self.blocks_by_layer.items():
            for block in blocks:
                block_entries.append((layer_name, block))
                v1_mag = np.linalg.norm(block.v1)
                v2_mag = np.linalg.norm(block.v2)
                h_mag = np.linalg.norm(block.hvec)
                area = 2 * (v1_mag * v2_mag + v1_mag * h_mag + v2_mag * h_mag)
                block_areas.append(area)

        total_area = float(sum(block_areas))
        if total_area <= 0.0:
            total_area = 1.0

        processed = 0
        total_blocks = len(block_entries)

        for (layer_name, block), area in zip(block_entries, block_areas):
            block_layer_id = self._resolve_layer_id(block, layer_name)
            block_point_count = max(1, int(self.total_points * area / total_area))

            flux_sign = 1 if block.parent_name == self.master_conductor_name else 0

            if block.parent_name and block.parent_name in self.conductor_names:
                net_id = self.conductor_names[block.parent_name]
                net_name = block.parent_name
            else:
                net_id = 0
                net_name = "UNKNOWN"

            block_points, block_net_names = super().sample_block_surface_adaptive(
                block, flux_sign, net_id, net_name, block_point_count
            )

            self.points.append(block_points)
            self.point_net_names.extend(block_net_names)
            self.point_layers.extend([block_layer_id] * len(block_points))

            processed += 1
            if processed % 100 == 0 or processed == total_blocks:
                print(f"  Processed {processed}/{total_blocks} conductor blocks")

        if self.points:
            all_points = np.vstack(self.points)
            layer_array = np.asarray(self.point_layers, dtype=np.int32)

            if len(all_points) > self.total_points:
                indices = np.random.choice(len(all_points), self.total_points, replace=False)
                all_points = all_points[indices]
                layer_array = layer_array[indices]
                self.point_net_names = [self.point_net_names[i] for i in indices]

            self.points = all_points
            self.point_layers = layer_array
            print(f"  Final sample count: {len(self.points)}")
        else:
            print("  WARNING: No conductor blocks sampled; creating empty point cloud.")
            self.points = np.zeros((0, 9), dtype=np.float32)
            self.point_layers = np.zeros((0,), dtype=np.int32)
            self.point_net_names = []

        self._generate_conductor_metadata()

    # ------------------------------------------------------------------
    # NPZ persistence with layer metadata
    # ------------------------------------------------------------------
    def save_npz(self, output_file: str):
        """Save point cloud to NPZ, adding per-point layer ids."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        data['points'] = self.points.astype(np.float32)
        data['point_net_names'] = np.array(self.point_net_names, dtype=object)
        data['conductor_ids'] = np.array(
            [c['conductor_id'] for c in self.conductor_metadata],
            dtype=np.int32,
        )
        metadata_str = ";".join(
            f"{c['conductor_name']}|{c['layer']}" for c in self.conductor_metadata
        )
        data['conductor_metadata_str'] = np.array(metadata_str)

        if self.window:
            data['window_bounds'] = np.array([
                self.window.v1[0], self.window.v1[1], self.window.v1[2],
                self.window.v2[0], self.window.v2[1], self.window.v2[2],
            ], dtype=np.float32)
            data['window_name_str'] = np.array(self.window.name)

        layer_ids = self.point_layers.astype(np.int32)
        data['layer_ids'] = layer_ids

        max_layer_id = int(layer_ids.max()) if layer_ids.size else -1
        lookup: List[str] = []
        for lid in range(max_layer_id + 1):
            lookup.append(self.layer_id_to_name.get(lid, f"layer_{lid}"))
        data['layer_name_lookup'] = np.array(lookup, dtype=object)

        np.savez_compressed(output_path, **data)

        print(f"  Saved NPZ: {output_path} ({len(self.points)} points)")
        return output_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_layer_id(self, block: Block, layer_name: str) -> int:
        if block.layer is not None:
            layer_id = int(block.layer)
            self.layer_id_to_name.setdefault(layer_id, layer_name)
            return layer_id

        if layer_name in self._layer_name_to_id:
            return self._layer_name_to_id[layer_name]

        if layer_name not in self._unknown_layer_name_to_id:
            self._unknown_layer_name_to_id[layer_name] = self._next_unknown_id
            self.layer_id_to_name[self._next_unknown_id] = layer_name
            self._next_unknown_id += 1

        return self._unknown_layer_name_to_id[layer_name]


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert CAP3D window files to PCT-Cap NPZ point clouds.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--windows-dir",
        type=Path,
        default=REPO_ROOT / "windows",
        help="Directory containing W*.cap3d window files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=POINT_CLOUDS_DIR,
        help="Directory to write NPZ files.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="First window index (inclusive).",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=9,
        help="Last window index (inclusive).",
    )
    parser.add_argument(
        "--points-per-window",
        type=int,
        default=10000,
        help="Target number of sampled points per window.",
    )
    parser.add_argument(
        "--master-conductor",
        help="Optional conductor name to treat as master (defaults to auto-detect).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional RNG seed for reproducible sampling.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.seed is not None:
        np.random.seed(args.seed)
        random.seed(args.seed)

    window_indices = range(args.start, args.end + 1)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    for idx in window_indices:
        cap3d_path = args.windows_dir / f"W{idx}.cap3d"
        if not cap3d_path.exists():
            print(f"Skipping W{idx}: missing {cap3d_path}")
            continue

        generator = LayerAwarePointCloudGenerator(
            str(cap3d_path),
            total_points=args.points_per_window,
            master_conductor=args.master_conductor,
        )
        generator.parse_cap3d()
        generator.generate_point_clouds()

        window_id = cap3d_path.stem
        output_path = output_dir / f"{window_id}.npz"
        saved_path = Path(generator.save_npz(str(output_path)))

        # Print processing summary
        num_points = int(generator.points.shape[0]) if generator.points is not None else 0
        print(f"    Generated {num_points} points for {window_id}")

    print("\nConversion complete.")


if __name__ == "__main__":  # pragma: no cover
    main()

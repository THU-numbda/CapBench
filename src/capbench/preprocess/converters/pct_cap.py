#!/usr/bin/env python3
"""
CAP3D to PCT-Cap Point Cloud Converter

Converts CAP3D files into point cloud format compatible with PCT-Cap models.
Implements the Gauss law-based point cloud feature representation from the
PCT-Cap paper (ISEDA 2024).

Samples points on conductor surface boundaries (not inside conductors) with
9 features per point:
  1-3. 3D coordinates (x, y, z)
  4-6. Outward surface normals (nx, ny, nz)
  7.   Dielectric constant (εr) at each point
  8.   Electric flux sign (Φ): +1 for master, 0 for environment, -1 for coupling
  9.   Net ID: integer identifier (legacy, use point_net_names instead)

Additional data saved in NPZ:
  - point_net_names: array of net name strings (one per point) for validation

Usage:
    python cap3d_to_pct.py input.cap3d --output output.npz --total-points 10000
    python cap3d_to_pct.py ../windows/cap3d/W0.cap3d --master-conductor Net.5
"""

import sys
import argparse
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
# CSV import removed - CSV generation disabled
from datetime import datetime
import yaml
from tqdm import tqdm

from capbench.preprocess.cap3d_parser import StreamingCap3DParser
from capbench.preprocess.cap3d_models import Block, Layer, Window, PlateMedium, ParsedCap3DData
from capbench._internal.common.datasets import (
    DATASET_ROOT,
    POINT_CLOUDS_DIR,
    to_dataset_relative,
    repo_relative,
    extract_process_node_from_path,
    get_dataset_subdirs,
)


class PointCloudGenerator:
    """Generate PCT-Cap compatible point clouds from CAP3D files"""

    def __init__(self, cap3d_file: str, total_points: int = 1024, master_conductor: Optional[str] = None):
        """
        Initialize point cloud generator

        Args:
            cap3d_file: Path to CAP3D file
            total_points: Total number of points to sample from entire window
            master_conductor: Name of master conductor (auto-detect if None)
        """
        self.cap3d_file = Path(cap3d_file)
        self.total_points = total_points
        self.master_conductor_name = master_conductor

        # Parsed data
        self.window: Optional[Window] = None
        self.layers: Dict[int, Layer] = {}
        self.layer_order: List[str] = []
        self.blocks_by_layer: Dict[str, List[Block]] = defaultdict(list)
        self.plate_mediums: List[PlateMedium] = []
        self.conductor_names: Dict[str, int] = {}  # conductor_name -> conductor_id (legacy)

        # Point cloud data
        self.points: List[np.ndarray] = []  # List of [x, y, z, nx, ny, nz, diel, flux_sign, net_id]
        self.point_net_names: List[str] = []  # Net name for each point (parallel to points)
        self.conductor_metadata: List[Dict] = []

    def parse_cap3d(self):
        """Parse CAP3D file and extract structure"""
        
        parser = StreamingCap3DParser(str(self.cap3d_file))
        parsed_data = parser.parse_complete()

        # Extract window bounds
        if parsed_data.window:
            self.window = parsed_data.window

        # CAP3D block.layer stores the explicit <layer> id, not the list position.
        self.layers = {
            int(getattr(layer, "id", idx)): layer
            for idx, layer in enumerate(parsed_data.layers)
        }
        self.layer_order = [layer.name for layer in parsed_data.layers]

        # Extract plate mediums (dielectric layers)
        self.plate_mediums = sorted(parsed_data.plate_mediums, key=lambda pm: pm.z_top)

        # Extract blocks and organize by layer
        conductor_id = 1
        for block in parsed_data.blocks:
            # Skip dielectric blocks (type == 'medium')
            if block.type == 'medium':
                continue

            # Determine layer name
            if block.layer is not None and block.layer in self.layers:
                layer_name = self.layers[block.layer].name
                layer_type = self.layers[block.layer].type
            else:
                if block.name == "GROUND" or block.parent_name == "GROUND":
                    layer_name = "GROUND"
                    layer_type = "substrate"
                else:
                    layer_name = "unknown"
                    layer_type = "unknown"

            # Skip SUBSTRATE layer (ground plane is boundary condition, not a feature)
            if layer_name == "SUBSTRATE" or layer_type == "substrate":
                continue

            self.blocks_by_layer[layer_name].append(block)

            # Assign conductor IDs
            if block.parent_name and block.parent_name not in self.conductor_names:
                self.conductor_names[block.parent_name] = conductor_id
                conductor_id += 1

        # Determine master conductor if not specified
        if self.master_conductor_name is None:
            # Auto-detect: use conductor with most blocks
            if self.conductor_names:
                conductor_block_counts = {}
                for conductor_name in self.conductor_names:
                    count = sum(1 for blocks in self.blocks_by_layer.values()
                              for block in blocks if block.parent_name == conductor_name)
                    conductor_block_counts[conductor_name] = count

                self.master_conductor_name = max(conductor_block_counts.items(), key=lambda x: x[1])[0]
        else:
            if self.master_conductor_name not in self.conductor_names:
                raise ValueError(
                    f"Specified master conductor '{self.master_conductor_name}' not found in CAP3D data."
                )

    def get_dielectric_at_z(self, z: float, tolerance: float = 1e-9) -> float:
        """
        Get dielectric constant at a given z-coordinate

        Implements PCT-Cap paper's multi-dielectric interface handling:
        - If point is at interface between two dielectrics, return mean permittivity
        - Otherwise return the dielectric of the containing region

        Args:
            z: Z-coordinate of the point
            tolerance: Tolerance for detecting interface boundaries (in microns)

        Returns:
            Relative permittivity (εr) at this z-coordinate
        """
        if not self.plate_mediums:
            return 1.0  # Default to air

        # Check if point is at interface between two plate mediums
        for i in range(len(self.plate_mediums) - 1):
            pm_lower = self.plate_mediums[i]
            pm_upper = self.plate_mediums[i + 1]

            # If point is at the boundary between two layers (within tolerance)
            if abs(z - pm_lower.z_top) < tolerance:
                # Use mean permittivity at multi-dielectric interface (PCT-Cap paper)
                return (pm_lower.diel + pm_upper.diel) / 2.0

        # Find the plate medium that contains this z-coordinate
        for pm in self.plate_mediums:
            if z <= pm.z_top:
                return pm.diel

        # If above all plate mediums, use the last one
        return self.plate_mediums[-1].diel

    def sample_block_surface_adaptive(self, block: Block, flux_sign: int, net_id: int, net_name: str, num_points: int) -> Tuple[np.ndarray, List[str]]:
        """
        Sample points on block surfaces with adaptive point count

        Args:
            block: Block to sample
            flux_sign: Electric flux sign (+1 for master, 0 for environment, -1 for coupling target)
            net_id: Integer net/conductor ID for validation
            net_name: Net/conductor name string for validation
            num_points: Total number of points to sample on this block

        Returns:
            Tuple of (points_array, net_names_list)
            - points_array: shape (num_points, 9) with [x, y, z, nx, ny, nz, diel, flux_sign, net_id]
            - net_names_list: list of net_name repeated num_points times
        """
        total_points = max(1, num_points)
        return self.sample_block_surface(block, flux_sign, net_id, net_name, total_points)

    def sample_block_surface(self, block: Block, flux_sign: int, net_id: int, net_name: str, total_points: int = 50) -> Tuple[np.ndarray, List[str]]:
        """
        Sample points on block faces using area-proportional probabilities.

        Based on Gauss's law, samples points on conductor surface boundaries where
        electric flux originates (+1) or terminates (0, -1). Each face receives a
        probability equal to its share of the cuboid's total surface area so long,
        thin faces receive proportionally more samples.

        Args:
            block: Block to sample
            flux_sign: Electric flux direction indicator:
                      +1 = master conductor (electric field originates here)
                       0 = environment conductor (non-target)
                      -1 = environment conductor (coupling target)
            net_id: Integer net/conductor ID for validation against golden labels
            net_name: Net/conductor name string for validation
            total_points: Total number of points to draw on this block

        Returns:
            Tuple of (points_array, net_names_list)
            - points_array: shape (N, 9) with [x, y, z, nx, ny, nz, diel, flux_sign, net_id]
            - net_names_list: list of net_name strings (one per point)
        """
        if total_points <= 0:
            return np.zeros((0, 9)), []

        # Base point and vectors defining the block
        bp = block.base
        v1 = block.v1
        v2 = block.v2
        hvec = block.hvec

        # Define the 6 faces and their outward normals
        # Each face is defined by: base_corner, edge1_vector, edge2_vector, normal
        faces = [
            # Bottom face (z = bp[2])
            (bp, v1, v2, np.array([0, 0, -1])),
            # Top face (z = bp[2] + hvec[2])
            (bp + hvec, v1, v2, np.array([0, 0, 1])),
            # Front face (y = bp[1])
            (bp, v1, hvec, np.array([0, -1, 0])),
            # Back face (y = bp[1] + v2[1])
            (bp + v2, v1, hvec, np.array([0, 1, 0])),
            # Left face (x = bp[0])
            (bp, v2, hvec, np.array([-1, 0, 0])),
            # Right face (x = bp[0] + v1[0])
            (bp + v1, v2, hvec, np.array([1, 0, 0])),
        ]

        # Compute area for each face to determine sampling probabilities.
        # Use float64 normalization here because block geometry is stored as
        # float32, and np.random.choice is strict about probabilities summing to 1.
        face_areas = np.asarray(
            [np.linalg.norm(np.cross(edge1, edge2)) for _, edge1, edge2, _ in faces],
            dtype=np.float64,
        )
        face_areas[~np.isfinite(face_areas)] = 0.0
        face_areas = np.clip(face_areas, 0.0, None)

        total_face_area = float(face_areas.sum())
        if total_face_area > 0.0:
            face_probs = face_areas / total_face_area
            face_probs[-1] = max(0.0, 1.0 - float(face_probs[:-1].sum()))
            prob_sum = float(face_probs.sum())
            if prob_sum <= 0.0 or not np.isfinite(prob_sum):
                face_probs = np.full(len(faces), 1.0 / len(faces), dtype=np.float64)
            else:
                face_probs /= prob_sum
        else:
            face_probs = np.full(len(faces), 1.0 / len(faces), dtype=np.float64)

        # Assign points to faces based on probabilities
        face_indices = np.random.choice(len(faces), size=total_points, p=face_probs)

        points_list = []
        for idx, (base_corner, edge1, edge2, normal) in enumerate(faces):
            count = np.count_nonzero(face_indices == idx)
            if count == 0:
                continue

            # Sample random points on this face using barycentric coords
            u = np.random.random(count)
            v = np.random.random(count)

            # Generate 3D points
            points_3d = base_corner + u[:, np.newaxis] * edge1 + v[:, np.newaxis] * edge2

            # Get dielectric for each point based on z-coordinate
            diel = np.array([self.get_dielectric_at_z(z) for z in points_3d[:, 2]])

            # Create normal vectors (same for all points on this face)
            normals = np.tile(normal, (count, 1))

            # Create flux sign array (constant for all points on this block)
            flux_signs = np.full(count, flux_sign, dtype=np.float32)

            # Create net ID array (constant for all points on this block)
            net_ids = np.full(count, net_id, dtype=np.float32)

            # Combine: [x, y, z, nx, ny, nz, diel, flux_sign, net_id]
            face_points = np.hstack([
                points_3d,                 # x, y, z (position)
                normals,                   # nx, ny, nz (surface normal)
                diel[:, np.newaxis],       # εr (relative permittivity)
                flux_signs[:, np.newaxis], # Φ (electric flux sign for training)
                net_ids[:, np.newaxis]     # net_id (conductor ID for validation)
            ])

            points_list.append(face_points)

        # Generate net names list (one per point)
        net_names_list = [net_name] * total_points

        if points_list:
            points_stack = np.vstack(points_list)
        else:
            points_stack = np.zeros((0, 9))

        return points_stack, net_names_list

    def generate_point_clouds(self):
        """Generate point clouds from all conductor blocks"""

        total_blocks = sum(len(blocks) for blocks in self.blocks_by_layer.values())

        # Calculate surface area for each block to weight sampling
        block_areas = []
        block_list = []

        for layer_name, blocks in self.blocks_by_layer.items():
            for block in blocks:
                # Calculate total surface area (sum of 6 faces)
                v1_mag = np.linalg.norm(block.v1)
                v2_mag = np.linalg.norm(block.v2)
                hvec_mag = np.linalg.norm(block.hvec)

                area = 2 * (v1_mag * v2_mag + v1_mag * hvec_mag + v2_mag * hvec_mag)
                block_areas.append(area)
                block_list.append(block)

        total_area = float(np.sum(np.asarray(block_areas, dtype=np.float64)))
        if total_area <= 0.0 or not np.isfinite(total_area):
            total_area = float(len(block_areas)) if block_areas else 1.0

        # Sample points proportional to surface area

        for block, area in zip(block_list, block_areas):
            # Number of points for this block (proportional to area)
            area_value = float(area)
            if area_value <= 0.0 or not np.isfinite(area_value):
                area_value = 1.0
            block_point_count = max(1, int(self.total_points * area_value / total_area))

            # Determine flux sign based on PCT-Cap paper (Gauss's law)
            # Φ = +1 for master conductor (electric field originates)
            # Φ =  0 for environment conductors (electric field terminates)
            # Φ = -1 for coupling target (future extension)
            if block.parent_name == self.master_conductor_name:
                flux_sign = 1  # Master conductor
            else:
                flux_sign = 0  # Environment conductor

            # Get net ID and name for validation
            if block.parent_name and block.parent_name in self.conductor_names:
                net_id = self.conductor_names[block.parent_name]
                net_name = block.parent_name
            else:
                net_id = 0  # Unknown conductor
                net_name = "UNKNOWN"

            # Sample points on this block
            block_points, block_net_names = self.sample_block_surface_adaptive(
                block, flux_sign, net_id, net_name, block_point_count
            )
            self.points.append(block_points)
            self.point_net_names.extend(block_net_names)

        # Combine all points
        if self.points:
            self.points = np.vstack(self.points)

            # Subsample to exact target if needed
            if len(self.points) > self.total_points:
                indices = np.random.choice(len(self.points), self.total_points, replace=False)
                self.points = self.points[indices]
                # Also subsample net names to match
                self.point_net_names = [self.point_net_names[i] for i in indices]

        else:
            self.points = np.zeros((0, 9))
            self.point_net_names = []

        # Generate conductor metadata
        self._generate_conductor_metadata()

    def _generate_conductor_metadata(self):
        """Generate conductor metadata for later use"""

        for conductor_name, conductor_id in sorted(self.conductor_names.items(), key=lambda x: x[1]):
            # Find which layer this conductor appears in
            layer_name = "unknown"
            for lname, blocks in self.blocks_by_layer.items():
                for block in blocks:
                    if block.parent_name == conductor_name:
                        layer_name = lname
                        break
                if layer_name != "unknown":
                    break

            self.conductor_metadata.append({
                'conductor_id': int(conductor_id),
                'conductor_name': conductor_name,
                'layer': layer_name
            })


    def save_npz(self, output_file: str):
        """Save point cloud to NPZ file"""
        output_path = Path(output_file)

        # Prepare data dictionary
        data = {}

        # Store point cloud data
        data['points'] = self.points.astype(np.float32)

        # Store net names for each point (parallel array to points)
        data['point_net_names'] = np.array(self.point_net_names, dtype=object)

        # Store conductor metadata as numeric arrays + save names/layers to JSON
        data['conductor_ids'] = np.array([c['conductor_id'] for c in self.conductor_metadata], dtype=np.int32)

        # Encode conductor names and layers as concatenated string (compatible format)
        # Format: "name1|layer1;name2|layer2;..."
        metadata_str = ";".join([f"{c['conductor_name']}|{c['layer']}" for c in self.conductor_metadata])
        data['conductor_metadata_str'] = np.array(metadata_str)

        # Store window bounds
        if self.window:
            data['window_bounds'] = np.array([
                self.window.v1[0], self.window.v1[1], self.window.v1[2],
                self.window.v2[0], self.window.v2[1], self.window.v2[2]
            ], dtype=np.float32)
            data['window_name_str'] = np.array(self.window.name)

        # Save NPZ file
        np.savez_compressed(output_path, **data)

        return output_path

    def save_annotation_csv(self, output_file: str, npz_file: str):
        """Save PCT-Cap compatible annotation CSV - DISABLED"""
        # CSV generation disabled - all information is already stored in the NPZ file:
        # - Window coordinates: stored in 'window_bounds' array in NPZ
        # - Window name: stored in 'window_name_str' in NPZ
        # - Point cloud path: Same filename as NPZ file
        # CSV files were redundant and much larger than NPZ files


def main():
    parser = argparse.ArgumentParser(
        description='Convert CAP3D files to PCT-Cap point clouds',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (auto-detect master conductor)
  python cap3d_to_pct.py ../windows/cap3d/W0.cap3d

  # Specify total points and output file
  python cap3d_to_pct.py ../windows/cap3d/W0.cap3d --output data/W0.npz --total-points 5000

  # Specify master conductor explicitly
  python cap3d_to_pct.py ../windows/cap3d/W0.cap3d --master-conductor Net.5 --total-points 10000

  # Full example with all options
  python cap3d_to_pct.py ../designs/cap3d/gcd.cap3d \\
      --total-points 20000 \\
      --master-conductor VDD \\
      --output data/gcd.npz \\
      --annotation data/gcd_annotation.csv

Features:
  - Implements PCT-Cap paper (ISEDA 2024) Gauss law-based point cloud
  - 9 features per point: [x, y, z, nx, ny, nz, εr, Φ, net_id]
  - Samples on conductor SURFACES (not inside) with outward normals
  - Electric flux sign Φ: +1 for master, 0 for environment (for training)
  - Net names: parallel array 'point_net_names' for validation against golden labels
  - Dielectric constant εr with interface averaging per paper
  - Excludes SUBSTRATE layer (ground plane is boundary condition)
  - Area-proportional sampling for efficiency
        """
    )

    parser.add_argument('input', help='Input CAP3D file')
    parser.add_argument('-o', '--output', help='Output NPZ file (default: <input_stem>.npz)')
    parser.add_argument('-n', '--total-points', type=int, default=10000,
                       help='Total number of points to sample from window (default: 10000)')
    parser.add_argument('-m', '--master-conductor', help='Name of master conductor (auto-detect largest if not specified)')
    # CSV annotation generation removed - information already stored in NPZ files

    args = parser.parse_args()

    # Determine output files
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        return 1

    if args.output:
        output_npz = Path(args.output)
        if output_npz.exists() and output_npz.is_dir():
            output_npz = output_npz / f"{input_path.stem}.npz"
        elif output_npz.suffix.lower() != ".npz":
            output_npz = output_npz.with_suffix(".npz")
    else:
        output_npz = POINT_CLOUDS_DIR / f"{input_path.stem}.npz"
    output_npz.parent.mkdir(parents=True, exist_ok=True)

    # CSV output removed - information already stored in NPZ files

    # Generate point clouds
    try:
        generator = PointCloudGenerator(
            args.input,
            total_points=args.total_points,
            master_conductor=args.master_conductor
        )
        generator.parse_cap3d()
        generator.generate_point_clouds()
        saved_npz = Path(generator.save_npz(str(output_npz)))
        # CSV annotation generation disabled - all information is already in NPZ file
        generator.save_annotation_csv("", str(saved_npz))  # Just show the disabled message

        # PCT metadata validation removed - converter no longer checks manifest metadata
        window_id = input_path.stem


    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return


def convert_window(
    cap3d_path: Path,
    *,
    total_points: int = 1024,
    master_conductor: Optional[str] = None,
    output_npz: Optional[Path] = None,
    dataset_dirs: Optional[Dict[str, Path]] = None,
) -> Path:
    """
    Convert a single CAP3D window into the PCT-Cap point cloud format.

    Args:
        cap3d_path: Path to the input CAP3D window.
        total_points: Target number of samples generated by the converter.
        master_conductor: Optional conductor name to treat as the master.
        output_npz: Optional override for the NPZ destination.

    Returns:
        Path to the generated NPZ file.
    """
    input_path = Path(cap3d_path)
    window_id = input_path.stem

    if output_npz is None:
        if dataset_dirs and 'point_clouds' in dataset_dirs:
            output_npz = dataset_dirs['point_clouds'] / f"{window_id}.npz"
        else:
            output_npz = POINT_CLOUDS_DIR / f"{window_id}.npz"

    output_npz.parent.mkdir(parents=True, exist_ok=True)

    generator = PointCloudGenerator(
        str(input_path),
        total_points=total_points,
        master_conductor=master_conductor,
    )
    generator.parse_cap3d()
    generator.generate_point_clouds()

    saved_npz = Path(generator.save_npz(str(output_npz)))
    # CSV annotation generation disabled - all information is in NPZ
    generator.save_annotation_csv("", str(saved_npz))

    # PCT metadata validation removed - converter no longer checks manifest metadata
    # Manifest loading and validation removed to simplify the converter

    return saved_npz


def main():
    parser = argparse.ArgumentParser(
        description="Convert CAP3D window(s) into PCT-Cap NPZ point clouds."
    )
    parser.add_argument("inputs", nargs="+", help="Input CAP3D window file(s)")
    parser.add_argument("--output", help="Output NPZ file or directory (default: datasets/point_clouds/<window>.npz)")
    parser.add_argument("--total-points", type=int, default=1024, help="Target number of sampled points per window")
    parser.add_argument("--master-conductor", help="Optional name of master conductor")

    args = parser.parse_args()

    # Auto-detect process node from first CAP3D file and determine dataset directories
    try:
        first_cap3d = Path(args.inputs[0])
        # Try to detect process node from CAP3D file path or parent directories
        process_node = None

        # Check if CAP3D file is in a dataset directory with process node
        for parent in first_cap3d.parents:
            if parent.name in ['nangate45', 'asap7', 'sky130hd', 'gf180', 'tsmc28']:
                process_node = parent.name
                break

        # If not found, try to extract from path pattern
        if process_node is None:
            try:
                process_node = extract_process_node_from_path(first_cap3d.parent)
            except ValueError:
                pass

        # If still not found, try to extract from datasets path
        if process_node is None and 'datasets' in str(first_cap3d):
            dataset_parts = Path(first_cap3d).parts
            datasets_idx = dataset_parts.index('datasets') if 'datasets' in dataset_parts else -1
            if datasets_idx >= 0 and datasets_idx + 1 < len(dataset_parts):
                possible_node = dataset_parts[datasets_idx + 1]
                if possible_node in ['nangate45', 'asap7', 'sky130hd', 'gf180', 'tsmc28']:
                    process_node = possible_node

        if process_node is None:
            print("ERROR: Could not determine process node from input files", file=sys.stderr)
            print("Please ensure CAP3D files are in dataset directories with process node names", file=sys.stderr)
            return 1

        dataset_dirs = get_dataset_subdirs(DATASET_ROOT / f"{process_node}/small")
    except Exception as exc:
        print(f"ERROR: Could not determine dataset directories: {exc}", file=sys.stderr)
        return 1

    # Initialize progress tracking
    successful_conversions = 0
    failed_conversions = []

    output_path = Path(args.output) if args.output else None

    # Process files with progress bar
    pbar = tqdm(args.inputs, desc="Converting CAP3D → Point Clouds", unit="file",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')

    for cap3d_file in pbar:
        cap3d_path = Path(cap3d_file)
        pbar.set_postfix_str(f"File: {cap3d_path.name}")

        try:
            if not cap3d_path.exists():
                failed_conversions.append((cap3d_file, "File not found"))
                continue

            if output_path:
                if len(args.inputs) == 1 and output_path.suffix:
                    npz_path = output_path
                else:
                    npz_path = output_path / f"{cap3d_path.stem}.npz"
            else:
                npz_path = dataset_dirs['point_clouds'] / f"{cap3d_path.stem}.npz"

            convert_window(
                cap3d_path,
                total_points=args.total_points,
                master_conductor=args.master_conductor,
                output_npz=npz_path,
                dataset_dirs=dataset_dirs,
            )
            successful_conversions += 1

        except Exception as exc:
            failed_conversions.append((cap3d_file, str(exc)))
            continue

    # Final status report
    if failed_conversions:
        for filename, error in failed_conversions:
            print(f"ERROR: Conversion failed for {filename}: {error}", file=sys.stderr)

    return 0 if not failed_conversions else 1


if __name__ == "__main__":
    sys.exit(main())

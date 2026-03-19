"""Dataset directory helpers and utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import yaml
from capbench.paths import PACKAGE_ROOT, TECH_ROOT

# Root dataset directories
DATASET_ROOT = Path(os.environ.get("CAPBENCH_DATASET_ROOT", "datasets")).expanduser()
REPO_ROOT = PACKAGE_ROOT

# Dataset subdirectories (will be resolved relative to specific dataset paths)
def get_dataset_subdirs(dataset_path: Optional[Path] = None) -> Dict[str, Path]:
    """Get dataset subdirectories for a specific dataset path.

    Args:
        dataset_path: Path to specific dataset (e.g., datasets/nangate45/small)
                     If None, returns fallback root-level directories

    Returns:
        Dictionary mapping subdir names to paths
    """
    if dataset_path:
        base_path = Path(dataset_path)
    else:
        base_path = DATASET_ROOT

    return {
        'cap3d': base_path / "cap3d",
        'cap3d_split': base_path / "cap3d_split",
        'gds': base_path / "gds",
        'def': base_path / "def",
        'point_clouds': base_path / "point_clouds",
        'density_maps': base_path / "density_maps",
        'binary_masks': base_path / "binary-masks",
        'density_maps_scaled': base_path / "density_maps_scaled",
        'labels_rwcap': base_path / "labels_rwcap",
        'labels_raphael': base_path / "labels_raphael",
        'manifests': base_path / "manifests",
    }

# Fallback root-level directories (for backwards compatibility)
CAP3D_DIR = DATASET_ROOT / "cap3d"
POINT_CLOUDS_DIR = DATASET_ROOT / "point_clouds"
DENSITY_MAPS_DIR = DATASET_ROOT / "density_maps"
BINARY_MASKS_DIR = DATASET_ROOT / "binary-masks"
LABELS_RWCAP_DIR = DATASET_ROOT / "labels_rwcap"
LABELS_RAPHAEL_DIR = DATASET_ROOT / "labels_raphael"
MANIFESTS_DIR = DATASET_ROOT / "manifests"


def repo_relative(path: Path) -> Path:
    """Convert a path to be relative to the current workspace when possible."""
    resolved = Path(path).resolve()
    for root in (Path.cwd().resolve(), REPO_ROOT.resolve()):
        try:
            return resolved.relative_to(root)
        except ValueError:
            continue
    return resolved


def to_dataset_relative(path: Path, dataset_dirs: Optional[Dict[str, Path]] = None) -> Path:
    """Convert a path to be relative to the most appropriate dataset subdirectory."""
    if dataset_dirs is None:
        dataset_dirs = get_dataset_subdirs()

    path = Path(path)

    # Try to make it relative to each dataset subdir
    for subdir_name, subdir_path in dataset_dirs.items():
        try:
            return path.relative_to(subdir_path)
        except ValueError:
            continue

    # If that fails, return relative to dataset root
    if hasattr(path, 'relative_to'):
        try:
            dataset_root = next(iter(dataset_dirs.values())).parent
            return path.relative_to(dataset_root)
        except ValueError:
            pass

    return path


def extract_process_node_from_path(dataset_path: Path) -> str:
    """Extract process node from dataset path name.

    Args:
        dataset_path: Path to the dataset directory (e.g., datasets/small_nangate45 or datasets/nangate45/small)

    Returns:
        Process node name (e.g., "nangate45")

    Examples:
        - datasets/small_nangate45 → "nangate45"
        - datasets/nangate45/small → "nangate45"
        - datasets/medium_asap7 → "asap7"

    Raises:
        ValueError: If process node cannot be extracted from path
    """
    # Extract from the last part of the path
    dataset_name = dataset_path.name

    # Try parent directory name if current directory name doesn't contain process node
    parent_name = dataset_path.parent.name if dataset_path.parent else ""

    # Look for known process nodes in both current and parent directory names
    known_nodes = ['nangate45', 'asap7', 'sky130hd', 'gf180', 'tsmc28']

    for node in known_nodes:
        if node in dataset_name.lower():
            return node
        if node in parent_name.lower():
            return node

    raise ValueError(
        f"Cannot extract process node from path '{dataset_path}'. "
        f"Checked directory names: '{dataset_name}', '{parent_name}'"
    )


def find_tech_stack_for_process_node(process_node: str) -> Optional[Path]:
    """Find the tech stack YAML file for a given process node.

    Args:
        process_node: Process node name (e.g., "nangate45", "asap7")

    Returns:
        Path to the tech stack YAML file, or None if not found

    Raises:
        ValueError: If process_node is empty or None
    """
    if not process_node:
        raise ValueError("Process node cannot be empty or None")

    tech_stack_file = TECH_ROOT / f"{process_node}.yaml"

    if tech_stack_file.exists():
        return tech_stack_file

    return None


def find_layermap_for_process_node(process_node: str) -> Optional[Path]:
    """Find the layermap file for a given process node.

    Args:
        process_node: Process node name (e.g., "nangate45", "asap7")

    Returns:
        Path to the layermap file, or None if not found

    Raises:
        ValueError: If process_node is empty or None
    """
    if not process_node:
        raise ValueError("Process node cannot be empty or None")

    layermap_file = TECH_ROOT / f"{process_node}.layermap"

    if layermap_file.exists():
        return layermap_file

    # Try alternative locations
    alternative_locations = [
        TECH_ROOT / f"{process_node}.layermap",
        TECH_ROOT.parent / "tech" / "layermaps" / f"{process_node}.layermap",
        TECH_ROOT.parent / "tech" / process_node / f"{process_node}.layermap",
    ]

    for location in alternative_locations:
        if location.exists():
            return location

    return None


# Import CAP3D parser for stats extraction
try:
    from capbench.preprocess.cap3d_parser import StreamingCap3DParser
except ImportError:
    StreamingCap3DParser = None


def extract_cap3d_stats(cap3d_path: Path) -> Dict[str, int]:
    """Extract comprehensive statistics from a CAP3D file.

    Args:
        cap3d_path: Path to the CAP3D file

    Returns:
        Dictionary with CAP3D parsing statistics
    """
    if StreamingCap3DParser is None:
        print(f"Warning: CAP3D parser not available, cannot extract stats from {cap3d_path}")
        return {}

    if not cap3d_path.exists():
        print(f"Warning: CAP3D file not found: {cap3d_path}")
        return {}

    try:
        parser = StreamingCap3DParser()
        parsed_data = parser.parse_complete(str(cap3d_path))

        if not parsed_data:
            print(f"Warning: Failed to parse CAP3D file: {cap3d_path}")
            return {}

        stats = parsed_data.stats or {}

        # Convert to a more convenient format and ensure types
        cap3d_stats = {
            'total_blocks': int(stats.get('total_blocks', 0)),
            'conductor_blocks': int(stats.get('conductors', 0)),
            'dielectric_blocks': int(stats.get('mediums', 0)),
            'poly_elements': int(stats.get('poly_elements', 0)),
            'num_layers': int(stats.get('layers', 0)),
            'num_conductors': 0,  # Will be counted below
            'num_dielectrics': 0,  # Will be counted below
            'window_exists': bool(stats.get('has_window', False)),
            'task_exists': bool(stats.get('has_task', False)),
            'parse_time_ms': round(float(stats.get('parse_time', 0)) * 1000, 2),
        }

        # Count unique conductors and dielectrics from parsed data
        if parsed_data.conductors:
            cap3d_stats['num_conductors'] = len(parsed_data.conductors)
        if parsed_data.mediums:
            cap3d_stats['num_dielectrics'] = len(parsed_data.mediums)

        return cap3d_stats

    except Exception as e:
        print(f"Warning: Failed to extract CAP3D stats from {cap3d_path}: {e}")
        return {}


# Alias for backwards compatibility
load_manifest = None  # This function has been removed
save_manifest = None  # This function has been removed
WindowManifest = None  # This class has been removed

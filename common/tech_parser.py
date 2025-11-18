#!/usr/bin/env python3
"""
Technology File Parser for CNNCap

Parses layer stack YAML files to extract conductor layer information.
Supports the new unified stack format with type-based layer categorization.

Usage:
    from common.tech_parser import get_conductor_layers

    layers, z_heights = get_conductor_layers('asap7.yaml')
    print(f"Found {len(layers)} conductor layers")
"""

from pathlib import Path
from typing import List, Dict, Tuple, Any
import yaml


def get_conductor_layers(tech_file_path: str) -> Tuple[List[str], Dict[str, float]]:
    """
    Extract conductor layers from technology stack YAML file.
    Supports the new unified stack format with explicit type field.

    Args:
        tech_file_path: Path to technology stack YAML file

    Returns:
        Tuple of:
            - List of conductor layer names in z-order (bottom to top)
            - Dictionary mapping layer name -> z_top height (microns)

    Raises:
        FileNotFoundError: If tech file doesn't exist
        ValueError: If tech file format is invalid

    New Tech File Format:
        stack:
          - {name: STI, type: dielectric, thickness_um: 0.05, er: 3.9}
          - {name: M1, type: metal, thickness_um: 0.036, wmin_um: 0.018}
          - {name: M1_TO_M2_PART1, type: dielectric, thickness_um: 0.036, er: 2.9}
          - {name: M2, type: metal, thickness_um: 0.036, wmin_um: 0.018}
          ...
        vias:
          V1: {from: M1, to: M2, wmin_um: 0.018}

    Example:
        >>> layers, z_heights = get_conductor_layers('asap7.yaml')
        >>> layers
        ['M1', 'V1', 'M2', 'V2', 'M3', ..., 'V9']
        >>> z_heights['M1']
        0.058
    """
    tech_path = Path(tech_file_path)

    if not tech_path.exists():
        raise FileNotFoundError(f"Tech file not found: {tech_file_path}")

    # Parse YAML file
    with tech_path.open('r') as f:
        tech_data = yaml.safe_load(f)

    if not tech_data or 'stack' not in tech_data:
        raise ValueError(f"Invalid tech file format: missing 'stack' key in {tech_file_path}")

    stack_data = tech_data['stack']

    if not isinstance(stack_data, list):
        raise ValueError(f"Invalid tech file format: 'stack' must be a list in {tech_file_path}")

    # Extract conductor layers and compute z-heights
    metal_layers = []
    z_heights = {}
    cumulative_z = 0.0

    # First pass: collect metal layers and their z-heights
    for layer_entry in stack_data:
        if not isinstance(layer_entry, dict):
            raise ValueError(f"Invalid layer entry format: {layer_entry}")

        layer_name = layer_entry.get('name')
        layer_type = layer_entry.get('type')
        thickness = layer_entry.get('thickness_um', 0.0)

        if not layer_name or not layer_type:
            raise ValueError(f"Invalid layer entry: missing name or type: {layer_entry}")

        # Update cumulative z-height
        cumulative_z += thickness

        # Add conductor layers only (type: 'metal')
        if layer_type == 'metal':
            metal_layers.append(layer_name)
            z_heights[layer_name] = cumulative_z

    # Second pass: interleave vias between metals using actual via names from tech file
    conductor_layers = []
    vias_data = tech_data.get('vias', {})

    # Create via mapping: find via that connects each metal to the next one
    via_between_metals = {}
    for via_name, via_info in vias_data.items():
        from_metal = via_info.get('from')
        to_metal = via_info.get('to')

        if from_metal in z_heights and to_metal in z_heights:
            # Calculate via z-height at the midpoint between the two metal layers
            via_z = (z_heights[from_metal] + z_heights[to_metal]) / 2.0
            via_between_metals[(from_metal, to_metal)] = via_name
            z_heights[via_name] = via_z

    # Interleave layers: M1, via1, M2, via2, M3, via3, etc.
    for i, metal_layer in enumerate(metal_layers):
        conductor_layers.append(metal_layer)

        # Find and add the via that connects this metal to the next metal
        if i + 1 < len(metal_layers):
            next_metal = metal_layers[i + 1]
            via_key = (metal_layer, next_metal)
            if via_key in via_between_metals:
                via_name = via_between_metals[via_key]
                conductor_layers.append(via_name)

    if not conductor_layers:
        raise ValueError(f"No conductor layers found in tech file: {tech_file_path}")

    return conductor_layers, z_heights


def get_layer_min_widths(tech_file_path: str) -> Dict[str, float]:
    """
    Extract minimum width values for conductor layers from technology stack YAML file.

    Args:
        tech_file_path: Path to technology stack YAML file

    Returns:
        Dictionary mapping layer name -> minimum width (microns)

    Raises:
        FileNotFoundError: If tech file doesn't exist
        ValueError: If tech file format is invalid
    """
    tech_path = Path(tech_file_path)

    if not tech_path.exists():
        raise FileNotFoundError(f"Tech file not found: {tech_file_path}")

    # Parse YAML file
    with tech_path.open('r') as f:
        tech_data = yaml.safe_load(f)

    if not tech_data or 'stack' not in tech_data:
        raise ValueError(f"Invalid tech file format: missing 'stack' key in {tech_file_path}")

    stack_data = tech_data['stack']

    if not isinstance(stack_data, list):
        raise ValueError(f"Invalid tech file format: 'stack' must be a list in {tech_file_path}")

    # Extract minimum widths for conductor layers
    min_widths = {}

    for layer_entry in stack_data:
        if not isinstance(layer_entry, dict):
            continue

        layer_name = layer_entry.get('name')
        layer_type = layer_entry.get('type')
        wmin_um = layer_entry.get('wmin_um')

        # Only process conductor layers with width data
        if layer_name and layer_type == 'metal' and wmin_um is not None:
            min_widths[layer_name] = float(wmin_um)

    # Also extract via minimum widths if available
    if 'vias' in tech_data:
        via_data = tech_data['vias']
        if isinstance(via_data, dict):
            for via_name, via_def in via_data.items():
                if isinstance(via_def, dict):
                    wmin_um = via_def.get('wmin_um')
                    if wmin_um is not None:
                        min_widths[via_name] = float(wmin_um)

    return min_widths


def get_all_layers_with_limit(tech_file_path: str, max_layers: int = None) -> Tuple[List[str], List[str], Dict[str, float]]:
    """
    Extract all layers (conductors + dielectrics) from technology stack YAML file with optional layer count limit.
    The limit applies to the total number of layer entries in the stack, counting both conductors and dielectrics.
    Supports the new unified stack format with type-based layer categorization.

    Args:
        tech_file_path: Path to technology stack YAML file
        max_layers: Maximum number of total layer entries to include (None = no limit)

    Returns:
        Tuple of:
            - List of all layer names in z-order (bottom to top), limited to max_layers
            - List of conductor layer names only (from the limited set)
            - Dictionary mapping layer name -> z_top height (microns)

    Raises:
        FileNotFoundError: If tech file doesn't exist
        ValueError: If tech file format is invalid

    New Tech File Format:
        stack:
          - {name: STI, type: dielectric, thickness_um: 0.05, er: 3.9}
          - {name: M1, type: metal, thickness_um: 0.036, wmin_um: 0.018}
          - {name: M1_TO_M2_PART1, type: dielectric, thickness_um: 0.036, er: 2.9}
          - {name: M2, type: metal, thickness_um: 0.036, wmin_um: 0.018}
          ...
    """
    tech_path = Path(tech_file_path)

    if not tech_path.exists():
        raise FileNotFoundError(f"Tech file not found: {tech_file_path}")

    # Parse YAML file
    with tech_path.open('r') as f:
        tech_data = yaml.safe_load(f)

    if not tech_data or 'stack' not in tech_data:
        raise ValueError(f"Invalid tech file format: missing 'stack' key in {tech_file_path}")

    stack_data = tech_data['stack']

    if not isinstance(stack_data, list):
        raise ValueError(f"Invalid tech file format: 'stack' must be a list in {tech_file_path}")

    # Extract all layers and compute z-heights
    all_layers = []
    conductor_layers = []
    z_heights = {}
    cumulative_z = 0.0

    # Apply limit if specified
    if max_layers is not None and max_layers > 0:
        stack_data = stack_data[:max_layers]

    for layer_entry in stack_data:
        if not isinstance(layer_entry, dict):
            raise ValueError(f"Invalid layer entry format: {layer_entry}")

        layer_name = layer_entry.get('name')
        layer_type = layer_entry.get('type')
        thickness = layer_entry.get('thickness_um', 0.0)

        if not layer_name or not layer_type:
            raise ValueError(f"Invalid layer entry: missing name or type: {layer_entry}")

        # Update cumulative z-height
        cumulative_z += thickness

        # Add to all layers list
        all_layers.append(layer_name)
        z_heights[layer_name] = cumulative_z

        # Add to conductor layers if it's a conductor (type: 'metal')
        if layer_type == 'metal':
            conductor_layers.append(layer_name)

    if not all_layers:
        raise ValueError(f"No layers found in tech file: {tech_file_path}")

    return all_layers, conductor_layers, z_heights


def get_conductor_layers_with_limit(tech_file_path: str, max_layers: int = None) -> Tuple[List[str], Dict[str, float]]:
    """
    Extract conductor layers from technology stack YAML file with optional layer count limit.

    Args:
        tech_file_path: Path to technology stack YAML file
        max_layers: Maximum number of conductor layers to include (None = no limit)

    Returns:
        Tuple of:
            - List of conductor layer names in z-order (bottom to top), limited to max_layers
            - Dictionary mapping layer name -> z_top height (microns)

    Raises:
        FileNotFoundError: If tech file doesn't exist
        ValueError: If tech file format is invalid
    """
    layers, z_heights = get_conductor_layers(tech_file_path)

    if max_layers is not None and max_layers > 0:
        # Return only the bottom max_layers
        layers = layers[:max_layers]
        # Filter z_heights to only include returned layers
        z_heights = {layer: z_heights[layer] for layer in layers}

    return layers, z_heights


def get_num_conductor_channels(tech_file_path: str) -> int:
    """
    Get the number of conductor channels for CNN input.

    Convenience function for model instantiation.

    Args:
        tech_file_path: Path to technology stack YAML file

    Returns:
        Number of conductor layers (input channels for CNN)

    Example:
        >>> num_channels = get_num_conductor_channels('nangate45_stack.yaml')
        >>> num_channels
        11
    """
    layers, _ = get_conductor_layers(tech_file_path)
    return len(layers)


def match_layers_by_height(
    tech_layers: List[str],
    tech_z_heights: Dict[str, float],
    cap3d_layers: List[str],
    cap3d_z_heights: Dict[str, float],
    tolerance: float = 1e-4
) -> Tuple[List[Tuple[str, str]], List[str]]:
    """
    Match tech file layers to CAP3D layers based on z-heights.

    Args:
        tech_layers: Ordered list of conductor layer names from tech file
        tech_z_heights: Dictionary of tech layer name -> z_top height
        cap3d_layers: Ordered list of conductor layer names from CAP3D
        cap3d_z_heights: Dictionary of CAP3D layer name -> z_top height
        tolerance: Maximum z-height difference for matching (microns)

    Returns:
        Tuple of:
            - List of matched pairs: (tech_layer_name, cap3d_layer_name)
            - List of warnings (empty if all matched successfully)

    Matching Strategy:
        1. Check that layer counts match
        2. Sort both by z-height
        3. Match pairwise if z-heights within tolerance
        4. Warn if layer names don't match but z-heights do
        5. Use CAP3D layer names in case of name mismatch
    """
    warnings = []
    matched_pairs = []

    # Check layer count
    if len(tech_layers) != len(cap3d_layers):
        warnings.append(
            f"Layer count mismatch: tech has {len(tech_layers)} layers, "
            f"CAP3D has {len(cap3d_layers)} layers"
        )
        return [], warnings

    # Sort both lists by z-height
    tech_sorted = sorted(tech_layers, key=lambda l: tech_z_heights[l])
    cap3d_sorted = sorted(cap3d_layers, key=lambda l: cap3d_z_heights[l])

    # Match pairwise
    for tech_layer, cap3d_layer in zip(tech_sorted, cap3d_sorted):
        tech_z = tech_z_heights[tech_layer]
        cap3d_z = cap3d_z_heights[cap3d_layer]

        # Check z-height match
        z_diff = abs(tech_z - cap3d_z)
        if z_diff > tolerance:
            warnings.append(
                f"Z-height mismatch for {tech_layer} (tech={tech_z:.6f}μm) vs "
                f"{cap3d_layer} (CAP3D={cap3d_z:.6f}μm), diff={z_diff:.6f}μm"
            )
            continue

        # Check name match (case-insensitive)
        if tech_layer.lower() != cap3d_layer.lower():
            warnings.append(
                f"Layer name mismatch at z={cap3d_z:.6f}μm: "
                f"tech='{tech_layer}' vs CAP3D='{cap3d_layer}' - using CAP3D name"
            )

        # Add matched pair (use CAP3D name)
        matched_pairs.append((tech_layer, cap3d_layer))

    return matched_pairs, warnings


if __name__ == '__main__':
    # Test with NanGate45 tech file
    import sys

    if len(sys.argv) > 1:
        tech_file = sys.argv[1]
    else:
        tech_file = 'tech/nangate45.yaml'

    print(f"Parsing tech file: {tech_file}")

    try:
        layers, z_heights = get_conductor_layers(tech_file)

        print(f"\nFound {len(layers)} conductor layers:")
        for i, layer in enumerate(layers):
            print(f"  {i:2d}. {layer:10s} z_top={z_heights[layer]:8.6f} μm")

        print(f"\nNumber of CNN input channels: {len(layers)}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

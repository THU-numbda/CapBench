#!/usr/bin/env python3
"""
Layer Stack Summary for CAP3D Files

Reads CAP3D files and displays a clean layer stack summary table.
The table format looks good both with and without markdown rendering.
Uses the streaming parser for memory-efficient processing of large files.
"""

import sys
import argparse
from typing import List, Optional
from pathlib import Path

# Add the project root to the path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from window_tools.cap3d_parser import StreamingCap3DParser
from window_tools.cap3d_models import ParsedCap3DData


class LayerInfo:
    """Simple container for layer information."""

    def __init__(self, name: str, layer_type: str, z_top: float, z_bottom: Optional[float] = None):
        self.name = name
        self.layer_type = layer_type  # 'interconnect', 'dielectric', 'via', 'substrate'
        self.z_top = z_top
        self.z_bottom = z_bottom if z_bottom is not None else 0.0
        self.thickness = self.z_top - self.z_bottom

    def __repr__(self):
        return f"LayerInfo(name='{self.name}', type='{self.layer_type}', z={self.z_top:.3f}μm, thickness={self.thickness:.3f}μm)"


def parse_cap3d_file(filepath: str) -> ParsedCap3DData:
    """Parse a CAP3D file using the streaming parser."""
    try:
        parser = StreamingCap3DParser(filepath)
        parsed_data = parser.parse_complete()
        return parsed_data
    except FileNotFoundError:
        print(f"Error: CAP3D file '{filepath}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing CAP3D file '{filepath}': {e}")
        sys.exit(1)


def extract_layer_info(parsed_data: ParsedCap3DData) -> List[LayerInfo]:
    """Extract and combine layer information from plate_medium and layer definitions."""
    layers = []

    # Extract plate_mediums information (dielectric layers with Z coordinates)
    plate_mediums = sorted(parsed_data.plate_mediums, key=lambda p: p.z_top)

    # Create dielectric layer info from plate_mediums
    z_prev = 0.0
    for i, plate in enumerate(plate_mediums):
        layer_name = getattr(plate, 'name', f'PLATE_MEDIUM_{i}')
        layer_info = LayerInfo(
            name=layer_name,
            layer_type='dielectric',
            z_top=plate.z_top,
            z_bottom=z_prev
        )
        layers.append(layer_info)
        z_prev = plate.z_top

    # Create a dictionary for conductor layers by name for easier merging
    conductor_layer_dict = {}
    for layer in parsed_data.layers:
        layer_type = layer.type if layer.type else 'interconnect'
        # Normalize via type names
        if 'via' in layer.name.lower() or layer_type == 'via':
            layer_type = 'via'

        layer_info = LayerInfo(
            name=layer.name,
            layer_type=layer_type,
            z_top=0.0,  # Will be updated based on conductor positions
            z_bottom=0.0
        )

        # If layer already exists, keep the existing type and merge info
        if layer.name in conductor_layer_dict:
            existing = conductor_layer_dict[layer.name]
            # Prefer 'via' type over 'interconnect' for via layers
            if layer_type == 'via':
                existing.layer_type = 'via'
        else:
            conductor_layer_dict[layer.name] = layer_info

    # Try to match conductor layers to Z positions based on conductor blocks
    conductor_blocks = [block for block in parsed_data.blocks if block.type == 'conductor']

    if conductor_blocks:
        conductor_z_positions = {}

        # Collect Z positions from all conductor blocks
        for block in conductor_blocks:
            if hasattr(block, 'base') and len(block.base) >= 3:
                z_pos = block.base[2]  # Z coordinate
                if hasattr(block, 'layer') and block.layer is not None:
                    if block.layer not in conductor_z_positions:
                        conductor_z_positions[block.layer] = []
                    conductor_z_positions[block.layer].append(z_pos)

        # Update conductor layer Z positions
        for layer_idx, z_positions in conductor_z_positions.items():
            if z_positions:
                avg_z = sum(z_positions) / len(z_positions)
                # Find matching conductor layer by layer index
                if layer_idx < len(parsed_data.layers):
                    layer_name = parsed_data.layers[layer_idx].name
                    if layer_name in conductor_layer_dict:
                        layer_info = conductor_layer_dict[layer_name]
                        # Conductors start at the Z position, but we want to show them
                        # as a layer, so we'll position them at their top edge
                        layer_info.z_top = avg_z
                        # Estimate thickness based on layer name (simplified)
                        if 'metal' in layer_info.name.lower():
                            layer_info.thickness = 0.14  # Typical metal thickness
                        elif 'via' in layer_info.name.lower():
                            layer_info.thickness = 0.08  # Typical via thickness
                        elif 'mcon' in layer_info.name.lower():
                            layer_info.thickness = 0.05  # Contact thickness
                        layer_info.z_bottom = layer_info.z_top - layer_info.thickness

    # Convert dictionary back to list
    conductor_layers = list(conductor_layer_dict.values())

    # Combine and sort all layers by Z position
    all_layers = layers + conductor_layers

    # Remove layers with zero Z position (unmatched conductors) if we have plate mediums
    if plate_mediums:
        all_layers = [layer for layer in all_layers if layer.z_top > 0]

    # Sort by Z position (bottom to top)
    all_layers.sort(key=lambda l: l.z_top)

    return all_layers


def print_layer_summary(layers: List[LayerInfo], args):
    """Print the layer stack summary table in a clean format."""
    if args.conductors_only:
        layers = [layer for layer in layers if layer.layer_type == 'interconnect']

    if not layers:
        print("No layers found matching the specified criteria.")
        return

    print(f"Layer Summary ({len(layers)} layers):")
    print("-" * 60)

    # Table header - looks good in both plain text and markdown
    if args.show_thickness:
        print(f"{'Layer Name':<20} | {'Type':<12} | {'Bottom Z':<9} | {'Top Z':<9} | {'Thickness':<10}")
        print("-" * 84)
    else:
        print(f"{'Layer Name':<20} | {'Type':<12} | {'Bottom Z':<9} | {'Top Z':<9}")
        print("-" * 72)

    # Table rows - display from top to bottom (highest Z first)
    for layer in reversed(layers):
        layer_name = layer.name[:19]  # Truncate if too long
        layer_type = layer.layer_type[:11]  # Truncate if too long
        z_bottom = f"{layer.z_bottom:7.3f}μm"
        z_top = f"{layer.z_top:7.3f}μm"

        if args.show_thickness and layer.thickness > 0:
            thickness = f"{layer.thickness:7.3f}μm"
            print(f"  {layer_name:<19} | {layer_type:<12} | {z_bottom:<9} | {z_top:<9} | {thickness:<10}")
        else:
            if args.show_thickness:
                print(f"  {layer_name:<19} | {layer_type:<12} | {z_bottom:<9} | {z_top:<9} | {'':<10}")
            else:
                print(f"  {layer_name:<19} | {layer_type:<12} | {z_bottom:<9} | {z_top:<9}")


def main():
    """Main function for the layer stack summary."""
    parser = argparse.ArgumentParser(
        description="Display a clean layer stack summary table from CAP3D files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s designs/cap3d/test_l_shapes.cap3d
  %(prog)s designs/cap3d/test_l_shapes.cap3d --conductors-only
  %(prog)s designs/cap3d/test_l_shapes.cap3d --show-thickness
        """
    )

    parser.add_argument('cap3d_file', help='Path to the CAP3D file to analyze')
    parser.add_argument('--conductors-only', action='store_true',
                       help='Show only conductor (interconnect) layers')
    parser.add_argument('--show-thickness', action='store_true',
                       help='Show layer thickness calculations')

    args = parser.parse_args()

    # Validate input file
    if not Path(args.cap3d_file).exists():
        print(f"Error: File '{args.cap3d_file}' does not exist.")
        sys.exit(1)

    # Parse CAP3D file
    if args.verbose if hasattr(args, 'verbose') else False:
        print(f"Parsing CAP3D file: {args.cap3d_file}")

    parsed_data = parse_cap3d_file(args.cap3d_file)

    # Extract layer information
    layers = extract_layer_info(parsed_data)

    # Print summary table
    print_layer_summary(layers, args)


if __name__ == "__main__":
    main()

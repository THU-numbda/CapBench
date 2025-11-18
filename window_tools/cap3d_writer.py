"""
CAP3D Writer Utilities

Provides functions to write CAP3D files from extracted geometry and layer data.

This module is KLayout-agnostic aside from reading `.bbox` fields that expose
`left`, `right`, `top`, `bottom` numeric attributes in database units. Callers
should supply `dbu` to convert to microns.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


def _sorted_layer_entries(layer_map: Dict[str, Tuple[int, float, float]],
                          via_map: Dict[str, Tuple[int, float, float]]) -> List[Tuple[str, float, str]]:
    """Build sorted layer entries (name, z_center, type) for CAP3D <layer> section."""
    entries: List[Tuple[str, float, str]] = []
    for name, (_, z0, z1) in layer_map.items():
        z_center = 0.5 * (z0 + z1)
        entries.append((name, z_center, 'interconnect'))
    for name, (_, z0, z1) in via_map.items():
        z_center = 0.5 * (z0 + z1)
        entries.append((name, z_center, 'via'))
    # Sort bottom to top; tie-break by name for stability
    entries.sort(key=lambda t: (t[1], t[0]))
    return entries


def write_cap3d(
    output_path: str,
    *,
    # Window extents (microns)
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    # Database units -> microns scale
    dbu: float,
    # Margin factor for window and ground plane (1.0 = no margin, 1.1 = 10% margin)
    margin_factor: float = 1.1,
    # Dielectric stack as list of (name, z_top, dielectric)
    dielectric_stack: List[Tuple[str, float, float]],
    # Physical layer maps: name -> (gds_layer_num, z_bottom, z_top)
    layer_map: Dict[str, Tuple[int, float, float]],
    via_map: Dict[str, Tuple[int, float, float]],
    # Mapping name -> integer CAP3D layer id
    cap3d_layer_ids: Dict[str, int],
    # Shapes per net: net_name -> Iterable of (layer_name, bbox) where bbox is properly decomposed rectangle
    net_shapes: Dict[str, Iterable],
) -> None:
    """Write a CAP3D file to `output_path` from extracted shapes and layer data."""
    with open(output_path, 'w') as f:
        # Calculate margins for window and ground plane
        if margin_factor > 1.0:
            width = x_max - x_min
            height = y_max - y_min
            # margin_factor represents the percentage margin per side (e.g., 1.1 = 10% margin each side)
            margin_percentage_per_side = (margin_factor - 1.0)
            x_margin = width * margin_percentage_per_side
            y_margin = height * margin_percentage_per_side
            x_min_margin = x_min - x_margin
            y_min_margin = y_min - y_margin
            x_max_margin = x_max + x_margin
            y_max_margin = y_max + y_margin
        else:
            # No margin (margin_factor = 1.0)
            x_min_margin, y_min_margin = x_min, y_min
            x_max_margin, y_max_margin = x_max, y_max

        # Header and window
        f.write("<cap3d>\n")
        f.write("<window>\n")
        f.write("\tname case-0\n")
        z_top = float(dielectric_stack[-1][1]) if dielectric_stack else 0.0
        f.write(f"\tv1({x_min_margin:.4f},{y_min_margin:.4f},-0.0100)\n")
        f.write(f"\tv2({x_max_margin:.4f},{y_max_margin:.4f},{z_top:.4f})\n")
        f.write("</window>\n")

        # Dielectric plates
        for idx, (name, z_top, diel) in enumerate(dielectric_stack):
            # Fallback to generic name if somehow name is missing
            display_name = name if name and name.strip() else f"PLATE_MEDIUM_{idx}"
            # Ensure values are treated as float
            diel_value = float(diel) if not isinstance(diel, float) else diel
            z_top_value = float(z_top) if not isinstance(z_top, float) else z_top
            f.write("<plate_medium>\n")
            f.write(f"\tname {display_name}\n")
            f.write(f"\tdiel {diel_value:.1f}\n")
            f.write(f"\tz_top {z_top_value:.4f}\n")
            f.write("</plate_medium>\n")

        # Ground plane
        f.write("<conductor>\n")
        f.write("\tname GROUND\n")
        f.write("\t<block>\n")
        f.write("\t\tname 0\n")
        f.write("\t\tlayer 0\n")
        f.write(f"\t\tbasepoint({x_min_margin:.4f},{y_min_margin:.4f},-0.0100)\n")
        f.write(f"\t\tv1({x_max_margin - x_min_margin:.4f},0,0)\n")
        f.write(f"\t\tv2(0,{y_max_margin - y_min_margin:.4f},0)\n")
        f.write("\t\thvector(0,0,0.100000)\n")
        f.write("\t</block>\n")
        f.write("</conductor>\n")

        # Conductors
        block_id = 1
        for net_name in sorted(net_shapes.keys()):
            shapes = list(net_shapes[net_name])
            if not shapes:
                continue

            f.write("<conductor>\n")
            f.write(f"\tname {net_name}\n")

            for layer_name, bbox in shapes:
                # Determine physical z extents and CAP3D layer id
                if layer_name in layer_map:
                    _, z_bottom, z_top = layer_map[layer_name]
                    layer_num = cap3d_layer_ids.get(layer_name, 2)
                elif layer_name in via_map:
                    _, z_bottom, z_top = via_map[layer_name]
                    layer_num = cap3d_layer_ids.get(layer_name, 2)
                else:
                    continue

                # Use the properly decomposed rectangle directly
                # KLayout's decomposition ensures no overlaps between shapes
                x1 = bbox.left * dbu
                y1 = bbox.bottom * dbu
                x2 = bbox.right * dbu
                y2 = bbox.top * dbu
                width = x2 - x1
                height = y2 - y1
                z_height = z_top - z_bottom

                f.write("\t\t<block>\n")
                f.write(f"\t\t\tname {block_id}\n")
                f.write(f"\t\t\tlayer {layer_num}\n")
                f.write(f"\t\t\tbasepoint({x1:.4f},{y1:.4f},{z_bottom:.4f})\n")
                f.write(f"\t\t\tv1({width:.4f},0,0)\n")
                f.write(f"\t\t\tv2(0,{height:.4f},0)\n")
                f.write(f"\t\t\thvector(0,0,{z_height:.6f})\n")
                f.write("\t\t</block>\n")

                block_id += 1

            f.write("</conductor>\n")

        # Layer definitions
        f.write("<layer>\n")
        f.write("\tname SUBSTRATE\n")
        f.write("\tid 0\n")
        f.write("\ttype substrate\n")
        f.write("</layer>\n")

        entries = _sorted_layer_entries(layer_map, via_map)
        for idx, (name, _zc, ltype) in enumerate(entries, start=1):
            display_name = 'POLY' if name == 'poly' else name
            f.write("<layer>\n")
            f.write(f"\tname {display_name}\n")
            f.write(f"\tid {idx}\n")
            f.write(f"\ttype {ltype}\n")
            f.write("</layer>\n")

        dielectric_start_id = len(entries) + 1
        for i, (name, _, _) in enumerate(dielectric_stack):
            # Fallback to generic name if somehow name is missing
            display_name = name if name and name.strip() else f"PLATE_MEDIUM_{i}"
            f.write("<layer>\n")
            f.write(f"\tname {display_name}\n")
            f.write(f"\tid {dielectric_start_id + i}\n")
            f.write("\ttype dielectric\n")
            f.write("</layer>\n")

        # Tasks: one per net
        for net_name in sorted(net_shapes.keys()):
            f.write("<task>\n")
            f.write("\t<capacitance>\n")
            f.write(f"\t\t{net_name}\n")
            f.write("\t</capacitance>\n")
            f.write("</task>\n")

        f.write("</cap3d>\n")


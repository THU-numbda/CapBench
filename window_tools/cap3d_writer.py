"""
CAP3D Writer Utilities

Provides functions to write CAP3D files from extracted geometry and layer data.

This module is KLayout-agnostic aside from reading `.bbox` fields that expose
`left`, `right`, `top`, `bottom` numeric attributes in database units. Callers
should supply `dbu` to convert to microns.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple


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
    # Optional explicit dielectric medium sections, one rectangular block per section.
    # Each item expects: name, layer_name, diel, base, v1, v2, hvec
    medium_sections: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Write a CAP3D file to `output_path` from extracted shapes and layer data."""
    with open(output_path, 'w') as f:
        medium_sections = list(medium_sections or [])
        conformal_layer_names: List[str] = []
        for medium in medium_sections:
            layer_name = str(medium["layer_name"]).strip()
            if layer_name and layer_name not in conformal_layer_names:
                conformal_layer_names.append(layer_name)

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

        entries = _sorted_layer_entries(layer_map, via_map)
        dielectric_start_id = len(entries) + 1
        conformal_layer_ids = {
            layer_name: dielectric_start_id + len(dielectric_stack) + idx
            for idx, layer_name in enumerate(conformal_layer_names)
        }

        for block_id, medium in enumerate(medium_sections):
            layer_name = str(medium["layer_name"]).strip()
            layer_num = conformal_layer_ids.get(layer_name)
            if layer_num is None:
                continue
            diel_value = float(medium["diel"])
            base = medium["base"]
            v1 = medium["v1"]
            v2 = medium["v2"]
            hvec = medium["hvec"]
            section_name = str(medium.get("name", f"rect_conf_{block_id}")).strip() or f"rect_conf_{block_id}"

            f.write("<medium>\n")
            f.write(f"\tname {section_name}\n")
            f.write("\t<block>\n")
            f.write(f"\t\tname {block_id}\n")
            f.write(f"\t\tlayer {layer_num}\n")
            f.write(f"\t\tbasepoint({float(base[0]):.4f},{float(base[1]):.4f},{float(base[2]):.4f})\n")
            f.write(f"\t\tv1({float(v1[0]):.4f},{float(v1[1]):.4f},{float(v1[2]):.4f})\n")
            f.write(f"\t\tv2({float(v2[0]):.4f},{float(v2[1]):.4f},{float(v2[2]):.4f})\n")
            f.write(f"\t\thvector({float(hvec[0]):.4f},{float(hvec[1]):.4f},{float(hvec[2]):.6f})\n")
            f.write("\t</block>\n")
            f.write(f"\tdiel {diel_value:.4f}\n")
            f.write("</medium>\n")

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

        for idx, (name, _zc, ltype) in enumerate(entries, start=1):
            display_name = 'POLY' if name == 'poly' else name
            f.write("<layer>\n")
            f.write(f"\tname {display_name}\n")
            f.write(f"\tid {idx}\n")
            f.write(f"\ttype {ltype}\n")
            f.write("</layer>\n")

        for i, (name, _, _) in enumerate(dielectric_stack):
            # Fallback to generic name if somehow name is missing
            display_name = name if name and name.strip() else f"PLATE_MEDIUM_{i}"
            f.write("<layer>\n")
            f.write(f"\tname {display_name}\n")
            f.write(f"\tid {dielectric_start_id + i}\n")
            f.write("\ttype dielectric\n")
            f.write("</layer>\n")

        for layer_name in conformal_layer_names:
            f.write("<layer>\n")
            f.write(f"\tname {layer_name}\n")
            f.write(f"\tid {conformal_layer_ids[layer_name]}\n")
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


def write_parsed_cap3d(output_path: str, parsed_data) -> None:
    """Write a CAP3D file from ParsedCap3DData.

    This function writes a CAP3D file from a ParsedCap3DData object,
    which is the output of StreamingCap3DParser. This enables round-trip
    parsing and modification of CAP3D files (e.g., for partitioning).

    Args:
        output_path: Path to output CAP3D file
        parsed_data: ParsedCap3DData object containing the CAP3D data
    """
    with open(output_path, 'w') as f:
        def write_block(block, indent: str) -> None:
            indent2 = indent + "\t"
            f.write(f"{indent}<block>\n")
            f.write(f"{indent2}name {block.name}\n")
            if block.layer is not None:
                f.write(f"{indent2}layer {int(block.layer)}\n")
            base = block.base
            v1 = block.v1
            v2 = block.v2
            hvec = block.hvec
            f.write(f"{indent2}basepoint({base[0]:.4f},{base[1]:.4f},{base[2]:.4f})\n")
            f.write(f"{indent2}v1({v1[0]:.4f},{v1[1]:.4f},{v1[2]:.4f})\n")
            f.write(f"{indent2}v2({v2[0]:.4f},{v2[1]:.4f},{v2[2]:.4f})\n")
            f.write(f"{indent2}hvector({hvec[0]:.4f},{hvec[1]:.4f},{hvec[2]:.6f})\n")
            f.write(f"{indent}</block>\n")

        def write_poly(poly, indent: str) -> None:
            indent2 = indent + "\t"
            f.write(f"{indent}<poly>\n")
            f.write(f"{indent2}name {poly.name}\n")
            base = poly.base
            v1 = poly.v1
            v2 = poly.v2
            hvec = poly.hvector
            f.write(f"{indent2}basepoint({base[0]:.4f},{base[1]:.4f},{base[2]:.4f})\n")
            f.write(f"{indent2}v1({v1[0]:.4f},{v1[1]:.4f},{v1[2]:.4f})\n")
            f.write(f"{indent2}v2({v2[0]:.4f},{v2[1]:.4f},{v2[2]:.4f})\n")
            f.write(f"{indent2}hvector({hvec[0]:.4f},{hvec[1]:.4f},{hvec[2]:.6f})\n")
            if poly.coordinates:
                coords_text = " ".join(
                    f"({x:.4f},{y:.4f})" for x, y in poly.coordinates
                )
                f.write(f"{indent2}<coord>{coords_text}</coord>\n")
            f.write(f"{indent}</poly>\n")

        # Header
        f.write("<cap3d>\n")

        # Window section
        if parsed_data.window:
            f.write("<window>\n")
            if parsed_data.window.name:
                f.write(f"\tname {parsed_data.window.name}\n")
            v1 = parsed_data.window.v1 if parsed_data.window.v1 is not None else (0, 0, -0.01)
            v2 = parsed_data.window.v2 if parsed_data.window.v2 is not None else (0, 0, 0)
            f.write(f"\tv1({v1[0]:.4f},{v1[1]:.4f},{v1[2]:.4f})\n")
            f.write(f"\tv2({v2[0]:.4f},{v2[1]:.4f},{v2[2]:.4f})\n")
            if parsed_data.window.boundary_type:
                f.write(f"\tboundary_type {parsed_data.window.boundary_type}\n")
            f.write("</window>\n")

        # Dielectric plates (plate_medium sections)
        for medium in parsed_data.plate_mediums:
            f.write("<plate_medium>\n")
            f.write(f"\tname {medium.name}\n")
            f.write(f"\tdiel {medium.diel:.1f}\n")
            f.write(f"\tz_top {medium.z_top:.4f}\n")
            f.write("</plate_medium>\n")

        conductor_blocks = {}
        medium_blocks = {}
        medium_diels = {}
        conductor_order = []
        medium_order = []
        for block in parsed_data.blocks:
            parent = block.parent_name or "unknown"
            if block.type == 'medium':
                if parent not in medium_blocks:
                    medium_blocks[parent] = []
                    medium_order.append(parent)
                medium_blocks[parent].append(block)
                if block.diel is not None and parent not in medium_diels:
                    medium_diels[parent] = block.diel
            else:
                if parent not in conductor_blocks:
                    conductor_blocks[parent] = []
                    conductor_order.append(parent)
                conductor_blocks[parent].append(block)

        poly_by_conductor = {}
        poly_by_medium = {}
        for poly in parsed_data.poly_elements:
            parent = poly.parent_name or "unknown"
            section_type = getattr(poly, "section_type", None)
            if section_type == "medium":
                if parent not in poly_by_medium:
                    poly_by_medium[parent] = []
                    if parent not in medium_blocks and parent not in medium_order:
                        medium_order.append(parent)
                poly_by_medium[parent].append(poly)
            elif section_type == "conductor":
                if parent not in poly_by_conductor:
                    poly_by_conductor[parent] = []
                    if parent not in conductor_blocks and parent not in conductor_order:
                        conductor_order.append(parent)
                poly_by_conductor[parent].append(poly)
            elif parent in medium_blocks and parent not in conductor_blocks:
                if parent not in poly_by_medium:
                    poly_by_medium[parent] = []
                    if parent not in medium_order:
                        medium_order.append(parent)
                poly_by_medium[parent].append(poly)
            else:
                if parent not in poly_by_conductor:
                    poly_by_conductor[parent] = []
                    if parent not in conductor_order:
                        conductor_order.append(parent)
                poly_by_conductor[parent].append(poly)

        for medium_name in medium_order:
            blocks = medium_blocks.get(medium_name, [])
            polys = poly_by_medium.get(medium_name, [])
            if not blocks and not polys:
                continue
            f.write("<medium>\n")
            f.write(f"\tname {medium_name}\n")
            diel = medium_diels.get(medium_name)
            if diel is not None:
                f.write(f"\tdiel {diel:.1f}\n")
            for block in blocks:
                write_block(block, "\t")
            for poly in polys:
                write_poly(poly, "\t")
            f.write("</medium>\n")

        # Write conductors (skip ground which is typically named "GROUND")
        for parent_name in conductor_order:
            if parent_name == "GROUND":
                continue

            blocks = conductor_blocks.get(parent_name, [])
            polys = poly_by_conductor.get(parent_name, [])
            if not blocks and not polys:
                continue

            f.write("<conductor>\n")
            f.write(f"\tname {parent_name}\n")

            for block in blocks:
                write_block(block, "\t")
            for poly in polys:
                write_poly(poly, "\t")

            f.write("</conductor>\n")

        # Write ground plane (if exists)
        ground_blocks = conductor_blocks.get("GROUND", [])
        ground_polys = poly_by_conductor.get("GROUND", [])
        if ground_blocks or ground_polys:
            f.write("<conductor>\n")
            f.write("\tname GROUND\n")
            for block in ground_blocks:
                write_block(block, "\t")
            for poly in ground_polys:
                write_poly(poly, "\t")
            f.write("</conductor>\n")

        # Layer definitions
        f.write("<layer>\n")
        f.write("\tname SUBSTRATE\n")
        f.write("\tid 0\n")
        f.write("\ttype substrate\n")
        f.write("</layer>\n")

        # Write layer definitions from parsed data
        layer_id = 1
        for layer_obj in parsed_data.layers:
            if layer_obj.name and layer_obj.name.lower() != 'substrate':
                f.write("<layer>\n")
                f.write(f"\tname {layer_obj.name}\n")
                f.write(f"\tid {layer_id}\n")
                f.write(f"\ttype {layer_obj.type}\n")
                f.write("</layer>\n")
                layer_id += 1

        # Dielectric layer IDs (for plate_mediums)
        for medium in parsed_data.plate_mediums:
            f.write("<layer>\n")
            f.write(f"\tname {medium.name}\n")
            f.write(f"\tid {layer_id}\n")
            f.write("\ttype dielectric\n")
            f.write("</layer>\n")
            layer_id += 1

        # Tasks (capacitance targets)
        if parsed_data.task and parsed_data.task.capacitance_targets:
            for target in parsed_data.task.capacitance_targets:
                f.write("<task>\n")
                f.write("\t<capacitance>\n")
                f.write(f"\t\t{target}\n")
                f.write("\t</capacitance>\n")
                f.write("</task>\n")

        # Footer
        f.write("</cap3d>\n")

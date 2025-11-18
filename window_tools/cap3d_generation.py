#!/usr/bin/env python3
"""
Convert DEF+GDS to CAP3D format, preserving DEF net names.

USAGE:
    klayout -b -zz -r window_tools/cap3d_generation.py -- [OPTIONS]

    Or run with defaults:
    klayout -b -zz -r window_tools/cap3d_generation.py

OPTIONS:
    --gds FILE       GDS layout file (default: ../designs/gds/gcd.gds)
    --def FILE       DEF placement file (default: ../designs/def/gcd.def)
    --stack FILE     YAML layer stack config (default: ../designs/tech/nangate45/nangate45_stack.yaml)
    --layermap FILE  KLayout layer map file (default: ../designs/tech/nangate45/nangate45.layermap)
    -o/--output FILE Output cap3d file (default: ../designs/cap3d/gcd.cap3d)

EXAMPLE:
    klayout -b -zz -r window_tools/cap3d_generation.py -- --gds design.gds --def design.def -o output.cap3d
"""

import argparse
import io
import re
import sys
import yaml
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, DefaultDict

from window_tools.cap3d_writer import write_cap3d
from window_tools.def_parser import parse_def

try:
    import pya
except ImportError:
    print("ERROR: This script must be run with KLayout in batch mode!")
    sys.exit(1)


# Strip everything except alphanumerics, underscore, and dot.
NET_NAME_CLEAN_RE = re.compile(r"[^A-Za-z0-9_.]")

@dataclass
class LayerEntry:
    """Physical layer metadata with explicit GDS layer/datatype pairing."""

    gds_layer: int
    datatype: int
    z_bottom: float
    z_top: float


class DEF2Cap3D:
    """Convert DEF+GDS to cap3d format using KLayout's layout-to-netlist extraction.

    Required inputs:
    - GDS layout file
    - DEF placement file
    - YAML layer stack configuration (conductor/dielectric thicknesses and ER values)
    - KLayout layer map file (GDS layer number to canonical name mapping)
    """

    def __init__(self, gds_file: str, def_file: str,
                 output_file: str, stack_file: str, layermap_file: str,
                 debug_probe: bool = False,
                 process_node: Optional[str] = None,
                 lef_files: Optional[List[str]] = None):
        self.gds_file = Path(gds_file)
        self.def_file = Path(def_file)
        self.output_file = Path(output_file)
        # Ensure output directory exists
        try:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.stack_file = Path(stack_file)
        self.layermap_file = Path(layermap_file)
        self.debug_probe = debug_probe
        inferred_node = process_node if process_node else self._infer_process_node()
        self.process_node = inferred_node.lower() if isinstance(inferred_node, str) else None

        # Layer configuration (populated from stack and layermap files)
        self.layer_map: Dict[str, LayerEntry] = {}  # conductor name -> LayerEntry
        self.dielectric_stack: List[Tuple[str, float, float]] = []     # [(name, z_top, dielectric_constant), ...]

        # KLayout objects
        self.layout = None
        self.top_cell = None
        self.def_layout = None
        self.def_top_cell = None
        self.l2n = None

        # For each canonical layer name, map layout layer_idx -> L2N layer region
        self.layer_regions: Dict[str, Dict[int, pya.LayoutToNetlist.Layer]] = {}
        self._def_units: Optional[int] = None
        provided_lefs = [Path(p) for p in lef_files] if lef_files else []
        self._lef_files: List[Path] = provided_lefs if provided_lefs else self._resolve_lef_files()

        # Net name mappings
        self.cluster_to_net = {}  # cluster_id -> net_name
        self.def_nets = set()     # nets from DEF
        self.unnamed_count = 0
        self.floating_nets: Dict[str, int] = {}
        self._sanitized_net_name_cache: Dict[str, str] = {}
        self._used_net_names: Set[str] = set()

    
    def _infer_process_node(self) -> Optional[str]:
        """Infer process node name from stack or layermap filenames."""
        known_nodes = {"nangate45", "asap7", "sky130hd"}
        for path in (getattr(self, "stack_file", None), getattr(self, "layermap_file", None)):
            if not path:
                continue
            stem = path.stem.lower()
            if stem in known_nodes:
                return stem
            for node in known_nodes:
                if node in stem:
                    return node
            for part in path.parts:
                lower = part.lower()
                if lower in known_nodes:
                    return lower
                for node in known_nodes:
                    if node in lower:
                        return node
        return None

    def _resolve_lef_files(self) -> List[Path]:
        """Locate LEF file(s) associated with the current process node."""
        candidates: List[Path] = []
        potential_paths: List[Path] = []

        stack_file = getattr(self, "stack_file", None)
        if stack_file:
            potential_paths.append(stack_file.with_suffix(".lef"))
        if getattr(self, "process_node", None) and stack_file:
            base_dir = stack_file.parent
            potential_paths.append(base_dir / f"{self.process_node}.lef")
            potential_paths.append(base_dir / f"{self.process_node}.tlef")

        seen: Set[Path] = set()
        for candidate in potential_paths:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            if resolved.exists():
                candidates.append(resolved)
                seen.add(resolved)

        return candidates

    def _sanitize_net_name(self, name: str) -> str:
        """Return a safe net name with disallowed characters removed."""
        cached = self._sanitized_net_name_cache.get(name)
        if cached is not None:
            return cached

        sanitized = NET_NAME_CLEAN_RE.sub("", name).strip()
        if not sanitized:
            sanitized = "NET"

        candidate = sanitized
        suffix = 1
        while candidate in self._used_net_names:
            candidate = f"{sanitized}_{suffix}"
            suffix += 1

        self._used_net_names.add(candidate)
        self._sanitized_net_name_cache[name] = candidate
        return candidate

    def _load_yaml_stack(self):
        """Parse YAML layer stack file and build layer maps and dielectric stack.

        YAML format:
        layers:
          - [name, thickness_um]                      # conductor
          - [name, thickness_um, dielectric_constant] # dielectric

        Populates self.layer_map and self.dielectric_stack.
        """
        with self.stack_file.open() as f:
            data = yaml.safe_load(f)

        # Store tech_data for via definitions
        self.tech_data = data

        stack = data.get('stack', [])
        if not stack:
            raise RuntimeError(f"No stack found in stack file: {self.stack_file}")

        # Build z-heights by accumulating thicknesses from bottom to top
        z = 0.0
        conductor_layers = []  # List of (name, z_bottom, z_top) for processing later
        dielectric_stack: List[Tuple[str, float, float]] = []      # [(name, z_top, dielectric_constant), ...]

        for layer in stack:
            if not isinstance(layer, dict):
                raise ValueError(f"Invalid layer entry format: {layer}")

            name = layer.get('name')
            layer_type = layer.get('type')
            thickness = layer.get('thickness_um', 0.0)

            if not name or not layer_type:
                raise ValueError(f"Invalid layer entry: missing name or type: {layer}")

            # Update cumulative z-height
            z += thickness
            z_top = z  # Current top of this layer (always defined)

            # Add conductor layers only (type: 'metal')
            if layer_type == 'metal':
                z_bottom = z - thickness  # Bottom of this layer
                conductor_layers.append((name, z_bottom, z_top))

                # Directly assign Z-coordinates to matching layer map entries (require exact match)
                if name in self.layer_map:
                    entry = self.layer_map[name]
                    self.layer_map[name] = LayerEntry(
                        gds_layer=entry.gds_layer,
                        datatype=entry.datatype,
                        z_bottom=z_bottom,
                        z_top=z_top,
                    )

            elif layer_type == 'dielectric':
                dielectric = float(layer.get('er', 1.0))
                z_top_value = float(z_top)
                dielectric_stack.append((name, z_top_value, dielectric))

        # Store results
        self.dielectric_stack = dielectric_stack

        # Process via definitions now that we have all conductor layer Z-coordinates
        if self.tech_data and 'vias' in self.tech_data:
            # Create conductor z-map for direct lookup
            conductor_z_map = {name: (z_bottom, z_top) for name, z_bottom, z_top in conductor_layers}

            matched_vias = 0
            skipped_vias = 0

            for via_name, via_def in self.tech_data['vias'].items():
                if via_name not in self.layer_map:
                    print(f"Error: {via_name} not found in layermap - layermap and tech stack names must match exactly")
                    skipped_vias += 1
                    continue

                from_layer = via_def.get('from')
                to_layer = via_def.get('to')

                # Direct lookup using from/to field names (require exact match)
                if from_layer in conductor_z_map and to_layer in conductor_z_map:
                    from_z_bottom, from_z_top = conductor_z_map[from_layer]
                    to_z_bottom, to_z_top = conductor_z_map[to_layer]

                    # YAML via definitions: from=lower_layer, to=upper_layer (intuitive)
                    # Example: V1: { from: M1, to: M2 } means V1 connects lower M1 to upper M2
                    lower_layer = from_layer      # YAML 'from' field = lower layer
                    upper_layer = to_layer        # YAML 'to' field = upper layer
                    lower_z_bottom = from_z_bottom
                    lower_z_top = from_z_top
                    upper_z_bottom = to_z_bottom
                    upper_z_top = to_z_top

                    # Verify layer stack order (lower layer should be below upper layer)
                    if lower_z_top > upper_z_bottom:
                        print(f"Error: {via_name} invalid layer stack order (lower={lower_layer} z={lower_z_bottom:.3f}-{lower_z_top:.3f}, upper={upper_layer} z={upper_z_bottom:.3f}-{upper_z_top:.3f})")
                        skipped_vias += 1
                        continue

                    # Via spans from top of lower layer to bottom of upper layer
                    via_z_bottom = lower_z_top   # Top of lower layer (where via starts)
                    via_z_top = upper_z_bottom    # Bottom of upper layer (where via ends)

                    self.layer_map[via_name] = LayerEntry(
                        gds_layer=self.layer_map[via_name].gds_layer,
                        datatype=self.layer_map[via_name].datatype,
                        z_bottom=via_z_bottom,
                        z_top=via_z_top,
                    )
                    matched_vias += 1
                else:
                    skipped_vias += 1
                    print(f"Error: {via_name} could not find layers (from={from_layer}, to={to_layer}) in conductor stack - names must match exactly")

  
        # Return conductor data for any downstream usage
        conductor_z_map = {name: (z_bottom, z_top) for name, z_bottom, z_top in conductor_layers}
        return conductor_z_map

    
    def _load_layermap(self):
        """Parse KLayout layer map file and populate GDS layer numbers.

        Standard KLayout format:
          source_layer/datatype : target_name (target_layer/datatype)
          Example: 11/0 : metal1 (11/0)

        Populates self.layer_map with GDS layer numbers for all layers.
        Z-heights are set to (0, 0) initially and filled in later by stack file.
        """
        with self.layermap_file.open() as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#'):
                    continue

                # Parse KLayout layer map format: "layer/datatype : name (layer/datatype)"
                if ':' not in s:
                    continue

                parts = s.split(':')
                if len(parts) < 2:
                    continue

                # Parse target (right side): "name (layer/datatype)" or just "name"
                target = parts[1].strip()
                if '(' in target:
                    lname = target.split('(')[0].strip()
                else:
                    lname = target.strip()

                # Parse source (left side): "layer/datatype" or "layer"
                source = parts[0].strip()
                lnum = 0
                dtype = 0
                if '/' in source:
                    tokens = source.split('/', 1)
                    try:
                        lnum = int(tokens[0].strip())
                        dtype = int(tokens[1].strip())
                    except ValueError:
                        continue
                else:
                    try:
                        lnum = int(source)
                    except ValueError:
                        continue

                # Store all layers from layermap - layer types will be determined from YAML stack
                # Store all layers in layer_map regardless of type
                # Via detection will be handled by YAML vias section
                self.layer_map[lname] = LayerEntry(
                    gds_layer=lnum,
                    datatype=dtype,
                    z_bottom=0.0,
                    z_top=0.0,
                )

    
    def load_layouts(self):
        """Load GDS and DEF files."""
        # Load GDS
        self.layout = pya.Layout()
        self.layout.read(str(self.gds_file))
        self.top_cell = self.layout.top_cell()
        if not self.top_cell:
            raise RuntimeError("No top cell found in GDS file")

        # Flatten the layout to get individual primitive shapes
        flat_cell_index = self.layout.add_cell("FLAT")
        flat_cell = self.layout.cell(flat_cell_index)
        flat_cell.copy_tree(self.top_cell)
        flat_cell.flatten(True)  # True = prune empty cells after flattening
        self.top_cell = flat_cell

        # Load DEF
        try:
            def_data = parse_def(self.def_file)
            self._def_units = def_data.units if def_data and def_data.units else None
        except Exception:
            self._def_units = None

        self.def_layout = pya.Layout()
        options = pya.LoadLayoutOptions()
        lefdef = pya.LEFDEFReaderConfiguration()
        lefdef.produce_net_names = True
        lefdef.net_property_name = "NET"
        lefdef.read_all_layers = True
        if self._lef_files:
            lefdef.lef_files = [str(path) for path in self._lef_files]
        if self._def_units:
            try:
                lefdef.dbu = 1.0 / float(self._def_units)
            except Exception:
                pass
        options.lefdef_config = lefdef
        self.def_layout.read(str(self.def_file), options)
        if self._def_units:
            try:
                self.def_layout.dbu = 1.0 / float(self._def_units)
            except Exception:
                pass
        self.def_top_cell = self.def_layout.top_cell()
        if not self.def_top_cell:
            raise RuntimeError("No top cell found in DEF file")

    def run_l2n_extraction(self):
        """Run L2N on flattened GDS to find geometric clusters."""
        # Helper: collect all layout layer indices in GDS for a given layer number (any datatype)
        def collect_indices(entry: LayerEntry) -> List[int]:
            idxs: List[int] = []
            for li in range(self.layout.layers()):
                info = self.layout.get_info(li)
                if not info:
                    continue
                if info.layer == entry.gds_layer and info.datatype == entry.datatype:
                    idxs.append(li)
            return idxs

        # Use flat layout for L2N (layout is already flattened)
        rsi = pya.RecursiveShapeIterator(self.layout, self.top_cell, [])
        self.l2n = pya.LayoutToNetlist(rsi)

        # Create layer regions (conductors)
        # Track used layer names to avoid duplicates
        used_names = set()
        # Conductor layers are populated in self.layer_map for downstream use
        for name, entry in self.layer_map.items():
            idxs = collect_indices(entry)
            if not idxs:
                continue
            self.layer_regions[name] = {}
            for i, li in enumerate(idxs):
                # Create unique layer name to avoid conflicts
                # Use format: name_idx where idx is the index in the idxs list
                unique_name = f"{name}_{i}"
                if unique_name in used_names:
                    # If still conflict, add layout index
                    unique_name = f"{name}_{i}_{li}"
                used_names.add(unique_name)
                self.layer_regions[name][li] = self.l2n.make_layer(li, unique_name)

        # Report presence/absence
        # Connect all conductor layers dynamically (all layers in layer_map are considered conductors)
        conductor_names = list(self.layer_regions.keys())
        for name in conductor_names:
            if name in self.layer_regions:
                for lr in self.layer_regions[name].values():
                    self.l2n.connect(lr)

        # Connect vias using YAML via definitions with proper L2N connectivity
        if self.tech_data and 'vias' in self.tech_data:
            for vname, via_def in self.tech_data['vias'].items():
                via_layers = self.layer_regions.get(vname)
                if not via_layers:
                    continue

                from_layer = via_def.get('from')
                to_layer = via_def.get('to')
                lower_regions = self.layer_regions.get(from_layer) if from_layer else None
                upper_regions = self.layer_regions.get(to_layer) if to_layer else None

                for via_region in via_layers.values():
                    if lower_regions:
                        for lr in lower_regions.values():
                            self.l2n.connect(via_region, lr)
                    if upper_regions:
                        for ur in upper_regions.values():
                            self.l2n.connect(via_region, ur)

        self.l2n.extract_netlist()

        netlist = self.l2n.netlist()
        top_circuit = netlist.circuit_by_name(self.top_cell.name)
        if top_circuit is None and hasattr(netlist, "top_circuit"):
            top_circuit = netlist.top_circuit()
        if top_circuit is None and hasattr(netlist, "each_circuit"):
            for circuit in netlist.each_circuit():
                top_circuit = circuit
                break

        if top_circuit is None:
            raise RuntimeError("No top circuit found after L2N extraction")

    def match_def_nets_to_clusters(self):
        """Match DEF net names (including SPECIALNETS) to GDS clusters."""

        probe_points: Dict[str, List[Tuple[pya.Point, Optional[str]]]] = {}
        probe_layer_names: DefaultDict[str, Set[str]] = defaultdict(set)
        # Track used layer names to avoid conflicts (for additional layer creation)
        used_names: Set[str] = set()
        extra_via_layer_cache: Dict[Tuple[str, int], pya.LayoutToNetlist.Layer] = {}
        # Convert DEF coords (in microns from our parser) -> GDS DBU
        um_to_dbu = (1.0 / self.layout.dbu) if self.layout.dbu > 0 else 1.0
        dx = 0
        dy = 0

        # Use our DEF parser to iterate routed segments and probe at each segment center
        try:
            from window_tools.def_parser import parse_def as _parse_def
        except Exception as e:
            raise RuntimeError(f"Failed to import DEF parser: {e}")

        def_data = _parse_def(self.def_file)

        # Optional debug: build geometric Regions per canonical layer to test midpoint-inside
        geom_regions: Dict[str, Optional[pya.Region]] = {}
        geom_stats: Dict[str, Dict[str, int]] = {}

        def _get_or_build_region(canonical_layer: str) -> Optional[pya.Region]:
            if not self.debug_probe:
                return None
            if canonical_layer in geom_regions:
                return geom_regions[canonical_layer]
            entry = self.layer_map.get(canonical_layer)
            if not entry:
                geom_regions[canonical_layer] = None
                return None
            idxs: List[int] = []
            for li in range(self.layout.layers()):
                info = self.layout.get_info(li)
                if info and info.layer == entry.gds_layer and info.datatype == entry.datatype:
                    idxs.append(li)
            if not idxs:
                geom_regions[canonical_layer] = None
                return None
            reg = pya.Region()
            for li in idxs:
                shapes = self.top_cell.shapes(li)
                for sh in shapes.each():
                    if sh.is_box():
                        reg.insert(sh.box)
                    elif sh.is_polygon():
                        reg.insert(sh.polygon)
                    elif sh.is_path():
                        reg.insert(sh.path.polygon())
            geom_regions[canonical_layer] = reg
            return reg

        def add_segment_midpoints(net_obj):
            lname_set: Set[str] = set()
            ep_layers: DefaultDict[Tuple[int, int], Set[str]] = defaultdict(set)
            for seg in getattr(net_obj, 'routing', []) or []:
                lname = str(seg.layer).lower()
                # Check if layer exists in our layermap (no canonicalization needed)
                if lname not in self.layer_map:
                    continue
                pts = seg.points or []
                for i in range(len(pts) - 1):
                    (x0, y0) = pts[i]
                    (x1, y1) = pts[i + 1]
                    mx = 0.5 * (x0 + x1)
                    my = 0.5 * (y0 + y1)
                    px = int(round(mx * um_to_dbu + dx))
                    py = int(round(my * um_to_dbu + dy))
                    if net_obj.name not in probe_points:
                        probe_points[net_obj.name] = []
                    probe_points[net_obj.name].append((pya.Point(px, py), lname))
                    lname_set.add(lname)
                    # endpoints for via detection
                    ex0 = int(round(x0 * um_to_dbu + dx)); ey0 = int(round(y0 * um_to_dbu + dy))
                    ex1 = int(round(x1 * um_to_dbu + dx)); ey1 = int(round(y1 * um_to_dbu + dy))
                    ep_layers[(ex0, ey0)].add(lname)
                    ep_layers[(ex1, ey1)].add(lname)

                    # Debug: midpoint-inside test against GDS polygons on same layer
                    if self.debug_probe:
                        if lname not in geom_stats:
                            geom_stats[lname] = {"total": 0, "inside": 0, "outside": 0}
                        geom_stats[lname]["total"] += 1
                        reg = _get_or_build_region(lname)
                        if reg is None:
                            geom_stats[lname]["outside"] += 1
                        else:
                            box = pya.Box(px - 1, py - 1, px + 1, py + 1)
                            inside = not (reg & pya.Region(box)).is_empty()
                            if inside:
                                geom_stats[lname]["inside"] += 1
                            else:
                                geom_stats[lname]["outside"] += 1
            if lname_set:
                self.def_nets.add(net_obj.name)
                for cn in lname_set:
                    probe_layer_names[net_obj.name].add(cn)
            # Add probes at centers of via-like endpoints for this net
            for (ex, ey), layers in ep_layers.items():
                vcanon = None
                # Use YAML via definitions to determine via connections
                if self.tech_data and 'vias' in self.tech_data:
                    for via_name, via_def in self.tech_data['vias'].items():
                        if via_name in self.layer_map:
                            from_layer = via_def.get('from')
                            to_layer = via_def.get('to')
                            # Check if this via connects the layers we found at this endpoint
                            if (from_layer in layers and to_layer in layers) or (to_layer in layers and from_layer in layers):
                                vcanon = via_name
                                break
                if vcanon:
                    if net_obj.name not in probe_points:
                        probe_points[net_obj.name] = []
                    probe_points[net_obj.name].append((pya.Point(ex, ey), vcanon))

        # Include both nets and special nets
        for n in def_data.nets:
            add_segment_midpoints(n)
        for n in def_data.specialnets:
            add_segment_midpoints(n)

        # Match to GDS clusters (try all probe points to catch all disconnected clusters)
        matched_nets = set()  # nets that successfully probed any cluster
        total_cluster_matches = 0
        for net_name, point_list in probe_points.items():
            for pt, layer_name in point_list:
                canonical_layer = layer_name.lower() if layer_name else None
                # Preferred regions: canonical layer variants if available, else all layers
                regions_to_try: List[pya.LayoutToNetlist.Layer] = []
                if canonical_layer:
                    if canonical_layer in self.layer_regions:
                        regions_to_try.extend(self.layer_regions[canonical_layer].values())
                    # include via regions when requested (check if layer is in via_map)
                    if canonical_layer in self.layer_map:
                        vinfo = self.layer_map.get(canonical_layer)
                        if vinfo:
                            for j, li in enumerate(range(self.layout.layers())):
                                info = self.layout.get_info(li)
                                if not info:
                                    continue
                                if info.layer == vinfo.gds_layer and info.datatype == vinfo.datatype:
                                    key = (canonical_layer, li)
                                    cached_region = extra_via_layer_cache.get(key)
                                    if cached_region is None:
                                        # Create unique layer name for additional via layers
                                        base_name = f"{canonical_layer}_extra_{j}"
                                        unique_layer_name = base_name
                                        suffix = 0
                                        while unique_layer_name in used_names:
                                            if suffix == 0:
                                                unique_layer_name = f"{base_name}_{li}"
                                            else:
                                                unique_layer_name = f"{base_name}_{li}_{suffix}"
                                            suffix += 1
                                        used_names.add(unique_layer_name)
                                        cached_region = self.l2n.make_layer(li, unique_layer_name)
                                        extra_via_layer_cache[key] = cached_region
                                    regions_to_try.append(cached_region)
                        # Also try layers connected to this via according to YAML definitions
                        if self.tech_data and 'vias' in self.tech_data and canonical_layer in self.tech_data['vias']:
                            via_def = self.tech_data['vias'][canonical_layer]
                            from_layer = via_def.get('from')
                            to_layer = via_def.get('to')

                            if from_layer in self.layer_regions:
                                regions_to_try.extend(self.layer_regions[from_layer].values())
                            if to_layer in self.layer_regions:
                                regions_to_try.extend(self.layer_regions[to_layer].values())
                if not regions_to_try:
                    for d in self.layer_regions.values():
                        regions_to_try.extend(d.values())

                for lr in regions_to_try:
                    probed = self.l2n.probe_net(lr, pt)
                    if not probed:
                        continue
                    cid = probed.cluster_id
                    matched_nets.add(net_name)
                    if cid not in self.cluster_to_net:
                        sanitized_name = self._sanitize_net_name(net_name)
                        self.cluster_to_net[cid] = sanitized_name
                        total_cluster_matches += 1
                    break  # stop trying more regions for this point

        # Report by-layer presence to help explain low matches
        present_layers = [name for name, regs in self.layer_regions.items() if regs]
        missing_layers = [name for name in self.layer_map if name not in self.layer_regions or not self.layer_regions[name]]
        # No enforcement: with correct window regrouping, nets should naturally map 1:1 to clusters

        if self.debug_probe and geom_stats:
            def layer_sort_key(s: str) -> Tuple[int, int]:
                if s == 'poly':
                    return (0, 0)
                m = re.search(r'(\d+)', s)
                return (1, int(m.group(1)) if m else 0)
            for lname in sorted(geom_stats.keys(), key=layer_sort_key):
                st = geom_stats[lname]
                tot = st.get('total', 0)
                inside = st.get('inside', 0)

        # Mark floating nets (present in DEF probes but unmatched in GDS clusters)
        self.floating_nets = {}
        for net_name, pts in probe_points.items():
            if net_name not in matched_nets:
                self.floating_nets[net_name] = len(pts)
        if self.floating_nets:
            floating_preview = ", ".join(list(self.floating_nets.keys())[:10])

    def assign_generic_names(self):
        """Assign generic names to unmapped GDS clusters."""

        netlist = self.l2n.netlist()
        top_circuit = netlist.circuit_by_name(self.top_cell.name)
        if top_circuit is None and hasattr(netlist, "top_circuit"):
            top_circuit = netlist.top_circuit()
        if top_circuit is None and hasattr(netlist, "each_circuit"):
            for circuit in netlist.each_circuit():
                top_circuit = circuit
                break
        if top_circuit is None:
            available = []
            if hasattr(netlist, "each_circuit"):
                available = [getattr(c, "name", "<unnamed>") for c in netlist.each_circuit()]
            raise RuntimeError(
                f"Could not find top circuit '{self.top_cell.name}' (available: {available})"
            )

        unnamed_clusters = []
        for net in top_circuit.each_net():
            if net.cluster_id not in self.cluster_to_net:
                unnamed_clusters.append(net.cluster_id)

        # Assign generic names
        for cluster_id in unnamed_clusters:
            self.unnamed_count += 1
            generated = f"Net.{self.unnamed_count}"
            self.cluster_to_net[cluster_id] = self._sanitize_net_name(generated)

    def propagate_net_names_through_connectivity(self):
        """
        Not needed - we'll fix this at the L2N level by creating unified clusters
        that contain both via and metal geometries.
        """
        pass

    def extract_shapes_per_net(self) -> Dict[str, List[Tuple[str, pya.Box]]]:
        """Extract all shapes grouped by net name using KLayout Region API."""

        net_shapes: Dict[str, List[Tuple[str, pya.Box]]] = {}

        # Combine metal layers and vias for extraction
        all_layers = self.layer_map
        dbu = self.layout.dbu
        if dbu <= 0:
            raise RuntimeError("Invalid DBU encountered while extracting shapes")
        # Iterate through each layer (metals and vias)
        for layer_name, layer_entry in all_layers.items():
            # Collect all layout layer indices for this GDS layer number (any datatype)
            layer_indices = []
            for li in range(self.layout.layers()):
                info = self.layout.get_info(li)
                if info and info.layer == layer_entry.gds_layer and info.datatype == layer_entry.datatype:
                    layer_indices.append(li)
            if not layer_indices:
                continue

            # Determine which L2N region to use for probing
            if layer_name in self.layer_map and layer_name in self.tech_data.get('vias', {}):
                # For vias, use YAML definitions to find connected layers
                lower, upper = None, None
                if self.tech_data and 'vias' in self.tech_data and layer_name in self.tech_data['vias']:
                    via_def = self.tech_data['vias'][layer_name]
                    lower = via_def.get('from')
                    upper = via_def.get('to')
                # Try upper first, then lower
                probe_region = None
                for metal in [upper, lower]:
                    if metal and metal in self.layer_regions:
                        probe_region = next(iter(self.layer_regions[metal].values()))
                        break
                if not probe_region:
                    continue
            else:
                # For metals, probe on the same layer
                if layer_name not in self.layer_regions:
                    continue
                probe_region = next(iter(self.layer_regions[layer_name].values()))

            # Process each layer index (datatype variant)
            for layer_idx in layer_indices:
                # Collect all shapes on this layer into a Region
                layer_region = pya.Region()
                for shape in self.top_cell.shapes(layer_idx).each():
                    if shape.is_box():
                        layer_region.insert(shape.box)
                    elif shape.is_polygon():
                        layer_region.insert(shape.polygon)
                    elif shape.is_path():
                        # Convert path to polygon first
                        layer_region.insert(shape.path.polygon())

                if layer_region.is_empty():
                    continue

                # Merge overlapping shapes to eliminate redundancy
                layer_region.merge()

                # Decompose complex polygons into simple trapezoids/rectangles using KLayout's built-in methods
                # This properly separates shapes without overlaps
                decomposed = layer_region.decompose_trapezoids_to_region(pya.Polygon.TD_simple)

                # Probe each resulting trapezoid/rectangle to find its net
                for poly in decomposed.each():
                    # Use the shape's actual center for probing
                    # This maintains geometric accuracy better than bbox centers
                    bbox = poly.bbox()
                    cx = (bbox.left + bbox.right) / 2.0
                    cy = (bbox.bottom + bbox.top) / 2.0
                    probe_pt = pya.Point(int(round(cx)), int(round(cy)))

                    # Use layer-specific region if available for metal layers
                    reg = probe_region
                    if layer_name in self.layer_regions and layer_idx in self.layer_regions[layer_name]:
                        reg = self.layer_regions[layer_name][layer_idx]

                    probed = self.l2n.probe_net(reg, probe_pt)
                    if probed and probed.cluster_id in self.cluster_to_net:
                        net_name = self.cluster_to_net[probed.cluster_id]
                        if net_name not in net_shapes:
                            net_shapes[net_name] = []
                        # Store the bounding box of the properly decomposed shape
                        net_shapes[net_name].append((layer_name, bbox))

        return net_shapes

    def debug_cluster_composition(self):
        """Debug method to understand cluster composition and net assignment."""
        print("\n" + "="*60)
        print("DEBUG: CLUSTER COMPOSITION ANALYSIS")
        print("="*60)

        netlist = self.l2n.netlist()
        top_circuit = netlist.circuit_by_name(self.top_cell.name)
        if top_circuit is None and hasattr(netlist, "top_circuit"):
            top_circuit = netlist.top_circuit()
        if top_circuit is None and hasattr(netlist, "each_circuit"):
            for circuit in netlist.each_circuit():
                top_circuit = circuit
                break

        if top_circuit is None:
            print("No top circuit found")
            return

        # Analyze clusters and their assigned net names
        cluster_info = {}
        for net in top_circuit.each_net():
            cluster_id = net.cluster_id
            cluster_info[cluster_id] = {
                'net_obj': net,
                'assigned_name': self.cluster_to_net.get(cluster_id, 'UNNAMED'),
                'pin_count': len(list(net.each_pin()))
            }

        print(f"Found {len(cluster_info)} total clusters")
        print(f"DEF-assigned clusters: {len([c for c in cluster_info.values() if c['assigned_name'] != 'UNNAMED'])}")
        print(f"Unnamed clusters: {len([c for c in cluster_info.values() if c['assigned_name'] == 'UNNAMED'])}")

        # Show details for first few clusters
        print("\nFirst 10 clusters:")
        for i, (cluster_id, info) in enumerate(list(cluster_info.items())[:10]):
            print(f"  Cluster {cluster_id}: {info['assigned_name']} (pins: {info['pin_count']})")

        # Show specific problematic cases we know about
        print("\nLooking for via-only clusters that should be part of metal clusters...")
        via_clusters = []
        metal_clusters = []

        for cluster_id, info in cluster_info.items():
            assigned_name = info['assigned_name']
            if assigned_name.startswith('Net.') and assigned_name[4:].isdigit():
                via_clusters.append((cluster_id, info))
            elif assigned_name.startswith('_') and assigned_name.endswith('_'):
                metal_clusters.append((cluster_id, info))

        print(f"Found {len(via_clusters)} likely via clusters (Net.X naming)")
        print(f"Found {len(metal_clusters)} likely metal clusters (_XXXXXX_ naming)")

        # Show some examples
        if via_clusters:
            print("\nExample via clusters:")
            for cluster_id, info in via_clusters[:5]:
                print(f"  Cluster {cluster_id}: {info['assigned_name']} (pins: {info['pin_count']})")

        if metal_clusters:
            print("\nExample metal clusters:")
            for cluster_id, info in metal_clusters[:5]:
                print(f"  Cluster {cluster_id}: {info['assigned_name']} (pins: {info['pin_count']})")

        print("="*60)

    def _build_cap3d_layer_ids(self) -> Dict[str, int]:
        """Assign distinct CAP3D layer IDs per physical layer (conductors and vias).

        Ground plane uses 0. Conductor and via layers start from 1, ordered by z-height.
        """
        entries: List[Tuple[str, float, float]] = []

        # Add metal layers (interconnect layers)
        for name, entry in self.layer_map.items():
            entries.append((name, entry.z_bottom, entry.z_top))

        # Add via layers - this was missing in the original code!
        for name, entry in self.layer_map.items():
            if name in self.tech_data.get('vias', {}):
                entries.append((name, entry.z_bottom, entry.z_top))

        # Sort by z center (bottom first), tie-break by name for stability
        entries.sort(key=lambda t: (0.5 * (t[1] + t[2]), t[0]))

        layer_ids: Dict[str, int] = {}
        next_id = 1
        for name, _, _ in entries:
            layer_ids[name] = next_id
            next_id += 1

        return layer_ids

    def write_cap3d(self, net_shapes: Dict[str, List[Tuple[str, pya.Box]]]):
        """Write cap3d format file using utils.writer.write_cap3d."""
        dbu = self.layout.dbu
        bbox = self.top_cell.bbox()
        x_min = bbox.left * dbu
        y_min = bbox.bottom * dbu
        x_max = bbox.right * dbu
        y_max = bbox.top * dbu

        cap3d_layer_ids = self._build_cap3d_layer_ids()
        writer_layer_map = {
            name: (entry.gds_layer, entry.z_bottom, entry.z_top)
            for name, entry in self.layer_map.items()
        }
        writer_via_map = {
            name: (entry.gds_layer, entry.z_bottom, entry.z_top)
            for name, entry in self.layer_map.items()
            if name in self.tech_data.get('vias', {})
        }
        write_cap3d(
            str(self.output_file),
            x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max,
            dbu=dbu,
            margin_factor=1.1,  # 10% margin on all sides
            dielectric_stack=self.dielectric_stack,
            layer_map=writer_layer_map,
            via_map=writer_via_map,
            cap3d_layer_ids=cap3d_layer_ids,
            net_shapes=net_shapes,
        )

    def run(self):
        """Run the complete conversion process."""
        # Load configuration files
        self._load_layermap()           # Populates layer_map and via_map with GDS layer numbers
        self._load_yaml_stack()         # Populates dielectric_stack and assigns z-heights to layers and vias

        # Process layouts
        self.load_layouts()
        self.run_l2n_extraction()
        self.match_def_nets_to_clusters()
        self.assign_generic_names()
        self.propagate_net_names_through_connectivity()
        net_shapes = self.extract_shapes_per_net()
        self.write_cap3d(net_shapes)


def main():
    parser = argparse.ArgumentParser(description='Convert DEF+GDS to cap3d format.')
    parser.add_argument('--gds', type=str, default='../designs/gds/gcd.gds',
                        help='GDS file (default: %(default)s)')
    parser.add_argument('--def', '--def-file', type=str, dest='def_file',
                        default='../designs/def/gcd.def',
                        help='DEF file (default: %(default)s)')
    parser.add_argument('--stack', type=str, default='../designs/tech/nangate45/nangate45_stack.yaml',
                        help='YAML file with complete layer stack (default: %(default)s)')
    parser.add_argument('--layermap', type=str, default='../designs/tech/nangate45/nangate45.layermap',
                        help='KLayout layer map file (default: %(default)s)')
    parser.add_argument('-o', '--output', type=str, default='../designs/cap3d/gcd.cap3d',
                        help='Output cap3d file (default: %(default)s)')
    parser.add_argument('--debug-probe', action='store_true',
                        help='Enable debug summary: test DEF segment midpoints inside GDS polygons')
    parser.add_argument('-l', '--lef', action='append',
                        help='Technology LEF file(s). Can be specified multiple times.')

    args = parser.parse_args()

    # Allow overrides provided via KLayout -rd key=value flags
    try:
        app = pya.Application.instance()
    except Exception:
        app = None

    if app is not None:
        rd_overrides = {}
        arg_list = list(app.arguments())
        for idx, token in enumerate(arg_list):
            if token != '-rd':
                continue
            if idx + 1 >= len(arg_list):
                continue
            key_val = arg_list[idx + 1]
            if '=' not in key_val:
                continue
            key, value = key_val.split('=', 1)
            rd_overrides[key.strip()] = value.strip()

        override_map = {
            'gds': 'gds',
            'def': 'def_file',
            'stack': 'stack',
            'layermap': 'layermap',
            'output': 'output',
        }
        for cfg_key, attr in override_map.items():
            value = rd_overrides.get(cfg_key)
            if not value:
                continue
            setattr(args, attr, value)

    # Check files exist
    required_files = [Path(args.gds), Path(args.def_file), Path(args.stack), Path(args.layermap)]
    missing = [str(p) for p in required_files if not Path(p).expanduser().exists()]
    if missing:
        print("ERROR: Missing files:")
        for f in missing:
            print(f"  - {f}")
        sys.exit(1)

    process_node = Path(args.stack).stem.lower() if args.stack else None

    converter = DEF2Cap3D(
        gds_file=args.gds,
        def_file=args.def_file,
        output_file=args.output,
        stack_file=args.stack,
        layermap_file=args.layermap,
        debug_probe=args.debug_probe,
        process_node=process_node,
        lef_files=args.lef,
    )

    try:
        converter.run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

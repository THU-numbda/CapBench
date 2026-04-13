"""
DEF Parser and Window Filtering Utilities

Parse DEF files, detect cell placement grids, snap windows to grid boundaries,
and filter components/nets to generate windowed DEF files.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Set, Optional, Sequence
from pathlib import Path
import re
from collections import defaultdict
import math

_POWER_NET_NAMES = {"VDD", "VDDPE", "VPWR", "POWER"}
_GROUND_NET_NAMES = {"VSS", "VSSPE", "VGND", "GND", "GROUND"}


@dataclass
class GridInfo:
    """Cell placement grid information."""
    x_pitch: float  # microns
    y_pitch: float  # microns
    x_offset: float  # microns (origin)
    y_offset: float  # microns (origin)


@dataclass
class Row:
    """DEF ROW entry."""
    name: str
    site: str
    x: float  # microns
    y: float  # microns
    orient: str
    num_x: int
    num_y: int
    step_x: float
    step_y: float


@dataclass
class Component:
    """DEF COMPONENT entry."""
    name: str
    cell_type: str
    x: float  # microns (placement position)
    y: float  # microns
    orient: str
    status: str  # PLACED, FIXED, etc.

    @property
    def center_x(self) -> float:
        # For center-based inclusion, we approximate center as placement position
        # (Actual cell width would require LEF parsing)
        return self.x

    @property
    def center_y(self) -> float:
        return self.y


def _strip_semicolon(value: str) -> str:
    value = value.strip()
    if value.endswith(";"):
        return value[:-1].strip()
    return value


def parse_lef_macro_sizes(lef_files: Sequence[Path | str]) -> Dict[str, Tuple[float, float]]:
    """Parse macro SIZE data from one or more LEF files."""
    macro_sizes: Dict[str, Tuple[float, float]] = {}
    for lef_file in lef_files:
        path = Path(lef_file)
        if not path.exists():
            continue
        current_macro: Optional[str] = None
        in_macro = False
        with path.open() as handle:
            for raw_line in handle:
                line = raw_line.split("#", 1)[0].strip()
                if not line:
                    continue
                if not in_macro:
                    if line.startswith("MACRO "):
                        current_macro = _strip_semicolon(line[6:])
                        in_macro = True
                    continue
                if line.startswith("SIZE ") and current_macro:
                    match = re.search(r"SIZE\s+([+-]?[0-9]*\.?[0-9]+)\s+BY\s+([+-]?[0-9]*\.?[0-9]+)", line)
                    if match:
                        macro_sizes[current_macro] = (float(match.group(1)), float(match.group(2)))
                    continue
                if line.startswith("END "):
                    end_name = _strip_semicolon(line[4:])
                    if current_macro and end_name == current_macro:
                        in_macro = False
                        current_macro = None
    return macro_sizes


def _apply_component_orientation(point: Tuple[float, float], orient: str) -> Tuple[float, float]:
    x, y = float(point[0]), float(point[1])
    orient = str(orient).upper()
    alias_map = {
        "R0": "N",
        "R90": "E",
        "R180": "S",
        "R270": "W",
        "MX": "FS",
        "MY": "FN",
        "MYR90": "FE",
        "MXR90": "FW",
    }
    orient = alias_map.get(orient, orient)
    if orient.startswith("F"):
        x = -x
        orient = orient[1:]
    if orient == "N":
        return x, y
    if orient == "S":
        return -x, -y
    if orient == "E":
        return y, -x
    if orient == "W":
        return -y, x
    raise ValueError(f"Unsupported DEF orientation: {orient}")


def _component_bbox(
    component: Component,
    macro_sizes: Dict[str, Tuple[float, float]],
) -> Optional[Tuple[float, float, float, float]]:
    size = macro_sizes.get(component.cell_type)
    if size is None:
        return None
    size_x, size_y = size
    corners = [
        _apply_component_orientation((0.0, 0.0), component.orient),
        _apply_component_orientation((size_x, 0.0), component.orient),
        _apply_component_orientation((0.0, size_y), component.orient),
        _apply_component_orientation((size_x, size_y), component.orient),
    ]
    bbox_min_x = min(x for x, _ in corners)
    bbox_min_y = min(y for _, y in corners)
    xs = [component.x + x - bbox_min_x for x, _ in corners]
    ys = [component.y + y - bbox_min_y for _, y in corners]
    return min(xs), min(ys), max(xs), max(ys)


def _bboxes_overlap(
    ax0: float,
    ay0: float,
    ax1: float,
    ay1: float,
    bx0: float,
    by0: float,
    bx1: float,
    by1: float,
) -> bool:
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


@dataclass
class NetConnection:
    """Net connection point."""
    component: str  # Component name or "PIN"
    pin: str


@dataclass
class RoutingSegment:
    """DEF routing segment."""
    layer: str
    points: List[Tuple[float, float]]  # List of (x, y) coordinates (in microns)
    via: Optional[str] = None
    width: Optional[float] = None  # microns


@dataclass
class Net:
    """DEF NET or SPECIALNET entry."""
    name: str
    connections: List[NetConnection]
    routing: List[RoutingSegment]
    use: str = "SIGNAL"  # SIGNAL, POWER, GROUND, CLOCK, etc.
    is_special: bool = False

    @property
    def is_power(self) -> bool:
        return self.use in ["POWER", "GROUND"] or self.name in ["VDD", "VSS", "VDDPE", "VSSPE"]


@dataclass
class Via:
    """DEF VIA definition.

    Supports both explicit geometry (+ RECT ...) and rule-based forms
    (+ VIARULE ... + LAYERS ... + CUTSIZE ... etc.). When `raw_def` is
    populated, it will be re-emitted verbatim after the via name.
    """
    name: str
    layers: List[Tuple[str, List[Tuple[float, float, float, float]]]]  # (layer, rects)
    raw_def: Optional[str] = None


@dataclass
class DefData:
    """Complete DEF file data."""
    design_name: str
    units: int  # DISTANCE MICRONS value
    diearea: Tuple[float, float, float, float]  # (x1, y1, x2, y2) in microns
    rows: List[Row]
    components: List[Component]
    nets: List[Net]
    specialnets: List[Net]
    vias: List[Via]
    pins: List[dict]  # Top-level pins
    version: str = "5.7"
    tech: str = ""


def parse_def(def_file: Path) -> DefData:
    """Parse DEF file into structured data.

    Args:
        def_file: Path to DEF file

    Returns:
        DefData object with parsed structure
    """
    # Parsing DEF file silently

    with open(def_file) as f:
        lines = f.readlines()

    data = DefData(
        design_name="", units=2000, diearea=(0, 0, 0, 0),
        rows=[], components=[], nets=[], specialnets=[], vias=[], pins=[],
        version="5.7", tech=""
    )

    # Parse line by line
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Header fields
        if line.startswith("DESIGN "):
            data.design_name = line.split()[1].rstrip(";")
        elif line.startswith("TECHNOLOGY "):
            data.tech = line.split()[1].rstrip(";")
        elif line.startswith("UNITS DISTANCE MICRONS"):
            data.units = int(line.split()[3])
        elif line.startswith("DIEAREA"):
            # Parse: DIEAREA ( x1 y1 ) ( x2 y2 ) ;
            tokens = line.split()
            x1 = float(tokens[2]) / data.units
            y1 = float(tokens[3]) / data.units
            x2 = float(tokens[6]) / data.units
            y2 = float(tokens[7]) / data.units
            data.diearea = (x1, y1, x2, y2)

        # ROW definitions
        elif line.startswith("ROW "):
            row = _parse_row(line, data.units)
            if row:
                data.rows.append(row)

        # VIAS section
        elif line.startswith("VIAS "):
            count = int(line.split()[1])
            i += 1
            vias_parsed = 0
            while vias_parsed < count and i < len(lines):
                line = lines[i].strip()
                if line.startswith("- "):
                    via = _parse_via(lines, i, data.units)
                    if via:
                        data.vias.append(via)
                        vias_parsed += 1
                elif line == "END VIAS":
                    break
                i += 1
            continue

        # COMPONENTS section
        elif line.startswith("COMPONENTS "):
            count = int(line.split()[1])
            i += 1
            comps_parsed = 0
            while comps_parsed < count and i < len(lines):
                line = lines[i].strip()
                if line.startswith("- "):
                    comp = _parse_component(line, data.units)
                    if comp:
                        data.components.append(comp)
                        comps_parsed += 1
                elif line == "END COMPONENTS":
                    break
                i += 1
            continue

        # NETS section
        elif line.startswith("NETS "):
            count = int(line.split()[1])
            i += 1
            nets_parsed = 0
            while nets_parsed < count and i < len(lines):
                if lines[i].strip().startswith("- "):
                    net = _parse_net(lines, i, data.units, is_special=False)
                    if net:
                        data.nets.append(net)
                        nets_parsed += 1
                        i = net.end_line
                elif lines[i].strip() == "END NETS":
                    break
                i += 1
            continue

        # SPECIALNETS section
        elif line.startswith("SPECIALNETS "):
            count = int(line.split()[1])
            i += 1
            nets_parsed = 0
            while nets_parsed < count and i < len(lines):
                if lines[i].strip().startswith("- "):
                    net = _parse_net(lines, i, data.units, is_special=True)
                    if net:
                        data.specialnets.append(net)
                        nets_parsed += 1
                        i = net.end_line
                elif lines[i].strip() == "END SPECIALNETS":
                    break
                i += 1
            continue

        i += 1

    # DEF parsing completed silently

    return data


def _parse_row(line: str, units: int) -> Optional[Row]:
    """Parse ROW line."""
    # ROW ROW_0 FreePDK45_38x28_10R_NP_162NW_34O 2280 2800 N DO 180 BY 1 STEP 380 0 ;
    tokens = line.split()
    if len(tokens) < 11:
        return None

    return Row(
        name=tokens[1],
        site=tokens[2],
        x=float(tokens[3]) / units,
        y=float(tokens[4]) / units,
        orient=tokens[5],
        num_x=int(tokens[7]),
        num_y=int(tokens[9]),
        step_x=float(tokens[11]) / units,
        step_y=float(tokens[12]) / units if len(tokens) > 12 else 0.0
    )


def _parse_component(line: str, units: int) -> Optional[Component]:
    """Parse COMPONENT line."""
    # - FILLER_0_1 FILLCELL_X16 + SOURCE DIST + PLACED ( 2660 2800 ) N ;
    tokens = line.split()
    if len(tokens) < 8:
        return None

    name = tokens[1]
    cell_type = tokens[2]

    # Find PLACED/FIXED
    status = "PLACED"
    x, y = 0.0, 0.0
    orient = "N"

    for i, tok in enumerate(tokens):
        if tok in ["PLACED", "FIXED"]:
            status = tok
            if i + 4 < len(tokens):
                x = float(tokens[i + 2]) / units
                y = float(tokens[i + 3]) / units
                orient = tokens[i + 5]
            break

    return Component(name=name, cell_type=cell_type, x=x, y=y, orient=orient, status=status)


def _parse_via(lines: List[str], start_idx: int, units: int) -> Optional[Via]:
    """Parse VIA definition supporting both +RECT and +VIARULE styles.

    Examples:
      - via1 ... + VIARULE ... + LAYERS metal1 via1 metal2 ... ;
      - via_custom
          + RECT metal1 ( x1 y1 ) ( x2 y2 )
          + RECT via1   ( x1 y1 ) ( x2 y2 )
          + RECT metal2 ( x1 y1 ) ( x2 y2 )
          ;
    """
    first = lines[start_idx].strip()
    toks = first.split()
    if len(toks) < 2 or toks[0] != '-':
        return None
    via_name = toks[1]

    # Collect body until terminating ';'
    body_parts: List[str] = []
    layers: List[Tuple[str, List[Tuple[float, float, float, float]]]] = []

    # If the first line contains more after the name, capture and parse it too.
    rest = first[first.find(via_name) + len(via_name):].strip()
    if rest:
        body_parts.append(rest)
        if rest.endswith(';'):
            raw_def = ' '.join(p.strip() for p in body_parts if p).strip()
            if raw_def and not raw_def.endswith(';'):
                raw_def += ' ;'
            return Via(name=via_name, layers=layers, raw_def=raw_def or None)

    i = start_idx + 1
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        # Accumulate raw text for verbatim re-emission
        body_parts.append(s)

        if s.startswith('+ RECT'):
            tokens = s.replace('(', ' ').replace(')', ' ').split()
            if len(tokens) >= 7:
                layer = tokens[2]
                try:
                    x1 = float(tokens[3]) / units
                    y1 = float(tokens[4]) / units
                    x2 = float(tokens[5]) / units
                    y2 = float(tokens[6]) / units
                    if layers and layers[-1][0] == layer:
                        layers[-1][1].append((x1, y1, x2, y2))
                    else:
                        layers.append((layer, [(x1, y1, x2, y2)]))
                except Exception:
                    pass
        # End of VIA definition
        if s.endswith(';'):
            break
        i += 1

    raw_def = ' '.join(p.strip() for p in body_parts if p).strip()
    if raw_def and not raw_def.endswith(';'):
        raw_def += ' ;'

    return Via(name=via_name, layers=layers, raw_def=raw_def or None)


class NetParser:
    """Helper to track parsing state for multi-line net definitions."""
    def __init__(self):
        self.end_line = 0


def _parse_net(lines: List[str], start_idx: int, units: int, is_special: bool) -> Optional[Net]:
    """Parse NET or SPECIALNET (multi-line)."""
    # - net_name ( comp pin ) ( comp pin ) ...
    #   + USE SIGNAL
    #   + ROUTED layer ( x1 y1 ) ( x2 y2 ) ...
    #   ;
    line = lines[start_idx].strip()
    tokens = line.split()
    net_name = tokens[1]

    connections = []
    routing = []
    if is_special and net_name.upper() in _GROUND_NET_NAMES:
        use = "GROUND"
    elif is_special and net_name.upper() in _POWER_NET_NAMES:
        use = "POWER"
    else:
        use = "POWER" if is_special else "SIGNAL"

    # Parse connections on first line
    i = 2
    while i < len(tokens):
        if tokens[i] == "(":
            if i + 2 < len(tokens):
                comp = tokens[i + 1]
                pin = tokens[i + 2].rstrip(")")
                connections.append(NetConnection(comp, pin))
            i += 3
        else:
            i += 1

    # Parse continuation lines
    idx = start_idx + 1
    route_prefixes = ("+ ROUTED", "NEW ")
    route_keywords = {
        "ROUTED", "NEW", "+", "WIDTH", "MASK", "SPACING", "TAPER", "TAPERRULE", "OFFSET",
    }

    while idx < len(lines):
        line = lines[idx].strip()

        if line.startswith("+ USE"):
            use = line.split()[2]
        elif any(line.startswith(prefix) for prefix in route_prefixes):
            # Parse a routed/new segment: layer and coordinate pairs
            tokens = line.replace('(', ' ( ').replace(')', ' ) ').split()
            # Determine layer: first non-keyword token before first '('
            layer = None
            width_val: Optional[float] = None
            # Find index of first coord paren
            try:
                first_paren = tokens.index('(')
            except ValueError:
                first_paren = len(tokens)
            # Extract layer and immediate numeric width (common form: LAYER WIDTH)
            i2 = 0
            while i2 < first_paren:
                t = tokens[i2]
                tu = t.upper()
                if tu in route_keywords:
                    i2 += 1
                    continue
                if layer is None:
                    layer = t
                    # Check next token for numeric width before first '('
                    if i2 + 1 < first_paren:
                        nxt = tokens[i2 + 1]
                        try:
                            width_val = float(nxt) / units
                            i2 += 2
                            continue
                        except Exception:
                            pass
                    i2 += 1
                    continue
                else:
                    # Sometimes a numeric width appears as standalone after layer
                    try:
                        width_val = float(t) / units
                    except Exception:
                        pass
                    i2 += 1
                    continue
            # Fallback: look for explicit WIDTH token anywhere
            for j, tok in enumerate(tokens):
                if tok.upper() == 'WIDTH' and j + 1 < len(tokens):
                    try:
                        width_val = float(tokens[j + 1]) / units
                        break
                    except Exception:
                        pass
            # Extract coordinate pairs with '*' support (repeat previous component)
            pts: List[Tuple[float, float]] = []
            prev_x: Optional[float] = None
            prev_y: Optional[float] = None
            i2 = 0
            while i2 < len(tokens):
                if tokens[i2] == '(' and i2 + 3 < len(tokens) and tokens[i2+3] == ')':
                    xtok = tokens[i2+1]
                    ytok = tokens[i2+2]
                    xval: Optional[float] = None
                    yval: Optional[float] = None
                    if xtok == '*':
                        xval = prev_x
                    else:
                        try:
                            xval = float(xtok) / units
                        except Exception:
                            xval = None
                    if ytok == '*':
                        yval = prev_y
                    else:
                        try:
                            yval = float(ytok) / units
                        except Exception:
                            yval = None
                    if xval is not None and yval is not None:
                        pts.append((xval, yval))
                        prev_x, prev_y = xval, yval
                    i2 += 4
                    continue
                i2 += 1
            if layer and len(pts) >= 2:
                routing.append(RoutingSegment(layer=layer, points=pts, width=width_val))
            # If this line terminates the net, break
            if line.endswith(';'):
                break
        elif line.endswith(";"):
            break

        idx += 1

    net = Net(name=net_name, connections=connections, routing=routing, use=use, is_special=is_special)
    net_parser = NetParser()
    net_parser.end_line = idx
    net.end_line = idx  # Attach end line for parser

    return net


def detect_cell_grid(def_data: DefData) -> GridInfo:
    """Detect cell placement grid from DEF data.

    Args:
        def_data: Parsed DEF data

    Returns:
        GridInfo with detected grid pitch and offset
    """
    print("Detecting cell placement grid...")

    # Y-grid from ROW definitions
    if def_data.rows:
        row_y_positions = [row.y for row in def_data.rows]
        y_pitch = def_data.rows[0].step_y if def_data.rows[0].step_y > 0 else (
            min(abs(row_y_positions[i+1] - row_y_positions[i])
                for i in range(len(row_y_positions)-1)) if len(row_y_positions) > 1 else 2.8
        )
        y_offset = min(row_y_positions)
    else:
        y_pitch = 2.8  # Default for NanGate45
        y_offset = 0.0

    # X-grid from component placements
    if def_data.components:
        x_positions = [comp.x for comp in def_data.components]
        x_offset = min(x_positions)

        # Find common pitch by analyzing differences
        diffs = []
        sorted_x = sorted(set(x_positions))
        for i in range(len(sorted_x) - 1):
            diff = sorted_x[i+1] - sorted_x[i]
            if diff > 0.01:  # Ignore tiny differences
                diffs.append(diff)

        if diffs:
            # Find GCD-like common pitch
            from math import gcd as math_gcd
            from functools import reduce

            # Convert to integer (in nanometers) for GCD
            diffs_nm = [int(round(d * 1000)) for d in diffs[:20]]  # Sample first 20
            common_nm = reduce(math_gcd, diffs_nm) if diffs_nm else 380
            x_pitch = common_nm / 1000.0
        else:
            x_pitch = 0.38  # Default for NanGate45
    else:
        x_pitch = 0.38
        x_offset = 0.0

    grid = GridInfo(x_pitch=x_pitch, y_pitch=y_pitch, x_offset=x_offset, y_offset=y_offset)
    print(f"  Grid detected: X pitch={grid.x_pitch:.4f}μm, Y pitch={grid.y_pitch:.4f}μm")
    print(f"  Grid offset: X={grid.x_offset:.4f}μm, Y={grid.y_offset:.4f}μm")

    return grid


def snap_window_to_grid(window: dict, grid: GridInfo, min_cells_x: int = 3, min_cells_y: int = 3) -> dict:
    """Snap window coordinates to cell grid boundaries, shrinking inward.

    Args:
        window: Dictionary with 'name', 'x1', 'y1', 'x2', 'y2' (microns)
        grid: Grid information
        min_cells_x: Minimum number of cells in X direction
        min_cells_y: Minimum number of cells in Y direction

    Returns:
        Adjusted window dictionary with snapped coordinates
    """
    eps = 1e-9

    def _ceil_index(value: float, pitch: float, offset: float) -> int:
        ratio = (value - offset) / pitch
        return math.ceil(ratio - eps)

    def _floor_index(value: float, pitch: float, offset: float) -> int:
        ratio = (value - offset) / pitch
        return math.floor(ratio + eps)

    # Preserve X bounds exactly (requested behavior); only shrink along Y rows.
    x1 = window['x1']
    x2 = window['x2']
    if x2 <= x1:
        return {
            'name': window['name'],
            'x1': window['x1'], 'y1': window['y1'],
            'x2': window['x2'], 'y2': window['y2'],
            'width': window['x2'] - window['x1'],
            'height': window['y2'] - window['y1']
        }

    y1_idx = _ceil_index(window['y1'], grid.y_pitch, grid.y_offset)
    y2_idx = _floor_index(window['y2'], grid.y_pitch, grid.y_offset)

    # Ensure indices define a valid region; if not, fall back to original window
    if y2_idx <= y1_idx:
        return {
            'name': window['name'],
            'x1': window['x1'], 'y1': window['y1'],
            'x2': window['x2'], 'y2': window['y2'],
            'width': window['x2'] - window['x1'],
            'height': window['y2'] - window['y1']
        }

    y1 = grid.y_offset + y1_idx * grid.y_pitch
    y2 = grid.y_offset + y2_idx * grid.y_pitch

    # Clamp to original bounds to guarantee we only shrink along Y
    y1 = max(y1, window['y1'])
    y2 = min(y2, window['y2'])

    # After clamping, ensure region is still valid; otherwise fall back to original
    if y2 <= y1:
        return {
            'name': window['name'],
            'x1': window['x1'], 'y1': window['y1'],
            'x2': window['x2'], 'y2': window['y2'],
            'width': window['x2'] - window['x1'],
            'height': window['y2'] - window['y1']
        }

    return {
        'name': window['name'],
        'x1': x1, 'y1': y1,
        'x2': x2, 'y2': y2,
        'width': x2 - x1,
        'height': y2 - y1
    }


def filter_components_in_window(
    components: List[Component],
    window: dict,
    macro_sizes: Optional[Dict[str, Tuple[float, float]]] = None,
) -> List[Component]:
    """Filter components that overlap the window.

    Args:
        components: List of components
        window: Window with 'x1', 'y1', 'x2', 'y2'
        macro_sizes: Optional LEF-derived macro sizes in microns

    Returns:
        List of components overlapping the window
    """
    included = []
    wx0 = float(window['x1'])
    wy0 = float(window['y1'])
    wx1 = float(window['x2'])
    wy1 = float(window['y2'])
    for comp in components:
        bbox = _component_bbox(comp, macro_sizes or {})
        if bbox is None:
            if wx0 <= comp.center_x <= wx1 and wy0 <= comp.center_y <= wy1:
                included.append(comp)
            continue
        if _bboxes_overlap(bbox[0], bbox[1], bbox[2], bbox[3], wx0, wy0, wx1, wy1):
            included.append(comp)

    return included


def _liang_barsky_clip(x0: float, y0: float, x1: float, y1: float,
                       rx0: float, ry0: float, rx1: float, ry1: float) -> Optional[Tuple[float, float, float, float]]:
    """Clip a line to an axis-aligned rectangle using the Liang–Barsky algorithm.

    Returns (cx0, cy0, cx1, cy1) if intersection exists; otherwise None.
    """
    dx = x1 - x0
    dy = y1 - y0
    p = [-dx, dx, -dy, dy]
    q = [x0 - rx0, rx1 - x0, y0 - ry0, ry1 - y0]
    u1, u2 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            # Parallel to boundary; reject if outside
            if qi < 0:
                return None
            continue
        t = qi / pi
        if pi < 0:
            # entering
            if t > u1:
                u1 = t
        else:
            # leaving
            if t < u2:
                u2 = t
        if u1 > u2:
            return None
    cx0 = x0 + u1 * dx
    cy0 = y0 + u1 * dy
    cx1 = x0 + u2 * dx
    cy1 = y0 + u2 * dy
    return (cx0, cy0, cx1, cy1)


def _clip_polyline_to_window(points: List[Tuple[float, float]], rx0: float, ry0: float, rx1: float, ry1: float,
                             eps: float = 1e-9) -> List[List[Tuple[float, float]]]:
    """Clip a polyline to a rectangular window; return inside pieces as polylines."""
    pieces: List[List[Tuple[float, float]]] = []
    cur: List[Tuple[float, float]] = []
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i+1]
        clip = _liang_barsky_clip(x0, y0, x1, y1, rx0, ry0, rx1, ry1)
        if not clip:
            # If we were accumulating a piece, close it
            if cur:
                if len(cur) >= 2:
                    pieces.append(cur)
                cur = []
            continue
        cx0, cy0, cx1, cy1 = clip
        s = (cx0, cy0)
        e = (cx1, cy1)
        if not cur:
            cur = [s, e]
        else:
            # If the new start matches the current end, extend; else start new piece
            px, py = cur[-1]
            if abs(px - s[0]) <= eps and abs(py - s[1]) <= eps:
                if abs(e[0] - px) > eps or abs(e[1] - py) > eps:
                    cur.append(e)
            else:
                if len(cur) >= 2:
                    pieces.append(cur)
                cur = [s, e]
    if cur and len(cur) >= 2:
        pieces.append(cur)
    return pieces


# Endpoint stitching of polylines was intentionally removed per user preference.


def filter_nets_in_window(nets: List[Net], included_component_names: Set[str], window: dict) -> List[Net]:
    """Filter and clip nets to the window, splitting into sub-nets by disconnected pieces.

    - Keeps only nets that either connect to included components or have routed geometry in window.
    - Clips ROUTED polylines to the window bounds.
    - Splits a net into multiple sub-nets using suffixes ".1", ".2", ... when disconnected.
    """
    x0, y0, x1, y1 = window['x1'], window['y1'], window['x2'], window['y2']
    windowed_nets: List[Net] = []

    for net in nets:
        # Connections kept only for components inside the window and PINs
        connected_comps = [conn for conn in net.connections
                           if conn.component in included_component_names or conn.component == "PIN"]

        # Clip ROUTED segments to window
        # Collect clipped polylines per layer (no endpoint stitching by design)
        pieces_per_layer: List[Tuple[str, Optional[float], List[Tuple[float, float]]]] = []
        for seg in net.routing:
            if not seg.points or len(seg.points) < 2:
                continue
            pieces = _clip_polyline_to_window(seg.points, x0, y0, x1, y1)
            for poly in pieces:
                pieces_per_layer.append((seg.layer, seg.width, poly))

        if not pieces_per_layer and not connected_comps:
            # Nothing of this net is relevant for the window
            continue

        if not pieces_per_layer:
            # Net connects to a component inside but has no visible routing; keep as a bare net
            wn = Net(
                name=net.name,
                connections=connected_comps,
                routing=[],
                use=net.use,
                is_special=net.is_special,
            )
            windowed_nets.append(wn)
            continue

        # If exactly one piece, preserve original net name
        if len(pieces_per_layer) == 1:
            layer, width, poly = pieces_per_layer[0]
            wn = Net(
                name=net.name,
                connections=connected_comps,
                routing=[RoutingSegment(layer=layer, points=poly, width=width)],
                use=net.use,
                is_special=net.is_special,
            )
            windowed_nets.append(wn)
        else:
            # Create subnets for each disconnected piece (per layer). Numbered .1, .2, ...
            for idx, (layer, width, poly) in enumerate(pieces_per_layer, start=1):
                sub_name = f"{net.name}.{idx}"
                wn = Net(
                    name=sub_name,
                    connections=connected_comps,
                    routing=[RoutingSegment(layer=layer, points=poly, width=width)],
                    use=net.use,
                    is_special=net.is_special,
                )
                windowed_nets.append(wn)

    return windowed_nets


def write_def(output_file: Path, def_data: DefData, windowed_components: List[Component],
              windowed_nets: List[Net], windowed_specialnets: List[Net], window: dict,
              offset_x: float = 0.0, offset_y: float = 0.0):
    """Write windowed DEF file.

    Args:
        output_file: Output DEF file path
        def_data: Original DEF data (for vias, etc.)
        windowed_components: Filtered components
        windowed_nets: Filtered nets
        windowed_specialnets: Filtered special nets
        window: Window bounds for DIEAREA
    """
    with open(output_file, 'w') as f:
        # Header
        f.write(f"VERSION {def_data.version} ;\n")
        f.write("   NAMESCASESENSITIVE ON ;\n")
        f.write("   DIVIDERCHAR \"/\" ;\n")
        f.write("   BUSBITCHARS \"()\" ;\n")
        f.write(f"   DESIGN {window['name']} ;\n")
        if def_data.tech:
            f.write(f"   TECHNOLOGY {def_data.tech} ;\n")
        f.write(f"   UNITS DISTANCE MICRONS {def_data.units} ;\n")

        # DIEAREA from window bounds (apply optional origin rebase)
        x1_dbu = int(round((window['x1'] - offset_x) * def_data.units))
        y1_dbu = int(round((window['y1'] - offset_y) * def_data.units))
        x2_dbu = int(round((window['x2'] - offset_x) * def_data.units))
        y2_dbu = int(round((window['y2'] - offset_y) * def_data.units))
        f.write(f"   DIEAREA ( {x1_dbu} {y1_dbu} ) ( {x2_dbu} {y2_dbu} ) ;\n\n")

        # VIAS: preserve original definitions (including VIARULE/LAYERS forms)
        if def_data.vias:
            f.write(f"VIAS {len(def_data.vias)} ;\n")
            for via in def_data.vias:
                if via.raw_def:
                    # Emit verbatim after the name
                    f.write(f"   - {via.name} {via.raw_def}\n")
                else:
                    # Emit explicit RECT geometry if available
                    f.write(f"   - {via.name}\n")
                    for layer, rects in via.layers:
                        for x1, y1, x2, y2 in rects:
                            x1_dbu = int(round((x1 - offset_x) * def_data.units))
                            y1_dbu = int(round((y1 - offset_y) * def_data.units))
                            x2_dbu = int(round((x2 - offset_x) * def_data.units))
                            y2_dbu = int(round((y2 - offset_y) * def_data.units))
                            f.write(f"      + RECT {layer} ( {x1_dbu} {y1_dbu} ) ( {x2_dbu} {y2_dbu} )\n")
                    f.write("   ;\n")
            f.write("END VIAS\n\n")

        # COMPONENTS
        f.write(f"COMPONENTS {len(windowed_components)} ;\n")
        for comp in windowed_components:
            x_dbu = int(round((comp.x - offset_x) * def_data.units))
            y_dbu = int(round((comp.y - offset_y) * def_data.units))
            f.write(f"    - {comp.name} {comp.cell_type} + SOURCE DIST + {comp.status} ( {x_dbu} {y_dbu} ) {comp.orient} ;\n")
        f.write("END COMPONENTS\n\n")

        # PINS (skip for now - typically empty for windows)
        f.write("PINS 0 ;\n")
        f.write("END PINS\n\n")

        # SPECIALNETS
        if windowed_specialnets:
            f.write(f"SPECIALNETS {len(windowed_specialnets)} ;\n")
            for net in windowed_specialnets:
                f.write(f"   - {net.name}")
                for conn in net.connections:
                    f.write(f" ( {conn.component} {conn.pin} )")
                f.write("\n")
                f.write(f"      + USE {net.use}\n")
                # Emit clipped routing segments if present
                for seg in net.routing:
                    if not seg.points or len(seg.points) < 2:
                        continue
                    if seg.width is not None:
                        w = int(round(seg.width * def_data.units))
                        f.write(f"      + ROUTED {seg.layer} {w}")
                    else:
                        f.write(f"      + ROUTED {seg.layer}")
                    for (x, y) in seg.points:
                        xd = int(round((x - offset_x) * def_data.units))
                        yd = int(round((y - offset_y) * def_data.units))
                        f.write(f" ( {xd} {yd} )")
                    f.write("\n")
                f.write("   ;\n")
            f.write("END SPECIALNETS\n\n")

        # NETS
        if windowed_nets:
            f.write(f"NETS {len(windowed_nets)} ;\n")
            for net in windowed_nets:
                f.write(f"   - {net.name}")
                for conn in net.connections:
                    f.write(f" ( {conn.component} {conn.pin} )")
                f.write("\n")
                f.write(f"      + USE {net.use}\n")
                # Emit clipped routing segments
                for seg in net.routing:
                    if not seg.points or len(seg.points) < 2:
                        continue
                    if seg.width is not None:
                        w = int(round(seg.width * def_data.units))
                        f.write(f"      + ROUTED {seg.layer} {w}")
                    else:
                        f.write(f"      + ROUTED {seg.layer}")
                    for (x, y) in seg.points:
                        xd = int(round((x - offset_x) * def_data.units))
                        yd = int(round((y - offset_y) * def_data.units))
                        f.write(f" ( {xd} {yd} )")
                    f.write("\n")
                f.write("   ;\n")
            f.write("END NETS\n\n")

        f.write("END DESIGN\n")

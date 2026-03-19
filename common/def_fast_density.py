from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from torch.profiler import record_function

REPO_ROOT = Path(__file__).resolve().parents[1]

from common.cap3d_fast_density import (
    DEFAULT_TARGET_SIZE,
    DEFAULT_TORCH_EXTENSION_DIR,
    INT16_MAX,
    RECT_COL_CONDUCTOR_ID,
    RECT_COL_COUNT,
    RECT_COL_LAYER,
    RECT_COL_PX_MAX,
    RECT_COL_PX_MIN,
    RECT_COL_PY_MAX,
    RECT_COL_PY_MIN,
    expand_fast_idmaps_cpu,
    expand_fast_idmaps_cuda,
    rasterize_binary_masks_cpu,
    rasterize_binary_masks_cuda,
)
from common.tech_parser import get_metal_layers_and_min_widths
from window_tools.def_parser import Component, DefData, Net, NetConnection, RoutingSegment


DEFAULT_FAST_LEFDEF_EXTENSION_NAME = "capbench_lefdef_fast_parser_v2"
_NATIVE_SOURCE_DIR = REPO_ROOT / "common" / "native"
_FAST_LEFDEF_MODULE = None
_FAST_LEFDEF_LOAD_ATTEMPTED = False
_LEFDEF_TECH_CONTEXT_CACHE: Dict[Tuple[Tuple[Path, ...], Path], "LefDefTechContext"] = {}

_DEF_SUPPLY_NAMES = {"ground"}
_DEFAULT_SYNTHETIC_SOURCE_KIND = "synthetic_lef"
_DEFAULT_REAL_SOURCE_KIND = "real_net"
_POWER_PIN_USES = {"POWER"}
_GROUND_PIN_USES = {"GROUND"}
_POWER_NET_NAMES = {"VDD", "VDDPE", "VPWR", "POWER"}
_GROUND_NET_NAMES = {"VSS", "VSSPE", "VGND", "GND", "GROUND"}
RECT_SOURCE_ROUTE = np.uint8(0)
RECT_SOURCE_SPECIAL_ROUTE = np.uint8(1)
RECT_SOURCE_LEF_PIN = np.uint8(2)
RECT_SOURCE_LEF_OBS = np.uint8(3)
CONDUCTOR_SOURCE_REAL = np.uint8(0)
CONDUCTOR_SOURCE_SYNTHETIC_LEF = np.uint8(1)
_RECT_SOURCE_KIND_BY_CODE = {
    int(RECT_SOURCE_ROUTE): "route",
    int(RECT_SOURCE_SPECIAL_ROUTE): "special_route",
    int(RECT_SOURCE_LEF_PIN): "lef_pin",
    int(RECT_SOURCE_LEF_OBS): "lef_obs",
}
class MissingLefMacroError(RuntimeError):
    """Raised when DEF components reference macros missing from the loaded LEF."""


@dataclass(frozen=True)
class LefRect:
    layer: str
    x0: float
    y0: float
    x1: float
    y1: float
    pin_name: Optional[str] = None
    pin_use: Optional[str] = None
    is_obs: bool = False


@dataclass(frozen=True)
class LefMacro:
    name: str
    size_x: float
    size_y: float
    pin_rects: Tuple[LefRect, ...]
    obs_rects: Tuple[LefRect, ...]


@dataclass(frozen=True)
class LefDefTechContext:
    lef_path: Path
    lef_paths: Tuple[Path, ...]
    tech_path: Path
    channel_layers: List[str]
    layer_name_to_channel: Dict[str, int]
    layer_widths_um: Dict[str, float]
    macros: Dict[str, LefMacro]


@dataclass(frozen=True)
class PreparedDefRasterInput:
    def_path: Path
    lef_path: Path
    lef_paths: Tuple[Path, ...]
    channel_layers: List[str]
    backend: str
    target_size: int
    pixel_resolution: float
    window_bounds: np.ndarray  # [6], float64
    conductor_names_sorted: Optional[List[str]]
    conductor_ids_sorted: np.ndarray  # [N], int16
    conductor_is_synthetic: np.ndarray  # [N], bool
    conductor_source_kind_codes: np.ndarray  # [N], uint8
    packed_rects: np.ndarray  # [B, 6], int32
    packed_rects_torch: Optional[torch.Tensor]
    rect_source_kind_codes: np.ndarray  # [B], uint8
    net_name_to_gpu_id: Optional[Dict[str, int]]
    total_segments: int
    total_endpoint_extensions: int
    active_rectangles: int
    parse_ms: float
    prepare_ms: float
    component_resolution_stats: Dict[str, int]

    @property
    def active_blocks(self) -> int:
        return self.active_rectangles

    @property
    def real_conductor_ids_sorted(self) -> np.ndarray:
        return self.conductor_ids_sorted[~self.conductor_is_synthetic]

    @property
    def conductor_source_kind(self) -> np.ndarray:
        labels = np.empty((self.conductor_source_kind_codes.shape[0],), dtype=object)
        labels[:] = _DEFAULT_REAL_SOURCE_KIND
        labels[self.conductor_source_kind_codes == CONDUCTOR_SOURCE_SYNTHETIC_LEF] = _DEFAULT_SYNTHETIC_SOURCE_KIND
        return labels

    @property
    def rect_source_kind(self) -> np.ndarray:
        labels = np.empty((self.rect_source_kind_codes.shape[0],), dtype=object)
        for code, label in _RECT_SOURCE_KIND_BY_CODE.items():
            labels[self.rect_source_kind_codes == code] = label
        return labels


@dataclass(frozen=True)
class PreparedDefRasterRuntimeInput:
    channel_layers: List[str]
    target_size: int
    pixel_resolution: float
    packed_rects_torch: torch.Tensor
    conductor_ids_torch: torch.Tensor
    active_rectangles: int
    parse_ms: float
    prepare_ms: float


@dataclass(frozen=True)
class PreparedDefBinaryMaskRuntimeInput:
    channel_layers: List[str]
    target_size: int
    pixel_resolution: float
    occupied: torch.Tensor
    master_masks: torch.Tensor
    master_conductor_ids_torch: torch.Tensor
    active_rectangles: int
    parse_ms: float
    prepare_ms: float


@dataclass(frozen=True)
class CompiledDefRuntimeConfig:
    tech_path: Path
    channel_layers: List[str]
    width_map: Dict[str, float]


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def _format_missing_macro_error(
    *,
    def_path: Path,
    lef_paths: Sequence[Path],
    missing_by_macro: Dict[str, List[str]],
    max_examples_per_macro: int = 5,
) -> str:
    window_id = def_path.stem
    missing_instances = sum(len(instances) for instances in missing_by_macro.values())
    lef_list = [str(path) for path in lef_paths]
    lines = [
        f"Missing LEF macro definitions for DEF components in {window_id}",
        f"  def_path={def_path}",
        f"  lef_files={len(lef_list)}",
        *[f"  lef[{idx}]={path}" for idx, path in enumerate(lef_list)],
        f"  missing_macro_types={len(missing_by_macro)} missing_instances={missing_instances}",
    ]
    for macro_name in sorted(missing_by_macro):
        instances = sorted(missing_by_macro[macro_name])
        preview = instances[:max_examples_per_macro]
        suffix = ", ..." if len(instances) > max_examples_per_macro else ""
        lines.append(
            f"  {macro_name}: {', '.join(preview)}{suffix} (instances={len(instances)})"
        )
    return "\n".join(lines)


def _verify_def_macros_exist_in_lef(
    *,
    def_path: Path,
    lef_paths: Sequence[Path],
    def_data: DefData,
    context: LefDefTechContext,
) -> None:
    missing_by_macro: Dict[str, List[str]] = {}
    for component in def_data.components:
        if component.cell_type in context.macros:
            continue
        missing_by_macro.setdefault(component.cell_type, []).append(component.name)
    if missing_by_macro:
        raise MissingLefMacroError(
            _format_missing_macro_error(
                def_path=def_path,
                lef_paths=lef_paths,
                missing_by_macro=missing_by_macro,
            )
        )


def _normalize_layer_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _normalize_net_name(name: str) -> str:
    return str(name).strip()


def _strip_semicolon(value: str) -> str:
    value = value.strip()
    if value.endswith(";"):
        return value[:-1].strip()
    return value


def _resolve_lef_paths(
    *,
    tech_path: Path | str,
    lef_path: Path | str | None = None,
    lef_files: Optional[Sequence[Path | str]] = None,
) -> Tuple[Path, ...]:
    explicit_candidates: List[Path] = []
    if lef_files:
        explicit_candidates.extend(Path(value).resolve() for value in lef_files)
    elif lef_path is not None:
        explicit_candidates.append(Path(lef_path).resolve())

    if explicit_candidates:
        missing = [str(path) for path in explicit_candidates if not path.exists()]
        if missing:
            raise FileNotFoundError(f"LEF file(s) not found: {', '.join(missing)}")
        return tuple(explicit_candidates)

    tech_path = Path(tech_path).resolve()
    candidates = [
        tech_path.with_suffix(".tlef"),
        tech_path.with_suffix(".lef"),
        tech_path.parent / f"{tech_path.stem}.tlef",
        tech_path.parent / f"{tech_path.stem}.lef",
    ]
    resolved: List[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            resolved.append(candidate)
    if resolved:
        return tuple(resolved)
    raise FileNotFoundError(
        f"Could not infer LEF file(s) for tech stack {tech_path}; tried: {', '.join(str(p) for p in candidates)}"
    )


def _materialize_compact_backend_lef_path(lef_paths: Sequence[Path]) -> Path:
    resolved_paths = tuple(Path(path).resolve() for path in lef_paths)
    if not resolved_paths:
        raise ValueError("At least one LEF path is required for compact DEF raster preparation.")
    if len(resolved_paths) == 1:
        return resolved_paths[0]

    digest = hashlib.sha256()
    for path in resolved_paths:
        stat = path.stat()
        digest.update(str(path).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
    merged_dir = DEFAULT_TORCH_EXTENSION_DIR / "merged_lef_inputs"
    merged_dir.mkdir(parents=True, exist_ok=True)
    merged_path = merged_dir / f"{digest.hexdigest()[:16]}.lef"
    if merged_path.exists():
        return merged_path

    parts: List[str] = []
    for path in resolved_paths:
        parts.append(f"# BEGIN LEF {path}\n")
        parts.append(path.read_text(encoding="utf-8"))
        if not parts[-1].endswith("\n"):
            parts.append("\n")
        parts.append(f"# END LEF {path}\n")
    merged_path.write_text("".join(parts), encoding="utf-8")
    return merged_path


def load_fast_lefdef_parser_extension():
    global _FAST_LEFDEF_MODULE, _FAST_LEFDEF_LOAD_ATTEMPTED

    if _FAST_LEFDEF_MODULE is not None:
        return _FAST_LEFDEF_MODULE
    if _FAST_LEFDEF_LOAD_ATTEMPTED:
        raise RuntimeError("The fast LEF+DEF parser extension failed to initialize earlier in this process.")

    _FAST_LEFDEF_LOAD_ATTEMPTED = True

    try:
        from torch.utils.cpp_extension import load
    except ImportError as exc:
        raise RuntimeError("torch.utils.cpp_extension is required to build the fast LEF+DEF parser extension.") from exc

    source_paths = [
        _NATIVE_SOURCE_DIR / "lefdef_fast_parser.c",
        _NATIVE_SOURCE_DIR / "lefdef_fast_parser_bindings.cpp",
        _NATIVE_SOURCE_DIR / "lefdef_fast_parser_compiled.cpp",
    ]
    missing_sources = [str(path) for path in source_paths if not path.exists()]
    if missing_sources:
        raise RuntimeError(
            "Fast LEF+DEF parser sources are missing: "
            + ", ".join(missing_sources)
        )

    build_dir = DEFAULT_TORCH_EXTENSION_DIR / DEFAULT_FAST_LEFDEF_EXTENSION_NAME
    build_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_EXTENSIONS_DIR", str(DEFAULT_TORCH_EXTENSION_DIR))

    try:
        _FAST_LEFDEF_MODULE = load(
            name=DEFAULT_FAST_LEFDEF_EXTENSION_NAME,
            sources=[str(path) for path in source_paths],
            extra_cflags=["-O3"],
            extra_include_paths=[str(_NATIVE_SOURCE_DIR)],
            build_directory=str(build_dir),
            verbose=False,
        )
    except Exception as exc:
        raise RuntimeError(
            "Failed to build or load the fast LEF+DEF parser extension "
            f"'{DEFAULT_FAST_LEFDEF_EXTENSION_NAME}' from {build_dir}"
        ) from exc
    return _FAST_LEFDEF_MODULE


def load_fast_lef_abstract_parser_extension():
    return load_fast_lefdef_parser_extension()


def _parse_lef_macros(lef_path: Path) -> Dict[str, LefMacro]:
    module = load_fast_lefdef_parser_extension()
    parsed = module.parse_lef_abstracts_file(str(lef_path))
    macros: Dict[str, LefMacro] = {}
    for macro_name, data in parsed["macros"].items():
        pin_rects = tuple(
            LefRect(
                layer=str(rec[2]),
                x0=float(rec[3]),
                y0=float(rec[4]),
                x1=float(rec[5]),
                y1=float(rec[6]),
                pin_name=str(rec[0]),
                pin_use=str(rec[1]),
                is_obs=False,
            )
            for rec in data["pin_rects"]
        )
        obs_rects = tuple(
            LefRect(
                layer=str(rec[0]),
                x0=float(rec[1]),
                y0=float(rec[2]),
                x1=float(rec[3]),
                y1=float(rec[4]),
                is_obs=True,
            )
            for rec in data["obs_rects"]
        )
        macros[str(macro_name)] = LefMacro(
            name=str(macro_name),
            size_x=float(data["size_x"]),
            size_y=float(data["size_y"]),
            pin_rects=pin_rects,
            obs_rects=obs_rects,
        )
    return macros

def _parse_lef_macros_from_files(lef_paths: Sequence[Path]) -> Dict[str, LefMacro]:
    merged: Dict[str, LefMacro] = {}
    for lef_path in lef_paths:
        merged.update(_parse_lef_macros(lef_path))
    return merged


def _parse_def_compact(def_path: Path) -> DefData:
    module = load_fast_lefdef_parser_extension()
    parsed = module.parse_def_compact(str(def_path))

    def _build_net(data: dict) -> Net:
        connections = [
            NetConnection(component=str(conn[0]), pin=str(conn[1]))
            for conn in data["connections"]
        ]
        routing = [
            RoutingSegment(
                layer=str(segment["layer"]),
                points=[(float(point[0]), float(point[1])) for point in segment["points"]],
                width=float(segment["width"]) if bool(segment["has_width"]) else None,
            )
            for segment in data["routing"]
        ]
        return Net(
            name=str(data["name"]),
            connections=connections,
            routing=routing,
            use=str(data["use"]),
            is_special=bool(data["is_special"]),
        )

    components = [
        Component(
            name=str(component[0]),
            cell_type=str(component[1]),
            x=float(component[2]),
            y=float(component[3]),
            orient=str(component[4]),
            status=str(component[5]),
        )
        for component in parsed["components"]
    ]
    nets = [_build_net(data) for data in parsed["nets"]]
    specialnets = [_build_net(data) for data in parsed["specialnets"]]
    return DefData(
        design_name=str(parsed["design_name"]),
        units=int(parsed["units"]),
        diearea=tuple(float(value) for value in parsed["diearea"]),
        rows=[],
        components=components,
        nets=nets,
        specialnets=specialnets,
        vias=[],
        pins=[],
        version="5.7",
        tech=str(parsed["tech"]),
    )


def _load_lefdef_tech_context(lef_paths: Sequence[Path], tech_path: Path) -> LefDefTechContext:
    resolved_lef_paths = tuple(path.resolve() for path in lef_paths)
    if not resolved_lef_paths:
        raise ValueError(f"At least one LEF path is required for {tech_path}")
    key = (resolved_lef_paths, tech_path.resolve())
    cached = _LEFDEF_TECH_CONTEXT_CACHE.get(key)
    if cached is not None:
        return cached

    metal_layers, min_widths = get_metal_layers_and_min_widths(str(tech_path))
    layer_name_to_channel: Dict[str, int] = {}
    layer_widths_um: Dict[str, float] = {}
    for idx, layer_name in enumerate(metal_layers):
        normalized = _normalize_layer_name(layer_name)
        layer_name_to_channel[normalized] = idx
        width = min_widths.get(layer_name)
        if width is not None:
            layer_widths_um[normalized] = float(width)

    ctx = LefDefTechContext(
        lef_path=resolved_lef_paths[0],
        lef_paths=resolved_lef_paths,
        tech_path=tech_path.resolve(),
        channel_layers=list(metal_layers),
        layer_name_to_channel=layer_name_to_channel,
        layer_widths_um=layer_widths_um,
        macros=_parse_lef_macros_from_files(resolved_lef_paths),
    )
    _LEFDEF_TECH_CONTEXT_CACHE[key] = ctx
    return ctx


def _resolve_window_bounds(def_data: DefData) -> Tuple[np.ndarray, np.float64, np.float64]:
    x_min, y_min, x_max, y_max = def_data.diearea
    if not np.isfinite([x_min, y_min, x_max, y_max]).all():
        raise ValueError("DEF DIEAREA contains non-finite coordinates.")
    if x_max <= x_min or y_max <= y_min:
        raise ValueError(f"DEF DIEAREA is invalid: {def_data.diearea}")
    bounds = np.asarray([x_min, y_min, 0.0, x_max, y_max, 0.0], dtype=np.float64)
    return bounds, np.float64(x_min), np.float64(y_min)


def _resolve_pixel_resolution(bounds: np.ndarray, target_size: int, pixel_resolution: Optional[float]) -> np.float32:
    width_um = np.float32(bounds[3] - bounds[0])
    height_um = np.float32(bounds[4] - bounds[1])
    if pixel_resolution is None:
        resolved = np.float32(max(float(width_um), float(height_um)) / float(target_size))
    else:
        resolved = np.float32(pixel_resolution)
    if not np.isfinite(resolved) or float(resolved) <= 0.0:
        raise ValueError(f"Invalid pixel resolution resolved from DEF window: {resolved}")
    return resolved


def _resolve_raster_bounds(
    raster_bounds: Optional[Sequence[float] | np.ndarray],
    fallback_bounds: np.ndarray,
) -> Tuple[np.ndarray, np.float64, np.float64]:
    if raster_bounds is None:
        bounds = np.asarray(fallback_bounds, dtype=np.float64)
    else:
        flat = np.asarray(raster_bounds, dtype=np.float64).reshape(-1)
        if flat.shape[0] != 4:
            raise ValueError(f"raster_bounds must provide 4 values [x_min, y_min, x_max, y_max], got shape {flat.shape}")
        x_min, y_min, x_max, y_max = flat.tolist()
        bounds = np.asarray([x_min, y_min, 0.0, x_max, y_max, 0.0], dtype=np.float64)
    if not np.isfinite(bounds[[0, 1, 3, 4]]).all():
        raise ValueError("Raster bounds contain non-finite coordinates.")
    if bounds[3] <= bounds[0] or bounds[4] <= bounds[1]:
        raise ValueError(f"Invalid raster bounds: {bounds}")
    return bounds, np.float64(bounds[0]), np.float64(bounds[1])


def _resolve_native_channel_layers(
    tech_path: Path,
    selected_layers: Optional[Sequence[str]],
) -> Tuple[List[str], Dict[str, float]]:
    metal_layers, min_widths = get_metal_layers_and_min_widths(str(tech_path))
    if selected_layers is None:
        channel_layers = list(metal_layers)
    else:
        requested = {_normalize_layer_name(name) for name in selected_layers}
        channel_layers = [layer for layer in metal_layers if _normalize_layer_name(layer) in requested]

    width_map: Dict[str, float] = {}
    for layer_name in channel_layers:
        width = min_widths.get(layer_name)
        if width is not None:
            width_map[_normalize_layer_name(layer_name)] = float(width)
    return channel_layers, width_map


def _select_layer_map(
    context: LefDefTechContext,
    selected_layers: Optional[Sequence[str]],
) -> Tuple[List[str], Dict[str, int]]:
    if selected_layers is None:
        channel_layers = list(context.channel_layers)
    else:
        requested = {_normalize_layer_name(name): str(name) for name in selected_layers}
        channel_layers = [layer for layer in context.channel_layers if _normalize_layer_name(layer) in requested]
    layer_name_to_channel = {
        _normalize_layer_name(layer_name): idx for idx, layer_name in enumerate(channel_layers)
    }
    return channel_layers, layer_name_to_channel


def _iter_routed_nets(def_data: DefData):
    for net in def_data.nets:
        yield net, False
    for net in def_data.specialnets:
        yield net, True


def _include_net(net: Net, *, include_supply_nets: bool) -> bool:
    name = _normalize_net_name(net.name)
    if not name:
        return False
    if include_supply_nets:
        return True
    if net.is_power:
        return False
    return name.lower() not in _DEF_SUPPLY_NAMES


def _classify_supply_net(net_name: str) -> Optional[str]:
    upper = str(net_name).upper()
    if upper in _POWER_NET_NAMES:
        return "POWER"
    if upper in _GROUND_NET_NAMES:
        return "GROUND"
    return None


def _segment_to_rects(
    segments: Sequence[RoutingSegment],
    width_um: float,
) -> Tuple[List[Tuple[float, float, float, float]], int]:
    rects: List[Tuple[float, float, float, float]] = []
    endpoint_extensions = 0
    if width_um <= 0.0 or not np.isfinite(width_um):
        raise ValueError(f"Invalid route width: {width_um}")

    half = 0.5 * float(width_um)
    edges: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    for segment in segments:
        for start, end in zip(segment.points, segment.points[1:]):
            edges.append(((float(start[0]), float(start[1])), (float(end[0]), float(end[1]))))

    def edge_orientation(edge: Tuple[Tuple[float, float], Tuple[float, float]]) -> str:
        (ax, ay), (bx, by) = edge
        if np.isclose(ay, by) and not np.isclose(ax, bx):
            return "h"
        if np.isclose(ax, bx) and not np.isclose(ay, by):
            return "v"
        raise ValueError(
            f"Non-Manhattan DEF segment edge: ({ax}, {ay}) -> ({bx}, {by})"
        )

    for start, end in edges:
        x0, y0 = float(start[0]), float(start[1])
        x1, y1 = float(end[0]), float(end[1])
        if np.isclose(x0, x1) and np.isclose(y0, y1):
            continue
        orient = edge_orientation((start, end))
        if orient == "h":
            lo = min(x0, x1) - half
            hi = max(x0, x1) + half
            rects.append((lo, hi, y0 - half, y0 + half))
            endpoint_extensions += 2
            continue
        if orient == "v":
            lo = min(y0, y1) - half
            hi = max(y0, y1) + half
            rects.append((x0 - half, x0 + half, lo, hi))
            endpoint_extensions += 2
            continue
    return rects, endpoint_extensions


def _touches_or_overlaps(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float], eps: float = 1e-9) -> bool:
    return not (a[1] < b[0] - eps or b[1] < a[0] - eps or a[3] < b[2] - eps or b[3] < a[2] - eps)


def _apply_orientation(point: Tuple[float, float], orient: str) -> Tuple[float, float]:
    x, y = float(point[0]), float(point[1])
    orient = orient.upper()
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


def _transform_rect(rect: LefRect, macro: LefMacro, component: Component) -> Tuple[float, float, float, float]:
    corners = [
        _apply_orientation((0.0, 0.0), component.orient),
        _apply_orientation((macro.size_x, 0.0), component.orient),
        _apply_orientation((0.0, macro.size_y), component.orient),
        _apply_orientation((macro.size_x, macro.size_y), component.orient),
    ]
    bbox_min_x = min(x for x, _ in corners)
    bbox_min_y = min(y for _, y in corners)

    rect_corners = [
        _apply_orientation((rect.x0, rect.y0), component.orient),
        _apply_orientation((rect.x1, rect.y0), component.orient),
        _apply_orientation((rect.x0, rect.y1), component.orient),
        _apply_orientation((rect.x1, rect.y1), component.orient),
    ]
    xs = [component.x + x - bbox_min_x for x, _ in rect_corners]
    ys = [component.y + y - bbox_min_y for _, y in rect_corners]
    return min(xs), max(xs), min(ys), max(ys)


def _clip_world_rect(
    rect: Tuple[float, float, float, float],
    bounds: np.ndarray,
) -> Optional[Tuple[float, float, float, float]]:
    x0, x1, y0, y1 = rect
    x0 = max(float(bounds[0]), x0)
    x1 = min(float(bounds[3]), x1)
    y0 = max(float(bounds[1]), y0)
    y1 = min(float(bounds[4]), y1)
    if x0 >= x1 or y0 >= y1:
        return None
    return x0, x1, y0, y1


def _world_rect_to_pixels(
    rect: Tuple[float, float, float, float],
    *,
    x_min: float,
    y_min: float,
    pixel_resolution: float,
    target_size: int,
) -> Optional[Tuple[int, int, int, int]]:
    rect_x0, rect_x1, rect_y0, rect_y1 = rect
    px_min = int(np.floor((rect_x0 - x_min) / pixel_resolution))
    px_max = int(np.ceil((rect_x1 - x_min) / pixel_resolution))
    py_min = int(np.floor((rect_y0 - y_min) / pixel_resolution))
    py_max = int(np.ceil((rect_y1 - y_min) / pixel_resolution))

    px_min = int(np.clip(px_min, 0, target_size))
    px_max = int(np.clip(px_max, 0, target_size))
    py_min = int(np.clip(py_min, 0, target_size))
    py_max = int(np.clip(py_max, 0, target_size))
    if px_min >= px_max or py_min >= py_max:
        return None
    return px_min, px_max, py_min, py_max


def _build_instance_pin_to_net(def_data: DefData, *, include_supply_nets: bool) -> Dict[Tuple[str, str], str]:
    instance_pin_to_net: Dict[Tuple[str, str], str] = {}
    for net, _is_special in _iter_routed_nets(def_data):
        net_name = _normalize_net_name(net.name)
        if not _include_net(net, include_supply_nets=include_supply_nets):
            continue
        for conn in net.connections:
            comp_name = _normalize_net_name(conn.component)
            pin_name = _normalize_net_name(conn.pin)
            if not comp_name or not pin_name or comp_name.upper() == "PIN":
                continue
            instance_pin_to_net[(comp_name, pin_name)] = net_name
    return instance_pin_to_net


def _build_supply_use_to_net(def_data: DefData, *, include_supply_nets: bool) -> Dict[str, str]:
    supply_use_to_net: Dict[str, str] = {}
    if not include_supply_nets:
        return supply_use_to_net
    for net in def_data.specialnets:
        net_name = _normalize_net_name(net.name)
        if not net_name:
            continue
        supply_use = _classify_supply_net(net_name)
        if supply_use is None:
            supply_use = str(net.use).upper() if str(net.use).upper() in {"POWER", "GROUND"} else None
        if supply_use is None:
            continue
        supply_use_to_net.setdefault(supply_use, net_name)
    return supply_use_to_net


def _collect_touching_nets(
    primitives: Sequence[Tuple[Tuple[float, float, float, float], Optional[str], bool]],
    member_indices: Sequence[int],
    touch_rects: Sequence[Tuple[Tuple[float, float, float, float], str]],
) -> set[str]:
    touched: set[str] = set()
    if not touch_rects:
        return touched
    for idx in member_indices:
        rect = primitives[idx][0]
        for touch_rect, net_name in touch_rects:
            if _touches_or_overlaps(rect, touch_rect):
                touched.add(net_name)
    return touched


def _component_layer_primitives(
    component: Component,
    macro: LefMacro,
    *,
    bounds: np.ndarray,
    layer_name_to_channel: Dict[str, int],
    instance_pin_to_net: Dict[Tuple[str, str], str],
    supply_use_to_net: Dict[str, str],
) -> Dict[str, List[Tuple[Tuple[float, float, float, float], Optional[str], bool, str, str]]]:
    per_layer: Dict[str, List[Tuple[Tuple[float, float, float, float], Optional[str], bool, str, str]]] = {}
    instance_name = _normalize_net_name(component.name)

    for rect in macro.pin_rects:
        normalized_layer = _normalize_layer_name(rect.layer)
        if normalized_layer not in layer_name_to_channel:
            continue
        world_rect = _clip_world_rect(_transform_rect(rect, macro, component), bounds)
        if world_rect is None:
            continue
        pin_name = _normalize_net_name(rect.pin_name or "")
        attached_net = instance_pin_to_net.get((instance_name, pin_name))
        if attached_net is None:
            pin_use = str(rect.pin_use or "").upper()
            if pin_use in _POWER_PIN_USES | _GROUND_PIN_USES:
                attached_net = supply_use_to_net.get(pin_use)
        per_layer.setdefault(normalized_layer, []).append(
            (world_rect, attached_net, False, pin_name, str(rect.pin_use or "").upper())
        )

    for rect in macro.obs_rects:
        normalized_layer = _normalize_layer_name(rect.layer)
        if normalized_layer not in layer_name_to_channel:
            continue
        world_rect = _clip_world_rect(_transform_rect(rect, macro, component), bounds)
        if world_rect is None:
            continue
        per_layer.setdefault(normalized_layer, []).append((world_rect, None, True, "", ""))

    return per_layer


def _assign_component_conductors(
    component: Component,
    macro: LefMacro,
    *,
    bounds: np.ndarray,
    layer_name_to_channel: Dict[str, int],
    instance_pin_to_net: Dict[Tuple[str, str], str],
    supply_use_to_net: Dict[str, str],
    touch_rects_by_layer: Dict[str, List[Tuple[Tuple[float, float, float, float], str]]],
) -> Tuple[List[Tuple[str, str, int, Tuple[float, float, float, float], np.uint8]], Dict[str, int]]:
    result: List[Tuple[str, str, int, Tuple[float, float, float, float], np.uint8]] = []
    stats = {
        "explicit_pin": 0,
        "supply_fallback": 0,
        "routed_touch": 0,
        "pin_and_geom": 0,
        "ambiguous": 0,
        "no_net": 0,
    }
    per_layer = _component_layer_primitives(
        component,
        macro,
        bounds=bounds,
        layer_name_to_channel=layer_name_to_channel,
        instance_pin_to_net=instance_pin_to_net,
        supply_use_to_net=supply_use_to_net,
    )

    for normalized_layer, primitives in per_layer.items():
        uf = _UnionFind(len(primitives))
        for i in range(len(primitives)):
            rect_i = primitives[i][0]
            for j in range(i + 1, len(primitives)):
                same_pin = bool(primitives[i][3]) and primitives[i][3] == primitives[j][3]
                if same_pin or _touches_or_overlaps(rect_i, primitives[j][0]):
                    uf.union(i, j)

        groups: Dict[int, List[int]] = {}
        for idx in range(len(primitives)):
            root = uf.find(idx)
            groups.setdefault(root, []).append(idx)

        for component_idx, member_indices in enumerate(sorted(groups.values(), key=lambda ids: min(ids))):
            pin_nets = {
                primitives[idx][1]
                for idx in member_indices
                if primitives[idx][1] is not None and _normalize_net_name(primitives[idx][1])
            }
            geom_nets = _collect_touching_nets(primitives, member_indices, touch_rects_by_layer.get(normalized_layer, ()))
            touched_nets = sorted(
                {
                    _normalize_net_name(net_name)
                    for net_name in list(pin_nets) + list(geom_nets)
                    if net_name is not None and _normalize_net_name(net_name)
                }
            )
            if len(touched_nets) == 1:
                conductor_name = touched_nets[0]
                source_kind = _DEFAULT_REAL_SOURCE_KIND
                explicit_pin_match = False
                supply_fallback_match = False
                for idx in member_indices:
                    if primitives[idx][1] != conductor_name:
                        continue
                    pin_name = primitives[idx][3]
                    pin_use = primitives[idx][4]
                    if pin_name and (_normalize_net_name(component.name), pin_name) in instance_pin_to_net:
                        explicit_pin_match = True
                    elif pin_use in {"POWER", "GROUND"}:
                        supply_fallback_match = True
                if pin_nets and geom_nets:
                    stats["pin_and_geom"] += 1
                elif explicit_pin_match:
                    stats["explicit_pin"] += 1
                elif supply_fallback_match:
                    stats["supply_fallback"] += 1
                else:
                    stats["routed_touch"] += 1
            else:
                conductor_name = f"__lef__/{_normalize_net_name(component.name)}/{normalized_layer}/{component_idx}"
                source_kind = _DEFAULT_SYNTHETIC_SOURCE_KIND
                if len(touched_nets) == 0:
                    stats["no_net"] += 1
                else:
                    stats["ambiguous"] += 1

            channel = layer_name_to_channel[normalized_layer]
            for idx in member_indices:
                rect_source_kind = RECT_SOURCE_LEF_OBS if primitives[idx][2] else RECT_SOURCE_LEF_PIN
                result.append((conductor_name, source_kind, channel, primitives[idx][0], rect_source_kind))

    return result, stats


def _prepare_reference_unique_def_raster_input(
    *,
    def_path: Path,
    tech_path: Path,
    lef_path: Path,
    lef_paths: Optional[Sequence[Path]] = None,
    target_size: int,
    pixel_resolution: Optional[float],
    selected_layers: Optional[Sequence[str]],
    raster_bounds: Optional[Sequence[float] | np.ndarray],
    include_supply_nets: bool,
) -> PreparedDefRasterInput:
    channel_layers, width_map = _resolve_native_channel_layers(tech_path, selected_layers)
    module = load_fast_lefdef_parser_extension()

    with record_function("lefdef.prepare.native_unique"):
        prepared = module.prepare_def_raster_compact(
            str(def_path),
            str(lef_path),
            list(channel_layers),
            dict(width_map),
            int(target_size),
            None if pixel_resolution is None else float(pixel_resolution),
            None if raster_bounds is None else [float(value) for value in np.asarray(raster_bounds, dtype=np.float64).reshape(-1)],
            bool(include_supply_nets),
        )

    with record_function("lefdef.prepare.python_convert"):
        return _prepared_input_from_native_result(
            def_path=def_path,
            lef_path=lef_path,
            lef_paths=tuple(Path(path).resolve() for path in (lef_paths or (lef_path,))),
            channel_layers=channel_layers,
            target_size=target_size,
            prepared=prepared,
            backend="native_compact",
        )


def _prepared_input_from_native_result(
    *,
    def_path: Path,
    lef_path: Path,
    lef_paths: Sequence[Path],
    channel_layers: Sequence[str],
    target_size: int,
    prepared: object,
    backend: str,
) -> PreparedDefRasterInput:
    packed_rects_raw = prepared["packed_rects"]
    packed_rects_torch: Optional[torch.Tensor]
    with record_function("lefdef.prepare.packed_rects_tensor"):
        if isinstance(packed_rects_raw, torch.Tensor):
            packed_rects_torch = packed_rects_raw.contiguous()
            packed_rects = packed_rects_torch.numpy()
        else:
            packed_rects_torch = None
            packed_rects = np.asarray(packed_rects_raw, dtype=np.int32)
    rect_codes = np.asarray(prepared["rect_source_kind_codes"], dtype=np.uint8)
    for code in rect_codes.tolist():
        if int(code) not in _RECT_SOURCE_KIND_BY_CODE:
            raise ValueError(f"Unknown rect source kind code returned by native prepare path: {code}")
    conductor_names_raw = prepared.get("conductor_names_sorted", None)
    conductor_names_sorted = None if conductor_names_raw is None else [str(name) for name in list(conductor_names_raw)]
    conductor_count = int(prepared["conductor_count"])
    real_conductor_count = int(prepared["real_conductor_count"])
    if real_conductor_count < 0 or real_conductor_count > conductor_count:
        raise ValueError(
            f"Invalid real_conductor_count returned by native prepare path for {def_path}: {real_conductor_count}"
        )
    if conductor_names_sorted is not None and len(conductor_names_sorted) != conductor_count:
        raise ValueError(
            f"Native prepare returned {len(conductor_names_sorted)} conductor names but packed_rects use {conductor_count} conductor IDs"
        )
    conductor_is_synthetic = np.zeros((conductor_count,), dtype=bool)
    conductor_source_kind_codes = np.zeros((conductor_count,), dtype=np.uint8)
    if real_conductor_count < conductor_count:
        conductor_is_synthetic[real_conductor_count:] = True
        conductor_source_kind_codes[real_conductor_count:] = CONDUCTOR_SOURCE_SYNTHETIC_LEF
    net_name_to_gpu_id = None
    if conductor_names_sorted is not None:
        net_name_to_gpu_id = {name: idx + 1 for idx, name in enumerate(conductor_names_sorted)}

    return PreparedDefRasterInput(
        def_path=def_path,
        lef_path=lef_path,
        lef_paths=tuple(Path(path).resolve() for path in lef_paths),
        channel_layers=list(channel_layers),
        backend=backend,
        target_size=int(target_size),
        pixel_resolution=float(prepared["pixel_resolution"]),
        window_bounds=np.asarray(prepared["window_bounds"], dtype=np.float64),
        conductor_names_sorted=conductor_names_sorted,
        conductor_ids_sorted=np.arange(1, conductor_count + 1, dtype=np.int16),
        conductor_is_synthetic=conductor_is_synthetic,
        conductor_source_kind_codes=conductor_source_kind_codes,
        packed_rects=packed_rects,
        packed_rects_torch=packed_rects_torch,
        rect_source_kind_codes=rect_codes,
        net_name_to_gpu_id=net_name_to_gpu_id,
        total_segments=int(prepared["total_segments"]),
        total_endpoint_extensions=int(prepared["total_endpoint_extensions"]),
        active_rectangles=int(prepared["active_rectangles"]),
        parse_ms=float(prepared["parse_ms"]),
        prepare_ms=float(prepared["prepare_ms"]),
        component_resolution_stats={str(key): int(value) for key, value in dict(prepared["component_resolution_stats"]).items()},
    )


def _default_lef_metadata_path(tech_path: Path) -> Path:
    return (tech_path.parent / f"{tech_path.stem}.lef").resolve()


def _supports_compiled_recipe_backend(tech_path: Path) -> bool:
    tech_key = _normalize_layer_name(tech_path.stem) or _normalize_layer_name(tech_path.name)
    return tech_key in {"nangate45", "sky130hd"}


def _compiled_recipe_tech_key(tech_path: Path) -> str:
    tech_key = _normalize_layer_name(tech_path.stem) or _normalize_layer_name(tech_path.name)
    if not _supports_compiled_recipe_backend(tech_path):
        raise ValueError(f"Unsupported compiled recipe tech: {tech_path}")
    return tech_key


def _validate_compiled_recipe_inputs(tech_path: Path) -> None:
    if _supports_compiled_recipe_backend(tech_path):
        return
    raise ValueError(
        "Compiled prepare only supports the static nangate45/sky130hd recipe tables; "
        f"got tech={tech_path}"
    )


def build_compiled_def_runtime_config(
    tech_path: Path | str,
    *,
    selected_layers: Optional[Sequence[str]] = None,
) -> CompiledDefRuntimeConfig:
    tech_path = Path(tech_path).resolve()
    _validate_compiled_recipe_inputs(tech_path)
    channel_layers, width_map = _resolve_native_channel_layers(tech_path, selected_layers)
    return CompiledDefRuntimeConfig(
        tech_path=tech_path,
        channel_layers=channel_layers,
        width_map=width_map,
    )


def _prepare_compiled_def_raster_input(
    *,
    def_path: Path,
    tech_path: Path,
    target_size: int,
    pixel_resolution: Optional[float],
    selected_layers: Optional[Sequence[str]],
    raster_bounds: Optional[Sequence[float] | np.ndarray],
    include_supply_nets: bool,
    include_conductor_names: bool,
) -> PreparedDefRasterInput:
    channel_layers, width_map = _resolve_native_channel_layers(tech_path, selected_layers)
    module = load_fast_lefdef_parser_extension()
    _validate_compiled_recipe_inputs(tech_path)

    with record_function("lefdef.prepare.native_compiled_call"):
        prepared = module.prepare_def_raster_compiled(
            str(def_path),
            _compiled_recipe_tech_key(tech_path),
            list(channel_layers),
            dict(width_map),
            int(target_size),
            None if pixel_resolution is None else float(pixel_resolution),
            None if raster_bounds is None else [float(value) for value in np.asarray(raster_bounds, dtype=np.float64).reshape(-1)],
            bool(include_supply_nets),
            bool(include_conductor_names),
        )

    with record_function("lefdef.prepare.python_convert"):
        return _prepared_input_from_native_result(
            def_path=def_path,
            lef_path=_default_lef_metadata_path(tech_path),
            lef_paths=(_default_lef_metadata_path(tech_path),),
            channel_layers=channel_layers,
            target_size=target_size,
            prepared=prepared,
            backend="compiled_recipe",
        )


def prepare_fast_def_raster_runtime(
    def_path: Path | str,
    runtime_config: CompiledDefRuntimeConfig,
    *,
    target_size: int = DEFAULT_TARGET_SIZE,
    pixel_resolution: Optional[float] = None,
    raster_bounds: Optional[Sequence[float] | np.ndarray] = None,
    include_supply_nets: bool = False,
) -> PreparedDefRasterRuntimeInput:
    def_path = Path(def_path).resolve()
    if target_size <= 0:
        raise ValueError(f"target_size must be positive, got {target_size}")
    module = load_fast_lefdef_parser_extension()

    with record_function("lefdef.prepare.native_runtime_call"):
        prepared = module.prepare_def_raster_compiled_runtime(
            str(def_path),
            _compiled_recipe_tech_key(runtime_config.tech_path),
            list(runtime_config.channel_layers),
            dict(runtime_config.width_map),
            int(target_size),
            None if pixel_resolution is None else float(pixel_resolution),
            None if raster_bounds is None else [float(value) for value in np.asarray(raster_bounds, dtype=np.float64).reshape(-1)],
            bool(include_supply_nets),
        )

    return PreparedDefRasterRuntimeInput(
        channel_layers=list(runtime_config.channel_layers),
        target_size=int(target_size),
        pixel_resolution=float(prepared["pixel_resolution"]),
        packed_rects_torch=prepared["packed_rects"].contiguous(),
        conductor_ids_torch=prepared["conductor_ids"].contiguous(),
        active_rectangles=int(prepared["active_rectangles"]),
        parse_ms=float(prepared["parse_ms"]),
        prepare_ms=float(prepared["prepare_ms"]),
    )


def prepare_fast_def_binary_masks_runtime(
    def_path: Path | str,
    runtime_config: CompiledDefRuntimeConfig,
    *,
    target_size: int = DEFAULT_TARGET_SIZE,
    pixel_resolution: Optional[float] = None,
    raster_bounds: Optional[Sequence[float] | np.ndarray] = None,
    include_supply_nets: bool = False,
    device: torch.device,
) -> PreparedDefBinaryMaskRuntimeInput:
    if device.type != "cuda":
        raise ValueError(f"prepare_fast_def_binary_masks_runtime requires a CUDA device, got: {device}")
    prepared = prepare_fast_def_raster_runtime(
        def_path=def_path,
        runtime_config=runtime_config,
        target_size=target_size,
        pixel_resolution=pixel_resolution,
        raster_bounds=raster_bounds,
        include_supply_nets=include_supply_nets,
    )
    real_conductor_count = int(prepared.conductor_ids_torch.numel())
    with record_function("lefdef.prepare.upload_rects"):
        packed_rects_cuda = prepared.packed_rects_torch.to(
            device=device,
            dtype=torch.int32,
            non_blocking=True,
        ).contiguous()
    with record_function("lefdef.prepare.rasterize_binary_masks"):
        occupied, master_masks = rasterize_binary_masks_cuda(
            packed_rects_cuda,
            num_layers=len(prepared.channel_layers),
            target_size=prepared.target_size,
            real_conductor_count=real_conductor_count,
        )
    return PreparedDefBinaryMaskRuntimeInput(
        channel_layers=list(prepared.channel_layers),
        target_size=prepared.target_size,
        pixel_resolution=prepared.pixel_resolution,
        occupied=occupied,
        master_masks=master_masks,
        master_conductor_ids_torch=prepared.conductor_ids_torch.to(device=device, dtype=torch.int16, non_blocking=True).contiguous(),
        active_rectangles=prepared.active_rectangles,
        parse_ms=prepared.parse_ms,
        prepare_ms=prepared.prepare_ms,
    )


def prepare_fast_def_binary_masks_cpu(
    prepared: PreparedDefRasterInput,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    real_conductor_ids = np.asarray(prepared.real_conductor_ids_sorted, dtype=np.int16)
    occupied, master_masks = rasterize_binary_masks_cpu(
        prepared.packed_rects,
        num_layers=len(prepared.channel_layers),
        target_size=prepared.target_size,
        real_conductor_count=int(real_conductor_ids.shape[0]),
    )
    return occupied, master_masks, real_conductor_ids


def _prepare_reference_generic_def_raster_input(
    def_path: Path | str,
    tech_path: Path | str,
    *,
    lef_path: Path | str | None = None,
    lef_files: Optional[Sequence[Path | str]] = None,
    target_size: int = DEFAULT_TARGET_SIZE,
    pixel_resolution: Optional[float] = None,
    selected_layers: Optional[Sequence[str]] = None,
    raster_bounds: Optional[Sequence[float] | np.ndarray] = None,
    include_supply_nets: bool = False,
) -> PreparedDefRasterInput:
    def_path = Path(def_path).resolve()
    tech_path = Path(tech_path).resolve()
    lef_paths = _resolve_lef_paths(tech_path=tech_path, lef_path=lef_path, lef_files=lef_files)
    primary_lef_path = lef_paths[0]
    if target_size <= 0:
        raise ValueError(f"target_size must be positive, got {target_size}")

    parse_start = perf_counter()
    with record_function("lefdef.prepare.parse_def"):
        def_data = _parse_def_compact(def_path)
    with record_function("lefdef.prepare.load_tech_context"):
        context = _load_lefdef_tech_context(lef_paths, tech_path)
    with record_function("lefdef.prepare.verify_macros"):
        _verify_def_macros_exist_in_lef(
            def_path=def_path,
            lef_paths=lef_paths,
            def_data=def_data,
            context=context,
        )
    parse_ms = (perf_counter() - parse_start) * 1000.0

    prep_start = perf_counter()
    with record_function("lefdef.prepare.resolve_setup"):
        diearea_bounds, _diearea_x_min, _diearea_y_min = _resolve_window_bounds(def_data)
        channel_layers, layer_name_to_channel = _select_layer_map(context, selected_layers)
        bounds, x_min, y_min = _resolve_raster_bounds(raster_bounds, diearea_bounds)
        resolved_resolution = _resolve_pixel_resolution(bounds, target_size, pixel_resolution)
        instance_pin_to_net = _build_instance_pin_to_net(def_data, include_supply_nets=include_supply_nets)
        supply_use_to_net = _build_supply_use_to_net(def_data, include_supply_nets=include_supply_nets)

    rect_entries: List[Tuple[str, str, int, int, int, int, int, np.uint8]] = []
    real_net_names: set[str] = set()
    synthetic_names: set[str] = set()
    total_segments = 0
    total_endpoint_extensions = 0
    touch_rects_by_layer: Dict[str, List[Tuple[Tuple[float, float, float, float], str]]] = {}

    with record_function("lefdef.prepare.route_rects"):
        for net, is_special in _iter_routed_nets(def_data):
            net_name = _normalize_net_name(net.name)
            if not _include_net(net, include_supply_nets=include_supply_nets):
                continue
            if not net.routing:
                continue

            segments_by_layer: Dict[str, List[RoutingSegment]] = {}
            widths_by_layer: Dict[str, float] = {}
            for segment in net.routing:
                total_segments += max(0, len(segment.points) - 1)
                normalized_layer = _normalize_layer_name(segment.layer)
                width_um = float(segment.width) if segment.width is not None else context.layer_widths_um.get(normalized_layer)
                if width_um is None:
                    raise ValueError(
                        f"DEF route width missing for layer '{segment.layer}' in {def_path}; tech data also lacks wmin_um."
                    )
                channel = layer_name_to_channel.get(normalized_layer)
                if channel is None:
                    continue
                segments_by_layer.setdefault(normalized_layer, []).append(segment)
                widths_by_layer.setdefault(normalized_layer, width_um)
                if not np.isclose(widths_by_layer[normalized_layer], width_um):
                    raise ValueError(
                        f"Mixed route widths on net '{net_name}' layer '{segment.layer}' are not supported in the simplified path."
                    )

            rect_source_kind = RECT_SOURCE_SPECIAL_ROUTE if is_special else RECT_SOURCE_ROUTE
            for normalized_layer, layer_segments in segments_by_layer.items():
                channel = layer_name_to_channel[normalized_layer]
                rects, extension_count = _segment_to_rects(layer_segments, widths_by_layer[normalized_layer])
                total_endpoint_extensions += int(extension_count)
                for rect in rects:
                    clipped = _clip_world_rect(rect, bounds)
                    if clipped is None:
                        continue
                    touch_rects_by_layer.setdefault(normalized_layer, []).append((clipped, net_name))
                    pixels = _world_rect_to_pixels(
                        clipped,
                        x_min=float(x_min),
                        y_min=float(y_min),
                        pixel_resolution=float(resolved_resolution),
                        target_size=target_size,
                    )
                    if pixels is None:
                        continue
                    px_min, px_max, py_min, py_max = pixels
                    rect_entries.append((net_name, _DEFAULT_REAL_SOURCE_KIND, channel, px_min, px_max, py_min, py_max, rect_source_kind))
                    real_net_names.add(net_name)

    component_resolution_stats = {
        "explicit_pin": 0,
        "supply_fallback": 0,
        "routed_touch": 0,
        "pin_and_geom": 0,
        "ambiguous": 0,
        "no_net": 0,
    }
    with record_function("lefdef.prepare.component_rects"):
        for component in def_data.components:
            macro = context.macros.get(component.cell_type)
            if macro is None:
                continue
            component_rects, component_stats = _assign_component_conductors(
                component,
                macro,
                bounds=diearea_bounds,
                layer_name_to_channel=layer_name_to_channel,
                instance_pin_to_net=instance_pin_to_net,
                supply_use_to_net=supply_use_to_net,
                touch_rects_by_layer=touch_rects_by_layer,
            )
            for key, value in component_stats.items():
                component_resolution_stats[key] += int(value)
            for conductor_name, source_kind, channel, world_rect, rect_source_kind in component_rects:
                clipped = _clip_world_rect(world_rect, bounds)
                if clipped is None:
                    continue
                pixels = _world_rect_to_pixels(
                    clipped,
                    x_min=float(x_min),
                    y_min=float(y_min),
                    pixel_resolution=float(resolved_resolution),
                    target_size=target_size,
                )
                if pixels is None:
                    continue
                px_min, px_max, py_min, py_max = pixels
                rect_entries.append((conductor_name, source_kind, channel, px_min, px_max, py_min, py_max, rect_source_kind))
                if source_kind == _DEFAULT_REAL_SOURCE_KIND:
                    real_net_names.add(conductor_name)
                else:
                    synthetic_names.add(conductor_name)

    with record_function("lefdef.prepare.finalize_conductors"):
        real_names_sorted = sorted(real_net_names)
        synthetic_names_sorted = sorted(synthetic_names)
        conductor_names_sorted = list(real_names_sorted) + list(synthetic_names_sorted)
        if len(conductor_names_sorted) > INT16_MAX:
            raise ValueError(
                f"Prepared LEF+DEF conductors exceed int16 limit for {def_path}: {len(conductor_names_sorted)}"
            )

        net_name_to_gpu_id = {name: idx + 1 for idx, name in enumerate(real_names_sorted)}
        conductor_id_map = {name: idx + 1 for idx, name in enumerate(conductor_names_sorted)}

    with record_function("lefdef.prepare.pack_rects"):
        packed_rects = np.empty((len(rect_entries), RECT_COL_COUNT), dtype=np.int32)
        rect_source_kind_codes = np.empty((len(rect_entries),), dtype=np.uint8)
        for row_idx, (conductor_name, _source_kind, channel, px_min, px_max, py_min, py_max, source_kind) in enumerate(rect_entries):
            packed_rects[row_idx, RECT_COL_LAYER] = np.int32(channel)
            packed_rects[row_idx, RECT_COL_CONDUCTOR_ID] = np.int32(conductor_id_map[conductor_name])
            packed_rects[row_idx, RECT_COL_PX_MIN] = np.int32(px_min)
            packed_rects[row_idx, RECT_COL_PX_MAX] = np.int32(px_max)
            packed_rects[row_idx, RECT_COL_PY_MIN] = np.int32(py_min)
            packed_rects[row_idx, RECT_COL_PY_MAX] = np.int32(py_max)
            rect_source_kind_codes[row_idx] = np.uint8(source_kind)

        conductor_is_synthetic = np.zeros((len(conductor_names_sorted),), dtype=bool)
        conductor_source_kind_codes = np.zeros((len(conductor_names_sorted),), dtype=np.uint8)
        if synthetic_names_sorted:
            conductor_is_synthetic[len(real_names_sorted):] = True
            conductor_source_kind_codes[len(real_names_sorted):] = CONDUCTOR_SOURCE_SYNTHETIC_LEF

    prepare_ms = (perf_counter() - prep_start) * 1000.0
    return PreparedDefRasterInput(
        def_path=def_path,
        lef_path=primary_lef_path,
        lef_paths=tuple(lef_paths),
        channel_layers=list(channel_layers),
        backend="native_generic",
        target_size=int(target_size),
        pixel_resolution=float(resolved_resolution),
        window_bounds=bounds,
        conductor_names_sorted=conductor_names_sorted,
        conductor_ids_sorted=np.arange(1, len(conductor_names_sorted) + 1, dtype=np.int16),
        conductor_is_synthetic=conductor_is_synthetic,
        conductor_source_kind_codes=conductor_source_kind_codes,
        packed_rects=packed_rects,
        packed_rects_torch=None,
        rect_source_kind_codes=rect_source_kind_codes,
        net_name_to_gpu_id=net_name_to_gpu_id,
        total_segments=int(total_segments),
        total_endpoint_extensions=int(total_endpoint_extensions),
        active_rectangles=int(packed_rects.shape[0]),
        parse_ms=float(parse_ms),
        prepare_ms=float(prepare_ms),
        component_resolution_stats=component_resolution_stats,
    )


def prepare_fast_def_raster_input(
    def_path: Path | str,
    tech_path: Path | str,
    *,
    lef_path: Path | str | None = None,
    lef_files: Optional[Sequence[Path | str]] = None,
    target_size: int = DEFAULT_TARGET_SIZE,
    pixel_resolution: Optional[float] = None,
    selected_layers: Optional[Sequence[str]] = None,
    raster_bounds: Optional[Sequence[float] | np.ndarray] = None,
    include_supply_nets: bool = False,
    include_conductor_names: bool = False,
    backend: str = "auto",
) -> PreparedDefRasterInput:
    def_path = Path(def_path).resolve()
    tech_path = Path(tech_path).resolve()
    if target_size <= 0:
        raise ValueError(f"target_size must be positive, got {target_size}")
    if backend not in {"auto", "compiled", "compact"}:
        raise ValueError(f"Unsupported fast DEF prepare backend '{backend}'")

    if backend in {"auto", "compiled"} and _supports_compiled_recipe_backend(tech_path):
        return _prepare_compiled_def_raster_input(
            def_path=def_path,
            tech_path=tech_path,
            target_size=target_size,
            pixel_resolution=pixel_resolution,
            selected_layers=selected_layers,
            raster_bounds=raster_bounds,
            include_supply_nets=include_supply_nets,
            include_conductor_names=include_conductor_names,
        )

    if backend == "compiled":
        raise ValueError(
            "Compiled prepare backend is unavailable for this tech; "
            f"got tech={tech_path}"
        )

    resolved_lef_paths = _resolve_lef_paths(
        tech_path=tech_path,
        lef_path=lef_path,
        lef_files=lef_files,
    )
    compact_lef_path = _materialize_compact_backend_lef_path(resolved_lef_paths)
    return _prepare_reference_unique_def_raster_input(
        def_path=def_path,
        tech_path=tech_path,
        lef_path=compact_lef_path,
        lef_paths=resolved_lef_paths,
        target_size=target_size,
        pixel_resolution=pixel_resolution,
        selected_layers=selected_layers,
        raster_bounds=raster_bounds,
        include_supply_nets=include_supply_nets,
    )


def rasterize_def_idmaps_cpu(prepared_def: PreparedDefRasterInput) -> np.ndarray:
    return expand_fast_idmaps_cpu(prepared_def)



def rasterize_def_idmaps_cuda(prepared_def: PreparedDefRasterInput, device: torch.device) -> torch.Tensor:
    return expand_fast_idmaps_cuda(prepared_def, device=device)

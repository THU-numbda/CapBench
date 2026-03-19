#!/usr/bin/env python3
"""
Convert already-windowed DEF files into conformal-augmented CAP3D windows.

This tracked script reuses the existing SMIC28 DEF parsing helpers from the
experiments converter, while adding explicit case10-style dielectric <medium>
sections derived from explicit ITF conformal dielectric fields such as SW_T
and TW_T. ETCH is applied to conductor geometry only.
SIDE_TANGENT is parsed for reference but ignored here because this flow emits
axis-aligned CAP3D blocks only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
EXPERIMENT_HELPER_DIR = REPO_ROOT / "experiments" / "smic28_def2cap3d"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(EXPERIMENT_HELPER_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_HELPER_DIR))

from window_tools.cap3d_writer import write_cap3d

try:
    from convert_def_windows_to_cap3d import (
        DefWindow,
        RectBox,
        RunReport,
        TechStack,
        ViaTemplate,
        WindowReport,
        _build_cap3d_layer_ids,
        _default_lef_path,
        _iter_itf_blocks,
        _normalize_name,
        _parse_layers_arg,
        _resolve_input_defs,
        _resolve_via_template,
        _sanitize_net_names,
        _segment_rects,
        load_smic28_stack,
        parse_lef_via_templates,
        parse_window_def,
    )
except ImportError as exc:  # pragma: no cover - defensive import path check
    raise SystemExit(
        "Failed to import experiments SMIC28 DEF-to-CAP3D helpers. "
        f"Expected {EXPERIMENT_HELPER_DIR / 'convert_def_windows_to_cap3d.py'} to exist."
    ) from exc


EPSILON = 1e-9


@dataclass(frozen=True)
class StackInterval:
    kind: str
    name: str
    normalized_name: str
    z_bottom: float
    z_top: float
    thickness: float
    er: Optional[float] = None
    sw_t: Optional[float] = None
    tw_t: Optional[float] = None
    measured_from: Optional[str] = None
    wmin: Optional[float] = None
    etch: Optional[float] = None
    side_tangent: Optional[float] = None


@dataclass(frozen=True)
class OwnerProfile:
    owner_name: str
    z_bottom: float
    z_top: float
    thickness: float
    etch: Optional[float]
    side_tangent: Optional[float]


@dataclass(frozen=True)
class ConformalTechStack:
    base_stack: TechStack
    total_height: float
    intervals: Tuple[StackInterval, ...]
    metal_profiles: Dict[str, OwnerProfile]
    via_profiles: Dict[str, OwnerProfile]
    dielectric_intervals_by_metal: Dict[str, Tuple[StackInterval, ...]]
    dielectric_intervals_by_via: Dict[str, Tuple[StackInterval, ...]]
    beol_surrogate_sw_t: float


def _parse_optional_float(raw: Optional[str], *, absolute: bool = False) -> Optional[float]:
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return abs(value) if absolute else value


def _build_active_stack_intervals(
    *,
    itf_path: Path,
    selected_metals: Sequence[str],
) -> Tuple[Tuple[StackInterval, ...], Dict[str, OwnerProfile], float]:
    blocks = list(_iter_itf_blocks(itf_path.read_text(encoding="utf-8")))
    selected_set = {_normalize_name(layer) for layer in selected_metals}
    active_stack = [
        block
        for block in blocks
        if (
            block.kind == "DIELECTRIC"
            and not block.commented
        ) or (
            block.kind == "CONDUCTOR"
            and (not block.commented or _normalize_name(block.name) in selected_set)
        )
    ]

    intervals: List[StackInterval] = []
    metal_profiles: Dict[str, OwnerProfile] = {}
    z_cursor = 0.0

    for block in reversed(active_stack):
        z_bottom = z_cursor
        z_cursor += block.thickness
        z_top = z_cursor
        normalized_name = _normalize_name(block.name)
        interval = StackInterval(
            kind=block.kind.lower(),
            name=block.name,
            normalized_name=normalized_name,
            z_bottom=z_bottom,
            z_top=z_top,
            thickness=max(0.0, z_top - z_bottom),
            er=float(block.er) if block.er is not None else None,
            sw_t=_parse_optional_float(block.properties.get("SW_T"), absolute=True),
            tw_t=_parse_optional_float(block.properties.get("TW_T"), absolute=True),
            measured_from=block.properties.get("MEASURED_FROM"),
            wmin=float(block.wmin) if block.wmin is not None else None,
            etch=_parse_optional_float(block.properties.get("ETCH")),
            side_tangent=_parse_optional_float(block.properties.get("SIDE_TANGENT")),
        )
        intervals.append(interval)

        if interval.kind == "conductor" and normalized_name in selected_set:
            metal_profiles[normalized_name] = OwnerProfile(
                owner_name=normalized_name,
                z_bottom=z_bottom,
                z_top=z_top,
                thickness=max(0.0, z_top - z_bottom),
                etch=interval.etch,
                side_tangent=interval.side_tangent,
            )

    return tuple(intervals), metal_profiles, z_cursor

def load_smic28_conformal_stack(itf_path: Path, selected_metals: Sequence[str]) -> ConformalTechStack:
    base_stack = load_smic28_stack(itf_path, selected_metals)
    intervals, metal_profiles, total_height = _build_active_stack_intervals(
        itf_path=itf_path,
        selected_metals=selected_metals,
    )

    sorted_metals = sorted(base_stack.layer_map.items(), key=lambda item: item[1][1])
    dielectric_intervals_by_metal: Dict[str, Tuple[StackInterval, ...]] = {}
    for idx, (metal_name, (_layer_idx, _z_bottom, z_top)) in enumerate(sorted_metals):
        if idx + 1 < len(sorted_metals):
            next_metal_name = sorted_metals[idx + 1][0]
            next_boundary = base_stack.layer_map[next_metal_name][1]
        else:
            next_boundary = total_height

        metal_dielectrics = tuple(
            interval
            for interval in intervals
            if interval.kind == "dielectric"
            and interval.z_bottom >= z_top - EPSILON
            and interval.z_top <= next_boundary + EPSILON
            and interval.z_top > z_top + EPSILON
        )
        dielectric_intervals_by_metal[metal_name] = metal_dielectrics

    via_profiles: Dict[str, OwnerProfile] = {}
    dielectric_intervals_by_via: Dict[str, Tuple[StackInterval, ...]] = {}
    via_owner_map: Dict[str, Tuple[str, str]] = {}
    blocks = list(_iter_itf_blocks(itf_path.read_text(encoding="utf-8")))
    for block in blocks:
        if block.commented or block.kind != "VIA":
            continue
        via_name = _normalize_name(block.name)
        via_owner_map[via_name] = (
            _normalize_name(block.from_layer or ""),
            _normalize_name(block.to_layer or ""),
        )

    for via_name, (_layer_idx, z_bottom, z_top) in base_stack.via_map.items():
        lower_owner, upper_owner = via_owner_map.get(via_name, ("", ""))
        base_profile = metal_profiles.get(lower_owner) or metal_profiles.get(upper_owner)
        via_profiles[via_name] = OwnerProfile(
            owner_name=via_name,
            z_bottom=z_bottom,
            z_top=z_top,
            thickness=max(0.0, z_top - z_bottom),
            etch=base_profile.etch if base_profile is not None else None,
            side_tangent=base_profile.side_tangent if base_profile is not None else None,
        )
        dielectric_intervals_by_via[via_name] = tuple(
            interval
            for interval in intervals
            if interval.kind == "dielectric"
            and interval.z_top > z_bottom + EPSILON
            and interval.z_bottom < z_top - EPSILON
        )

    lowest_selected_metal_bottom = min(
        (entry[1] for entry in base_stack.layer_map.values()),
        default=float("inf"),
    )
    beol_surrogate_sw_t = max(
        (
            abs(interval.sw_t)
            for interval in intervals
            if interval.kind == "dielectric"
            and interval.sw_t is not None
            and _normalize_name(interval.measured_from or "") == "top_of_chip"
            and interval.z_top <= lowest_selected_metal_bottom + EPSILON
        ),
        default=0.0,
    )

    return ConformalTechStack(
        base_stack=base_stack,
        total_height=total_height,
        intervals=intervals,
        metal_profiles=metal_profiles,
        via_profiles=via_profiles,
        dielectric_intervals_by_metal=dielectric_intervals_by_metal,
        dielectric_intervals_by_via=dielectric_intervals_by_via,
        beol_surrogate_sw_t=beol_surrogate_sw_t,
    )


def _resolve_shell_thickness(interval: StackInterval, profile: Optional[OwnerProfile]) -> Tuple[float, float]:
    sw_t = max(0.0, float(interval.sw_t if interval.sw_t is not None else 0.0))
    tw_raw = interval.tw_t if interval.tw_t is not None else interval.sw_t
    if tw_raw is None:
        tw_raw = sw_t
    tw_t = max(0.0, float(tw_raw))
    return sw_t, tw_t


def _resolve_beol_shell_thickness(
    interval: StackInterval,
    profile: Optional[OwnerProfile],
    *,
    surrogate_sw_t: float,
) -> Tuple[float, float]:
    sw_t, tw_t = _resolve_shell_thickness(interval, profile)
    if (
        profile is not None
        and profile.owner_name.startswith("metal")
        and sw_t <= EPSILON
        and surrogate_sw_t > EPSILON
    ):
        sw_t = surrogate_sw_t
        tw_t = surrogate_sw_t
    return sw_t, tw_t


def _sort_rects(rects: Iterable[RectBox]) -> List[RectBox]:
    return sorted(
        rects,
        key=lambda rect: (rect.left, rect.bottom, rect.right, rect.top),
    )


def _append_medium_block(
    medium_sections: List[Dict[str, object]],
    family_indices: Dict[str, int],
    family_counts: DefaultDict[str, int],
    *,
    layer_name: str,
    diel: float,
    rect: RectBox,
    z_bottom: float,
    z_top: float,
) -> None:
    width = rect.right - rect.left
    height = rect.top - rect.bottom
    thickness = z_top - z_bottom
    if width <= EPSILON or height <= EPSILON or thickness <= EPSILON:
        return

    family_index = family_indices.setdefault(layer_name, len(family_indices))
    instance_index = family_counts[layer_name]
    family_counts[layer_name] += 1
    medium_sections.append(
        {
            "name": f"rect_conf_{family_index}_{instance_index}",
            "layer_name": layer_name,
            "diel": diel,
            "base": (rect.left, rect.bottom, z_bottom),
            "v1": (width, 0.0, 0.0),
            "v2": (0.0, height, 0.0),
            "hvec": (0.0, 0.0, thickness),
        }
    )


def _expand_rect(
    rect: RectBox,
    *,
    delta: float,
    bounds: Tuple[float, float, float, float],
) -> Optional[RectBox]:
    if delta <= EPSILON:
        return rect.clipped(bounds)
    return RectBox(
        left=rect.left - delta,
        right=rect.right + delta,
        bottom=rect.bottom - delta,
        top=rect.top + delta,
    ).clipped(bounds)


def _apply_etch_to_rect(
    rect: RectBox,
    *,
    etch: Optional[float],
    bounds: Tuple[float, float, float, float],
) -> Optional[RectBox]:
    if etch is None or abs(etch) <= EPSILON:
        return rect.clipped(bounds)
    return RectBox(
        left=rect.left + etch,
        right=rect.right - etch,
        bottom=rect.bottom + etch,
        top=rect.top - etch,
    ).clipped(bounds)


def _iter_ring_rects(owner_rect: RectBox, *, shell_thickness: float, bounds: Tuple[float, float, float, float]) -> Iterable[RectBox]:
    if shell_thickness <= EPSILON:
        return []
    expanded = RectBox(
        left=owner_rect.left - shell_thickness,
        right=owner_rect.right + shell_thickness,
        bottom=owner_rect.bottom - shell_thickness,
        top=owner_rect.top + shell_thickness,
    ).clipped(bounds)
    cover = owner_rect.clipped(bounds)
    if expanded is None or cover is None:
        return []

    ring_rects: List[RectBox] = []
    left_rect = RectBox(
        left=expanded.left,
        right=min(expanded.right, cover.left),
        bottom=expanded.bottom,
        top=expanded.top,
    ).clipped(bounds)
    right_rect = RectBox(
        left=max(expanded.left, cover.right),
        right=expanded.right,
        bottom=expanded.bottom,
        top=expanded.top,
    ).clipped(bounds)
    bottom_rect = RectBox(
        left=cover.left,
        right=cover.right,
        bottom=expanded.bottom,
        top=min(expanded.top, cover.bottom),
    ).clipped(bounds)
    top_rect = RectBox(
        left=cover.left,
        right=cover.right,
        bottom=max(expanded.bottom, cover.top),
        top=expanded.top,
    ).clipped(bounds)
    for rect in (left_rect, right_rect, bottom_rect, top_rect):
        if rect is not None:
            ring_rects.append(rect)
    return ring_rects


def _build_conformal_medium_sections(
    *,
    tech_stack: ConformalTechStack,
    route_rects_by_layer: Dict[str, List[RectBox]],
    via_rects_by_layer: Dict[str, List[RectBox]],
    bounds: Tuple[float, float, float, float],
    max_slice_height: float,
) -> List[Dict[str, object]]:
    medium_sections: List[Dict[str, object]] = []
    family_indices: Dict[str, int] = {}
    family_counts: DefaultDict[str, int] = defaultdict(int)

    for metal_name, intervals in sorted(
        tech_stack.dielectric_intervals_by_metal.items(),
        key=lambda item: tech_stack.base_stack.layer_map[item[0]][1],
    ):
        owner_rects = _sort_rects(route_rects_by_layer.get(metal_name, []))
        if not owner_rects:
            continue
        profile = tech_stack.metal_profiles.get(metal_name)
        if profile is None:
            continue
        for interval in intervals:
            if interval.thickness <= EPSILON or interval.er is None:
                continue
            sw_t, tw_t = _resolve_beol_shell_thickness(
                interval,
                profile,
                surrogate_sw_t=tech_stack.beol_surrogate_sw_t,
            )
            if max(sw_t, tw_t) <= EPSILON:
                continue
            layer_name = f"{interval.name}_{metal_name}"
            for owner_rect in owner_rects:
                shell_thickness = max(sw_t, tw_t)
                outer_rect = _expand_rect(
                    owner_rect,
                    delta=shell_thickness,
                    bounds=bounds,
                )
                if outer_rect is None:
                    continue
                _append_medium_block(
                    medium_sections,
                    family_indices,
                    family_counts,
                    layer_name=layer_name,
                    diel=float(interval.er),
                    rect=outer_rect,
                    z_bottom=interval.z_bottom - profile.thickness,
                    z_top=interval.z_top - profile.thickness,
                )

    for via_name, intervals in sorted(
        tech_stack.dielectric_intervals_by_via.items(),
        key=lambda item: tech_stack.base_stack.via_map[item[0]][1],
    ):
        owner_rects = _sort_rects(via_rects_by_layer.get(via_name, []))
        if not owner_rects:
            continue
        profile = tech_stack.via_profiles.get(via_name)
        via_z_bottom = tech_stack.base_stack.via_map[via_name][1]
        via_z_top = tech_stack.base_stack.via_map[via_name][2]
        for interval in intervals:
            overlap_bottom = max(interval.z_bottom, via_z_bottom)
            overlap_top = min(interval.z_top, via_z_top)
            if overlap_top - overlap_bottom <= EPSILON or interval.er is None:
                continue
            sw_t, tw_t = _resolve_shell_thickness(interval, profile)
            if max(sw_t, tw_t) <= EPSILON:
                continue
            layer_name = f"{interval.name}_{via_name}"
            for owner_rect in owner_rects:
                shell_thickness = max(sw_t, tw_t)
                outer_rect = _expand_rect(
                    owner_rect,
                    delta=shell_thickness,
                    bounds=bounds,
                )
                if outer_rect is None:
                    continue
                _append_medium_block(
                    medium_sections,
                    family_indices,
                    family_counts,
                    layer_name=layer_name,
                    diel=float(interval.er),
                    rect=outer_rect,
                    z_bottom=overlap_bottom,
                    z_top=overlap_top,
                )

    return medium_sections


def convert_def_window_to_cap3d_conformal(
    def_window: DefWindow,
    *,
    tech_stack: ConformalTechStack,
    output_path: Path,
    margin_factor: float,
    max_slice_height: float,
) -> WindowReport:
    report = WindowReport(def_path=str(def_window.path), cap3d_path=str(output_path))
    report.input_nets = len(def_window.nets)

    bounds = def_window.diearea
    per_net_shapes: DefaultDict[str, List[Tuple[str, RectBox]]] = defaultdict(list)
    route_rects_by_layer: DefaultDict[str, List[RectBox]] = defaultdict(list)
    via_rects_by_layer: DefaultDict[str, List[RectBox]] = defaultdict(list)
    sanitized_names = _sanitize_net_names(net.name for net in def_window.nets)
    block_count = 0

    for net in def_window.nets:
        safe_name = sanitized_names[net.name]
        supported_shape_count_before = len(per_net_shapes[safe_name])

        for segment in net.segments:
            normalized_layer = _normalize_name(segment.layer)
            if normalized_layer not in tech_stack.base_stack.layer_map:
                report.dropped_unsupported_layers += 1
                report.warnings.append(
                    f"{def_window.path.name}: skipped unsupported layer '{segment.layer}' on net '{net.name}'"
                )
                continue
            width_um = segment.width_um
            if width_um is None:
                width_um = tech_stack.base_stack.metal_widths.get(normalized_layer)
            if width_um is None:
                report.dropped_unsupported_layers += 1
                report.warnings.append(
                    f"{def_window.path.name}: missing width for layer '{segment.layer}' on net '{net.name}'"
                )
                continue

            for rect in _segment_rects(segment, width_um):
                clipped = _apply_etch_to_rect(
                    rect,
                    etch=(
                        tech_stack.metal_profiles.get(normalized_layer).etch
                        if normalized_layer in tech_stack.metal_profiles
                        else None
                    ),
                    bounds=bounds,
                )
                if clipped is None:
                    continue
                per_net_shapes[safe_name].append((normalized_layer, clipped))
                route_rects_by_layer[normalized_layer].append(clipped)
                block_count += 1

        for via in net.vias:
            template = _resolve_via_template(
                via.name,
                via_templates=def_window.via_templates,
                tech_stack=tech_stack.base_stack,
            )
            if template is None:
                report.dropped_unresolved_vias += 1
                report.warnings.append(
                    f"{def_window.path.name}: unresolved via '{via.name}' on net '{net.name}'"
                )
                continue
            canonical_via = _normalize_name(template.canonical_via)
            if canonical_via not in tech_stack.base_stack.via_map:
                report.dropped_unsupported_vias += 1
                report.warnings.append(
                    f"{def_window.path.name}: skipped unsupported via '{via.name}' ({template.canonical_via}) on net '{net.name}'"
                )
                continue

            for cut_rect in template.cut_rects:
                placed = cut_rect.shifted(via.x, via.y).clipped(bounds)
                if placed is None:
                    continue
                per_net_shapes[safe_name].append((canonical_via, placed))
                via_rects_by_layer[canonical_via].append(placed)
                block_count += 1

        if len(per_net_shapes[safe_name]) == supported_shape_count_before:
            report.nets_with_no_supported_geometry += 1

    filtered_shapes = {
        net_name: shapes
        for net_name, shapes in per_net_shapes.items()
        if shapes
    }
    report.output_nets = len(filtered_shapes)
    report.blocks_written = block_count

    medium_sections = _build_conformal_medium_sections(
        tech_stack=tech_stack,
        route_rects_by_layer=route_rects_by_layer,
        via_rects_by_layer=via_rects_by_layer,
        bounds=bounds,
        max_slice_height=max_slice_height,
    )
    setattr(report, "medium_blocks_written", len(medium_sections))

    layer_ids = _build_cap3d_layer_ids(tech_stack.base_stack.layer_map, tech_stack.base_stack.via_map)
    write_cap3d(
        str(output_path),
        x_min=bounds[0],
        y_min=bounds[1],
        x_max=bounds[2],
        y_max=bounds[3],
        dbu=1.0,
        margin_factor=margin_factor,
        dielectric_stack=tech_stack.base_stack.dielectric_stack,
        layer_map=tech_stack.base_stack.layer_map,
        via_map=tech_stack.base_stack.via_map,
        cap3d_layer_ids=layer_ids,
        net_shapes=filtered_shapes,
        medium_sections=medium_sections,
    )
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert already-windowed DEF files into conformal-augmented CAP3D windows "
            "using the SMIC28 dielectric stack and extra ITF geometry hints."
        )
    )
    parser.add_argument("--def-glob", type=str, default=None, help="Glob, relative to the repo root, for input DEF windows.")
    parser.add_argument("--def-dir", type=Path, default=None, help="Directory containing input DEF windows.")
    parser.add_argument("--itf", type=Path, default=REPO_ROOT / "smic28.itf", help="Path to the SMIC28 ITF.")
    parser.add_argument("--lef", type=Path, default=_default_lef_path(), help="Optional Nangate45 LEF for via-template fallback.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for generated CAP3D files.")
    parser.add_argument("--report-json", type=Path, default=None, help="Optional JSON path for a batch conversion report.")
    parser.add_argument("--margin-factor", type=float, default=1.1, help="Margin factor passed through to the CAP3D writer.")
    parser.add_argument(
        "--strict-unsupported-layers",
        action="store_true",
        help="Fail the run if unsupported layers, unsupported vias, or unresolved vias are encountered.",
    )
    parser.add_argument(
        "--layers",
        type=str,
        default="metal1,metal2,metal3,metal4,metal5,metal6,metal7,metal8,metal9,metal10",
        help="Comma-separated list of supported metal layers.",
    )
    parser.add_argument(
        "--max-slice-height",
        type=float,
        default=0.004,
        help="Deprecated; conformal dielectric z-slicing is disabled.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_defs = _resolve_input_defs(args.def_glob, args.def_dir)
    selected_layers = _parse_layers_arg(args.layers)
    tech_stack = load_smic28_conformal_stack(args.itf, selected_layers)

    lef_vias: Dict[str, ViaTemplate] = {}
    if args.lef is not None:
        if not args.lef.exists():
            raise FileNotFoundError(f"LEF file not found: {args.lef}")
        lef_vias = parse_lef_via_templates(args.lef)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    run_report = RunReport()
    total_medium_blocks = 0

    for def_path in input_defs:
        def_window = parse_window_def(def_path, lef_via_templates=lef_vias)
        output_path = args.out_dir / f"{def_path.stem}.cap3d"
        report = convert_def_window_to_cap3d_conformal(
            def_window,
            tech_stack=tech_stack,
            output_path=output_path,
            margin_factor=args.margin_factor,
            max_slice_height=args.max_slice_height,
        )
        medium_block_count = int(getattr(report, "medium_blocks_written", 0))
        total_medium_blocks += medium_block_count
        run_report.windows_processed += 1
        run_report.total_blocks_written += report.blocks_written
        run_report.dropped_unsupported_layers += report.dropped_unsupported_layers
        run_report.dropped_unsupported_vias += report.dropped_unsupported_vias
        run_report.dropped_unresolved_vias += report.dropped_unresolved_vias
        run_report.windows.append(report)

        if args.strict_unsupported_layers:
            strict_failures = (
                report.dropped_unsupported_layers
                + report.dropped_unsupported_vias
                + report.dropped_unresolved_vias
            )
            if strict_failures:
                try:
                    output_path.unlink()
                except FileNotFoundError:
                    pass
                raise RuntimeError(
                    f"Strict mode failed for {def_path.name}: "
                    f"unsupported_layers={report.dropped_unsupported_layers}, "
                    f"unsupported_vias={report.dropped_unsupported_vias}, "
                    f"unresolved_vias={report.dropped_unresolved_vias}"
                )

        print(
            f"[ok] {def_path.name} -> {output_path.name} "
            f"(nets {report.output_nets}/{report.input_nets}, "
            f"conductor blocks {report.blocks_written}, "
            f"medium blocks {medium_block_count}, "
            f"drop layers {report.dropped_unsupported_layers}, "
            f"drop vias {report.dropped_unsupported_vias}, "
            f"unresolved vias {report.dropped_unresolved_vias})"
        )

    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(
                {
                    "windows_processed": run_report.windows_processed,
                    "total_blocks_written": run_report.total_blocks_written,
                    "total_medium_blocks": total_medium_blocks,
                    "dropped_unsupported_layers": run_report.dropped_unsupported_layers,
                    "dropped_unsupported_vias": run_report.dropped_unsupported_vias,
                    "dropped_unresolved_vias": run_report.dropped_unresolved_vias,
                    "windows": [
                        {
                            "def_path": report.def_path,
                            "cap3d_path": report.cap3d_path,
                            "input_nets": report.input_nets,
                            "output_nets": report.output_nets,
                            "blocks_written": report.blocks_written,
                            "medium_blocks_written": int(getattr(report, "medium_blocks_written", 0)),
                            "dropped_unsupported_layers": report.dropped_unsupported_layers,
                            "dropped_unsupported_vias": report.dropped_unsupported_vias,
                            "dropped_unresolved_vias": report.dropped_unresolved_vias,
                            "nets_with_no_supported_geometry": report.nets_with_no_supported_geometry,
                            "warnings": report.warnings,
                        }
                        for report in run_report.windows
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    print(
        f"[summary] windows={run_report.windows_processed} "
        f"blocks={run_report.total_blocks_written} "
        f"medium_blocks={total_medium_blocks} "
        f"dropped_layers={run_report.dropped_unsupported_layers} "
        f"dropped_vias={run_report.dropped_unsupported_vias} "
        f"unresolved_vias={run_report.dropped_unresolved_vias}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

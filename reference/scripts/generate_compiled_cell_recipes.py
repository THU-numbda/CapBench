#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass(frozen=True)
class LefRect:
    layer: str
    x0: float
    y0: float
    x1: float
    y1: float
    pin_name: str = ""
    pin_use: str = ""
    is_obs: bool = False


@dataclass(frozen=True)
class RectRecord:
    layer: str
    x0: float
    y0: float
    x1: float
    y1: float
    pin_name: str = ""
    pin_use: str = ""
    is_obs: bool = False


def _normalize_layer_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _parse_lef_macros(lef_path: Path) -> Dict[str, "LefMacroLike"]:
    macros: Dict[str, LefMacroLike] = {}
    current_macro_name = ""
    size_x = 0.0
    size_y = 0.0
    pin_rects: List[LefRect] = []
    obs_rects: List[LefRect] = []
    current_pin_name = ""
    current_pin_use = ""
    current_layer = ""
    in_port = False
    in_obs = False

    for raw_line in lef_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if not current_macro_name:
            if line.startswith("MACRO "):
                current_macro_name = line.split(None, 1)[1].strip()
                size_x = 0.0
                size_y = 0.0
                pin_rects = []
                obs_rects = []
                current_pin_name = ""
                current_pin_use = ""
                current_layer = ""
                in_port = False
                in_obs = False
            continue

        if line.startswith("SIZE "):
            match = re.match(r"SIZE\s+([^\s]+)\s+BY\s+([^\s;]+)", line)
            if match:
                size_x = float(match.group(1))
                size_y = float(match.group(2))
            continue

        if line.startswith("PIN "):
            current_pin_name = line.split(None, 1)[1].strip()
            current_pin_use = ""
            current_layer = ""
            in_port = False
            continue

        if line == "OBS":
            in_obs = True
            current_layer = ""
            in_port = False
            continue

        if line == "PORT":
            in_port = True
            continue

        if line == "END":
            if in_port:
                in_port = False
            elif in_obs:
                in_obs = False
            current_layer = ""
            continue

        if line.startswith("END "):
            end_name = line.split(None, 1)[1].strip()
            if current_pin_name and end_name == current_pin_name:
                current_pin_name = ""
                current_pin_use = ""
                current_layer = ""
                in_port = False
                continue
            if end_name == current_macro_name:
                macros[current_macro_name] = LefMacroLike(
                    name=current_macro_name,
                    size_x=size_x,
                    size_y=size_y,
                    pin_rects=tuple(pin_rects),
                    obs_rects=tuple(obs_rects),
                )
                current_macro_name = ""
                current_pin_name = ""
                current_pin_use = ""
                current_layer = ""
                in_port = False
                in_obs = False
            continue

        if current_pin_name and line.startswith("USE "):
            current_pin_use = line.split(None, 1)[1].split(";", 1)[0].strip()
            continue

        if line.startswith("LAYER "):
            current_layer = line.split(None, 1)[1].split(";", 1)[0].strip()
            continue

        if line.startswith("RECT "):
            match = re.match(r"RECT\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s;]+)", line)
            if not match or not current_layer:
                continue
            rect = LefRect(
                layer=current_layer,
                x0=float(match.group(1)),
                y0=float(match.group(2)),
                x1=float(match.group(3)),
                y1=float(match.group(4)),
                pin_name=current_pin_name,
                pin_use=current_pin_use,
                is_obs=in_obs,
            )
            if in_obs:
                obs_rects.append(rect)
            elif current_pin_name:
                pin_rects.append(rect)
    return macros


def _load_metal_layers_from_tech_yaml(tech_path: Path) -> List[str]:
    lines = tech_path.read_text(encoding="utf-8").splitlines()
    metal_layers: List[str] = []
    in_layers = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("layers:") or line.startswith("stack:"):
            in_layers = True
            continue
        if in_layers and not raw_line.startswith("  -"):
            break
        if in_layers:
            match = re.search(r"name:\s*([A-Za-z0-9_]+).*type:\s*metal", line)
            if match:
                metal_layers.append(match.group(1))
    if not metal_layers:
        raise RuntimeError(f"Could not resolve metal layers from tech file {tech_path}")
    return metal_layers


@dataclass(frozen=True)
class LefMacroLike:
    name: str
    size_x: float
    size_y: float
    pin_rects: Tuple[LefRect, ...]
    obs_rects: Tuple[LefRect, ...]


def _camelize(value: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", value)
    if not tokens:
        return "Unnamed"
    out = "".join(token[:1].upper() + token[1:] for token in tokens)
    if out[0].isdigit():
        out = f"_{out}"
    return out


def _format_float(value: float) -> str:
    return f"{float(value):.12g}"


def _rects_touch(a: RectRecord, b: RectRecord) -> bool:
    if a.layer != b.layer:
        return False
    return not (a.x1 < b.x0 or b.x1 < a.x0 or a.y1 < b.y0 or b.y1 < a.y0)


def _connected_components(rects: Sequence[RectRecord]) -> List[List[RectRecord]]:
    if not rects:
        return []
    parent = list(range(len(rects)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if _rects_touch(rects[i], rects[j]):
                union(i, j)

    groups: Dict[int, List[RectRecord]] = {}
    for idx, rect in enumerate(rects):
        groups.setdefault(find(idx), []).append(rect)
    return list(groups.values())


def _filter_rects(rects: Iterable[LefRect], allowed_layers: set[str]) -> List[RectRecord]:
    filtered: List[RectRecord] = []
    for rect in rects:
        layer = _normalize_layer_name(rect.layer)
        if layer not in allowed_layers:
            continue
        x0 = min(float(rect.x0), float(rect.x1))
        x1 = max(float(rect.x0), float(rect.x1))
        y0 = min(float(rect.y0), float(rect.y1))
        y1 = max(float(rect.y0), float(rect.y1))
        filtered.append(
            RectRecord(
                layer=layer,
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                pin_name=(rect.pin_name or "").strip(),
                pin_use=(rect.pin_use or "").strip(),
                is_obs=bool(rect.is_obs),
            )
        )
    return filtered


def _emit_rect_array(name: str, rects: Sequence[RectRecord]) -> List[str]:
    lines = [f"inline constexpr RectSpec {name}[] = {{"]
    for rect in rects:
        obs_suffix = ", true" if rect.is_obs else ""
        lines.append(
            f'    {{"{rect.layer}", {_format_float(rect.x0)}, {_format_float(rect.y0)}, '
            f"{_format_float(rect.x1)}, {_format_float(rect.y1)}{obs_suffix}}},"
        )
    lines.append("};")
    lines.append("")
    return lines


def build_header_text(
    *,
    lef_path: Path,
    tech_path: Path,
    prefix: str,
    array_name: str,
) -> str:
    macros = _parse_lef_macros(lef_path)
    metal_layers = _load_metal_layers_from_tech_yaml(tech_path)
    allowed_layers = {_normalize_layer_name(layer) for layer in metal_layers}
    prefix_ident = _camelize(prefix)

    lines = [
        "#pragma once",
        "",
        f'// Generated from {lef_path.relative_to(REPO_ROOT)}.',
        "",
        "namespace capbench_compiled_recipes {",
        "",
    ]

    macro_specs: List[Tuple[str, str, float, float]] = []
    for macro_name in sorted(macros):
        macro = macros[macro_name]
        macro_ident = f"{prefix_ident}{_camelize(macro_name)}"
        groups: List[Tuple[str, str, str]] = []

        pin_groups: Dict[Tuple[str, str], List[RectRecord]] = {}
        for rect in _filter_rects(macro.pin_rects, allowed_layers):
            use_upper = rect.pin_use.upper()
            if use_upper in {"POWER", "GROUND"}:
                key = ("supply", use_upper)
            else:
                pin_name = rect.pin_name
                if not pin_name:
                    continue
                key = ("pin", pin_name)
            pin_groups.setdefault(key, []).append(rect)

        for (group_kind, binding_name), rects in sorted(pin_groups.items()):
            suffix = f"{group_kind.title()}{_camelize(binding_name)}"
            rect_array_name = f"k{macro_ident}{suffix}"
            lines.extend(_emit_rect_array(rect_array_name, rects))
            binding_kind = "kSupplyNet" if group_kind == "supply" else "kPinNet"
            groups.append((binding_kind, binding_name, rect_array_name))

        obs_components = _connected_components(_filter_rects(macro.obs_rects, allowed_layers))
        for obs_idx, rects in enumerate(obs_components):
            rect_array_name = f"k{macro_ident}ObsGroup{obs_idx}"
            lines.extend(_emit_rect_array(rect_array_name, rects))
            groups.append(("kSyntheticNet", f"OBS{obs_idx}", rect_array_name))

        group_array_name = f"k{macro_ident}Groups"
        lines.append(f"inline constexpr GroupSpec {group_array_name}[] = {{")
        for binding_kind, binding_name, rect_array_name in groups:
            lines.append(
                f'    {{BindingKind::{binding_kind}, "{binding_name}", {rect_array_name}, std::size({rect_array_name})}},'
            )
        lines.append("};")
        lines.append("")

        macro_specs.append((macro_name, group_array_name, float(macro.size_x), float(macro.size_y)))

    lines.append(f"inline constexpr MacroSpec {array_name}[] = {{")
    for macro_name, group_array_name, size_x, size_y in macro_specs:
        lines.append(
            f'    {{"{macro_name}", {_format_float(size_x)}, {_format_float(size_y)}, '
            f"{group_array_name}, std::size({group_array_name})}},"
        )
    lines.append("};")
    lines.append("")
    lines.append("}  // namespace capbench_compiled_recipes")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate static compiled cell recipe headers from LEF abstracts.")
    parser.add_argument("--lef", required=True, help="Input LEF file")
    parser.add_argument("--tech", required=True, help="Tech YAML file used to select metal layers")
    parser.add_argument("--output", required=True, help="Output header path")
    parser.add_argument("--prefix", required=True, help="Identifier prefix, e.g. Sky130hd")
    parser.add_argument("--array-name", required=True, help="Final MacroSpec array name")
    args = parser.parse_args()

    lef_path = Path(args.lef).resolve()
    tech_path = Path(args.tech).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header_text = build_header_text(
        lef_path=lef_path,
        tech_path=tech_path,
        prefix=args.prefix,
        array_name=args.array_name,
    )
    output_path.write_text(header_text, encoding="utf-8")


if __name__ == "__main__":
    main()

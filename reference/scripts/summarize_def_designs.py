#!/usr/bin/env python3
"""Summarize DEF design statistics in a compact markdown table."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from window_tools.def_parser import DefData, parse_def


@dataclass(frozen=True)
class DesignMetrics:
    design: str
    process: str
    macros: int
    std_cells: int
    nets: int
    core_width_um: float
    core_height_um: float


def parse_args() -> argparse.Namespace:
    """Return CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Scan DEF files and print a markdown/aligned table with "
            "macro count, std cell count, net count, and core area."
        )
    )
    parser.add_argument(
        "--def-dir",
        type=Path,
        default=Path("designs/def"),
        help="Directory containing .def designs (default: designs/def)",
    )
    parser.add_argument(
        "--tech-dir",
        type=Path,
        default=Path("designs/tech"),
        help="Directory containing <process>.lef tech files (default: designs/tech)",
    )
    return parser.parse_args()


def infer_process_name(def_path: Path) -> str:
    """Infer the process node name from a DEF filename."""
    parts = def_path.stem.split(".")
    if len(parts) < 2:
        raise ValueError(
            f"DEF filename '{def_path.name}' does not encode a process suffix (expected <design>.<process>.def)"
        )
    return parts[-1]


def load_lef_macro_classes(process: str, tech_dir: Path) -> Dict[str, str]:
    """Parse the LEF file for a process node and cache macro classes."""
    lef_path = tech_dir / f"{process}.lef"
    if not lef_path.is_file():
        raise FileNotFoundError(f"Missing LEF file for process '{process}': {lef_path}")

    macro_classes: Dict[str, str] = {}
    current_macro: str | None = None
    current_class: str | None = None

    with lef_path.open() as lef_file:
        for raw_line in lef_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("MACRO "):
                current_macro = line.split()[1]
                current_class = None
                continue

            if current_macro and line.startswith("CLASS "):
                class_tokens = line[len("CLASS ") :].strip()
                if class_tokens.endswith(";"):
                    class_tokens = class_tokens[:-1].strip()
                current_class = class_tokens
                continue

            if current_macro and line.startswith("END "):
                end_name = line.split()[1]
                if end_name == current_macro:
                    macro_classes[current_macro] = current_class or ""
                    current_macro = None
                    current_class = None

    return macro_classes


def classify_components(components: Sequence, macro_classes: Dict[str, str], design_name: str) -> Tuple[int, int]:
    """Return (macros, std_cells) counts for a DEF's components."""
    macros = 0
    std_cells = 0
    unknown_cells = 0

    for component in components:
        cell_type = component.cell_type
        if not cell_type:
            std_cells += 1
            unknown_cells += 1
            continue

        class_value = macro_classes.get(cell_type)
        if class_value is None:
            std_cells += 1
            unknown_cells += 1
            continue

        if class_value.upper().startswith("CORE"):
            std_cells += 1
        else:
            macros += 1

    if unknown_cells:
        print(
            f"[warn] {design_name}: {unknown_cells} components missing LEF class entries, counted as std cells.",
            file=sys.stderr,
        )

    return macros, std_cells


def compute_core_dimensions_um(def_data: DefData) -> Tuple[float, float]:
    """Return the core width/height (die extents) in µm."""
    x1, y1, x2, y2 = def_data.diearea
    width = x2 - x1
    height = y2 - y1
    return width, height


def collect_metrics(def_files: Iterable[Path], tech_dir: Path) -> List[DesignMetrics]:
    """Collect metrics for each DEF design."""
    metrics: List[DesignMetrics] = []
    class_cache: Dict[str, Dict[str, str]] = {}

    for def_path in sorted(def_files):
        process = infer_process_name(def_path)
        if process not in class_cache:
            class_cache[process] = load_lef_macro_classes(process, tech_dir)

        data = parse_def(def_path)
        macros, std_cells = classify_components(data.components, class_cache[process], def_path.stem)
        nets = len(data.nets)
        width_um, height_um = compute_core_dimensions_um(data)

        metrics.append(
            DesignMetrics(
                design=def_path.stem,
                process=process,
                macros=macros,
                std_cells=std_cells,
                nets=nets,
                core_width_um=width_um,
                core_height_um=height_um,
            )
        )

    return metrics


def format_table(metrics: Sequence[DesignMetrics]) -> List[str]:
    """Build a markdown-friendly table with aligned columns."""
    headers = ["Design", "Process", "Macros", "Std Cells", "Nets", "Core (um x um)"]
    rows: List[List[str]] = [
        [
            m.design,
            m.process,
            f"{m.macros}",
            f"{m.std_cells}",
            f"{m.nets}",
            f"{m.core_width_um:,.3f} x {m.core_height_um:,.3f}",
        ]
        for m in metrics
    ]

    if not rows:
        return ["No DEF files found."]

    widths = [
        max(len(header), *(len(row[idx]) for row in rows))
        for idx, header in enumerate(headers)
    ]

    def fmt_row(row: Sequence[str]) -> str:
        cells = [value.ljust(widths[idx]) for idx, value in enumerate(row)]
        return "| " + " | ".join(cells) + " |"

    table_lines = [fmt_row(headers)]
    separator_cells = ["-" * width for width in widths]
    table_lines.append("|-" + "-|-".join(separator_cells) + "-|")
    for row in rows:
        table_lines.append(fmt_row(row))
    return table_lines


def main() -> None:
    args = parse_args()
    if not args.def_dir.is_dir():
        print(f"DEF directory not found: {args.def_dir}", file=sys.stderr)
        sys.exit(1)
    def_files = list(args.def_dir.glob("*.def"))
    metrics = collect_metrics(def_files, args.tech_dir)
    for line in format_table(metrics):
        print(line)


if __name__ == "__main__":
    main()

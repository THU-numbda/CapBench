#!/usr/bin/env python3
"""Summarize RWCap output statistics across one or more directories/files."""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
import re


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan RWCap .out files and report the average number of walks and runtime "
            "with standard deviation."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["datasets"],
        help=(
            "Paths to scan for RWCap outputs (files or directories). "
            "Defaults to the datasets/ tree."
        ),
    )
    parser.add_argument(
        "--pattern",
        default="*.out",
        help="Filename glob to match (default: *.out).",
    )
    return parser.parse_args()


def discover_out_files(targets: Sequence[str], pattern: str) -> List[Path]:
    files: List[Path] = []
    for target in targets:
        base = Path(target)
        if not base.exists():
            continue
        if base.is_file():
            if base.match(pattern):
                files.append(base)
            continue
        files.extend(sorted(base.rglob(pattern)))
    return files


def parse_rwcap_file(path: Path) -> tuple[Optional[int], Optional[float]]:
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return None, None

    walks_matches = re.findall(r"RWCap has run\s+(\d+)\s+walks", text)
    walks = int(walks_matches[-1]) if walks_matches else None

    elapsed_matches = re.findall(r"Elapsed time:\s*([\d.]+)sec", text)
    elapsed = float(elapsed_matches[-1]) if elapsed_matches else None
    return walks, elapsed


def compute_stats(values: Iterable[Optional[float]]) -> tuple[Optional[float], Optional[float], int]:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None, None, 0
    mean_val = statistics.mean(clean)
    std_val = statistics.stdev(clean) if len(clean) > 1 else 0.0
    return mean_val, std_val, len(clean)


def _abbreviate(value: float) -> str:
    abs_val = abs(value)
    for factor, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs_val >= factor:
            return f"{value / factor:.1f}{suffix}"
    return f"{value:,.0f}"


def format_stat(mean: Optional[float], std: Optional[float], unit: str = "", precision: int = 2) -> str:
    if mean is None:
        return "n/a"
    std = std or 0.0
    if unit == "walks":
        mean_str = _abbreviate(mean)
        std_str = _abbreviate(std)
        return f"{mean_str} ± {std_str}"
    if unit == "seconds":
        mean_str = f"{mean:.{precision}f}s"
        std_str = f"{std:.{precision}f}s"
        return f"{mean_str} ± {std_str}"
    return f"{mean:.{precision}f} ± {std:.{precision}f}"


def build_table(rows: List[List[str]]) -> str:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]

    def fmt(row: Sequence[str]) -> str:
        return "| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |"

    separator = "|-" + "-|-".join("-" * w for w in widths) + "-|"
    lines = [fmt(rows[0]), separator]
    lines.extend(fmt(row) for row in rows[1:])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    targets = args.paths or ["datasets"]
    files = discover_out_files(targets, args.pattern)
    if not files:
        print("No RWCap .out files found in the specified paths.", file=sys.stderr)
        sys.exit(1)

    walk_values: List[Optional[int]] = []
    elapsed_values: List[Optional[float]] = []
    for path in files:
        walks, elapsed = parse_rwcap_file(path)
        walk_values.append(walks)
        elapsed_values.append(elapsed)

    walk_mean, walk_std, walk_count = compute_stats(walk_values)
    elapsed_mean, elapsed_std, elapsed_count = compute_stats(elapsed_values)

    rows = [
        ["Metric", "Value", "Samples"],
        ["Total files scanned", f"{len(files)}", ""],
        ["Walks (total)", format_stat(walk_mean, walk_std, unit="walks"), f"{walk_count}"],
        ["Elapsed time", format_stat(elapsed_mean, elapsed_std, unit="seconds", precision=2), f"{elapsed_count}"],
    ]

    print(build_table(rows))


if __name__ == "__main__":
    main()

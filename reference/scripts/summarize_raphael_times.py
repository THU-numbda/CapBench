#!/usr/bin/env python3
"""Summarize Raphael runtimes by parsing all_nets.dspf files."""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
import re

RUNTIME_RE = re.compile(r"\*\|Raphael runtime:\s*([\d.]+)\s*s")
DSPF_RE = re.compile(r"\*\|DSPF FILE:.*?/W(\d+)_Net")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Raphael all_nets.dspf files and report per-window runtime stats."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["datasets"],
        help="Directories or files to scan (default: datasets/ tree).",
    )
    parser.add_argument(
        "--pattern",
        default="all_nets.dspf",
        help="Filename glob to match (default: all_nets.dspf).",
    )
    return parser.parse_args()


def discover_files(targets: Sequence[str], pattern: str) -> List[Path]:
    files: List[Path] = []
    for target in targets:
        base = Path(target)
        if not base.exists():
            continue
        if base.is_file() and base.match(pattern):
            files.append(base)
            continue
        files.extend(sorted(base.rglob(pattern)))
    return files


def parse_dspf(path: Path) -> Tuple[str, float]:
    total = 0.0
    current_window = path.parent.name  # fallback
    with path.open(errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            match = DSPF_RE.search(line)
            if match:
                current_window = f"W{match.group(1)}"
                continue
            match = RUNTIME_RE.search(line)
            if match:
                total += float(match.group(1))
    return current_window, total


def compute_stats(values: List[float]) -> Tuple[Optional[float], Optional[float]]:
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], 0.0
    return statistics.mean(values), statistics.stdev(values)


def build_table(rows: List[List[str]]) -> str:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]

    def fmt(row: List[str]) -> str:
        return "| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |"

    separator = "|-" + "-|-".join("-" * w for w in widths) + "-|"
    table_lines = [fmt(rows[0]), separator]
    table_lines.extend(fmt(row) for row in rows[1:])
    return "\n".join(table_lines)


def format_seconds(value: Optional[float], unit: str = "seconds") -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}s"


def find_out_raphael_dirs(base_paths: Sequence[str]) -> List[Path]:
    """Find all out_raphael directories in the given paths."""
    out_dirs = []
    for base_path in base_paths:
        path = Path(base_path)
        if not path.exists():
            continue
        # Find all directories named out_raphael
        for out_dir in path.rglob("out_raphael"):
            if out_dir.is_dir():
                out_dirs.append(out_dir)
    return sorted(out_dirs)


def main() -> None:
    args = parse_args()

    # Find all out_raphael directories
    out_raphael_dirs = find_out_raphael_dirs(args.paths)
    if not out_raphael_dirs:
        print("No out_raphael directories found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(out_raphael_dirs)} out_raphael directories:")
    print()

    # Process each out_raphael directory separately
    for out_dir in out_raphael_dirs:
        print(f"=== {out_dir} ===")

        # Find all_nets.dspf files in this out_raphael directory
        dspf_files = list(out_dir.rglob(args.pattern))
        if not dspf_files:
            print("  No all_nets.dspf files found in this directory.\n")
            continue

        # Parse DSPF files
        window_times: Dict[str, float] = {}
        for path in dspf_files:
            window, runtime = parse_dspf(path)
            window_times[window] = runtime

        # Compute statistics
        runtimes = list(window_times.values())
        mean_time, std_time = compute_stats(runtimes)

        # Build table for this directory
        # Extract technology and size category from path
        parts = out_dir.parts
        tech_node = "unknown"
        size_category = "unknown"

        for i, part in enumerate(parts):
            if part in ["asap7", "nangate45", "sky130hd"]:
                tech_node = part
                # Look for size category in the next few parts
                for j in range(i + 1, min(i + 3, len(parts))):
                    if parts[j] in ["small", "medium", "large"]:
                        size_category = parts[j]
                        break
                break

        rows = [
            ["Metric", "Value"],
            ["Technology", tech_node],
            ["Size category", size_category],
            ["DSPF files scanned", f"{len(dspf_files)}"],
            ["Windows found", f"{len(window_times)}"],
            ["Total runtime", f"{sum(runtimes):.2f}s"],
            ["Average runtime", f"{format_seconds(mean_time)} ± {format_seconds(std_time)}"],
        ]

        print(build_table(rows))
        print()


if __name__ == "__main__":
    main()

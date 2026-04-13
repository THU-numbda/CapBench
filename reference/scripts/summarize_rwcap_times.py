#!/usr/bin/env python3
"""Summarize RWCap runtimes by parsing out_rwcap/*.out files."""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
import re

PREP_COST_RE = re.compile(r"Preparation cost:\s*([\d.]+)sec")
INIT_COST_RE = re.compile(r"Task .*? initialization cost\s*([\d.]+)sec")
WALK_COST_RE = re.compile(r"Task .*? random walk cost\s*([\d.]+)sec")
WALK_COUNT_RE = re.compile(r"RWCap has run (\d+) walks")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan RWCap *.out files and report per-window runtime stats."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["datasets"],
        help="Directories or files to scan (default: datasets/ tree).",
    )
    parser.add_argument(
        "--pattern",
        default="*.out",
        help="Filename glob to match (default: *.out).",
    )
    return parser.parse_args()


def discover_out_rwcap_dirs(targets: Sequence[str]) -> List[Path]:
    """Find all out_rwcap directories in the given paths."""
    out_dirs = []
    for target in targets:
        base = Path(target)
        if not base.exists():
            continue

        # Find all directories named out_rwcap
        for out_dir in base.rglob("out_rwcap"):
            if out_dir.is_dir():
                out_dirs.append(out_dir)
    return sorted(out_dirs)


def parse_rwcap_file(path: Path) -> Tuple[str, Dict[str, float]]:
    """Parse a single RWCap output file and extract timing information."""
    prep_cost = 0.0
    total_init_cost = 0.0
    total_walk_cost = 0.0
    total_walks = 0

    try:
        with path.open('r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

            # Extract preparation cost
            prep_match = PREP_COST_RE.search(content)
            if prep_match:
                prep_cost = float(prep_match.group(1))

            # Extract all initialization costs
            for match in INIT_COST_RE.finditer(content):
                total_init_cost += float(match.group(1))

            # Extract all random walk costs
            for match in WALK_COST_RE.finditer(content):
                total_walk_cost += float(match.group(1))

            # Extract total walk count
            walk_count_match = WALK_COUNT_RE.search(content)
            if walk_count_match:
                total_walks = int(walk_count_match.group(1))

    except Exception as e:
        print(f"Warning: Could not parse {path}: {e}", file=sys.stderr)

    # Extract window name from filename (W0.out -> W0)
    window_name = path.stem

    # Calculate total time
    total_time = prep_cost + total_init_cost + total_walk_cost

    timing_data = {
        'total_time': total_time,
        'prep_cost': prep_cost,
        'total_init_cost': total_init_cost,
        'total_walk_cost': total_walk_cost,
        'total_walks': total_walks,
        'nets_processed': len(INIT_COST_RE.findall(content)) if 'content' in locals() else 0
    }

    return window_name, timing_data


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


def format_walks(value: Optional[int]) -> str:
    if value is None:
        return "n/a"
    return f"{value:,}"


def main() -> None:
    args = parse_args()

    # Find all out_rwcap directories
    out_rwcap_dirs = discover_out_rwcap_dirs(args.paths)
    if not out_rwcap_dirs:
        print("No out_rwcap directories found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(out_rwcap_dirs)} out_rwcap directories:")
    print()

    # Process each out_rwcap directory separately
    all_results = []

    for out_dir in out_rwcap_dirs:
        print(f"=== {out_dir} ===")

        # Find all .out files in this out_rwcap directory
        out_files = list(out_dir.glob(args.pattern))
        if not out_files:
            print("  No *.out files found in this directory.\n")
            continue

        # Parse timing data from each file
        window_timings: Dict[str, Dict[str, float]] = {}
        for path in out_files:
            window, timing_data = parse_rwcap_file(path)
            window_timings[window] = timing_data

        if not window_timings:
            print("  No valid timing data found.\n")
            continue

        # Calculate aggregate statistics
        total_times = [data['total_time'] for data in window_timings.values()]
        prep_times = [data['prep_cost'] for data in window_timings.values()]
        init_times = [data['total_init_cost'] for data in window_timings.values()]
        walk_times = [data['total_walk_cost'] for data in window_timings.values()]
        total_walks = [data['total_walks'] for data in window_timings.values()]
        net_counts = [data['nets_processed'] for data in window_timings.values()]

        # Compute statistics
        total_time_mean, total_time_std = compute_stats(total_times)
        prep_time_mean, prep_time_std = compute_stats(prep_times)
        init_time_mean, init_time_std = compute_stats(init_times)
        walk_time_mean, walk_time_std = compute_stats(walk_times)

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

        # Build table for this directory
        rows = [
            ["Metric", "Value"],
            ["Technology", tech_node],
            ["Size category", size_category],
            ["Output files", f"{len(out_files)}"],
            ["Windows processed", f"{len(window_timings)}"],
            ["Total runtime", f"{format_seconds(total_time_mean)} ± {format_seconds(total_time_std)}"],
            ["Preparation time", f"{format_seconds(prep_time_mean)} ± {format_seconds(prep_time_std)}"],
            ["Initialization time", f"{format_seconds(init_time_mean)} ± {format_seconds(init_time_std)}"],
            ["Random walk time", f"{format_seconds(walk_time_mean)} ± {format_seconds(walk_time_std)}"],
            ["Total walks", format_walks(sum(total_walks))],
            ["Average walks/window", f"{sum(total_walks)//len(window_timings):,}" if window_timings else "0"],
            ["Total nets processed", format_walks(sum(net_counts))],
        ]

        print(build_table(rows))
        print()

        # Store results for summary
        all_results.append({
            'dir': out_dir,
            'tech': tech_node,
            'size': size_category,
            'windows': len(window_timings),
            'total_time_mean': total_time_mean or 0,
            'total_time_std': total_time_std or 0,
            'total_walks': sum(total_walks)
        })

    # Print overall summary if multiple directories
    if len(all_results) > 1:
        print("=" * 80)
        print("OVERALL SUMMARY")
        print("=" * 80)

        summary_rows = [
            ["Technology", "Size", "Windows", "Total Time", "Walks"],
        ]

        for result in all_results:
            summary_rows.append([
                result['tech'],
                result['size'],
                str(result['windows']),
                f"{format_seconds(result['total_time_mean'])} ± {format_seconds(result['total_time_std'])}",
                format_walks(result['total_walks'])
            ])

        print(build_table(summary_rows))


if __name__ == "__main__":
    main()
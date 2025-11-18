#!/usr/bin/env python3
"""
Comprehensive Capacitance Comparison Tool

Compares capacitance extraction tools (RWCap vs Raphael vs OpenRCX) for both self and coupling
capacitance across multiple technologies and dataset sizes.

Usage:
    python capacitance_comparison.py [--type self|coupling|all] [--tech all|nangate45|asap7|sky130hd] [--tools all|rwcap_raphael|rwcap_openrcx|raphael_openrcx]
"""

import re
import numpy as np
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from collections import defaultdict
import statistics

# SPEF parsing patterns
NAME_MAP_RE = re.compile(r'^\*(\d+)\s+(\S+)')
SELF_CAP_RE = re.compile(r'^\*(\d+)\s+(\S+)\s+([\d.e-]+)$')  # Single net pattern
COUPLING_CAP_RE = re.compile(r'^\*(\d+)\s+(\S+)\s+(\S+)\s+([\d.e-]+)$')  # Two net pattern

def parse_spef_file(spef_path: Path) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
    """
    Parse a SPEF file and extract both self and coupling capacitance values.

    Returns:
        Tuple of (self_capacitances, coupling_capacitances)
        - self_capacitances: Dict mapping net names to self-capacitance values (in Farads)
        - coupling_capacitances: Dict mapping (net1, net2) tuples to coupling capacitance values
    """
    name_map = {}  # Maps numbers to net names
    self_capacitances = {}
    coupling_capacitances = {}

    # Ensure we have an absolute path
    spef_path = Path(spef_path).absolute()

    if not spef_path.exists():
        print(f"Warning: SPEF file not found: {spef_path}")
        return {}, {}

    try:
        with open(spef_path, 'r') as f:
            in_name_map = False
            in_cap_section = False

            for line in f:
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                # Track sections
                if line == '*NAME_MAP':
                    in_name_map = True
                    continue
                elif line == '*CAP':
                    in_cap_section = True
                    in_name_map = False
                    continue
                elif line.startswith('*') and not line.startswith('*NAME_MAP'):
                    in_cap_section = False
                    in_name_map = False
                    continue

                # Parse name map entries
                if in_name_map and not line.startswith('*'):
                    parts = line.split()
                    if len(parts) >= 2:
                        number = parts[0]
                        net_name = parts[1]
                        name_map[number] = net_name

                # Parse capacitance entries (both self and coupling in *CAP section)
                elif in_cap_section and not line.startswith('*'):
                    parts = line.split()
                    if len(parts) == 3:  # Self capacitance: id net_name value
                        try:
                            # The first part might be a number or *
                            net_id = parts[0] if not parts[0].startswith('*') else parts[0][1:]
                            net_name = parts[1]
                            # If net_name is a number, look it up in name_map
                            if net_name.isdigit():
                                net_name = name_map.get(net_name, net_name)

                            capacitance = float(parts[2])
                            # Convert from PF to F
                            capacitance_f = capacitance * 1e-12
                            self_capacitances[net_name] = capacitance_f
                        except (ValueError, IndexError):
                            continue

                    elif len(parts) == 4:  # Coupling capacitance: id net1 net2 value
                        try:
                            # The first part might be a number or *
                            id_part = parts[0] if not parts[0].startswith('*') else parts[0][1:]
                            net1 = parts[1]
                            net2 = parts[2]

                            # If net names are numbers, look them up in name_map
                            if net1.isdigit():
                                net1 = name_map.get(net1, net1)
                            if net2.isdigit():
                                net2 = name_map.get(net2, net2)

                            capacitance = float(parts[3])
                            # Convert from PF to F
                            capacitance_f = capacitance * 1e-12

                            # Create ordered tuple for consistent keying
                            pair_key = tuple(sorted([net1, net2]))
                            coupling_capacitances[pair_key] = capacitance_f
                        except (ValueError, IndexError):
                            continue

    except Exception as e:
        print(f"Warning: Error parsing {spef_path}: {e}")

    return self_capacitances, coupling_capacitances

def find_common_spef_files(tool1_dir: Path, tool2_dir: Path) -> List[str]:
    """Find common SPEF files between two tool directories."""
    tool1_files = {f.stem for f in tool1_dir.glob("*.spef")}
    tool2_files = {f.stem for f in tool2_dir.glob("*.spef")}

    common_files = sorted(tool1_files.intersection(tool2_files))
    return common_files

def determine_pair_order(tool1_name: str, tool2_name: str,
                         ground_truth_tool: Optional[str]) -> Tuple[str, str, bool]:
    """
    Ensure the chosen ground-truth tool is first in the pair.

    Returns:
        Tuple of (ordered_tool1, ordered_tool2, tool1_is_ground_truth)
    """
    if ground_truth_tool is None:
        return tool1_name, tool2_name, False

    if tool1_name == ground_truth_tool:
        return tool1_name, tool2_name, True

    if tool2_name == ground_truth_tool:
        return tool2_name, tool1_name, True

    return tool1_name, tool2_name, False

def compare_self_capacitances(tool1_caps: Dict[str, float], tool2_caps: Dict[str, float],
                             tool1_name: str, tool2_name: str,
                             tool1_is_ground_truth: bool = False) -> List[Dict]:
    """Compare self-capacitance values between two tools."""
    common_nets = set(tool1_caps.keys()).intersection(set(tool2_caps.keys()))
    errors = []

    for net in common_nets:
        tool1_val = tool1_caps[net]
        tool2_val = tool2_caps[net]

        if tool1_is_ground_truth:
            reference_val = tool1_val
            comparison_val = tool2_val
        else:
            reference_val = tool2_val
            comparison_val = tool1_val

        # Absolute and relative errors
        abs_error = abs(tool1_val - tool2_val)
        denom = max(reference_val, 1e-20)
        signed_rel_error = (comparison_val - reference_val) / denom
        rel_error = abs(signed_rel_error)

        errors.append({
            'net': net,
            tool1_name.lower(): tool1_val,
            tool2_name.lower(): tool2_val,
            'abs_error': abs_error,
            'rel_error': rel_error,
            'signed_rel_error': signed_rel_error,
            'ground_cap_f': reference_val,
            'comparison_cap_f': comparison_val
        })

    return errors

def compare_coupling_capacitances(tool1_caps: Dict, tool2_caps: Dict,
                                tool1_name: str, tool2_name: str,
                                tool1_is_ground_truth: bool = False) -> List[Dict]:
    """Compare coupling capacitance values between two tools."""
    common_pairs = set(tool1_caps.keys()).intersection(set(tool2_caps.keys()))
    errors = []

    for pair in common_pairs:
        tool1_val = tool1_caps[pair]
        tool2_val = tool2_caps[pair]

        if tool1_is_ground_truth:
            reference_val = tool1_val
            comparison_val = tool2_val
        else:
            reference_val = tool2_val
            comparison_val = tool1_val

        # Absolute and relative errors
        abs_error = abs(tool1_val - tool2_val)
        denom = max(reference_val, 1e-20)
        signed_rel_error = (comparison_val - reference_val) / denom
        rel_error = abs(signed_rel_error)

        net1, net2 = pair
        errors.append({
            'pair': f"{net1} - {net2}",
            tool1_name.lower(): tool1_val,
            tool2_name.lower(): tool2_val,
            'abs_error': abs_error,
            'rel_error': rel_error,
            'signed_rel_error': signed_rel_error,
            'ground_cap_f': reference_val,
            'comparison_cap_f': comparison_val
        })

    return errors

def get_available_tools(technology: str, size: str) -> Dict[str, Path]:
    """Get available capacitance extraction tools for a dataset."""
    base_path = Path(f"datasets/{technology}/{size}")
    tools = {}

    # Check for each tool directory
    tool_dirs = {
        'RWCap': base_path / "labels_rwcap",
        'Raphael': base_path / "labels_raphael",
        'OpenRCX': base_path / "labels_openrcx"
    }

    for tool_name, tool_dir in tool_dirs.items():
        if tool_dir.exists() and tool_dir.is_dir():
            # Check if there are SPEF files
            spef_files = list(tool_dir.glob("*.spef"))
            if spef_files:
                tools[tool_name] = tool_dir

    return tools

def analyze_dataset_comparison(technology: str, size: str, comparison_type: str = 'self',
                            tools_to_compare: str = 'all',
                            ground_truth_tool: Optional[str] = None,
                            collect_errors: bool = False) -> List[Dict]:
    """Analyze capacitance comparison for a specific dataset."""

    # Get available tools
    available_tools = get_available_tools(technology, size)

    if len(available_tools) < 2:
        return []

    results = []

    # Determine which tool pairs to compare
    tool_pairs = []
    tool_names = list(available_tools.keys())

    if tools_to_compare == 'all':
        # Compare all possible pairs
        for i in range(len(tool_names)):
            for j in range(i + 1, len(tool_names)):
                tool_pairs.append((tool_names[i], tool_names[j]))
    elif tools_to_compare == 'rwcap_raphael':
        if 'RWCap' in tool_names and 'Raphael' in tool_names:
            tool_pairs.append(('RWCap', 'Raphael'))
    elif tools_to_compare == 'rwcap_openrcx':
        if 'RWCap' in tool_names and 'OpenRCX' in tool_names:
            tool_pairs.append(('RWCap', 'OpenRCX'))
    elif tools_to_compare == 'raphael_openrcx':
        if 'Raphael' in tool_names and 'OpenRCX' in tool_names:
            tool_pairs.append(('Raphael', 'OpenRCX'))
    else:
        # Default to all pairs if invalid option
        for i in range(len(tool_names)):
            for j in range(i + 1, len(tool_names)):
                tool_pairs.append((tool_names[i], tool_names[j]))

    # Analyze each tool pair
    for raw_tool1_name, raw_tool2_name in tool_pairs:
        tool1_name, tool2_name, tool1_is_ground_truth = determine_pair_order(
            raw_tool1_name, raw_tool2_name, ground_truth_tool
        )

        tool1_dir = available_tools[tool1_name]
        tool2_dir = available_tools[tool2_name]

        # Find common files
        common_files = find_common_spef_files(tool1_dir, tool2_dir)
        if not common_files:
            continue

        result = analyze_capacitance_comparison(
            tool1_dir, tool2_dir, common_files,
            tool1_name, tool2_name, technology, size, comparison_type,
            tool1_is_ground_truth=tool1_is_ground_truth,
            collect_errors=collect_errors
        )

        if result:
            result['tool1_name'] = tool1_name
            result['tool2_name'] = tool2_name
            result['tool1_is_ground_truth'] = tool1_is_ground_truth
            result['ground_truth_tool'] = tool1_name if tool1_is_ground_truth else tool2_name
            results.append(result)

    return results

def analyze_capacitance_comparison(tool1_dir: Path, tool2_dir: Path, common_files: List[str],
                                 tool1_name: str, tool2_name: str, technology: str, size: str,
                                 analysis_type: str = 'all', *,
                                 tool1_is_ground_truth: bool = False,
                                 collect_errors: bool = False) -> Dict:
    """Perform detailed capacitance comparison analysis."""

    all_self_errors = []
    all_coupling_errors = []
    files_with_self_data = 0
    files_with_coupling_data = 0
    total_self_nets = 0
    total_coupling_pairs = 0

    print(f"\n{'='*60}")
    print(f"Analyzing {technology.upper()} {size.upper()} - {analysis_type.upper()}")
    print(f"{'='*60}")
    print(f"Found {len(common_files)} common SPEF files")

    for file_name in common_files:
        tool1_file = tool1_dir / f"{file_name}.spef"
        tool2_file = tool2_dir / f"{file_name}.spef"

        # Parse both files
        tool1_self, tool1_coupling = parse_spef_file(tool1_file)
        tool2_self, tool2_coupling = parse_spef_file(tool2_file)

        # Analyze self capacitances
        if (analysis_type == 'self' or analysis_type == 'all') and tool1_self and tool2_self:
            self_errors = compare_self_capacitances(
                tool1_self, tool2_self, tool1_name, tool2_name,
                tool1_is_ground_truth=tool1_is_ground_truth
            )
            if self_errors:
                all_self_errors.extend(self_errors)
                files_with_self_data += 1
                total_self_nets += len(self_errors)

        # Analyze coupling capacitances
        if (analysis_type == 'coupling' or analysis_type == 'all') and tool1_coupling and tool2_coupling:
            coupling_errors = compare_coupling_capacitances(
                tool1_coupling, tool2_coupling, tool1_name, tool2_name,
                tool1_is_ground_truth=tool1_is_ground_truth
            )
            if coupling_errors:
                all_coupling_errors.extend(coupling_errors)
                files_with_coupling_data += 1
                total_coupling_pairs += len(coupling_errors)

    # Compile results
    result = {
        'technology': technology,
        'size': size,
        'files_analyzed': len(common_files),
        'files_with_self_data': files_with_self_data,
        'files_with_coupling_data': files_with_coupling_data,
        'total_self_nets': total_self_nets,
        'total_coupling_pairs': total_coupling_pairs,
        'tool1_is_ground_truth': tool1_is_ground_truth,
        'ground_truth_tool': tool1_name if tool1_is_ground_truth else tool2_name
    }

    # Self-capacitance statistics
    if all_self_errors:
        self_rel_errors = [e['rel_error'] for e in all_self_errors]
        self_abs_errors = [e['abs_error'] for e in all_self_errors]

        result['self_cap'] = {
            'mean_rel_error': np.mean(self_rel_errors),
            'median_rel_error': np.median(self_rel_errors),
            'std_rel_error': np.std(self_rel_errors),
            'mean_abs_error': np.mean(self_abs_errors),
            'max_rel_error': np.max(self_rel_errors),
            'min_rel_error': np.min(self_rel_errors),
            'worst_errors': sorted(all_self_errors, key=lambda x: x['rel_error'], reverse=True)[:5]
        }

        print(f"Self-capacitance results:")
        print(f"  Files with data: {files_with_self_data}/{len(common_files)}")
        print(f"  Total nets: {total_self_nets:,}")
        print(f"  Mean relative error: {result['self_cap']['mean_rel_error']:.2%}")
        print(f"  Median relative error: {result['self_cap']['median_rel_error']:.2%}")
        print(f"  Standard deviation: {result['self_cap']['std_rel_error']:.2%}")

    # Coupling-capacitance statistics
    if all_coupling_errors:
        coupling_rel_errors = [e['rel_error'] for e in all_coupling_errors]
        coupling_abs_errors = [e['abs_error'] for e in all_coupling_errors]

        result['coupling_cap'] = {
            'mean_rel_error': np.mean(coupling_rel_errors),
            'median_rel_error': np.median(coupling_rel_errors),
            'std_rel_error': np.std(coupling_rel_errors),
            'mean_abs_error': np.mean(coupling_abs_errors),
            'max_rel_error': np.max(coupling_rel_errors),
            'min_rel_error': np.min(coupling_rel_errors),
            'worst_errors': sorted(all_coupling_errors, key=lambda x: x['rel_error'], reverse=True)[:5]
        }

        print(f"Coupling-capacitance results:")
        print(f"  Files with data: {files_with_coupling_data}/{len(common_files)}")
        print(f"  Total pairs: {total_coupling_pairs:,}")
        print(f"  Mean relative error: {result['coupling_cap']['mean_rel_error']:.2%}")
        print(f"  Median relative error: {result['coupling_cap']['median_rel_error']:.2%}")
        print(f"  Standard deviation: {result['coupling_cap']['std_rel_error']:.2%}")

    if collect_errors:
        if all_self_errors:
            result['self_errors'] = all_self_errors
        if all_coupling_errors:
            result['coupling_errors'] = all_coupling_errors

    return result

def format_comparison_table(results: List[Dict], analysis_type: str) -> str:
    """Format comparison results into a readable table."""

    if analysis_type == 'self':
        headers = ["Technology", "Size", "Tools", "Files", "Nets", "Mean Rel Error", "Median Rel Error", "Std Rel Error"]
        rows = [headers]

        for result in results:
            if 'self_cap' in result:
                stats = result['self_cap']
                tool_pair = f"{result['tool1_name']} vs {result['tool2_name']}"
                rows.append([
                    result['technology'].upper(),
                    result['size'].upper(),
                    tool_pair,
                    str(result['files_with_self_data']),
                    f"{result['total_self_nets']:,}",
                    f"{stats['mean_rel_error']:.2%}",
                    f"{stats['median_rel_error']:.2%}",
                    f"{stats['std_rel_error']:.2%}"
                ])

    elif analysis_type == 'coupling':
        headers = ["Technology", "Size", "Tools", "Files", "Pairs", "Mean Rel Error", "Median Rel Error", "Std Rel Error"]
        rows = [headers]

        for result in results:
            if 'coupling_cap' in result:
                stats = result['coupling_cap']
                tool_pair = f"{result['tool1_name']} vs {result['tool2_name']}"
                rows.append([
                    result['technology'].upper(),
                    result['size'].upper(),
                    tool_pair,
                    str(result['files_with_coupling_data']),
                    f"{result['total_coupling_pairs']:,}",
                    f"{stats['mean_rel_error']:.2%}",
                    f"{stats['median_rel_error']:.2%}",
                    f"{stats['std_rel_error']:.2%}"
                ])

    else:  # combined
        headers = ["Technology", "Size", "Tools", "Files", "Nets", "Pairs", "Self Err", "Coup Err", "Self Std", "Coup Std"]
        rows = [headers]

        for result in results:
            tech = result['technology'].upper()
            size = result['size'].upper()
            files = str(result['files_analyzed'])
            tool_pair = f"{result['tool1_name']} vs {result['tool2_name']}"

            if 'self_cap' in result and 'coupling_cap' in result:
                self_stats = result['self_cap']
                coup_stats = result['coupling_cap']
                rows.append([
                    tech, size, tool_pair, files,
                    f"{result['total_self_nets']:,}",
                    f"{result['total_coupling_pairs']:,}",
                    f"{self_stats['mean_rel_error']:.2%}",
                    f"{coup_stats['mean_rel_error']:.2%}",
                    f"{self_stats['std_rel_error']:.2%}",
                    f"{coup_stats['std_rel_error']:.2%}"
                ])
            elif 'self_cap' in result:
                self_stats = result['self_cap']
                rows.append([
                    tech, size, tool_pair, files,
                    f"{result['total_self_nets']:,}",
                    "N/A",
                    f"{self_stats['mean_rel_error']:.2%}",
                    "N/A",
                    f"{self_stats['std_rel_error']:.2%}",
                    "N/A"
                ])
            elif 'coupling_cap' in result:
                coup_stats = result['coupling_cap']
                rows.append([
                    tech, size, tool_pair, files,
                    "N/A",
                    f"{result['total_coupling_pairs']:,}",
                    "N/A",
                    f"{coup_stats['mean_rel_error']:.2%}",
                    "N/A",
                    f"{coup_stats['std_rel_error']:.2%}"
                ])

    # Format table
    col_widths = [max(len(str(row[i])) for row in rows) for i in range(len(headers))]
    def fmt_row(row):
        return " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))

    separator = "-+-".join("-" * w for w in col_widths)
    table_lines = [fmt_row(rows[0]), separator]
    table_lines.extend(fmt_row(row) for row in rows[1:])

    return "\n".join(table_lines)

def print_detailed_analysis(results: List[Dict], analysis_type: str):
    """Print detailed analysis for each dataset."""
    for result in results:
        tech = result['technology'].upper()
        size = result['size'].upper()
        tool1_name = result['tool1_name']
        tool2_name = result['tool2_name']

        print(f"\n{'='*60}")
        print(f"{tech} {size} - {tool1_name} vs {tool2_name} Detailed Analysis")
        print(f"{'='*60}")

        if analysis_type in ['self', 'all'] and 'self_cap' in result:
            stats = result['self_cap']
            print(f"Self-Capacitance:")
            print(f"  Files analyzed: {result['files_with_self_data']}")
            print(f"  Total nets: {result['total_self_nets']:,}")
            print(f"  Mean absolute error: {stats['mean_abs_error']:.2e} F")
            print(f"  Mean relative error: {stats['mean_rel_error']:.2%}")
            print(f"  Median relative error: {stats['median_rel_error']:.2%}")
            print(f"  Standard deviation: {stats['std_rel_error']:.2%}")
            print(f"  Min relative error: {stats['min_rel_error']:.2%}")
            print(f"  Max relative error: {stats['max_rel_error']:.2%}")

            print(f"  Worst 5 relative errors:")
            for i, error in enumerate(stats['worst_errors'][:5], 1):
                tool1_val = error[tool1_name.lower()]
                tool2_val = error[tool2_name.lower()]
                print(f"    {i}. Net {error['net']}: {error['rel_error']:.2%} "
                      f"({tool1_name}: {tool1_val:.2e}F, {tool2_name}: {tool2_val:.2e}F)")

        if analysis_type in ['coupling', 'all'] and 'coupling_cap' in result:
            stats = result['coupling_cap']
            print(f"Coupling-Capacitance:")
            print(f"  Files analyzed: {result['files_with_coupling_data']}")
            print(f"  Total pairs: {result['total_coupling_pairs']:,}")
            print(f"  Mean absolute error: {stats['mean_abs_error']:.2e} F")
            print(f"  Mean relative error: {stats['mean_rel_error']:.2%}")
            print(f"  Median relative error: {stats['median_rel_error']:.2%}")
            print(f"  Standard deviation: {stats['std_rel_error']:.2%}")
            print(f"  Min relative error: {stats['min_rel_error']:.2%}")
            print(f"  Max relative error: {stats['max_rel_error']:.2%}")

            print(f"  Worst 5 relative errors:")
            for i, error in enumerate(stats['worst_errors'][:5], 1):
                tool1_val = error[tool1_name.lower()]
                tool2_val = error[tool2_name.lower()]
                print(f"    {i}. {error['pair']}: {error['rel_error']:.2%} "
                      f"({tool1_name}: {tool1_val:.2e}F, {tool2_name}: {tool2_val:.2e}F)")

def generate_self_cap_scatter_plot(results: List[Dict], output_path: Path,
                                   max_points: int = 10_000,
                                   ground_truth_tool: Optional[str] = None,
                                   font_scale: float = 2.0) -> None:
    """Generate scatter plots comparing total capacitance vs. extraction error."""
    plot_ready = [
        r for r in results
        if r.get('self_errors') and (ground_truth_tool is None or r.get('ground_truth_tool') == ground_truth_tool)
    ]

    if not plot_ready:
        print("No self-capacitance error data available for scatter plot generation.")
        return

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - optional dependency
        print(f"Matplotlib is required for plotting but is not available ({exc}).")
        return

    num_plots = len(plot_ready)
    plt.rcParams.update({
        'font.family': 'Times New Roman',
        'font.size': plt.rcParams.get('font.size', 10) * font_scale
    })
    fig, axes = plt.subplots(1, num_plots, figsize=(6 * num_plots, 5), squeeze=False, sharey=True)
    axes = axes.flatten()

    for ax, result in zip(axes, plot_ready):
        errors = result['self_errors']
        if not errors:
            ax.set_visible(False)
            continue

        ground_caps = np.array([err['ground_cap_f'] for err in errors], dtype=float)
        signed_rel_errors = np.array([err['signed_rel_error'] for err in errors], dtype=float) * 100.0

        valid_mask = ground_caps > 0
        ground_caps = ground_caps[valid_mask]
        signed_rel_errors = signed_rel_errors[valid_mask]

        if ground_caps.size == 0:
            ax.set_visible(False)
            continue

        caps_ff = ground_caps * 1e15  # Convert to femtofarads for readability

        if caps_ff.size == 0:
            ax.set_visible(False)
            continue

        if caps_ff.size > max_points:
            caps_ff = caps_ff[:max_points]
            signed_rel_errors = signed_rel_errors[:max_points]

        comparison_tool = result['tool2_name'] if result.get('tool1_is_ground_truth') else result['tool1_name']
        color_map = {
            'RWCap': '#2c7fb8',     # darker blue tone
            'OpenRCX': '#c75062'    # darker magenta/red tone
        }
        point_color = color_map.get(comparison_tool, '#d62728')

        base_size = 6
        size_scale = 1.33 ** 2  # radius increase by 33%
        ax.scatter(signed_rel_errors, caps_ff, s=base_size * size_scale, alpha=0.8,
                   color=point_color, edgecolors='none')
        ax.axvline(0.0, color='black', linewidth=0.8, alpha=0.5)
        ax.set_yscale('log')

        tool_lower = comparison_tool.lower()
        if tool_lower == 'openrcx':
            ax.set_xlim(-200, 200)
            ax.set_xticks([-200, -100, 0, 100, 200])
        elif tool_lower == 'rwcap':
            ax.set_xlim(-10, 10)
            ax.set_xticks([-10, -5, 0, 5, 10])
        else:
            x_abs_max = np.max(np.abs(signed_rel_errors))
            x_limit = max(5.0, np.ceil(x_abs_max / 5.0) * 5.0)
            ax.set_xlim(-x_limit, x_limit)

        y_min = caps_ff.min()
        y_max = caps_ff.max()
        lower = max(1e-3, y_min)
        upper = max(1.0, 10 ** np.ceil(np.log10(max(y_max, lower * 10))))
        ax.set_ylim(lower, upper)

        ax.set_xlabel("Error (%)")

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    axes[0].set_ylabel("Total Capacitance (fF)")

    output_path = Path(output_path)
    if output_path.suffix.lower() != '.pdf':
        output_path = output_path.with_suffix('.pdf')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, format='pdf')
    plt.close(fig)
    print(f"Saved scatter plot to {output_path}")

def main():
    """Main comparison analysis."""
    parser = argparse.ArgumentParser(description='Comprehensive Capacitance Comparison Tool')
    parser.add_argument('--type', choices=['self', 'coupling', 'all'], default='all',
                       help='Type of capacitance analysis to perform')
    parser.add_argument('--tech', choices=['all', 'nangate45', 'asap7', 'sky130hd'], default='all',
                       help='Technology nodes to analyze')
    parser.add_argument('--size', choices=['all', 'small', 'medium', 'large'], default='all',
                       help='Dataset sizes to analyze')
    parser.add_argument('--tools', choices=['all', 'rwcap_raphael', 'rwcap_openrcx', 'raphael_openrcx'],
                       default='all', help='Tool pairs to compare')
    parser.add_argument('--no-details', action='store_true',
                       help='Skip detailed analysis output')
    parser.add_argument('--ground-truth-tool', choices=['RWCap', 'Raphael', 'OpenRCX'],
                        default=None, help='Tool to treat as ground truth when comparing pairs')
    parser.add_argument('--scatter-plot', type=str, default=None,
                        help='Output path for scatter plot of error vs total capacitance')
    parser.add_argument('--scatter-max-points', type=int, default=1_000,
                        help='Maximum number of points per subplot in the scatter plot')
    parser.add_argument('--scatter-font-scale', type=float, default=2.0,
                        help='Font scale multiplier for the scatter plot (default doubles the base size)')

    args = parser.parse_args()

    print("Comprehensive Capacitance Comparison: RWCap vs Raphael vs OpenRCX")
    print("=" * 80)

    # Define datasets to analyze
    all_datasets = [
        ('nangate45', 'small'),
        ('asap7', 'small'),
        ('sky130hd', 'small'),
        ('sky130hd', 'medium'),
        ('sky130hd', 'large'),
    ]

    # Filter datasets based on arguments
    if args.tech != 'all':
        all_datasets = [(tech, size) for tech, size in all_datasets if tech == args.tech]

    if args.size != 'all':
        all_datasets = [(tech, size) for tech, size in all_datasets if size == args.size]

    results = []
    collect_errors = bool(args.scatter_plot)

    # Analyze each dataset
    for technology, size in all_datasets:
        dataset_results = analyze_dataset_comparison(
            technology, size, args.type, args.tools,
            ground_truth_tool=args.ground_truth_tool,
            collect_errors=collect_errors
        )
        results.extend(dataset_results)

    # Print summary tables
    if not results:
        print("No comparison results found. Check that the specified tools and datasets exist.")
        return

    if args.type == 'all':
        print(f"\n{'='*80}")
        print("COMBINED SUMMARY TABLE")
        print(f"{'='*80}")
        print(format_comparison_table(results, 'combined'))

        print(f"\n{'='*80}")
        print("SELF-CAPACITANCE SUMMARY")
        print(f"{'='*80}")
        self_results = [r for r in results if 'self_cap' in r]
        if self_results:
            print(format_comparison_table(self_results, 'self'))

        print(f"\n{'='*80}")
        print("COUPLING-CAPACITANCE SUMMARY")
        print(f"{'='*80}")
        coupling_results = [r for r in results if 'coupling_cap' in r]
        if coupling_results:
            print(format_comparison_table(coupling_results, 'coupling'))

    else:
        print(f"\n{'='*80}")
        print(f"{args.type.upper()}-CAPACITANCE SUMMARY")
        print(f"{'='*80}")
        print(format_comparison_table(results, args.type))

    # Print detailed analysis
    if not args.no_details:
        print_detailed_analysis(results, args.type)

    if args.scatter_plot:
        generate_self_cap_scatter_plot(
            results,
            Path(args.scatter_plot),
            max_points=args.scatter_max_points,
            ground_truth_tool=args.ground_truth_tool,
            font_scale=args.scatter_font_scale
        )

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Comprehensive capacitance comparison tool for two SPEF directories.

Usage:
    python scripts/capacitance_comparison.py <dir_a> <dir_b> [--type self|coupling|all]

`self` mode compares `*D_NET` total capacitances, not derived 3-field ground CAP entries.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from spef_tools.python_parser import load_coupling_pairs, load_dnet_totals


DIR_A_NAME = "Dir A"
DIR_B_NAME = "Dir B"


def load_spef_capacitances(spef_path: Path) -> Tuple[Dict[str, float], Dict[Tuple[str, str], float]]:
    """Load per-net total capacitances and unordered coupling pairs in Farads."""
    spef_path = Path(spef_path).resolve()
    if not spef_path.exists():
        print(f"Warning: SPEF file not found: {spef_path}")
        return {}, {}

    try:
        total_capacitances = load_dnet_totals(spef_path)
        coupling_capacitances = load_coupling_pairs(spef_path)
    except Exception as exc:
        print(f"Warning: Error parsing {spef_path}: {exc}")
        return {}, {}

    return total_capacitances, coupling_capacitances


def _resolve_spef_dir(path: Path | str, *, label: str) -> Path:
    directory = Path(path).resolve()
    if not directory.exists():
        raise FileNotFoundError(f"{label} does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"{label} is not a directory: {directory}")
    return directory


def discover_spef_file_sets(dir_a: Path | str, dir_b: Path | str) -> tuple[list[str], list[str], list[str]]:
    """Return common stems and the stems unique to each directory."""
    resolved_a = _resolve_spef_dir(dir_a, label=DIR_A_NAME)
    resolved_b = _resolve_spef_dir(dir_b, label=DIR_B_NAME)

    files_a = {path.stem for path in resolved_a.glob("*.spef")}
    files_b = {path.stem for path in resolved_b.glob("*.spef")}
    common_files = sorted(files_a & files_b)
    only_a = sorted(files_a - files_b)
    only_b = sorted(files_b - files_a)
    return common_files, only_a, only_b


def compare_total_capacitances(
    dir_a_caps: Dict[str, float],
    dir_b_caps: Dict[str, float],
    dir_a_name: str,
    dir_b_name: str,
    *,
    dir_a_is_ground_truth: bool = False,
) -> List[Dict]:
    """Compare total D_NET capacitance values between two directories."""
    common_nets = set(dir_a_caps.keys()) & set(dir_b_caps.keys())
    errors = []

    for net in common_nets:
        dir_a_val = dir_a_caps[net]
        dir_b_val = dir_b_caps[net]

        if dir_a_is_ground_truth:
            reference_val = dir_a_val
            comparison_val = dir_b_val
        else:
            reference_val = dir_b_val
            comparison_val = dir_a_val

        abs_error = abs(dir_a_val - dir_b_val)
        denom = max(reference_val, 1e-20)
        signed_rel_error = (comparison_val - reference_val) / denom
        rel_error = abs(signed_rel_error)

        errors.append(
            {
                "net": net,
                dir_a_name.lower(): dir_a_val,
                dir_b_name.lower(): dir_b_val,
                "abs_error": abs_error,
                "rel_error": rel_error,
                "signed_rel_error": signed_rel_error,
                "reference_cap_f": reference_val,
                "comparison_cap_f": comparison_val,
            }
        )

    return errors


def compare_coupling_capacitances(
    dir_a_caps: Dict[Tuple[str, str], float],
    dir_b_caps: Dict[Tuple[str, str], float],
    dir_a_name: str,
    dir_b_name: str,
    *,
    dir_a_is_ground_truth: bool = False,
) -> List[Dict]:
    """Compare coupling capacitance values between two directories."""
    common_pairs = set(dir_a_caps.keys()) & set(dir_b_caps.keys())
    errors = []

    for pair in common_pairs:
        dir_a_val = dir_a_caps[pair]
        dir_b_val = dir_b_caps[pair]

        if dir_a_is_ground_truth:
            reference_val = dir_a_val
            comparison_val = dir_b_val
        else:
            reference_val = dir_b_val
            comparison_val = dir_a_val

        abs_error = abs(dir_a_val - dir_b_val)
        denom = max(reference_val, 1e-20)
        signed_rel_error = (comparison_val - reference_val) / denom
        rel_error = abs(signed_rel_error)

        net1, net2 = pair
        errors.append(
            {
                "pair": f"{net1} - {net2}",
                dir_a_name.lower(): dir_a_val,
                dir_b_name.lower(): dir_b_val,
                "abs_error": abs_error,
                "rel_error": rel_error,
                "signed_rel_error": signed_rel_error,
                "ground_cap_f": reference_val,
                "comparison_cap_f": comparison_val,
            }
        )

    return errors


def analyze_capacitance_comparison(
    dir_a: Path | str,
    dir_b: Path | str,
    common_files: List[str],
    *,
    dir_a_name: str = DIR_A_NAME,
    dir_b_name: str = DIR_B_NAME,
    analysis_type: str = "all",
    dir_a_is_ground_truth: bool = False,
    collect_errors: bool = False,
    only_dir_a_files: int = 0,
    only_dir_b_files: int = 0,
) -> Dict:
    """Perform detailed capacitance comparison analysis for two SPEF directories."""
    resolved_a = _resolve_spef_dir(dir_a, label=dir_a_name)
    resolved_b = _resolve_spef_dir(dir_b, label=dir_b_name)

    all_total_errors = []
    all_coupling_errors = []
    files_with_total_data = 0
    files_with_coupling_data = 0
    total_total_nets = 0
    total_coupling_pairs = 0

    print(f"\n{'=' * 60}")
    print(f"Analyzing {dir_a_name} vs {dir_b_name} - {analysis_type.upper()}")
    print(f"{'=' * 60}")
    print(f"{dir_a_name}: {resolved_a}")
    print(f"{dir_b_name}: {resolved_b}")
    print(f"Common SPEF files: {len(common_files)}")
    print(f"Only in {dir_a_name}: {only_dir_a_files}")
    print(f"Only in {dir_b_name}: {only_dir_b_files}")

    for file_name in common_files:
        dir_a_file = resolved_a / f"{file_name}.spef"
        dir_b_file = resolved_b / f"{file_name}.spef"

        dir_a_total, dir_a_coupling = load_spef_capacitances(dir_a_file)
        dir_b_total, dir_b_coupling = load_spef_capacitances(dir_b_file)

        if analysis_type in {"self", "all"} and dir_a_total and dir_b_total:
            total_errors = compare_total_capacitances(
                dir_a_total,
                dir_b_total,
                dir_a_name,
                dir_b_name,
                dir_a_is_ground_truth=dir_a_is_ground_truth,
            )
            if total_errors:
                all_total_errors.extend(total_errors)
                files_with_total_data += 1
                total_total_nets += len(total_errors)

        if analysis_type in {"coupling", "all"} and dir_a_coupling and dir_b_coupling:
            coupling_errors = compare_coupling_capacitances(
                dir_a_coupling,
                dir_b_coupling,
                dir_a_name,
                dir_b_name,
                dir_a_is_ground_truth=dir_a_is_ground_truth,
            )
            if coupling_errors:
                all_coupling_errors.extend(coupling_errors)
                files_with_coupling_data += 1
                total_coupling_pairs += len(coupling_errors)

    result = {
        "comparison_label": f"{dir_a_name} vs {dir_b_name}",
        "dir_a_name": dir_a_name,
        "dir_b_name": dir_b_name,
        "dir_a_path": str(resolved_a),
        "dir_b_path": str(resolved_b),
        "files_analyzed": len(common_files),
        "only_dir_a_files": int(only_dir_a_files),
        "only_dir_b_files": int(only_dir_b_files),
        "files_with_total_data": files_with_total_data,
        "files_with_coupling_data": files_with_coupling_data,
        "total_total_nets": total_total_nets,
        "total_coupling_pairs": total_coupling_pairs,
        "dir_a_is_ground_truth": dir_a_is_ground_truth,
        "ground_truth_dir": dir_a_name if dir_a_is_ground_truth else dir_b_name,
    }

    if all_total_errors:
        total_rel_errors = [error["rel_error"] for error in all_total_errors]
        total_abs_errors = [error["abs_error"] for error in all_total_errors]
        result["total_cap"] = {
            "mean_rel_error": np.mean(total_rel_errors),
            "median_rel_error": np.median(total_rel_errors),
            "std_rel_error": np.std(total_rel_errors),
            "mean_abs_error": np.mean(total_abs_errors),
            "max_rel_error": np.max(total_rel_errors),
            "min_rel_error": np.min(total_rel_errors),
            "worst_errors": sorted(all_total_errors, key=lambda value: value["rel_error"], reverse=True)[:5],
        }
        print("Total-capacitance results:")
        print(f"  Files with data: {files_with_total_data}/{len(common_files)}")
        print(f"  Total nets: {total_total_nets:,}")
        print(f"  Mean relative error: {result['total_cap']['mean_rel_error']:.2%}")
        print(f"  Median relative error: {result['total_cap']['median_rel_error']:.2%}")
        print(f"  Standard deviation: {result['total_cap']['std_rel_error']:.2%}")

    if all_coupling_errors:
        coupling_rel_errors = [error["rel_error"] for error in all_coupling_errors]
        coupling_abs_errors = [error["abs_error"] for error in all_coupling_errors]
        result["coupling_cap"] = {
            "mean_rel_error": np.mean(coupling_rel_errors),
            "median_rel_error": np.median(coupling_rel_errors),
            "std_rel_error": np.std(coupling_rel_errors),
            "mean_abs_error": np.mean(coupling_abs_errors),
            "max_rel_error": np.max(coupling_rel_errors),
            "min_rel_error": np.min(coupling_rel_errors),
            "worst_errors": sorted(all_coupling_errors, key=lambda value: value["rel_error"], reverse=True)[:5],
        }
        print("Coupling-capacitance results:")
        print(f"  Files with data: {files_with_coupling_data}/{len(common_files)}")
        print(f"  Total pairs: {total_coupling_pairs:,}")
        print(f"  Mean relative error: {result['coupling_cap']['mean_rel_error']:.2%}")
        print(f"  Median relative error: {result['coupling_cap']['median_rel_error']:.2%}")
        print(f"  Standard deviation: {result['coupling_cap']['std_rel_error']:.2%}")

    if collect_errors:
        if all_total_errors:
            result["total_errors"] = all_total_errors
        if all_coupling_errors:
            result["coupling_errors"] = all_coupling_errors

    return result


def format_comparison_table(results: List[Dict], analysis_type: str) -> str:
    """Format comparison results into a readable table."""
    if analysis_type == "self":
        headers = ["Comparison", "Common", "Only A", "Only B", "Nets", "Mean Rel Error", "Median Rel Error", "Std Rel Error"]
        rows = [headers]
        for result in results:
            if "total_cap" not in result:
                continue
            stats = result["total_cap"]
            rows.append(
                [
                    result["comparison_label"],
                    str(result["files_with_total_data"]),
                    str(result["only_dir_a_files"]),
                    str(result["only_dir_b_files"]),
                    f"{result['total_total_nets']:,}",
                    f"{stats['mean_rel_error']:.2%}",
                    f"{stats['median_rel_error']:.2%}",
                    f"{stats['std_rel_error']:.2%}",
                ]
            )
    elif analysis_type == "coupling":
        headers = ["Comparison", "Common", "Only A", "Only B", "Pairs", "Mean Rel Error", "Median Rel Error", "Std Rel Error"]
        rows = [headers]
        for result in results:
            if "coupling_cap" not in result:
                continue
            stats = result["coupling_cap"]
            rows.append(
                [
                    result["comparison_label"],
                    str(result["files_with_coupling_data"]),
                    str(result["only_dir_a_files"]),
                    str(result["only_dir_b_files"]),
                    f"{result['total_coupling_pairs']:,}",
                    f"{stats['mean_rel_error']:.2%}",
                    f"{stats['median_rel_error']:.2%}",
                    f"{stats['std_rel_error']:.2%}",
                ]
            )
    else:
        headers = ["Comparison", "Common", "Only A", "Only B", "Nets", "Pairs", "Total Err", "Coup Err", "Total Std", "Coup Std"]
        rows = [headers]
        for result in results:
            total_stats = result.get("total_cap")
            coupling_stats = result.get("coupling_cap")
            rows.append(
                [
                    result["comparison_label"],
                    str(result["files_analyzed"]),
                    str(result["only_dir_a_files"]),
                    str(result["only_dir_b_files"]),
                    f"{result['total_total_nets']:,}" if total_stats else "N/A",
                    f"{result['total_coupling_pairs']:,}" if coupling_stats else "N/A",
                    f"{total_stats['mean_rel_error']:.2%}" if total_stats else "N/A",
                    f"{coupling_stats['mean_rel_error']:.2%}" if coupling_stats else "N/A",
                    f"{total_stats['std_rel_error']:.2%}" if total_stats else "N/A",
                    f"{coupling_stats['std_rel_error']:.2%}" if coupling_stats else "N/A",
                ]
            )

    col_widths = [max(len(str(row[index])) for row in rows) for index in range(len(headers))]

    def fmt_row(row):
        return " | ".join(str(row[index]).ljust(col_widths[index]) for index in range(len(row)))

    separator = "-+-".join("-" * width for width in col_widths)
    return "\n".join([fmt_row(rows[0]), separator, *(fmt_row(row) for row in rows[1:])])


def print_detailed_analysis(results: List[Dict], analysis_type: str):
    """Print detailed analysis for each comparison result."""
    for result in results:
        dir_a_name = result["dir_a_name"]
        dir_b_name = result["dir_b_name"]

        print(f"\n{'=' * 60}")
        print(f"{result['comparison_label']} Detailed Analysis")
        print(f"{'=' * 60}")
        print(f"{dir_a_name}: {result['dir_a_path']}")
        print(f"{dir_b_name}: {result['dir_b_path']}")
        print(f"Only in {dir_a_name}: {result['only_dir_a_files']}")
        print(f"Only in {dir_b_name}: {result['only_dir_b_files']}")

        if analysis_type in {"self", "all"} and "total_cap" in result:
            stats = result["total_cap"]
            print("Total-Capacitance:")
            print(f"  Files analyzed: {result['files_with_total_data']}")
            print(f"  Total nets: {result['total_total_nets']:,}")
            print(f"  Mean absolute error: {stats['mean_abs_error']:.2e} F")
            print(f"  Mean relative error: {stats['mean_rel_error']:.2%}")
            print(f"  Median relative error: {stats['median_rel_error']:.2%}")
            print(f"  Standard deviation: {stats['std_rel_error']:.2%}")
            print(f"  Min relative error: {stats['min_rel_error']:.2%}")
            print(f"  Max relative error: {stats['max_rel_error']:.2%}")
            print("  Worst 5 relative errors:")
            for index, error in enumerate(stats["worst_errors"][:5], 1):
                dir_a_val = error[dir_a_name.lower()]
                dir_b_val = error[dir_b_name.lower()]
                print(
                    f"    {index}. Net {error['net']}: {error['rel_error']:.2%} "
                    f"({dir_a_name}: {dir_a_val:.2e}F, {dir_b_name}: {dir_b_val:.2e}F)"
                )

        if analysis_type in {"coupling", "all"} and "coupling_cap" in result:
            stats = result["coupling_cap"]
            print("Coupling-Capacitance:")
            print(f"  Files analyzed: {result['files_with_coupling_data']}")
            print(f"  Total pairs: {result['total_coupling_pairs']:,}")
            print(f"  Mean absolute error: {stats['mean_abs_error']:.2e} F")
            print(f"  Mean relative error: {stats['mean_rel_error']:.2%}")
            print(f"  Median relative error: {stats['median_rel_error']:.2%}")
            print(f"  Standard deviation: {stats['std_rel_error']:.2%}")
            print(f"  Min relative error: {stats['min_rel_error']:.2%}")
            print(f"  Max relative error: {stats['max_rel_error']:.2%}")
            print("  Worst 5 relative errors:")
            for index, error in enumerate(stats["worst_errors"][:5], 1):
                dir_a_val = error[dir_a_name.lower()]
                dir_b_val = error[dir_b_name.lower()]
                print(
                    f"    {index}. {error['pair']}: {error['rel_error']:.2%} "
                    f"({dir_a_name}: {dir_a_val:.2e}F, {dir_b_name}: {dir_b_val:.2e}F)"
                )


def generate_self_cap_scatter_plot(
    results: List[Dict],
    output_path: Path,
    *,
    max_points: int = 10_000,
    font_scale: float = 2.0,
) -> None:
    """Generate scatter plots comparing total capacitance vs. extraction error."""
    plot_ready = [result for result in results if result.get("total_errors")]
    if not plot_ready:
        print("No total-capacitance error data available for scatter plot generation.")
        return

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - optional dependency
        print(f"Matplotlib is required for plotting but is not available ({exc}).")
        return

    num_plots = len(plot_ready)
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": plt.rcParams.get("font.size", 10) * font_scale,
        }
    )
    fig, axes = plt.subplots(1, num_plots, figsize=(6 * num_plots, 5), squeeze=False, sharey=True)
    axes = axes.flatten()

    for axis, result in zip(axes, plot_ready):
        errors = result["total_errors"]
        ground_caps = np.array([error["reference_cap_f"] for error in errors], dtype=float)
        signed_rel_errors = np.array([error["signed_rel_error"] for error in errors], dtype=float) * 100.0

        valid_mask = ground_caps > 0
        ground_caps = ground_caps[valid_mask]
        signed_rel_errors = signed_rel_errors[valid_mask]
        if ground_caps.size == 0:
            axis.set_visible(False)
            continue

        caps_ff = ground_caps * 1e15
        if caps_ff.size > max_points:
            caps_ff = caps_ff[:max_points]
            signed_rel_errors = signed_rel_errors[:max_points]

        point_color = "#c75062" if result.get("dir_a_is_ground_truth") else "#2c7fb8"
        axis.scatter(
            signed_rel_errors,
            caps_ff,
            s=6 * (1.33 ** 2),
            alpha=0.8,
            color=point_color,
            edgecolors="none",
        )
        axis.axvline(0.0, color="black", linewidth=0.8, alpha=0.5)
        axis.set_yscale("log")

        x_abs_max = float(np.max(np.abs(signed_rel_errors))) if signed_rel_errors.size else 0.0
        x_limit = max(5.0, np.ceil(x_abs_max / 5.0) * 5.0)
        axis.set_xlim(-x_limit, x_limit)

        y_min = float(caps_ff.min())
        y_max = float(caps_ff.max())
        lower = max(1e-3, y_min)
        upper = max(1.0, 10 ** np.ceil(np.log10(max(y_max, lower * 10))))
        axis.set_ylim(lower, upper)

        axis.set_title(result["comparison_label"])
        axis.set_xlabel("Error (%)")
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    axes[0].set_ylabel("Total Capacitance (fF)")

    output_path = Path(output_path)
    if output_path.suffix.lower() != ".pdf":
        output_path = output_path.with_suffix(".pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, format="pdf")
    plt.close(fig)
    print(f"Saved scatter plot to {output_path}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare capacitance values across two SPEF directories.")
    parser.add_argument("dir_a", type=Path, help="First directory containing .spef files.")
    parser.add_argument("dir_b", type=Path, help="Second directory containing .spef files.")
    parser.add_argument(
        "--type",
        choices=["self", "coupling", "all"],
        default="all",
        help="Type of capacitance analysis to perform. `self` compares D_NET totals.",
    )
    parser.add_argument("--no-details", action="store_true", help="Skip detailed analysis output.")
    parser.add_argument(
        "--ground-truth",
        choices=["a", "b"],
        default=None,
        help="Which directory to treat as ground truth when computing signed relative errors.",
    )
    parser.add_argument("--scatter-plot", type=str, default=None, help="Output path for total-capacitance scatter plot.")
    parser.add_argument(
        "--scatter-max-points",
        type=int,
        default=1_000,
        help="Maximum number of points per subplot in the scatter plot.",
    )
    parser.add_argument(
        "--scatter-font-scale",
        type=float,
        default=2.0,
        help="Font scale multiplier for the scatter plot.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    dir_a = _resolve_spef_dir(args.dir_a, label=DIR_A_NAME)
    dir_b = _resolve_spef_dir(args.dir_b, label=DIR_B_NAME)

    print(f"Comprehensive Capacitance Comparison: {DIR_A_NAME} vs {DIR_B_NAME}")
    print("=" * 80)

    common_files, only_a, only_b = discover_spef_file_sets(dir_a, dir_b)
    if not common_files:
        print("No comparison results found. The two directories do not share any .spef filename stems.")
        return 0

    result = analyze_capacitance_comparison(
        dir_a,
        dir_b,
        common_files,
        analysis_type=args.type,
        dir_a_is_ground_truth=args.ground_truth == "a",
        collect_errors=bool(args.scatter_plot),
        only_dir_a_files=len(only_a),
        only_dir_b_files=len(only_b),
    )
    results = [result]

    if args.type == "all":
        print(f"\n{'=' * 80}")
        print("COMBINED SUMMARY TABLE")
        print(f"{'=' * 80}")
        print(format_comparison_table(results, "combined"))

        total_results = [current for current in results if "total_cap" in current]
        if total_results:
            print(f"\n{'=' * 80}")
            print("TOTAL-CAPACITANCE SUMMARY")
            print(f"{'=' * 80}")
            print(format_comparison_table(total_results, "self"))

        coupling_results = [current for current in results if "coupling_cap" in current]
        if coupling_results:
            print(f"\n{'=' * 80}")
            print("COUPLING-CAPACITANCE SUMMARY")
            print(f"{'=' * 80}")
            print(format_comparison_table(coupling_results, "coupling"))
    else:
        print(f"\n{'=' * 80}")
        if args.type == "self":
            print("TOTAL-CAPACITANCE SUMMARY")
        else:
            print(f"{args.type.upper()}-CAPACITANCE SUMMARY")
        print(f"{'=' * 80}")
        print(format_comparison_table(results, args.type))

    if not args.no_details:
        print_detailed_analysis(results, args.type)

    if args.scatter_plot:
        generate_self_cap_scatter_plot(
            results,
            Path(args.scatter_plot),
            max_points=args.scatter_max_points,
            font_scale=args.scatter_font_scale,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

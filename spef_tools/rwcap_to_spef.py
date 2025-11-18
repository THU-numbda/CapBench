#!/usr/bin/env python3
"""
Convert every RWCap `.out` file in a directory to capacitance-only SPEF files.

Usage:
    python spef/rwcap_to_spef.py <rwcap_dir> <spef_dir>

Each `.out` file is parsed and written to `<spef_dir>/<window>.spef`, where
`<window>` is derived from the RWCap filename. All capacitive pairs found in the
RWCap reports, including terms against `GROUND`, are emitted as explicit
coupling entries in the SPEF.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tqdm import tqdm



TaskRe = re.compile(r"^Task\s+(?P<net>.+?):\s")
MasterRe = re.compile(r"^Master\s+(?P<net>.+?)\s*:\s*(?P<val>[+\-]?[0-9]*\.?[0-9]+(?:[eE][+\-]?[0-9]+)?)\s*F\s*$")
CapOnRe = re.compile(r"^Capacitance on\s+(?P<name>.+?)\s*=\s*(?P<val>[+\-]?[0-9]*\.?[0-9]+(?:[eE][+\-]?[0-9]+)?)\s*F\s*$")


def parse_rwcap(
    lines: Iterable[str],
    *,
    drop_nets: Set[str],
    threshold_f: float,
) -> Tuple[Dict[str, float], Dict[Tuple[str, str], float]]:
    """Parse RWCap output.

    Returns:
      self_cap_f: net -> self capacitance (F)
      coupling_f: (min(net_i, net_j), max(...)) -> coupling (F), averaged if seen twice
    """

    self_cap_f: Dict[str, float] = {}
    coupling_f: Dict[Tuple[str, str], float] = {}

    current: Optional[str] = None

    for raw in lines:
        line = raw.rstrip("\n")
        m = TaskRe.match(line)
        if m:
            current = m.group("net")
            continue

        m = MasterRe.match(line)
        if m:
            net = m.group("net")
            try:
                val = float(m.group("val"))
            except ValueError:
                continue
            self_cap_f[net] = val
            # If parsing "Master X" outside a Task block, still fine.
            if current is None:
                current = net
            continue

        m = CapOnRe.match(line)
        if m and current is not None:
            name = m.group("name")
            try:
                val = float(m.group("val"))
            except ValueError:
                continue

            if name == current:
                # consistency check: self value; keep the max if duplicate
                if current not in self_cap_f or abs(self_cap_f[current]) < abs(val):
                    self_cap_f[current] = val
                continue

            # Magnitude thresholding for non-self lines
            if abs(val) < threshold_f:
                continue

            if name in drop_nets:
                continue

            # Coupling contribution (RWCap uses negative values for couplings)
            c = abs(val)
            i, j = sorted((current, name))
            if (i, j) in coupling_f:
                # average to reduce asymmetry between the two tasks
                coupling_f[(i, j)] = 0.5 * (coupling_f[(i, j)] + c)
            else:
                coupling_f[(i, j)] = c

    return self_cap_f, coupling_f


def build_name_map(nets: Iterable[str]) -> List[str]:
    return sorted(set(nets))


DEFAULT_DROP_NETS: Set[str] = set()
DEFAULT_THRESHOLD_F = 0.0
DEFAULT_COUPLING_THRESHOLD_RATIO = 0.01  # 1% of self capacitance by default
DEFAULT_DESIGN_NAME = "design"


def filter_couplings_by_threshold(
    coupling_f: Dict[Tuple[str, str], float],
    self_cap_f: Dict[str, float],
    coupling_threshold_ratio: float,
) -> Tuple[Dict[Tuple[str, str], float], int, int]:
    """Return couplings that clear the threshold plus removal stats.

    Returns:
        filtered: dictionary with surviving couplings
        removed_count: couplings dropped for falling below the threshold
        considered_count: couplings that had sufficient self capacitance data to evaluate
    """

    filtered: Dict[Tuple[str, str], float] = {}
    removed_count = 0
    considered_count = 0

    for (i, j), c in coupling_f.items():
        self_cap_i = abs(self_cap_f.get(i, 0.0))
        self_cap_j = abs(self_cap_f.get(j, 0.0))

        # Skip if either net has zero self capacitance to avoid division by zero
        if self_cap_i == 0.0 or self_cap_j == 0.0:
            continue

        considered_count += 1

        threshold_i = self_cap_i * coupling_threshold_ratio
        threshold_j = self_cap_j * coupling_threshold_ratio

        if c >= threshold_i and c >= threshold_j:
            filtered[(i, j)] = c
        else:
            removed_count += 1

    return filtered, removed_count, considered_count


def write_spef(
    out,
    *,
    design: str,
    nets: List[str],
    self_cap_f: Dict[str, float],
    coupling_f: Dict[Tuple[str, str], float],
) -> None:
    # Header
    now = _dt.datetime.now().strftime("%H:%M:%S %A %B %d, %Y")
    print('*SPEF "ieee 1481-1999"', file=out)
    print(f'*DESIGN "{design}"', file=out)
    print(f'*DATE "{now}"', file=out)
    print('*VENDOR "RWCap-to-SPEF"', file=out)
    print('*PROGRAM "rwcap_to_spef"', file=out)
    print('*VERSION "1.0"', file=out)
    print('*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"', file=out)
    print('*DIVIDER /', file=out)
    print('*DELIMITER :', file=out)
    print('*BUS_DELIMITER []', file=out)
    print('*T_UNIT 1 NS', file=out)
    print('*C_UNIT 1 PF', file=out)
    print('*R_UNIT 1 OHM', file=out)
    print('*L_UNIT 1 HENRY', file=out)
    print('', file=out)

    # Name map: 1-based indices
    print('*NAME_MAP', file=out)
    id_by_name = {name: i + 1 for i, name in enumerate(nets)}
    for name in nets:
        idx = id_by_name[name]
        print(f'*{idx} {name}', file=out)
    print('', file=out)

    # Emit per-net sections
    # Pre-build adjacency for couplings (thresholding already applied upstream)
    neighbors: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for (i, j), c in coupling_f.items():
        neighbors[i].append((j, c))
        neighbors[j].append((i, c))

    for net in nets:
        # Determine entries to emit
        cap_entries: List[Tuple[str, Optional[str], float]] = []

        # Emit couplings only when net is lexicographically smaller to avoid duplicates
        # Include GROUND couplings even though GROUND is not in the nets list
        emitted_sum = 0.0
        for (other, c) in neighbors.get(net, []):
            if other == "GROUND" or net < other:
                cap_entries.append((net, other, c))
                emitted_sum += c
        # Self-capacitance from RWCap
        net_self_cap_f = self_cap_f.get(net, 0.0)

        cap_entries.insert(0, (net, None, net_self_cap_f))

        # Convert to pF
        cap_entries_pf = [(a, b, v * 1e12) for (a, b, v) in cap_entries]
        # Total capacitance should be the self-capacitance value from RWCap, not the sum
        total_pf = net_self_cap_f * 1e12

        # Section header
        print(f'*D_NET *{id_by_name[net]} {total_pf:.12g}', file=out)
        print('*CONN', file=out)
        # Minimal single port so the net has a connection
        print(f'*P {net} B', file=out)
        print('*CAP', file=out)

        # Emit CAP entries
        idx = 1
        for (a, b, vpf) in cap_entries_pf:
            if b is None:
                # self-capacitance
                print(f'{idx} {a} {vpf:.12g}', file=out)
            else:
                print(f'{idx} {a} {b} {vpf:.12g}', file=out)
            idx += 1

        print('*RES', file=out)
        # No resistors (capacitance-only)
        print('*END', file=out)
        print('', file=out)

    return None


def _sanitize_window_id(input_path: Path) -> str:
    """Derive a window identifier from the RWCap filename."""
    window_id = input_path.stem
    # Handle double extensions like "W0.rwcap.out"
    if window_id.endswith(".rwcap"):
        window_id = window_id[: -len(".rwcap")]
    if not window_id:
        window_id = input_path.name.replace(".out", "").strip() or "window"
    return window_id


def convert_single_file(
    input_path: Path,
    output_dir: Path,
    *,
    drop_nets: Set[str] = DEFAULT_DROP_NETS,
    threshold_f: float = DEFAULT_THRESHOLD_F,
    coupling_threshold_ratio: float = DEFAULT_COUPLING_THRESHOLD_RATIO,
    design_name: Optional[str] = None,
) -> Dict[str, object]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    window_id = _sanitize_window_id(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{window_id}.spef"

    design = design_name or window_id or DEFAULT_DESIGN_NAME

    with input_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    self_cap_f, coupling_f = parse_rwcap(
        lines,
        drop_nets=set(drop_nets),
        threshold_f=threshold_f,
    )

    if coupling_f:
        new_coupling: Dict[Tuple[str, str], float] = {}
        for (i, j), v in coupling_f.items():
            keep_i = i in self_cap_f and i not in drop_nets
            keep_j = j in self_cap_f and j not in drop_nets
            # Special handling for GROUND couplings - include them if the other net has self-cap
            if i == "GROUND" and keep_j:
                new_coupling[(i, j)] = v
            elif j == "GROUND" and keep_i:
                new_coupling[(i, j)] = v
            elif keep_i or keep_j:
                new_coupling[(i, j)] = v
                continue
            # both ends lack self-cap entries; ignore
        coupling_f = new_coupling

    # Build net list (exclude dropped and GROUND)
    # GROUND only appears as coupling, not as a separate net
    regular_nets = set(self_cap_f.keys())
    if "GROUND" in regular_nets:
        regular_nets.remove("GROUND")

    nets = sorted(n for n in regular_nets if n not in drop_nets)
    if not nets:
        raise ValueError(f"No nets parsed in {input_path}; check RWCap output.")

    coupling_by_net: Dict[str, float] = defaultdict(float)
    for (i, j), v in coupling_f.items():
        coupling_by_net[i] += v
        coupling_by_net[j] += v
    total_self = sum(self_cap_f.get(net, 0.0) for net in nets)
    total_coupling = sum(coupling_by_net.get(net, 0.0) for net in nets)
    coupling_minus_self = total_coupling - total_self

    filtered_coupling_f, removed_couplings_count, coupling_cap_count = filter_couplings_by_threshold(
        coupling_f,
        self_cap_f,
        coupling_threshold_ratio,
    )
    retained_couplings_count = len(filtered_coupling_f)

    retained_coupling_by_net: Dict[str, float] = defaultdict(float)
    for (i, j), v in filtered_coupling_f.items():
        retained_coupling_by_net[i] += v
        retained_coupling_by_net[j] += v
    total_retained_coupling = sum(retained_coupling_by_net.get(net, 0.0) for net in nets)
    coupling_minus_self_retained = total_retained_coupling - total_self

    # Write SPEF
    with output_path.open("w", encoding="utf-8") as out:
        write_spef(
            out,
            design=design,
            nets=nets,
            self_cap_f=self_cap_f,
            coupling_f=filtered_coupling_f,
        )

    return {
        "total_coupling_pre_threshold": float(total_coupling),
        "coupling_minus_self_pre_threshold": float(coupling_minus_self),
        "total_coupling_post_threshold": float(total_retained_coupling),
        "coupling_minus_self_post_threshold": float(coupling_minus_self_retained),
        "window_id": window_id,
        "output_path": str(output_path),
        "removed_couplings_count": removed_couplings_count,
        "retained_couplings_count": retained_couplings_count,
        "coupling_capacitance_count": coupling_cap_count,
    }

def convert_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    coupling_threshold_ratio: float = DEFAULT_COUPLING_THRESHOLD_RATIO,
) -> int:
    if not input_dir.is_dir():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        return 1

    rwcap_files = sorted(f for f in input_dir.glob("*.out") if f.is_file())
    if not rwcap_files:
        print(f"No .out files found in {input_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    diff_records: List[Dict[str, object]] = []
    total_removed_couplings = 0
    total_retained_couplings = 0

    iterator = tqdm(rwcap_files, desc="Converting RWCAP", unit="file")

    for rwcap_file in iterator:
        try:
            result = convert_single_file(
                rwcap_file,
                output_dir,
                coupling_threshold_ratio=coupling_threshold_ratio,
            )
            total_coupling = result["total_coupling_pre_threshold"]
            diff = result["coupling_minus_self_pre_threshold"]
            ratio = (abs(diff) / total_coupling) if total_coupling else float("inf")
            removed_count = result["removed_couplings_count"]
            retained_count = result["retained_couplings_count"]
            total_caps = result["coupling_capacitance_count"]
            total_removed_couplings += removed_count
            total_retained_couplings += retained_count

            total_coupling_post = float(result["total_coupling_post_threshold"])
            diff_post = float(result["coupling_minus_self_post_threshold"])
            diff_records.append(
                {
                    "name": rwcap_file.name,
                    "diff_pre": float(diff),
                    "diff_post": diff_post,
                    "ratio_pre": float(ratio),
                    "ratio_post": (abs(diff_post) / total_coupling_post) if total_coupling_post else float("inf"),
                    "total_coupling_pre_threshold": float(total_coupling),
                    "total_coupling_post_threshold": total_coupling_post,
                    "removed_couplings_count": removed_count,
                    "retained_couplings_count": retained_count,
                    "total_coupling_capacitances": total_caps,
                }
            )

            # Report removed couplings for this file
            tqdm.write(
                f"[rwcap_to_spef] {result['window_id']}.spef: Retained {retained_count:,} coupling capacitances, removed {removed_count:,} below the {coupling_threshold_ratio:.1%} threshold"
            )

        except Exception as exc:  # pragma: no cover - diagnostics
            failures += 1
            tqdm.write(f"[rwcap_to_spef] Failed on {rwcap_file}: {exc}")

    iterator.close()

    if diff_records:
        sorted_by_ratio = sorted(diff_records, key=lambda r: r["ratio_pre"], reverse=True)

        def ratio_str(value: float) -> str:
            if not math.isfinite(value):
                return "∞"
            return f"{value:.2%}"

        print("[rwcap_to_spef] Largest relative discrepancies (|Σc-Σs| / Σc, includes removed couplings):")
        for record in sorted_by_ratio[:5]:
            print(
                f"  - {record['name']}: ratio={ratio_str(record['ratio_pre'])} "
                f"(|Σc-Σs|={abs(record['diff_pre']):.3e} F, Σc={record['total_coupling_pre_threshold']:.3e} F)"
            )
            if math.isfinite(record["ratio_post"]):
                print(
                    f"      ↳ After threshold: ratio={ratio_str(record['ratio_post'])}, "
                    f"Σc_retained={record['total_coupling_post_threshold']:.3e} F"
                )

    if failures:
        print(f"[rwcap_to_spef] {failures} file(s) failed", file=sys.stderr)
        return 2

    print(f"[rwcap_to_spef] Converted {len(rwcap_files)} files into {output_dir}")
    if total_retained_couplings or total_removed_couplings:
        print(
            f"[rwcap_to_spef] Coupling summary: {total_retained_couplings:,} retained / {total_removed_couplings:,} removed across {len(rwcap_files)} files ({coupling_threshold_ratio:.1%} threshold)"
        )

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Convert RWCap output to SPEF format")
    parser.add_argument("rwcap_dir", help="Directory containing RWCap .out files")
    parser.add_argument("spef_dir", help="Output directory for SPEF files")
    parser.add_argument(
        "--coupling-threshold",
        type=float,
        default=DEFAULT_COUPLING_THRESHOLD_RATIO,
        help=f"Skip coupling capacitances below this percentage of self capacitance (default: {DEFAULT_COUPLING_THRESHOLD_RATIO * 100:.1f}%%)",
    )

    args = parser.parse_args(argv)

    input_dir = Path(args.rwcap_dir).resolve()
    output_dir = Path(args.spef_dir).resolve()

    return convert_directory(
        input_dir,
        output_dir,
        coupling_threshold_ratio=args.coupling_threshold,
    )


if __name__ == "__main__":
    raise SystemExit(main())

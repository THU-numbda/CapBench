#!/usr/bin/env python3
"""
Convert OpenRCX SPEF outputs into simplified per-net SPEFs.

Each input SPEF is collapsed into a single capacitance entry per net while
preserving net-to-net coupling capacitors.  This dramatically reduces file
size while keeping the data needed by the CNN/GNN pipelines.

Usage (single file):
    python openrcx_to_simple_spef.py input.spef output.spef

Usage (directory):
    python openrcx_to_simple_spef.py datasets/nangate45/small/out_openrcx \\
        datasets/nangate45/small/labels_rwcap --glob \"W*.spef\"
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Tuple


def _normalize_ports_block(text: str) -> str:
    lines = text.splitlines()
    out: List[str] = []
    in_ports = False
    for ln in lines:
        s = ln.rstrip("\n")
        if s.startswith("*PORTS"):
            in_ports = True
            out.append(s)
            continue
        if in_ports:
            if s.startswith("*"):
                in_ports = False
                out.append(s)
                continue
            if s.strip() == "":
                out.append(s)
                continue
            out.append("*" + s)
            continue
        out.append(s)
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(out) + suffix


def _with_normalized_ports(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    if "*PORTS" not in text:
        return path
    normalized = _normalize_ports_block(text)
    if normalized == text:
        return path
    tmp = tempfile.NamedTemporaryFile(prefix="spef_norm_", suffix=".spef", delete=False)
    try:
        tmp.write(normalized.encode("utf-8", errors="ignore"))
        tmp.flush()
    finally:
        tmp.close()
    return tmp.name


def _unit_to_farads(unit: str) -> float:
    tbl = {
        "F": 1.0,
        "FARAD": 1.0,
        "PF": 1e-12,
        "NF": 1e-9,
        "UF": 1e-6,
        "MF": 1e-3,
        "KF": 1e3,
        "FF": 1e-15,
    }
    return tbl.get(unit.upper(), 1.0)


def parse_spef_components(path: str) -> Tuple[Dict[str, float], Dict[str, List[Tuple[str, float]]], float]:
    name_map: Dict[str, str] = {}
    ground_f: DefaultDict[str, float] = defaultdict(float)
    pair_coupling: Dict[Tuple[str, str], float] = {}
    nets_seen: set[str] = set()
    c_unit_factor = 1.0

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("*C_UNIT"):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    scale = float(parts[1])
                except ValueError:
                    scale = 1.0
                unit = parts[2]
                c_unit_factor = scale * _unit_to_farads(unit)
            i += 1
            continue
        if line.startswith("*NAME_MAP"):
            i += 1
            while i < len(lines):
                ln = lines[i].strip()
                if not ln or not ln.startswith("*") or ln.startswith("*D_NET"):
                    break
                parts = ln.split(maxsplit=1)
                if len(parts) == 2:
                    name_map[parts[0]] = parts[1]
                i += 1
            continue

        if line.startswith("*D_NET"):
            parts = line.split()
            raw = parts[1]
            net = name_map.get(raw, raw)
            nets_seen.add(net)
            i += 1
            while i < len(lines):
                ln = lines[i].strip()
                if ln.startswith("*CAP"):
                    i += 1
                    while i < len(lines):
                        entry = lines[i].strip()
                        if not entry or entry.startswith("*"):
                            break
                        fields = entry.split()
                        if len(fields) == 3:
                            try:
                                val = float(fields[2])
                            except ValueError:
                                val = 0.0
                            ground_f[net] += abs(val) * c_unit_factor
                        elif len(fields) == 4:
                            node_b = fields[2]
                            try:
                                val = float(fields[3])
                            except ValueError:
                                val = 0.0
                            value_f = abs(val) * c_unit_factor
                            if node_b.startswith("*") or value_f == 0.0:
                                ground_f[net] += value_f
                            else:
                                other = node_b
                                pair = tuple(sorted((net, other)))
                                if pair in pair_coupling:
                                    pair_coupling[pair] = 0.5 * (pair_coupling[pair] + value_f)
                                else:
                                    pair_coupling[pair] = value_f
                        i += 1
                    continue
                if ln.startswith("*END"):
                    break
                i += 1
        i += 1

    adjacency: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for (a, b), val in pair_coupling.items():
        if val == 0.0:
            continue
        adjacency[a].append((b, val))
        adjacency[b].append((a, val))
        nets_seen.add(a)
        nets_seen.add(b)

    # Ensure every seen net has a ground entry (possibly zero)
    for net in nets_seen:
        ground_f.setdefault(net, 0.0)
        adjacency.setdefault(net, [])

    return dict(ground_f), dict(adjacency), c_unit_factor


def write_simple_spef(
    out_path: str,
    *,
    design: str,
    nets: List[str],
    ground_f: Dict[str, float],
    adjacency: Dict[str, List[Tuple[str, float]]],
    c_unit: str,
    include_conn: bool,
) -> None:
    target_factor = _unit_to_farads(c_unit)

    nets_sorted = sorted(nets)
    id_by_name = {name: idx for idx, name in enumerate(nets_sorted, start=1)}

    now = _dt.datetime.now().strftime("%H:%M:%S %A %B %d, %Y")
    with open(out_path, "w", encoding="utf-8") as out:
        print('*SPEF "ieee 1481-1999"', file=out)
        print(f'*DESIGN "{design}"', file=out)
        print(f'*DATE "{now}"', file=out)
        print('*VENDOR "simple-spef"', file=out)
        print('*PROGRAM "spef_to_simple"', file=out)
        print('*VERSION "0.2"', file=out)
        print('*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"', file=out)
        print('*DIVIDER /', file=out)
        print('*DELIMITER :', file=out)
        print('*BUS_DELIMITER []', file=out)
        print('*T_UNIT 1 NS', file=out)
        print(f'*C_UNIT 1 {c_unit.upper()}', file=out)
        print('*R_UNIT 1 OHM', file=out)
        print('*L_UNIT 1 HENRY', file=out)
        print('', file=out)

        print('*NAME_MAP', file=out)
        for name in nets_sorted:
            print(f'*{id_by_name[name]} {name}', file=out)
        print('', file=out)

        for name in nets_sorted:
            idx = id_by_name[name]
            ground_val = ground_f.get(name, 0.0)
            couplings = adjacency.get(name, [])
            total = ground_val + sum(val for _, val in couplings)
            total_out = total / target_factor if target_factor else total
            print(f'*D_NET *{idx} {total_out:.12g}', file=out)
            print('*CONN', file=out)
            if include_conn:
                print(f'*P {name} B', file=out)
            print('*CAP', file=out)
            cap_index = 1
            ground_out = ground_val / target_factor if target_factor else ground_val
            print(f'{cap_index} {name} {ground_out:.12g}', file=out)
            cap_index += 1
            for other, value in couplings:
                value_out = value / target_factor if target_factor else value
                print(f'{cap_index} {name} {other} {value_out:.12g}', file=out)
                cap_index += 1
            print('*RES', file=out)
            print('*END', file=out)
            print('', file=out)


def _convert_file(
    input_path: Path,
    output_path: Path,
    *,
    design: str | None,
    unit: str,
    include_conn: bool,
) -> bool:
    tmp_path = _with_normalized_ports(str(input_path))
    try:
        ground_f, adjacency, _ = parse_spef_components(tmp_path)
    finally:
        if tmp_path != str(input_path) and os.path.basename(tmp_path).startswith("spef_norm_"):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    nets = sorted(set(ground_f) | set(adjacency))
    if not nets:
        print(f"[openrcx_to_simple] No nets found in {input_path}")
        return False

    design_name = design or input_path.stem
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_simple_spef(
        str(output_path),
        design=design_name,
        nets=nets,
        ground_f=ground_f,
        adjacency=adjacency,
        c_unit=unit,
        include_conn=include_conn,
    )
    return True


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Simplify OpenRCX SPEFs while preserving net-to-net coupling capacitors.")
    ap.add_argument("input", help="Input directory containing OpenRCX SPEFs")
    ap.add_argument("output", help="Output directory for simplified SPEFs")
    ap.add_argument("--unit", default="PF", help="Capacitance unit for output (default: PF)")
    ap.add_argument("--glob", default="*.spef", help="Glob to select files inside the input directory")
    ap.add_argument(
        "--no-conn",
        action="store_true",
        help="Skip emitting *CONN/*P entries (default: emit connections for each net)",
    )
    args = ap.parse_args(argv)

    include_conn = not args.no_conn
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.is_dir():
        print(f"[openrcx_to_simple] Input directory not found: {input_path}")
        return 1

    output_path.mkdir(parents=True, exist_ok=True)
    files = sorted(input_path.glob(args.glob))
    if not files:
        print(f"[openrcx_to_simple] No files matching {args.glob} under {input_path}")
        return 1

    converted = 0
    for spef_file in files:
        dest = output_path / spef_file.name
        if _convert_file(
            spef_file,
            dest,
            design=spef_file.stem,
            unit=args.unit,
            include_conn=include_conn,
        ):
            converted += 1

    print(f"[openrcx_to_simple] Converted {converted}/{len(files)} files into {output_path}")
    return 0 if converted == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())

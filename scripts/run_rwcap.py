#!/usr/bin/env python3
"""Parallel RWCap runner with tqdm progress reporting."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover CAP3D windows and run RWCap with optional parallelism."
    )
    parser.add_argument(
        "--process-nodes",
        type=str,
        default="",
        help="Comma-separated list of process nodes to include (default: all).",
    )
    parser.add_argument(
        "--sizes",
        type=str,
        default="",
        help="Comma-separated list of dataset sizes to include (default: all).",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Number of parallel RWCap processes to spawn (default: 1).",
    )
    parser.add_argument(
        "--datasets-root",
        type=Path,
        default=Path("datasets"),
        help="Root directory containing dataset folders (default: datasets/).",
    )
    return parser.parse_args()


def check_rwcap_env() -> str:
    rwcap_bin = os.environ.get("RWCAP_BIN")
    if not rwcap_bin:
        sys.exit("ERROR: RWCAP_BIN environment variable is not set.")
    binary_path = Path(rwcap_bin)
    if not binary_path.exists():
        sys.exit(f"ERROR: RWCap binary not found: {binary_path}")
    if not os.access(binary_path, os.X_OK):
        sys.exit(f"ERROR: RWCap binary is not executable: {binary_path}")
    return str(binary_path)


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        minutes, secs = divmod(seconds, 60)
        return f"{minutes}m{secs}s"
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    return f"{hours}h{minutes}m"


def parse_filters(csv: str) -> Optional[set[str]]:
    csv = csv.strip()
    if not csv:
        return None
    return {token.strip() for token in csv.split(",") if token.strip()}


def dataset_info_from_path(path: Path) -> Tuple[Optional[str], Optional[str]]:
    parts = path.resolve().parts
    for idx, part in enumerate(parts):
        if part == "datasets" and idx + 2 < len(parts):
            return parts[idx + 1], parts[idx + 2]
    return None, None


def matches_filter(value: Optional[str], allowed: Optional[set[str]]) -> bool:
    if allowed is None:
        return True
    if value is None:
        return False
    return value in allowed


def discover_datasets(root: Path) -> List[Path]:
    if not root.is_dir():
        sys.exit(f"ERROR: datasets root not found: {root}")
    return sorted(root.rglob("windows.yaml"))


def find_cap3d_files(dataset_path: Path) -> List[Path]:
    cap3d_dir = dataset_path / "cap3d"
    if not cap3d_dir.is_dir():
        return []
    return sorted(cap3d_dir.glob("*.cap3d"))


def out_file_for_cap3d(cap3d_file: Path) -> Path:
    return cap3d_file.parent.parent / "out_rwcap" / f"{cap3d_file.stem}.out"


def log_file_for_cap3d(cap3d_file: Path) -> Path:
    dataset_dir = cap3d_file.parent.parent
    return dataset_dir / "log_rwcap" / f"{cap3d_file.stem}.log"


def run_rwcap(rwcap_bin: str, cap3d_file: Path) -> Tuple[bool, Path]:
    out_file = out_file_for_cap3d(cap3d_file)
    log_file = log_file_for_cap3d(cap3d_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        rwcap_bin,
        "-n",
        "32",
        "-p",
        "0.005",
        "-f",
        str(cap3d_file),
        "--out-file",
        str(out_file),
    ]

    with log_file.open("w") as log_handle:
        result = subprocess.run(cmd, stdout=log_handle, stderr=subprocess.STDOUT)

    return result.returncode == 0, log_file


def collect_tasks(
    datasets_root: Path,
    process_filter: Optional[set[str]],
    size_filter: Optional[set[str]],
) -> Tuple[List[Path], int, int]:
    total_candidates = 0
    skipped = 0
    tasks: List[Path] = []

    for yaml_path in discover_datasets(datasets_root):
        dataset_dir = yaml_path.parent
        process_node, size = dataset_info_from_path(dataset_dir)
        if not matches_filter(process_node, process_filter):
            continue
        if not matches_filter(size, size_filter):
            continue

        cap3d_files = find_cap3d_files(dataset_dir)
        for cap3d_file in cap3d_files:
            total_candidates += 1
            out_file = out_file_for_cap3d(cap3d_file)
            if out_file.exists():
                skipped += 1
                continue
            tasks.append(cap3d_file)

    return tasks, total_candidates, skipped


def main() -> None:
    args = parse_args()
    rwcap_bin = check_rwcap_env()

    if args.jobs < 1:
        sys.exit("ERROR: --jobs must be >= 1.")

    process_filter = parse_filters(args.process_nodes)
    size_filter = parse_filters(args.sizes)

    tasks, total_candidates, skipped = collect_tasks(
        args.datasets_root, process_filter, size_filter
    )

    remaining = len(tasks)
    print(f"Discovered {total_candidates} CAP3D files after filtering.")
    print(f"Already solved (out_rwcap exists): {skipped}")
    print(f"Remaining files to process: {remaining}")

    if remaining == 0:
        print("All CAP3D files already have RWCap outputs. Nothing to do.")
        return

    start_time = time.time()
    successes = 0
    failures = 0

    with ThreadPoolExecutor(max_workers=args.jobs) as executor, tqdm(
        total=remaining, desc="RWCap windows", unit="win"
    ) as progress:
        future_to_cap3d = {
            executor.submit(run_rwcap, rwcap_bin, cap3d_file): cap3d_file
            for cap3d_file in tasks
        }

        for future in as_completed(future_to_cap3d):
            cap3d_file = future_to_cap3d[future]
            ok, log_path = future.result()
            if ok:
                successes += 1
            else:
                failures += 1
                tqdm.write(
                    f"[WARN] RWCap failed for {cap3d_file.name}; see log {log_path}"
                )
            progress.update(1)

    duration = time.time() - start_time
    print("\n=== RWCap Processing Summary ===")
    print(f"Total CAP3D files considered: {total_candidates}")
    print(f"Total files processed: {remaining}")
    print(f"Total files skipped: {skipped}")
    print(f"Successful: {successes}")
    print(f"Failed: {failures}")
    print(f"Total time: {format_duration(duration)}")

    if failures > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

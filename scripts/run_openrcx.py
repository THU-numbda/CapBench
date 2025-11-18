#!/usr/bin/env python3
"""
run_openrcx.py
==============

Batch driver that discovers DEF windows under ``datasets/`` and runs an
OpenRCX/OpenROAD extraction for every window that does not yet have a
corresponding SPEF in ``out_openrcx/``.

The script is intentionally lightweight: it only handles discovery, basic
book‑keeping, and command construction.  By default it auto-generates a minimal
OpenROAD launcher (``scripts/_openrcx_launcher.sh``) that expects the ``openroad``
binary to be present in the current environment. To override the launcher with
your own container wrapper, set the ``OPENROAD_LAUNCH_SCRIPT`` environment
variable to point at your script before running this tool.

The launcher is expected to understand the following CLI arguments:

    --tech-node <node>      Process node (e.g., nangate45, asap7, sky130hd)
    --def <path.def>        DEF window to process
    --lef <tech.lef>        Technology LEF file for the node
    --tech-yaml <stack>     (Optional) stack YAML describing layers
    --layermap <map>        (Optional) KLayout layermap
    --gds <path.gds>        (Optional) matching GDS window if available
    --out-spef <path.spef>  Destination SPEF file inside out_openrcx/
    --rcx-script <tcl>      (Optional) custom RCX TCL to source inside OpenROAD

Adjust the launcher to consume these switches and invoke OpenROAD accordingly.

Example usage
-------------

    export OPENROAD_LAUNCH_SCRIPT=$HOME/bin/openroad_run.sh
    python scripts/run_openrcx.py --process-nodes nangate45 --sizes small

The command above scans ``datasets/nangate45/small/def/*.def`` and runs the
launcher for every missing SPEF under ``datasets/nangate45/small/out_openrcx``.
"""

from __future__ import annotations

import argparse
import os
import shlex
import stat
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Tuple


DATASETS_ROOT = Path("datasets")
RCX_ROOT = Path("openrcx")
DEFAULT_LAUNCHER_ENV = "OPENROAD_LAUNCH_SCRIPT"
DEFAULT_LAUNCHER_NAME = "_openrcx_launcher.sh"
REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINER_MOUNT_DEFAULT = Path("/workspace")


@dataclass(frozen=True)
class WindowDef:
    """Metadata for a DEF window discovered under datasets/."""

    process_node: str
    size: str
    def_path: Path
    dataset_dir: Path  # e.g., datasets/nangate45/small

    @property
    def window_id(self) -> str:
        return self.def_path.stem

    @property
    def out_dir(self) -> Path:
        return self.dataset_dir / "out_openrcx"

    @property
    def spef_path(self) -> Path:
        return self.out_dir / f"{self.window_id}.spef"

    @property
    def gds_path(self) -> Optional[Path]:
        gds_candidate = self.dataset_dir / "gds" / f"{self.window_id}.gds"
        return gds_candidate if gds_candidate.exists() else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch OpenRCX runner for window DEF files."
    )
    parser.add_argument(
        "--datasets-root",
        type=Path,
        default=DATASETS_ROOT,
        help="Root directory containing datasets/<node>/<size>/def (default: %(default)s)",
    )
    parser.add_argument(
        "--rcx-root",
        type=Path,
        default=RCX_ROOT,
        help="Root directory containing per-node RCX collateral (default: %(default)s).",
    )
    parser.add_argument(
        "--rcx-script",
        type=Path,
        default=None,
        help="OpenROAD TCL deck for RCX (default: <rcx-root>/setRC.tcl if present).",
    )
    parser.add_argument(
        "--process-nodes",
        type=lambda s: [p.strip() for p in s.split(",") if p.strip()],
        default=None,
        help="Comma-separated list of process nodes to process (default: all).",
    )
    parser.add_argument(
        "--sizes",
        type=lambda s: [p.strip() for p in s.split(",") if p.strip()],
        default=None,
        help="Comma-separated list of dataset sizes to process (default: all).",
    )
    parser.add_argument(
        "--launcher-env",
        default=DEFAULT_LAUNCHER_ENV,
        help="Environment variable that stores the OpenROAD launcher script (default: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after processing N windows (useful for smoke tests).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run OpenRCX even if a SPEF already exists.",
    )
    parser.add_argument(
        "--use-docker",
        action="store_true",
        help="Run each extraction inside a docker container (openroad/orfs:latest).",
    )
    parser.add_argument(
        "--docker-image",
        default="openroad/orfs:latest",
        help="Docker image to use when --use-docker is enabled (default: %(default)s).",
    )
    parser.add_argument(
        "--docker-mount",
        type=Path,
        default=CONTAINER_MOUNT_DEFAULT,
        help="Mount point inside the container for the repository (default: %(default)s).",
    )
    return parser.parse_args()


def discover_windows(
    datasets_root: Path,
    nodes_filter: Optional[Sequence[str]],
    sizes_filter: Optional[Sequence[str]],
) -> Iterable[WindowDef]:
    """Yield WindowDef objects discovered under datasets_root."""
    datasets_root = datasets_root.resolve()
    if not datasets_root.exists():
        raise FileNotFoundError(f"Datasets root not found: {datasets_root}")

    for node_dir in sorted(p for p in datasets_root.iterdir() if p.is_dir()):
        node = node_dir.name
        if nodes_filter and node not in nodes_filter:
            continue

        for size_dir in sorted(p for p in node_dir.iterdir() if p.is_dir()):
            size = size_dir.name
            if sizes_filter and size not in sizes_filter:
                continue

            def_dir = size_dir / "def"
            if not def_dir.is_dir():
                continue

            for def_path in sorted(def_dir.glob("W*.def")):
                yield WindowDef(
                    process_node=node,
                    size=size,
                    def_path=def_path.resolve(),
                    dataset_dir=size_dir.resolve(),
                )


DEFAULT_LAUNCHER_TEMPLATE = """#!/bin/bash
set -euo pipefail

# Default OpenROAD/OpenRCX launcher generated by run_openrcx.py.
# It expects the openroad binary to be available in the current PATH.

function usage() {
  cat <<'EOF'
Usage: $0 [args]
  --tech-node <node>
  --def <window.def>
  --lef <tech.lef>
  --tech-yaml <stack.yaml>
  --layermap <map>
  --gds <window.gds>
  --out-spef <output.spef>   (required)
  --rcx-script <rcx.tcl>
EOF
}

TECH_NODE=""
DEF_FILE=""
LEF_FILES=()
TECH_YAML=""
LAYERMAP=""
GDS_FILE=""
OUT_SPEF=""
RCX_SCRIPT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tech-node) TECH_NODE="$2"; shift 2;;
    --def) DEF_FILE="$2"; shift 2;;
    --lef) LEF_FILES+=("$2"); shift 2;;
    --tech-yaml) TECH_YAML="$2"; shift 2;;
    --layermap) LAYERMAP="$2"; shift 2;;
    --gds) GDS_FILE="$2"; shift 2;;
    --out-spef) OUT_SPEF="$2"; shift 2;;
    --rcx-script) RCX_SCRIPT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1;;
  esac
done

if [[ -z "${DEF_FILE}" || -z "${OUT_SPEF}" ]]; then
  echo "[openrcx-launcher] --def and --out-spef are required" >&2
  exit 1
fi

# Export helper vars so custom RCX TCL can reuse them.
export OPENRCX_TECH_NODE="${TECH_NODE}"
export OPENRCX_TECH_YAML="${TECH_YAML}"
export OPENRCX_LAYERMAP="${LAYERMAP}"
export OPENRCX_LEF_LIST="${LEF_FILES[*]}"
export OPENRCX_DEF="${DEF_FILE}"
export OPENRCX_GDS="${GDS_FILE}"
export OPENRCX_OUT_SPEF="${OUT_SPEF}"

TCL_SCRIPT="$(mktemp)"
trap 'rm -f "$TCL_SCRIPT"' EXIT

OPENROAD_BIN="${OPENROAD_BIN:-/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad}"

{
  for lef in "${LEF_FILES[@]}"; do
    printf 'read_lef %s\n' "${lef}"
  done
  if [[ -n "${GDS_FILE}" && -f "${GDS_FILE}" ]]; then
    printf 'if { [info commands read_gds] != "" } {\n'
    printf '  read_gds %s\n' "${GDS_FILE}"
    printf '} else {\n'
    printf '  puts "WARNING: read_gds command unavailable; skipping GDS load"\n'
    printf '}\n'
  fi
  printf 'read_def %s\n' "${DEF_FILE}"
  if [[ -n "${RCX_SCRIPT}" && -f "${RCX_SCRIPT}" ]]; then
    printf 'source %s\n' "${RCX_SCRIPT}"
  else
    printf 'puts "ERROR: no RCX script provided; cannot run extraction"\n'
    printf 'exit 1\n'
  fi
  printf 'exit\n'
} > "${TCL_SCRIPT}"

echo "[openrcx-launcher] running openroad on ${DEF_FILE}"
"${OPENROAD_BIN}" -exit "${TCL_SCRIPT}"
"""


def resolve_launcher(env_name: str) -> Path:
    value = os.environ.get(env_name)
    if not value:
        launcher = Path(__file__).resolve().with_name(DEFAULT_LAUNCHER_NAME)
        if not launcher.exists():
            print(f"[INFO] {env_name} not set. Generating default launcher at {launcher}")
            launcher.write_text(textwrap.dedent(DEFAULT_LAUNCHER_TEMPLATE), encoding="utf-8")
            launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
        else:
            launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
        return launcher

    launcher = Path(value).expanduser()
    if not launcher.exists():
        raise FileNotFoundError(
            f"OpenROAD launcher script not found: {launcher} (from ${env_name})"
        )
    if not os.access(launcher, os.X_OK):
        raise PermissionError(f"Launcher is not executable: {launcher}")
    return launcher


def build_path_mapper(container_mount: Path) -> Callable[[Path], Path]:
    repo_root = REPO_ROOT.resolve()
    container_mount = container_mount.resolve()

    def mapper(path: Path) -> Path:
        path = path.resolve()
        try:
            rel = path.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError(f"Path {path} is outside repository root {repo_root}") from exc
        return container_mount / rel

    return mapper


def tech_files(rcx_node_dir: Path) -> Tuple[List[Path], Optional[Path]]:
    """Return list of LEFs/TLEFs and default RCX script for a node."""
    ordered_lefs: List[Path] = []
    seen = set()

    def append_unique(paths: Iterable[Path]):
        for path in paths:
            if path not in seen:
                ordered_lefs.append(path)
                seen.add(path)

    # Technology files (.tlef) must be loaded before cell LEFs.
    append_unique(sorted(rcx_node_dir.glob("*.tlef")))
    append_unique(sorted(rcx_node_dir.glob("*tech*.lef")))
    append_unique(sorted(rcx_node_dir.glob("*macro*.lef")))
    append_unique(sorted(rcx_node_dir.glob("*.lef")))

    rcx_script = rcx_node_dir / "setRC.tcl"
    if not rcx_script.exists():
        rcx_script = None

    return ordered_lefs, rcx_script



def build_command(
    launcher: Path,
    window: WindowDef,
    lefs: List[Path],
    rcx_script: Optional[Path],
    path_mapper: Optional[Callable[[Path], Path]] = None,
) -> List[str]:

    def map_path(p: Optional[Path]) -> Optional[str]:
        if p is None:
            return None
        mapped = path_mapper(p) if path_mapper else p
        return str(mapped)

    cmd: List[str] = [str(path_mapper(launcher) if path_mapper else launcher)]

    cmd.extend([
        "--tech-node",
        window.process_node,
    ])

    cmd.extend([
        "--def",
        map_path(window.def_path),
        "--out-spef",
        map_path(window.spef_path),
    ])

    for lef_path in lefs:
        cmd.extend(["--lef", map_path(lef_path)])
    if window.gds_path:
        cmd.extend(["--gds", map_path(window.gds_path)])
    if rcx_script:
        cmd.extend(["--rcx-script", map_path(rcx_script.resolve())])

    return cmd


def run_command(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True)


def format_duration(seconds: float) -> str:
    total_seconds = int(round(seconds))
    hours, rem = divmod(total_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes or hours:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return "".join(parts)


def main() -> None:
    args = parse_args()

    launcher = resolve_launcher(args.launcher_env)

    path_mapper = build_path_mapper(args.docker_mount) if args.use_docker else None

    processed = 0
    skipped = 0
    failures: List[Tuple[WindowDef, Exception]] = []
    start_time = time.time()

    for window in discover_windows(args.datasets_root, args.process_nodes, args.sizes):
        if args.limit is not None and processed >= args.limit:
            break

        if window.spef_path.exists() and not args.force:
            skipped += 1
            continue

        window.out_dir.mkdir(parents=True, exist_ok=True)

        rcx_node_dir = (args.rcx_root / window.process_node).resolve()
        lefs, default_rcx_script = tech_files(rcx_node_dir)
        rcx_script = args.rcx_script.resolve() if args.rcx_script else default_rcx_script

        cmd = build_command(launcher, window, lefs, rcx_script, path_mapper)

        if args.use_docker:
            inner = " ".join(shlex.quote(part) for part in cmd)
            docker_cmd = [
                "docker",
                "run",
                "--rm",
                "-u",
                f"{os.getuid()}:{os.getgid()}",
                "-v",
                f"{REPO_ROOT.resolve()}:{args.docker_mount.resolve()}:Z",
                args.docker_image,
                "bash",
                "-lc",
                f"cd {shlex.quote(str(args.docker_mount))} && OPENROAD_BIN=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad {inner}",
            ]
            exec_cmd = docker_cmd
        else:
            exec_cmd = cmd

        print(f"[INFO] {window.window_id}: running OpenRCX for {window.process_node}/{window.size}")
        if args.dry_run:
            print("       DRY-RUN:", " ".join(exec_cmd))
            processed += 1
            continue

        try:
            run_command(exec_cmd)
            processed += 1
        except subprocess.CalledProcessError as exc:
            failures.append((window, exc))
            print(f"[ERROR] {window.window_id}: OpenRCX failed (exit {exc.returncode})", file=sys.stderr)

    print("\nSummary")
    print("-------")
    print(f"Processed : {processed}")
    print(f"Skipped   : {skipped}")
    print(f"Failures  : {len(failures)}")

    if failures:
        for window, exc in failures:
            print(f"  - {window.window_id} ({window.process_node}/{window.size}): {exc}", file=sys.stderr)
        sys.exit(1)

    elapsed = format_duration(time.time() - start_time)
    print("\n[INFO] === OpenRCX Processing Summary ===")
    print(f"[INFO] Total windows processed: {processed}")
    print(f"[INFO] [OK] Successful: {processed}/{processed}")
    print(f"[INFO] Total time: {elapsed}")


if __name__ == "__main__":
    main()

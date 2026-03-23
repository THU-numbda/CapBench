"""Console entrypoint for the standardized CapBench library/CLI surface."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from . import __version__
from .datasets import get_dataset_info, get_dataset_infos, install_dataset, list_datasets
from .paths import get_cache_dir
from .visualize import visualize_cap3d, visualize_density, visualize_point_cloud


_DATASET_SIZE_ORDER = {
    "small": 0,
    "medium": 1,
    "large": 2,
}


def _dataset_status_rows(info: dict[str, object]) -> list[tuple[str, str]]:
    artifacts = sorted(str(artifact) for artifact in info["artifacts"])
    status = dict(info["artifact_status"])
    return [
        (
            artifact,
            "ready" if status.get(artifact) else "missing",
        )
        for artifact in artifacts
    ]


def _print_dataset_status(info: dict[str, object]) -> None:
    title = f"Dataset state: {info['id']}"
    workspace = info["workspace_root"] or "not installed"
    rows = _dataset_status_rows(info)

    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        print(title)
        print(f"  Cache root: {info['cache_root']}")
        print(f"  Workspace:  {workspace}")
        headers = ("Artifact", "Status")
        widths = [len(header) for header in headers]
        for row in rows:
            for index, value in enumerate(row):
                widths[index] = max(widths[index], len(value))
        header_row = " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
        separator = "-+-".join("-" * width for width in widths)
        print(header_row)
        print(separator)
        for row in rows:
            print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
        return

    console = Console()
    table = Table(title=title)
    table.add_column("Artifact")
    table.add_column("Status")
    for row in rows:
        table.add_row(*row)
    console.print(table)
    console.print(f"[bold]Cache root:[/bold] {info['cache_root']}")
    console.print(f"[bold]Workspace:[/bold] {workspace}")


def _print_dataset_list() -> None:
    print(f"Cache root: {get_cache_dir()}")
    grouped: dict[str, dict[str, object]] = {}
    for info in list_datasets():
        dataset_id = str(info["id"])
        process_node = str(info["process_node"])
        size = dataset_id.split("/", 1)[1] if "/" in dataset_id else dataset_id
        group = grouped.setdefault(
            process_node,
            {
                "process_node": process_node,
                "version": info["version"],
                "sizes": [],
            },
        )
        group["sizes"].append(size)
    for process_node in sorted(grouped):
        group = grouped[process_node]
        sizes = ", ".join(
            sorted(
                (str(size) for size in group["sizes"]),
                key=lambda size: (_DATASET_SIZE_ORDER.get(size.lower(), 999), size),
            )
        )
        print(f"- {process_node} (version={group['version']}, sizes={sizes})")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capbench",
        description="CapBench library CLI for cache-backed datasets, dataloaders, and visualization.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    datasets_parser = subparsers.add_parser("datasets", help="Dataset download and cache inspection commands.")
    datasets_subparsers = datasets_parser.add_subparsers(dest="datasets_command", required=True)

    datasets_subparsers.add_parser("list", help="List registered datasets.")

    datasets_info = datasets_subparsers.add_parser("info", help="Show metadata and cache status for one dataset id or one PDK selector.")
    datasets_info.add_argument("dataset")

    datasets_install = datasets_subparsers.add_parser(
        "install",
        help="Download one exact dataset id or an entire PDK into the shared cache.",
    )
    datasets_install.add_argument("dataset")
    datasets_install.add_argument("--source", default=None, help="Override the configured dataset source name.")

    visualize_parser = subparsers.add_parser("visualize", help="Visualization commands for cached artifacts.")
    visualize_subparsers = visualize_parser.add_subparsers(dest="visualize_command", required=True)

    density_parser = visualize_subparsers.add_parser("density", help="Visualize one density-map window.")
    density_parser.add_argument("--dataset", default="nangate45/small", help="Registered dataset id or explicit dataset path.")
    density_parser.add_argument("--window", required=True, help="Window id, for example W0.")
    density_parser.add_argument("viewer_args", nargs=argparse.REMAINDER, help="Extra args passed through to the viewer.")

    point_parser = visualize_subparsers.add_parser("point-cloud", help="Visualize one point-cloud window.")
    point_parser.add_argument("--dataset", default="nangate45/small", help="Registered dataset id or explicit dataset path.")
    point_parser.add_argument("--window", required=True, help="Window id, for example W0.")
    point_parser.add_argument("viewer_args", nargs=argparse.REMAINDER, help="Extra args passed through to the viewer.")

    cap3d_parser = visualize_subparsers.add_parser("cap3d", help="Visualize one CAP3D window.")
    cap3d_parser.add_argument("--dataset", default="nangate45/small", help="Registered dataset id or explicit dataset path.")
    cap3d_parser.add_argument("--window", required=True, help="Window id, for example W0.")
    cap3d_parser.add_argument("viewer_args", nargs=argparse.REMAINDER, help="Extra args passed through to the viewer.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "datasets":
        if args.datasets_command == "list":
            _print_dataset_list()
            return 0
        if args.datasets_command == "info":
            infos = get_dataset_infos(args.dataset)
            payload: object = infos[0] if len(infos) == 1 else infos
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.datasets_command == "install":
            path = install_dataset(
                args.dataset,
                source=args.source,
            )
            for info in get_dataset_infos(args.dataset):
                _print_dataset_status(info)
            print(path)
            return 0

    if args.command == "visualize":
        if args.visualize_command == "density":
            visualize_density(args.dataset, window_id=args.window, extra_args=args.viewer_args)
            return 0
        if args.visualize_command == "point-cloud":
            visualize_point_cloud(args.dataset, window_id=args.window, extra_args=args.viewer_args)
            return 0
        if args.visualize_command == "cap3d":
            visualize_cap3d(args.dataset, window_id=args.window, extra_args=args.viewer_args)
            return 0

    parser.error("Unhandled command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

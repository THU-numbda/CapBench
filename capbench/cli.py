"""Console entrypoint for the standardized CapBench library/CLI surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from . import __version__
from .datasets import ensure_dataset, get_dataset_info, list_datasets, materialize_dataset, preprocess_dataset
from .dev import list_dev_tools, run_dev_tool
from .paths import get_cache_dir
from .visualize import visualize_cap3d, visualize_density, visualize_point_cloud


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capbench",
        description="CapBench library CLI for cache-backed datasets, dataloaders, visualization, and dev tools.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    datasets_parser = subparsers.add_parser("datasets", help="Dataset download, cache, and materialization commands.")
    datasets_subparsers = datasets_parser.add_subparsers(dest="datasets_command", required=True)

    datasets_subparsers.add_parser("list", help="List registered datasets.")

    datasets_info = datasets_subparsers.add_parser("info", help="Show metadata and cache status for one dataset.")
    datasets_info.add_argument("dataset")

    datasets_ensure = datasets_subparsers.add_parser("ensure", help="Download a dataset into the shared cache.")
    datasets_ensure.add_argument("dataset")
    datasets_ensure.add_argument("--artifact", nargs="*", default=(), help="Required artifacts to verify or generate.")
    datasets_ensure.add_argument("--source", default=None, help="Override the configured dataset source name.")

    datasets_materialize = datasets_subparsers.add_parser(
        "materialize",
        help="Create a workspace symlink for a cached dataset (defaults to ./datasets/<dataset>).",
    )
    datasets_materialize.add_argument("dataset")
    datasets_materialize.add_argument("--artifact", nargs="*", default=(), help="Required artifacts to verify or generate.")
    datasets_materialize.add_argument("--source", default=None, help="Override the configured dataset source name.")
    datasets_materialize.add_argument("--to", type=Path, default=None, help="Destination path for the workspace symlink.")

    datasets_preprocess = datasets_subparsers.add_parser(
        "preprocess",
        help="Generate missing cache artifacts such as density maps, binary masks, or point clouds.",
    )
    datasets_preprocess.add_argument("dataset")
    datasets_preprocess.add_argument("--artifact", nargs="+", required=True, help="Artifacts to generate.")

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

    dev_parser = subparsers.add_parser("dev", help="Developer-only dataset authoring and maintenance tools.")
    dev_subparsers = dev_parser.add_subparsers(dest="dev_command", required=True)
    dev_subparsers.add_parser("list", help="List developer-only tools.")
    for tool_name, description in list_dev_tools().items():
        tool_parser = dev_subparsers.add_parser(tool_name, help=description)
        tool_parser.add_argument("tool_args", nargs=argparse.REMAINDER, help="Arguments passed through to the legacy tool.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "datasets":
        if args.datasets_command == "list":
            print(f"Cache root: {get_cache_dir()}")
            for info in list_datasets():
                print(f"- {info['id']} (version={info['version']}, process_node={info['process_node']})")
            return 0
        if args.datasets_command == "info":
            print(json.dumps(get_dataset_info(args.dataset), indent=2, sort_keys=True))
            return 0
        if args.datasets_command == "ensure":
            path = ensure_dataset(args.dataset, artifacts=args.artifact, source=args.source)
            print(path)
            return 0
        if args.datasets_command == "materialize":
            path = materialize_dataset(args.dataset, destination=args.to, artifacts=args.artifact, source=args.source)
            print(path)
            return 0
        if args.datasets_command == "preprocess":
            path = preprocess_dataset(args.dataset, artifacts=args.artifact)
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

    if args.command == "dev":
        if args.dev_command == "list":
            for name, description in list_dev_tools().items():
                print(f"- {name}: {description}")
            return 0
        run_dev_tool(args.dev_command, args.tool_args)
        return 0

    parser.error("Unhandled command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

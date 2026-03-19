#!/usr/bin/env python3
"""Report how many windows contain any elements on each dataset layer.

This helps identify layers that are always empty or nearly empty across a
dataset and may be candidates for removal from model inputs.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from window_tools.cap3d_parser import StreamingCap3DParser


LEGACY_WINDOW_SIZE = 200
LEGACY_WINDOW_STRIDE = 160
LEGACY_WINDOW_MARGIN = 180


@dataclass
class LayerCoverage:
    """Per-layer coverage counters."""

    windows_listing_layer: int = 0
    windows_with_arrays: int = 0
    windows_with_elements: int = 0
    window_ids_with_elements: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Analysis outcome for a dataset path."""

    dataset_format: str
    analyzed_path: Path
    total_windows: int
    layer_coverage: Dict[str, LayerCoverage]
    notes: List[str]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Count how many windows contain any elements on each layer in a dataset. "
            "Supports CapBench per-window density/id-map datasets, legacy CNN-Cap datasets, and CAP3D windows."
        )
    )
    parser.add_argument(
        "dataset",
        type=Path,
        help=(
            "Dataset root or concrete input directory. Examples: datasets/nangate45/small, "
            "datasets/nangate45/small/density_maps, datasets/nangate45/small/binary-masks, "
            "datasets/cnncap_small, datasets/nangate45/small/cap3d."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("auto", "density", "legacy", "cap3d"),
        default="auto",
        help="Force a specific dataset format. Defaults to auto-detection.",
    )
    parser.add_argument(
        "--legacy-layers",
        help=(
            "Legacy CNN-Cap only: choose the layer stack to analyze "
            "(for example: POLY1_MET1_MET2)."
        ),
    )
    parser.add_argument(
        "--warn-below",
        type=float,
        default=0.0,
        help=(
            "If > 0, print an extra summary of layers whose window coverage ratio is below "
            "this threshold (0.0-1.0)."
        ),
    )
    return parser.parse_args()


def _sorted_npz_files(path: Path) -> List[Path]:
    return sorted(path.glob("*.npz"))


def _sorted_cap3d_files(path: Path) -> List[Path]:
    return sorted(path.glob("*.cap3d"))


def _npz_has_layers_key(path: Path) -> bool:
    try:
        with np.load(path, allow_pickle=True) as data:
            return "layers" in data
    except Exception:
        return False


def _discover_legacy_layer_stacks(dataset_path: Path) -> List[str]:
    label_dir = dataset_path / "label"
    if not label_dir.exists():
        return []

    suffixes = (
        "_total_train.txt",
        "_total_val.txt",
        "_env_train.txt",
        "_env_val.txt",
    )

    stacks = set()
    for label_path in label_dir.glob("*.txt"):
        name = label_path.name
        for suffix in suffixes:
            if name.endswith(suffix):
                stacks.add(name[: -len(suffix)])
                break

    return sorted(stacks)


def _detect_dataset_format(dataset_path: Path) -> Tuple[str, Path]:
    dataset_path = dataset_path.resolve()

    direct_npz_files = _sorted_npz_files(dataset_path)
    if direct_npz_files:
        if _npz_has_layers_key(direct_npz_files[0]):
            return "density", dataset_path
        if (dataset_path / "label").exists():
            return "legacy", dataset_path

    density_dir = dataset_path / "density_maps"
    if density_dir.exists() and density_dir.is_dir():
        density_files = _sorted_npz_files(density_dir)
        if density_files and _npz_has_layers_key(density_files[0]):
            return "density", density_dir

    binary_masks_dir = dataset_path / "binary-masks"
    if binary_masks_dir.exists() and binary_masks_dir.is_dir():
        binary_masks_files = _sorted_npz_files(binary_masks_dir)
        if binary_masks_files and _npz_has_layers_key(binary_masks_files[0]):
            return "density", binary_masks_dir

    cap3d_dir = dataset_path / "cap3d"
    if cap3d_dir.exists() and cap3d_dir.is_dir() and _sorted_cap3d_files(cap3d_dir):
        return "cap3d", cap3d_dir

    direct_cap3d_files = _sorted_cap3d_files(dataset_path)
    if direct_cap3d_files:
        return "cap3d", dataset_path

    raise ValueError(
        f"Could not auto-detect dataset format for {dataset_path}. "
        "Expected per-window density NPZs, a legacy CNN-Cap dataset, or CAP3D window files."
    )


def _resolve_requested_format(dataset_path: Path, requested_format: str) -> Tuple[str, Path]:
    dataset_path = dataset_path.resolve()
    if requested_format == "auto":
        return _detect_dataset_format(dataset_path)

    if requested_format == "density":
        if dataset_path.is_dir() and _sorted_npz_files(dataset_path):
            return "density", dataset_path
        density_dir = dataset_path / "density_maps"
        if density_dir.is_dir():
            return "density", density_dir.resolve()
        binary_masks_dir = dataset_path / "binary-masks"
        if binary_masks_dir.is_dir():
            return "density", binary_masks_dir.resolve()
        return "density", dataset_path

    if requested_format == "legacy":
        return "legacy", dataset_path

    cap3d_dir = dataset_path / "cap3d" if (dataset_path / "cap3d").is_dir() else dataset_path
    return "cap3d", cap3d_dir.resolve()


def _analyze_density_dataset(density_dir: Path) -> AnalysisResult:
    npz_files = _sorted_npz_files(density_dir)
    if not npz_files:
        raise ValueError(f"No NPZ files found in density-map directory: {density_dir}")

    coverage: DefaultDict[str, LayerCoverage] = defaultdict(LayerCoverage)
    notes: List[str] = []

    for npz_path in npz_files:
        window_id = npz_path.stem
        with np.load(npz_path, allow_pickle=True) as data:
            if "layers" not in data:
                raise KeyError(f"{npz_path} is missing the required 'layers' array")

            layers = [str(layer) for layer in np.asarray(data["layers"]).tolist()]
            for layer_name in layers:
                layer_stats = coverage[layer_name]
                layer_stats.windows_listing_layer += 1

                img_key = f"{layer_name}_img"
                idx_key = f"{layer_name}_idx"
                has_img = img_key in data
                has_idx = idx_key in data

                if has_img or has_idx:
                    layer_stats.windows_with_arrays += 1

                has_elements = False
                if has_idx:
                    has_elements = bool(np.any(np.asarray(data[idx_key]) > 0))
                elif has_img:
                    has_elements = bool(np.any(np.asarray(data[img_key]) != 0))

                if has_elements:
                    layer_stats.windows_with_elements += 1
                    layer_stats.window_ids_with_elements.append(window_id)

    notes.append("Per-window density dataset: a window counts for a layer when its stored layer map is non-empty.")
    notes.append("If a layer is listed in NPZ metadata but lacks per-layer arrays, it is counted as listed but empty.")

    return AnalysisResult(
        dataset_format="density",
        analyzed_path=density_dir,
        total_windows=len(npz_files),
        layer_coverage=dict(coverage),
        notes=notes,
    )


def _choose_legacy_stack(dataset_path: Path, explicit_stack: Optional[str]) -> str:
    if explicit_stack:
        return explicit_stack

    stacks = _discover_legacy_layer_stacks(dataset_path)
    if not stacks:
        raise ValueError(f"No legacy label files found under {dataset_path / 'label'}")
    if len(stacks) > 1:
        raise ValueError(
            "Multiple legacy layer stacks found: "
            + ", ".join(stacks)
            + ". Pass --legacy-layers to choose one."
        )
    return stacks[0]


def _iter_legacy_window_keys(label_dir: Path, layer_stack: str) -> Iterable[Tuple[int, int, int, int]]:
    for label_path in sorted(label_dir.glob(f"{layer_stack}_*.txt")):
        text = label_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            fields = line.split()
            if len(fields) < 4:
                raise ValueError(f"Malformed legacy label row in {label_path}:{line_number}: {line!r}")
            yield tuple(int(fields[idx]) for idx in range(4))


def _legacy_window_slice(offset_x: int, offset_y: int, grid_x: int, grid_y: int) -> Tuple[slice, slice]:
    x_origin = grid_x * LEGACY_WINDOW_STRIDE + LEGACY_WINDOW_MARGIN + offset_x
    y_origin = grid_y * LEGACY_WINDOW_STRIDE + LEGACY_WINDOW_MARGIN + offset_y
    return (
        slice(x_origin, x_origin + LEGACY_WINDOW_SIZE),
        slice(y_origin, y_origin + LEGACY_WINDOW_SIZE),
    )


def _analyze_legacy_dataset(dataset_path: Path, explicit_stack: Optional[str]) -> AnalysisResult:
    layer_stack = _choose_legacy_stack(dataset_path, explicit_stack)
    layer_names = layer_stack.split("_")
    label_dir = dataset_path / "label"

    window_keys = sorted(set(_iter_legacy_window_keys(label_dir, layer_stack)))
    if not window_keys:
        raise ValueError(f"No window labels found for legacy stack {layer_stack} in {label_dir}")

    layer_arrays: Dict[str, Tuple[Optional[np.ndarray], Optional[np.ndarray]]] = {}
    for layer_name in layer_names:
        npz_path = dataset_path / f"{layer_name}.npz"
        if not npz_path.exists():
            raise FileNotFoundError(f"Legacy layer NPZ not found: {npz_path}")

        with np.load(npz_path, allow_pickle=True) as data:
            img = np.asarray(data["img"]) if "img" in data else None
            idx = np.asarray(data["idx"]) if "idx" in data else None
            if img is None and idx is None:
                raise KeyError(f"Legacy layer NPZ has neither 'img' nor 'idx': {npz_path}")
            layer_arrays[layer_name] = (img, idx)

    coverage = {layer_name: LayerCoverage() for layer_name in layer_names}
    total_windows = len(window_keys)

    for layer_name in layer_names:
        coverage[layer_name].windows_listing_layer = total_windows
        coverage[layer_name].windows_with_arrays = total_windows

    for window_key in window_keys:
        x_slice, y_slice = _legacy_window_slice(*window_key)
        window_id = ",".join(str(value) for value in window_key)
        for layer_name in layer_names:
            img, idx = layer_arrays[layer_name]
            has_elements = False

            if idx is not None:
                window_idx = idx[x_slice, y_slice]
                has_elements = bool(window_idx.size and np.any(window_idx > 0))
            elif img is not None:
                window_img = img[x_slice, y_slice]
                has_elements = bool(window_img.size and np.any(window_img != 0))

            if has_elements:
                coverage[layer_name].windows_with_elements += 1
                coverage[layer_name].window_ids_with_elements.append(window_id)

    notes = [
        f"Legacy CNN-Cap dataset using layer stack: {layer_stack}.",
        "Windows are deduplicated by the first four label fields (the geometric crop parameters).",
    ]

    return AnalysisResult(
        dataset_format="legacy",
        analyzed_path=dataset_path,
        total_windows=total_windows,
        layer_coverage=coverage,
        notes=notes,
    )


def _analyze_cap3d_dataset(cap3d_dir: Path) -> AnalysisResult:
    cap3d_files = _sorted_cap3d_files(cap3d_dir)
    if not cap3d_files:
        raise ValueError(f"No CAP3D files found in {cap3d_dir}")

    coverage: DefaultDict[str, LayerCoverage] = defaultdict(LayerCoverage)

    for cap3d_path in cap3d_files:
        window_id = cap3d_path.stem
        parser = StreamingCap3DParser(str(cap3d_path))
        parsed = parser.parse_complete()

        declared_layers = [layer.name for layer in parsed.layers]
        for layer_name in declared_layers:
            coverage[layer_name].windows_listing_layer += 1

        layers_by_index = {idx: layer.name for idx, layer in enumerate(parsed.layers)}
        present_layers = set()
        for block in parsed.blocks:
            if block.type != "conductor" or block.layer is None:
                continue
            present_layers.add(layers_by_index.get(block.layer, str(block.layer)))

        for layer_name in present_layers:
            stats = coverage[layer_name]
            stats.windows_with_arrays += 1
            stats.windows_with_elements += 1
            stats.window_ids_with_elements.append(window_id)

    notes = [
        "CAP3D dataset: a layer counts when at least one conductor block in the window maps to that layer.",
        "Polygon conductor elements without a resolvable layer index are not counted.",
    ]

    return AnalysisResult(
        dataset_format="cap3d",
        analyzed_path=cap3d_dir,
        total_windows=len(cap3d_files),
        layer_coverage=dict(coverage),
        notes=notes,
    )


def _print_result(result: AnalysisResult, warn_below: float) -> None:
    print(f"Dataset format: {result.dataset_format}")
    print(f"Analyzed path: {result.analyzed_path}")
    print(f"Total windows: {result.total_windows}")
    print()

    print(
        f"{'Layer':<18} {'Listed':>8} {'Arrays':>8} {'Windows':>8} {'Coverage':>9}"
    )
    print("-" * 56)

    ordered_layers = sorted(
        result.layer_coverage.items(),
        key=lambda item: (
            item[1].windows_with_elements,
            item[1].windows_listing_layer,
            item[0],
        ),
    )

    sparse_layers: List[Tuple[str, float, LayerCoverage]] = []
    for layer_name, stats in ordered_layers:
        denom = stats.windows_listing_layer or result.total_windows or 1
        coverage_ratio = stats.windows_with_elements / denom
        if warn_below > 0 and coverage_ratio < warn_below:
            sparse_layers.append((layer_name, coverage_ratio, stats))

        print(
            f"{layer_name:<18} "
            f"{stats.windows_listing_layer:>8} "
            f"{stats.windows_with_arrays:>8} "
            f"{stats.windows_with_elements:>8} "
            f"{coverage_ratio:>8.1%}"
        )

    if result.notes:
        print()
        for note in result.notes:
            print(f"Note: {note}")

    if sparse_layers:
        print()
        print(f"Layers below coverage threshold ({warn_below:.1%}):")
        for layer_name, coverage_ratio, stats in sparse_layers:
            print(
                f"  {layer_name}: {stats.windows_with_elements}/{stats.windows_listing_layer or result.total_windows} "
                f"windows ({coverage_ratio:.1%})"
            )

    sparse_window_layers = [
        (layer_name, stats)
        for layer_name, stats in ordered_layers
        if 0 < stats.windows_with_elements < 10
    ]
    if sparse_window_layers:
        print()
        print("Exact window IDs for layers present in fewer than 10 windows:")
        for layer_name, stats in sparse_window_layers:
            print(
                f"  {layer_name}: "
                + ", ".join(stats.window_ids_with_elements)
            )


def main() -> int:
    args = _parse_args()

    if not 0.0 <= args.warn_below <= 1.0:
        raise ValueError("--warn-below must be between 0.0 and 1.0")

    dataset_format, analyzed_path = _resolve_requested_format(args.dataset, args.format)
    if dataset_format == "density":
        result = _analyze_density_dataset(analyzed_path)
    elif dataset_format == "legacy":
        result = _analyze_legacy_dataset(analyzed_path, args.legacy_layers)
    else:
        result = _analyze_cap3d_dataset(analyzed_path)

    _print_result(result, args.warn_below)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

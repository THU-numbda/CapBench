#!/usr/bin/env python3
"""
DEF/LEF to binary-masks converter for the newer U-Net flow.

This writes compact per-layer conductor ID maps plus conductor name metadata for
the U-Net training path. It replaces the legacy CAP3D-backed rasterization path
with direct DEF/LEF rasterization, using the exact DEF DIEAREA without adding
context margin around the window.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

import numpy as np

from capbench._internal.common.datasets import get_dataset_subdirs
from capbench._internal.common.def_fast_density import (
    PreparedDefRasterInput,
    prepare_fast_def_raster_input,
    rasterize_def_idmaps_cpu,
)
from capbench.preprocess.converters.cnn_cap import (
    _resolve_target_size,
)


INT16_MAX = np.iinfo(np.int16).max
_DATASET_PARENT_DIRS = {
    "cap3d",
    "def",
    "gds",
    "point_clouds",
    "density_maps",
    "binary-masks",
    "density_maps_scaled",
    "labels_rwcap",
    "labels_raphael",
    "manifests",
}


def _infer_dataset_base(input_path: Path) -> Path:
    parent = input_path.parent
    if parent.name.lower() in _DATASET_PARENT_DIRS:
        return parent.parent
    return parent


def _resolve_dataset_dirs_for_input(
    input_path: Path,
    dataset_dirs: Optional[Dict[str, Path]] = None,
) -> Dict[str, Path]:
    if dataset_dirs:
        return dataset_dirs
    return get_dataset_subdirs(_infer_dataset_base(input_path))


def _resolve_def_path(
    input_path: Path,
    *,
    dataset_dirs: Optional[Dict[str, Path]] = None,
    explicit_def_path: Optional[Path] = None,
) -> Path:
    if explicit_def_path is not None:
        resolved = Path(explicit_def_path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"DEF file not found: {resolved}")
        return resolved

    resolved_input = Path(input_path).resolve()
    if resolved_input.suffix.lower() == ".def":
        if not resolved_input.exists():
            raise FileNotFoundError(f"DEF file not found: {resolved_input}")
        return resolved_input

    candidates = []
    dirs = _resolve_dataset_dirs_for_input(resolved_input, dataset_dirs)
    candidates.append((dirs["def"] / f"{resolved_input.stem}.def").resolve())
    if resolved_input.parent.name.lower() == "cap3d":
        candidates.append((resolved_input.parent.parent / "def" / f"{resolved_input.stem}.def").resolve())
    candidates.append(resolved_input.with_suffix(".def").resolve())

    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"Could not resolve a DEF file for {resolved_input}. Tried: "
        + ", ".join(str(candidate) for candidate in candidates)
    )


def _prepare_export_raster_input(
    def_path: Path,
    tech_path: Path,
    *,
    pixel_resolution: Optional[float],
    target_size: int,
    selected_layers: Optional[Iterable[str]] = None,
    lef_files: Optional[Sequence[Path]] = None,
) -> PreparedDefRasterInput:
    return prepare_fast_def_raster_input(
        def_path=def_path,
        tech_path=Path(tech_path).resolve(),
        lef_files=lef_files,
        target_size=target_size,
        pixel_resolution=pixel_resolution,
        selected_layers=list(selected_layers) if selected_layers is not None else None,
        raster_bounds=None,
        include_supply_nets=True,
        include_conductor_names=True,
        backend="compiled",
    )


def _build_export_conductor_metadata(
    prepared: PreparedDefRasterInput,
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    if prepared.conductor_names_sorted is None:
        raise ValueError(f"Prepared DEF input did not include conductor names for {prepared.def_path}")

    names = [str(name) for name in prepared.conductor_names_sorted]
    ids = np.asarray(prepared.conductor_ids_sorted, dtype=np.int32)
    is_synthetic = np.asarray(prepared.conductor_is_synthetic, dtype=bool)

    if not (len(names) == len(ids) == len(is_synthetic)):
        raise ValueError(
            f"Conductor metadata length mismatch for {prepared.def_path}: "
            f"names={len(names)} ids={len(ids)} synthetic={len(is_synthetic)}"
        )

    if len(names) > INT16_MAX:
        raise ValueError(
            f"Window {prepared.def_path.stem} has more than {INT16_MAX} conductors, "
            f"which exceeds the int16 export limit."
        )

    remap = np.zeros((int(ids.max()) + 1,) if ids.size else (1,), dtype=np.int32)
    for source_id in ids.tolist():
        remap[int(source_id)] = int(source_id)

    export_ids = ids.astype(np.int16, copy=False)
    return names, export_ids, remap, is_synthetic


def build_id_map_npz_data(prepared: PreparedDefRasterInput) -> Dict[str, np.ndarray]:
    """Build a binary-masks NPZ payload from prepared DEF raster input."""
    raw_idmaps = np.asarray(rasterize_def_idmaps_cpu(prepared), dtype=np.int32)
    if raw_idmaps.ndim != 3:
        raise ValueError(
            f"Expected rasterized DEF ID maps with shape [layers, height, width], got {raw_idmaps.shape}"
        )

    conductor_names, conductor_ids, remap, conductor_is_synthetic = _build_export_conductor_metadata(prepared)
    remapped_idmaps = remap[raw_idmaps].astype(np.int16, copy=False)

    data: Dict[str, np.ndarray] = {
        "layers": np.array(list(prepared.channel_layers), dtype=object),
        "conductor_layers": np.array(list(prepared.channel_layers), dtype=object),
        "window_bounds": np.asarray(prepared.window_bounds, dtype=np.float64),
        "pixel_resolution": np.array(float(prepared.pixel_resolution), dtype=np.float64),
        "conductor_names": np.array(conductor_names, dtype=object),
        "conductor_ids": conductor_ids,
        "conductor_is_synthetic": conductor_is_synthetic.astype(np.bool_, copy=False),
    }

    for layer_idx, layer_name in enumerate(prepared.channel_layers):
        data[f"{layer_name}_idx"] = remapped_idmaps[layer_idx]

    return data


def _coarsen_occupancy_map(id_map: np.ndarray, target_size: int) -> np.ndarray:
    occupied = (np.asarray(id_map, dtype=np.int32) > 0).astype(np.float64, copy=False)
    height, width = occupied.shape
    coarse_size = max(1, int(target_size))
    y_bins = np.linspace(0, height, coarse_size + 1, dtype=int)
    x_bins = np.linspace(0, width, coarse_size + 1, dtype=int)
    coarse = np.zeros((coarse_size, coarse_size), dtype=np.float64)

    for yi in range(coarse_size):
        y0, y1 = y_bins[yi], y_bins[yi + 1]
        if y0 == y1:
            continue
        for xi in range(coarse_size):
            x0, x1 = x_bins[xi], x_bins[xi + 1]
            if x0 == x1:
                continue
            tile = occupied[y0:y1, x0:x1]
            coarse[yi, xi] = tile.mean() if tile.size > 0 else 0.0

    return coarse


def _iter_plot_layers(data: Dict[str, np.ndarray]) -> Iterable[tuple[str, np.ndarray]]:
    layers = [str(layer) for layer in np.asarray(data["layers"]).tolist()]
    for layer_name in layers:
        idx_key = f"{layer_name}_idx"
        if idx_key not in data:
            continue
        yield layer_name, np.asarray(data[idx_key], dtype=np.int16)


def _generate_idmap_plot(
    window_label: str,
    data: Dict[str, np.ndarray],
    output_path: Path,
    *,
    coarse_size: int,
    dpi: int,
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
    except ImportError:
        return

    plot_layers = list(_iter_plot_layers(data))
    if not plot_layers:
        return

    n_layers = len(plot_layers)
    n_cols = min(4, n_layers)
    n_rows = (n_layers + n_cols - 1) // n_cols
    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(4.5 * n_cols, 4.5 * n_rows),
        constrained_layout=True,
    )
    axes = np.atleast_2d(axes)

    last_image = None
    for idx, (layer_name, id_map) in enumerate(plot_layers):
        ax = axes[idx // n_cols, idx % n_cols]
        coarse_map = _coarsen_occupancy_map(id_map, coarse_size)
        im = ax.imshow(
            coarse_map,
            cmap="Greys_r",
            vmin=0.0,
            vmax=1.0,
            origin="lower",
            interpolation="nearest",
        )
        last_image = im
        ax.set_xticks(np.arange(-0.5, coarse_size, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, coarse_size, 1), minor=True)
        ax.grid(which="minor", color="black", linewidth=0.3, alpha=0.25)
        ax.tick_params(which="both", bottom=False, left=False, labelbottom=False, labelleft=False)
        ax.set_title(layer_name)

    for idx in range(n_layers, n_rows * n_cols):
        axes[idx // n_cols, idx % n_cols].axis("off")

    if last_image is not None:
        fig.colorbar(
            last_image,
            ax=axes[:n_rows, :n_cols].ravel().tolist(),
            shrink=0.85,
            pad=0.04,
            label="Average occupancy (darker = higher)",
        )

    fig.suptitle(f"{window_label} - U-Net ID Map Occupancy", fontsize=14, y=1.02)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def convert_window(
    input_path: Path,
    tech_path: Path,
    *,
    def_path: Optional[Path] = None,
    lef_files: Optional[Sequence[Path]] = None,
    pixel_resolution: Optional[float] = None,
    output_npz: Optional[Path] = None,
    plot: bool = False,
    plot_dir: Optional[Path] = None,
    coarse_size: int = 30,
    dpi: int = 150,
    dataset_dirs: Optional[Dict[str, Path]] = None,
    target_size: Optional[int] = None,
    scaled_output: bool = False,
    selected_layers: Optional[Iterable[str]] = None,
) -> Path:
    """
    Generate a binary-masks NPZ for a single window using direct DEF rasterization.

    `input_path` may be either a window DEF path or a CAP3D path. CAP3D inputs are
    accepted for backward compatibility, but the DEF sibling is resolved and used as
    the actual source of truth.
    """
    input_path = Path(input_path).resolve()
    tech_path = Path(tech_path).resolve()

    dataset_dirs = _resolve_dataset_dirs_for_input(input_path, dataset_dirs)
    resolved_def_path = _resolve_def_path(
        input_path,
        dataset_dirs=dataset_dirs,
        explicit_def_path=def_path,
    )
    resolved_target_size = _resolve_target_size(
        input_path,
        target_size=target_size,
        scaled_output=scaled_output,
    )

    if output_npz is None:
        output_npz = dataset_dirs["binary_masks"] / f"{resolved_def_path.stem}.npz"

    output_npz.parent.mkdir(parents=True, exist_ok=True)

    try:
        prepared = _prepare_export_raster_input(
            resolved_def_path,
            tech_path,
            pixel_resolution=pixel_resolution,
            target_size=resolved_target_size,
            selected_layers=selected_layers,
            lef_files=lef_files,
        )
    except Exception as exc:
        lef_debug = [str(Path(path).resolve()) for path in lef_files] if lef_files else []
        raise RuntimeError(
            "Binary-mask preprocessing failed\n"
            f"  input_path={input_path}\n"
            f"  def_path={resolved_def_path}\n"
            f"  tech_path={tech_path}\n"
            f"  target_size={resolved_target_size}\n"
            f"  pixel_resolution={pixel_resolution}\n"
            f"  selected_layers={list(selected_layers) if selected_layers is not None else 'ALL'}\n"
            f"  lef_files={lef_debug if lef_debug else 'AUTO'}\n"
            f"  error_type={type(exc).__name__}\n"
            f"  error={exc}"
        ) from exc

    data = build_id_map_npz_data(prepared)
    np.savez_compressed(output_npz, **data)

    if plot:
        resolved_plot_dir = plot_dir or output_npz.parent
        resolved_plot_dir.mkdir(parents=True, exist_ok=True)
        plot_path = resolved_plot_dir / f"{resolved_def_path.stem}_visualization.png"
        _generate_idmap_plot(
            resolved_def_path.stem,
            data,
            plot_path,
            coarse_size=coarse_size,
            dpi=dpi,
        )

    return output_npz


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a window DEF into the binary-masks dataset format.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Input DEF file, or a CAP3D path whose sibling DEF should be used",
    )
    parser.add_argument(
        "--def-path",
        type=Path,
        default=None,
        help="Optional explicit DEF override when input_path is not itself a DEF file",
    )
    parser.add_argument("--tech", type=Path, required=True, help="Technology stack YAML")
    parser.add_argument(
        "--lef-file",
        type=Path,
        action="append",
        default=None,
        help="Optional explicit LEF/TLEF file. Repeat to provide multiple files.",
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=None,
        help="Optional microns-per-pixel override (auto-derived when omitted)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional explicit NPZ output path (defaults to dataset binary-masks/)",
    )
    parser.add_argument(
        "--target-size",
        type=int,
        default=None,
        help="Optional explicit square grid size",
    )
    parser.add_argument(
        "--scaled-output",
        action="store_true",
        help="Use the same 128/256/512 size-bucketing policy as the legacy converter",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Also emit a coarse occupancy visualization PNG for inspection",
    )
    parser.add_argument(
        "--plot-dir",
        type=Path,
        default=None,
        help="Optional directory for the visualization PNG",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_npz = convert_window(
        input_path=args.input_path,
        tech_path=args.tech,
        def_path=args.def_path,
        lef_files=args.lef_file,
        pixel_resolution=args.resolution,
        output_npz=args.output,
        plot=args.plot,
        plot_dir=args.plot_dir,
        target_size=args.target_size,
        scaled_output=args.scaled_output,
    )
    print(output_npz)
    return 0


if __name__ == "__main__":
    sys.exit(main())

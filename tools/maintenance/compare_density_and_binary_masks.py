#!/usr/bin/env python3
from __future__ import annotations

"""Plot per-layer density maps next to binary-mask occupancy for one window.

Example:
    python -m tools.maintenance.compare_density_and_binary_masks \
        --dataset-path /path/to/dataset \
        --window W0
"""

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


def _load_density_maps(npz_path: Path) -> Tuple[List[str], Dict[str, np.ndarray], float]:
    with np.load(npz_path, allow_pickle=True) as data:
        layers = [str(layer) for layer in data["layers"].tolist()]
        density_maps: Dict[str, np.ndarray] = {}
        for layer in layers:
            key = f"{layer}_img"
            if key not in data:
                continue
            density_maps[layer] = np.asarray(data[key], dtype=np.float32)
        pixel_resolution = float(np.asarray(data["pixel_resolution"]).item())
    return layers, density_maps, pixel_resolution


def _load_binary_masks(npz_path: Path) -> Tuple[List[str], Dict[str, np.ndarray], float]:
    with np.load(npz_path, allow_pickle=True) as data:
        layers = [str(layer) for layer in data["layers"].tolist()]
        binary_maps: Dict[str, np.ndarray] = {}
        for layer in layers:
            key = f"{layer}_idx"
            if key not in data:
                continue
            id_map = np.asarray(data[key], dtype=np.int32)
            binary_maps[layer] = (id_map > 0).astype(np.float32, copy=False)
        pixel_resolution = float(np.asarray(data["pixel_resolution"]).item())
    return layers, binary_maps, pixel_resolution


def _build_comparison_layers(
    density_layers: List[str],
    density_maps: Dict[str, np.ndarray],
    binary_maps: Dict[str, np.ndarray],
) -> List[str]:
    return [layer for layer in density_layers if layer in density_maps and layer in binary_maps]


def plot_window(
    dataset_path: Path,
    window_id: str,
    output_path: Path,
) -> Path:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required to render comparison plots") from exc

    density_npz = dataset_path / "density_maps" / f"{window_id}.npz"
    binary_npz = dataset_path / "binary-masks" / f"{window_id}.npz"

    if not density_npz.exists():
        raise FileNotFoundError(f"Missing density-map NPZ: {density_npz}")
    if not binary_npz.exists():
        raise FileNotFoundError(f"Missing binary-mask NPZ: {binary_npz}")

    density_layers, density_maps, density_res = _load_density_maps(density_npz)
    _, binary_maps, binary_res = _load_binary_masks(binary_npz)
    layers = _build_comparison_layers(density_layers, density_maps, binary_maps)

    if not layers:
        raise RuntimeError(
            f"No shared layers found between {density_npz.name} and {binary_npz.name}"
        )

    n_rows = len(layers)
    fig, axes = plt.subplots(n_rows, 3, figsize=(12, max(3, 2.8 * n_rows)), squeeze=False)
    fig.suptitle(
        f"{window_id} density-maps vs binary-masks\n"
        f"density_res={density_res:.6g}um, binary_res={binary_res:.6g}um",
        fontsize=12,
    )

    for row, layer in enumerate(layers):
        density = density_maps[layer]
        binary = binary_maps[layer]

        ax_density, ax_binary, ax_diff = axes[row]
        im0 = ax_density.imshow(density, origin="lower", cmap="viridis", vmin=0.0, vmax=1.0)
        ax_density.set_title(f"{layer} density\nmean={density.mean():.3f}")
        ax_density.set_axis_off()
        fig.colorbar(im0, ax=ax_density, fraction=0.046, pad=0.04)

        im1 = ax_binary.imshow(binary, origin="lower", cmap="gray", vmin=0.0, vmax=1.0)
        ax_binary.set_title(f"{layer} binary\nfill={binary.mean():.3f}")
        ax_binary.set_axis_off()
        fig.colorbar(im1, ax=ax_binary, fraction=0.046, pad=0.04)

        if density.shape == binary.shape:
            diff = np.abs(density - binary)
            im2 = ax_diff.imshow(diff, origin="lower", cmap="magma", vmin=0.0, vmax=1.0)
            ax_diff.set_title(f"{layer} abs(density-binary)\nmean={diff.mean():.3f}")
            fig.colorbar(im2, ax=ax_diff, fraction=0.046, pad=0.04)
        else:
            ax_diff.text(
                0.5,
                0.5,
                f"shape mismatch\n{density.shape} vs {binary.shape}",
                ha="center",
                va="center",
                fontsize=10,
            )
            ax_diff.set_title(f"{layer} diff unavailable")
        ax_diff.set_axis_off()

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot all shared layers for one window comparing density maps and binary masks."
    )
    parser.add_argument("--dataset-path", required=True, help="Dataset root containing density_maps/ and binary-masks/")
    parser.add_argument("--window", default="W0", help="Window id to compare (default: W0)")
    parser.add_argument(
        "--output",
        help="Optional PNG output path (default: <dataset>/comparison_plots/<window>_density_vs_binary_masks.png)",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset_path).resolve()
    output_path = (
        Path(args.output).resolve()
        if args.output
        else dataset_path / "comparison_plots" / f"{args.window}_density_vs_binary_masks.png"
    )
    saved = plot_window(dataset_path=dataset_path, window_id=args.window, output_path=output_path)
    print(saved)


if __name__ == "__main__":
    main()

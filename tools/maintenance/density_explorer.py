#!/usr/bin/env python3
"""Experimental real-time density explorer for CAP3D inputs."""

from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from capbench.preprocess.cap3d_parser import StreamingCap3DParser


PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (56, 128, 255),
    (0, 201, 167),
    (255, 171, 64),
    (255, 99, 132),
    (156, 39, 176),
    (0, 188, 212),
    (139, 195, 74),
    (255, 202, 40),
    (121, 134, 203),
    (244, 67, 54),
    (0, 150, 136),
    (103, 58, 183),
)

_EXCLUDED_LAYER_TYPES = {"substrate", "dielectric"}
_METAL_LAYER_TYPES = {"interconnect", "metal"}


@dataclass(frozen=True)
class DesignBounds:
    design_name: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width_um(self) -> float:
        return self.x_max - self.x_min

    @property
    def height_um(self) -> float:
        return self.y_max - self.y_min


@dataclass(frozen=True)
class ExplorerGeometry:
    bounds: DesignBounds
    layer_names: List[str]
    layer_colors: List[Tuple[float, float, float]]
    pixel_resolution_um: float
    window_pixels: int
    rect_layers: np.ndarray
    rect_bounds: np.ndarray
    spatial_bins: Dict[Tuple[int, int], List[int]]
    spatial_bin_size_um: float
    layout_image: np.ndarray


def _color_from_palette(index: int) -> Tuple[float, float, float]:
    rgb = PALETTE[index % len(PALETTE)]
    return rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0


def _block_to_xy_bounds(block) -> Tuple[float, float, float, float]:
    base = block.base
    v1 = block.v1
    v2 = block.v2
    x_coords = (
        float(base[0]),
        float(base[0] + v1[0]),
        float(base[0] + v2[0]),
        float(base[0] + v1[0] + v2[0]),
    )
    y_coords = (
        float(base[1]),
        float(base[1] + v1[1]),
        float(base[1] + v2[1]),
        float(base[1] + v1[1] + v2[1]),
    )
    return min(x_coords), max(x_coords), min(y_coords), max(y_coords)


def _compute_bounds(parsed, cap3d_path: Path) -> DesignBounds:
    if parsed.window is not None:
        x0 = min(float(parsed.window.v1[0]), float(parsed.window.v2[0]))
        y0 = min(float(parsed.window.v1[1]), float(parsed.window.v2[1]))
        x1 = max(float(parsed.window.v1[0]), float(parsed.window.v2[0]))
        y1 = max(float(parsed.window.v1[1]), float(parsed.window.v2[1]))
        return DesignBounds(
            design_name=parsed.window.name or cap3d_path.stem,
            x_min=x0,
            y_min=y0,
            x_max=x1,
            y_max=y1,
        )

    x_values: List[float] = []
    y_values: List[float] = []
    for block in parsed.blocks:
        if getattr(block, "type", "").lower() != "conductor":
            continue
        x0, x1, y0, y1 = _block_to_xy_bounds(block)
        x_values.extend((x0, x1))
        y_values.extend((y0, y1))
    if not x_values or not y_values:
        raise ValueError(f"No conductor geometry found in {cap3d_path}")
    return DesignBounds(
        design_name=cap3d_path.stem,
        x_min=min(x_values),
        y_min=min(y_values),
        x_max=max(x_values),
        y_max=max(y_values),
    )


def _build_spatial_bins(
    rect_bounds: np.ndarray,
    bounds: DesignBounds,
    *,
    bin_size_um: float,
) -> Dict[Tuple[int, int], List[int]]:
    if bin_size_um <= 0.0:
        raise ValueError(f"spatial bin size must be positive, got {bin_size_um}")

    bins: Dict[Tuple[int, int], List[int]] = {}
    for rect_idx, rect in enumerate(rect_bounds):
        x0, x1, y0, y1 = (float(value) for value in rect)
        if x0 >= x1 or y0 >= y1:
            continue
        bx0 = int(math.floor((x0 - bounds.x_min) / bin_size_um))
        bx1 = int(math.floor((x1 - bounds.x_min - 1e-9) / bin_size_um))
        by0 = int(math.floor((y0 - bounds.y_min) / bin_size_um))
        by1 = int(math.floor((y1 - bounds.y_min - 1e-9) / bin_size_um))
        for bx in range(bx0, bx1 + 1):
            for by in range(by0, by1 + 1):
                bins.setdefault((bx, by), []).append(rect_idx)
    return bins


def _build_layout_image(
    rect_layers: np.ndarray,
    rect_bounds: np.ndarray,
    layer_colors: Sequence[Tuple[float, float, float]],
    *,
    bounds: DesignBounds,
    max_dim: int,
) -> np.ndarray:
    if max_dim <= 0:
        raise ValueError("layout resolution must be positive")

    scale = min(max_dim / bounds.width_um, max_dim / bounds.height_um)
    image_width = max(1, int(math.ceil(bounds.width_um * scale)))
    image_height = max(1, int(math.ceil(bounds.height_um * scale)))
    image = np.zeros((image_height, image_width, 3), dtype=np.float32)
    image[:, :, :] = 0.05

    for layer_idx, rect in zip(rect_layers.tolist(), rect_bounds.tolist()):
        if layer_idx < 0 or layer_idx >= len(layer_colors):
            continue
        x0, x1, y0, y1 = rect
        ix0 = max(0, min(image_width, int(math.floor((x0 - bounds.x_min) * scale))))
        ix1 = max(0, min(image_width, int(math.ceil((x1 - bounds.x_min) * scale))))
        iy0 = max(0, min(image_height, int(math.floor((y0 - bounds.y_min) * scale))))
        iy1 = max(0, min(image_height, int(math.ceil((y1 - bounds.y_min) * scale))))
        if ix0 >= ix1 or iy0 >= iy1:
            continue
        color = np.asarray(layer_colors[layer_idx], dtype=np.float32)
        block = image[iy0:iy1, ix0:ix1, :]
        np.maximum(block, color * 0.9, out=block)

    return image


def _load_geometry(
    cap3d_path: Path,
    *,
    window_size_um: float,
    window_pixels: int,
    layout_resolution: int,
) -> ExplorerGeometry:
    if window_size_um <= 0.0:
        raise ValueError(f"window size must be positive, got {window_size_um}")
    if window_pixels <= 0:
        raise ValueError(f"pixel size must be positive, got {window_pixels}")

    parsed = StreamingCap3DParser(str(cap3d_path), use_fast=False).parse_complete()
    bounds = _compute_bounds(parsed, cap3d_path)
    if bounds.width_um < window_size_um or bounds.height_um < window_size_um:
        raise ValueError(
            f"Requested {window_size_um:.3f}um window does not fit inside CAP3D bounds "
            f"{bounds.width_um:.3f}um x {bounds.height_um:.3f}um"
        )

    parsed_layer_to_channel: Dict[int, int] = {}
    layer_names: List[str] = []
    for parsed_idx, layer in enumerate(parsed.layers):
        layer_type = str(getattr(layer, "type", "") or "").lower()
        if layer_type in _EXCLUDED_LAYER_TYPES:
            continue
        if layer_type not in _METAL_LAYER_TYPES:
            continue
        layer_id = int(getattr(layer, "id", parsed_idx))
        parsed_layer_to_channel[layer_id] = len(layer_names)
        layer_names.append(str(layer.name))

    if not layer_names:
        raise ValueError(f"No conductor layers with geometry found in {cap3d_path}")

    name_to_channel = {name.lower(): idx for idx, name in enumerate(layer_names)}
    rect_layers: List[int] = []
    rect_bounds: List[Tuple[float, float, float, float]] = []

    for block in parsed.blocks:
        if getattr(block, "type", "").lower() != "conductor":
            continue

        channel_idx: Optional[int] = None
        layer_idx = getattr(block, "layer", None)
        if layer_idx is not None and int(layer_idx) in parsed_layer_to_channel:
            channel_idx = parsed_layer_to_channel[int(layer_idx)]
        else:
            fallback_name = str(getattr(block, "parent_name", "") or "").lower()
            if fallback_name in name_to_channel:
                channel_idx = name_to_channel[fallback_name]
        if channel_idx is None:
            continue

        x0, x1, y0, y1 = _block_to_xy_bounds(block)
        if x0 >= x1 or y0 >= y1:
            continue
        rect_layers.append(channel_idx)
        rect_bounds.append((x0, x1, y0, y1))

    if not rect_bounds:
        raise ValueError(f"No conductor rectangles could be derived from {cap3d_path}")

    rect_layers_array = np.asarray(rect_layers, dtype=np.int16)
    rect_bounds_array = np.asarray(rect_bounds, dtype=np.float32)
    pixel_resolution_um = window_size_um / float(window_pixels)
    layer_colors = [_color_from_palette(index) for index in range(len(layer_names))]
    spatial_bin_size_um = max(window_size_um * 0.5, pixel_resolution_um * 8.0)
    spatial_bins = _build_spatial_bins(
        rect_bounds_array,
        bounds,
        bin_size_um=spatial_bin_size_um,
    )
    layout_image = _build_layout_image(
        rect_layers_array,
        rect_bounds_array,
        layer_colors,
        bounds=bounds,
        max_dim=layout_resolution,
    )

    return ExplorerGeometry(
        bounds=bounds,
        layer_names=layer_names,
        layer_colors=layer_colors,
        pixel_resolution_um=pixel_resolution_um,
        window_pixels=window_pixels,
        rect_layers=rect_layers_array,
        rect_bounds=rect_bounds_array,
        spatial_bins=spatial_bins,
        spatial_bin_size_um=spatial_bin_size_um,
        layout_image=layout_image,
    )


class DensityExplorer:
    def __init__(
        self,
        geometry: ExplorerGeometry,
        *,
        window_size_um: float,
        step_um: float,
        screenshot: Optional[Path],
        start_x: Optional[float] = None,
        start_y: Optional[float] = None,
    ) -> None:
        self.geometry = geometry
        self.window_size_um = float(window_size_um)
        self.step_um = float(step_um)
        self.screenshot = screenshot

        self.window_x = self._resolve_start_coordinate(
            start=start_x,
            lower=geometry.bounds.x_min,
            upper=geometry.bounds.x_max,
        )
        self.window_y = self._resolve_start_coordinate(
            start=start_y,
            lower=geometry.bounds.y_min,
            upper=geometry.bounds.y_max,
        )

        self._figure = None
        self._layout_axis = None
        self._layer_axes: List = []
        self._layer_images: List = []
        self._window_patch = None
        self._status_text = None

    def _resolve_start_coordinate(self, *, start: Optional[float], lower: float, upper: float) -> float:
        max_start = upper - self.window_size_um
        if start is None:
            return 0.5 * (lower + max_start)
        return min(max(float(start), lower), max_start)

    def _query_candidate_indices(self) -> List[int]:
        bin_size = self.geometry.spatial_bin_size_um
        bx0 = int(math.floor((self.window_x - self.geometry.bounds.x_min) / bin_size))
        bx1 = int(math.floor((self.window_x + self.window_size_um - self.geometry.bounds.x_min - 1e-9) / bin_size))
        by0 = int(math.floor((self.window_y - self.geometry.bounds.y_min) / bin_size))
        by1 = int(math.floor((self.window_y + self.window_size_um - self.geometry.bounds.y_min - 1e-9) / bin_size))

        candidates: set[int] = set()
        for bx in range(bx0, bx1 + 1):
            for by in range(by0, by1 + 1):
                candidates.update(self.geometry.spatial_bins.get((bx, by), ()))
        return sorted(candidates)

    def _compute_density_stack(self) -> Tuple[np.ndarray, int]:
        densities = np.zeros(
            (len(self.geometry.layer_names), self.geometry.window_pixels, self.geometry.window_pixels),
            dtype=np.uint8,
        )
        candidates = self._query_candidate_indices()
        pixel_resolution = self.geometry.pixel_resolution_um
        x_limit = self.window_x + self.window_size_um
        y_limit = self.window_y + self.window_size_um

        for rect_idx in candidates:
            layer_idx = int(self.geometry.rect_layers[rect_idx])
            x0, x1, y0, y1 = (float(value) for value in self.geometry.rect_bounds[rect_idx])
            ix0 = max(x0, self.window_x)
            ix1 = min(x1, x_limit)
            iy0 = max(y0, self.window_y)
            iy1 = min(y1, y_limit)
            if ix0 >= ix1 or iy0 >= iy1:
                continue

            local_x0 = max(0, int(math.floor((ix0 - self.window_x) / pixel_resolution)))
            local_x1 = min(self.geometry.window_pixels, int(math.ceil((ix1 - self.window_x) / pixel_resolution)))
            local_y0 = max(0, int(math.floor((iy0 - self.window_y) / pixel_resolution)))
            local_y1 = min(self.geometry.window_pixels, int(math.ceil((iy1 - self.window_y) / pixel_resolution)))
            if local_x0 >= local_x1 or local_y0 >= local_y1:
                continue

            densities[layer_idx, local_y0:local_y1, local_x0:local_x1] = 1

        return densities, len(candidates)

    @staticmethod
    def _colorize_density(binary_map: np.ndarray, color: Tuple[float, float, float]) -> np.ndarray:
        output = np.empty(binary_map.shape + (3,), dtype=np.float32)
        output[:, :, :] = 0.08
        if np.any(binary_map):
            output[binary_map > 0] = np.asarray(color, dtype=np.float32)
        return output

    def _move_window(self, dx_um: float, dy_um: float) -> None:
        new_x = min(max(self.window_x + dx_um, self.geometry.bounds.x_min), self.geometry.bounds.x_max - self.window_size_um)
        new_y = min(max(self.window_y + dy_um, self.geometry.bounds.y_min), self.geometry.bounds.y_max - self.window_size_um)
        if math.isclose(new_x, self.window_x, abs_tol=1e-12) and math.isclose(new_y, self.window_y, abs_tol=1e-12):
            return
        self.window_x = new_x
        self.window_y = new_y
        self._refresh()

    def _refresh(self, *, initial: bool = False) -> None:
        update_start = time.perf_counter()
        density_stack, candidate_count = self._compute_density_stack()
        compute_ms = (time.perf_counter() - update_start) * 1000.0

        self._window_patch.set_xy((self.window_x, self.window_y))
        self._status_text.set_text(
            f"window=({self.window_x:.3f}, {self.window_y:.3f})um  size={self.window_size_um:.3f}um  "
            f"pixels={self.geometry.window_pixels}  step={self.step_um:.3f}um  "
            f"update={compute_ms:.1f}ms  candidates={candidate_count}"
        )

        for layer_idx, image_artist in enumerate(self._layer_images):
            occupancy = density_stack[layer_idx]
            image_artist.set_data(self._colorize_density(occupancy, self.geometry.layer_colors[layer_idx]))
            density_pct = 100.0 * float(occupancy.mean())
            self._layer_axes[layer_idx].set_title(
                f"{self.geometry.layer_names[layer_idx]}  {density_pct:.1f}%",
                fontsize=9,
                color="#d8d8d8",
            )

        self._figure.canvas.draw_idle()

        if initial and self.screenshot is not None:
            self.screenshot.parent.mkdir(parents=True, exist_ok=True)
            self._figure.savefig(self.screenshot, dpi=180, bbox_inches="tight")

    def _on_key_press(self, event) -> None:
        if event is None or not event.key:
            return

        key = str(event.key).lower()
        multiplier = 5.0 if "shift+" in key else 1.0
        base_key = key.split("+")[-1]
        delta = self.step_um * multiplier

        if base_key in {"left", "a"}:
            self._move_window(-delta, 0.0)
            return
        if base_key in {"right", "d"}:
            self._move_window(delta, 0.0)
            return
        if base_key in {"up", "w"}:
            self._move_window(0.0, delta)
            return
        if base_key in {"down", "s"}:
            self._move_window(0.0, -delta)
            return
        if base_key == "r":
            self.window_x = self._resolve_start_coordinate(
                start=None,
                lower=self.geometry.bounds.x_min,
                upper=self.geometry.bounds.x_max,
            )
            self.window_y = self._resolve_start_coordinate(
                start=None,
                lower=self.geometry.bounds.y_min,
                upper=self.geometry.bounds.y_max,
            )
            self._refresh()
            return
        if base_key == "p" and self.screenshot is not None:
            self.screenshot.parent.mkdir(parents=True, exist_ok=True)
            self._figure.savefig(self.screenshot, dpi=180, bbox_inches="tight")

    def show(self) -> None:
        try:
            import matplotlib.pyplot as plt
            from matplotlib.gridspec import GridSpec
            from matplotlib.patches import Rectangle
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise SystemExit(
                "matplotlib is required for the experimental density explorer. "
                "Install it with `python -m pip install '.[vis]'` or `python -m pip install matplotlib`."
            ) from exc

        layer_count = len(self.geometry.layer_names)
        if layer_count <= 6:
            right_columns = 2
        elif layer_count <= 15:
            right_columns = 3
        else:
            right_columns = 4
        right_rows = max(1, int(math.ceil(layer_count / right_columns)))
        figure_height = max(7.0, 1.95 * right_rows)
        self._figure = plt.figure(figsize=(18, figure_height), constrained_layout=True)
        try:
            self._figure.canvas.manager.set_window_title("CapBench Experimental CAP3D Density Explorer")
        except Exception:
            pass

        outer = GridSpec(1, 2, figure=self._figure, width_ratios=[2.5, 2.2])
        self._layout_axis = self._figure.add_subplot(outer[0, 0])
        self._layout_axis.set_title(
            f"{self.geometry.bounds.design_name}: live {self.window_size_um:.1f}um CAP3D window",
            fontsize=13,
        )
        self._layout_axis.imshow(
            self.geometry.layout_image,
            origin="lower",
            extent=(
                self.geometry.bounds.x_min,
                self.geometry.bounds.x_max,
                self.geometry.bounds.y_min,
                self.geometry.bounds.y_max,
            ),
            interpolation="nearest",
        )
        self._layout_axis.set_aspect("equal", adjustable="box")
        self._layout_axis.set_xlabel("X (um)")
        self._layout_axis.set_ylabel("Y (um)")
        self._layout_axis.set_facecolor("#0f0f10")

        self._window_patch = Rectangle(
            (self.window_x, self.window_y),
            self.window_size_um,
            self.window_size_um,
            linewidth=1.8,
            edgecolor="#ffffff",
            facecolor=(1.0, 1.0, 1.0, 0.10),
        )
        self._layout_axis.add_patch(self._window_patch)

        self._layout_axis.text(
            0.01,
            1.02,
            "Controls: arrows or WASD move, Shift accelerates, R resets, P saves screenshot",
            transform=self._layout_axis.transAxes,
            fontsize=10,
            color="#d8d8d8",
            ha="left",
            va="bottom",
        )
        self._status_text = self._layout_axis.text(
            0.01,
            -0.10,
            "",
            transform=self._layout_axis.transAxes,
            fontsize=10,
            color="#d8d8d8",
            ha="left",
            va="top",
        )

        right_grid = outer[0, 1].subgridspec(right_rows, right_columns, hspace=0.10, wspace=0.08)
        for layer_idx, layer_name in enumerate(self.geometry.layer_names):
            row = layer_idx // right_columns
            col = layer_idx % right_columns
            axis = self._figure.add_subplot(right_grid[row, col])
            axis.set_facecolor("#111214")
            axis.set_xticks([])
            axis.set_yticks([])
            image_artist = axis.imshow(
                np.zeros((self.geometry.window_pixels, self.geometry.window_pixels, 3), dtype=np.float32),
                origin="lower",
                interpolation="nearest",
            )
            axis.set_title(layer_name, fontsize=9, color="#d8d8d8")
            self._layer_axes.append(axis)
            self._layer_images.append(image_artist)

        total_slots = right_rows * right_columns
        for slot_idx in range(layer_count, total_slots):
            row = slot_idx // right_columns
            col = slot_idx % right_columns
            axis = self._figure.add_subplot(right_grid[row, col])
            axis.axis("off")

        self._figure.canvas.mpl_connect("key_press_event", self._on_key_press)
        self._refresh(initial=True)
        plt.show()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimental real-time CAP3D density explorer.")
    parser.add_argument("--cap3d", required=True, type=Path, help="Path to the CAP3D file.")
    parser.add_argument(
        "--window-size",
        type=float,
        default=10.0,
        help="Moving square window size in microns. Default: 10.0",
    )
    parser.add_argument(
        "--pixel-size",
        "--window-pixels",
        dest="window_pixels",
        type=int,
        default=224,
        help="Density-map resolution per layer. Default: 224",
    )
    parser.add_argument(
        "--layout-resolution",
        type=int,
        default=900,
        help="Max pixel dimension for the left-side context image. Default: 900",
    )
    parser.add_argument(
        "--step-um",
        type=float,
        default=0.5,
        help="Movement step in microns per key press. Hold Shift to move 5x faster. Default: 0.5",
    )
    parser.add_argument("--start-x", type=float, help="Optional starting window X coordinate in microns.")
    parser.add_argument("--start-y", type=float, help="Optional starting window Y coordinate in microns.")
    parser.add_argument("--screenshot", type=Path, help="Optional screenshot path for the initial frame or the P hotkey.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    cap3d_path = args.cap3d.resolve()
    if not cap3d_path.exists():
        parser.error(f"CAP3D file not found: {cap3d_path}")

    try:
        geometry = _load_geometry(
            cap3d_path,
            window_size_um=float(args.window_size),
            window_pixels=int(args.window_pixels),
            layout_resolution=int(args.layout_resolution),
        )
    except Exception as exc:
        print(f"ERROR: failed to prepare CAP3D geometry: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    explorer = DensityExplorer(
        geometry,
        window_size_um=float(args.window_size),
        step_um=float(args.step_um),
        screenshot=args.screenshot,
        start_x=args.start_x,
        start_y=args.start_y,
    )
    explorer.show()


if __name__ == "__main__":  # pragma: no cover
    main()

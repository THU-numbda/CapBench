#!/usr/bin/env python3
"""
Interactive VTK viewer for CapBench density maps with optional CAP3D overlay.

Given a density-map NPZ (as produced by `converters/cnn_cap.py`), this tool
renders each per-layer density image as a translucent slice positioned at the
corresponding physical Z height. When a CAP3D file is supplied, the script also
draws a faint 3D rendering of the underlying geometry to provide context.

Usage:
    python cap3d_density_viewer.py density_map.npz [--cap3d design.cap3d]
"""

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import numpy as np

from capbench.visualization._common import (
    ensure_repo_root_on_path,
    apply_start_angle,
    capture_initial_screenshot,
)

ensure_repo_root_on_path()

from capbench.preprocess.cap3d_parser import StreamingCap3DParser


# Soft color palette reused for density layer shading
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


@dataclass
class DensityDataset:
    """In-memory representation of a CapBench density NPZ file."""

    path: Path
    layers: List[str]
    density_maps: Dict[str, np.ndarray]
    pixel_resolution: float
    window_bounds: Tuple[float, float, float, float, float, float]


@dataclass
class Cap3DLayerStats:
    """Per-layer aggregate metadata extracted from a CAP3D file."""

    z_min: float
    z_max: float
    block_count: int
    layer_type: str


@dataclass
class Cap3DMetadata:
    """CAP3D aggregation results shared with the viewer."""

    layer_stats: Dict[str, Cap3DLayerStats]
    via_blocks: Dict[str, List]


def load_density_npz(path: Path) -> DensityDataset:
    """Load density map NPZ data from disk."""
    if not path.exists():
        raise FileNotFoundError(f"Density map file not found: {path}")

    data = np.load(path, allow_pickle=True)

    try:
        layers = [str(layer) for layer in data["layers"].tolist()]
    except KeyError as exc:
        raise KeyError("NPZ file missing required 'layers' array") from exc

    density_maps: Dict[str, np.ndarray] = {}
    for layer in layers:
        key = f"{layer}_img"
        if key not in data:
            raise KeyError(f"NPZ file missing density image for layer '{layer}' (expected key '{key}')")
        # Ensure data is stored as float64/float32 for VTK
        arr = np.asarray(data[key], dtype=np.float32)
        density_maps[layer] = arr

    pixel_resolution = float(np.asarray(data["pixel_resolution"]).item())
    window_bounds = tuple(float(v) for v in np.asarray(data["window_bounds"]).tolist())
    if len(window_bounds) != 6:
        raise ValueError("window_bounds must contain six values [xmin, ymin, zmin, xmax, ymax, zmax]")

    return DensityDataset(
        path=path,
        layers=layers,
        density_maps=density_maps,
        pixel_resolution=pixel_resolution,
        window_bounds=window_bounds,  # type: ignore[arg-type]
    )


def _block_to_bounds(block) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Compute axis-aligned bounds for a CAP3D block."""
    bx, by, bz = float(block.base[0]), float(block.base[1]), float(block.base[2])
    dx = float(block.v1[0])
    dy = float(block.v2[1])
    dz = float(block.hvec[2])
    x1, y1, z1 = bx, by, bz
    x2, y2, z2 = bx + dx, by + dy, bz + dz
    return (min(x1, x2), min(y1, y2), min(z1, z2)), (max(x1, x2), max(y1, y2), max(z1, z2))


def collect_cap3d_metadata(cap3d_path: Path) -> Cap3DMetadata:
    """Parse CAP3D once and gather per-layer stats plus via block lists."""
    if not cap3d_path.exists():
        raise FileNotFoundError(f"CAP3D file not found: {cap3d_path}")

    parser = StreamingCap3DParser(str(cap3d_path), use_fast=False)
    parsed = parser.parse_complete()

    layers_by_index = {idx: layer for idx, layer in enumerate(parsed.layers)}
    layer_stats: Dict[str, Cap3DLayerStats] = {}
    via_blocks: Dict[str, List] = defaultdict(list)

    for block in parsed.blocks:
        if block.layer is not None and block.layer in layers_by_index:
            layer_obj = layers_by_index[block.layer]
            layer_name = layer_obj.name
            layer_type = (layer_obj.type or "").lower()
        else:
            layer_name = block.parent_name or "unknown"
            layer_type = ""

        (min_bounds, max_bounds) = _block_to_bounds(block)
        z_lo, z_hi = min_bounds[2], max_bounds[2]

        stats = layer_stats.get(layer_name)
        if stats is None:
            stats = Cap3DLayerStats(z_min=z_lo, z_max=z_hi, block_count=0, layer_type=layer_type)
        else:
            stats.z_min = min(stats.z_min, z_lo)
            stats.z_max = max(stats.z_max, z_hi)
        stats.block_count += 1
        layer_stats[layer_name] = stats

        if "via" in layer_type:
            via_blocks[layer_name].append(block)

    return Cap3DMetadata(layer_stats=layer_stats, via_blocks=dict(via_blocks))


def compute_layer_heights(dataset: DensityDataset, cap3d_meta: Optional[Cap3DMetadata]) -> Dict[str, float]:
    """Determine a representative Z height for each density layer."""
    heights: Dict[str, float] = {}

    if cap3d_meta:
        for layer, stats in cap3d_meta.layer_stats.items():
            heights[layer] = 0.5 * (stats.z_min + stats.z_max)

    missing = [layer for layer in dataset.layers if layer not in heights]
    if missing:
        z0 = min(dataset.window_bounds[2], dataset.window_bounds[5])
        z1 = max(dataset.window_bounds[2], dataset.window_bounds[5])
        span = z1 - z0
        if span <= 1e-6:
            # No usable Z span; space layers uniformly with small offset
            z0 = 0.0
            span = max(dataset.pixel_resolution, 1.0)
        step = span / (len(dataset.layers) + 1)
        for idx, layer in enumerate(dataset.layers):
            if layer in heights:
                continue
            heights[layer] = z0 + step * (idx + 1)

    return heights


def generate_via_density_maps(
    dataset: DensityDataset,
    cap3d_meta: Optional[Cap3DMetadata],
) -> Dict[str, np.ndarray]:
    """Rasterize via layers from CAP3D blocks to align with density maps."""
    if not cap3d_meta or not cap3d_meta.via_blocks:
        return {}

    via_maps: Dict[str, np.ndarray] = {}
    if not dataset.density_maps:
        return via_maps

    sample_map = next(iter(dataset.density_maps.values()))
    rows, cols = sample_map.shape

    pixel_resolution = dataset.pixel_resolution
    x_min, y_min, *_ = dataset.window_bounds

    for layer_name, blocks in cap3d_meta.via_blocks.items():
        if not blocks:
            continue

        layer_arr = np.zeros((rows, cols), dtype=np.float32)

        for block in blocks:
            (min_pt, max_pt) = _block_to_bounds(block)
            x0, y0 = min_pt[0], min_pt[1]
            x1, y1 = max_pt[0], max_pt[1]

            px_min = int(np.floor((x0 - x_min) / pixel_resolution))
            px_max = int(np.ceil((x1 - x_min) / pixel_resolution))
            py_min = int(np.floor((y0 - y_min) / pixel_resolution))
            py_max = int(np.ceil((y1 - y_min) / pixel_resolution))

            if px_max <= px_min or py_max <= py_min:
                continue

            px_min = max(0, min(cols, px_min))
            px_max = max(0, min(cols, px_max))
            py_min = max(0, min(rows, py_min))
            py_max = max(0, min(rows, py_max))

            if px_min >= px_max or py_min >= py_max:
                continue

            layer_arr[py_min:py_max, px_min:px_max] = 1.0

        if np.any(layer_arr > 0.0):
            via_maps[layer_name] = layer_arr

    return via_maps


def create_density_actor(
    layer: str,
    density_map: np.ndarray,
    pixel_resolution: float,
    origin_xy: Tuple[float, float],
    z_height: float,
    color: Tuple[int, int, int],
):
    """Create a VTK actor that displays a single density layer with edge highlighting."""
    import vtk
    from vtk.util import numpy_support

    rows, cols = density_map.shape
    if rows == 0 or cols == 0:
        raise ValueError(f"Density map for layer '{layer}' is empty")

    image = vtk.vtkImageData()
    image.SetSpacing(pixel_resolution, pixel_resolution, 1.0)
    image.SetOrigin(origin_xy[0], origin_xy[1], z_height)
    image.SetExtent(0, cols - 1, 0, rows - 1, 0, 0)

    flat = np.ascontiguousarray(density_map.ravel(order="C"))
    vtk_array = numpy_support.numpy_to_vtk(flat, deep=True, array_type=vtk.VTK_FLOAT)
    vtk_array.SetName(f"{layer}_density")
    image.GetPointData().SetScalars(vtk_array)

    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(256)
    lut.SetRange(0.0, 1.0)
    lut.Build()

    r, g, b = (c / 255.0 for c in color)
    lut.SetTableValue(0, r, g, b, 0.0)
    for idx in range(1, 256):
        alpha = min(1.0, 0.12 + 0.88 * (idx / 255.0))
        lut.SetTableValue(idx, r, g, b, alpha)

    mapper = vtk.vtkImageMapToColors()
    mapper.SetLookupTable(lut)
    mapper.SetInputData(image)

    actor = vtk.vtkImageActor()
    actor.GetMapper().SetInputConnection(mapper.GetOutputPort())
    actor.SetOpacity(1.0)
    actor.SetPickable(False)

    # Create outline actor for edge highlighting
    outline_actor = create_density_outline_actor(
        origin_xy, z_height, pixel_resolution, rows, cols, color
    )

    return actor, outline_actor


def create_density_outline_actor(
    origin_xy: Tuple[float, float],
    z_height: float,
    pixel_resolution: float,
    rows: int,
    cols: int,
    color: Tuple[int, int, int],
):
    """Create a VTK actor that displays the outline edges of a density plane."""
    import vtk

    # Calculate the bounds of the density plane
    x_min, y_min = origin_xy
    x_max = x_min + cols * pixel_resolution
    y_max = y_min + rows * pixel_resolution

    # Create a rectangular outline using vtkPolyData
    points = vtk.vtkPoints()
    points.InsertNextPoint(x_min, y_min, z_height)  # Bottom-left
    points.InsertNextPoint(x_max, y_min, z_height)  # Bottom-right
    points.InsertNextPoint(x_max, y_max, z_height)  # Top-right
    points.InsertNextPoint(x_min, y_max, z_height)  # Top-left

    # Create line segments for the outline
    lines = vtk.vtkCellArray()
    lines.InsertNextCell(2)  # Bottom edge
    lines.InsertCellPoint(0)
    lines.InsertCellPoint(1)
    lines.InsertNextCell(2)  # Right edge
    lines.InsertCellPoint(1)
    lines.InsertCellPoint(2)
    lines.InsertNextCell(2)  # Top edge
    lines.InsertCellPoint(2)
    lines.InsertCellPoint(3)
    lines.InsertNextCell(2)  # Left edge
    lines.InsertCellPoint(3)
    lines.InsertCellPoint(0)

    # Create polydata for the outline
    outline_polydata = vtk.vtkPolyData()
    outline_polydata.SetPoints(points)
    outline_polydata.SetLines(lines)

    # Create mapper and actor for the outline
    outline_mapper = vtk.vtkPolyDataMapper()
    outline_mapper.SetInputData(outline_polydata)

    outline_actor = vtk.vtkActor()
    outline_actor.SetMapper(outline_mapper)

    # Set outline color to layer color (convert to 0-1 range)
    r, g, b = (c / 255.0 for c in color)
    outline_actor.GetProperty().SetColor(r, g, b)
    outline_actor.GetProperty().SetLineWidth(2.0)  # Make edges more visible
    outline_actor.GetProperty().SetOpacity(0.8)   # Slightly transparent
    outline_actor.GetProperty().SetRenderLinesAsTubes(True)  # Make lines more visible
    outline_actor.SetPickable(False)

    return outline_actor


def build_cap3d_actor(cap3d_path: Path, max_blocks: int, opacity: float):
    """Build a low-opacity surface actor for the CAP3D geometry."""
    import vtk

    parser = StreamingCap3DParser(str(cap3d_path), use_fast=False)
    parsed = parser.parse_complete()

    points = vtk.vtkPoints()
    polys = vtk.vtkCellArray()

    if hasattr(points, "SetDataTypeToFloat"):
        points.SetDataTypeToFloat()

    count = 0
    for block in parsed.blocks:
        if max_blocks > 0 and count >= max_blocks:
            break
        (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(block)

        i0 = points.InsertNextPoint(x1, y1, z1)
        i1 = points.InsertNextPoint(x2, y1, z1)
        i2 = points.InsertNextPoint(x2, y2, z1)
        i3 = points.InsertNextPoint(x1, y2, z1)
        i4 = points.InsertNextPoint(x1, y1, z2)
        i5 = points.InsertNextPoint(x2, y1, z2)
        i6 = points.InsertNextPoint(x2, y2, z2)
        i7 = points.InsertNextPoint(x1, y2, z2)

        faces = (
            (i0, i1, i2),
            (i0, i2, i3),
            (i4, i6, i5),
            (i4, i7, i6),
            (i0, i5, i1),
            (i0, i4, i5),
            (i3, i2, i6),
            (i3, i6, i7),
            (i0, i3, i7),
            (i0, i7, i4),
            (i1, i5, i6),
            (i1, i6, i2),
        )
        for a, b, c in faces:
            polys.InsertNextCell(3)
            polys.InsertCellPoint(a)
            polys.InsertCellPoint(b)
            polys.InsertCellPoint(c)

        count += 1

    polydata = vtk.vtkPolyData()
    polydata.SetPoints(points)
    polydata.SetPolys(polys)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(polydata)

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(0.85, 0.85, 0.9)
    actor.GetProperty().SetOpacity(max(0.01, min(opacity, 1.0)))
    actor.GetProperty().SetAmbient(0.4)
    actor.GetProperty().SetDiffuse(0.3)
    actor.GetProperty().SetSpecular(0.2)
    actor.SetPickable(False)
    return actor


def create_renderer(
    dataset: DensityDataset,
    heights: Dict[str, float],
    args,
    cap3d_meta: Optional[Cap3DMetadata],
    via_density_maps: Optional[Dict[str, np.ndarray]],
) -> "vtk.vtkRenderer":
    """Create a renderer with density slices and optional CAP3D mesh."""
    import vtk

    renderer = vtk.vtkRenderer()
    # Use white background when taking screenshot
    if args.screenshot is not None:
        renderer.SetBackground(1.0, 1.0, 1.0)  # White for screenshots
    else:
        renderer.SetBackground(0.08, 0.09, 0.11)  # Dark for interactive use

    x_min, y_min, *_ = dataset.window_bounds

    active_layers: Optional[Set[str]] = None
    if cap3d_meta:
        active_layers = {
            layer
            for layer, stats in cap3d_meta.layer_stats.items()
            if stats.block_count > 0 and stats.layer_type.lower() != "substrate"
        }

    palette_index = 0

    for layer in dataset.layers:
        lower_name = layer.lower()
        if "substrate" in lower_name:
            continue
        if active_layers is not None and layer not in active_layers:
            continue
        density_map = dataset.density_maps[layer]
        if active_layers is None and not np.any(density_map > 0.0):
            continue
        color = PALETTE[palette_index % len(PALETTE)]
        density_actor, outline_actor = create_density_actor(
            layer=layer,
            density_map=density_map,
            pixel_resolution=dataset.pixel_resolution,
            origin_xy=(x_min, y_min),
            z_height=heights[layer],
            color=color,
        )
        renderer.AddActor(density_actor)
        renderer.AddActor(outline_actor)
        palette_index += 1

    if via_density_maps:
        via_color = (160, 160, 160)
        for layer, via_map in sorted(via_density_maps.items()):
            if not np.any(via_map > 0.0):
                continue
            if cap3d_meta:
                stats = cap3d_meta.layer_stats.get(layer)
                if (
                    not stats
                    or stats.block_count == 0
                    or stats.layer_type.lower() == "substrate"
                ):
                    continue
            if layer not in heights:
                continue
            via_color = PALETTE[palette_index % len(PALETTE)]
            density_actor, outline_actor = create_density_actor(
                layer=layer,
                density_map=via_map,
                pixel_resolution=dataset.pixel_resolution,
                origin_xy=(x_min, y_min),
                z_height=heights[layer],
                color=via_color,
            )
            renderer.AddActor(density_actor)
            renderer.AddActor(outline_actor)
            palette_index += 1

    if args.cap3d:
        cap3d_path = Path(args.cap3d)
        try:
            cap3d_actor = build_cap3d_actor(cap3d_path, args.max_blocks, args.cap3d_opacity)
            renderer.AddActor(cap3d_actor)
        except FileNotFoundError as exc:
            raise
        except Exception as exc:
            print(f"WARNING: failed to add CAP3D overlay '{cap3d_path}': {exc}")

    bounds = dataset.window_bounds

    return renderer


def launch_viewer(renderer: "vtk.vtkRenderer", start_angle: float, screenshot: Optional[Path]) -> None:
    """Start the VTK render window interactor."""
    import vtk

    ren_win = vtk.vtkRenderWindow()
    ren_win.AddRenderer(renderer)
    ren_win.SetSize(1280, 960)
    ren_win.SetWindowName("CAP3D Density Viewer")
    ren_win.SetMultiSamples(0)

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(ren_win)
    style = vtk.vtkInteractorStyleTrackballCamera()
    interactor.SetInteractorStyle(style)

    renderer.ResetCamera()
    apply_start_angle(renderer, start_angle)
    camera = renderer.GetActiveCamera()
    if camera is not None:
        camera.Zoom(1.2)

    ren_win.Render()
    capture_initial_screenshot(ren_win, screenshot)
    interactor.Initialize()
    interactor.Start()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize CapBench density maps with optional CAP3D overlay.")
    parser.add_argument("density_map", help="Path to density-map NPZ produced by converters/cnn_cap.py")
    parser.add_argument("--cap3d", help="Optional CAP3D file for faint geometry overlay")
    parser.add_argument("--max-blocks", type=int, default=40000, help="Limit number of CAP3D blocks rendered (0 = no limit)")
    parser.add_argument("--cap3d-opacity", type=float, default=0.18, help="Opacity of CAP3D overlay (0.0-1.0)")
    parser.add_argument("--start-angle", type=float, default=0.0, help="Rotate initial camera azimuth by this many degrees")
    parser.add_argument("--screenshot", type=Path, help="Optional PNG path to save the initial view")
    return parser.parse_args(argv)


def main(args: argparse.Namespace) -> None:
    try:
        dataset = load_density_npz(Path(args.density_map))
    except Exception as exc:
        print(f"ERROR: failed to load density map: {exc}")
        sys.exit(1)

    cap3d_meta: Optional[Cap3DMetadata] = None
    via_density_maps: Optional[Dict[str, np.ndarray]] = None

    if args.cap3d:
        cap3d_path = Path(args.cap3d)
        try:
            cap3d_meta = collect_cap3d_metadata(cap3d_path)
        except FileNotFoundError as exc:
            print(str(exc))
            sys.exit(1)
        except Exception as exc:
            print(f"WARNING: failed to parse CAP3D metadata '{cap3d_path}': {exc}")
            cap3d_meta = None

        if cap3d_meta:
            via_density_maps = generate_via_density_maps(dataset, cap3d_meta)

    layer_heights = compute_layer_heights(dataset, cap3d_meta)

    try:
        renderer = create_renderer(dataset, layer_heights, args, cap3d_meta, via_density_maps)
    except Exception as exc:
        print(f"ERROR: failed to build renderer: {exc}")
        sys.exit(1)

    try:
        launch_viewer(renderer, args.start_angle, args.screenshot)
    except Exception as exc:
        print(f"ERROR: VTK viewer encountered an issue: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main(parse_args())

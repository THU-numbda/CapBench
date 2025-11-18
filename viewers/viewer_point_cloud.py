#!/usr/bin/env python3
"""
VTK viewer for PCT-Cap point clouds (NPZ format).

Usage (inside vtkglx env):
    conda run -n vtkglx python pct_cap_viewer.py datasets/point_clouds/W0.npz \\
        --tech tech/nangate45/nangate45_stack.yaml

The NPZ file must come from pct_cap_prepare_windows.py (or the native
PCT-Cap converter) so that the point cloud contains the standard
feature layout plus the `layer_ids` lookup used for coloring.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import vtk  # type: ignore
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "vtk is required for visualization. Install it in the vtkglx environment:\n"
        "  conda run -n vtkglx pip install vtk\n"
        f"Original error: {exc}"
    ) from exc

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from viewers._common import (
    ensure_repo_root_on_path,
    apply_start_angle,
    capture_initial_screenshot,
)

ensure_repo_root_on_path()

from common.tech_parser import get_conductor_layers
from common.datasets import POINT_CLOUDS_DIR

# Palette shared across viewers
PALETTE_10: Tuple[Tuple[int, int, int], ...] = (
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


def color_from_palette(index: int) -> Tuple[float, float, float]:
    rgb = PALETTE_10[index % len(PALETTE_10)]
    return rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0


@dataclass
class PointCloudData:
    positions: np.ndarray
    dielectrics: np.ndarray
    flux_signs: np.ndarray
    net_ids: np.ndarray
    conductor_names: List[str]
    layer_ids: np.ndarray
    layer_lookup: List[str]
    window_name: str


def load_point_cloud(npz_path: Path) -> PointCloudData:
    if not npz_path.exists():
        raise FileNotFoundError(f"Point cloud not found: {npz_path}")

    data = np.load(npz_path, allow_pickle=True)

    points = data["points"]
    if points.shape[1] < 9:
        raise ValueError(
            f"Expected at least 9 point features, found {points.shape[1]}"
        )

    positions = points[:, 0:3].astype(np.float32)
    dielectrics = points[:, 6].astype(np.float32)
    flux_signs = points[:, 7].astype(np.float32)
    net_ids = points[:, 8].astype(np.int32)

    if "point_net_names" in data:
        conductor_names = list(data["point_net_names"])
    else:
        conductor_names = [f"net_{nid}" for nid in net_ids]

    if "layer_ids" in data:
        layer_ids = data["layer_ids"].astype(np.int32)
    else:
        layer_ids = np.zeros(len(points), dtype=np.int32)

    if "layer_name_lookup" in data:
        lookup_array = data["layer_name_lookup"]
        layer_lookup = [str(item) for item in lookup_array.tolist()]
    else:
        max_id = int(layer_ids.max()) if layer_ids.size else -1
        layer_lookup = [f"layer_{idx}" for idx in range(max_id + 1)]

    window_name = str(data["window_name_str"]) if "window_name_str" in data else npz_path.stem

    return PointCloudData(
        positions=positions,
        dielectrics=dielectrics,
        flux_signs=flux_signs,
        net_ids=net_ids,
        conductor_names=conductor_names,
        layer_ids=layer_ids,
        layer_lookup=layer_lookup,
        window_name=window_name,
    )


def build_layer_color_map(
    layer_lookup: List[str],
    tech_layers: Optional[List[str]],
) -> Dict[int, Tuple[float, float, float]]:
    color_map: Dict[int, Tuple[float, float, float]] = {}
    tech_index: Dict[str, int] = {}

    if tech_layers:
        tech_index = {name.lower(): idx for idx, name in enumerate(tech_layers)}

    for idx, name in enumerate(layer_lookup):
        palette_index = idx
        if tech_layers:
            palette_index = tech_index.get(name.lower(), idx)
        color_map[idx] = color_from_palette(palette_index)

    return color_map


class PointCloudViewer:
    """Simple VTK point cloud viewer with hover tooltips."""

    def __init__(
        self,
        cloud: PointCloudData,
        cap3d_data: Optional[Any] = None,
        sphere_radius: float = 0.03,
    ) -> None:
        self.cloud = cloud
        self.cap3d_data = cap3d_data
        self.sphere_radius = sphere_radius

        # Generate layer colors from CAP3D data - required
        if not cap3d_data or not hasattr(cap3d_data, 'layers'):
            raise ValueError("CAP3D data with layers is required for point cloud visualization")

        self.layer_colors = self._build_layer_colors_from_cap3d(cap3d_data)

        self.renderer: Optional[vtk.vtkRenderer] = None
        self.render_window: Optional[vtk.vtkRenderWindow] = None
        self.interactor: Optional[vtk.vtkRenderWindowInteractor] = None
        self.picker: Optional[vtk.vtkPointPicker] = None

        self.highlight_source: Optional[vtk.vtkSphereSource] = None
        self.highlight_actor: Optional[vtk.vtkActor] = None
        self.info_text: Optional[vtk.vtkTextActor] = None

        # Identify substrate points based on layer information rather than Z-coordinate
        self.substrate_point_indices = self._identify_substrate_points()
        print(f"Identified {len(self.substrate_point_indices)} substrate points")

        # Substrate toggle state (hidden by default)
        self.substrate_visible = False

        # Create separate polydata and actors for substrate and regular points
        self._regular_polydata, self._substrate_polydata = self._build_separate_polydata()
        self._regular_glyph_actor = self._build_glyph_actor(self._regular_polydata)
        self._substrate_glyph_actor = self._build_glyph_actor(self._substrate_polydata)

    # ------------------------------------------------------------------
    def _identify_substrate_points(self) -> set:
        """Identify substrate points as those belonging to the lowest layer ID."""
        if len(self.cloud.positions) == 0:
            return set()

        substrate_indices = set()

        # Check if we have layer information to work with
        if hasattr(self.cloud, 'layer_ids'):
            # Find the minimum layer ID
            min_layer_id = None
            for i, layer_id in enumerate(self.cloud.layer_ids):
                if min_layer_id is None or layer_id < min_layer_id:
                    min_layer_id = layer_id

            if min_layer_id is not None:
                # Collect all points belonging to the lowest layer
                for i, layer_id in enumerate(self.cloud.layer_ids):
                    if layer_id == min_layer_id:
                        substrate_indices.add(i)

        return substrate_indices

    def _build_layer_colors_from_cap3d(self, cap3d_data) -> Dict[int, Tuple[float, float, float]]:
        """Build layer colors from CAP3D layer data using fixed palette."""
        layer_colors = {}

        if hasattr(cap3d_data, 'layers'):
            for layer in cap3d_data.layers:
                layer_id = getattr(layer, 'id', None)
                if layer_id is not None:
                    # Use fixed 10-color palette based on layer ID
                    color = PALETTE_10[layer_id % len(PALETTE_10)]
                    # Convert to 0-1 range for VTK
                    layer_colors[layer_id] = tuple(c / 255.0 for c in color)

        return layer_colors

    def _add_cap3d_geometry_overlay(self) -> None:
        """Add semi-transparent CAP3D geometry overlay to the scene."""
        if not self.cap3d_data or not hasattr(self.cap3d_data, 'blocks'):
            return

        import vtk
        from window_tools.cap3d_parser import Block  # Import Block type

        # Create geometry for CAP3D blocks
        points = vtk.vtkPoints()
        polys = vtk.vtkCellArray()
        colors = vtk.vtkFloatArray()
        colors.SetNumberOfComponents(3)
        colors.SetName("Colors")

        block_count = 0
        for blk in self.cap3d_data.blocks:
            if not isinstance(blk, Block):
                continue

            try:
                # Get block coordinates
                base = blk.base
                v1 = blk.v1
                v2 = blk.v2
                hvec = blk.hvec

                # Calculate box corners
                corners = [
                    base,
                    [base[0] + v1[0], base[1] + v1[1], base[2] + v1[2]],
                    [base[0] + v1[0] + v2[0], base[1] + v1[1] + v2[1], base[2] + v1[2] + v2[2]],
                    [base[0] + v2[0], base[1] + v2[1], base[2] + v2[2]],
                    [base[0] + hvec[0], base[1] + hvec[1], base[2] + hvec[2]],
                    [base[0] + v1[0] + hvec[0], base[1] + v1[1] + hvec[1], base[2] + v1[2] + hvec[2]],
                    [base[0] + v1[0] + v2[0] + hvec[0], base[1] + v1[1] + v2[1] + hvec[1], base[2] + v1[2] + v2[2] + hvec[2]],
                    [base[0] + v2[0] + hvec[0], base[1] + v2[1] + hvec[1], base[2] + v2[2] + hvec[2]],
                ]

                # Add points
                point_ids = []
                for corner in corners:
                    point_id = points.InsertNextPoint(*corner)
                    point_ids.append(point_id)

                # Add faces (12 triangles for a cube)
                faces = [
                    [0, 1, 2], [0, 2, 3],  # bottom
                    [4, 6, 5], [4, 7, 6],  # top
                    [0, 4, 5], [0, 5, 1],  # front
                    [2, 6, 7], [2, 7, 3],  # back
                    [0, 3, 7], [0, 7, 4],  # left
                    [1, 5, 6], [1, 6, 2],  # right
                ]

                for face in faces:
                    triangle = vtk.vtkTriangle()
                    for i, vertex_idx in enumerate(face):
                        triangle.GetPointIds().SetId(i, point_ids[vertex_idx])
                    polys.InsertNextCell(triangle)

                # Set color based on layer
                layer_id = getattr(blk, 'layer', 0)
                if layer_id in self.layer_colors:
                    r, g, b = self.layer_colors[layer_id]
                else:
                    # Default gray color
                    r, g, b = 0.5, 0.5, 0.5

                # Add color for each vertex of this block
                for _ in range(8):  # 8 vertices per block
                    colors.InsertNextTuple3(r, g, b)

                block_count += 1

            except Exception as e:
                print(f"Warning: Could not process block {blk}: {e}")
                continue

        if block_count > 0:
            # Create polydata
            poly_data = vtk.vtkPolyData()
            poly_data.SetPoints(points)
            poly_data.SetPolys(polys)
            poly_data.GetPointData().SetScalars(colors)

            # Create mapper and actor
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(poly_data)

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetOpacity(0.3)  # Semi-transparent
            actor.GetProperty().SetEdgeVisibility(1)
            actor.GetProperty().SetEdgeColor(0.2, 0.2, 0.2)
            actor.GetProperty().SetLineWidth(0.5)

            # Add to renderer
            if self.renderer:
                self.renderer.AddActor(actor)
                print(f"Added semi-transparent CAP3D overlay with {block_count} blocks")

    def _build_separate_polydata(self) -> Tuple[vtk.vtkPolyData, vtk.vtkPolyData]:
        """Build separate polydata for regular and substrate points."""
        # Build regular points polydata
        regular_points = vtk.vtkPoints()
        regular_points.SetDataTypeToFloat()

        # Build substrate points polydata
        substrate_points = vtk.vtkPoints()
        substrate_points.SetDataTypeToFloat()

        # Separate points by substrate status
        regular_indices = []
        substrate_indices_list = []

        for i, position in enumerate(self.cloud.positions):
            if i in self.substrate_point_indices:
                substrate_points.InsertNextPoint(float(position[0]), float(position[1]), float(position[2]))
                substrate_indices_list.append(i)
            else:
                regular_points.InsertNextPoint(float(position[0]), float(position[1]), float(position[2]))
                regular_indices.append(i)

        # Create regular polydata with colors
        regular_poly = vtk.vtkPolyData()
        regular_poly.SetPoints(regular_points)
        regular_poly.GetVerts().InsertNextCell(len(regular_indices))
        for idx in range(len(regular_indices)):
            regular_poly.GetVerts().InsertCellPoint(idx)

        # Add colors to regular polydata
        regular_color_array = vtk.vtkUnsignedCharArray()
        regular_color_array.SetName("colors")
        regular_color_array.SetNumberOfComponents(3)

        for idx in regular_indices:
            layer_id = int(self.cloud.layer_ids[idx])
            rgb = self.layer_colors.get(int(layer_id), color_from_palette(0))
            regular_color_array.InsertNextTuple3(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

        regular_poly.GetPointData().SetScalars(regular_color_array)

        # Create substrate polydata with colors
        substrate_poly = vtk.vtkPolyData()
        substrate_poly.SetPoints(substrate_points)
        substrate_poly.GetVerts().InsertNextCell(len(substrate_indices_list))
        for idx in range(len(substrate_indices_list)):
            substrate_poly.GetVerts().InsertCellPoint(idx)

        # Add colors to substrate polydata
        substrate_color_array = vtk.vtkUnsignedCharArray()
        substrate_color_array.SetName("colors")
        substrate_color_array.SetNumberOfComponents(3)

        for idx in substrate_indices_list:
            layer_id = int(self.cloud.layer_ids[idx])
            rgb = self.layer_colors.get(int(layer_id), color_from_palette(0))
            substrate_color_array.InsertNextTuple3(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

        substrate_poly.GetPointData().SetScalars(substrate_color_array)

        return regular_poly, substrate_poly

    def _build_polydata(self) -> vtk.vtkPolyData:
        points = vtk.vtkPoints()
        points.SetDataTypeToFloat()
        for xyz in self.cloud.positions:
            points.InsertNextPoint(float(xyz[0]), float(xyz[1]), float(xyz[2]))

        poly = vtk.vtkPolyData()
        poly.SetPoints(points)

        color_array = vtk.vtkUnsignedCharArray()
        color_array.SetName("colors")
        color_array.SetNumberOfComponents(3)

        for layer_id in self.cloud.layer_ids:
            rgb = self.layer_colors.get(int(layer_id), color_from_palette(0))
            color_array.InsertNextTuple3(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

        poly.GetPointData().SetScalars(color_array)
        return poly

    def _build_glyph_actor(self, polydata: vtk.vtkPolyData) -> vtk.vtkActor:
        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(self.sphere_radius)
        sphere.SetPhiResolution(12)
        sphere.SetThetaResolution(12)

        mapper = vtk.vtkGlyph3DMapper()
        mapper.SetInputData(polydata)
        mapper.SetSourceConnection(sphere.GetOutputPort())
        mapper.ScalingOff()
        mapper.SetColorModeToDirectScalars()

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetOpacity(0.9)
        return actor

    # ------------------------------------------------------------------
    def start(self, start_angle: float = 0.0, screenshot: Optional[Path] = None) -> None:
        self.renderer = vtk.vtkRenderer()
        # Use white background when taking screenshot
        if screenshot is not None:
            self.renderer.SetBackground(1.0, 1.0, 1.0)  # White for screenshots
        else:
            self.renderer.SetBackground(0.08, 0.09, 0.11)  # Dark for interactive use

        self.render_window = vtk.vtkRenderWindow()
        self.render_window.SetSize(1280, 960)
        self.render_window.SetMultiSamples(0)
        self.render_window.AddRenderer(self.renderer)
        self.render_window.SetWindowName(f"PCT-Cap Point Cloud · {self.cloud.window_name}")

        # Add both regular and substrate actors
        self.renderer.AddActor(self._regular_glyph_actor)
        self.renderer.AddActor(self._substrate_glyph_actor)

        # Set initial substrate visibility (hidden by default)
        self._substrate_glyph_actor.SetVisibility(0)

        # Add semi-transparent CAP3D geometry overlay
        self._add_cap3d_geometry_overlay()

        self._add_highlight_actor()
        self._add_info_text()
        self._add_axes()

        self.renderer.ResetCamera()
        apply_start_angle(self.renderer, start_angle)

        self.interactor = vtk.vtkRenderWindowInteractor()
        self.interactor.SetRenderWindow(self.render_window)
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)

        self.picker = vtk.vtkPointPicker()
        self.picker.PickFromListOn()
        self.picker.AddPickList(self._regular_glyph_actor)
        self.picker.AddPickList(self._substrate_glyph_actor)
        self.interactor.SetPicker(self.picker)
        self.interactor.AddObserver("MouseMoveEvent", self._on_mouse_move)
        self.interactor.AddObserver("KeyPressEvent", self._on_key_press)

        self.render_window.Render()
        capture_initial_screenshot(self.render_window, screenshot)
        self.interactor.Initialize()
        self.interactor.Start()

    def _add_axes(self) -> None:
        return None

    def _add_info_text(self) -> None:
        self.info_text = vtk.vtkTextActor()
        self.info_text.SetInput("Move cursor over a point to inspect metadata\nPress 'M' to toggle substrate visibility")
        text_prop = self.info_text.GetTextProperty()
        text_prop.SetFontSize(18)
        text_prop.SetColor(0.95, 0.95, 0.95)
        self.info_text.SetDisplayPosition(10, 10)
        self.renderer.AddActor2D(self.info_text)

    def _add_highlight_actor(self) -> None:
        self.highlight_source = vtk.vtkSphereSource()
        self.highlight_source.SetRadius(self.sphere_radius * 1.8)
        self.highlight_source.SetPhiResolution(18)
        self.highlight_source.SetThetaResolution(18)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(self.highlight_source.GetOutputPort())

        self.highlight_actor = vtk.vtkActor()
        self.highlight_actor.SetMapper(mapper)
        self.highlight_actor.GetProperty().SetColor(1.0, 1.0, 1.0)
        self.highlight_actor.GetProperty().SetOpacity(0.35)
        self.highlight_actor.VisibilityOff()
        self.renderer.AddActor(self.highlight_actor)

    # ------------------------------------------------------------------
    def _on_mouse_move(self, _obj, _event) -> None:
        if not self.picker or not self.renderer or not self.interactor:
            return

        x, y = self.interactor.GetEventPosition()
        picked = self.picker.Pick(x, y, 0, self.renderer)
        if picked:
            point_id = self.picker.GetPointId()
            if point_id >= 0:
                self._update_hover(point_id)
                self.render_window.Render()  # type: ignore[union-attr]
                return

        self._clear_hover()
        self.render_window.Render()  # type: ignore[union-attr]

    def _update_hover(self, point_id: int) -> None:
        if not self.highlight_source or not self.highlight_actor or not self.info_text:
            return

        position = self.cloud.positions[point_id]
        layer_id = int(self.cloud.layer_ids[point_id])
        layer_name = (
            self.cloud.layer_lookup[layer_id]
            if layer_id < len(self.cloud.layer_lookup)
            else f"layer_{layer_id}"
        )
        conductor = self.cloud.conductor_names[point_id]
        net_id = int(self.cloud.net_ids[point_id])
        flux = float(self.cloud.flux_signs[point_id])
        diel = float(self.cloud.dielectrics[point_id])

        self.highlight_source.SetCenter(float(position[0]), float(position[1]), float(position[2]))
        self.highlight_source.Modified()
        self.highlight_actor.VisibilityOn()

        info = (
            f"{self.cloud.window_name} · {conductor}\n"
            f"Pos ({position[0]:.4f}, {position[1]:.4f}, {position[2]:.4f})\n"
            f"Layer {layer_id} ({layer_name}) · Net {net_id}\n"
            f"εr={diel:.2f} · Φ={flux:+.0f}"
        )
        self.info_text.SetInput(info)

    def _clear_hover(self) -> None:
        if self.highlight_actor:
            self.highlight_actor.VisibilityOff()
        if self.info_text:
            self.info_text.SetInput("Move cursor over a point to inspect metadata")

    def _on_key_press(self, obj, event) -> None:
        """Handle keyboard events for substrate toggling."""
        if not self.interactor:
            return

        key = self.interactor.GetKeySym()
        if key and key.lower() == 'm':
            # Toggle substrate visibility
            self.substrate_visible = not self.substrate_visible
            visibility = 1 if self.substrate_visible else 0

            # Update substrate actor visibility
            self._substrate_glyph_actor.SetVisibility(visibility)

            # Re-render
            if self.render_window:
                self.render_window.Render()

            # Print status message
            status = "shown" if self.substrate_visible else "hidden"
            print(f"Substrate points {status} (press 'M' to toggle)")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def auto_discover_point_cloud(window_id: str) -> Tuple[Optional[Path], Optional[Dict]]:
    """
    Auto-discover point cloud file for a given window ID.

    Args:
        window_id: Window identifier (e.g., 'W0', 'W1')

    Returns:
        Tuple of (npz_file_path, None) or (None, None) if not found
    """
    # Check for NPZ file in datasets/point_clouds/
    npz_path = POINT_CLOUDS_DIR / f"{window_id}.npz"
    if not npz_path.exists():
        return None, None

    return npz_path, None


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Visualize PCT-Cap point clouds (NPZ format).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  # Auto-discovery by window ID (recommended)
  python pct_cap_viewer.py W0
  python pct_cap_viewer.py W0 --cap3d path/to/W0.cap3d

  # Direct file path (legacy)
  python pct_cap_viewer.py path/to/W0.npz
  python pct_cap_viewer.py datasets/point_clouds/W0.npz --cap3d path/to/W0.cap3d

Note: With auto-discovery, files are searched in datasets/point_clouds/
and metadata is loaded from datasets/manifests/<window>.yaml
CAP3D file is required for accurate layer coloring and geometry overlay.
        """
    )

    # Accept either window ID for auto-discovery or direct file path
    parser.add_argument(
        "input_or_window",
        help="Window ID (e.g., W0) for auto-discovery OR path to NPZ point cloud file",
    )
    parser.add_argument(
        "--cap3d",
        type=Path,
        help="Original CAP3D file for accurate layer coloring and geometry overlay",
    )
    parser.add_argument(
        "--start-angle",
        type=float,
        default=0.0,
        help="Rotate initial camera azimuth by this many degrees.",
    )
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="Optional PNG path to save the initial view.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Determine if input is a window ID or file path
    input_path = Path(args.input_or_window)
    npz_file = None
    manifest = None

    if not input_path.exists():
        # Treat as window ID for auto-discovery
        window_id = args.input_or_window
        print(f"Auto-discovering point cloud for window: {window_id}")

        npz_file, _ = auto_discover_point_cloud(window_id)
        if npz_file is None:
            print(f"ERROR: No point cloud found for window '{window_id}' in {POINT_CLOUDS_DIR}")
            print(f"  Expected file: {POINT_CLOUDS_DIR / f'{window_id}.npz'}")
            sys.exit(1)

        print(f"Found point cloud: {npz_file}")

    else:
        # Direct file path mode (legacy)
        if not input_path.suffix == '.npz':
            print(f"ERROR: Expected .npz file, got: {input_path}")
            sys.exit(1)

        npz_file = input_path
        print(f"Loading point cloud from: {npz_file}")

    # Load the point cloud
    cloud = load_point_cloud(npz_file)

    # Load CAP3D file for accurate layer coloring and geometry overlay
    cap3d_data = None
    if args.cap3d and Path(args.cap3d).exists():
        try:
            from window_tools.cap3d_parser import parse_cap3d_file
            cap3d_data = parse_cap3d_file(str(args.cap3d))
            print(f"Loaded CAP3D file: {args.cap3d}")
        except Exception as e:
            print(f"Warning: Could not load CAP3D file {args.cap3d}: {e}")
            print("Using default layer coloring.")
            cap3d_data = None
    elif args.cap3d:
        print(f"Warning: CAP3D file not found: {args.cap3d}")
        print("Using default layer coloring.")

    viewer = PointCloudViewer(cloud, cap3d_data=cap3d_data)
    viewer.start(start_angle=args.start_angle, screenshot=args.screenshot)


if __name__ == "__main__":  # pragma: no cover
    main()

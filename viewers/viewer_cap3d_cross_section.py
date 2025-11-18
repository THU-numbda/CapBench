#!/usr/bin/env python3
"""
Interactive VTK viewer for CAP3D cross-section visualization.

This tool loads a CAP3D file and displays it with an interactive cutting plane
that can be moved through the depth axis using arrow keys. The plane shows
layer-colored intersections with the conductors.

Usage:
    python viewer_cap3d_cross_section.py design.cap3d [--step-size 0.2] [--plane-opacity 0.8]
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

from window_tools.cap3d_parser import StreamingCap3DParser

# Color palette reused from viewer_cap3d.py
PALETTE_10: Tuple[Tuple[int, int, int], ...] = (
    (56, 128, 255),   # cobalt
    (0, 201, 167),    # teal
    (255, 171, 64),   # amber
    (255, 99, 132),   # coral
    (156, 39, 176),   # violet
    (0, 188, 212),    # cyan
    (139, 195, 74),   # lime
    (255, 202, 40),   # gold
    (121, 134, 203),  # periwinkle
    (244, 67, 54),    # red
    (0, 150, 136),    # jade
    (103, 58, 183),   # indigo
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


def _color_for_block(blk) -> Tuple[int, int, int]:
    """Choose a color from a fixed 10-color palette - matches viewer_cap3d.py exactly."""
    # Try to read explicit layer index
    for attr in ('layer', 'layer_index', 'layer_num', 'layer_number'):
        v = getattr(blk, attr, None)
        if isinstance(v, int):
            return PALETTE_10[v % len(PALETTE_10)]
        if isinstance(v, str) and v.isdigit():
            idx = int(v) % len(PALETTE_10)
            return PALETTE_10[idx]

    # Fallback: stable color from group key (L:n or Z:bucket)
    key = _group_key_for_layer(blk)
    return PALETTE_10[hash(key) % len(PALETTE_10)]


def _group_key_for_layer(blk) -> str:
    """Group by metal layer if available; otherwise by Z height bucket - matches viewer_cap3d.py exactly."""
    # Get explicit layer index
    v = getattr(blk, 'layer', None)
    if v is not None:
        return f"L:{v}"

    # Fallback: Use Z height bucket when no layer is defined
    try:
        # Calculate top Z coordinate (base.z + hvec.z)
        base_z = float(blk.base[2])
        height_z = float(blk.hvec[2])
        top_z = base_z + height_z
        # Round to nearest 0.1 units to create discrete height buckets
        z_bucket = round(top_z * 10) / 10
        return f"Z:{z_bucket}"
    except Exception:
        # If height calculation fails, use a default group
        return "Z:unknown"


class CrossSectionViewer:
    """Interactive CAP3D cross-section viewer with movable cutting plane."""

    def __init__(self, cap3d_file: str, step_size: float = 0.2, plane_opacity: float = 0.8):
        self.cap3d_file = Path(cap3d_file)
        self.step_size = step_size
        self.plane_opacity = plane_opacity

        # CAP3D data
        self.blocks = []
        self.layers = {}
        self.window_bounds = None
        self.design_bounds = None

        # VTK objects
        self.renderer = None
        self.render_window = None
        self.interactor = None

        # Cutting plane
        self.plane = None
        self.plane_actor = None
        self.plane_position = 0.0  # Position along X axis for vertical plane
        self.min_coord = 0.0
        self.max_coord = 0.0

        # Main geometry actors
        self.main_actors = []
        self.main_visible = True

        # Continuous movement
        self.movement_speed = 2.0  # Units per second (faster movement)
        self.keys_pressed = set()
        self.last_update_time = None

        # Load and process data
        self._load_cap3d_data()
        self._calculate_design_bounds()
        self._initialize_plane_position()

    def _load_cap3d_data(self):
        """Load CAP3D file and extract blocks and layers."""
        parser = StreamingCap3DParser(str(self.cap3d_file), use_fast=False)
        parsed = parser.parse_complete()

        self.blocks = parsed.blocks
        self.layers = {idx: layer for idx, layer in enumerate(parsed.layers)}

        # Extract window bounds if available
        if parsed.window:
            w = parsed.window
            wx1 = float(min(w.v1[0], w.v2[0]))
            wy1 = float(min(w.v1[1], w.v2[1]))
            wz1 = float(min(w.v1[2], w.v2[2]))
            wx2 = float(max(w.v1[0], w.v2[0]))
            wy2 = float(max(w.v1[1], w.v2[1]))
            wz2 = float(max(w.v1[2], w.v2[2]))
            self.window_bounds = (wx1, wy1, wz1, wx2, wy2, wz2)

    def _calculate_design_bounds(self):
        """Calculate the overall bounds of all conductor blocks."""
        if not self.blocks:
            return

        x_coords, y_coords, z_coords = [], [], []

        for block in self.blocks:
            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(block)
            x_coords.extend([x1, x2])
            y_coords.extend([y1, y2])
            z_coords.extend([z1, z2])

        self.design_bounds = (
            min(x_coords), min(y_coords), min(z_coords),
            max(x_coords), max(y_coords), max(z_coords)
        )

        # Set bounds for X-axis movement (vertical plane)
        self.min_coord = self.design_bounds[0]  # Min X
        self.max_coord = self.design_bounds[3]  # Max X

    def _initialize_plane_position(self):
        """Set initial cutting plane position at 40% of design width."""
        if self.min_coord >= self.max_coord:
            self.plane_position = 0.0
        else:
            width = self.max_coord - self.min_coord
            self.plane_position = self.min_coord + 0.4 * width  # 40% from left

    def _create_main_geometry(self):
        """Create translucent main geometry actors - following viewer_cap3d.py patterns."""
        import vtk

        # Identify substrate conductor (first conductor - typically lowest Z conductor)
        substrate_conductor_name = None
        conductor_blocks = [blk for blk in self.blocks if getattr(blk, 'type', 'conductor') == 'conductor']
        if conductor_blocks:
            # Find the conductor with the lowest Z coordinate (substrate)
            lowest_z = float('inf')
            for blk in conductor_blocks:
                try:
                    base_z = float(blk.base[2])
                    if base_z < lowest_z:
                        lowest_z = base_z
                        substrate_conductor_name = blk.parent_name
                except Exception:
                    continue
            print(f"Identified substrate conductor: {substrate_conductor_name} at Z={lowest_z}")

        # Get window bounds for span detection
        window_bounds = None
        if self.window_bounds:
            wx1, wy1, wz1, wx2, wy2, wz2 = self.window_bounds
            window_bounds = (wx1, wy1, wx2, wy2)

        def _is_spanning_element(blk) -> bool:
            """Check if element spans most of the window in X and Y dimensions."""
            if window_bounds is None:
                return False
            wx1, wy1, wx2, wy2 = window_bounds
            window_width = wx2 - wx1
            window_height = wy2 - wy1

            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(blk)
            elem_width = x2 - x1
            elem_height = y2 - y1

            # Consider spanning if element covers at least 80% of window in both X and Y
            spans_x = elem_width >= 0.8 * window_width
            spans_y = elem_height >= 0.8 * window_height
            return spans_x and spans_y

        # Use instanced rendering for performance (following viewer_cap3d.py exactly)
        centers = vtk.vtkPoints()
        if hasattr(centers, "SetDataTypeToFloat"):
            centers.SetDataTypeToFloat()

        scale_arr = vtk.vtkFloatArray()
        scale_arr.SetName("scale")
        scale_arr.SetNumberOfComponents(3)

        colors_arr = vtk.vtkFloatArray()
        colors_arr.SetName("RGB")  # VTK recognizes "RGB" as special
        colors_arr.SetNumberOfComponents(3)

        # Separate arrays for substrate and spanning elements
        g_centers = vtk.vtkPoints()
        if hasattr(g_centers, "SetDataTypeToFloat"):
            g_centers.SetDataTypeToFloat()
        g_scale_arr = vtk.vtkFloatArray()
        g_scale_arr.SetName("scale")
        g_scale_arr.SetNumberOfComponents(3)
        g_colors_arr = vtk.vtkFloatArray()
        g_colors_arr.SetName("RGB")
        g_colors_arr.SetNumberOfComponents(3)

        s_centers = vtk.vtkPoints()
        if hasattr(s_centers, "SetDataTypeToFloat"):
            s_centers.SetDataTypeToFloat()
        s_scale_arr = vtk.vtkFloatArray()
        s_scale_arr.SetName("scale")
        s_scale_arr.SetNumberOfComponents(3)
        s_colors_arr = vtk.vtkFloatArray()
        s_colors_arr.SetName("RGB")
        s_colors_arr.SetNumberOfComponents(3)

        count = 0
        gcount = 0
        scount = 0
        max_blocks = 100000  # Default limit

        for blk in self.blocks:
            if count >= max_blocks:
                break
            if getattr(blk, 'type', 'conductor') == 'medium':
                continue  # Skip medium blocks like in viewer_cap3d.py

            # Robust center/scale via bounds to handle any sign on vectors
            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(blk)
            cx = 0.5 * (x1 + x2)
            cy = 0.5 * (y1 + y2)
            cz = 0.5 * (z1 + z2)
            sx = abs(x2 - x1)
            sy = abs(y2 - y1)
            sz = abs(z2 - z1)

            # Check if this block belongs to the substrate conductor
            is_substrate = substrate_conductor_name and blk.parent_name == substrate_conductor_name
            # Check if this element spans most of the window
            is_spanning = _is_spanning_element(blk)

            r, g, b = _color_for_block(blk)
            # Convert to 0-1 range for float arrays
            rf, gf, bf = r / 255.0, g / 255.0, b / 255.0

            if is_substrate:
                s_centers.InsertNextPoint(cx, cy, cz)
                s_scale_arr.InsertNextTuple3(sx, sy, sz)
                s_colors_arr.InsertNextTuple3(rf, gf, bf)
                scount += 1
            elif is_spanning:
                g_centers.InsertNextPoint(cx, cy, cz)
                g_scale_arr.InsertNextTuple3(sx, sy, sz)
                g_colors_arr.InsertNextTuple3(rf, gf, bf)
                gcount += 1
            else:
                centers.InsertNextPoint(cx, cy, cz)
                scale_arr.InsertNextTuple3(sx, sy, sz)
                colors_arr.InsertNextTuple3(rf, gf, bf)
                count += 1

        if centers.GetNumberOfPoints() == 0 and g_centers.GetNumberOfPoints() == 0 and s_centers.GetNumberOfPoints() == 0:
            return

        # Create cube source
        cube = vtk.vtkCubeSource()
        cube.SetXLength(1.0)
        cube.SetYLength(1.0)
        cube.SetZLength(1.0)
        cube.SetCenter(0.0, 0.0, 0.0)
        cube.Update()

        # Create normals for lighting
        c_norm = vtk.vtkPolyDataNormals()
        c_norm.SetInputConnection(cube.GetOutputPort())
        c_norm.ComputeCellNormalsOn()
        c_norm.ComputePointNormalsOff()
        c_norm.SplittingOff()
        c_norm.ConsistencyOn()
        c_norm.AutoOrientNormalsOn()
        c_norm.Update()

        # Main conductors
        if centers.GetNumberOfPoints() > 0:
            inst_pd = vtk.vtkPolyData()
            inst_pd.SetPoints(centers)
            inst_pd.GetPointData().AddArray(scale_arr)
            inst_pd.GetPointData().AddArray(colors_arr)
            inst_pd.GetPointData().SetScalars(colors_arr)
            if hasattr(inst_pd.GetPointData(), 'SetActiveScalars'):
                inst_pd.GetPointData().SetActiveScalars("RGB")
            if hasattr(inst_pd.GetPointData(), 'SetVectors'):
                inst_pd.GetPointData().SetVectors(scale_arr)

            try:
                gmapper = vtk.vtkGlyph3DMapper()
                gmapper.SetInputData(inst_pd)
                gmapper.SetSourceConnection(c_norm.GetOutputPort())
                if hasattr(gmapper, 'OrientOff'):
                    gmapper.OrientOff()
                if hasattr(gmapper, 'SetScaling'):
                    gmapper.SetScaling(True)
                if hasattr(gmapper, 'SetScaleFactor'):
                    gmapper.SetScaleFactor(1.0)
                # Require component-wise scaling, otherwise fall back to vtkGlyph3D
                if hasattr(gmapper, 'SetScaleModeToScaleByComponents'):
                    gmapper.SetScaleModeToScaleByComponents()
                else:
                    raise RuntimeError('Glyph3DMapper lacks ScaleByComponents')
                # Bind scale array with association if supported
                try:
                    from vtkmodules.vtkCommonDataModel import vtkDataObject
                    if hasattr(gmapper, 'SetScaleArray'):
                        try:
                            gmapper.SetScaleArray(vtkDataObject.FIELD_ASSOCIATION_POINTS, "scale")
                        except TypeError:
                            gmapper.SetScaleArray("scale")
                except Exception:
                    if hasattr(gmapper, 'SetScaleArray'):
                        gmapper.SetScaleArray("scale")
                # Use DirectScalars for RGB data
                if hasattr(gmapper, 'SetColorModeToDirectScalars'):
                    gmapper.SetColorModeToDirectScalars()
                if hasattr(gmapper, 'SetScalarModeToUsePointFieldData'):
                    gmapper.SetScalarModeToUsePointFieldData()
                    if hasattr(gmapper, 'SelectColorArray'):
                        gmapper.SelectColorArray("RGB")
                else:
                    gmapper.SetScalarModeToUsePointData()
                if hasattr(gmapper, 'SetInterpolateScalarsBeforeMapping'):
                    gmapper.SetInterpolateScalarsBeforeMapping(0)
                gmapper.SetScalarVisibility(1)

                c_actor = vtk.vtkActor()
                c_actor.SetMapper(gmapper)
                c_actor.GetProperty().LightingOn()
                c_actor.GetProperty().SetInterpolationToFlat()
                c_actor.GetProperty().SetDiffuse(0.9)
                c_actor.GetProperty().SetSpecular(0.1)
                c_actor.GetProperty().SetOpacity(1.0)  # Fully opaque
                c_actor.GetProperty().BackfaceCullingOn()
                c_actor.SetPickable(False)

                self.main_actors.append(c_actor)

            except Exception:
                # Fallback to classic rendering
                print("Warning: Instanced rendering not available, using fallback")
                self._create_classic_main_geometry()
                return

        # Spanning elements
        if g_centers.GetNumberOfPoints() > 0:
            g_inst_pd = vtk.vtkPolyData()
            g_inst_pd.SetPoints(g_centers)
            g_inst_pd.GetPointData().AddArray(g_scale_arr)
            g_inst_pd.GetPointData().AddArray(g_colors_arr)
            g_inst_pd.GetPointData().SetScalars(g_colors_arr)
            if hasattr(g_inst_pd.GetPointData(), 'SetActiveScalars'):
                g_inst_pd.GetPointData().SetActiveScalars("RGB")
            if hasattr(g_inst_pd.GetPointData(), 'SetVectors'):
                g_inst_pd.GetPointData().SetVectors(g_scale_arr)

            try:
                g_gmapper = vtk.vtkGlyph3DMapper()
                g_gmapper.SetInputData(g_inst_pd)
                g_gmapper.SetSourceConnection(c_norm.GetOutputPort())
                if hasattr(g_gmapper, 'OrientOff'):
                    g_gmapper.OrientOff()
                if hasattr(g_gmapper, 'SetScaling'):
                    g_gmapper.SetScaling(True)
                if hasattr(g_gmapper, 'SetScaleFactor'):
                    g_gmapper.SetScaleFactor(1.0)
                if hasattr(g_gmapper, 'SetScaleModeToScaleByComponents'):
                    g_gmapper.SetScaleModeToScaleByComponents()
                # Bind scale array with association if supported
                try:
                    from vtkmodules.vtkCommonDataModel import vtkDataObject
                    if hasattr(g_gmapper, 'SetScaleArray'):
                        try:
                            g_gmapper.SetScaleArray(vtkDataObject.FIELD_ASSOCIATION_POINTS, "scale")
                        except TypeError:
                            g_gmapper.SetScaleArray("scale")
                except Exception:
                    if hasattr(g_gmapper, 'SetScaleArray'):
                        g_gmapper.SetScaleArray("scale")
                # Use DirectScalars for RGB data
                if hasattr(g_gmapper, 'SetColorModeToDirectScalars'):
                    g_gmapper.SetColorModeToDirectScalars()
                if hasattr(g_gmapper, 'SetScalarModeToUsePointFieldData'):
                    g_gmapper.SetScalarModeToUsePointFieldData()
                    if hasattr(g_gmapper, 'SelectColorArray'):
                        g_gmapper.SelectColorArray("RGB")
                else:
                    g_gmapper.SetScalarModeToUsePointData()
                if hasattr(g_gmapper, 'SetInterpolateScalarsBeforeMapping'):
                    g_gmapper.SetInterpolateScalarsBeforeMapping(0)
                g_gmapper.SetScalarVisibility(1)

                g_actor = vtk.vtkActor()
                g_actor.SetMapper(g_gmapper)
                g_actor.GetProperty().LightingOn()
                g_actor.GetProperty().SetInterpolationToFlat()
                g_actor.GetProperty().SetDiffuse(0.9)
                g_actor.GetProperty().SetSpecular(0.1)
                g_actor.GetProperty().SetOpacity(1.0)  # Fully opaque
                g_actor.GetProperty().BackfaceCullingOn()
                g_actor.SetPickable(False)

                self.main_actors.append(g_actor)

            except Exception:
                pass  # Skip if instanced fails

        # Substrate conductor
        if s_centers.GetNumberOfPoints() > 0:
            s_inst_pd = vtk.vtkPolyData()
            s_inst_pd.SetPoints(s_centers)
            s_inst_pd.GetPointData().AddArray(s_scale_arr)
            s_inst_pd.GetPointData().AddArray(s_colors_arr)
            s_inst_pd.GetPointData().SetScalars(s_colors_arr)
            if hasattr(s_inst_pd.GetPointData(), 'SetActiveScalars'):
                s_inst_pd.GetPointData().SetActiveScalars("RGB")
            if hasattr(s_inst_pd.GetPointData(), 'SetVectors'):
                s_inst_pd.GetPointData().SetVectors(s_scale_arr)

            try:
                s_gmapper = vtk.vtkGlyph3DMapper()
                s_gmapper.SetInputData(s_inst_pd)
                s_gmapper.SetSourceConnection(c_norm.GetOutputPort())
                if hasattr(s_gmapper, 'OrientOff'):
                    s_gmapper.OrientOff()
                if hasattr(s_gmapper, 'SetScaling'):
                    s_gmapper.SetScaling(True)
                if hasattr(s_gmapper, 'SetScaleFactor'):
                    s_gmapper.SetScaleFactor(1.0)
                if hasattr(s_gmapper, 'SetScaleModeToScaleByComponents'):
                    s_gmapper.SetScaleModeToScaleByComponents()
                # Bind scale array with association if supported
                try:
                    from vtkmodules.vtkCommonDataModel import vtkDataObject
                    if hasattr(s_gmapper, 'SetScaleArray'):
                        try:
                            s_gmapper.SetScaleArray(vtkDataObject.FIELD_ASSOCIATION_POINTS, "scale")
                        except TypeError:
                            s_gmapper.SetScaleArray("scale")
                except Exception:
                    if hasattr(s_gmapper, 'SetScaleArray'):
                        s_gmapper.SetScaleArray("scale")
                # Use DirectScalars for RGB data
                if hasattr(s_gmapper, 'SetColorModeToDirectScalars'):
                    s_gmapper.SetColorModeToDirectScalars()
                if hasattr(s_gmapper, 'SetScalarModeToUsePointFieldData'):
                    s_gmapper.SetScalarModeToUsePointFieldData()
                    if hasattr(s_gmapper, 'SelectColorArray'):
                        s_gmapper.SelectColorArray("RGB")
                else:
                    s_gmapper.SetScalarModeToUsePointData()
                if hasattr(s_gmapper, 'SetInterpolateScalarsBeforeMapping'):
                    s_gmapper.SetInterpolateScalarsBeforeMapping(0)
                s_gmapper.SetScalarVisibility(1)

                s_actor = vtk.vtkActor()
                s_actor.SetMapper(s_gmapper)
                s_actor.GetProperty().LightingOn()
                s_actor.GetProperty().SetInterpolationToFlat()
                s_actor.GetProperty().SetDiffuse(0.9)
                s_actor.GetProperty().SetSpecular(0.1)
                s_actor.GetProperty().SetOpacity(1.0)  # Fully opaque
                s_actor.GetProperty().BackfaceCullingOn()
                s_actor.SetPickable(False)

                self.main_actors.append(s_actor)

            except Exception:
                pass  # Skip if instanced fails

    def _create_classic_main_geometry(self):
        """Fallback classic rendering for main geometry."""
        import vtk

        points = vtk.vtkPoints()
        if hasattr(points, "SetDataTypeToFloat"):
            points.SetDataTypeToFloat()

        polys = vtk.vtkCellArray()
        colors = vtk.vtkUnsignedCharArray()
        colors.SetName("colors")
        colors.SetNumberOfComponents(3)

        count = 0
        for block in self.blocks:
            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(block)
            color = _color_for_block(block)

            # Define cube vertices
            i0 = points.InsertNextPoint(x1, y1, z1)
            i1 = points.InsertNextPoint(x2, y1, z1)
            i2 = points.InsertNextPoint(x2, y2, z1)
            i3 = points.InsertNextPoint(x1, y2, z1)
            i4 = points.InsertNextPoint(x1, y1, z2)
            i5 = points.InsertNextPoint(x2, y1, z2)
            i6 = points.InsertNextPoint(x2, y2, z2)
            i7 = points.InsertNextPoint(x1, y2, z2)

            # Define cube faces
            faces = [
                (i0, i1, i2), (i0, i2, i3),
                (i4, i6, i5), (i4, i7, i6),
                (i0, i5, i1), (i0, i4, i5),
                (i3, i2, i6), (i3, i6, i7),
                (i0, i3, i7), (i0, i7, i4),
                (i1, i5, i6), (i1, i6, i2),
            ]

            for a, b, c in faces:
                polys.InsertNextCell(3)
                polys.InsertCellPoint(a)
                polys.InsertCellPoint(b)
                polys.InsertCellPoint(c)
                colors.InsertNextTuple3(*color)

            count += 1

        if points.GetNumberOfPoints() == 0:
            return

        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(polys)
        polydata.GetCellData().SetScalars(colors)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        if hasattr(mapper, 'SetInterpolateScalarsBeforeMapping'):
            mapper.SetInterpolateScalarsBeforeMapping(0)
        if hasattr(mapper, 'SetColorModeToDirectScalars'):
            mapper.SetColorModeToDirectScalars()
        if hasattr(mapper, 'SetScalarModeToUseCellData'):
            mapper.SetScalarModeToUseCellData()
        mapper.SetScalarVisibility(1)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().LightingOn()
        actor.GetProperty().SetInterpolationToFlat()
        actor.GetProperty().SetDiffuse(0.9)
        actor.GetProperty().SetSpecular(0.1)
        actor.GetProperty().SetOpacity(1.0)  # Fully opaque
        actor.GetProperty().BackfaceCullingOn()
        actor.SetPickable(False)

        self.main_actors.append(actor)

    def _create_cutting_plane(self):
        """Create the interactive vertical cutting plane."""
        import vtk

        if not self.design_bounds:
            return

        # Create vertical plane geometry (YZ plane perpendicular to substrate)
        x_min, y_min, z_min, x_max, y_max, z_max = self.design_bounds

        # Create a large vertical plane that covers the entire design height and depth
        plane_points = vtk.vtkPoints()
        plane_points.InsertNextPoint(self.plane_position, y_min, z_min)
        plane_points.InsertNextPoint(self.plane_position, y_max, z_min)
        plane_points.InsertNextPoint(self.plane_position, y_max, z_max)
        plane_points.InsertNextPoint(self.plane_position, y_min, z_max)

        # Create plane polygon
        plane_poly = vtk.vtkPolygon()
        plane_poly.GetPointIds().SetNumberOfIds(4)
        for i in range(4):
            plane_poly.GetPointIds().SetId(i, i)

        plane_polys = vtk.vtkCellArray()
        plane_polys.InsertNextCell(plane_poly)

        plane_polydata = vtk.vtkPolyData()
        plane_polydata.SetPoints(plane_points)
        plane_polydata.SetPolys(plane_polys)

        # Create plane mapper and actor
        plane_mapper = vtk.vtkPolyDataMapper()
        plane_mapper.SetInputData(plane_polydata)

        self.plane_actor = vtk.vtkActor()
        self.plane_actor.SetMapper(plane_mapper)
        self.plane_actor.GetProperty().SetColor(0.3, 0.3, 0.3)  # Gray
        self.plane_actor.GetProperty().SetOpacity(self.plane_opacity)
        self.plane_actor.GetProperty().SetAmbient(1.0)
        self.plane_actor.GetProperty().SetDiffuse(0.0)
        self.plane_actor.GetProperty().SetSpecular(0.0)
        self.plane_actor.SetPickable(False)

        # Create white edge outline for the plane
        self.plane_edge_actor = self._create_plane_edge_actor()

    def _create_plane_edge_actor(self):
        """Create a white edge outline for the cutting plane."""
        import vtk

        if not self.design_bounds:
            return None

        x_min, y_min, z_min, x_max, y_max, z_max = self.design_bounds

        # Create edge lines for the vertical plane
        edge_points = vtk.vtkPoints()
        edge_points.InsertNextPoint(self.plane_position, y_min, z_min)
        edge_points.InsertNextPoint(self.plane_position, y_max, z_min)
        edge_points.InsertNextPoint(self.plane_position, y_max, z_max)
        edge_points.InsertNextPoint(self.plane_position, y_min, z_max)

        # Create line segments for edges
        lines = vtk.vtkCellArray()
        # Bottom edge
        lines.InsertNextCell(2)
        lines.InsertCellPoint(0)
        lines.InsertCellPoint(1)
        # Right edge
        lines.InsertNextCell(2)
        lines.InsertCellPoint(1)
        lines.InsertCellPoint(2)
        # Top edge
        lines.InsertNextCell(2)
        lines.InsertCellPoint(2)
        lines.InsertCellPoint(3)
        # Left edge
        lines.InsertNextCell(2)
        lines.InsertCellPoint(3)
        lines.InsertCellPoint(0)

        edge_polydata = vtk.vtkPolyData()
        edge_polydata.SetPoints(edge_points)
        edge_polydata.SetLines(lines)

        edge_mapper = vtk.vtkPolyDataMapper()
        edge_mapper.SetInputData(edge_polydata)

        edge_actor = vtk.vtkActor()
        edge_actor.SetMapper(edge_mapper)
        edge_actor.GetProperty().SetColor(1.0, 1.0, 1.0)  # White
        edge_actor.GetProperty().SetLineWidth(3.0)  # Thicker lines
        edge_actor.GetProperty().SetOpacity(1.0)  # Solid white edges
        edge_actor.GetProperty().SetAmbient(1.0)
        edge_actor.GetProperty().SetDiffuse(0.0)
        edge_actor.GetProperty().SetSpecular(0.0)
        edge_actor.SetPickable(False)

        return edge_actor

    def _update_cutting_plane(self):
        """Update the vertical cutting plane position and intersections."""
        import vtk

        if not self.design_bounds or not self.plane_actor:
            return

        x_min, y_min, z_min, x_max, y_max, z_max = self.design_bounds

        # Update vertical plane geometry
        plane_points = vtk.vtkPoints()
        plane_points.InsertNextPoint(self.plane_position, y_min, z_min)
        plane_points.InsertNextPoint(self.plane_position, y_max, z_min)
        plane_points.InsertNextPoint(self.plane_position, y_max, z_max)
        plane_points.InsertNextPoint(self.plane_position, y_min, z_max)

        plane_poly = vtk.vtkPolygon()
        plane_poly.GetPointIds().SetNumberOfIds(4)
        for i in range(4):
            plane_poly.GetPointIds().SetId(i, i)

        plane_polys = vtk.vtkCellArray()
        plane_polys.InsertNextCell(plane_poly)

        plane_polydata = vtk.vtkPolyData()
        plane_polydata.SetPoints(plane_points)
        plane_polydata.SetPolys(plane_polys)

        # Find intersected blocks and create colored intersection geometry
        intersection_actors = self._create_intersection_geometry()

        # Update plane actor
        plane_mapper = vtk.vtkPolyDataMapper()
        plane_mapper.SetInputData(plane_polydata)
        self.plane_actor.SetMapper(plane_mapper)

        # Update plane edge
        if hasattr(self, 'plane_edge_actor') and self.plane_edge_actor:
            # Remove old edge actor from renderer
            if self.renderer:
                self.renderer.RemoveActor(self.plane_edge_actor)
            # Create new edge actor
            self.plane_edge_actor = self._create_plane_edge_actor()
            if self.plane_edge_actor and self.renderer:
                self.renderer.AddActor(self.plane_edge_actor)

        # Remove old intersection actors and add new ones
        self._remove_intersection_actors()
        for actor in intersection_actors:
            self.renderer.AddActor(actor)

        # Store intersection actors for cleanup
        self.intersection_actors = intersection_actors

        # Trigger render
        if self.render_window:
            self.render_window.Render()

    def _create_intersection_geometry(self) -> List:
        """Create colored geometry for blocks intersected by the vertical cutting plane."""
        import vtk

        intersection_actors = []

        if not self.design_bounds:
            return intersection_actors

        # Group intersected blocks by layer color
        colored_groups = {}

        for block in self.blocks:
            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(block)

            # Check if block intersects with the vertical cutting plane (X position)
            if x1 <= self.plane_position <= x2:
                color = _color_for_block(block)
                color_key = tuple(color)

                if color_key not in colored_groups:
                    colored_groups[color_key] = []
                colored_groups[color_key].append(block)

        # Create geometry for each color group
        for color, blocks in colored_groups.items():
            actor = self._create_intersection_group(blocks, color)
            if actor:
                intersection_actors.append(actor)

        return intersection_actors

    def _create_intersection_group(self, blocks: List, color: Tuple[int, int, int]) -> Optional:
        """Create a single actor for a group of blocks with the same color."""
        import vtk

        if not blocks:
            return None

        points = vtk.vtkPoints()
        if hasattr(points, "SetDataTypeToFloat"):
            points.SetDataTypeToFloat()

        polys = vtk.vtkCellArray()

        for block in blocks:
            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(block)

            # Create intersection geometry for vertical plane (YZ plane)
            # Create a thin slab at the plane position
            thickness = 0.01  # Small thickness for visibility

            x_plane = self.plane_position

            # Define intersection slab vertices
            i0 = points.InsertNextPoint(x_plane - thickness/2, y1, z1)
            i1 = points.InsertNextPoint(x_plane + thickness/2, y1, z1)
            i2 = points.InsertNextPoint(x_plane + thickness/2, y2, z1)
            i3 = points.InsertNextPoint(x_plane - thickness/2, y2, z1)
            i4 = points.InsertNextPoint(x_plane - thickness/2, y1, z2)
            i5 = points.InsertNextPoint(x_plane + thickness/2, y1, z2)
            i6 = points.InsertNextPoint(x_plane + thickness/2, y2, z2)
            i7 = points.InsertNextPoint(x_plane - thickness/2, y2, z2)

            # Define faces
            faces = [
                (i0, i1, i2), (i0, i2, i3),  # Front face (z=z1)
                (i4, i6, i5), (i4, i7, i6),  # Back face (z=z2)
                (i0, i5, i1), (i0, i4, i5),  # Bottom face (y=y1)
                (i3, i2, i6), (i3, i6, i7),  # Top face (y=y2)
                (i0, i3, i7), (i0, i7, i4),  # Left face (x=x_plane - thickness/2)
                (i1, i5, i6), (i1, i6, i2),  # Right face (x=x_plane + thickness/2)
            ]

            for a, b, c in faces:
                polys.InsertNextCell(3)
                polys.InsertCellPoint(a)
                polys.InsertCellPoint(b)
                polys.InsertCellPoint(c)

        if points.GetNumberOfPoints() == 0:
            return None

        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(polys)

        # Add normals for better lighting
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(polydata)
        normals.ComputeCellNormalsOn()
        normals.ComputePointNormalsOff()
        normals.SplittingOff()
        normals.ConsistencyOn()
        normals.AutoOrientNormalsOn()
        normals.Update()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(normals.GetOutput())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        # Set color and properties
        r, g, b = (c / 255.0 for c in color)
        actor.GetProperty().SetColor(r, g, b)
        actor.GetProperty().SetOpacity(1.0)  # Solid for intersections
        actor.GetProperty().SetAmbient(0.4)
        actor.GetProperty().SetDiffuse(0.6)
        actor.GetProperty().SetSpecular(0.2)
        actor.GetProperty().SetInterpolationToFlat()
        actor.GetProperty().BackfaceCullingOn()
        actor.SetPickable(False)

        return actor

    def _remove_intersection_actors(self):
        """Remove all intersection actors from the renderer."""
        if hasattr(self, 'intersection_actors'):
            for actor in getattr(self, 'intersection_actors', []):
                if actor and self.renderer:
                    self.renderer.RemoveActor(actor)
        self.intersection_actors = []

    def _setup_keyboard_callbacks(self):
        """Setup keyboard event handlers for continuous plane movement and toggling."""
        import time

        def _key_press_callback(obj, event):
            key = self.interactor.GetKeySym()

            if key in ['Up', 'Left']:
                # Move plane left/right (X direction)
                self.keys_pressed.add(key)
                if self.last_update_time is None:
                    self.last_update_time = time.time()

            elif key in ['Down', 'Right']:
                # Move plane left/right (X direction)
                self.keys_pressed.add(key)
                if self.last_update_time is None:
                    self.last_update_time = time.time()

            elif key and key.lower() == 'm':
                # Toggle main geometry visibility
                self.main_visible = not self.main_visible
                for actor in self.main_actors:
                    if actor:
                        actor.SetVisibility(1 if self.main_visible else 0)
                if self.render_window:
                    self.render_window.Render()
                print(f"Main geometry: {'visible' if self.main_visible else 'hidden'}")

        def _key_release_callback(obj, event):
            key = self.interactor.GetKeySym()
            if key in self.keys_pressed:
                self.keys_pressed.remove(key)
            if not self.keys_pressed:
                self.last_update_time = None

        def _timer_callback(obj, event):
            if not self.keys_pressed or self.last_update_time is None:
                return

            import time
            current_time = time.time()
            dt = current_time - self.last_update_time
            self.last_update_time = current_time

            # Calculate movement based on keys pressed
            movement = 0.0
            if 'Up' in self.keys_pressed or 'Right' in self.keys_pressed:
                movement += self.movement_speed * dt
            if 'Down' in self.keys_pressed or 'Left' in self.keys_pressed:
                movement -= self.movement_speed * dt

            if movement != 0.0:
                new_position = self.plane_position + movement

                # Clamp to design bounds
                new_position = max(self.min_coord, min(new_position, self.max_coord))

                if abs(new_position - self.plane_position) > 1e-6:
                    self.plane_position = new_position
                    self._update_cutting_plane()
                    print(f"Plane X position: {self.plane_position:.3f} μm")

        # Add observers
        self.interactor.AddObserver('KeyPressEvent', _key_press_callback)
        self.interactor.AddObserver('KeyReleaseEvent', _key_release_callback)

        # Add timer for continuous movement (60 FPS)
        timer_id = self.interactor.CreateRepeatingTimer(16)  # ~16ms = 60 FPS
        self.interactor.AddObserver('TimerEvent', _timer_callback)

    def run(self, start_angle: float = 0.0, screenshot: Optional[Path] = None):
        """Run the interactive visualization."""
        import vtk

        # Create renderer and window
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(1.0, 1.0, 1.0)

        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        self.render_window.SetSize(1280, 960)
        self.render_window.SetWindowName("CAP3D Cross-Section Viewer (←→: Move plane, M: Toggle main geometry)")
        self.render_window.SetMultiSamples(0)

        # Create interactor
        self.interactor = vtk.vtkRenderWindowInteractor()
        self.interactor.SetRenderWindow(self.render_window)
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)

        # Create geometry
        self._create_main_geometry()
        self._create_cutting_plane()

        # Add actors to renderer
        for actor in self.main_actors:
            self.renderer.AddActor(actor)

        if self.plane_actor:
            self.renderer.AddActor(self.plane_actor)
        if hasattr(self, 'plane_edge_actor') and self.plane_edge_actor:
            self.renderer.AddActor(self.plane_edge_actor)

        # Initialize intersection actors list
        self.intersection_actors = []

        # Setup keyboard callbacks
        self._setup_keyboard_callbacks()

        # Setup camera
        if self.design_bounds:
            x_min, y_min, z_min, x_max, y_max, z_max = self.design_bounds
            center_x = (x_min + x_max) / 2
            center_y = (y_min + y_max) / 2
            center_z = (z_min + z_max) / 2

            # Position camera for good view
            camera = self.renderer.GetActiveCamera()
            if camera:
                camera.SetPosition(center_x, center_y, center_z + max(y_max - y_min, x_max - x_min) * 2)
                camera.SetFocalPoint(center_x, center_y, center_z)
                camera.SetViewUp(0, 1, 0)

        self.renderer.ResetCamera()
        apply_start_angle(self.renderer, start_angle)

        # Initial plane update
        self._update_cutting_plane()

        # Print initial state
        print(f"CAP3D Cross-Section Viewer")
        print(f"Loaded: {self.cap3d_file}")
        print(f"Blocks: {len(self.blocks)}")
        print(f"Design bounds: {self.design_bounds}")
        print(f"Initial plane X position: {self.plane_position:.3f} μm")
        print(f"Movement speed: {self.movement_speed} μm/s")
        print(f"Controls: ←→ Arrow keys to move plane (continuous), M to toggle main geometry")

        # Start rendering
        self.render_window.Render()
        capture_initial_screenshot(self.render_window, screenshot)
        self.interactor.Initialize()
        self.interactor.Start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Interactive CAP3D cross-section viewer')
    parser.add_argument('cap3d_file', help='Path to CAP3D file')
    parser.add_argument('--step-size', type=float, default=0.2,
                       help='Step size for plane movement in microns (default: 0.2)')
    parser.add_argument('--plane-opacity', type=float, default=0.8,
                       help='Opacity of cutting plane (0.0-1.0, default: 0.8)')
    parser.add_argument('--start-angle', type=float, default=0.0,
                       help='Rotate initial camera azimuth by this many degrees')
    parser.add_argument('--screenshot', type=Path,
                       help='Optional PNG path to save the initial view')
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    if not Path(args.cap3d_file).exists():
        print(f"ERROR: CAP3D file not found: {args.cap3d_file}")
        sys.exit(1)

    try:
        viewer = CrossSectionViewer(
            args.cap3d_file,
            step_size=args.step_size,
            plane_opacity=args.plane_opacity
        )
        viewer.run(start_angle=args.start_angle, screenshot=args.screenshot)
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main(parse_args())

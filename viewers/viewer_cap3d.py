#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Tuple, List

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

def _add_cap3d_viz_to_path() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    cap3d_viz_root = os.path.abspath(os.path.join(here, '..', 'CAP3D-Viz'))
    if os.path.isdir(os.path.join(cap3d_viz_root, 'cap3d_viz')):
        if cap3d_viz_root not in sys.path:
            sys.path.insert(0, cap3d_viz_root)


_add_cap3d_viz_to_path()


def _block_to_bounds(block) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    bx, by, bz = float(block.base[0]), float(block.base[1]), float(block.base[2])
    dx = float(block.v1[0])
    dy = float(block.v2[1])
    dz = float(block.hvec[2])
    x1, y1, z1 = bx, by, bz
    x2, y2, z2 = bx + dx, by + dy, bz + dz
    return (min(x1, x2), min(y1, y2), min(z1, z2)), (max(x1, x2), max(y1, y2), max(z1, z2))


def _has_conductors_at_z(z_level: float, blocks: list, tolerance: float = 1e-6, proximity_threshold: float = 0.2) -> bool:
    """Check if any conductor blocks exist near the given Z level.

    Less aggressive filtering: shows layer lines if conductors exist within a reasonable
    proximity threshold, not just at the exact Z level. This accounts for the fact that
    plate_medium z_top levels represent dielectric boundaries that should be visible
    if there are conductors in the adjacent layers.

    Args:
        z_level: Target Z coordinate to check
        blocks: List of conductor blocks
        tolerance: Tolerance for exact Z-level matching
        proximity_threshold: Maximum distance to consider conductors as "near" the Z level

    Returns:
        True if conductors exist near this Z level, False otherwise
    """
    for blk in blocks:
        if getattr(blk, 'type', 'conductor') == 'medium':
            continue
        try:
            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(blk)
            # Check if the Z level intersects with this block's Z range
            if (z1 - tolerance) <= z_level <= (z2 + tolerance):
                return True
            # Check if conductors are within proximity threshold of this Z level
            if abs(z1 - z_level) <= proximity_threshold or abs(z2 - z_level) <= proximity_threshold:
                return True
            # Check if this Z level falls within the expanded range of the conductor
            if (z1 - proximity_threshold) <= z_level <= (z2 + proximity_threshold):
                return True
        except Exception:
            continue
    return False


def _get_uppermost_conductor_z(blocks: list) -> float:
    """Find the highest Z coordinate among all conductor blocks.

    Args:
        blocks: List of conductor blocks

    Returns:
        Highest Z coordinate, or 0.0 if no conductor blocks found
    """
    max_z = 0.0
    if not isinstance(blocks, (list, tuple)):
        return 0.0
    for blk in blocks:
        if getattr(blk, 'type', 'conductor') == 'medium':
            continue
        try:
            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(blk)
            if z2 > max_z:
                max_z = z2
        except Exception:
            continue
    return max_z


PALETTE_10: Tuple[Tuple[int,int,int], ...] = (
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

def _color_for_block(blk) -> Tuple[int, int, int]:
    """Choose a color from a fixed 10-color palette based on CAP3D layer ID.

    - Uses explicit integer `layer` attribute from CAP3D data
    - Errors out if no valid layer ID found
    """
    # Get layer ID from CAP3D block
    layer_id = getattr(blk, 'layer', None)
    if layer_id is None:
        raise ValueError(f"Block {blk} has no layer attribute")

    if isinstance(layer_id, int):
        return PALETTE_10[layer_id % len(PALETTE_10)]
    elif isinstance(layer_id, str) and layer_id.isdigit():
        idx = int(layer_id) % len(PALETTE_10)
        return PALETTE_10[idx]
    else:
        raise ValueError(f"Block {blk} has invalid layer attribute: {layer_id} (type: {type(layer_id)})")

def _group_key_for_layer(blk) -> str:
    """Group by metal layer if available; otherwise by Z height bucket.

    - Use integer `layer` attribute when present (preferred).
    - Fallback: bucket by rounded top Z (base.z + hvec.z) to capture height slabs.
    """
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
        


def _build_highlight_conductor_actor(conductor_blocks: list, use_instanced: bool = True) -> Optional['vtk.vtkActor']:
    """Build a highlighted actor for an entire conductor group.

    Args:
        conductor_blocks: List of blocks belonging to the same conductor
        use_instanced: Whether to use instanced rendering for highlights

    Returns:
        VTK actor for the highlighted conductor, or None if no blocks
    """
    import vtk

    if not conductor_blocks:
        return None

    def _append_box(points: 'vtk.vtkPoints', polys: 'vtk.vtkCellArray',
                    x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> None:
        i0 = points.InsertNextPoint(x1, y1, z1)
        i1 = points.InsertNextPoint(x2, y1, z1)
        i2 = points.InsertNextPoint(x2, y2, z1)
        i3 = points.InsertNextPoint(x1, y2, z1)
        i4 = points.InsertNextPoint(x1, y1, z2)
        i5 = points.InsertNextPoint(x2, y1, z2)
        i6 = points.InsertNextPoint(x2, y2, z2)
        i7 = points.InsertNextPoint(x1, y2, z2)
        tri_faces = [
            (i0, i1, i2), (i0, i2, i3),
            (i4, i6, i5), (i4, i7, i6),
            (i0, i5, i1), (i0, i4, i5),
            (i3, i2, i6), (i3, i6, i7),
            (i0, i3, i7), (i0, i7, i4),
            (i1, i5, i6), (i1, i6, i2),
        ]
        for a, b, c in tri_faces:
            polys.InsertNextCell(3)
            polys.InsertCellPoint(a)
            polys.InsertCellPoint(b)
            polys.InsertCellPoint(c)

    if use_instanced:
        # Instanced rendering for highlights
        try:
            centers = vtk.vtkPoints()
            if hasattr(centers, 'SetDataTypeToFloat'):
                centers.SetDataTypeToFloat()
            scale_arr = vtk.vtkFloatArray()
            scale_arr.SetName("scale")
            scale_arr.SetNumberOfComponents(3)

            for blk in conductor_blocks:
                (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(blk)
                cx = 0.5 * (x1 + x2)
                cy = 0.5 * (y1 + y2)
                cz = 0.5 * (z1 + z2)
                sx = abs(x2 - x1)
                sy = abs(y2 - y1)
                sz = abs(z2 - z1)

                centers.InsertNextPoint(cx, cy, cz)
                scale_arr.InsertNextTuple3(sx, sy, sz)

            inst_pd = vtk.vtkPolyData()
            inst_pd.SetPoints(centers)
            inst_pd.GetPointData().SetVectors(scale_arr)

            cube = vtk.vtkCubeSource()
            cube.SetXLength(1.0)
            cube.SetYLength(1.0)
            cube.SetZLength(1.0)
            cube.SetCenter(0.0, 0.0, 0.0)
            cube.Update()

            # Add normals for proper lighting
            c_norm = vtk.vtkPolyDataNormals()
            c_norm.SetInputConnection(cube.GetOutputPort())
            c_norm.ComputeCellNormalsOn()
            c_norm.ComputePointNormalsOff()
            c_norm.SplittingOff()
            c_norm.ConsistencyOn()
            c_norm.AutoOrientNormalsOn()

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
                if hasattr(gmapper, 'SetScaleModeToScaleByComponents'):
                    gmapper.SetScaleModeToScaleByComponents()
                else:
                    raise RuntimeError('Glyph3DMapper lacks ScaleByComponents')

                actor = vtk.vtkActor()
                actor.SetMapper(gmapper)
            except Exception:
                # Fallback to vtkGlyph3D
                glyph = vtk.vtkGlyph3D()
                glyph.SetInputData(inst_pd)
                glyph.SetSourceConnection(c_norm.GetOutputPort())
                if hasattr(glyph, 'OrientOff'):
                    glyph.OrientOff()
                if hasattr(glyph, 'SetVectorModeToUseVector'):
                    glyph.SetVectorModeToUseVector()
                if hasattr(glyph, 'SetScaleModeToScaleByVectorComponents'):
                    glyph.SetScaleModeToScaleByVectorComponents()
                if hasattr(glyph, 'SetScaleFactor'):
                    glyph.SetScaleFactor(1.0)
                if hasattr(glyph, 'ClampingOff'):
                    glyph.ClampingOff()
                if hasattr(glyph, 'SetInputArrayToProcess'):
                    glyph.SetInputArrayToProcess(1, 0, 0, 0, "scale")
                glyph.Update()

                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputConnection(glyph.GetOutputPort())
                actor = vtk.vtkActor()
                actor.SetMapper(mapper)

        except Exception:
            # Fallback to classic rendering
            use_instanced = False

    if not use_instanced:
        # Classic triangle-based rendering for highlights
        points = vtk.vtkPoints()
        if hasattr(points, 'SetDataTypeToFloat'):
            points.SetDataTypeToFloat()
        polys = vtk.vtkCellArray()

        for blk in conductor_blocks:
            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(blk)
            _append_box(points, polys, x1, y1, z1, x2, y2, z2)

        poly_data = vtk.vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.SetPolys(polys)

        # Add normals for proper lighting
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(poly_data)
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

    # Set highlight appearance - bright orange/yellow with emission
    actor.GetProperty().SetColor(1.0, 0.8, 0.0)  # Bright yellow-orange
    actor.GetProperty().SetEmission(0.3)  # Make it glow
    actor.GetProperty().SetSpecular(0.8)
    actor.GetProperty().SetSpecularPower(20.0)
    actor.GetProperty().SetDiffuse(0.9)
    actor.GetProperty().SetOpacity(0.9)
    actor.GetProperty().LightingOn()
    actor.GetProperty().SetInterpolationToPhong()
    actor.GetProperty().BackfaceCullingOn()

    # Add edge highlighting for better visibility
    actor.GetProperty().SetEdgeVisibility(1)
    actor.GetProperty().SetEdgeColor(1.0, 1.0, 0.0)  # Bright yellow edges
    actor.GetProperty().SetLineWidth(2.0)

    return actor


def _build_net_glow_actors(
    conductor_blocks: list,
    scale_factor: float = 1.15,
    glow_color: Tuple[float, float, float] = (1.0, 0.78, 0.45),
) -> List['vtk.vtkActor']:
    """Create translucent glow shells similar to graph viewer highlights."""
    import vtk

    if not conductor_blocks:
        return []

    append = vtk.vtkAppendPolyData()
    min_extent = 0.02  # Avoid zero-thickness halos

    for blk in conductor_blocks:
        (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(blk)
        cx = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)
        cz = 0.5 * (z1 + z2)
        sx = max(abs(x2 - x1) * scale_factor, min_extent)
        sy = max(abs(y2 - y1) * scale_factor, min_extent)
        sz = max(abs(z2 - z1) * scale_factor, min_extent)

        cube = vtk.vtkCubeSource()
        cube.SetCenter(cx, cy, cz)
        cube.SetXLength(sx)
        cube.SetYLength(sy)
        cube.SetZLength(sz)
        cube.Update()
        append.AddInputData(cube.GetOutput())

    append.Update()

    cleaner = vtk.vtkCleanPolyData()
    cleaner.SetInputConnection(append.GetOutputPort())
    cleaner.PointMergingOn()
    cleaner.Update()

    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(cleaner.GetOutputPort())
    normals.ComputeCellNormalsOn()
    normals.ComputePointNormalsOff()
    normals.SplittingOff()
    normals.ConsistencyOn()
    normals.AutoOrientNormalsOn()
    normals.Update()

    # Primary translucent halo
    halo_mapper = vtk.vtkPolyDataMapper()
    halo_mapper.SetInputConnection(normals.GetOutputPort())
    halo_actor = vtk.vtkActor()
    halo_actor.SetMapper(halo_mapper)
    halo_actor.SetPickable(0)
    halo_prop = halo_actor.GetProperty()
    halo_prop.SetColor(glow_color)
    halo_prop.SetOpacity(0.42)
    halo_prop.SetDiffuse(0.95)
    halo_prop.SetAmbient(0.2)
    halo_prop.SetSpecular(0.55)
    halo_prop.SetSpecularPower(70.0)
    halo_prop.SetInterpolationToPhong()
    halo_prop.LightingOn()

    # Thin outline for crisp edges
    outline_mapper = vtk.vtkPolyDataMapper()
    outline_mapper.SetInputConnection(normals.GetOutputPort())
    outline_actor = vtk.vtkActor()
    outline_actor.SetMapper(outline_mapper)
    outline_prop = outline_actor.GetProperty()
    outline_prop.SetRepresentationToWireframe()
    outline_prop.SetColor(1.0, 1.0, 1.0)
    outline_prop.SetLineWidth(1.8)
    outline_prop.SetOpacity(0.85)
    outline_prop.LightingOff()
    outline_actor.SetPickable(0)

    return [halo_actor, outline_actor]


def _build_dielectric_blocks(parsed_data, conductor_blocks: list, window_bounds: tuple) -> Optional['vtk.vtkActor']:
    """Build 3D dielectric blocks from plate_medium data with intersection highlighting.

    Args:
        parsed_data: Parsed CAP3D data containing plate_mediums
        conductor_blocks: List of conductor blocks for filtering
        window_bounds: (x1, y1, z1, x2, y2, z2) window boundaries

    Returns:
        VTK actor with dielectric blocks, or None if no dielectric data found
    """
    import vtk

    plate_mediums = getattr(parsed_data, 'plate_mediums', None)
    if not plate_mediums:
        return None

    # Sort dielectric boundaries by z-coordinate
    dielectric_levels = sorted([(float(pm.z_top), pm.diel) for pm in plate_mediums if pm.z_top is not None])
    if len(dielectric_levels) < 2:
        return None  # Need at least 2 levels to form volume

    # Get window boundaries
    x1, y1, z1, x2, y2, z2 = window_bounds
    wx1, wy1, wx2, wy2 = min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

    # Create a composite actor containing both dielectric blocks and intersection lines
    composite_actor = vtk.vtkAssembly()

    # Build dielectric blocks between consecutive z-levels
    points = vtk.vtkPoints()
    polys = vtk.vtkCellArray()
    colors = vtk.vtkFloatArray()
    colors.SetNumberOfComponents(3)
    colors.SetName("DielectricColors")

    # Create a color palette for dielectrics based on dielectric constant
    dielectric_colors = []
    for i in range(len(dielectric_levels) - 1):
        # Map dielectric constant to color (lower = more transparent blue, higher = more opaque orange)
        er = dielectric_levels[i][1]
        if er <= 2.0:
            # Low-k dielectrics - blue tones, more transparent
            r, g, b = 0.2, 0.4, 0.8
            opacity = 0.15
        elif er <= 4.0:
            # Medium-k dielectrics - green tones, medium transparency
            r, g, b = 0.2, 0.7, 0.3
            opacity = 0.25
        else:
            # High-k dielectrics - orange/red tones, less transparent
            r, g, b = 0.9, 0.4, 0.2
            opacity = 0.35
        dielectric_colors.append((r, g, b, opacity))

    # Build dielectric blocks
    block_count = 0
    for i in range(len(dielectric_levels) - 1):
        z_bottom = dielectric_levels[i][0]
        z_top = dielectric_levels[i + 1][0]

        # Skip if completely outside window Z range
        if z_top <= z1 or z_bottom >= z2:
            continue

        # Clip to window Z range
        z_bottom = max(z_bottom, z1)
        z_top = min(z_top, z2)

        # Skip very thin layers
        if z_top - z_bottom < 1e-6:
            continue

        # Get color for this dielectric layer
        r, g, b, opacity = dielectric_colors[min(i, len(dielectric_colors) - 1)]

        # Add box corners (similar to _append_box pattern)
        p0 = points.InsertNextPoint(wx1, wy1, z_bottom)
        p1 = points.InsertNextPoint(wx2, wy1, z_bottom)
        p2 = points.InsertNextPoint(wx2, wy2, z_bottom)
        p3 = points.InsertNextPoint(wx1, wy2, z_bottom)
        p4 = points.InsertNextPoint(wx1, wy1, z_top)
        p5 = points.InsertNextPoint(wx2, wy1, z_top)
        p6 = points.InsertNextPoint(wx2, wy2, z_top)
        p7 = points.InsertNextPoint(wx1, wy2, z_top)

        # Add 12 triangles (6 faces * 2 triangles each)
        faces = [
            [p0, p1, p2], [p0, p2, p3],  # bottom
            [p4, p6, p5], [p4, p7, p6],  # top
            [p0, p4, p5], [p0, p5, p1],  # front
            [p2, p6, p7], [p2, p7, p3],  # back
            [p0, p3, p7], [p0, p7, p4],  # left
            [p1, p5, p6], [p1, p6, p2],  # right
        ]

        for face in faces:
            triangle = vtk.vtkTriangle()
            for j, vertex_idx in enumerate(face):
                triangle.GetPointIds().SetId(j, vertex_idx)
            polys.InsertNextCell(triangle)

        # Add color for each vertex of this block (8 vertices)
        for _ in range(8):
            colors.InsertNextTuple3(r, g, b)

        block_count += 1

    if block_count > 0:
        # Create polydata and actor for dielectric blocks
        poly_data = vtk.vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.SetPolys(polys)
        poly_data.GetPointData().SetScalars(colors)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly_data)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        # Set appearance
        actor.GetProperty().SetOpacity(0.3)  # Overall transparency
        actor.GetProperty().SetColor(0.7, 0.7, 0.7)  # Base color (will be overridden by vertex colors)
        actor.GetProperty().SetEdgeVisibility(1)
        actor.GetProperty().SetEdgeColor(0.3, 0.3, 0.3)
        actor.GetProperty().SetLineWidth(0.5)

        composite_actor.AddPart(actor)

    # Add intersection highlighting lines at dielectric boundaries within window
    line_points = vtk.vtkPoints()
    line_polys = vtk.vtkCellArray()

    # Create prominent square lines at each dielectric level that intersects with the window
    for i, (z_level, _) in enumerate(dielectric_levels):
        if z_level <= z1 or z_level >= z2:
            continue  # Skip levels outside window Z range

        # Add square outline at this Z level
        idx0 = line_points.InsertNextPoint(wx1, wy1, z_level)
        idx1 = line_points.InsertNextPoint(wx2, wy1, z_level)
        idx2 = line_points.InsertNextPoint(wx2, wy2, z_level)
        idx3 = line_points.InsertNextPoint(wx1, wy2, z_level)
        idx4 = line_points.InsertNextPoint(wx1, wy1, z_level)  # Close the square

        # Create polyline for square outline
        polyline = vtk.vtkPolyLine()
        polyline.GetPointIds().SetNumberOfIds(5)
        polyline.GetPointIds().SetId(0, idx0)
        polyline.GetPointIds().SetId(1, idx1)
        polyline.GetPointIds().SetId(2, idx2)
        polyline.GetPointIds().SetId(3, idx3)
        polyline.GetPointIds().SetId(4, idx4)
        line_polys.InsertNextCell(polyline)

    if line_polys.GetNumberOfCells() > 0:
        # Create line polydata and actor
        line_poly = vtk.vtkPolyData()
        line_poly.SetPoints(line_points)
        line_poly.SetLines(line_polys)

        line_mapper = vtk.vtkPolyDataMapper()
        line_mapper.SetInputData(line_poly)

        line_actor = vtk.vtkActor()
        line_actor.SetMapper(line_mapper)

        # Make lines prominent and distinct
        line_actor.GetProperty().SetColor(0.0, 0.8, 1.0)  # Bright cyan color
        line_actor.GetProperty().SetLineWidth(2.5)  # Thicker lines for visibility
        line_actor.GetProperty().SetOpacity(0.9)  # High opacity
        line_actor.GetProperty().LightingOff()  # No lighting for consistent color

        composite_actor.AddPart(line_actor)

    if block_count > 0:
        print(f"Created {block_count} 3D dielectric blocks with intersection highlighting")
    return composite_actor


def visualize_cap3d_vtk(
    file_path: str,
    max_blocks: int = 100000,
    use_instanced: bool = True,
    start_angle: float = 0.0,
    screenshot_path: Optional[Path] = None,
    white_background: bool = False,
) -> None:
    import vtk
    import time

    # Pure-Python parser (no Cython)
    parser = StreamingCap3DParser(file_path, use_fast=False)
    parsed = parser.parse_complete()
    blocks = parsed.blocks

    # Group blocks by conductor for hover highlighting
    conductor_groups = {}
    block_to_conductor = {}
    block_index_map = {}  # Maps block global index to block object

    # Process blocks and build conductor groupings
    conductor_block_count = 0
    for blk in blocks:
        if getattr(blk, 'type', 'conductor') == 'conductor':
            conductor_name = getattr(blk, 'parent_name', f'Conductor_{conductor_block_count}')
            if conductor_name not in conductor_groups:
                conductor_groups[conductor_name] = []
            conductor_groups[conductor_name].append(blk)
            block_to_conductor[id(blk)] = conductor_name
            # We'll map blocks during rendering when we know their actual positions
            conductor_block_count += 1

    print(f"Grouped {conductor_block_count} conductor blocks into {len(conductor_groups)} conductors")
    
    # Get window bounds for span detection
    window_bounds = None
    if getattr(parsed, 'window', None) is not None:
        w = parsed.window
        wx1 = float(min(w.v1[0], w.v2[0])); wy1 = float(min(w.v1[1], w.v2[1]))
        wx2 = float(max(w.v1[0], w.v2[0])); wy2 = float(max(w.v1[1], w.v2[1]))
        window_bounds = (wx1, wy1, wx2, wy2)

    # Identify substrate conductor as the conductor with the lowest Z coordinate
    substrate_conductor_name = None
    if not isinstance(blocks, (list, tuple)):
        conductor_blocks = []
    else:
        conductor_blocks = [blk for blk in blocks if getattr(blk, 'type', 'conductor') == 'conductor']
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
  
    # Renderer and window (GPU-backed if available)
    renderer = vtk.vtkRenderer()
    # Set background based on mode
    if white_background:
        renderer.SetBackground(1.0, 1.0, 1.0)  # White for screenshots
    else:
        renderer.SetBackground(0.08, 0.09, 0.11)  # Dark for interactive use
    renWin = vtk.vtkRenderWindow()
    # Higher resolution for better screenshot quality
    if screenshot_path is not None:
        renWin.SetSize(1920, 1080)
    else:
        renWin.SetSize(1280, 960)
    # Enable MSAA for better quality when taking screenshots
    if screenshot_path is not None:
        renWin.SetMultiSamples(4)  # Enable anti-aliasing for screenshots
    else:
        renWin.SetMultiSamples(0)  # Lower MSAA for performance during interaction
    renWin.AddRenderer(renderer)

    # Interactor
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renWin)
    # Use trackball camera for intuitive rotation and wheel zoom
    style = vtk.vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    # Shared helper to append a box (used by classic path and window box)
    def _append_box(points: 'vtk.vtkPoints', polys: 'vtk.vtkCellArray',
                    x1: float, y1: float, z1: float, x2: float, y2: float, z2: float,
                    color_array: 'vtk.vtkUnsignedCharArray' = None,
                    rgb: Tuple[int, int, int] = None) -> None:
        i0 = points.InsertNextPoint(x1, y1, z1)
        i1 = points.InsertNextPoint(x2, y1, z1)
        i2 = points.InsertNextPoint(x2, y2, z1)
        i3 = points.InsertNextPoint(x1, y2, z1)
        i4 = points.InsertNextPoint(x1, y1, z2)
        i5 = points.InsertNextPoint(x2, y1, z2)
        i6 = points.InsertNextPoint(x2, y2, z2)
        i7 = points.InsertNextPoint(x1, y2, z2)
        tri_faces = [
            (i0, i1, i2), (i0, i2, i3),
            (i4, i6, i5), (i4, i7, i6),
            (i0, i5, i1), (i0, i4, i5),
            (i3, i2, i6), (i3, i6, i7),
            (i0, i3, i7), (i0, i7, i4),
            (i1, i5, i6), (i1, i6, i2),
        ]
        for a, b, c in tri_faces:
            polys.InsertNextCell(3)
            polys.InsertCellPoint(a)
            polys.InsertCellPoint(b)
            polys.InsertCellPoint(c)
            if color_array is not None and rgb is not None:
                color_array.InsertNextTuple3(rgb[0], rgb[1], rgb[2])

    # Helper to build classic merged mesh (triangles)
    def _get_mem_mb() -> float:
        try:
            import resource as _res
            kb = float(_res.getrusage(_res.RUSAGE_SELF).ru_maxrss)
            # On Linux ru_maxrss is KB; convert to MB
            return kb / 1024.0
        except Exception:
            return 0.0

    def _build_classic_conductors():
        import time as _t
        t0 = _t.perf_counter()
        m0 = _get_mem_mb()
        # Regular conductors (excluding substrate)
        c_points = vtk.vtkPoints(); c_polys = vtk.vtkCellArray()
        if hasattr(c_points, 'SetDataTypeToFloat'):
            c_points.SetDataTypeToFloat()
        c_colors = vtk.vtkUnsignedCharArray(); c_colors.SetName("colors"); c_colors.SetNumberOfComponents(3)
        # Substrate conductor blocks (separate for toggling)
        s_points = vtk.vtkPoints(); s_polys = vtk.vtkCellArray()
        if hasattr(s_points, 'SetDataTypeToFloat'):
            s_points.SetDataTypeToFloat()
        s_colors = vtk.vtkUnsignedCharArray(); s_colors.SetName("colors"); s_colors.SetNumberOfComponents(3)
        # Spanning elements (large elements that span most of the window)
        g_points = vtk.vtkPoints(); g_polys = vtk.vtkCellArray()
        if hasattr(g_points, 'SetDataTypeToFloat'):
            g_points.SetDataTypeToFloat()
        g_colors = vtk.vtkUnsignedCharArray(); g_colors.SetName("colors"); g_colors.SetNumberOfComponents(3)
        count = 0
        scount = 0
        gcount = 0
        # Clear block index mapping and rebuild it
        block_index_map.clear()
        for blk in blocks:
            if count >= max_blocks:
                break
            (x1, y1, z1), (x2, y2, z2) = _block_to_bounds(blk)
            if getattr(blk, 'type', 'conductor') == 'medium':
                continue
            # Check if this block belongs to the substrate conductor
            is_substrate = substrate_conductor_name and blk.parent_name == substrate_conductor_name
            # Check if this element spans most of the window (instead of name-based ground detection)
            is_spanning = _is_spanning_element(blk)
            rgb = _color_for_block(blk)
            if is_substrate:
                _append_box(s_points, s_polys, x1, y1, z1, x2, y2, z2, s_colors, rgb)
                # Store block index mapping for substrate blocks
                for _ in range(12):  # 12 triangles per block
                    block_index_map[len(block_index_map)] = blk
                scount += 1
            elif is_spanning:
                _append_box(g_points, g_polys, x1, y1, z1, x2, y2, z2, g_colors, rgb)
                # Store block index mapping for spanning blocks
                for _ in range(12):  # 12 triangles per block
                    block_index_map[len(block_index_map)] = blk
                gcount += 1
            else:
                _append_box(c_points, c_polys, x1, y1, z1, x2, y2, z2, c_colors, rgb)
                # Store block index mapping for regular blocks
                for _ in range(12):  # 12 triangles per block
                    block_index_map[len(block_index_map)] = blk
                count += 1

        if c_points.GetNumberOfPoints() == 0 and g_points.GetNumberOfPoints() == 0 and s_points.GetNumberOfPoints() == 0:
            return None, None, None, None
        c_poly = vtk.vtkPolyData()
        c_poly.SetPoints(c_points)
        c_poly.SetPolys(c_polys)
        # Keep lighting simple but on; normals once for crisp edges
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(c_poly)
        normals.ComputeCellNormalsOn()
        normals.ComputePointNormalsOff()
        normals.SplittingOff()
        normals.ConsistencyOn()
        normals.AutoOrientNormalsOn()
        normals.Update()
        out_poly = normals.GetOutput()
        out_poly.GetCellData().SetScalars(c_colors)
        try:
            c_mapper = vtk.vtkStaticPolyDataMapper()
        except Exception:
            c_mapper = vtk.vtkPolyDataMapper()
        c_mapper.SetInputData(out_poly)
        if hasattr(c_mapper, 'SetInterpolateScalarsBeforeMapping'):
            c_mapper.SetInterpolateScalarsBeforeMapping(0)
        if hasattr(c_mapper, 'SetColorModeToDirectScalars'):
            c_mapper.SetColorModeToDirectScalars()
        if hasattr(c_mapper, 'SetScalarModeToUseCellData'):
            c_mapper.SetScalarModeToUseCellData()
        else:
            c_mapper.SetScalarModeToUseCellFieldData()
            c_mapper.SelectColorArray("colors")
        c_mapper.SetScalarVisibility(1)
        c_actor = vtk.vtkActor(); c_actor.SetMapper(c_mapper)
        c_actor.GetProperty().LightingOn(); c_actor.GetProperty().SetInterpolationToFlat()
        c_actor.GetProperty().SetDiffuse(0.9); c_actor.GetProperty().SetSpecular(0.1)
        c_actor.GetProperty().SetSpecularPower(10.0); c_actor.GetProperty().SetOpacity(1.0)
        c_actor.GetProperty().BackfaceCullingOn()

        g_actor = None
        if g_points.GetNumberOfPoints() > 0:
            g_poly = vtk.vtkPolyData(); g_poly.SetPoints(g_points); g_poly.SetPolys(g_polys)
            g_norm = vtk.vtkPolyDataNormals(); g_norm.SetInputData(g_poly)
            g_norm.ComputeCellNormalsOn(); g_norm.ComputePointNormalsOff(); g_norm.SplittingOff()
            g_norm.ConsistencyOn(); g_norm.AutoOrientNormalsOn(); g_norm.Update()
            gout = g_norm.GetOutput(); gout.GetCellData().SetScalars(g_colors)
            try:
                g_mapper = vtk.vtkStaticPolyDataMapper()
            except Exception:
                g_mapper = vtk.vtkPolyDataMapper()
            g_mapper.SetInputData(gout)
            if hasattr(g_mapper, 'SetInterpolateScalarsBeforeMapping'):
                g_mapper.SetInterpolateScalarsBeforeMapping(0)
            if hasattr(g_mapper, 'SetColorModeToDirectScalars'):
                g_mapper.SetColorModeToDirectScalars()
            if hasattr(g_mapper, 'SetScalarModeToUseCellData'):
                g_mapper.SetScalarModeToUseCellData()
            else:
                g_mapper.SetScalarModeToUseCellFieldData(); g_mapper.SelectColorArray("colors")
            g_mapper.SetScalarVisibility(1)
            g_actor = vtk.vtkActor(); g_actor.SetMapper(g_mapper)
            g_actor.GetProperty().LightingOn(); g_actor.GetProperty().SetInterpolationToFlat()
            g_actor.GetProperty().SetDiffuse(0.9); g_actor.GetProperty().SetSpecular(0.1)
            g_actor.GetProperty().SetSpecularPower(10.0); g_actor.GetProperty().SetOpacity(1.0)
            g_actor.GetProperty().BackfaceCullingOn()

        # Substrate conductor actor (separate for toggling)
        s_actor = None
        if s_points.GetNumberOfPoints() > 0:
            s_poly = vtk.vtkPolyData(); s_poly.SetPoints(s_points); s_poly.SetPolys(s_polys)
            s_norm = vtk.vtkPolyDataNormals(); s_norm.SetInputData(s_poly)
            s_norm.ComputeCellNormalsOn(); s_norm.ComputePointNormalsOff(); s_norm.SplittingOff()
            s_norm.ConsistencyOn(); s_norm.AutoOrientNormalsOn(); s_norm.Update()
            sout = s_norm.GetOutput(); sout.GetCellData().SetScalars(s_colors)
            try:
                s_mapper = vtk.vtkStaticPolyDataMapper()
            except Exception:
                s_mapper = vtk.vtkPolyDataMapper()
            s_mapper.SetInputData(sout)
            if hasattr(s_mapper, 'SetInterpolateScalarsBeforeMapping'):
                s_mapper.SetInterpolateScalarsBeforeMapping(0)
            if hasattr(s_mapper, 'SetColorModeToDirectScalars'):
                s_mapper.SetColorModeToDirectScalars()
            if hasattr(s_mapper, 'SetScalarModeToUseCellData'):
                s_mapper.SetScalarModeToUseCellData()
            else:
                s_mapper.SetScalarModeToUseCellFieldData(); s_mapper.SelectColorArray("colors")
            s_mapper.SetScalarVisibility(1)
            s_actor = vtk.vtkActor(); s_actor.SetMapper(s_mapper)
            s_actor.GetProperty().LightingOn(); s_actor.GetProperty().SetInterpolationToFlat()
            s_actor.GetProperty().SetDiffuse(0.9); s_actor.GetProperty().SetSpecular(0.1)
            s_actor.GetProperty().SetSpecularPower(10.0); s_actor.GetProperty().SetOpacity(1.0)
            s_actor.GetProperty().BackfaceCullingOn()
        dt = _t.perf_counter() - t0
        m1 = _get_mem_mb()
        stats = {
            'mode': 'classic',
            'blocks': count + gcount + scount,
            'build_time_s': dt,
            'mem_delta_mb': max(0.0, m1 - m0),
            'tris': (count + gcount + scount) * 12,
        }
        return c_actor, g_actor, s_actor, stats

    # Helper to build instanced path (glyphs). Falls back to classic on failure.
    def _build_instanced_conductors():
        try:
            import time as _t
            t0 = _t.perf_counter()
            m0 = _get_mem_mb()
            centers = vtk.vtkPoints()
            if hasattr(centers, 'SetDataTypeToFloat'):
                centers.SetDataTypeToFloat()
            scale_arr = vtk.vtkFloatArray()
            scale_arr.SetName("scale")
            scale_arr.SetNumberOfComponents(3)
            colors_arr = vtk.vtkFloatArray()
            colors_arr.SetName("colors")
            colors_arr.SetNumberOfComponents(3)
            # Spanning element arrays
            g_centers = vtk.vtkPoints()
            if hasattr(g_centers, 'SetDataTypeToFloat'):
                g_centers.SetDataTypeToFloat()
            g_scale_arr = vtk.vtkFloatArray(); g_scale_arr.SetName("scale"); g_scale_arr.SetNumberOfComponents(3)
            g_colors_arr = vtk.vtkFloatArray(); g_colors_arr.SetName("colors"); g_colors_arr.SetNumberOfComponents(3)
            # Substrate conductor arrays (separate for toggling)
            s_centers = vtk.vtkPoints()
            if hasattr(s_centers, 'SetDataTypeToFloat'):
                s_centers.SetDataTypeToFloat()
            s_scale_arr = vtk.vtkFloatArray(); s_scale_arr.SetName("scale"); s_scale_arr.SetNumberOfComponents(3)
            s_colors_arr = vtk.vtkFloatArray(); s_colors_arr.SetName("colors"); s_colors_arr.SetNumberOfComponents(3)
            count = 0
            gcount = 0
            scount = 0
            # Clear block index mapping and rebuild it
            block_index_map.clear()
            for blk in blocks:
                if count >= max_blocks:
                    break
                if getattr(blk, 'type', 'conductor') == 'medium':
                    continue
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
                # Check if this element spans most of the window (instead of name-based ground detection)
                is_spanning = _is_spanning_element(blk)
                r, g, b = _color_for_block(blk)
                # Convert to 0-1 range for float arrays
                rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
                if is_substrate:
                    s_centers.InsertNextPoint(cx, cy, cz)
                    s_scale_arr.InsertNextTuple3(sx, sy, sz)
                    s_colors_arr.InsertNextTuple3(rf, gf, bf)
                    # Store block index mapping for substrate blocks (one-to-one in instanced mode)
                    block_index_map[len(block_index_map)] = blk
                    scount += 1
                elif is_spanning:
                    g_centers.InsertNextPoint(cx, cy, cz)
                    g_scale_arr.InsertNextTuple3(sx, sy, sz)
                    g_colors_arr.InsertNextTuple3(rf, gf, bf)
                    # Store block index mapping for spanning blocks (one-to-one in instanced mode)
                    block_index_map[len(block_index_map)] = blk
                    gcount += 1
                else:
                    centers.InsertNextPoint(cx, cy, cz)
                    scale_arr.InsertNextTuple3(sx, sy, sz)
                    colors_arr.InsertNextTuple3(rf, gf, bf)
                    # Store block index mapping for regular blocks (one-to-one in instanced mode)
                    block_index_map[len(block_index_map)] = blk
                    count += 1
            if centers.GetNumberOfPoints() == 0 and g_centers.GetNumberOfPoints() == 0 and s_centers.GetNumberOfPoints() == 0:
                return None, None, None, None
            
            # Mark color array as RGB data
            colors_arr.SetName("RGB")  # VTK recognizes "RGB" as special
            
            inst_pd = vtk.vtkPolyData()
            inst_pd.SetPoints(centers)
            # Attach arrays and mark as active for consumers with legacy APIs
            inst_pd.GetPointData().AddArray(scale_arr)
            inst_pd.GetPointData().AddArray(colors_arr)
            inst_pd.GetPointData().SetScalars(colors_arr)
            if hasattr(inst_pd.GetPointData(), 'SetActiveScalars'):
                inst_pd.GetPointData().SetActiveScalars("RGB")
            if hasattr(inst_pd.GetPointData(), 'SetVectors'):
                inst_pd.GetPointData().SetVectors(scale_arr)

            # Mark ground color array as RGB data
            g_colors_arr.SetName("RGB")  # VTK recognizes "RGB" as special

            g_inst_pd = vtk.vtkPolyData()
            g_inst_pd.SetPoints(g_centers)
            g_inst_pd.GetPointData().AddArray(g_scale_arr)
            g_inst_pd.GetPointData().AddArray(g_colors_arr)
            g_inst_pd.GetPointData().SetScalars(g_colors_arr)
            if hasattr(g_inst_pd.GetPointData(), 'SetActiveScalars'):
                g_inst_pd.GetPointData().SetActiveScalars("RGB")
            if hasattr(g_inst_pd.GetPointData(), 'SetVectors'):
                g_inst_pd.GetPointData().SetVectors(g_scale_arr)

            # Mark substrate color array as RGB data
            s_colors_arr.SetName("RGB")  # VTK recognizes "RGB" as special

            s_inst_pd = vtk.vtkPolyData()
            s_inst_pd.SetPoints(s_centers)
            s_inst_pd.GetPointData().AddArray(s_scale_arr)
            s_inst_pd.GetPointData().AddArray(s_colors_arr)
            s_inst_pd.GetPointData().SetScalars(s_colors_arr)
            if hasattr(s_inst_pd.GetPointData(), 'SetActiveScalars'):
                s_inst_pd.GetPointData().SetActiveScalars("RGB")
            if hasattr(s_inst_pd.GetPointData(), 'SetVectors'):
                s_inst_pd.GetPointData().SetVectors(s_scale_arr)

            cube = vtk.vtkCubeSource()
            cube.SetXLength(1.0)
            cube.SetYLength(1.0)
            cube.SetZLength(1.0)
            cube.SetCenter(0.0, 0.0, 0.0)
            cube.Update()
            
            # Ensure normals exist for lighting
            c_norm = vtk.vtkPolyDataNormals()
            c_norm.SetInputConnection(cube.GetOutputPort())
            c_norm.ComputeCellNormalsOn()
            c_norm.ComputePointNormalsOff()
            c_norm.SplittingOff()
            c_norm.ConsistencyOn()
            c_norm.AutoOrientNormalsOn()

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
                
                c_actor = vtk.vtkActor(); c_actor.SetMapper(gmapper)
                # Ground mapper/actor
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
                g_actor_inst = vtk.vtkActor(); g_actor_inst.SetMapper(g_gmapper)

                # Substrate mapper/actor (instanced version)
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
                s_actor_inst = vtk.vtkActor(); s_actor_inst.SetMapper(s_gmapper)
            except Exception:
                # Fallback to vtkGlyph3D (more broadly supported)
                glyph = vtk.vtkGlyph3D()
                glyph.SetInputData(inst_pd)
                glyph.SetSourceConnection(cube.GetOutputPort())
                # Ensure no orientation; use vector components for scaling
                if hasattr(glyph, 'OrientOff'):
                    glyph.OrientOff()
                if hasattr(glyph, 'SetVectorModeToUseVector'):
                    glyph.SetVectorModeToUseVector()
                if hasattr(glyph, 'SetScaleModeToScaleByVectorComponents'):
                    glyph.SetScaleModeToScaleByVectorComponents()
                if hasattr(glyph, 'SetScaleFactor'):
                    glyph.SetScaleFactor(1.0)
                # Make sure clamping is disabled (no minimum size)
                if hasattr(glyph, 'ClampingOff'):
                    glyph.ClampingOff()
                if hasattr(glyph, 'SetClamping'):
                    try:
                        glyph.SetClamping(False)
                    except Exception:
                        pass
                # Bind per-instance colors (scalars) and scale (vectors)
                try:
                    from vtkmodules.vtkCommonDataModel import vtkDataObject
                    if hasattr(glyph, 'SetInputArrayToProcess'):
                        # idx=0 selects scalars, idx=1 selects vectors
                        glyph.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, "colors")
                        glyph.SetInputArrayToProcess(1, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, "scale")
                except Exception:
                    if hasattr(glyph, 'SetInputArrayToProcess'):
                        glyph.SetInputArrayToProcess(0, 0, 0, 0, "colors")
                        glyph.SetInputArrayToProcess(1, 0, 0, 0, "scale")
                glyph.Update()
                c_mapper = vtk.vtkPolyDataMapper()
                c_mapper.SetInputConnection(glyph.GetOutputPort())
                if hasattr(c_mapper, 'SetColorModeToDirectScalars'):
                    c_mapper.SetColorModeToDirectScalars()
                if hasattr(c_mapper, 'SetInterpolateScalarsBeforeMapping'):
                    c_mapper.SetInterpolateScalarsBeforeMapping(0)
                c_mapper.SetScalarModeToUsePointData()
                c_mapper.SetScalarVisibility(1)
                c_actor = vtk.vtkActor(); c_actor.SetMapper(c_mapper)
                # Ground glyph fallback
                g_glyph = vtk.vtkGlyph3D()
                g_glyph.SetInputData(g_inst_pd)
                g_glyph.SetSourceConnection(cube.GetOutputPort())
                if hasattr(g_glyph, 'OrientOff'):
                    g_glyph.OrientOff()
                if hasattr(g_glyph, 'SetVectorModeToUseVector'):
                    g_glyph.SetVectorModeToUseVector()
                if hasattr(g_glyph, 'SetScaleModeToScaleByVectorComponents'):
                    g_glyph.SetScaleModeToScaleByVectorComponents()
                if hasattr(g_glyph, 'SetScaleFactor'):
                    g_glyph.SetScaleFactor(1.0)
                if hasattr(g_glyph, 'ClampingOff'):
                    g_glyph.ClampingOff()
                if hasattr(g_glyph, 'SetInputArrayToProcess'):
                    try:
                        from vtkmodules.vtkCommonDataModel import vtkDataObject
                        g_glyph.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, "colors")
                        g_glyph.SetInputArrayToProcess(1, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, "scale")
                    except Exception:
                        g_glyph.SetInputArrayToProcess(0, 0, 0, 0, "colors")
                        g_glyph.SetInputArrayToProcess(1, 0, 0, 0, "scale")
                g_glyph.Update()
                g_cmapper = vtk.vtkPolyDataMapper(); g_cmapper.SetInputConnection(g_glyph.GetOutputPort())
                if hasattr(g_cmapper, 'SetColorModeToDirectScalars'):
                    g_cmapper.SetColorModeToDirectScalars()
                if hasattr(g_cmapper, 'SetInterpolateScalarsBeforeMapping'):
                    g_cmapper.SetInterpolateScalarsBeforeMapping(0)
                g_cmapper.SetScalarModeToUsePointData(); g_cmapper.SetScalarVisibility(1)
                g_actor_inst = vtk.vtkActor(); g_actor_inst.SetMapper(g_cmapper)

                # Substrate glyph fallback
                s_glyph = vtk.vtkGlyph3D()
                s_glyph.SetInputData(s_inst_pd)
                s_glyph.SetSourceConnection(cube.GetOutputPort())
                if hasattr(s_glyph, 'OrientOff'):
                    s_glyph.OrientOff()
                if hasattr(s_glyph, 'SetVectorModeToUseVector'):
                    s_glyph.SetVectorModeToUseVector()
                if hasattr(s_glyph, 'SetScaleModeToScaleByVectorComponents'):
                    s_glyph.SetScaleModeToScaleByVectorComponents()
                if hasattr(s_glyph, 'SetScaleFactor'):
                    s_glyph.SetScaleFactor(1.0)
                if hasattr(s_glyph, 'ClampingOff'):
                    s_glyph.ClampingOff()
                if hasattr(s_glyph, 'SetInputArrayToProcess'):
                    try:
                        from vtkmodules.vtkCommonDataModel import vtkDataObject
                        s_glyph.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, "colors")
                        s_glyph.SetInputArrayToProcess(1, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, "scale")
                    except Exception:
                        s_glyph.SetInputArrayToProcess(0, 0, 0, 0, "colors")
                        s_glyph.SetInputArrayToProcess(1, 0, 0, 0, "scale")
                s_glyph.Update()
                s_cmapper = vtk.vtkPolyDataMapper(); s_cmapper.SetInputConnection(s_glyph.GetOutputPort())
                if hasattr(s_cmapper, 'SetColorModeToDirectScalars'):
                    s_cmapper.SetColorModeToDirectScalars()
                if hasattr(s_cmapper, 'SetInterpolateScalarsBeforeMapping'):
                    s_cmapper.SetInterpolateScalarsBeforeMapping(0)
                s_cmapper.SetScalarModeToUsePointData(); s_cmapper.SetScalarVisibility(1)
                s_actor_inst = vtk.vtkActor(); s_actor_inst.SetMapper(s_cmapper)

            # Enable lighting so instances respond to illumination
            c_actor.GetProperty().LightingOn()
            c_actor.GetProperty().SetInterpolationToFlat()
            c_actor.GetProperty().SetDiffuse(0.9)
            c_actor.GetProperty().SetSpecular(0.1)
            c_actor.GetProperty().SetSpecularPower(10.0)
            c_actor.GetProperty().SetOpacity(1.0)
            c_actor.GetProperty().BackfaceCullingOn()
            # Ground actor props
            g_actor_inst.GetProperty().LightingOn()
            g_actor_inst.GetProperty().SetInterpolationToFlat()
            g_actor_inst.GetProperty().SetDiffuse(0.9)
            g_actor_inst.GetProperty().SetSpecular(0.1)
            g_actor_inst.GetProperty().SetSpecularPower(10.0)
            g_actor_inst.GetProperty().SetOpacity(1.0)
            g_actor_inst.GetProperty().BackfaceCullingOn()
            # Substrate actor props
            s_actor_inst.GetProperty().LightingOn()
            s_actor_inst.GetProperty().SetInterpolationToFlat()
            s_actor_inst.GetProperty().SetDiffuse(0.9)
            s_actor_inst.GetProperty().SetSpecular(0.1)
            s_actor_inst.GetProperty().SetSpecularPower(10.0)
            s_actor_inst.GetProperty().SetOpacity(1.0)
            s_actor_inst.GetProperty().BackfaceCullingOn()

            dt = _t.perf_counter() - t0
            m1 = _get_mem_mb()
            stats = {
                'mode': 'instanced',
                'blocks': count + gcount + scount,
                'build_time_s': dt,
                'mem_delta_mb': max(0.0, m1 - m0),
                'instances': count + gcount + scount,
            }
            return c_actor, g_actor_inst, s_actor_inst, stats
        except Exception:
            return None, None, None, None

    # Build conductors (classic by default, instanced if requested and supported)
    result = _build_instanced_conductors() if use_instanced else _build_classic_conductors()
    # Unpack main, spanning, and substrate conductor actors and stats
    if isinstance(result, tuple) and len(result) == 4:
        c_actor, spanning_cond_actor, substrate_actor, c_stats = result
    else:
        c_actor, spanning_cond_actor, substrate_actor, c_stats = result, None, None, None
    if c_actor is None and use_instanced:
        # Fallback to classic if instancing path failed
        c_actor, spanning_cond_actor, substrate_actor, c_stats = _build_classic_conductors()
    if c_actor is not None:
        renderer.AddActor(c_actor)
    if spanning_cond_actor is not None:
        renderer.AddActor(spanning_cond_actor)
    if substrate_actor is not None:
        renderer.AddActor(substrate_actor)
    # Print resource usage stats
    if c_stats:
        mode = c_stats.get('mode')
        num_blocks = c_stats.get('blocks')  # Use different variable name to avoid overwriting blocks list
        dt = c_stats.get('build_time_s')
        memd = c_stats.get('mem_delta_mb')
        extra = f" tris={c_stats.get('tris')}" if mode == 'classic' else f" instances={c_stats.get('instances')}"
        print(f"[STATS] mode={mode} blocks={num_blocks}{extra} build_time={dt:.3f}s mem_increase={memd:.1f}MB")

    # Mediums are not rendered per-block; instead we add a translucent
    # window-sized box to hint the simulation domain.

    # Add a translucent window box representing the medium domain
    window_actor = None
    lines_actor = None
    ground_actor = None
    dielectric_actor_ref = None  # Initialize dielectric actor reference
    if getattr(parsed, 'window', None) is not None:
        w = parsed.window
        try:
            x1 = float(min(w.v1[0], w.v2[0])); y1 = float(min(w.v1[1], w.v2[1])); z1 = float(min(w.v1[2], w.v2[2]))
            x2 = float(max(w.v1[0], w.v2[0])); y2 = float(max(w.v1[1], w.v2[1]))
            # Find the uppermost conductor Z and limit window height to that
            uppermost_z = _get_uppermost_conductor_z(blocks)
            z2 = min(float(max(w.v1[2], w.v2[2])), uppermost_z)
                        # Add small epsilon to prevent z-fighting with conductors
            eps = max((x2-x1), (y2-y1), (z2-z1)) * 1e-6
            x1 -= eps; y1 -= eps; z1 -= eps
            x2 += eps; y2 += eps; z2 += eps
            w_points = vtk.vtkPoints()
            if hasattr(w_points, 'SetDataTypeToFloat'):
                w_points.SetDataTypeToFloat()
            w_polys = vtk.vtkCellArray()
            _append_box(w_points, w_polys, x1, y1, z1, x2, y2, z2)
            w_poly = vtk.vtkPolyData()
            w_poly.SetPoints(w_points)
            w_poly.SetPolys(w_polys)
            # Light normals for proper shading
            w_normals = vtk.vtkPolyDataNormals()
            w_normals.SetInputData(w_poly)
            w_normals.ComputeCellNormalsOn()
            w_normals.ComputePointNormalsOff()
            w_normals.SplittingOff()
            w_normals.ConsistencyOn()
            w_normals.AutoOrientNormalsOn()
            w_normals.Update()
            w_mapper = vtk.vtkPolyDataMapper()
            w_mapper.SetInputData(w_normals.GetOutput())
            w_actor = vtk.vtkActor()
            w_actor.SetMapper(w_mapper)
            # Soft bluish translucent volume hint
            w_actor.GetProperty().SetColor(0.65, 0.78, 0.95)
            w_actor.GetProperty().SetOpacity(0.18)
            w_actor.GetProperty().LightingOn()
            w_actor.GetProperty().SetDiffuse(0.8)
            w_actor.GetProperty().SetSpecular(0.05)
            w_actor.GetProperty().BackfaceCullingOn()
            renderer.AddActor(w_actor)
            window_actor = w_actor

            # Add gray lines at each plate_medium z-top within the window to show layer splits
            # Only show lines for layers that have actual conductors
            if getattr(parsed, 'plate_mediums', None):
                zs = sorted({float(pm.z_top) for pm in parsed.plate_mediums if pm.z_top is not None})
                # Never draw the highest dielectric split (often "air" cap)
                if zs:
                    top_z = max(zs)
                    zs = [z for z in zs if z != top_z]
                # Filter out Z levels that don't have conductors
                zs = [z for z in zs if _has_conductors_at_z(z, blocks)]
                # Build a single polydata with multiple polylines for efficiency
                l_points = vtk.vtkPoints()
                l_lines = vtk.vtkCellArray()
                if hasattr(l_points, 'SetDataTypeToFloat'):
                    l_points.SetDataTypeToFloat()
                for z in zs:
                    if z <= z1 or z >= z2:
                        continue  # skip lines on the window boundaries
                    idx0 = l_points.InsertNextPoint(x1, y1, z)
                    idx1 = l_points.InsertNextPoint(x2, y1, z)
                    idx2 = l_points.InsertNextPoint(x2, y2, z)
                    idx3 = l_points.InsertNextPoint(x1, y2, z)
                    idx4 = l_points.InsertNextPoint(x1, y1, z)
                    polyline = vtk.vtkPolyLine()
                    polyline.GetPointIds().SetNumberOfIds(5)
                    polyline.GetPointIds().SetId(0, idx0)
                    polyline.GetPointIds().SetId(1, idx1)
                    polyline.GetPointIds().SetId(2, idx2)
                    polyline.GetPointIds().SetId(3, idx3)
                    polyline.GetPointIds().SetId(4, idx4)
                    l_lines.InsertNextCell(polyline)
                if l_lines.GetNumberOfCells() > 0:
                    l_poly = vtk.vtkPolyData()
                    l_poly.SetPoints(l_points)
                    l_poly.SetLines(l_lines)
                    l_mapper = vtk.vtkPolyDataMapper()
                    l_mapper.SetInputData(l_poly)
                    l_actor = vtk.vtkActor()
                    l_actor.SetMapper(l_mapper)
                    # Enhanced appearance: brighter color, thicker lines, more visible
                    l_actor.GetProperty().SetColor(0.7, 0.8, 1.0)  # Bright blue-gray color
                    l_actor.GetProperty().SetOpacity(0.8)  # Higher opacity for better visibility
                    l_actor.GetProperty().SetLineWidth(1.8)  # Thicker lines for prominence
                    l_actor.GetProperty().LightingOff()
                    renderer.AddActor(l_actor)
                    lines_actor = l_actor

            # Add 3D dielectric blocks from plate_medium data
            dielectric_actor = _build_dielectric_blocks(parsed, blocks, (x1, y1, z1, x2, y2, z2))
            if dielectric_actor is not None:
                renderer.AddActor(dielectric_actor)
                dielectric_actor_ref = dielectric_actor  # Store reference for toggle

            # Add an optional ground base (thin plate at window bottom)
            try:
                gz1 = z1
                # Thickness as a tiny fraction of the window height to avoid z-fighting
                gth = max((z2 - z1) * 1e-3, 1e-9)
                g_points = vtk.vtkPoints()
                if hasattr(g_points, 'SetDataTypeToFloat'):
                    g_points.SetDataTypeToFloat()
                g_polys = vtk.vtkCellArray()
                _append_box(g_points, g_polys, x1, y1, gz1, x2, y2, gz1 + gth)
                g_poly = vtk.vtkPolyData()
                g_poly.SetPoints(g_points)
                g_poly.SetPolys(g_polys)
                g_normals = vtk.vtkPolyDataNormals()
                g_normals.SetInputData(g_poly)
                g_normals.ComputeCellNormalsOn()
                g_normals.ComputePointNormalsOff()
                g_normals.SplittingOff()
                g_normals.ConsistencyOn()
                g_normals.AutoOrientNormalsOn()
                g_normals.Update()
                g_mapper = vtk.vtkPolyDataMapper()
                g_mapper.SetInputData(g_normals.GetOutput())
                g_actor = vtk.vtkActor()
                g_actor.SetMapper(g_mapper)
                g_actor.GetProperty().SetColor(0.4, 0.4, 0.45)
                g_actor.GetProperty().SetOpacity(0.25)
                g_actor.GetProperty().LightingOn()
                g_actor.GetProperty().SetDiffuse(0.8)
                g_actor.GetProperty().SetSpecular(0.05)
                g_actor.GetProperty().BackfaceCullingOn()
                renderer.AddActor(g_actor)
                ground_actor = g_actor
            except Exception:
                pass
        except Exception:
            pass

    # dielectric_actor_ref is now properly set within the window creation block above

    # Keyboard toggle 'm' to hide/show substrate conductor, spanning elements, layer marks, window, and dielectric blocks
    # Default view: hidden (same as pressing 'M' once)
    # When enabled: shows window with layer lines + dielectric intersection highlights + substrate/spanning elements

    
    if 'iren' in locals():
        toggle_state = {'on': False}

        def _toggle_state(new_on: bool):
            toggle_state['on'] = new_on
            # Always show window and layer lines when dielectrics are enabled
            if window_actor is not None:
                window_actor.SetVisibility(1 if new_on else 0)
            if lines_actor is not None:
                lines_actor.SetVisibility(1 if new_on else 0)
            # Show dielectric intersection highlights when enabled
            if dielectric_actor_ref is not None:
                dielectric_actor_ref.SetVisibility(1 if new_on else 0)
            # Show substrate and spanning elements when enabled
            if substrate_actor is not None:
                substrate_actor.SetVisibility(1 if new_on else 0)
            if spanning_cond_actor is not None:
                spanning_cond_actor.SetVisibility(1 if new_on else 0)
            # Show ground base when enabled
            if ground_actor is not None:
                ground_actor.SetVisibility(1 if new_on else 0)
            renWin.Render()

        def _key_cb(obj, evt):
            key = iren.GetKeySym()
            if key and key.lower() == 'm':
                _toggle_state(not toggle_state['on'])

        # Apply default hidden state
        _toggle_state(False)
        iren.AddObserver('KeyPressEvent', _key_cb)

        # Hover highlighting system
        hover_state = {
            'current_conductor': None,
            'highlight_actors': [],
            'info_actor': None
        }

        # Create text actor for conductor information display
        info_actor = vtk.vtkTextActor()
        info_actor.SetInput("")
        info_actor.GetTextProperty().SetFontFamilyToArial()
        info_actor.GetTextProperty().SetFontSize(14)
        info_actor.GetTextProperty().SetColor(1.0, 1.0, 1.0)
        info_actor.GetTextProperty().SetOpacity(0.9)
        info_actor.GetTextProperty().SetBackgroundColor(0.0, 0.0, 0.0)
        info_actor.GetTextProperty().SetBackgroundOpacity(0.7)
        info_actor.SetDisplayPosition(10, 40)  # Position above FPS counter
        renderer.AddActor2D(info_actor)
        hover_state['info_actor'] = info_actor

        # Create cell picker for hover detection
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(1e-6)

        # Hover move event handler
        def _hover_move_cb(obj, evt):
            try:
                # Get mouse position
                x, y = iren.GetEventPosition()

                # Pick at mouse position
                picker.Pick(x, y, 0, renderer)

                # Get picked actor and cell
                picked_actor = picker.GetActor()
                picked_cell = picker.GetCellId()

                # Determine which conductor we're hovering over
                new_conductor = None
                if picked_actor is not None and picked_cell >= 0:
                    # Try to match with any of the conductor actors
                    conductor_actors = [c_actor, spanning_cond_actor, substrate_actor]

                    if picked_actor in conductor_actors:
                        # Map cell ID back to block index
                        if use_instanced:
                            block_index = picked_cell  # In instanced mode, cell ID = instance ID
                        else:
                            block_index = picked_cell // 12  # 12 triangles per block in classic mode

                        if block_index in block_index_map:
                            block = block_index_map[block_index]
                            new_conductor = block_to_conductor.get(id(block))

                # Update highlight if conductor changed
                if new_conductor != hover_state['current_conductor']:
                    highlight_changed = False
                    text_changed = False

                    # Remove previous highlight/glow actors
                    if hover_state['highlight_actors']:
                        for actor in hover_state['highlight_actors']:
                            try:
                                renderer.RemoveActor(actor)
                            except Exception:
                                pass
                        hover_state['highlight_actors'] = []
                        highlight_changed = True

                    hover_state['current_conductor'] = new_conductor

                    if new_conductor and new_conductor in conductor_groups:
                        conductor_blocks = conductor_groups[new_conductor]
                        new_actors: List['vtk.vtkActor'] = []

                        highlight_actor = _build_highlight_conductor_actor(conductor_blocks, use_instanced)
                        if highlight_actor:
                            renderer.AddActor(highlight_actor)
                            new_actors.append(highlight_actor)

                        for glow_actor in _build_net_glow_actors(conductor_blocks):
                            renderer.AddActor(glow_actor)
                            new_actors.append(glow_actor)

                        if new_actors:
                            hover_state['highlight_actors'] = new_actors
                            highlight_changed = True

                        block_count = len(conductor_blocks)
                        info_actor.SetInput(f"Net: {new_conductor}\nBlocks: {block_count}")
                        text_changed = True
                    else:
                        info_actor.SetInput("")
                        text_changed = True

                    if highlight_changed or text_changed:
                        renWin.Render()

            except Exception as e:
                # Silently handle errors to avoid breaking interaction
                pass

        # Add hover move observer
        iren.AddObserver('MouseMoveEvent', _hover_move_cb)

    # FPS counter: prefer library timing if available; else fall back to EndEvent timing
    fps_actor = vtk.vtkTextActor()
    fps_actor.SetInput("FPS: --")
    fps_actor.GetTextProperty().SetFontFamilyToArial()
    fps_actor.GetTextProperty().SetFontSize(16)
    fps_actor.GetTextProperty().SetColor(1.0, 1.0, 1.0)
    fps_actor.GetTextProperty().SetOpacity(0.9)
    fps_actor.SetDisplayPosition(10, 10)
    renderer.AddActor2D(fps_actor)

    if hasattr(renWin, 'GetLastRenderTimeInSeconds'):
        # Newer VTK path
        def _fps_timer_cb(obj, evt):
            try:
                last = renWin.GetLastRenderTimeInSeconds()
                if last and last > 0:
                    fps_actor.SetInput(f"FPS: {1.0/last:5.1f}")
            except Exception:
                pass
            renWin.Render()
        iren.CreateRepeatingTimer(500)
        iren.AddObserver('TimerEvent', _fps_timer_cb)
    else:
        # Fallback: measure time between renders, drive renders by timer
        import time as _pytime
        fps_state = {'last': _pytime.perf_counter(), 'ema': 0.0}

        def _on_end_event(obj, evt):
            now = _pytime.perf_counter()
            dt = now - fps_state['last']
            if dt > 0:
                inst = 1.0 / dt
                fps_state['ema'] = 0.3 * inst + 0.7 * fps_state['ema']
                fps_actor.SetInput(f"FPS: {fps_state['ema']:5.1f}")
            fps_state['last'] = now

        def _timer_drive(obj, evt):
            renWin.Render()

        renWin.AddObserver('EndEvent', _on_end_event)
        iren.CreateRepeatingTimer(250)
        iren.AddObserver('TimerEvent', _timer_drive)

    renderer.ResetCamera()
    apply_start_angle(renderer, start_angle)
    renderer.ResetCameraClippingRange()
    renWin.Render()

    # Add rendering delay for complex scenes to ensure full rendering
    if screenshot_path is not None:
        import time
        print("Waiting for scene to fully render...")
        time.sleep(2.0)  # Wait 2 seconds for complex rendering
        renWin.Render()
        time.sleep(1.0)  # Additional wait
        renWin.Render()

    capture_initial_screenshot(renWin, screenshot_path)

    if screenshot_path is not None:
        print(f"Screenshot saved to: {screenshot_path}")
        return

    iren.Initialize()
    iren.Start()


def main() -> None:
    ap = argparse.ArgumentParser(description='VTK interactive CAP3D viewer (GPU-accelerated)')
    ap.add_argument('cap3d_file', help='Path to input .cap3d file')
    ap.add_argument('--max-blocks', type=int, default=200000, help='Limit blocks for rendering')
    ap.add_argument('--classic', action='store_true', help='Use classic triangle-based rendering (slower, more memory)')
    ap.add_argument('--start-angle', type=float, default=0.0, help='Rotate initial camera azimuth by this many degrees')
    ap.add_argument('--screenshot', type=Path, help='Optional PNG path to save the initial view')
    args = ap.parse_args()

    if not os.path.isfile(args.cap3d_file):
        raise SystemExit(f"File not found: {args.cap3d_file}")

    use_instanced = not args.classic  # Instanced by default, classic only if requested
    # Use white background when taking screenshot
    white_bg = args.screenshot is not None
    visualize_cap3d_vtk(
        args.cap3d_file,
        max_blocks=args.max_blocks,
        use_instanced=use_instanced,
        start_angle=args.start_angle,
        screenshot_path=args.screenshot,
        white_background=white_bg,
    )


if __name__ == '__main__':
    main()

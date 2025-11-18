#!/usr/bin/env python3
"""
Interactive GNN-Cap Graph Visualization

Visualizes GNN-Cap graph representations with interactive edge highlighting.
Reads PyTorch Geometric graph files (.pt) and displays 3D cuboid meshes with
hover-based connectivity visualization.

Features:
- 3D cuboid rendering with highlighted edges showing decomposition
- Interactive hover to highlight connected nodes
- Color-coded connections: warm tones (orange/red) for normal edges,
  cool tones (blue/purple) for virtual edges
- Edge lines: solid for normal edges, dashed for virtual edges

Requirements:
    - vtk: conda run -n klayout-net pip install vtk
    - torch: pip install torch
    - pyyaml: pip install pyyaml

Usage:
    python visualize_gnncap_graph.py <graph.pt> --tech <tech_stack.yaml> [options]

Example:
    python visualize_gnncap_graph.py data/test_graph.pt --tech tech/nangate45/nangate45_stack.yaml
"""

import sys
import argparse
import numpy as np
import yaml
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set
from collections import defaultdict

import torch
import vtk

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

from common.datasets import GRAPHS_DIR

# Color palette (same as cap3d_view.py)
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


def color_for_layer(layer: Optional[int]) -> Tuple[float, float, float]:
    """
    Get color for a layer from the 10-color palette.
    Returns RGB values in 0-1 range for VTK.
    """
    if layer is None:
        layer = 0
    rgb = PALETTE_10[layer % len(PALETTE_10)]
    return (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)


def get_warm_highlight(base_color: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Create warm-toned highlight (orange/red tint) from base color.
    Used for normal edges.
    """
    r, g, b = base_color
    # Shift towards warm tones (increase red, decrease blue)
    r = min(1.0, r * 1.3 + 0.2)
    g = min(1.0, g * 1.1)
    b = max(0.0, b * 0.6)
    return (r, g, b)


def get_cool_highlight(base_color: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Create cool-toned highlight (blue/purple tint) from base color.
    Used for virtual edges.
    """
    r, g, b = base_color
    # Shift towards cool tones (increase blue, decrease red)
    r = max(0.0, r * 0.6)
    g = min(1.0, g * 1.1)
    b = min(1.0, b * 1.3 + 0.2)
    return (r, g, b)


def create_box_polydata(
    center: Tuple[float, float, float],
    dimensions: Tuple[float, float, float]
) -> vtk.vtkPolyData:
    """
    Create a box polydata from center and dimensions.
    Returns polydata with triangulated faces (for solid rendering).
    """
    cx, cy, cz = center
    dx, dy, dz = dimensions

    # Half dimensions
    hx, hy, hz = dx / 2, dy / 2, dz / 2

    # 8 vertices
    points = vtk.vtkPoints()
    points.SetDataTypeToFloat()

    # Bottom face (z = cz - hz)
    points.InsertNextPoint(cx - hx, cy - hy, cz - hz)  # 0
    points.InsertNextPoint(cx + hx, cy - hy, cz - hz)  # 1
    points.InsertNextPoint(cx + hx, cy + hy, cz - hz)  # 2
    points.InsertNextPoint(cx - hx, cy + hy, cz - hz)  # 3

    # Top face (z = cz + hz)
    points.InsertNextPoint(cx - hx, cy - hy, cz + hz)  # 4
    points.InsertNextPoint(cx + hx, cy - hy, cz + hz)  # 5
    points.InsertNextPoint(cx + hx, cy + hy, cz + hz)  # 6
    points.InsertNextPoint(cx - hx, cy + hy, cz + hz)  # 7

    # Create triangulated faces (12 triangles for 6 faces)
    polys = vtk.vtkCellArray()

    # Face indices (each face = 2 triangles)
    face_triangles = [
        # Bottom face (z-)
        (0, 1, 2), (0, 2, 3),
        # Top face (z+)
        (4, 6, 5), (4, 7, 6),
        # Front face (y-)
        (0, 5, 1), (0, 4, 5),
        # Back face (y+)
        (3, 2, 6), (3, 6, 7),
        # Left face (x-)
        (0, 3, 7), (0, 7, 4),
        # Right face (x+)
        (1, 5, 6), (1, 6, 2),
    ]

    for v0, v1, v2 in face_triangles:
        polys.InsertNextCell(3)
        polys.InsertCellPoint(v0)
        polys.InsertCellPoint(v1)
        polys.InsertCellPoint(v2)

    # Create polydata
    polydata = vtk.vtkPolyData()
    polydata.SetPoints(points)
    polydata.SetPolys(polys)

    # Compute normals for proper lighting
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(polydata)
    normals.ComputeCellNormalsOn()
    normals.ComputePointNormalsOff()
    normals.SplittingOff()
    normals.ConsistencyOn()
    normals.AutoOrientNormalsOn()
    normals.Update()

    return normals.GetOutput()


def create_box_edges(
    center: Tuple[float, float, float],
    dimensions: Tuple[float, float, float]
) -> vtk.vtkPolyData:
    """
    Create wireframe edges of a box (12 edges only, no diagonals).
    Returns polydata with lines.
    """
    cx, cy, cz = center
    dx, dy, dz = dimensions

    # Half dimensions
    hx, hy, hz = dx / 2, dy / 2, dz / 2

    # 8 vertices
    points = vtk.vtkPoints()
    points.SetDataTypeToFloat()

    # Bottom face (z = cz - hz)
    points.InsertNextPoint(cx - hx, cy - hy, cz - hz)  # 0
    points.InsertNextPoint(cx + hx, cy - hy, cz - hz)  # 1
    points.InsertNextPoint(cx + hx, cy + hy, cz - hz)  # 2
    points.InsertNextPoint(cx - hx, cy + hy, cz - hz)  # 3

    # Top face (z = cz + hz)
    points.InsertNextPoint(cx - hx, cy - hy, cz + hz)  # 4
    points.InsertNextPoint(cx + hx, cy - hy, cz + hz)  # 5
    points.InsertNextPoint(cx + hx, cy + hy, cz + hz)  # 6
    points.InsertNextPoint(cx - hx, cy + hy, cz + hz)  # 7

    # Create the 12 edges of the box
    lines = vtk.vtkCellArray()

    # Bottom face edges (4 edges)
    edge_pairs = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # Bottom rectangle
        (4, 5), (5, 6), (6, 7), (7, 4),  # Top rectangle
        (0, 4), (1, 5), (2, 6), (3, 7),  # Vertical edges
    ]

    for p0, p1 in edge_pairs:
        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, p0)
        line.GetPointIds().SetId(1, p1)
        lines.InsertNextCell(line)

    # Create polydata
    polydata = vtk.vtkPolyData()
    polydata.SetPoints(points)
    polydata.SetLines(lines)

    return polydata


class GraphVisualizer:
    """Interactive graph visualizer using VTK"""

    def __init__(
        self,
        graph_path: str,
        max_nodes: Optional[int] = None,
        edge_width: float = 2.0
    ):
        """
        Initialize visualizer

        Args:
            graph_path: Path to .pt graph file
            max_nodes: Maximum number of nodes to display (None = all)
            edge_width: Width of edge lines
        """
        self.graph_path = Path(graph_path)
        self.max_nodes = max_nodes
        self.edge_width = edge_width

        # Load graph data
        print(f"Loading graph from: {graph_path}")
        # Use weights_only=False for PyTorch Geometric Data objects
        # This is safe since we're loading our own generated graph files
        self.data = torch.load(graph_path, weights_only=False)

        # Extract graph components
        self.node_features = self.data.x.numpy()  # [num_nodes, 3] - dimensions
        self.edge_index = self.data.edge_index.numpy()  # [2, num_edges]
        self.edge_is_virtual = self.data.edge_is_virtual.numpy()  # [num_edges]
        self.node_centers = self.data.node_centers.numpy()  # [num_nodes, 3]
        self.node_layers = self.data.node_layers  # List of layer indices

        self.num_nodes = len(self.node_features)
        self.num_edges = self.edge_index.shape[1]

        # Fix layer assignment based on Z-height
        # The cuboid decomposition assigns wrong layers, so we need to reassign based on Z
        self._fix_layer_assignment()

        unique_layers = sorted(set(self.node_layers))

        print(f"  Nodes: {self.num_nodes}")
        print(f"  Edges: {self.num_edges}")
        print(f"  Virtual edges: {self.edge_is_virtual.sum()}")
        print(f"  Unique layers (after Z-based correction): {unique_layers}")

        # Apply node limit if specified
        if self.max_nodes and self.num_nodes > self.max_nodes:
            print(f"  Limiting display to {self.max_nodes} nodes")
            self.num_nodes = self.max_nodes
            self.node_features = self.node_features[:self.max_nodes]
            self.node_centers = self.node_centers[:self.max_nodes]
            self.node_layers = self.node_layers[:self.max_nodes]
            # Filter edges to only include visible nodes
            mask = (self.edge_index[0] < self.max_nodes) & (self.edge_index[1] < self.max_nodes)
            self.edge_index = self.edge_index[:, mask]
            self.edge_is_virtual = self.edge_is_virtual[mask]
            self.num_edges = self.edge_index.shape[1]

        # Build edge lookup: node_id -> [(target_id, is_virtual), ...]
        self.edges_from_node: Dict[int, List[Tuple[int, bool]]] = defaultdict(list)
        for i in range(self.num_edges):
            src = int(self.edge_index[0, i])
            dst = int(self.edge_index[1, i])
            is_virtual = bool(self.edge_is_virtual[i])
            self.edges_from_node[src].append((dst, is_virtual))
            self.edges_from_node[dst].append((src, is_virtual))  # Undirected

        # Identify substrate nodes (lowest Z coordinates)
        self.substrate_node_ids = set()
        if self.num_nodes > 0:
            # Find the minimum Z coordinate among all node centers
            min_z = float('inf')
            for node_id in range(self.num_nodes):
                z_coord = self.node_centers[node_id][2]
                if z_coord < min_z:
                    min_z = z_coord

            # Find all nodes at the minimum Z coordinate (within small tolerance)
            tolerance = 1e-6
            for node_id in range(self.num_nodes):
                z_coord = self.node_centers[node_id][2]
                if abs(z_coord - min_z) < tolerance:
                    self.substrate_node_ids.add(node_id)

            print(f"  Identified {len(self.substrate_node_ids)} substrate nodes at Z={min_z:.6f}")

        # VTK components
        self.renderer = None
        self.render_window = None
        self.interactor = None
        self.picker = None

        # Actor storage
        self.cuboid_actors: List[vtk.vtkActor] = []  # Solid transparent actors
        self.edge_actors: List[vtk.vtkActor] = []    # Black wireframe actors
        self.substrate_actors: List[vtk.vtkActor] = []  # Substrate actors (separate for toggling)
        self.substrate_edge_actors: List[vtk.vtkActor] = []  # Substrate edge actors (separate for toggling)
        self.actor_to_node: Dict[int, int] = {}  # Actor memory address -> node ID

        # Highlight state
        self.highlight_actors: List[vtk.vtkActor] = []
        self.edge_line_actors: List[vtk.vtkActor] = []
        self.current_hover_node: Optional[int] = None

        # Substrate toggle state (visible by default so lowest layer shows up)
        self.substrate_visible = True

    def _fix_layer_assignment(self):
        """
        Fix layer assignment based on Z-height.

        The cuboid decomposition assigns incorrect layers because it uses center-point
        checking which fails when cuboids span multiple layers. We reassign layers
        based on Z-center height matching typical layer stack spacing.
        """
        # Define approximate Z-centers for each layer (from W0.cap3d analysis)
        # These are typical for NanGate45-like tech stacks
        # Extract layer information from CAP3D data instead of hardcoding
        layer_z_map = []
        if hasattr(self, 'layer_centers') and hasattr(self, 'node_layers'):
            # Build dynamic layer mapping from actual CAP3D data
            layer_to_z = {}
            for i in range(self.num_nodes):
                layer_id = self.node_layers[i]
                z_center = self.node_centers[i, 2]
                if layer_id not in layer_to_z:
                    layer_to_z[layer_id] = []
                layer_to_z[layer_id].append(z_center)

            # Average Z positions per layer and create sorted mapping
            for layer_id, z_positions in layer_to_z.items():
                avg_z = sum(z_positions) / len(z_positions)
                layer_z_map.append((layer_id, avg_z))

            # Sort by layer ID to maintain consistent ordering
            layer_z_map.sort(key=lambda x: x[0])
        else:
            # Fallback: empty mapping (will be handled gracefully)
            print("Warning: No layer information available, using empty layer mapping")

        # Reassign layers based on closest Z-center
        for i in range(self.num_nodes):
            z_center = self.node_centers[i, 2]

            # Find closest layer by Z-height
            min_dist = float('inf')
            best_layer = self.node_layers[i]  # Default to current

            for layer_id, layer_z in layer_z_map:
                dist = abs(z_center - layer_z)
                if dist < min_dist:
                    min_dist = dist
                    best_layer = layer_id

            self.node_layers[i] = best_layer

    def _create_cuboid_actors(self):
        """Create VTK actors for all cuboids: transparent solid + black wireframe edges"""
        print("Creating cuboid actors...")

        for node_id in range(self.num_nodes):
            center = tuple(self.node_centers[node_id])
            dimensions = tuple(self.node_features[node_id])
            layer = self.node_layers[node_id]
            # Use actual layer ID for color (same as cap3d_view.py)
            color = color_for_layer(layer)

            # Check if this is a substrate node
            is_substrate = node_id in self.substrate_node_ids

            # Create solid transparent actor
            solid_polydata = create_box_polydata(center, dimensions)
            solid_mapper = vtk.vtkPolyDataMapper()
            solid_mapper.SetInputData(solid_polydata)

            solid_actor = vtk.vtkActor()
            solid_actor.SetMapper(solid_mapper)
            solid_actor.GetProperty().SetColor(color)
            solid_actor.GetProperty().LightingOn()
            solid_actor.GetProperty().SetInterpolationToFlat()
            solid_actor.GetProperty().SetDiffuse(0.8)
            solid_actor.GetProperty().SetSpecular(0.2)
            solid_actor.GetProperty().SetSpecularPower(20.0)
            solid_actor.GetProperty().SetOpacity(0.7)  # Transparent

            # Store in appropriate list based on substrate status
            if is_substrate:
                self.substrate_actors.append(solid_actor)
            else:
                self.cuboid_actors.append(solid_actor)

            # Map solid actor to node ID for picking (works for both substrate and regular)
            self.actor_to_node[id(solid_actor)] = node_id

            # Create black wireframe edges (12 edges only)
            edge_polydata = create_box_edges(center, dimensions)
            edge_mapper = vtk.vtkPolyDataMapper()
            edge_mapper.SetInputData(edge_polydata)

            edge_actor = vtk.vtkActor()
            edge_actor.SetMapper(edge_mapper)
            edge_actor.GetProperty().SetColor(0.0, 0.0, 0.0)  # Black edges
            edge_actor.GetProperty().SetLineWidth(1.5)
            edge_actor.GetProperty().SetOpacity(1.0)  # Fully opaque edges
            edge_actor.GetProperty().LightingOff()

            # Store in appropriate list based on substrate status
            if is_substrate:
                self.substrate_edge_actors.append(edge_actor)
            else:
                self.edge_actors.append(edge_actor)

        print(f"  Created {len(self.cuboid_actors)} regular cuboid actors and {len(self.substrate_actors)} substrate actors")

    def _setup_renderer(self, white_background: bool = False, screenshot=None):
        """Setup VTK renderer and window"""
        self.renderer = vtk.vtkRenderer()
        # Set background based on mode
        if white_background:
            self.renderer.SetBackground(1.0, 1.0, 1.0)  # White for screenshots
        else:
            self.renderer.SetBackground(0.08, 0.09, 0.11)  # Dark for interactive use

        self.render_window = vtk.vtkRenderWindow()
        # Higher resolution for better screenshot quality
        if screenshot is not None:
            self.render_window.SetSize(1920, 1080)
        else:
            self.render_window.SetSize(1280, 960)
        # Enable MSAA for better quality when taking screenshots
        if screenshot is not None:
            self.render_window.SetMultiSamples(4)  # Enable anti-aliasing for screenshots
        else:
            self.render_window.SetMultiSamples(0)  # Disable MSAA for performance
        self.render_window.AddRenderer(self.renderer)
        self.render_window.SetWindowName("GNN-Cap Graph Viewer")

        # Add all solid cuboid actors (transparent)
        for actor in self.cuboid_actors:
            self.renderer.AddActor(actor)

        # Add all edge wireframe actors (black, opaque)
        for actor in self.edge_actors:
            self.renderer.AddActor(actor)

        # Add substrate actors (separate for toggling)
        for actor in self.substrate_actors:
            self.renderer.AddActor(actor)

        # Add substrate edge actors (separate for toggling)
        for actor in self.substrate_edge_actors:
            self.renderer.AddActor(actor)

    def _setup_interaction(self):
        """Setup interactive picker and callbacks"""
        self.interactor = vtk.vtkRenderWindowInteractor()
        self.interactor.SetRenderWindow(self.render_window)

        # Use trackball camera for intuitive interaction
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)

        # Setup picker
        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.001)
        self.interactor.SetPicker(self.picker)

        # Add mouse move callback
        self.interactor.AddObserver('MouseMoveEvent', self._on_mouse_move)

        # Add keyboard callback for substrate toggling
        self.interactor.AddObserver('KeyPressEvent', self._on_key_press)

        # Add info text
        self._add_info_text()

    def _add_info_text(self):
        """Add instructional text to the viewport"""
        unique_layers = len(set(self.node_layers))
        text = vtk.vtkTextActor()
        text.SetInput(
            f"Nodes: {self.num_nodes} | Edges: {self.num_edges} | Layers: {unique_layers}\n"
            "Hover over cuboid to highlight connections\n"
            "Orange/Red = Normal edges | Blue/Purple = Virtual edges"
        )
        text.GetTextProperty().SetFontFamilyToArial()
        text.GetTextProperty().SetFontSize(14)
        text.GetTextProperty().SetColor(1.0, 1.0, 1.0)
        text.GetTextProperty().SetOpacity(0.8)
        text.SetDisplayPosition(10, 10)
        self.renderer.AddActor2D(text)

    def _on_mouse_move(self, obj, event):
        """Handle mouse move events for hover detection"""
        # Get mouse position
        x, y = self.interactor.GetEventPosition()

        # Pick at mouse position
        self.picker.Pick(x, y, 0, self.renderer)
        picked_actor = self.picker.GetActor()

        if picked_actor is not None:
            actor_id = id(picked_actor)
            if actor_id in self.actor_to_node:
                node_id = self.actor_to_node[actor_id]

                # Only update if hovering over different node
                if node_id != self.current_hover_node:
                    self.current_hover_node = node_id
                    self._highlight_connected_nodes(node_id)
                    self.render_window.Render()
        else:
            # Not hovering over any cuboid
            if self.current_hover_node is not None:
                self.current_hover_node = None
                self._clear_highlights()
                self.render_window.Render()

    def _highlight_connected_nodes(self, node_id: int):
        """
        Highlight nodes connected to the given node and draw edge lines.

        Args:
            node_id: The hovered node ID
        """
        # Clear previous highlights
        self._clear_highlights()

        # Get connected nodes
        if node_id not in self.edges_from_node:
            return

        connected = self.edges_from_node[node_id]
        if not connected:
            return

        # Get hovered node info
        hover_center = self.node_centers[node_id]
        hover_layer = self.node_layers[node_id]
        hover_base_color = color_for_layer(hover_layer)

        # Create highlights for connected nodes and edge lines
        for target_id, is_virtual in connected:
            if target_id >= self.num_nodes:
                continue

            target_center = tuple(self.node_centers[target_id])
            target_dimensions = tuple(self.node_features[target_id])
            target_layer = self.node_layers[target_id]
            target_base_color = color_for_layer(target_layer)

            # Choose glow color based on edge type (bright, nearly white)
            if is_virtual:
                # Cool glow (bright blue-white)
                glow_color = (0.6, 0.8, 1.0)
                line_color = (0.4, 0.6, 1.0)  # Cool blue for virtual
            else:
                # Warm glow (bright orange-white)
                glow_color = (1.0, 0.7, 0.4)
                line_color = (1.0, 0.6, 0.3)  # Warm orange for normal

            # Create halo: slightly larger transparent shell around the cuboid
            halo_scale = 1.15  # 15% larger
            halo_dimensions = (
                target_dimensions[0] * halo_scale,
                target_dimensions[1] * halo_scale,
                target_dimensions[2] * halo_scale,
            )

            halo_polydata = create_box_polydata(target_center, halo_dimensions)
            halo_mapper = vtk.vtkPolyDataMapper()
            halo_mapper.SetInputData(halo_polydata)

            halo_actor = vtk.vtkActor()
            halo_actor.SetMapper(halo_mapper)
            halo_actor.GetProperty().SetColor(glow_color)
            halo_actor.GetProperty().SetOpacity(0.35)  # Semi-transparent halo
            halo_actor.GetProperty().LightingOn()
            halo_actor.GetProperty().SetDiffuse(0.9)
            halo_actor.GetProperty().SetSpecular(0.3)
            halo_actor.GetProperty().SetSpecularPower(30.0)
            halo_actor.SetPickable(0)  # Don't interfere with picking

            self.highlight_actors.append(halo_actor)
            self.renderer.AddActor(halo_actor)

            # Create edge line from hover center to target center
            line_source = vtk.vtkLineSource()
            line_source.SetPoint1(hover_center[0], hover_center[1], hover_center[2])
            line_source.SetPoint2(target_center[0], target_center[1], target_center[2])

            line_mapper = vtk.vtkPolyDataMapper()
            line_mapper.SetInputConnection(line_source.GetOutputPort())

            line_actor = vtk.vtkActor()
            line_actor.SetMapper(line_mapper)
            line_actor.GetProperty().SetColor(line_color)
            line_actor.GetProperty().SetLineWidth(self.edge_width)
            line_actor.GetProperty().SetOpacity(0.9)  # Slightly transparent
            line_actor.GetProperty().LightingOff()

            # Set line stipple for virtual edges (dashed)
            if is_virtual:
                line_actor.GetProperty().SetLineStipplePattern(0x00FF)  # Dashed
                line_actor.GetProperty().SetLineStippleRepeatFactor(1)

            self.edge_line_actors.append(line_actor)
            self.renderer.AddActor(line_actor)

        # Also highlight the hovered node itself with VERY STRONG bright white halo
        hover_dimensions = tuple(self.node_features[node_id])
        hover_glow_color = (1.0, 1.0, 1.0)  # Pure bright white

        # Create strong halo: much larger transparent shell
        hover_halo_scale = 1.35  # 35% larger for very visible halo
        hover_halo_dimensions = (
            hover_dimensions[0] * hover_halo_scale,
            hover_dimensions[1] * hover_halo_scale,
            hover_dimensions[2] * hover_halo_scale,
        )

        halo_polydata = create_box_polydata(tuple(hover_center), hover_halo_dimensions)
        halo_mapper = vtk.vtkPolyDataMapper()
        halo_mapper.SetInputData(halo_polydata)

        halo_actor = vtk.vtkActor()
        halo_actor.SetMapper(halo_mapper)
        halo_actor.GetProperty().SetColor(hover_glow_color)
        halo_actor.GetProperty().SetOpacity(0.65)  # Very strong, visible halo
        halo_actor.GetProperty().LightingOn()
        halo_actor.GetProperty().SetDiffuse(1.0)
        halo_actor.GetProperty().SetSpecular(0.7)  # High specular for bright shine
        halo_actor.GetProperty().SetSpecularPower(80.0)  # Sharp, bright highlight
        halo_actor.SetPickable(0)  # Don't interfere with picking

        self.highlight_actors.append(halo_actor)
        self.renderer.AddActor(halo_actor)


    def _clear_highlights(self):
        """Remove all highlight actors and edge lines"""
        for actor in self.highlight_actors:
            self.renderer.RemoveActor(actor)
        self.highlight_actors.clear()

        for actor in self.edge_line_actors:
            self.renderer.RemoveActor(actor)
        self.edge_line_actors.clear()

    def _on_key_press(self, obj, event):
        """Handle keyboard events for substrate toggling"""
        key = self.interactor.GetKeySym()
        if key and key.lower() == 'm':
            # Toggle substrate visibility
            self.substrate_visible = not self.substrate_visible
            visibility = 1 if self.substrate_visible else 0

            # Update substrate solid actors
            for actor in self.substrate_actors:
                actor.SetVisibility(visibility)

            # Update substrate edge actors
            for actor in self.substrate_edge_actors:
                actor.SetVisibility(visibility)

            # Re-render
            self.render_window.Render()

            # Print status message
            status = "shown" if self.substrate_visible else "hidden"
            print(f"Substrate nodes {status} (press 'M' to toggle)")

    def run(self, start_angle: float = 0.0, screenshot: Optional[Path] = None, screenshot_mode: bool = False):
        """Start the interactive visualization or screenshot-only mode"""
        if screenshot_mode:
            print("Running in screenshot-only mode...")
            print("  Auto-highlighting a conductor for visual interest")
        else:
            print("Starting interactive viewer...")
            print("  Hover over cuboids to see connections")
            print("  Orange/Red highlights = Normal edges (solid lines)")
            print("  Blue/Purple highlights = Virtual edges (dashed lines)")
            print("  Press 'M' to toggle substrate visibility")
            print("  Press 'q' to quit")

        self._create_cuboid_actors()
        # Use white background when taking screenshot
        white_bg = screenshot is not None
        self._setup_renderer(white_background=white_bg, screenshot=screenshot)
        self._setup_interaction()

        # Set initial substrate visibility (shown by default so lowest layer is visible)
        visibility = 1 if self.substrate_visible else 0
        for actor in self.substrate_actors:
            actor.SetVisibility(visibility)
        for actor in self.substrate_edge_actors:
            actor.SetVisibility(visibility)

        self.renderer.ResetCamera()
        apply_start_angle(self.renderer, start_angle)
        self.renderer.ResetCameraClippingRange()

        # For screenshot mode, auto-highlight a conductor for visual interest
        if screenshot_mode and self.num_nodes > 0:
            # Find a good conductor to highlight (not substrate, has connections)
            target_node = None
            for node_id in range(min(10, self.num_nodes)):  # Check first 10 nodes
                if node_id not in self.substrate_node_ids and node_id in self.edges_from_node:
                    if self.edges_from_node[node_id]:  # Has connections
                        target_node = node_id
                        break

            # If no suitable node found in first 10, use any non-substrate node with connections
            if target_node is None:
                for node_id in range(self.num_nodes):
                    if node_id not in self.substrate_node_ids and node_id in self.edges_from_node:
                        if self.edges_from_node[node_id]:
                            target_node = node_id
                            break

            # Highlight the selected node
            if target_node is not None:
                print(f"  Auto-highlighting node {target_node} with {len(self.edges_from_node[target_node])} connections")
                self._highlight_connected_nodes(target_node)
                self.current_hover_node = target_node

        self.render_window.Render()

        # Add rendering delay for complex scenes to ensure full rendering
        if screenshot is not None:
            import time
            print("Waiting for scene to fully render...")
            time.sleep(2.0)  # Wait 2 seconds for complex rendering
            self.render_window.Render()
            time.sleep(1.0)  # Additional wait
            self.render_window.Render()

        capture_initial_screenshot(self.render_window, screenshot)

        if screenshot_mode:
            print("Screenshot captured successfully!")
            return

        self.interactor.Initialize()
        self.interactor.Start()


def main():
    parser = argparse.ArgumentParser(
        description='Interactive GNN-Cap graph visualization',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  # Auto-discovery by window ID (recommended)
  python visualize_gnncap_graph.py W0
  python visualize_gnncap_graph.py W0 --max-nodes 1000

  # Direct file path (legacy)
  python visualize_gnncap_graph.py path/to/W0_graph.pt
  python visualize_gnncap_graph.py path/to/graph1.pt path/to/graph2.pt --graph-index 1

Note: With auto-discovery, files are searched in datasets/graphs/
and metadata is loaded from datasets/manifests/<window>.yaml
        """
    )

    parser.add_argument(
        'window_or_files',
        nargs='+',
        metavar='WINDOW_OR_FILE',
        help='Window ID (e.g., W0) for auto-discovery OR one or more .pt graph file paths'
    )

    parser.add_argument('--max-nodes', type=int, default=None,
                        help='Maximum number of nodes to display (for large graphs)')
    parser.add_argument('--edge-width', type=float, default=2.5,
                        help='Width of edge lines in pixels')
    parser.add_argument(
        '--graph-index',
        type=int,
        default=0,
        help='Index of the graph to visualize when multiple input files are provided'
    )
    parser.add_argument('--start-angle', type=float, default=0.0,
                        help='Rotate initial camera azimuth by this many degrees')
    parser.add_argument('--screenshot', type=Path,
                        help='Optional PNG path to save the initial view')

    args = parser.parse_args()

    # Determine if we're doing auto-discovery or using direct file paths
    if len(args.window_or_files) == 1 and not Path(args.window_or_files[0]).exists():
        # Auto-discovery mode (single argument that's not a file path)
        window_id = args.window_or_files[0]
        print(f"Auto-discovering GNN graph for window: {window_id}")

        graph_path, _ = auto_discover_gnn_graph(window_id)
        if graph_path is None:
            print(f"ERROR: No GNN graph found for window '{window_id}' in {GRAPHS_DIR}")
            print(f"  Expected file: {GRAPHS_DIR / f'{window_id}_graph.pt'}")
            return 1

        print(f"Found GNN graph: {graph_path}")

        selected_graph = str(graph_path)

    else:
        # Direct file path mode (legacy)
        graph_files = args.window_or_files
        if not graph_files:
            print("ERROR: No graph files provided")
            return 1

        num_graphs = len(graph_files)
        if args.graph_index < 0 or args.graph_index >= num_graphs:
            print(f"ERROR: graph-index {args.graph_index} is out of range for {num_graphs} input files")
            return 1

        if num_graphs > 1 and args.graph_index == 0:
            print("WARNING: Multiple graph files provided; displaying only the first. "
                  "Use --graph-index to view others.")

        selected_graph = graph_files[args.graph_index]

        # Check file exists
        if not Path(selected_graph).exists():
            print(f"ERROR: Graph file not found: {selected_graph}")
            return 1

    # Create and run visualizer
    visualizer = GraphVisualizer(
        graph_path=selected_graph,
        max_nodes=args.max_nodes,
        edge_width=args.edge_width
    )
    # Use screenshot mode when taking screenshot
    screenshot_mode = args.screenshot is not None
    visualizer.run(start_angle=args.start_angle, screenshot=args.screenshot, screenshot_mode=screenshot_mode)

    return 0


def auto_discover_gnn_graph(window_id: str) -> Tuple[Optional[Path], Optional[Dict]]:
    """
    Auto-discover GNN graph file for a given window ID.

    Args:
        window_id: Window identifier (e.g., 'W0', 'W1')

    Returns:
        Tuple of (graph_file_path, None) or (None, None) if not found
    """
    # Check for graph file in datasets/graphs/
    graph_path = GRAPHS_DIR / f"{window_id}_graph.pt"
    if not graph_path.exists():
        return None, None

    return graph_path, None


if __name__ == '__main__':
    sys.exit(main())

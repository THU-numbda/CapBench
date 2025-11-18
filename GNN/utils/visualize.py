"""
Visualization Tool for GNN-Cap Graphs

Creates interactive HTML visualizations of graph structures using pyvis.
Helps inspect node/edge attributes and graph topology.
"""

import torch
import networkx as nx
from pyvis.network import Network
import numpy as np
from pathlib import Path
import argparse
from typing import Optional, Dict
import json

import sys
sys.path.append(str(Path(__file__).parent.parent))
import config


def pytorch_geometric_to_networkx(data) -> nx.Graph:
    """
    Convert PyTorch Geometric Data to NetworkX graph

    Args:
        data: PyTorch Geometric Data object

    Returns:
        NetworkX Graph
    """
    G = nx.Graph()

    # Add nodes with attributes
    num_nodes = data.x.size(0)
    for i in range(num_nodes):
        node_features = data.x[i].cpu().numpy()

        # Get net name if available
        net_name = data.node_net_names[i] if hasattr(data, 'node_net_names') else f"node_{i}"

        # Get center coordinates if available
        center = data.node_centers[i].cpu().numpy() if hasattr(data, 'node_centers') else [0, 0, 0]

        # Get layer if available
        layer = data.node_layers[i] if hasattr(data, 'node_layers') else None

        G.add_node(
            i,
            label=f"{net_name}\n({node_features[0]:.2f}, {node_features[1]:.2f}, {node_features[2]:.2f})",
            x_len=float(node_features[0]),
            y_len=float(node_features[1]),
            z_len=float(node_features[2]),
            net_name=net_name,
            center_x=float(center[0]),
            center_y=float(center[1]),
            center_z=float(center[2]),
            layer=layer,
        )

    # Add edges with attributes
    edge_index = data.edge_index.cpu().numpy()
    edge_attr = data.edge_attr.cpu().numpy()
    edge_is_virtual = data.edge_is_virtual.cpu().numpy() if hasattr(data, 'edge_is_virtual') else np.zeros(edge_index.shape[1], dtype=bool)

    for idx in range(edge_index.shape[1]):
        source = int(edge_index[0, idx])
        target = int(edge_index[1, idx])

        edge_features = edge_attr[idx]
        is_virtual = bool(edge_is_virtual[idx])

        G.add_edge(
            source,
            target,
            distance=float(edge_features[0]),
            is_virtual=is_virtual,
            edge_type='virtual' if is_virtual else 'regular',
        )

    return G


def create_pyvis_visualization(
    G: nx.Graph,
    output_path: str = 'graph_visualization.html',
    color_by: str = 'net',  # 'net', 'layer', or 'none'
    node_size_scale: float = 100.0,
    edge_width_scale: float = 5.0,
    height: str = '800px',
    width: str = '100%',
    physics_enabled: bool = True
):
    """
    Create interactive pyvis visualization

    Args:
        G: NetworkX graph
        output_path: Output HTML file path
        color_by: How to color nodes ('net', 'layer', or 'none')
        node_size_scale: Scale factor for node sizes
        edge_width_scale: Scale factor for edge widths
        height: Canvas height
        width: Canvas width
        physics_enabled: Enable physics simulation
    """
    # Create pyvis network
    net = Network(
        height=height,
        width=width,
        bgcolor='#222222',
        font_color='white',
        directed=False
    )

    # Set physics
    if physics_enabled:
        net.barnes_hut(
            gravity=-5000,
            central_gravity=0.3,
            spring_length=100,
            spring_strength=0.001,
            damping=0.09,
            overlap=0
        )
    else:
        net.toggle_physics(False)

    # Color palette for nets or layers
    colors = [
        '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
        '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
        '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000',
        '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080'
    ]

    # Get unique net names or layers for coloring
    if color_by == 'net':
        unique_values = sorted(set(nx.get_node_attributes(G, 'net_name').values()))
    elif color_by == 'layer':
        unique_values = sorted(set(v for v in nx.get_node_attributes(G, 'layer').values() if v is not None))
    else:
        unique_values = []

    value_to_color = {val: colors[i % len(colors)] for i, val in enumerate(unique_values)}

    # Add nodes
    for node_id in G.nodes():
        node_data = G.nodes[node_id]

        # Determine color
        if color_by == 'net':
            color = value_to_color.get(node_data.get('net_name'), '#888888')
        elif color_by == 'layer':
            color = value_to_color.get(node_data.get('layer'), '#888888')
        else:
            color = '#3cb44b'

        # Calculate node size based on volume
        volume = node_data['x_len'] * node_data['y_len'] * node_data['z_len']
        size = max(5, min(50, node_size_scale * (volume ** (1/3))))  # Cube root for visual balance

        # Create tooltip
        tooltip = f"""
        <b>{node_data.get('net_name', 'Unknown')}</b><br>
        Dimensions: ({node_data['x_len']:.3f}, {node_data['y_len']:.3f}, {node_data['z_len']:.3f}) μm<br>
        Center: ({node_data['center_x']:.3f}, {node_data['center_y']:.3f}, {node_data['center_z']:.3f}) μm<br>
        Layer: {node_data.get('layer', 'N/A')}<br>
        Volume: {volume:.6f} μm³
        """

        net.add_node(
            node_id,
            label=node_data.get('label', str(node_id)),
            title=tooltip,
            color=color,
            size=size,
            shape='dot'
        )

    # Add edges
    for source, target, edge_data in G.edges(data=True):
        is_virtual = edge_data.get('is_virtual', False)

        # Edge style
        if is_virtual:
            color = '#ff6b6b'
            dashes = True
            width = 1
        else:
            color = '#4ecdc4'
            dashes = False
            # Width based on distance (shorter = stronger coupling)
            distance = edge_data.get('distance', 1.0)
            width = max(0.5, edge_width_scale / (distance + 0.1))

        # Create tooltip
        tooltip = f"""
        <b>Edge {source} → {target}</b><br>
        Type: {'Virtual' if is_virtual else 'Regular'}<br>
        Distance: {edge_data.get('distance', 'N/A'):.3f} μm
        """

        net.add_edge(
            source,
            target,
            title=tooltip,
            color=color,
            width=width,
            dashes=dashes
        )

    # Add legend
    legend_html = f"""
    <div style="position: fixed; top: 10px; right: 10px; background: rgba(34,34,34,0.9);
                padding: 15px; border-radius: 5px; color: white; font-family: Arial;">
        <h3 style="margin-top: 0;">GNN-Cap Graph</h3>
        <p><span style="color: #4ecdc4;">━━</span> Regular Edge</p>
        <p><span style="color: #ff6b6b;">┄┄</span> Virtual Edge</p>
        <p>Node size ∝ volume</p>
        <p>Edge width ∝ 1/distance</p>
        <br>
        <p><b>Stats:</b></p>
        <p>Nodes: {G.number_of_nodes()}</p>
        <p>Edges: {G.number_of_edges()}</p>
    </div>
    """

    # Save
    net.save_graph(output_path)

    # Add legend to HTML
    with open(output_path, 'r') as f:
        html_content = f.read()

    html_content = html_content.replace('</body>', f'{legend_html}</body>')

    with open(output_path, 'w') as f:
        f.write(html_content)

    print(f"Saved interactive visualization to: {output_path}")
    print(f"Open in browser to explore the graph")


def visualize_graph_file(
    graph_file: str,
    output_path: Optional[str] = None,
    color_by: str = 'net',
    **kwargs
):
    """
    Visualize a graph from a .pt file

    Args:
        graph_file: Path to .pt file
        output_path: Output HTML path (default: same name as input with .html)
        color_by: How to color nodes
        **kwargs: Additional arguments for create_pyvis_visualization
    """
    print(f"Loading graph from: {graph_file}")

    # Load graph (weights_only=False needed for PyTorch Geometric Data objects)
    data = torch.load(graph_file, weights_only=False)

    # Convert to NetworkX
    print("Converting to NetworkX...")
    G = pytorch_geometric_to_networkx(data)

    print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

    # Determine output path
    if output_path is None:
        output_path = str(Path(graph_file).with_suffix('.html'))

    # Create visualization
    print("Creating interactive visualization...")
    create_pyvis_visualization(G, output_path, color_by=color_by, **kwargs)


def main():
    parser = argparse.ArgumentParser(description='Visualize GNN-Cap graphs')
    parser.add_argument('input', help='Input .pt graph file')
    parser.add_argument('-o', '--output', help='Output HTML file (default: same name as input)')
    parser.add_argument('--color-by', choices=['net', 'layer', 'none'], default='net',
                        help='How to color nodes')
    parser.add_argument('--node-size-scale', type=float, default=100.0,
                        help='Scale factor for node sizes')
    parser.add_argument('--edge-width-scale', type=float, default=5.0,
                        help='Scale factor for edge widths')
    parser.add_argument('--no-physics', action='store_true',
                        help='Disable physics simulation')

    args = parser.parse_args()

    visualize_graph_file(
        graph_file=args.input,
        output_path=args.output,
        color_by=args.color_by,
        node_size_scale=args.node_size_scale,
        edge_width_scale=args.edge_width_scale,
        physics_enabled=not args.no_physics
    )


if __name__ == '__main__':
    main()

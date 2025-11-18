#!/usr/bin/env python3
"""Analyze dataset statistics: blocks, conductors, and files per dataset."""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import numpy as np

def parse_cap3d_blocks(cap3d_path: Path) -> Tuple[int, int, Dict[str, int], List[str]]:
    """
    Parse a CAP3D file and count blocks and conductors (nets).

    Returns:
        Tuple of (total_blocks, total_conductors, conductor_counts, net_names)
    """
    if not cap3d_path.exists():
        return 0, 0, {}, []

    total_blocks = 0
    conductor_counts = defaultdict(int)
    net_names = set()

    try:
        with open(cap3d_path, 'r') as f:
            lines = f.readlines()

        # Parse conductor sections
        conductors = []
        in_conductor = False

        for line in lines:
            line = line.strip()
            if '<conductor>' in line:
                in_conductor = True
            elif '</conductor>' in line:
                in_conductor = False
            elif in_conductor and line.startswith('name') and not line.startswith('<!--'):
                # Extract name from lines like '    name Net.1'
                parts = line.split()
                if len(parts) >= 2 and parts[0] == 'name':
                    conductor_name = parts[1]
                    # Filter out block names (usually numbers) and keep net names
                    if not conductor_name.isdigit():
                        conductors.append(conductor_name)

        for conductor_name in conductors:
            net_names.add(conductor_name)

        # Count blocks
        content = ''.join(lines)
        block_pattern = re.compile(r'<block[^>]*>', re.IGNORECASE)
        blocks = block_pattern.findall(content)
        total_blocks = len(blocks)

        # Extract layer information from blocks
        layer_pattern = re.compile(r'<layer>\s*(\d+)\s*</layer>', re.IGNORECASE)
        for block in blocks:
            layer_match = layer_pattern.search(block)
            if layer_match:
                layer_id = layer_match.group(1)
                conductor_counts[layer_id] += 1
            else:
                # Count blocks without explicit layer as "unspecified"
                conductor_counts["unspecified"] += 1

    except Exception as e:
        print(f"Warning: Error parsing {cap3d_path}: {e}")
        return 0, 0, {}, []

    return total_blocks, len(net_names), dict(conductor_counts), list(net_names)

def parse_graph_nodes(graph_path: Path) -> Tuple[int, Dict[str, int]]:
    """
    Parse a PyTorch Geometric graph file and count nodes/conductors.

    Returns:
        Tuple of (total_nodes, layer_counts)
    """
    if not graph_path.exists():
        return 0, {}

    try:
        import torch
        data = torch.load(graph_path)

        # Count nodes
        if hasattr(data, 'num_nodes'):
            total_nodes = data.num_nodes
        elif hasattr(data, 'x'):
            total_nodes = data.x.shape[0]
        else:
            total_nodes = 0

        # Try to get layer information if available
        layer_counts = {}
        if hasattr(data, 'layer') and data.layer is not None:
            unique_layers, counts = torch.unique(data.layer, return_counts=True)
            for layer_id, count in zip(unique_layers.tolist(), counts.tolist()):
                layer_counts[str(layer_id)] = count

        return total_nodes, layer_counts

    except Exception as e:
        print(f"Warning: Error loading graph {graph_path}: {e}")
        return 0, {}

def analyze_dataset_structure(base_path: Path) -> Dict:
    """Analyze the structure and statistics of a dataset."""
    dataset_info = {
        'path': str(base_path),
        'technology': base_path.parent.name,
        'size': base_path.name,
        'cap3d_files': [],
        'graph_files': [],
        'window_directories': [],
        'directories': []
    }

    # List all subdirectories
    for item in base_path.iterdir():
        if item.is_dir():
            dataset_info['directories'].append(item.name)

    # Look for CAP3D files in cap3d directory
    cap3d_dir = base_path / "cap3d"
    if cap3d_dir.exists():
        cap3d_files = list(cap3d_dir.glob("*.cap3d"))
        dataset_info['cap3d_files'] = [f.name for f in cap3d_files]

    # Look for graph files in graphs directory
    graphs_dir = base_path / "graphs"
    if graphs_dir.exists():
        graph_files = list(graphs_dir.glob("*.pt"))
        dataset_info['graph_files'].extend([f"graphs/{f.name}" for f in graph_files])

    # Look for window directories (W0, W1, etc.)
    window_dirs = [d for d in base_path.iterdir() if d.is_dir() and re.match(r'^W\d+$', d.name)]
    window_dirs.sort(key=lambda x: int(x.name[1:]))  # Sort by window number
    dataset_info['window_directories'] = [d.name for d in window_dirs]

    # Look for graph files in window directories
    for window_dir in window_dirs:
        graph_files = list(window_dir.glob("*.pt"))
        dataset_info['graph_files'].extend([f"{window_dir.name}/{f.name}" for f in graph_files])

    # Also look for top-level graph files
    top_graphs = list(base_path.glob("*.pt"))
    dataset_info['graph_files'].extend([f.name for f in top_graphs])

    return dataset_info

def count_blocks_and_conductors(base_path: Path) -> Dict:
    """Count blocks and conductors (nets) for a dataset."""
    stats = {
        'dataset_path': str(base_path),
        'technology': base_path.parent.name,
        'size': base_path.name,
        'total_blocks': 0,
        'total_conductors': 0,
        'window_stats': {},
        'layer_distribution': defaultdict(int),
        'analysis_method': 'unknown',
        'files_processed': 0,
        'blocks_per_file': [],
        'conductors_per_file': []
    }

    # Try to analyze CAP3D files first - check for cap3d directory
    cap3d_dir = base_path / "cap3d"
    cap3d_files = []

    if cap3d_dir.exists():
        cap3d_files = list(cap3d_dir.glob("*.cap3d"))

    if cap3d_files:
        stats['analysis_method'] = 'CAP3D'
        total_dataset_blocks = 0
        total_dataset_conductors = 0
        total_dataset_conductor_counts = defaultdict(int)
        blocks_per_file = []
        conductors_per_file = []

        print(f"  Found {len(cap3d_files)} CAP3D files")
        for i, cap3d_file in enumerate(cap3d_files):
            if i % 100 == 0 and i > 0:
                print(f"    Processed {i} CAP3D files...")

            blocks, conductors, conductor_counts, net_names = parse_cap3d_blocks(cap3d_file)
            total_dataset_blocks += blocks
            total_dataset_conductors += conductors
            stats['total_blocks'] += blocks
            stats['total_conductors'] += conductors
            blocks_per_file.append(blocks)
            conductors_per_file.append(conductors)

            for layer, count in conductor_counts.items():
                total_dataset_conductor_counts[layer] += count
                stats['layer_distribution'][layer] += count

        stats['files_processed'] = len(cap3d_files)
        stats['blocks_per_file'] = blocks_per_file
        stats['conductors_per_file'] = conductors_per_file

        # Calculate block statistics
        if blocks_per_file:
            stats['avg_blocks_per_file'] = np.mean(blocks_per_file)
            stats['std_blocks_per_file'] = np.std(blocks_per_file)
            stats['median_blocks_per_file'] = np.median(blocks_per_file)
            stats['min_blocks_per_file'] = np.min(blocks_per_file)
            stats['max_blocks_per_file'] = np.max(blocks_per_file)
        else:
            stats['avg_blocks_per_file'] = 0
            stats['std_blocks_per_file'] = 0
            stats['median_blocks_per_file'] = 0
            stats['min_blocks_per_file'] = 0
            stats['max_blocks_per_file'] = 0

        # Calculate conductor statistics
        if conductors_per_file:
            stats['avg_conductors_per_file'] = np.mean(conductors_per_file)
            stats['std_conductors_per_file'] = np.std(conductors_per_file)
            stats['median_conductors_per_file'] = np.median(conductors_per_file)
            stats['min_conductors_per_file'] = np.min(conductors_per_file)
            stats['max_conductors_per_file'] = np.max(conductors_per_file)
        else:
            stats['avg_conductors_per_file'] = 0
            stats['std_conductors_per_file'] = 0
            stats['median_conductors_per_file'] = 0
            stats['min_conductors_per_file'] = 0
            stats['max_conductors_per_file'] = 0

    # If no CAP3D files, try to analyze graph files
    else:
        # Look for graphs directory
        graphs_dir = base_path / "graphs"
        graph_files = []

        if graphs_dir.exists():
            graph_files = list(graphs_dir.glob("*.pt"))

        # Also look for window directories with graph files
        window_dirs = [d for d in base_path.iterdir() if d.is_dir() and re.match(r'^W\d+$', d.name)]

        if graph_files or window_dirs:
            stats['analysis_method'] = 'Graph'
            total_dataset_nodes = 0
            total_dataset_layers = defaultdict(int)
            nodes_per_file = []

            if graph_files:
                print(f"  Found {len(graph_files)} graph files in graphs/ directory")
                for i, graph_file in enumerate(graph_files):
                    if i % 100 == 0 and i > 0:
                        print(f"    Processed {i} graph files...")

                    nodes, layer_counts = parse_graph_nodes(graph_file)
                    total_dataset_nodes += nodes
                    nodes_per_file.append(nodes)

                    for layer, count in layer_counts.items():
                        total_dataset_layers[layer] += count

            if window_dirs:
                print(f"  Found {len(window_dirs)} window directories with graphs")
                for window_dir in window_dirs:
                    window_graph_files = list(window_dir.glob("*.pt"))
                    if window_graph_files:
                        window_total = 0
                        window_layers = defaultdict(int)

                        for graph_file in window_graph_files:
                            nodes, layer_counts = parse_graph_nodes(graph_file)
                            window_total += nodes
                            nodes_per_file.append(nodes)

                            for layer, count in layer_counts.items():
                                window_layers[layer] += count
                                total_dataset_layers[layer] += count

                        total_dataset_nodes += window_total
                        stats['window_stats'][window_dir.name] = {
                            'total_nodes': window_total,
                            'layer_counts': dict(window_layers),
                            'graph_files': len(window_graph_files)
                        }

            stats['total_blocks'] = total_dataset_nodes  # Use nodes as blocks for graphs
            stats['total_conductors'] = sum(total_dataset_layers.values())
            stats['layer_distribution'] = dict(total_dataset_layers)
            stats['files_processed'] = len(graph_files) + sum(len(list(d.glob("*.pt"))) for d in window_dirs)
            stats['blocks_per_file'] = nodes_per_file

            # Calculate statistics
            if nodes_per_file:
                stats['avg_blocks_per_file'] = np.mean(nodes_per_file)
                stats['std_blocks_per_file'] = np.std(nodes_per_file)
                stats['median_blocks_per_file'] = np.median(nodes_per_file)
                stats['min_blocks_per_file'] = np.min(nodes_per_file)
                stats['max_blocks_per_file'] = np.max(nodes_per_file)
            else:
                stats['avg_blocks_per_file'] = 0
                stats['std_blocks_per_file'] = 0
                stats['median_blocks_per_file'] = 0
                stats['min_blocks_per_file'] = 0
                stats['max_blocks_per_file'] = 0

    return stats

def format_table(rows: List[List[str]]) -> str:
    """Format data as a markdown table."""
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]

    def fmt(row: List[str]) -> str:
        return "| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |"

    separator = "|-" + "-|-".join("-" * w for w in widths) + "-|"
    table_lines = [fmt(rows[0]), separator]
    table_lines.extend(fmt(row) for row in rows[1:])
    return "\n".join(table_lines)

def main():
    """Main analysis function."""
    print("Dataset Statistics Analysis")
    print("=" * 80)
    print("Analyzing blocks, conductors, and structure per dataset...")
    print("=" * 80)

    # Find all dataset directories
    datasets_path = Path("datasets")
    if not datasets_path.exists():
        print("Error: datasets directory not found!")
        return

    # Collect all datasets
    all_datasets = []
    for tech_dir in datasets_path.iterdir():
        if tech_dir.is_dir() and tech_dir.name not in ['__pycache__']:
            for size_dir in tech_dir.iterdir():
                if size_dir.is_dir():
                    all_datasets.append(size_dir)

    all_datasets.sort(key=lambda x: (x.parent.name, x.name))

    print(f"Found {len(all_datasets)} datasets to analyze\n")

    # Analyze each dataset
    dataset_results = []

    for dataset_path in all_datasets:
        technology = dataset_path.parent.name
        size = dataset_path.name

        print(f"Analyzing {technology.upper()} {size.upper()}...")

        # First get structure info
        structure_info = analyze_dataset_structure(dataset_path)

        # Then count blocks and conductors
        stats = count_blocks_and_conductors(dataset_path)
        stats.update(structure_info)

        dataset_results.append(stats)

        # Print brief summary for this dataset
        print(f"  Analysis method: {stats['analysis_method']}")
        print(f"  Files processed: {stats.get('files_processed', 0):,}")
        print(f"  Total blocks: {stats['total_blocks']:,}")
        print(f"  Total conductors: {stats['total_conductors']:,}")
        print(f"  Avg blocks per file: {stats.get('avg_blocks_per_file', 0):.1f}")
        print(f"  Std blocks per file: {stats.get('std_blocks_per_file', 0):.1f}")
        print(f"  Avg conductors per file: {stats.get('avg_conductors_per_file', 0):.1f}")
        print(f"  Std conductors per file: {stats.get('std_conductors_per_file', 0):.1f}")
        print(f"  Median blocks per file: {stats.get('median_blocks_per_file', 0):.1f}")
        print(f"  Median conductors per file: {stats.get('median_conductors_per_file', 0):.1f}")
        print(f"  Min-Max blocks per file: {stats.get('min_blocks_per_file', 0):,} - {stats.get('max_blocks_per_file', 0):,}")
        print(f"  Min-Max conductors per file: {stats.get('min_conductors_per_file', 0):,} - {stats.get('max_conductors_per_file', 0):,}")
        print(f"  CAP3D files: {len(stats['cap3d_files'])}")
        print(f"  Graph files: {len(stats['graph_files'])}")
        print(f"  Window directories: {len(stats['window_directories'])}")

        if stats['layer_distribution']:
            print(f"  Layer distribution: {dict(stats['layer_distribution'])}")
        print()

    # Generate summary table
    print("=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)

    summary_rows = [
        ["Technology", "Size", "Analysis", "Files", "Avg Blocks/File", "Std Blocks/File", "Avg Conductors/File", "Std Conductors/File", "Median Blocks", "Median Conductors"]
    ]

    for stats in dataset_results:
        summary_rows.append([
            stats['technology'].upper(),
            stats['size'].upper(),
            stats['analysis_method'],
            f"{stats.get('files_processed', 0):,}",
            f"{stats.get('avg_blocks_per_file', 0):.1f}",
            f"{stats.get('std_blocks_per_file', 0):.1f}",
            f"{stats.get('avg_conductors_per_file', 0):.1f}",
            f"{stats.get('std_conductors_per_file', 0):.1f}",
            f"{stats.get('median_blocks_per_file', 0):.1f}",
            f"{stats.get('median_conductors_per_file', 0):.1f}"
        ])

    print(format_table(summary_rows))

    # Detailed breakdown by technology
    print(f"\n{'='*80}")
    print("DETAILED BREAKDOWN")
    print(f"{'='*80}")

    # Group by technology
    by_tech = defaultdict(list)
    for stats in dataset_results:
        by_tech[stats['technology']].append(stats)

    for technology, tech_datasets in by_tech.items():
        print(f"\n{technology.upper()} Technology:")
        print("-" * 40)

        for stats in tech_datasets:
            print(f"  {stats['size'].upper()}:")
            print(f"    Method: {stats['analysis_method']}")
            print(f"    Files: {stats.get('files_processed', 0):,}")
            print(f"    Total blocks: {stats['total_blocks']:,}")
            print(f"    Total conductors: {stats['total_conductors']:,}")
            print(f"    Avg blocks per file: {stats.get('avg_blocks_per_file', 0):.1f} ± {stats.get('std_blocks_per_file', 0):.1f}")
            print(f"    Avg conductors per file: {stats.get('avg_conductors_per_file', 0):.1f} ± {stats.get('std_conductors_per_file', 0):.1f}")
            print(f"    Blocks per file range: {stats.get('min_blocks_per_file', 0):,} - {stats.get('max_blocks_per_file', 0):,}")
            print(f"    Conductors per file range: {stats.get('min_conductors_per_file', 0):,} - {stats.get('max_conductors_per_file', 0):,}")

            if stats['window_stats']:
                print(f"    Window breakdown:")
                for window, window_stats in sorted(stats['window_stats'].items(),
                                                  key=lambda x: int(x[0][1:]) if x[0][1:].isdigit() else x[0]):
                    print(f"      {window}: {window_stats['total_nodes']:,} nodes, "
                          f"{window_stats['graph_files']} graphs")

    # Save detailed results to JSON
    output_file = Path("dataset_statistics.json")
    with open(output_file, 'w') as f:
        # Convert defaultdict to regular dict for JSON serialization
        json_results = []
        for stats in dataset_results:
            json_stats = dict(stats)
            json_stats['layer_distribution'] = dict(stats['layer_distribution'])

            # Convert numpy types to regular Python types for JSON serialization
            for key in ['avg_blocks_per_file', 'std_blocks_per_file', 'median_blocks_per_file',
                       'avg_conductors_per_file', 'std_conductors_per_file', 'median_conductors_per_file']:
                if key in json_stats and json_stats[key] is not None:
                    json_stats[key] = float(json_stats[key])
            for key in ['min_blocks_per_file', 'max_blocks_per_file', 'min_conductors_per_file', 'max_conductors_per_file']:
                if key in json_stats and json_stats[key] is not None:
                    json_stats[key] = int(json_stats[key])

            json_results.append(json_stats)

        json.dump(json_results, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    main()
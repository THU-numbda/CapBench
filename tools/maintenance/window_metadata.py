#!/usr/bin/env python3
"""
Enhanced Window Generation Script

Creates non-overlapping small, medium, and large windows for IC designs.
Generates windows for all three sizes simultaneously with integrated visualization.

Features:
- 10×10 grid-based placement with random positioning within tiles
- Automatic design discovery from designs directory
- Automatic directory structure creation (datasets/{tech_node}/{size}/)
- Integrated visualization with PNG output
- Single script execution for all window sizes
- Non-overlapping window placement

Usage:
    python -m tools.maintenance.window_metadata [--windows-per-design N] [--seed SEED] [--output OUTPUT]

Examples:
    python -m tools.maintenance.window_metadata
    python -m tools.maintenance.window_metadata --windows-per-design 50
    python -m tools.maintenance.window_metadata --seed 123
    python -m tools.maintenance.window_metadata --output /custom/path

Default: 100 windows per size category per design, 10×10 grid
"""

import argparse
import math
import random
import sys
import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set

try:
    import yaml
except ImportError:  # pragma: no cover - depends on runtime environment
    yaml = None

# Ensure matplotlib uses a non-interactive backend for headless environments
os.environ.setdefault("MPLBACKEND", "Agg")

# No external dependencies for core functionality


def _require_yaml_module():
    if yaml is None:
        raise RuntimeError("PyYAML is required to run tools.maintenance.window_metadata")
    return yaml


class DesignInfo:
    """Information about a design and its associated files"""
    def __init__(self, name: str, tech_node: str, gds_file: str, def_file: str):
        self.name = name  # e.g., "ibex", "jpeg"
        self.tech_node = tech_node  # e.g., "nangate45", "asap7", "sky130hd"
        self.full_name = f"{name}_{tech_node}"  # e.g., "ibex_nangate45"
        self.gds_file = gds_file
        self.def_file = def_file
        self.stack_file = f"tech/{tech_node}.yaml"
        self.layermap_file = f"tech/{tech_node}.layermap"
        self.bounds = None  # (x1, y1, x2, y2) usable area in microns
        self.total_bounds = None  # Original DIEAREA bounds (no margin)


class MultiSizeWindowGenerator:
    """Generates non-overlapping windows of all sizes for designs"""

    def __init__(
        self,
        windows_per_design: int = 100,
        seed: int = 42,
        output_path: str | None = None,
        designs_root: str | None = None,
    ):
        self.windows_per_design = windows_per_design
        self.seed = seed

        self.repo_root = Path.cwd().resolve()
        self.designs_root = Path(designs_root).resolve() if designs_root else self.repo_root / "designs"

        # Set output path (default to datasets directory)
        if output_path is None:
            self.base_path = self.repo_root / "datasets"
        else:
            self.base_path = Path(output_path).resolve()

        random.seed(seed)

        self.size_categories = ['small', 'medium', 'large']
        self.existing_windows: Dict[str, Dict[str, Dict[str, Dict]]] = {}

        # Technology-specific window sizes (microns) for different size categories
        self.window_sizes = {
            'small': {
                'nangate45': (2.0, 2.0),     
                'asap7': (0.75, 0.75),         
                'sky130hd': (4.5, 4.5),    
            },
            'medium': {
                'nangate45': (5.0, 5.0),   
                'asap7': (2.5, 2.5),        
                'sky130hd': (10.0, 10.0),  
            },
            'large': {
                'nangate45': (10.0, 10.0),  
                'asap7': (5.0, 5.0),     
                'sky130hd': (20.0, 20.0), 
            }
        }

        # Window colors for visualization
        self.window_colors = {
            'small': (255, 100, 100, 128),    # Red, semi-transparent
            'medium': (100, 255, 100, 128),   # Green, semi-transparent
            'large': (100, 100, 255, 128),    # Blue, semi-transparent
        }

    def discover_designs(self) -> List[DesignInfo]:
        """Automatically discover available designs from the designs directory"""
        designs = []
        base_path = self.designs_root / "gds"

        # Find all GDS files and extract design names and tech nodes
        for gds_file in base_path.glob("*.gds"):
            filename = gds_file.stem
            if '.' in filename:
                design_name, tech_node = filename.rsplit('.', 1)

                # Check for corresponding DEF file
                def_file = base_path.parent / "def" / f"{filename}.def"

                if def_file.exists():
                    design = DesignInfo(design_name, tech_node, str(gds_file), str(def_file))
                    designs.append(design)

        return designs

    def parse_def_bounds(self, def_file: str) -> Tuple[Optional[Tuple[float, float, float, float]], Optional[Tuple[float, float, float, float]]]:
        """Extract usable (with margin) and total design boundaries from DEF file"""
        try:
            with open(def_file, 'r') as f:
                content = f.read()

            # Extract units from DEF file
            units_match = re.search(r'UNITS\s+DISTANCE\s+MICRONS\s+(\d+)', content)
            units_per_micron = int(units_match.group(1)) if units_match else 1000

            # Look for DIEAREA statement
            diearea_match = re.search(r'DIEAREA\s*\(\s*([\d.-]+)\s+([\d.-]+)\s*\)\s*\(\s*([\d.-]+)\s+([\d.-]+)\s*\)', content)

            if diearea_match:
                x1, y1, x2, y2 = map(float, diearea_match.groups())
                # Convert from DEF units to micrometers
                x1, y1, x2, y2 = x1/units_per_micron, y1/units_per_micron, x2/units_per_micron, y2/units_per_micron
                total_bounds = (x1, y1, x2, y2)

                # Add 10% margin around edges for window placement
                margin = 0.10
                total_width = x2 - x1
                total_height = y2 - y1
                margin_x = total_width * margin
                margin_y = total_height * margin

                x1 += margin_x
                y1 += margin_y
                x2 -= margin_x
                y2 -= margin_y
                usable_bounds = (x1, y1, x2, y2)

                return usable_bounds, total_bounds

        except Exception:
            pass

        return None, None

    def _create_grid_tiles(self, bounds: Tuple[float, float, float, float], grid_size: int) -> List[Tuple[float, float, float, float]]:
        """Create grid tiles for the design area using the specified grid size"""
        x1, y1, x2, y2 = bounds
        total_width = x2 - x1
        total_height = y2 - y1

        tile_width = total_width / grid_size
        tile_height = total_height / grid_size

        tiles = []
        for row in range(grid_size):
            for col in range(grid_size):
                tile_x1 = x1 + col * tile_width
                tile_y1 = y1 + row * tile_height
                tile_x2 = tile_x1 + tile_width
                tile_y2 = tile_y1 + tile_height
                tiles.append((tile_x1, tile_y1, tile_x2, tile_y2))

        return tiles

    def _can_fit_window_in_tile(self, tile: Tuple[float, float, float, float],
                               window_width: float, window_height: float) -> bool:
        """Check if a window can fit within a tile"""
        tile_x1, tile_y1, tile_x2, tile_y2 = tile
        tile_width = tile_x2 - tile_x1
        tile_height = tile_y2 - tile_y1
        return tile_width >= window_width and tile_height >= window_height

    def _sample_window_in_tile(self, tile: Tuple[float, float, float, float],
                              window_width: float, window_height: float,
                              window_id: int, size_category: str) -> Dict:
        """Sample a window within a tile"""
        tile_x1, tile_y1, tile_x2, tile_y2 = tile
        tile_width = tile_x2 - tile_x1
        tile_height = tile_y2 - tile_y1

        # Random position within tile
        max_x_offset = tile_width - window_width
        max_y_offset = tile_height - window_height

        if max_x_offset <= 0 or max_y_offset <= 0:
            raise ValueError(f"Tile too small for {size_category} window {window_id}")

        x_offset = random.uniform(0, max_x_offset)
        y_offset = random.uniform(0, max_y_offset)

        window_x1 = tile_x1 + x_offset
        window_y1 = tile_y1 + y_offset
        window_x2 = window_x1 + window_width
        window_y2 = window_y1 + window_height

        return {
            'name': f'W{window_id}',
            'size_category': size_category,
            'x1': round(window_x1, 3),
            'y1': round(window_y1, 3),
            'x2': round(window_x2, 3),
            'y2': round(window_y2, 3),
            'width': round(window_width, 3),
            'height': round(window_height, 3),
        }

    def generate_windows_for_design(self, design: DesignInfo) -> Dict[str, List[Dict]]:
        """Generate non-overlapping 9-window structures for a single design"""
        # Bounds should already be parsed in the main run method
        if design.bounds is None:
            return {}

        # Calculate optimal grid size and window count
        grid_size, optimal_count = self._calculate_optimal_grid_size(design)

        # Create grid tiles
        tiles = self._create_grid_tiles(design.bounds, grid_size)

        # Initialize windows for each size category
        all_windows = {'small': [], 'medium': [], 'large': []}

        # Shuffle tiles for random placement
        random.shuffle(tiles)

        # For each tile, try to place the 9-window structure
        used_tiles = 0
        for tile_idx, tile in enumerate(tiles):
            if used_tiles >= optimal_count:
                break

            tech_node = design.tech_node

            # Try to place 9 windows in this tile using the new structure
            window_id_base = len(all_windows['small']) + len(all_windows['medium']) + len(all_windows['large'])
            placed_windows = self._place_nine_windows_in_tile(tile, tech_node, window_id_base)

            if placed_windows:
                # Add windows to respective categories
                for window in placed_windows:
                    all_windows[window['size_category']].append(window)
                used_tiles += 1

        return all_windows


    def create_directory_structure(self, designs: List[DesignInfo]):
        """Create the datasets directory structure for discovered designs"""

        # Get unique tech nodes from discovered designs
        tech_nodes = set(design.tech_node for design in designs)

        for tech_node in tech_nodes:
            tech_path = self.base_path / tech_node
            for size_category in ['small', 'medium', 'large']:
                size_path = tech_path / size_category
                size_path.mkdir(parents=True, exist_ok=True)

    def generate_yaml_files(self, designs_with_windows: List[Tuple[DesignInfo, Dict[str, List[Dict]]]]):
        """Generate YAML files for each size category"""

        # Group designs by tech node
        tech_nodes = {}
        for design, windows_by_size in designs_with_windows:
            if design.tech_node not in tech_nodes:
                tech_nodes[design.tech_node] = []
            tech_nodes[design.tech_node].append((design, windows_by_size))

        # Generate files for each tech node and size category
        for tech_node, tech_designs in tech_nodes.items():
            for size_category in self.size_categories:
                new_entries = []

                for design, windows_by_size in tech_designs:
                    windows = windows_by_size.get(size_category, [])
                    if not windows:
                        continue
                    entry = {
                        'name': design.full_name,
                        'gds': self._relative_to_repo(design.gds_file),
                        'def': self._relative_to_repo(design.def_file),
                        'stack': design.stack_file,
                        'tech_node': design.tech_node,
                        'windows': windows,
                    }
                    if design.layermap_file:
                        entry['layermap'] = design.layermap_file
                    new_entries.append(entry)

                if not new_entries:
                    continue

                existing_map = self.existing_windows.get(tech_node, {}).get(size_category, {})
                ordered_entries = self._merge_preserving_order(existing_map, new_entries)
                total_windows = sum(len(entry['windows']) for entry in ordered_entries)

                output_file = self.base_path / tech_node / size_category / "windows.yaml"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                windows_per_design = len(ordered_entries[0]['windows']) if ordered_entries else 0

                with open(output_file, 'w') as f:
                    f.write(f"generated_by: generate_windows.py\n")
                    f.write(f"seed: {self.seed}\n")
                    f.write(f"windows_per_design: {windows_per_design}\n")
                    f.write(f"size_category: {size_category}\n")
                    f.write(f"total_designs: {len(ordered_entries)}\n")
                    f.write(f"total_windows: {total_windows}\n")
                    f.write("designs:\n")
                    for design_entry in ordered_entries:
                        f.write(f"  - name: {design_entry['name']}\n")
                        f.write(f"    gds: {design_entry['gds']}\n")
                        f.write(f"    def: {design_entry['def']}\n")
                        f.write(f"    stack: {design_entry['stack']}\n")
                        f.write(f"    tech_node: {design_entry['tech_node']}\n")
                        if 'layermap' in design_entry:
                            f.write(f"    layermap: {design_entry['layermap']}\n")
                        f.write("    windows:\n")
                        for window in design_entry['windows']:
                            f.write(f"      - name: {window['name']}\n")
                            f.write(f"        size_category: {window['size_category']}\n")
                            f.write(f"        x1: {window['x1']}\n")
                            f.write(f"        y1: {window['y1']}\n")
                            f.write(f"        x2: {window['x2']}\n")
                            f.write(f"        y2: {window['y2']}\n")
                            f.write(f"        width: {window['width']}\n")
                            f.write(f"        height: {window['height']}\n")

    def _relative_to_repo(self, file_path: str) -> str:
        """Convert absolute file paths to repo-relative strings for metadata."""
        path_obj = Path(file_path)
        if not path_obj.is_absolute():
            return str(path_obj)

        try:
            return str(path_obj.relative_to(self.repo_root))
        except ValueError:
            # Fall back to absolute path if it's outside the repository
            return str(path_obj)

    @staticmethod
    def _calculate_area(bounds: Optional[Tuple[float, float, float, float]]) -> Optional[float]:
        """Return the area for the provided bounds tuple."""
        if not bounds:
            return None
        x1, y1, x2, y2 = bounds
        area = (x2 - x1) * (y2 - y1)
        return area if area > 0 else None

    def _calculate_design_area(self, design: DesignInfo) -> Optional[float]:
        """Determine the total design area (prefers full DIEAREA when available)."""
        return self._calculate_area(design.total_bounds or design.bounds)

    def _calculate_total_window_area(self, windows_by_size: Dict[str, List[Dict]]) -> float:
        """Sum the area of all windows across size categories."""
        total_area = 0.0
        for windows in windows_by_size.values():
            for window in windows:
                width = window.get('width')
                height = window.get('height')
                if width is None or height is None:
                    x1 = window.get('x1', 0)
                    x2 = window.get('x2', 0)
                    y1 = window.get('y1', 0)
                    y2 = window.get('y2', 0)
                    width = x2 - x1
                    height = y2 - y1
                total_area += max(0.0, float(width)) * max(0.0, float(height))
        return total_area

    @staticmethod
    def _calculate_coverage_percent(window_area: float, design_area: Optional[float]) -> Optional[float]:
        """Compute the percentage of design area covered by windows."""
        if not design_area or design_area <= 0:
            return None
        return (window_area / design_area) * 100.0

    def _get_original_design_bounds(self, design: DesignInfo) -> Optional[Tuple[float, float, float, float]]:
        """Get original design bounds without margin for visualization"""
        if design.total_bounds:
            return design.total_bounds

        try:
            with open(design.def_file, 'r') as f:
                content = f.read()

            # Extract units from DEF file
            units_match = re.search(r'UNITS\s+DISTANCE\s+MICRONS\s+(\d+)', content)
            units_per_micron = int(units_match.group(1)) if units_match else 1000

            # Look for DIEAREA statement
            diearea_match = re.search(r'DIEAREA\s*\(\s*([\d.-]+)\s+([\d.-]+)\s*\)\s*\(\s*([\d.-]+)\s+([\d.-]+)\s*\)', content)

            if diearea_match:
                x1, y1, x2, y2 = map(float, diearea_match.groups())
                # Convert from DEF units to micrometers
                x1, y1, x2, y2 = x1/units_per_micron, y1/units_per_micron, x2/units_per_micron, y2/units_per_micron
                design.total_bounds = (x1, y1, x2, y2)
                return design.total_bounds

        except Exception:
            pass

        return None

    def _generate_visualization(self, design: DesignInfo, windows_by_size: Dict[str, List[Dict]]):
        """Generate visualization showing both total and usable areas"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
        except ImportError:
            return

        try:
            fig, ax = plt.subplots(1, 1, figsize=(14, 10))

            # Get original design bounds (without margin)
            original_bounds = self._get_original_design_bounds(design)
            usable_bounds = design.bounds

            # Plot total design area (original bounds)
            if original_bounds:
                ox1, oy1, ox2, oy2 = original_bounds
                total_rect = patches.Rectangle((ox1, oy1), ox2-ox1, oy2-oy1,
                                              linewidth=2, edgecolor='black',
                                              facecolor='lightgray', alpha=0.2,
                                              label='Total Design Area')
                ax.add_patch(total_rect)

            # Plot usable area (with 10% margin)
            if usable_bounds and original_bounds:
                ux1, uy1, ux2, uy2 = usable_bounds
                usable_rect = patches.Rectangle((ux1, uy1), ux2-ux1, uy2-uy1,
                                               linewidth=2, edgecolor='darkgray',
                                               facecolor='lightblue', alpha=0.2,
                                               label='Usable Area (10% margin)')
                ax.add_patch(usable_rect)

            # Plot windows for each size category
            colors = {'small': 'red', 'medium': 'green', 'large': 'blue'}

            for size_category, windows in windows_by_size.items():
                for window in windows:
                    rect = patches.Rectangle(
                        (window['x1'], window['y1']),
                        window['width'],
                        window['height'],
                        linewidth=1,
                        edgecolor=colors[size_category],
                        facecolor=colors[size_category],
                        alpha=0.6
                    )
                    ax.add_patch(rect)

            # Set plot properties
            ax.set_xlabel('X (μm)', fontsize=12)
            ax.set_ylabel('Y (μm)', fontsize=12)
            ax.set_title(f'{design.full_name} - Window Placement Visualization\n' +
                        f'Red: Small, Green: Medium, Blue: Large', fontsize=14)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)

            # Set axis limits to total design bounds
            if original_bounds:
                margin = (ox2 - ox1) * 0.02  # 2% margin for visualization
                ax.set_xlim(ox1 - margin, ox2 + margin)
                ax.set_ylim(oy1 - margin, oy2 + margin)

            # Add legend
            legend_elements = []
            if original_bounds:
                legend_elements.append(patches.Patch(color='lightgray', alpha=0.2,
                                                  label='Total Design Area'))
            if usable_bounds:
                legend_elements.append(patches.Patch(color='lightblue', alpha=0.2,
                                                  label='Usable Area (10% margin)'))

            for size_category, windows in windows_by_size.items():
                if windows:
                    count = len(windows)
                    legend_elements.append(
                        patches.Patch(color=colors[size_category], alpha=0.6,
                                     label=f'{size_category.title()} ({count} windows)')
                    )

            ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

            # Save as PNG
            png_file = self.base_path / "_plots" / f"{design.full_name}_windows.png"
            png_file.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(png_file, dpi=150, bbox_inches='tight')
            plt.close()

        except Exception:
            pass  # Silently skip visualization errors

    def _calculate_optimal_grid_size(self, design: DesignInfo) -> Tuple[int, int]:
        """Calculate optimal grid size and window count for 9-window structure"""
        if not design.bounds:
            return 10, self.windows_per_design  # Fallback to 10×10 grid

        x1, y1, x2, y2 = design.bounds
        design_width = x2 - x1
        design_height = y2 - y1
        tech_node = design.tech_node

        margin = 0.25

        # Get window dimensions
        medium_width, medium_height = self.window_sizes['medium'][tech_node]
        large_width, large_height = self.window_sizes['large'][tech_node]

        # Calculate required space for 9-window structure
        # Large center + 4 medium around + 4 small in bottom-right cluster
        structure_width = (large_width + medium_width) * (1 + margin)
        structure_height = (large_height + medium_height) * (1 + margin)

        # Add some spacing buffer (10% around structure)
        buffer_factor = 1.1
        required_width = structure_width * buffer_factor
        required_height = structure_height * buffer_factor

        # Calculate maximum tiles that can fit
        max_cols = int(design_width / required_width)
        max_rows = int(design_height / required_height)
        max_tiles = max_cols * max_rows
        # Find largest perfect square <= max_tiles and >= min_tiles
        min_tiles = 9  # Minimum 3x3 grid for 9-window structure
        max_square_root = int(math.sqrt(max_tiles))
        min_square_root = int(math.sqrt(min_tiles))
        if max_square_root < min_square_root:
            grid_size = min_square_root
        else:
            grid_size = max_square_root
        optimal_tiles = grid_size ** 2

        return grid_size, optimal_tiles

    def _place_nine_windows_in_tile(self, tile: Tuple[float, float, float, float],
                                  tech_node: str, window_id_base: int) -> List[Dict]:
        """Place 9 windows using connected touching layout within tile"""
        tile_x1, tile_y1, tile_x2, tile_y2 = tile
        tile_width = tile_x2 - tile_x1
        tile_height = tile_y2 - tile_y1

        # Get window dimensions
        small_width, small_height = self.window_sizes['small'][tech_node]
        medium_width, medium_height = self.window_sizes['medium'][tech_node]
        large_width, large_height = self.window_sizes['large'][tech_node]

        windows = []

        # Calculate total required space for the touching structure
        total_width = large_width + medium_width
        total_height = large_height + medium_height

        # Check if tile can accommodate the structure
        if tile_width >= total_width + 1.0 and tile_height >= total_height + 1.0:
            # Calculate available space for random positioning
            available_width = tile_width - total_width
            available_height = tile_height - total_height

            # Random positioning within the tile (with minimum 0.5μm margin from edges)
            min_margin = 0.5
            random_x_offset = random.uniform(min_margin, max(min_margin, available_width - min_margin))
            random_y_offset = random.uniform(min_margin, max(min_margin, available_height - min_margin))

            # Position the structure randomly within the tile
            base_x = tile_x1 + random_x_offset
            base_y = tile_y1 + random_y_offset

            # Large window (center-left of structure)
            large_x = base_x
            large_y = base_y
            windows.append({
                'name': f'W{window_id_base}',
                'size_category': 'large',
                'x1': round(large_x, 3),
                'y1': round(large_y, 3),
                'x2': round(large_x + large_width, 3),
                'y2': round(large_y + large_height, 3),
                'width': round(large_width, 3),
                'height': round(large_height, 3),
            })

            # Medium window 1: touching large on the right (same vertical position)
            medium1_x = large_x + large_width
            medium1_y = large_y
            windows.append({
                'name': f'W{window_id_base + 1}',
                'size_category': 'medium',
                'x1': round(medium1_x, 3),
                'y1': round(medium1_y, 3),
                'x2': round(medium1_x + medium_width, 3),
                'y2': round(medium1_y + medium_height, 3),
                'width': round(medium_width, 3),
                'height': round(medium_height, 3),
            })

            # Medium window 2: touching large at the bottom
            medium2_x = large_x + large_width
            medium2_y = large_y - medium_height
            windows.append({
                'name': f'W{window_id_base + 2}',
                'size_category': 'medium',
                'x1': round(medium2_x, 3),
                'y1': round(medium2_y, 3),
                'x2': round(medium2_x + medium_width, 3),
                'y2': round(medium2_y + medium_height, 3),
                'width': round(medium_width, 3),
                'height': round(medium_height, 3),
            })

            # Medium window 3: touching large on the top left
            medium3_x = large_x + medium_width
            medium3_y = large_y - medium_height
            windows.append({
                'name': f'W{window_id_base + 3}',
                'size_category': 'medium',
                'x1': round(medium3_x, 3),
                'y1': round(medium3_y, 3),
                'x2': round(medium3_x + medium_width, 3),
                'y2': round(medium3_y + medium_height, 3),
                'width': round(medium_width, 3),
                'height': round(medium_height, 3),
            })

            # Medium window 4: touching large at the top
            medium4_x = large_x
            medium4_y = large_y - medium_height
            windows.append({
                'name': f'W{window_id_base + 4}',
                'size_category': 'medium',
                'x1': round(medium4_x, 3),
                'y1': round(medium4_y, 3),
                'x2': round(medium4_x + medium_width, 3),
                'y2': round(medium4_y + medium_height, 3),
                'width': round(medium_width, 3),
                'height': round(medium_height, 3),
            })

            # Small windows: 2×2 cluster touching medium1 and medium2 at top-left corner
            # Position the cluster so its top-left corner touches the touching point
            small_cluster_x = large_x + large_width
            small_cluster_y = large_y + medium_height

            # 4 small windows in 2×2 arrangement
            small_positions = [
                (0, 0),                    # bottom-left
                (small_width, 0),          # bottom-right
                (0, small_height),         # top-left
                (small_width, small_height) # top-right
            ]

            for i, (dx, dy) in enumerate(small_positions):
                windows.append({
                    'name': f'W{window_id_base + 5 + i}',
                    'size_category': 'small',
                    'x1': round(small_cluster_x + dx, 3),
                    'y1': round(small_cluster_y + dy, 3),
                    'x2': round(small_cluster_x + dx + small_width, 3),
                    'y2': round(small_cluster_y + dy + small_height, 3),
                    'width': round(small_width, 3),
                    'height': round(small_height, 3),
                })

        return windows

    def run(self) -> bool:
        """Main execution function"""
        # Discover designs
        self.existing_windows = self._load_existing_windows()
        designs = self.discover_designs()
        if not designs:
            return False

        print(f"[*] Processing {len(designs)} designs...")

        # Pre-calculate optimal window counts for all designs
        design_counts = {}
        for design in designs:
            design.bounds, design.total_bounds = self.parse_def_bounds(design.def_file)
            if design.bounds:
                grid_size, optimal_count = self._calculate_optimal_grid_size(design)
                design_counts[design.full_name] = optimal_count
                print(f"   {design.full_name}: {optimal_count} tiles ({grid_size}×{grid_size} grid)")
            else:
                design_counts[design.full_name] = 0

        # Create directory structure
        self.create_directory_structure(designs)

        # Generate windows for each design
        designs_with_windows = []
        summary_rows: List[Dict[str, object]] = []

        for design in designs:
            is_existing = self._design_has_existing_windows(design)
            if is_existing:
                windows_by_size = self._get_existing_windows(design)
            else:
                windows_by_size = self.generate_windows_for_design(design)
                if windows_by_size:
                    designs_with_windows.append((design, windows_by_size))
                    self._generate_visualization(design, windows_by_size)

            if windows_by_size:
                small_count = len(windows_by_size['small'])
                medium_count = len(windows_by_size['medium'])
                large_count = len(windows_by_size['large'])
                total_tiles = len(set(w['name'] for w in windows_by_size['small'] +
                                    windows_by_size['medium'] + windows_by_size['large']))
            else:
                small_count = medium_count = large_count = 0
                total_tiles = 0

            window_area = self._calculate_total_window_area(windows_by_size) if windows_by_size else 0.0
            design_area = self._calculate_design_area(design)
            coverage_pct = self._calculate_coverage_percent(window_area, design_area)

            summary_rows.append({
                "design": design.full_name,
                "tech": design.tech_node,
                "tiles": total_tiles,
                "small": small_count,
                "medium": medium_count,
                "large": large_count,
                "is_generated": not is_existing,
                "coverage_pct": coverage_pct,
                "window_area": window_area,
                "design_area": design_area,
            })

        self._print_summary_table(summary_rows)

        print(f"\n[*] Generated YAML files for {len(designs_with_windows)} designs")

        # Generate YAML files
        self.generate_yaml_files(designs_with_windows)

        return True

    def _load_existing_windows(self) -> Dict[str, Dict[str, Dict[str, Dict]]]:
        existing: Dict[str, Dict[str, Dict[str, Dict]]] = {}
        for tech_dir in self.base_path.iterdir():
            if not tech_dir.is_dir():
                continue
            tech_node = tech_dir.name
            for size_category in self.size_categories:
                yaml_path = tech_dir / size_category / "windows.yaml"
                if not yaml_path.exists():
                    continue
                try:
                    yaml_module = _require_yaml_module()
                    with yaml_path.open() as fh:
                        data = yaml_module.safe_load(fh) or {}
                except Exception:
                    continue
                for design_entry in data.get('designs', []):
                    design_name = design_entry.get('name')
                    if not design_name:
                        continue
                    existing.setdefault(tech_node, {}).setdefault(size_category, {})[design_name] = design_entry
        return existing

    def _design_has_existing_windows(self, design: DesignInfo) -> bool:
        existing_for_design = self.existing_windows.get(design.tech_node, {})
        return any(
            design.full_name in existing_for_design.get(size, {})
            for size in self.size_categories
        )

    def _get_existing_windows(self, design: DesignInfo) -> Dict[str, List[Dict]]:
        existing_for_design = self.existing_windows.get(design.tech_node, {})
        reused = {}
        for size in self.size_categories:
            entry = existing_for_design.get(size, {}).get(design.full_name)
            if entry:
                reused[size] = [dict(window) for window in entry.get('windows', [])]
            else:
                reused[size] = []
        return reused

    @staticmethod
    def _merge_preserving_order(existing_map: Dict[str, Dict], new_entries: List[Dict]) -> List[Dict]:
        combined = list(existing_map.values()) + new_entries
        seen = set()
        ordered_entries = []
        for entry in combined:
            name = entry['name']
            if name in seen:
                continue
            seen.add(name)
            ordered_entries.append(entry)
        return ordered_entries

    def _print_summary_table(self, rows: List[Dict[str, object]]) -> None:
        if not rows:
            return

        def fmt_pct(value: Optional[float]) -> str:
            if value is None:
                return "-"
            return f"{value:.2f}%"

        total_tiles_generated = sum(row["tiles"] for row in rows if row["is_generated"])
        rows_with_area = [row for row in rows if row.get("design_area")]
        total_window_area = sum((row.get("window_area") or 0.0) for row in rows_with_area)
        total_design_area = sum((row.get("design_area") or 0.0) for row in rows_with_area)
        totals = {
            "tiles": sum(row["tiles"] for row in rows),
            "small": sum(row["small"] for row in rows),
            "medium": sum(row["medium"] for row in rows),
            "large": sum(row["large"] for row in rows),
            "generated_tiles": total_tiles_generated,
            "coverage_pct": self._calculate_coverage_percent(total_window_area, total_design_area),
            "window_area": total_window_area,
            "design_area": total_design_area,
        }
        rows = rows + [{
            "design": "TOTAL",
            "tech": "",
            "tiles": totals["tiles"],
            "small": totals["small"],
            "medium": totals["medium"],
            "large": totals["large"],
            "is_generated": None,
            "coverage_pct": totals["coverage_pct"],
            "window_area": total_window_area,
            "design_area": total_design_area,
        }]

        def gen_label(row: Dict[str, object]) -> str:
            flag = row.get("is_generated")
            if flag is True:
                return "yes"
            if flag is False:
                return "no"
            return f"{totals['generated_tiles']}"

        design_width = max(len("Design"), max(len(str(row["design"])) for row in rows))
        tech_width = max(len("Tech Node"), max(len(str(row["tech"])) for row in rows))
        tiles_width = max(len("Tiles"), max(len(str(row["tiles"])) for row in rows))
        gen_width = max(len("Generated"), max(len(gen_label(row)) for row in rows))
        small_width = max(len("Small"), max(len(str(row["small"])) for row in rows))
        medium_width = max(len("Medium"), max(len(str(row["medium"])) for row in rows))
        large_width = max(len("Large"), max(len(str(row["large"])) for row in rows))
        coverage_width = max(len("Coverage %"), max(len(fmt_pct(row.get("coverage_pct"))) for row in rows))

        header = (
            f"| {'Design':<{design_width}} | {'Tech Node':<{tech_width}} | "
            f"{'Tiles':>{tiles_width}} | {'Coverage %':>{coverage_width}} | {'Generated':<{gen_width}} | "
            f"{'Small':>{small_width}} | {'Medium':>{medium_width}} | {'Large':>{large_width}} |"
        )
        separator = (
            f"|:{'-'*design_width}-|:{'-'*tech_width}-|"
            f"{'-'*tiles_width}:|{'-'*coverage_width}:|{'-'*gen_width}-|"
            f"{'-'*small_width}:|{'-'*medium_width}:|{'-'*large_width}:|"
        )
        print(header)
        print(separator)

        for row in rows:
            gen_str = gen_label(row)
            coverage_str = fmt_pct(row.get("coverage_pct"))
            print(
                f"| {row['design']:<{design_width}} | {row['tech']:<{tech_width}} | "
                f"{row['tiles']:>{tiles_width}} | {coverage_str:>{coverage_width}} | {gen_str:<{gen_width}} | "
                f"{row['small']:>{small_width}} | {row['medium']:>{medium_width}} | {row['large']:>{large_width}} |"
            )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Enhanced window generation with grid-based non-overlapping placement',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m tools.maintenance.window_metadata
    python -m tools.maintenance.window_metadata --windows-per-design 50
    python -m tools.maintenance.window_metadata --seed 123
    python -m tools.maintenance.window_metadata --output /custom/path
        """
    )

    parser.add_argument(
        '--windows-per-design',
        type=int,
        default=100,
        help='Number of windows to generate per size category per design (default: 100)'
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducible results (default: 42)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output directory path (default: datasets)'
    )

    parser.add_argument(
        '--designs-root',
        type=str,
        help='Directory containing gds/ and def/ source design trees (default: ./designs)'
    )

    args = parser.parse_args(argv)

    # Create generator and run
    generator = MultiSizeWindowGenerator(
        windows_per_design=args.windows_per_design,
        seed=args.seed,
        output_path=args.output,
        designs_root=args.designs_root,
    )

    success = generator.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
CAP3D Cross-Section Sampler (self-contained)

Generates random cross-sections directly from a CAP3D file and saves them in an
NPZ file with the same structure used by gds-cross-section. Also plots 10
sample cases for quick visual inspection.

Key behaviors mirrored from gds-cross-section:
- Uses a sliding window of configurable width along the cut direction
- Picks a "center" (master) conductor and centers the window on it
- Keeps the master conductor at the geometric center of the window and as the
  first entry in the NPZ conductor list
- Excludes non-center conductors that touch window edges
- Window height is determined by including a configurable number of conductor
  layers above and below the center layer

Inputs: only a CAP3D file (no ITF or layer mapping required). Layer heights are
inferred from conductor block Z extents in the CAP3D content.

Usage:
  python window_tools/cap3d_cross_section.py <cap3d_file> [num_samples] [window_width]

Defaults:
  - num_samples = 100
  - window_width = 5.0 (same unit as CAP3D coordinates, typically microns)

Outputs:
  - NPZ at cap3d/cross_section_outputs/cross_sections.npz containing list of sample dicts
  - 10 plotted PNGs in cap3d/cross_section_outputs/cross_section_*.png
"""

from __future__ import annotations

import os
import sys
import random
import math
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

from window_tools.cap3d_parser import StreamingCap3DParser


# ------------------------------ Sampler Logic --------------------------------

def _merge_segments(segments: List[Tuple[float, float]], eps: float = 1e-6) -> List[Tuple[float, float]]:
    """Merge overlapping or nearly-adjacent segments with numeric tolerance.

    eps is an absolute tolerance in the same units as segment coordinates (μm).
    """
    if not segments:
        return []
    segments = sorted(segments)
    merged = [segments[0]]
    for cur in segments[1:]:
        last = merged[-1]
        if cur[0] <= last[1] + eps:  # overlap or within tolerance
            merged[-1] = (last[0], max(last[1], cur[1]))
        else:
            merged.append(cur)
    return merged


def _block_ranges(block) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
    x0 = float(block.base[0]); x1 = x0 + float(block.v1[0])
    y0 = float(block.base[1]); y1 = y0 + float(block.v2[1])
    z0 = float(block.base[2]); z1 = z0 + float(block.hvec[2])
    return (min(x0, x1), max(x0, x1)), (min(y0, y1), max(y0, y1)), (min(z0, z1), max(z0, z1))


def _parse_layer_id_map(file_path: str) -> Tuple[Dict[int, str], Dict[int, str]]:
    """Parse <layer> sections to build id->name and id->type maps."""
    id_to_name: Dict[int, str] = {}
    id_to_type: Dict[int, str] = {}
    in_layer = False
    cur_name = None
    cur_type = None
    cur_id = None
    with open(file_path, 'r', encoding='utf-8', buffering=8192) as f:
        for raw in f:
            s = raw.strip()
            if not s or s.startswith('<!--'):
                continue
            if s.startswith('<layer>'):
                in_layer = True
                cur_name = None; cur_type = None; cur_id = None
                continue
            if s.startswith('</layer>'):
                if in_layer and cur_id is not None and cur_name is not None and cur_type is not None:
                    id_to_name[cur_id] = cur_name
                    id_to_type[cur_id] = cur_type
                in_layer = False
                continue
            if not in_layer:
                continue
            if s.startswith('name '):
                cur_name = s[5:].strip()
            elif s.startswith('type '):
                cur_type = s[5:].strip()
            elif s.startswith('id '):
                try:
                    cur_id = int(float(s[3:].strip()))
                except Exception:
                    cur_id = None
    return id_to_name, id_to_type


class Cap3dCrossSectionSampler:
    def __init__(self, cap3d_file: str, layermap_file: str = None, tech_file: str = None):
        self.cap3d_file = cap3d_file
        self.layermap_file = layermap_file
        self.tech_file = tech_file

        # Load minimum width data if tech file is provided
        self.min_widths = {}
        if tech_file:
            try:
                from common.tech_parser import get_layer_min_widths
                self.min_widths = get_layer_min_widths(tech_file)
            except Exception as e:
                print(f"Warning: Could not load minimum widths from {tech_file}: {e}")
                self.min_widths = {}

        # Parse with shared StreamingCap3DParser
        parsed = StreamingCap3DParser(cap3d_file, use_fast=False).parse_complete()
        self._all_blocks = [b for b in parsed.blocks if getattr(b, 'type', '') == 'conductor' and getattr(b, 'layer', None) is not None]
        if not self._all_blocks:
            raise RuntimeError('No conductor blocks found in CAP3D file.')

        # Build layer id -> name/type map from file
        id_to_name, id_to_type = _parse_layer_id_map(cap3d_file)
        self.layer_names: Dict[int, str] = id_to_name
        self.layer_types: Dict[int, str] = id_to_type

        # Keep only interconnect blocks
        self.blocks = [b for b in self._all_blocks if self.layer_types.get(int(getattr(b, 'layer')), '').lower() == 'interconnect']
        if not self.blocks:
            raise RuntimeError('No interconnect conductor blocks available.')

        # Bounds: prefer window if present
        if parsed.window is not None:
            wx1 = float(min(parsed.window.v1[0], parsed.window.v2[0])); wy1 = float(min(parsed.window.v1[1], parsed.window.v2[1]))
            wx2 = float(max(parsed.window.v1[0], parsed.window.v2[0])); wy2 = float(max(parsed.window.v1[1], parsed.window.v2[1]))
            self.xmin, self.xmax = wx1, wx2
            self.ymin, self.ymax = wy1, wy2
        else:
            xs: List[float] = []
            ys: List[float] = []
            for b in self.blocks:
                xr, yr, _ = _block_ranges(b)
                xs.extend(xr); ys.extend(yr)
            self.xmin, self.xmax = float(min(xs)), float(max(xs))
            self.ymin, self.ymax = float(min(ys)), float(max(ys))

        # Per-layer Z extents from blocks
        layer_z: Dict[int, Tuple[float, float]] = {}
        for b in self.blocks:
            _, _, zr = _block_ranges(b)
            lid = int(getattr(b, 'layer'))
            if lid not in layer_z:
                layer_z[lid] = zr
            else:
                lo, hi = layer_z[lid]
                layer_z[lid] = (min(lo, zr[0]), max(hi, zr[1]))
        self.layer_z = layer_z
        self.ordered_layers: List[int] = sorted(layer_z.keys(), key=lambda lid: (layer_z[lid][0] + layer_z[lid][1]) * 0.5)

    def _segments_at_cut(self, cut_coord: float, axis: str) -> Dict[int, List[Tuple[float, float]]]:
        """Collect merged segments per layer (by layer_id) at a vertical/horizontal cut."""
        per_layer: Dict[int, List[Tuple[float, float]]] = {}

        for b in self.blocks:
            xr, yr, _ = _block_ranges(b)
            if axis == 'x':
                if cut_coord < xr[0] or cut_coord > xr[1]:
                    continue
                seg = yr  # segment runs along Y when cutting at fixed X
            else:
                if cut_coord < yr[0] or cut_coord > yr[1]:
                    continue
                seg = xr  # segment runs along X when cutting at fixed Y

            per_layer.setdefault(int(getattr(b, 'layer')), []).append(seg)

        # Merge per layer with tolerance to collapse tiny gaps from numeric noise
        for lid in list(per_layer.keys()):
            per_layer[lid] = _merge_segments(per_layer[lid], eps=1e-6)
        return per_layer

    def _z_window_for_layer(self, center_layer_id: int, layers_above: int, layers_below: int) -> Tuple[float, float, List[int]]:
        # Identify center in ordered layers
        try:
            idx = self.ordered_layers.index(center_layer_id)
        except ValueError:
            raise RuntimeError('Center layer not found in ordered layer set.')

        lo_idx = max(0, idx - layers_below)
        hi_idx = min(len(self.ordered_layers) - 1, idx + layers_above)
        chosen = self.ordered_layers[lo_idx:hi_idx + 1]

        zmins = [self.layer_z[lid][0] for lid in chosen]
        zmaxs = [self.layer_z[lid][1] for lid in chosen]
        return float(min(zmins)), float(max(zmaxs)), chosen

    def generate_sample(self, window_width: float = 5.0, layers_above: int = 2, layers_below: int = 2) -> Optional[Dict]:
        """Generate a sample ensuring at least two conductors are inside the window.

        Tries multiple center conductors per plane; if no valid selection is found,
        changes the cut coordinate (and axis as needed) and retries.
        """
        # Initial axis
        axis = random.choice(['x', 'y'])

        # Up to 6 plane attempts: 3 with initial axis (new coords), then flip axis for 3 more
        for plane_attempt in range(6):
            if plane_attempt == 3:
                axis = 'y' if axis == 'x' else 'x'

            # Pick a new cut coordinate for this plane attempt
            if axis == 'x':
                cut_coord = random.uniform(self.xmin, self.xmax)
            else:
                cut_coord = random.uniform(self.ymin, self.ymax)

            # Collect segments grouped by layer (interconnect only)
            layer_segments = self._segments_at_cut(cut_coord, axis)
            if not layer_segments:
                continue
            # Collect candidate segments per layer, filtering by width.
            per_layer_candidates: Dict[int, List[Tuple[float, float]]] = {}
            for lid, segs in layer_segments.items():
                filtered: List[Tuple[float, float]] = []
                for s in segs:
                    width = s[1] - s[0]
                    # Get layer-specific minimum width if available
                    layer_name = self.layer_names.get(lid)
                    min_width = 0.005  # Conservative default
                    if layer_name and layer_name in self.min_widths:
                        min_width = self.min_widths[layer_name]

                    # Filter out segments below minimum width and excessively wide ones
                    if width < min_width or width > window_width * 100:
                        continue
                    filtered.append(s)
                if filtered:
                    per_layer_candidates[lid] = filtered
            if not per_layer_candidates:
                continue

            candidate_layer_ids = list(per_layer_candidates.keys())
            random.shuffle(candidate_layer_ids)

            # Try each candidate layer (random order) and shuffle segments inside that layer.
            for center_layer_id in candidate_layer_ids:
                candidate_segs = per_layer_candidates[center_layer_id]
                random.shuffle(candidate_segs)
                for seg in candidate_segs:
                    seg_center = 0.5 * (seg[0] + seg[1])
                    # Define window limits along the cut direction
                    wmin = seg_center - 0.5 * window_width
                    wmax = seg_center + 0.5 * window_width

                    # Define window height from layers above/below
                    try:
                        _, _, included_layer_ids = self._z_window_for_layer(center_layer_id, layers_above, layers_below)
                    except RuntimeError:
                        continue

                    center_conductor = None
                    others: List[Tuple[np.ndarray, str]] = []  # ((x,y,w,h), layer_name)

                    # Build conductor rectangles inside window
                    for lid, segs in layer_segments.items():
                        # Skip layers outside z-range
                        if lid not in included_layer_ids:
                            continue
                        z0, z1 = self.layer_z[lid]
                        layer_center_y = 0.5 * (z0 + z1)
                        layer_height = (z1 - z0)

                        for s0, s1 in segs:
                            is_center_seg = (lid == center_layer_id) and (abs(s0 - seg[0]) < 1e-9) and (abs(s1 - seg[1]) < 1e-9)

                            # Edge and range checks for non-center conductors
                            if not is_center_seg:
                                if s0 <= wmin or s1 >= wmax:
                                    continue
                                if s1 <= wmin or s0 >= wmax:
                                    continue

                            s_center = 0.5 * (s0 + s1)
                            s_width = (s1 - s0)
                            rel_x = s_center - seg_center  # horizontal coordinate relative to master conductor center
                            rect = np.array([rel_x, layer_center_y, s_width, layer_height], dtype=np.float32)

                            lname = self.layer_names.get(lid, f"layer_{lid}")
                            if is_center_seg:
                                center_conductor = (rect, lname)
                            else:
                                others.append((rect, lname))

                    # Require at least a center conductor
                    if center_conductor is None:
                        continue

                    # Order with center first
                    rects = [center_conductor[0]] + [r for r, _ in others]
                    names = [center_conductor[1]] + [n for _, n in others]

                    return {
                        'axis': axis,
                        'cut_coord': float(cut_coord),
                        'conductor_coords': np.asarray(rects),  # (N,4) [x,y,width,height]
                        'conductor_layers': np.asarray(names, dtype=object),
                        'center_conductor_layer': self.layer_names.get(center_layer_id, str(center_layer_id))
                    }

        # Failed across multiple planes/axes
        return None

    def generate_dataset(self, num_samples: int, window_width: float = 5.0, layers_above: int = 2, layers_below: int = 2,
                         output_file: str | None = None, hist_file: str | None = None,
                         top_k: Optional[int] = None) -> List[Dict]:
        if output_file is None:
            base_dir = os.path.join(os.path.dirname(__file__), 'cross_section_outputs')
            output_file = os.path.join(base_dir, 'cross_sections.npz')
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        samples: List[Dict] = []
        success = 0
        attempts = 0
        if top_k is not None:
            print(f"Generating {num_samples} candidates; selecting top-{top_k} by conductor count...")
        else:
            print(f"Generating {num_samples} cross-section samples from CAP3D...")
        progress = tqdm(total=num_samples, desc='Sampling', unit='sample', leave=False) if num_samples > 0 else None
        while success < num_samples:
            attempts += 1
            s = self.generate_sample(window_width=window_width, layers_above=layers_above, layers_below=layers_below)
            if s is not None:
                samples.append(s)
                success += 1
                if progress is not None:
                    progress.update()
        if progress is not None:
            progress.close()

        # If top_k is provided, rank and select; else keep all
        selected = samples
        if top_k is not None and samples:
            with_counts = [dict(s, conductor_count=int(len(s['conductor_coords']))) for s in samples]
            with_counts.sort(key=lambda d: d['conductor_count'], reverse=True)
            selected = with_counts[:top_k]

        np.savez_compressed(output_file, samples=selected)
        if top_k is not None:
            print(f"Saved top {len(selected)} samples to {output_file}")
        else:
            print(f"Saved {len(selected)} samples to {output_file}")

        # Histogram: reuse code path; add top-K average overlay if applicable
        if hist_file is None:
            base_dir = os.path.join(os.path.dirname(__file__), 'cross_section_outputs')
            hist_file = os.path.join(base_dir, 'conductor_count_hist.png')
        try:
            counts = [int(len(s['conductor_coords'])) for s in samples]
            if counts:
                # Create bar chart with discrete conductor count values
                from collections import Counter
                count_freq = Counter(counts)
                conductor_vals = sorted(count_freq.keys())
                frequencies = [count_freq[c] for c in conductor_vals]

                plt.figure(figsize=(8, 5))
                plt.bar(conductor_vals, frequencies, color='#66B2FF', edgecolor='#003366', width=0.8)
                all_avg = float(np.mean(counts))
                plt.axvline(all_avg, color='black', linestyle='--', linewidth=1.5,
                            label=('Candidates avg' if top_k is not None else 'All samples avg')+f'={all_avg:.2f}')
                if top_k is not None and selected:
                    top_counts = [int(len(s['conductor_coords'])) for s in selected]
                    top_avg = float(np.mean(top_counts)) if top_counts else 0.0
                    plt.axvline(top_avg, color='red', linestyle='-', linewidth=1.5, label=f'Top-{top_k} avg={top_avg:.2f}')
                plt.legend()
                plt.title('Conductor Count per Sample (Candidates)' if top_k is not None else 'Conductor Count per Sample (All)')
                plt.xlabel('Number of conductors in window')
                plt.ylabel('Frequency')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(hist_file, dpi=150)
                plt.close()
                print(f"Saved bar chart to {hist_file}")
                # Console summary
                if top_k is not None and selected:
                    print(f"Average (candidates): {all_avg:.2f}")
                    print(f"Average (top-{top_k}): {top_avg:.2f}")
                else:
                    print(f"Average (all samples): {all_avg:.2f}")
        except Exception as e:
            print(f"Warning: failed to save histogram: {e}")
        return selected


# ------------------------------ Visualization --------------------------------

def visualize_sample(sample_data: dict, sample_idx: int = 0, figsize=(12, 8)):
    fig, ax = plt.subplots(figsize=figsize)

    conductor_coords = sample_data['conductor_coords']
    conductor_layers = sample_data['conductor_layers']
    center_layer = sample_data['center_conductor_layer']

    # Compute bounds from conductor coordinates
    x_lefts = conductor_coords[:, 0] - conductor_coords[:, 2] / 2.0
    x_rights = conductor_coords[:, 0] + conductor_coords[:, 2] / 2.0
    y_bottoms = conductor_coords[:, 1] - conductor_coords[:, 3] / 2.0
    y_tops = conductor_coords[:, 1] + conductor_coords[:, 3] / 2.0

    x_min, x_max = float(x_lefts.min()), float(x_rights.max())
    y_min, y_max = float(y_bottoms.min()), float(y_tops.max())

    x_range = x_max - x_min
    y_range = y_max - y_min

    label_positions: Dict[str, float] = {}
    for i, ((x, y, width, height), layer_name) in enumerate(zip(conductor_coords, conductor_layers)):
        rect_x = float(x) - float(width) / 2.0
        rect_y = float(y) - float(height) / 2.0
        is_center = (i == 0)
        if is_center:
            ax.add_patch(plt.Rectangle(
                (rect_x, rect_y), float(width), float(height),
                linewidth=3, edgecolor='darkred', facecolor='#FF3333', alpha=0.9, zorder=10
            ))
        else:
            ax.add_patch(plt.Rectangle(
                (rect_x, rect_y), float(width), float(height),
                linewidth=2, edgecolor='#0066CC', facecolor='#66B2FF', alpha=0.8, zorder=5
            ))
        if layer_name not in label_positions:
            label_positions[layer_name] = float(y)

    for layer_name, y_pos in label_positions.items():
        is_center_layer = (layer_name == center_layer)
        color = 'darkred' if is_center_layer else '#0066CC'
        weight = 'bold' if is_center_layer else 'normal'
        fontsize = 10 if is_center_layer else 9
        ax.text(x_max + 0.1, y_pos, str(layer_name), fontsize=fontsize,
                ha='left', va='center', color=color, weight=weight)

    # Add padding around the plot
    x_padding = x_range * 0.05 if x_range > 0 else 0.5
    y_padding = y_range * 0.05 if y_range > 0 else 0.5

    ax.set_xlim(x_min - x_padding, x_max + 0.4 + x_padding)
    ax.set_ylim(y_min - y_padding, y_max + y_padding)
    ax.set_aspect('equal')
    ax.set_xlabel('Position relative to master conductor (μm)', fontsize=12)
    ax.set_ylabel('Absolute height (μm)', fontsize=12)
    ax.set_title(f'CAP3D Cross-Section #{sample_idx}\nCut along {sample_data["axis"].upper()} at {sample_data["cut_coord"]:.3f}', fontsize=14)
    ax.grid(True, alpha=0.3)

    return fig, ax


def plot_first_n(samples: List[Dict], n: int, out_dir: Optional[str] = None) -> None:
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(__file__), 'cross_section_outputs')
    os.makedirs(out_dir, exist_ok=True)
    for i in range(min(n, len(samples))):
        fig, ax = visualize_sample(samples[i], i)
        out_file = os.path.join(out_dir, f'cross_section_{i}.png')
        plt.savefig(out_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved visualization to {out_file}")


# ---------------------------------- CLI --------------------------------------

def main(argv: List[str]) -> int:
    if len(argv) < 3:
        print("Usage: python window_tools/cap3d_cross_section.py <cap3d_file> <num_samples> [window_width] [--top <top_k>] [--layermap <layermap_file>] [--tech <tech_file>]")
        print("Examples:")
        print("  python window_tools/cap3d_cross_section.py cap3d/output.cap3d 100 5.0")
        print("  python window_tools/cap3d_cross_section.py cap3d/output.cap3d 100 --top 10")
        print("  python window_tools/cap3d_cross_section.py cap3d/output.cap3d 100 5.0 --layermap designs/tech/asap7.layermap --tech designs/tech/asap7.yaml")
        return 1

    cap3d_file = argv[1]
    try:
        num_samples = int(argv[2])
    except Exception:
        print("Error: <num_samples> must be an integer.")
        return 2

    # Optional window width (positional) before flags
    window_width = 5.0
    if len(argv) > 3 and not argv[3].startswith('--'):
        try:
            window_width = float(argv[3])
            flag_start = 4
        except Exception:
            flag_start = 3
    else:
        flag_start = 3

    # Optional --top <top_k>
    top_k: Optional[int] = None
    layermap_file: Optional[str] = None
    tech_file: Optional[str] = None

    # Parse optional arguments
    i = flag_start
    while i < len(argv):
        if argv[i] == '--top':
            if i + 1 >= len(argv):
                print("Error: --top requires an integer <top_k> value")
                return 2
            try:
                top_k = int(argv[i + 1])
            except Exception:
                print("Error: --top requires an integer <top_k> value")
                return 2
            i += 2
        elif argv[i] == '--layermap':
            if i + 1 >= len(argv):
                print("Error: --layermap requires a file path")
                return 2
            layermap_file = argv[i + 1]
            i += 2
        elif argv[i] == '--tech':
            if i + 1 >= len(argv):
                print("Error: --tech requires a file path")
                return 2
            tech_file = argv[i + 1]
            i += 2
        else:
            print(f"Error: Unknown argument: {argv[i]}")
            return 2

    sampler = Cap3dCrossSectionSampler(cap3d_file, layermap_file=layermap_file, tech_file=tech_file)

    # Generate dataset, optionally selecting top-K within the same pipeline
    results = sampler.generate_dataset(num_samples=num_samples, window_width=window_width, output_file=None,
                                       hist_file=None, top_k=top_k)
    plot_first_n(results, 10, out_dir=None)

    print("Done.")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

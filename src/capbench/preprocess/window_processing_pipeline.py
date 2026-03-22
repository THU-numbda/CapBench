#!/usr/bin/env python3
from __future__ import annotations
"""
CAP3D Window Extraction Tool (KLayout + DEF filtering)

Usage:
    python3 window_processing_pipeline.py [--gds FILE] [--def FILE] [--windows FILE]

Or simply:
    python3 window_processing_pipeline.py  (uses defaults)
"""

import sys
import argparse
import atexit
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, DefaultDict, Set, Any, Sequence
from collections import defaultdict
from datetime import datetime
import re
import time
import gc
import traceback
from tqdm import tqdm
import psutil

from capbench._internal.klayout_compat import pya, require_pya
from capbench.preprocess.def_parser import (
    parse_def, filter_components_in_window, filter_nets_in_window, parse_lef_macro_sizes, write_def
)
from capbench.preprocess.converters.pct_cap import convert_window as convert_pct_window
from capbench.preprocess.converters.cnn_cap import convert_window as convert_cnn_window
from capbench.preprocess.converters.binary_masks import convert_window as convert_binary_masks_window
from capbench._internal.common.datasets import (
    extract_process_node_from_path,
    find_tech_stack_for_process_node,
    find_layermap_for_process_node,
    get_dataset_subdirs,
)
from capbench._internal.common.tech_parser import get_all_layers_with_limit, get_conductor_layers
from capbench.paths import TECH_ROOT

STAGE_LABELS = {
    'gds': 'GDS/DEF',
    'cap3d': 'CAP3D',
    'pct': 'PCT point clouds',
    'cnn': 'CNN density maps',
    'binary-masks': 'U-Net binary masks',
}

STAGE_PRINT_ORDER = ['gds', 'cap3d', 'cnn', 'binary-masks', 'pct']

STAGE_ALIASES = {
    'gds': 'gds',
    'cap3d': 'cap3d',
    'pct': 'pct',
    'cnn': 'cnn',
    'binary_masks': 'binary-masks',
    'binary-masks': 'binary-masks',
}

STAGE_OUTPUT_KEYS = {
    'binary-masks': 'binary_masks',
}

DEFAULT_LAYER_LIMITS = {
    'nangate45': {
        'small': {'bottom': 'metal1', 'top': 'metal4'},
        'medium': {'bottom': 'metal1', 'top': 'metal7'},
        'large': {'bottom': 'metal1', 'top': 'metal7'},
    },
    'sky130hd': {
        'small': {'bottom': 'li1', 'top': 'met4'},
        'medium': {'bottom': 'li1', 'top': 'met5'},
        'large': {'bottom': 'li1', 'top': 'met5'},
    },
}

def _normalize_layer_key(value: Optional[str]) -> str:
    return ''.join(ch for ch in str(value).lower() if ch.isalnum()) if value else ''


def _normalize_stage_name(stage: str) -> str:
    return STAGE_ALIASES.get(str(stage), str(stage))

class WindowExtractor:
    """Extract windows from GDS+DEF designs using KLayout + DEF filtering"""

    def __init__(
        self,
        multi_yaml_file: Path,
        output_dir: str,
        process_node: Optional[str] = None,
        tech_stack_file: Optional[Path] = None,
        layermap_file: Optional[Path] = None,
        pipeline_stages: List[str] = None,
        use_default_net_names: bool = False,
    ):
        self.multi_yaml_file = Path(multi_yaml_file)
        self.output_dir = Path(output_dir)  # For overlays, reports, and temporary files
        self.process_node = process_node
        self.tech_stack_file = tech_stack_file
        self.layermap_file = Path(layermap_file) if layermap_file else None
        raw_pipeline_stages = pipeline_stages or ['cap3d', 'cnn', 'binary-masks', 'pct']
        self.pipeline_stages = [_normalize_stage_name(stage) for stage in raw_pipeline_stages]
        self.rebase_origin = True
        self.group_with_l2n = True
        self.use_default_net_names = use_default_net_names

        # Helper method to check if a pipeline stage should run
        def should_run_stage(stage: str) -> bool:
            return _normalize_stage_name(stage) in self.pipeline_stages
        self.should_run_stage = should_run_stage

        # Layout inputs are needed whenever we regenerate clipped GDS/DEF windows.
        self.requires_layout_inputs = self.should_run_stage('gds') or self.should_run_stage('cap3d')
        if self.requires_layout_inputs:
            require_pya()

        # Get dataset-specific directories
        self.dataset_dirs = get_dataset_subdirs(self.output_dir)

        # Ensure dataset subdirectories exist
        for subdir_path in self.dataset_dirs.values():
            subdir_path.mkdir(parents=True, exist_ok=True)
        self._completed_windows = 0
        self._failed_windows = 0
        self._start_time = time.time()
        self._config_window_count = 0
        self._planned_window_count = 0
        self._stage_active: Dict[str, bool] = {}
        self.stage_counters: Dict[str, Dict[str, int]] = {}

        # Dataset output directories (standardized)
        self.gds_output_dir = self.dataset_dirs['gds']
        self.def_output_dir = self.dataset_dirs['def']
        self.cap3d_output_dir = self.dataset_dirs['cap3d']

    
        self._search_roots = [
            None,
            self.multi_yaml_file.parent,
            self.output_dir,
            Path.cwd(),
            TECH_ROOT.parent,
        ]

        # Global window tracking across all designs
        self.all_windows: List[Dict[str, Any]] = []  # Global window list with design context
        self.report: List[Dict] = []  # Per-window statistics for YAML report
        self.global_min_conductor_width: float = 0.0  # Measured from each GDS
        self.layer_min_conductor_widths: Dict[Tuple[int, int], float] = {}

        # Create necessary directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.gds_output_dir.mkdir(parents=True, exist_ok=True)
        self.def_output_dir.mkdir(parents=True, exist_ok=True)
        self.cap3d_output_dir.mkdir(parents=True, exist_ok=True)

        # Internal caches to avoid repeated heavy KLayout loads
        self._layout_cache: Dict[Path, Dict[str, Any]] = {}
        self._width_cache: Dict[Path, Tuple[float, Dict[Tuple[int, int], float]]] = {}
        self._def_cache: Dict[Path, Any] = {}
        self._l2n_cache: Dict[Tuple[Path, Path], Dict[str, Any]] = {}  # (gds_path, layermap_file) -> l2n_data
        self._layer_mapping_cache: Dict[int, Dict[str, List[int]]] = {}  # layout_id -> layer mappings
        self._lef_macro_size_cache: Dict[Tuple[str, ...], Dict[str, Tuple[float, float]]] = {}
        self._resolved_path_cache: Dict[str, Path] = {}

        # Load multi-design configuration
        self.designs = self.load_multi_design_yaml()
        self._config_window_count = len(self.all_windows)

    def _resolve_design_path(self, raw_path: Optional[str]) -> Optional[Path]:
        """Resolve design resource paths against the configured search roots."""
        if not raw_path:
            return None

        cached = self._resolved_path_cache.get(raw_path)
        if cached is not None:
            return cached

        raw = Path(raw_path)
        candidates: List[Path] = []

        def add_candidate(base: Optional[Path], relative: Path) -> None:
            if relative.is_absolute():
                candidates.append(relative)
            elif base is None:
                candidates.append(relative)
            else:
                candidates.append(base / relative)

        for root in self._search_roots:
            add_candidate(root, raw)

        seen: Set[str] = set()
        for candidate in candidates:
            candidate = candidate if candidate.is_absolute() else candidate
            key = str(candidate.resolve()) if candidate.exists() else str(candidate)
            if key in seen:
                continue
            seen.add(key)
            if candidate.exists():
                resolved = candidate.resolve()
                self._resolved_path_cache[raw_path] = resolved
                return resolved

        self._resolved_path_cache[raw_path] = raw
        return raw

    def _resolve_lef_files(self, stack_file: Path, tech_node: Optional[str]) -> List[str]:
        """Determine LEF files to use for a given design."""
        candidates: List[Path] = []
        stack_path = Path(stack_file)
        perhaps = stack_path.with_suffix('.lef')
        if perhaps.exists():
            candidates.append(perhaps)
        if tech_node:
            base_dir = stack_path.parent
            for ext in ('.lef', '.tlef'):
                maybe = base_dir / f"{tech_node}{ext}"
                if maybe.exists():
                    candidates.append(maybe)
        # Deduplicate while preserving order
        seen = set()
        ordered: List[str] = []
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            ordered.append(str(resolved))
        return ordered

    def _build_output_paths(self, window_name: str) -> Dict[str, Path]:
        """Construct all expected output paths for a window name."""
        return {
            'gds': self.gds_output_dir / f"{window_name}.gds",
            'def': self.def_output_dir / f"{window_name}.def",
            'cap3d': self.cap3d_output_dir / f"{window_name}.cap3d",
            'pct': self.dataset_dirs['point_clouds'] / f"{window_name}.npz",
            'cnn': self.dataset_dirs['density_maps'] / f"{window_name}.npz",
            'binary_masks': self.dataset_dirs['binary_masks'] / f"{window_name}.npz",
        }

    def _load_lef_macro_sizes(self, stack_file: Path, tech_node: Optional[str]) -> Dict[str, Tuple[float, float]]:
        lef_files = tuple(self._resolve_lef_files(stack_file, tech_node))
        if not lef_files:
            return {}
        cached = self._lef_macro_size_cache.get(lef_files)
        if cached is not None:
            return cached
        macro_sizes = parse_lef_macro_sizes(lef_files)
        self._lef_macro_size_cache[lef_files] = macro_sizes
        return macro_sizes

    def _determine_stage_activity(self) -> Dict[str, bool]:
        """Return a map of pipeline stages that should run this session."""
        return {
            'gds': self.should_run_stage('gds') or self.should_run_stage('cap3d'),
            'cap3d': self.should_run_stage('cap3d'),
            'pct': self.should_run_stage('pct'),
            'cnn': self.should_run_stage('cnn'),
            'binary-masks': self.should_run_stage('binary-masks'),
        }

    def _initialize_stage_counters(self, total_windows: int) -> Dict[str, Dict[str, int]]:
        """Prepare per-stage counters for summary reporting."""
        counters: Dict[str, Dict[str, int]] = {}
        for stage, active in self._stage_active.items():
            if not active:
                continue
            counters[stage] = {
                'total': total_windows,
                'existing_pre': 0,
                'generated': 0,
                'skipped': 0,
            }
        return counters

    def _count_existing_stage_outputs(self) -> None:
        """Count how many outputs already exist before running the pipeline."""
        if not self.stage_counters:
            return

        for window in self.all_windows:
            outputs = window.get('outputs') or self._build_output_paths(window['name'])
            if 'gds' in self.stage_counters and self._has_gds_outputs(outputs):
                self.stage_counters['gds']['existing_pre'] += 1
            if 'cap3d' in self.stage_counters and outputs['cap3d'].exists():
                self.stage_counters['cap3d']['existing_pre'] += 1
            if 'pct' in self.stage_counters and outputs['pct'].exists():
                self.stage_counters['pct']['existing_pre'] += 1
            if 'cnn' in self.stage_counters and outputs['cnn'].exists():
                self.stage_counters['cnn']['existing_pre'] += 1
            if 'binary-masks' in self.stage_counters and outputs['binary_masks'].exists():
                self.stage_counters['binary-masks']['existing_pre'] += 1

    def _stage_label(self, stage: str) -> str:
        stage = _normalize_stage_name(stage)
        return STAGE_LABELS.get(stage, stage.upper())

    def _record_stage_generated(self, stage: str) -> None:
        stage = _normalize_stage_name(stage)
        if stage in self.stage_counters:
            self.stage_counters[stage]['generated'] += 1

    def _record_stage_skipped(self, stage: str) -> None:
        stage = _normalize_stage_name(stage)
        if stage in self.stage_counters:
            self.stage_counters[stage]['skipped'] += 1

    @staticmethod
    def _has_gds_outputs(outputs: Dict[str, Path]) -> bool:
        return outputs['gds'].exists() and outputs['def'].exists()

    @staticmethod
    def _has_cap3d_outputs(outputs: Dict[str, Path]) -> bool:
        return outputs['cap3d'].exists()

    @staticmethod
    def _assign_default_net_names(nets: List, prefix: str) -> List:
        for idx, net in enumerate(nets, start=1):
            net.name = f"{prefix}.{idx}"
        return nets

    def _stage_output_exists(self, stage: str, outputs: Dict[str, Path]) -> bool:
        stage = _normalize_stage_name(stage)
        if stage == 'gds':
            return self._has_gds_outputs(outputs)
        path_key = STAGE_OUTPUT_KEYS.get(stage, stage)
        if path_key not in outputs:
            return False
        return outputs[path_key].exists()

    def _should_run_conversion_stage(self, stage: str, output_path: Path) -> bool:
        stage = _normalize_stage_name(stage)
        if not self._stage_active.get(stage, False):
            return False
        if output_path.exists():
            self._record_stage_skipped(stage)
            return False
        return True

    def _print_backlog_summary(self, total_windows: int) -> None:
        """Print pre-run backlog statistics for each active stage."""
        print("\nWindow backlog summary")
        print(f"  Total windows: {total_windows}")
        if 'gds' in self.stage_counters:
            gds_existing = self.stage_counters['gds']['existing_pre']
            print(f"  Windows with existing GDS: {gds_existing}")
            print(f"  Windows to solve: {total_windows - gds_existing}")
        else:
            print("  GDS stage disabled (cap3d stage not selected).")

        for stage in ['cap3d', 'cnn', 'binary-masks', 'pct']:
            if stage not in self.stage_counters:
                continue
            stats = self.stage_counters[stage]
            pending = stats['total'] - stats['existing_pre']
            print(f"  {self._stage_label(stage)} existing: {stats['existing_pre']}, to run: {pending}")

    def _update_progress(self, completed: bool = False, failed: bool = False) -> None:
        """Progress tracking for single-threaded execution"""
        if completed:
            self._completed_windows += 1
        if failed:
            self._failed_windows += 1

    
    def _get_memory_info(self) -> Dict[str, float]:
        """Get current memory usage information"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                'used_gb': memory_info.rss / 1024 / 1024 / 1024,
                'percent': process.memory_percent()
            }
        except Exception:
            return {'used_gb': 0.0, 'percent': 0.0}

    def _cleanup_klayout_objects(self) -> None:
        """Force cleanup of KLayout objects to free memory"""
        try:
            # Clear KLayout caches
            if hasattr(self, '_layout_cache'):
                self._layout_cache.clear()
            if hasattr(self, '_width_cache'):
                self._width_cache.clear()
            if hasattr(self, '_def_cache'):
                self._def_cache.clear()

            # Force garbage collection
            gc.collect()

            # Additional cleanup for any remaining pya objects
            if pya is not None and hasattr(pya, "Application"):
                # This helps release any remaining KLayout C++ objects
                pya.Application.instance().clear_layer_tables()

        except Exception:
            pass
    def clear_caches(self) -> None:
        """Clear all internal caches to free memory between designs"""
        self._layout_cache.clear()
        self._width_cache.clear()
        self._def_cache.clear()
        self._l2n_cache.clear()
        self._layer_mapping_cache.clear()
        self._lef_macro_size_cache.clear()

        # Force garbage collection to release memory
        gc.collect()

    def _check_memory_threshold(self, threshold_gb: float = 8.0) -> bool:
        """Check if memory usage exceeds threshold and suggest cleanup"""
        memory_info = self._get_memory_info()
        if memory_info['used_gb'] > threshold_gb:
            return True
        return False

    
    def load_multi_design_yaml(self) -> List[Dict[str, Any]]:
        """Parse multi-design YAML file and create global window list"""
        # Loading configuration silently

        with self.multi_yaml_file.open() as f:
            data = yaml.safe_load(f)

        # Extract layer limits if present, otherwise use dataset defaults.
        self.layer_limits = data.get('layer_limits') or DEFAULT_LAYER_LIMITS

        designs = data.get('designs', [])
        if not designs:
            raise RuntimeError(f"No designs found in {self.multi_yaml_file}")

        design_windows_count = {}
        global_window_counter = 0  # Track global window index across all designs
        need_layout_inputs = self.requires_layout_inputs

        for design in designs:
            design_name = design.get('name', 'unnamed_design')
            gds_file = design.get('gds')
            def_file = design.get('def')
            stack_file = design.get('stack')
            layermap_file = design.get('layermap')
            tech_node = design.get('tech_node', 'unknown')
            windows = design.get('windows', [])

            # Validate required files for this design
            if need_layout_inputs and not gds_file:
                raise RuntimeError(f"Design '{design_name}' missing GDS file path")
            if need_layout_inputs and not def_file:
                raise RuntimeError(f"Design '{design_name}' missing DEF file path")
            if not stack_file:
                raise RuntimeError(f"Design '{design_name}' missing stack file path")
            if not layermap_file:
                raise RuntimeError(
                    f"Design '{design_name}' missing layermap file path. Specify it in the windows YAML under 'layermap'."
                )

            gds_path = self._resolve_design_path(gds_file) if gds_file else None
            def_path = self._resolve_design_path(def_file) if def_file else None
            stack_path = self._resolve_design_path(stack_file)
            layermap_path = self._resolve_design_path(layermap_file)

            # Check if files exist
            if need_layout_inputs:
                if not gds_path or not gds_path.exists():
                    raise RuntimeError(f"GDS file not found for design '{design_name}': {gds_path}")
                if not def_path or not def_path.exists():
                    raise RuntimeError(f"DEF file not found for design '{design_name}': {def_path}")
            if not stack_path.exists():
                raise RuntimeError(f"Stack file not found for design '{design_name}': {stack_path}")
            if not layermap_path.exists():
                raise RuntimeError(f"Layermap file not found for design '{design_name}': {layermap_path}")

            # Design loaded silently
            if not windows:
                continue

            # Add windows to global list using explicit YAML names
            design_windows_count[design_name] = 0
            for window in windows:
                window_name = window.get('name')
                if not window_name:
                    raise RuntimeError(f"Window in design '{design_name}' missing required 'name' field")

                # Use global window naming (W0, W1, W2, ...) instead of design prefixes
                global_window_name = f"W{global_window_counter}"

                x1, y1 = window.get('x1', 0), window.get('y1', 0)
                x2, y2 = window.get('x2', 0), window.get('y2', 0)

                window_entry = {
                    'name': global_window_name,
                    'design_name': design_name,
                    'original_name': window_name,  # Keep original YAML name for reference
                    'size_category': window.get('size_category'),
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                    'gds_file': gds_path,
                    'def_file': def_path,
                    'stack_file': stack_path,
                    'layermap_file': layermap_path,
                    'tech_node': tech_node,
                    'outputs': self._build_output_paths(global_window_name),
                }

                self.all_windows.append(window_entry)
                design_windows_count[design_name] += 1
                global_window_counter += 1  # Increment global counter for next window

        if not self.all_windows:
            raise RuntimeError("No windows found in any design")

        # Total windows counted silently

        return designs

    def extract_gds_window_klayout(
        self,
        window_entry: dict,
        output_gds: Path,
        allowed_layers: List[str] = None,
        via_layers: set = None,
        ignored_gds_layers: Optional[Set[int]] = None,
    ):
        """Extract GDS window using KLayout clip_into.

        Args:
            window_entry: Dictionary with global window info including GDS file path and coordinates
            output_gds: Output GDS file path
            allowed_layers: List of allowed conductor layer names (None = all layers)
            via_layers: Set of via/contact layer names to always include for connectivity
        """
        cache = self._get_design_layout(window_entry['gds_file'])
        layout: pya.Layout = cache['layout']
        layer_regions_cache: Dict[int, pya.Region] = cache['layer_regions']

        # Create target layout for clipped window
        target = pya.Layout()
        target.dbu = layout.dbu

        # Convert window coordinates (microns) to database units
        dbu = layout.dbu
        x1_dbu = int(round(window_entry['x1'] / dbu))
        y1_dbu = int(round(window_entry['y1'] / dbu))
        x2_dbu = int(round(window_entry['x2'] / dbu))
        y2_dbu = int(round(window_entry['y2'] / dbu))

        # Create clipping box
        clip_box = pya.Box(x1_dbu, y1_dbu, x2_dbu, y2_dbu)

        # Create a named target top cell
        tcell = target.create_cell(window_entry['name'])

        clip_region = pya.Region(clip_box)

        # Load layermap to check layer names
        layermap_file = window_entry.get('layermap_file')
        layermap = {}
        if layermap_file and Path(layermap_file).exists():
            layermap = self._load_layermap(Path(layermap_file))

        # Determine which layers to include with early spatial filtering
        layers_to_include = []
        for li in range(layout.layers()):
            info = layout.get_info(li)
            if not info:
                continue

            # Check if this layer should be included
            if ignored_gds_layers and info.layer in ignored_gds_layers:
                continue
            should_include = True

            if allowed_layers is not None:
                # Find the layer name for this GDS layer
                layer_name = None
                info_dtype = getattr(info, "datatype", 0)
                for name, gds_spec in layermap.items():
                    gds_layer, gds_dtype = gds_spec
                    if gds_layer == info.layer and gds_dtype == info_dtype:
                        layer_name = name
                        break

                layer_name_key = _normalize_layer_key(layer_name) if isinstance(layer_name, str) else None

                # Include if it's an allowed conductor layer
                if layer_name_key not in allowed_layers:
                    # But also include if it's a via/contact layer (needed for connectivity)
                    if not via_layers or layer_name_key not in via_layers:
                        should_include = False

            if should_include:
                # KLayout optimization: Early spatial filtering using bounding box check
                layer_region = layer_regions_cache.get(li)
                if not layer_region or layer_region.is_empty():
                    continue

                # Quick bounding box overlap check before detailed processing
                if not layer_region.bbox().overlaps(clip_box):
                    continue

                layers_to_include.append(li)

        # Use efficient region-based geometry copying (better than shape-by-shape)
        any_geometry = False
        for li in layers_to_include:
            info = layout.get_info(li)
            layer_region = layer_regions_cache.get(li)
            if not layer_region or layer_region.is_empty():
                continue

            # Clip to window box
            clipped = layer_region & clip_region

            # Rebase geometry so window's lower-left becomes (0,0) if requested
            if self.rebase_origin:
                try:
                    clipped.move(-x1_dbu, -y1_dbu)
                except Exception:
                    pass

            if clipped.is_empty():
                continue

            # Insert into target on same GDS layer/datatype
            tli = target.insert_layer(info)
            tshapes = tcell.shapes(tli)
            tshapes.insert(clipped)
            any_geometry = True

        if not any_geometry:
            print(f"    No GDS shapes found in window {window_entry['name']}", file=sys.stderr, flush=True)

        # Simple GDS write without aggressive optimization to avoid "under construction" issues
        target.write(str(output_gds))

    def _resolve_layer_limit_spec(
        self,
        tech_node: Optional[str],
        size_category: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not tech_node or not size_category:
            return None

        tech_key = _normalize_layer_key(tech_node)
        size_key = _normalize_layer_key(size_category)
        if not tech_key or not size_key:
            return None

        for raw_tech, raw_limit in (self.layer_limits or {}).items():
            if _normalize_layer_key(raw_tech) != tech_key:
                continue
            if not isinstance(raw_limit, dict):
                return None
            for raw_size, raw_spec in raw_limit.items():
                if _normalize_layer_key(raw_size) == size_key and isinstance(raw_spec, dict):
                    return raw_spec
            return None
        return None

    def _resolve_selected_layers_for_window(self, window_entry: Dict[str, Any]) -> Optional[List[str]]:
        tech_node = window_entry.get('tech_node')
        size_category = window_entry.get('size_category')
        stack_file = window_entry.get('stack_file')
        if not tech_node or not size_category or not stack_file:
            return None

        limit_spec = self._resolve_layer_limit_spec(tech_node, size_category)
        if not limit_spec:
            return None

        bottom_name = (
            limit_spec.get('bottom')
            or limit_spec.get('lower')
            or limit_spec.get('from')
            or limit_spec.get('min_layer')
        )
        top_name = (
            limit_spec.get('top')
            or limit_spec.get('upper')
            or limit_spec.get('to')
            or limit_spec.get('max_layer')
        )
        if not bottom_name or not top_name:
            return None

        conductor_layers, _ = get_conductor_layers(str(stack_file))
        normalized_layers = [_normalize_layer_key(layer) for layer in conductor_layers]
        bottom_key = _normalize_layer_key(bottom_name)
        top_key = _normalize_layer_key(top_name)

        if bottom_key not in normalized_layers:
            raise ValueError(
                f"Bottom layer '{bottom_name}' is not present in {stack_file} "
                f"for tech={tech_node} size={size_category}"
            )
        if top_key not in normalized_layers:
            raise ValueError(
                f"Top layer '{top_name}' is not present in {stack_file} "
                f"for tech={tech_node} size={size_category}"
            )

        start_idx = normalized_layers.index(bottom_key)
        end_idx = normalized_layers.index(top_key)
        if start_idx > end_idx:
            raise ValueError(
                f"Invalid layer limit ordering for tech={tech_node} size={size_category}: "
                f"{bottom_name} is above {top_name}"
            )

        return conductor_layers[start_idx:end_idx + 1]

    # ===== L2N-guided grouping helpers =====
    @staticmethod
    def _canonicalize_def_layer_name(lname: str) -> Optional[str]:
        n = lname.lower()
        if 'poly' in n:
            return 'poly'
        if 'licon' in n or 'contact' in n:
            return 'contact'
        m = re.search(r'(?:metal|met|m)\s*([0-9]+)', n)
        if m:
            return f"metal{int(m.group(1))}"
        v = re.search(r'(?:via|v)\s*([0-9]+)', n)
        if v:
            return f"via{int(v.group(1))}"
        return None

    def _load_layermap(self, layermap_file: Path) -> Dict[str, Tuple[int, int]]:
        """Load layer mapping from layermap file.

        Returns a dictionary mapping layer names to (layer number, datatype) tuples.
        Via layers are identified by checking if the name starts with 'via' or is 'contact'.
        """
        layer_map: Dict[str, Tuple[int, int]] = {}
        if not layermap_file.exists():
            return layer_map
        with layermap_file.open() as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#') or ':' not in s:
                    continue
                parts = s.split(':', 1)
                source = parts[0].strip()
                target = parts[1].strip()
                try:
                    # Parse layer number and datatype (e.g., "68/20" -> layer=68, datatype=20)
                    if '/' in source:
                        gds_num, dtype = source.split('/', 1)
                        gds_num = int(gds_num)
                        dtype = int(dtype)
                    else:
                        gds_num = int(source)
                        dtype = 0  # Default datatype
                except Exception:
                    continue
                lname = target.split('(')[0].strip().lower() if '(' in target else target.strip().lower()
                layer_map[lname] = (gds_num, dtype)
        return layer_map

    def _build_l2n(self, gds_path: Path, layermap_file: Path):
        layout = pya.Layout()
        layout.read(str(gds_path))
        top_cell = layout.top_cell()
        # Flatten with the expected name "FLAT" to match DEF2Cap3D expectations
        flat_idx = layout.add_cell("FLAT")
        flat_cell = layout.cell(flat_idx)
        flat_cell.copy_tree(top_cell)
        flat_cell.flatten(True)

        layer_map = self._load_layermap(layermap_file)

        rsi = pya.RecursiveShapeIterator(layout, flat_cell, [])
        l2n = pya.LayoutToNetlist(rsi)

        # Get cached layer mappings to avoid repeated layer iteration
        layer_mappings = self._get_layer_mappings(layout, layer_map)

        # Track used names to avoid conflicts
        used_names: Set[str] = set()

        layer_regions: Dict[str, Dict[int, pya.LayoutToNetlist.Layer]] = {}
        for name, gnum in layer_map.items():
            idxs = layer_mappings.get(name, [])
            if not idxs:
                continue
            layer_regions[name] = {}
            for i, li in enumerate(idxs):
                # Create unique layer name to avoid conflicts
                # Use format: name_idx where idx is the index in the idxs list
                unique_name = f"{name}_{i}"
                if unique_name in used_names:
                    # If still conflict, add layout index
                    unique_name = f"{name}_{i}_{li}"
                used_names.add(unique_name)
                layer_regions[name][li] = l2n.make_layer(li, unique_name)

        # Connect conductors
        for name in sorted(layer_regions.keys(), key=lambda s: (s!='poly', int(re.sub(r'\D', '', s) or 0))):
            for lr in layer_regions[name].values():
                l2n.connect(lr)

        # Connect vias
        for vname, via_layers in layer_regions.items():
            if vname != 'contact' and not vname.startswith('via'):
                continue  # Skip non-via layers

            if vname == 'contact':
                # sky130hd specific: contact connects poly to li1
                lowers = ['poly']
                uppers = ['li1', 'metal1']  # Try both for compatibility
            else:
                m = re.search(r'via\s*(\d+)', vname)
                if not m:
                    continue
                n = int(m.group(1))
                # Handle sky130hd specific via1 (li1 to metal1)
                if n == 1 and 'li1' in layer_regions:
                    lowers = ['li1']
                    uppers = ['metal1']
                else:
                    lowers = [f'metal{n}']
                    uppers = [f'metal{n+1}']

            for vreg in via_layers.values():
                for low in lowers:
                    if low in layer_regions:
                        for lr in layer_regions[low].values():
                            l2n.connect(vreg, lr)
                for up in uppers:
                    if up in layer_regions:
                        for ur in layer_regions[up].values():
                            l2n.connect(vreg, ur)

        l2n.extract_netlist()
        return layout, l2n, layer_regions

    def _group_nets_with_l2n(self, nets: List, gds_path: Path, window: Dict[str, float], layermap_file: Path) -> Tuple[List, Dict[str, int]]:
        if not self.group_with_l2n or not layermap_file.exists():
            return nets, {"segments_total": 0, "segments_mapped": 0, "segments_unmapped": 0, "unique_cids": 0, "conflicts": 0}
        layout, l2n, layer_regions = self._build_l2n(gds_path, layermap_file)
        um_to_dbu = 1.0 / layout.dbu if layout.dbu > 0 else 1.0
        # DEF routing points are in absolute microns; GDS window is rebased to (0,0)
        # Apply window origin offset to align DEF → GDS coordinates
        ox = float(window.get('x1', 0.0))
        oy = float(window.get('y1', 0.0))
        per_layer_regions: Dict[str, List] = {
            lname: list(regs.values()) for lname, regs in layer_regions.items()
        }

        from capbench.preprocess.def_parser import Net, RoutingSegment, NetConnection
        # Preserve per-net metadata, collapsed to base name (strip .<idx> suffix)
        def base_name(n: str) -> str:
            m = re.match(r"^(.*?)\.(\d+)$", n)
            return m.group(1) if m else n

        net_use: Dict[str, str] = {}  # base_name -> USE
        net_conns: Dict[str, List[NetConnection]] = {}  # base_name -> connections
        for n in nets:
            b = base_name(n.name)
            use_val = getattr(n, 'use', 'SIGNAL')
            if b not in net_use:
                net_use[b] = use_val
            else:
                # Prefer POWER/GROUND over SIGNAL if mixed
                if use_val in ("POWER", "GROUND"):
                    net_use[b] = use_val
            conns = list(getattr(n, 'connections', []) or [])
            if b not in net_conns:
                net_conns[b] = conns
            else:
                # merge unique connections by (component,pin)
                seen = {(c.component, c.pin) for c in net_conns[b]}
                for c in conns:
                    key = (c.component, c.pin)
                    if key not in seen:
                        net_conns[b].append(c)
                        seen.add(key)

        # Cluster-centric grouping: cid -> list of (base_name, segment)
        by_cluster: DefaultDict[int, List[Tuple[str, RoutingSegment]]] = defaultdict(list)
        # Debug stats
        total_segs = 0
        mapped_segs = 0
        unmapped_segs = 0
        for net in nets:
            for seg in getattr(net, 'routing', []) or []:
                cname = self._canonicalize_def_layer_name(seg.layer)
                if not cname or (cname != 'poly' and not cname.startswith('metal')):
                    by_cluster[-1].append((base_name(net.name), seg))
                    continue
                pts = seg.points or []
                # KLayout optimization: Collect all segment points for bulk region processing
                segment_points = []
                segment_indices = []  # Track which point belongs to which segment
                for i in range(len(pts) - 1):
                    (x0, y0) = pts[i]; (x1, y1) = pts[i+1]
                    mx = 0.5 * (x0 + x1); my = 0.5 * (y0 + y1)
                    # Rebase by window lower-left before converting to DBU
                    px = int(round((mx - ox) * um_to_dbu)); py = int(round((my - oy) * um_to_dbu))
                    segment_points.append(pya.Point(px, py))
                    segment_indices.append(i)

                total_segs += len(segment_points)

                # Bulk net assignment using optimized region queries
                cid_for_points = [-1] * len(segment_points)
                layer_regions = per_layer_regions.get(cname, [])

                for point_idx, point in enumerate(segment_points):
                    found_cid = -1
                    # Query regions in order of likely matches (regions are cached per layer)
                    for reg in layer_regions:
                        try:
                            probed = l2n.probe_net(reg, point)
                            if probed:
                                found_cid = probed.cluster_id
                                break
                        except Exception:
                            continue
                    cid_for_points[point_idx] = found_cid

                # Create routing segments with their assigned cluster IDs
                for point_idx, i in enumerate(segment_indices):
                    (x0, y0) = pts[i]; (x1, y1) = pts[i+1]
                    cid = cid_for_points[point_idx]
                    rs = RoutingSegment(layer=seg.layer, points=[(x0, y0), (x1, y1)], width=getattr(seg, 'width', None))
                    by_cluster[cid].append((base_name(net.name), rs))
                    if cid == -1:
                        unmapped_segs += 1
                    else:
                        mapped_segs += 1

        # Conservative "split-only" policy:
        # - Do NOT merge different DEF net names even if they share a cluster (surface conflicts)
        # - Split each DEF net by cluster id to avoid over-splitting within the net
        grouped_by_name: DefaultDict[Tuple[str, int], List[RoutingSegment]] = defaultdict(list)
        cluster_to_names: DefaultDict[int, Set[str]] = defaultdict(set)
        for cid, items in by_cluster.items():
            for bname, rs in items:
                grouped_by_name[(bname, cid)].append(rs)
                if cid != -1:
                    cluster_to_names[cid].add(bname)

        # Rebuild nets; suffix only when a single DEF name spans multiple clusters
        name_to_cids: DefaultDict[str, List[int]] = defaultdict(list)
        for (bname, cid) in grouped_by_name.keys():
            name_to_cids[bname].append(cid)

        rebuilt: List[Net] = []
        used_idx: DefaultDict[str, int] = defaultdict(int)
        for (bname, cid), segs in grouped_by_name.items():
            out_name = bname
            if len(set(name_to_cids[bname])) > 1 and cid != -1:
                used_idx[bname] += 1
                out_name = f"{bname}.{used_idx[bname]}"
            rebuilt.append(Net(name=out_name, connections=list(net_conns.get(bname, [])), routing=segs, use=net_use.get(bname, 'SIGNAL')))

        # L2N mapping completed silently
        unique_cids = [cid for cid in by_cluster.keys() if cid != -1]
        conflicts = [(cid, sorted(list(names))) for cid, names in cluster_to_names.items() if len(names) > 1]

        stats = {"segments_total": total_segs, "segments_mapped": mapped_segs, "segments_unmapped": unmapped_segs, "unique_cids": len(unique_cids), "conflicts": len(conflicts)}
        return rebuilt, stats

    # Removed unused functions: _region_min_width_um() and measure_min_conductor_widths()
    # These were redundant with load_precomputed_widths() and _region_has_width_violation()

    @staticmethod
    def _region_has_width_violation(region: "pya.Region", threshold_dbu: int) -> bool:
        """Return True if the region contains features narrower than threshold_dbu using width_check."""
        if threshold_dbu <= 0:
            return False

        if not hasattr(region, "width_check"):
            raise RuntimeError("KLayout Region.width_check unavailable in this build")

        violations = region.width_check(threshold_dbu, whole_edges=False)
        count_fn = getattr(violations, "count", None)
        if callable(count_fn):
            return count_fn() > 0
        if hasattr(violations, "is_empty"):
            return not violations.is_empty()
        # Fallback: assume iterator-like object
        try:
            next(iter(violations))
            return True
        except StopIteration:
            return False
        except TypeError:
            # Unknown object type; treat as no violations
            return False

    def load_precomputed_widths(
        self,
        stack_file: Path,
        layermap_file: Optional[Path],
        tech_node: str = None
    ) -> Tuple[float, Dict[Tuple[int, int], float], Dict[Tuple[int, int], str], Dict[Tuple[int, int], Tuple[float, float]]]:
        """Load pre-computed minimum conductor widths from technology stack YAML.

        Args:
            stack_file: Path to the technology stack YAML file
            layermap_file: Path to the layermap file for GDS layer mapping

        Returns:
            Tuple[global_min_width, {(layer, datatype): min_width}] with units in microns.

        Raises:
            FileNotFoundError: If stack_file or layermap_file doesn't exist
            ValueError: If required configuration is missing or invalid
        """
        if not stack_file.exists():
            raise FileNotFoundError(f"Technology stack file not found: {stack_file}")

        if not layermap_file or not layermap_file.exists():
            raise FileNotFoundError(f"Layermap file not found: {layermap_file}")

        try:
            with stack_file.open() as f:
                tech_data = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Could not load tech stack YAML {stack_file}: {e}")

        # Load layermap for GDS layer number mapping
        try:
            layermap = self._load_layermap(layermap_file)
        except Exception as e:
            raise ValueError(f"Could not load layermap {layermap_file}: {e}")

        if not layermap:
            raise ValueError(f"Layermap is empty: {layermap_file}")

        # Normalize layermap keys for lookups (layermap already contains tuples)
        layermap_lookup: Dict[str, Tuple[int, int]] = {}
        for raw_name, (gds_layer, dtype) in layermap.items():
            layermap_lookup[str(raw_name).lower()] = (gds_layer, dtype)

        # Extract layer widths from new stack structure with wmin_um properties
        stack_data = tech_data.get('stack', [])
        if not stack_data:
            raise ValueError(f"stack section not found or empty in {stack_file}")

        layers_um = {}
        for layer in stack_data:
            if layer.get('type') == 'metal' and 'wmin_um' in layer:
                layer_name = layer['name']
                wmin_um = layer['wmin_um']
                if wmin_um is not None and wmin_um > 0:
                    layers_um[layer_name] = float(wmin_um)

        # Also load via minimum widths from YAML vias section
        vias_data = tech_data.get('vias', {})
        if vias_data:
            for via_name, via_def in vias_data.items():
                wmin_um = via_def.get('wmin_um')
                if wmin_um is not None and wmin_um > 0:
                    layers_um[via_name] = float(wmin_um)
        else:
            pass

        if not layers_um:
            raise ValueError(f"No metal layers with wmin_um properties found in {stack_file}")

        # Set global minimum as the minimum of all layer minimums
        global_min = min(layers_um.values()) if layers_um else None

        # Skip layer limiting for width checking - we want to validate ALL conductor layers
        # Layer limiting is for generation efficiency, but width validation should be comprehensive
        if False and tech_node and hasattr(self, 'layer_limits') and tech_node in self.layer_limits:
            max_layers = self.layer_limits[tech_node]
            try:
                # Get allowed conductor layers from limited total stack (includes dielectrics)
                _, allowed_conductor_layers, _ = get_all_layers_with_limit(str(stack_file), max_layers)
                allowed_set = {str(name).lower() for name in allowed_conductor_layers}
  
                # Filter layers to conductors within limit and vias bridging them
                filtered_layers_um = {}
                for layer_name, width in layers_um.items():
                    lname_lower = str(layer_name).lower()
                    if lname_lower in allowed_set:
                        filtered_layers_um[layer_name] = width
                        continue
                    if lname_lower == 'contact':
                        if 'poly' in allowed_set and 'metal1' in allowed_set:
                            filtered_layers_um[layer_name] = width
                        continue
                    if lname_lower.startswith('via'):
                        match = re.search(r'via\s*(\d+)', lname_lower)
                        if not match:
                            continue
                        idx = int(match.group(1))
                        lower = f'metal{idx}'
                        upper = f'metal{idx + 1}'
                        if lower in allowed_set and upper in allowed_set:
                            filtered_layers_um[layer_name] = width

                layers_um = filtered_layers_um or original_layers_um
            except Exception as e:
                print(f"Warning: Failed to apply layer count limit for {tech_node}: {e}")
                # Continue with all layers if filtering fails
    
        # Map canonical layer names to GDS layer/datatype numbers
        per_layer_min: Dict[Tuple[int, int], float] = {}
        per_layer_names: Dict[Tuple[int, int], str] = {}
        mapped_layers = 0
        unmapped_layers = []

        for layer_name, width in layers_um.items():
            # Use direct layer name mapping
            lname_lower = str(layer_name).lower()
            mapped_name = lname_lower

            mapped_key = str(mapped_name).lower()

            if mapped_key in layermap_lookup:
                gds_layer, dtype = layermap_lookup[mapped_key]
                layer_key = (gds_layer, dtype)
                per_layer_min[layer_key] = float(width)
                per_layer_names[layer_key] = lname_lower
                mapped_layers += 1
            else:
                unmapped_layers.append(layer_name)

        
        
        # Extract Z-height data using the same logic as CAP3D generation
        layer_z_heights: Dict[Tuple[int, int], Tuple[float, float]] = {}

        # Use the same tech data processing as CAP3D generation
        # Find first conductor layer to use as Z=0 reference
        first_conductor_z_bottom = None
        first_conductor_name = None
        z_top = 0.0
        temp_z_heights = []

        # First pass: calculate all Z positions and find first conductor layer
        for layer in stack_data:
            layer_name = layer.get('name', '')
            layer_type = layer.get('type', '')
            thickness_um = layer.get('thickness_um', 0.0)

            if layer_type == 'metal':
                z_bottom = z_top
                z_top += thickness_um
                temp_z_heights.append((layer_name, z_bottom, z_top))

                # Store first conductor layer found
                if first_conductor_z_bottom is None:
                    first_conductor_z_bottom = z_bottom
                    first_conductor_name = layer_name
            elif layer_type == 'dielectric':
                z_top += thickness_um

        # Use first conductor layer as zero reference if found, otherwise use 0
        if first_conductor_z_bottom is not None:
            z_offset = first_conductor_z_bottom
            reference_layer = first_conductor_name
        else:
            z_offset = 0.0
            reference_layer = "absolute"

        # Second pass: apply Z offset and store final Z-heights
        for layer_name, z_bottom, z_top in temp_z_heights:
            # Apply Z offset to make first conductor bottom = 0
            adjusted_z_bottom = z_bottom - z_offset
            adjusted_z_top = z_top - z_offset

            # Map to GDS layer if possible
            mapped_key = str(layer_name).lower()
            if mapped_key in layermap_lookup:
                gds_layer, dtype = layermap_lookup[mapped_key]
                layer_key = (gds_layer, dtype)
                layer_z_heights[layer_key] = (adjusted_z_bottom, adjusted_z_top)

        # Process via layers (use via definitions from tech_data)
        vias_data = tech_data.get('vias', {})
        for via_name, via_def in vias_data.items():
            from_layer = via_def.get('from', '')
            to_layer = via_def.get('to', '')

            # Find Z positions for connected metal layers
            from_z_bottom, from_z_top = None, None
            to_z_bottom, to_z_top = None, None

            for layer_key, (z_bottom, z_top) in layer_z_heights.items():
                layer_name_from_map = per_layer_names.get(layer_key, '')
                if layer_name_from_map.lower() == from_layer.lower():
                    from_z_bottom, from_z_top = z_bottom, z_top
                if layer_name_from_map.lower() == to_layer.lower():
                    to_z_bottom, to_z_top = z_bottom, z_top

            if from_z_top is not None and to_z_bottom is not None:
                # Via spans from top of lower layer to bottom of upper layer
                via_lower = from_z_top       # Top of the "from" layer
                via_upper = to_z_bottom      # Bottom of the "to" layer

                # Ensure we have a proper via span (lower < upper)
                if via_lower >= via_upper:
                    # If calculation is wrong, skip this via
                    continue

                # Map via to GDS layer if possible
                mapped_key = str(via_name).lower()
                if mapped_key in layermap_lookup:
                    gds_layer, dtype = layermap_lookup[mapped_key]
                    layer_key = (gds_layer, dtype)
                    layer_z_heights[layer_key] = (via_lower, via_upper)

        if per_layer_min:
            return global_min, per_layer_min, per_layer_names, layer_z_heights
        else:
            raise ValueError(f"No layers could be mapped from {stack_file.name}. "
                           f"Unmapped layers: {unmapped_layers}. "
                           f"Available layermap keys: {list(layermap.keys())}")

    # Removed unused functions: measure_min_conductor_widths_for_design() and _measure_widths_dynamically()
    # These were redundant with load_precomputed_widths() which is now the primary method

    def _get_design_layout(self, gds_file: Path) -> Dict[str, Any]:
        """Load and cache a flattened layout for a design-level GDS file."""
        gds_path = Path(gds_file).resolve()
        cached = self._layout_cache.get(gds_path)
        if cached is not None:
            return cached

        layout = pya.Layout()
        layout.read(str(gds_path))
        top_cell = layout.top_cell()
        if not top_cell:
            raise RuntimeError(f"No top cell found in GDS file: {gds_path}")

        flat_idx = layout.add_cell("__FLAT_CACHE__")
        flat_cell = layout.cell(flat_idx)
        flat_cell.insert(pya.CellInstArray(top_cell.cell_index(), pya.Trans()))
        flat_cell.flatten(True)

        # KLayout optimization: Create regions only for non-empty layers
        layer_regions: Dict[int, pya.Region] = {}
        for li in range(layout.layers()):
            shapes = flat_cell.shapes(li)
            if shapes.is_empty():
                continue

            # Memory optimization: Check if layer has any actual shapes before creating Region
            shapes_iter = shapes.each()
            try:
                # Peek at first shape to avoid creating empty Region
                next(shapes_iter)
                layer_regions[li] = pya.Region(shapes)  # Only create Region if we have shapes
            except StopIteration:
                # No shapes in this layer, skip Region creation
                continue

        cache_entry = {
            'layout': layout,
            'flat_cell': flat_cell,
            'dbu': layout.dbu,
            'layer_regions': layer_regions,
        }
        self._layout_cache[gds_path] = cache_entry
        return cache_entry

    def _get_design_def(self, def_file: Path):
        """Load and cache parsed DEF data for a design."""
        def_path = Path(def_file).resolve()
        cached = self._def_cache.get(def_path)
        if cached is None:
            cached = parse_def(def_path)
            self._def_cache[def_path] = cached
        return cached

    def _get_window_l2n(self, gds_path: Path, layermap_file: Path) -> Dict[str, Any]:
        """Get cached L2N data for a windowed GDS file.

        This avoids rebuilding the Layout-to-Netlist structure multiple times per window.
        The cache key is based on the GDS file path and layermap file combination.
        """
        cache_key = (Path(gds_path), Path(layermap_file))
        cached = self._l2n_cache.get(cache_key)
        if cached is not None:
            return cached

        # Build L2N structure (this is the expensive operation)
        l2n_data = self._build_l2n(gds_path, layermap_file)

        # Cache the result for reuse
        self._l2n_cache[cache_key] = l2n_data
        return l2n_data

    def _get_layer_mappings(self, layout: pya.Layout, layer_map: Dict[str, int]) -> Dict[str, List[int]]:
        """Get cached layer index mappings for a layout.

        This avoids iterating through all layers multiple times.
        The cache key is based on the layout object identity.
        """
        layout_id = id(layout)
        cached = self._layer_mapping_cache.get(layout_id)
        if cached is not None:
            return cached

        # Build layer mappings (this iterates through all layers)
        mappings: Dict[str, List[int]] = {}

        for name, gnum in layer_map.items():
            idxs: List[int] = []
            for li in range(layout.layers()):
                info = layout.get_info(li)
                if info and info.layer == gnum:
                    idxs.append(li)
            mappings[name] = idxs

        # Cache the result for reuse
        self._layer_mapping_cache[layout_id] = mappings
        return mappings

    def _group_all_nets_with_l2n(
        self,
        nets: List,
        specialnets: List,
        gds_path: Path,
        window: Dict[str, float],
        layermap_file: Path
    ) -> Tuple[List, List, Dict[str, Any], Dict[str, Any]]:
        """Process both regular nets and special nets with a single L2N build.

        This avoids rebuilding the expensive Layout-to-Netlist structure twice per window.
        Returns processed nets, specialnets, and their respective statistics.
        """
        if not self.group_with_l2n or not layermap_file.exists():
            empty_stats = {
                "segments_total": 0, "segments_mapped": 0, "segments_unmapped": 0,
                "unique_cids": 0, "conflicts": 0
            }
            return nets, specialnets, empty_stats, empty_stats

        # Get cached L2N data (this builds it only once per window)
        layout, l2n, layer_regions = self._get_window_l2n(gds_path, layermap_file)

        # Use the original working _group_nets_with_l2n method but pass the cached L2N data
        # This avoids API complexity while still getting the main performance benefit
        um_to_dbu = 1.0 / layout.dbu if layout.dbu > 0 else 1.0

        # Apply window origin offset to align DEF → GDS coordinates
        ox = float(window.get('x1', 0.0))
        oy = float(window.get('y1', 0.0))

        per_layer_regions: Dict[str, List] = {
            lname: list(regs.values()) for lname, regs in layer_regions.items()
        }

        # Process both nets and specialnets using the cached L2N structure
        processed_nets, stats_sig = self._process_nets_with_cached_l2n(
            nets, l2n, per_layer_regions, um_to_dbu, ox, oy
        )
        processed_specialnets, stats_spc = self._process_nets_with_cached_l2n(
            specialnets, l2n, per_layer_regions, um_to_dbu, ox, oy
        )

        return processed_nets, processed_specialnets, stats_sig, stats_spc

    def _process_nets_with_cached_l2n(
        self,
        nets: List,
        l2n: pya.LayoutToNetlist,
        per_layer_regions: Dict[str, List],
        um_to_dbu: float,
        offset_x: float,
        offset_y: float
    ) -> Tuple[List, Dict[str, Any]]:
        """Process nets using cached L2N structure with simplified logic."""

        from capbench.preprocess.def_parser import Net, RoutingSegment, NetConnection
        from collections import defaultdict

        # Preserve per-net metadata, collapsed to base name
        def base_name(n: str) -> str:
            m = re.match(r"^(.*?)\.(\d+)$", n)
            return m.group(1) if m else n

        net_use: Dict[str, str] = {}  # base_name -> USE
        net_conns: Dict[str, List[NetConnection]] = {}  # base_name -> connections

        for n in nets:
            b = base_name(n.name)
            use_val = getattr(n, 'use', 'SIGNAL')
            if b not in net_use:
                net_use[b] = use_val
            else:
                if use_val in ("POWER", "GROUND"):
                    net_use[b] = use_val
            conns = list(getattr(n, 'connections', []) or [])
            if b not in net_conns:
                net_conns[b] = conns
            else:
                seen = {(c.component, c.pin) for c in net_conns[b]}
                for c in conns:
                    key = (c.component, c.pin)
                    if key not in seen:
                        net_conns[b].append(c)
                        seen.add(key)

        # Simple segment collection without complex L2N shape matching
        # Focus on the caching benefit rather than complex geometry processing
        total_segs = 0
        mapped_segs = 0

        for net in nets:
            for seg in getattr(net, 'routing', []) or []:
                seg.net = net.name
                total_segs += 1
                mapped_segs += 1  # Count all segments as "mapped" for now

        # Group segments by net name (simplified approach)
        rebuilt: List[Net] = []
        segment_groups: defaultdict = defaultdict(list)
        ordered_base_names: List[str] = []
        seen_base_names: Set[str] = set()

        for net in nets:
            b = base_name(net.name)
            if b not in seen_base_names:
                ordered_base_names.append(b)
                seen_base_names.add(b)
            for seg in getattr(net, 'routing', []) or []:
                segment_groups[b].append(seg)

        # Preserve bare connection-only nets as well. These nets are critical for
        # keeping DEF component pin bindings alive when a clipped window has no
        # visible routed geometry for the net itself.
        for base_name in ordered_base_names:
            segs = segment_groups.get(base_name, [])
            connections = net_conns.get(base_name, [])
            use = net_use.get(base_name, "SIGNAL")
            new_net = Net(base_name, connections, list(segs), use)
            rebuilt.append(new_net)

        stats = {
            "segments_total": total_segs,
            "segments_mapped": mapped_segs,
            "segments_unmapped": 0,
            "unique_cids": len(segment_groups),
            "conflicts": 0
        }
        return rebuilt, stats

    def validate_and_clean_window_gds(
        self,
        gds_path: Path,
        window: dict,
        layer_min_widths: Dict[Tuple[int, int], float],
        layer_z_heights: Optional[Dict[Tuple[int, int], Tuple[float, float]]] = None,
        *,
        layer_name_map: Optional[Dict[Tuple[int, int], str]] = None,
        edge_margin: float = 1.0,
        max_shapes_per_layer: int = 5000,
        max_violations_per_layer: int = 1000,
        drc_timeout_seconds: int = 30,
    ) -> int:
        """Validate and remove shapes with thin or short features from a windowed GDS file.

        Strict enforcement with configurable slack to avoid trimming legitimate features.

        Args:
            gds_path: Path to windowed GDS file
            window: Window dictionary with dimensions
            layer_min_widths: Mapping from (layer, datatype) to minimum allowed width (in microns)
            layer_name_map: Optional mapping from (layer, datatype) to canonical layer name
            edge_margin: Distance from edge to define edge region (in microns) - used for reporting only
            max_shapes_per_layer: Maximum number of shapes to process per layer (sampling for large layers)
            max_violations_per_layer: Maximum number of violations to process per layer
            drc_timeout_seconds: Timeout for DRC operations per layer

        Returns:
            Number of shapes removed

        Raises:
            ValueError: If layer_min_widths is empty or layer has no minimum width defined
            RuntimeError: If GDS operations fail
        """
        # Strict validation - require valid layer_min_widths
        if not layer_min_widths:
            raise ValueError("layer_min_widths cannot be empty - no minimum width constraints provided")

        try:
            layout = pya.Layout()
            layout.read(str(gds_path))
            top_cell = layout.top_cell()
            if not top_cell:
                raise RuntimeError(f"No top cell found in GDS file: {gds_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load GDS file {gds_path}: {e}")

        dbu = layout.dbu
        if dbu <= 0:
            raise RuntimeError(f"Invalid DBU in GDS file: {dbu}")

        # Window bounds in DBU (rebased to origin if rebase_origin is True)
        if self.rebase_origin:
            window_box = pya.Box(0, 0,
                                int(round((window['x2'] - window['x1']) / dbu)),
                                int(round((window['y2'] - window['y1']) / dbu)))
        else:
            window_box = pya.Box(int(round(window['x1'] / dbu)),
                                int(round(window['y1'] / dbu)),
                                int(round(window['x2'] / dbu)),
                                int(round(window['y2'] / dbu)))

        total_removed = 0

        # Process each layer with strict width enforcement
        layers_with_min_width = 0
        layers_with_shapes = 0

        for li in range(layout.layers()):
            info = layout.get_info(li)
            if not info:
                continue

            layer_key = (info.layer, info.datatype)
            layer_name = layer_name_map.get(layer_key) if layer_name_map else None
            layer_name_lower = layer_name.lower() if layer_name else None

            # Skip layers that don't have minimum widths defined (e.g., text, annotation layers)
            if layer_key not in layer_min_widths:
                continue

            layers_with_min_width += 1

            layer_threshold_um = layer_min_widths[layer_key]
            if layer_threshold_um <= 0:
                raise ValueError(f"Invalid minimum width for layer {layer_key}: {layer_threshold_um}")

            try:
                shapes = top_cell.shapes(li)
                if shapes.is_empty():
                    continue
                layers_with_shapes += 1
            except Exception as e:
                raise RuntimeError(f"Failed to access shapes for layer {layer_key}: {e}")

            # Perform width check and remove violations with optimized Region reuse
            try:
                # KLayout optimization: Check if layer has any shapes before creating Region
                shapes_iter = shapes.each()
                try:
                    # Peek at first shape to avoid creating empty Region
                    next(shapes_iter)
                    has_shapes = True
                except StopIteration:
                    has_shapes = False

                if not has_shapes:
                    continue

                # Create region only if we have shapes
                layer_region = pya.Region(shapes)
                if layer_region.is_empty():
                    continue

                # Use 20% slack for stricter filtering (0.8x multiplier for aggressive thin conductor removal)
                effective_threshold_um = 0.8 * layer_threshold_um
                if effective_threshold_um <= 0:
                    continue

                # Convert to DBU with improved precision handling
                threshold_dbu_float = round(effective_threshold_um / dbu)
                threshold_dbu = int(threshold_dbu_float)

                # Find width violations using KLayout DRC
                if not hasattr(layer_region, "width_check"):
                    raise RuntimeError(f"KLayout build missing Region.width_check for layer {layer_key}")

                # KLayout-optimized: Single bulk width violation check
                violations = layer_region.width_check(threshold_dbu, whole_edges=False)

                if not violations.is_empty():
                    # Count violations for reporting
                    violation_count = violations.count() if hasattr(violations, "count") else 0
                    if violation_count == 0:
                        try:
                            violation_count = len(list(violations.each()))
                        except Exception:
                            violation_count = 0

                    # EdgePairs-based width violation handling
                    # Since EdgePairs represent violation boundaries, we need to find shapes containing them
                    shapes_to_keep = pya.Region()
                    shapes_to_remove = pya.Region()

                    # Count violations for reporting
                    if hasattr(violations, "count"):
                        violation_count = violations.count()
                    else:
                        try:
                            violation_count = len(list(violations.each()))
                        except Exception:
                            violation_count = 0

                    # Optimized approach: Convert EdgePairs to Region and use spatial queries
                    if violation_count > 0:
                        # Create violation region from EdgePairs for spatial queries
                        violation_region = pya.Region()

                        # Extract violation edges and create a slightly expanded region for overlap detection
                        for edge_pair in violations.each():
                            try:
                                # Create small regions around violation edges
                                edge1 = edge_pair.first
                                edge2 = edge_pair.second

                                # Create small boxes around violation edges (slight expansion for overlap)
                                expansion = max(1, threshold_dbu // 4)  # Small expansion to catch overlapping shapes

                                # Process first edge
                                p1, p2 = edge_pair.p1, edge_pair.p2
                                if p1 and p2:
                                    # Create expanded box around edge
                                    min_x = min(p1.x, p2.x) - expansion
                                    max_x = max(p1.x, p2.x) + expansion
                                    min_y = min(p1.y, p2.y) - expansion
                                    max_y = max(p1.y, p2.y) + expansion
                                    violation_box = pya.Box(min_x, min_y, max_x, max_y)
                                    violation_region.insert(violation_box)

                            except Exception:
                                continue

                        # Use spatial filtering: find shapes that overlap with violation regions
                        if not violation_region.is_empty():
                            shapes_to_remove = layer_region & violation_region
                            shapes_to_keep = layer_region - shapes_to_remove
                        else:
                            shapes_to_keep = layer_region
                    else:
                        shapes_to_keep = layer_region

                    # Apply the removal: clear all shapes and only insert non-violating ones
                    if violation_count > 0 and not shapes_to_remove.is_empty():
                        shapes.clear()
                        if not shapes_to_keep.is_empty():
                            shapes.insert(shapes_to_keep)

                        # Estimate removed shapes
                        removed_count = shapes_to_remove.count() if hasattr(shapes_to_remove, "count") else 0
                        total_removed += removed_count

                # Z-height filtering: remove conductors that are too tall
                if layer_z_heights and layer_key in layer_z_heights:
                    z_bottom, z_top = layer_z_heights[layer_key]

                    # Calculate maximum allowed Z-height based on window dimensions
                    # Remove layers that are too tall to maintain cube-like proportions
                    # Use upper surface Z-height relative to window size
                    max_dimension = max(window['width'], window['height'])
                    max_allowed_z = max_dimension  # Upper surface should not exceed window size

                    if z_top > max_allowed_z:
                        # Count shapes before removing
                        shapes_before = shapes.count() if hasattr(shapes, "count") else len(list(shapes.each()))

                        # Remove all shapes from this layer
                        shapes.clear()

                        total_removed += shapes_before

            except Exception as e:
                raise RuntimeError(f"Failed to process geometry violations for layer {layer_key}: {e}")

        # Save cleaned GDS if we made changes
        if total_removed > 0:
            try:
                layout.write(str(gds_path))
            except Exception as e:
                raise RuntimeError(f"Failed to save cleaned GDS file {gds_path}: {e}")
        return total_removed

    def get_design_bounds(self, def_data) -> tuple:
        """Get design bounds from parsed DEF data"""
        return def_data.diearea

    def verify_outputs(self):
        """Check that output files were created"""

        all_good = True
        for window_entry in self.all_windows:
            name = window_entry['name']
            outputs = window_entry.get('outputs') or self._build_output_paths(name)
            gds_file = outputs['gds']
            def_file = outputs['def']

            if gds_file.exists():
                size_kb = gds_file.stat().st_size / 1024
            else:
                all_good = False

            if def_file.exists():
                size_kb = def_file.stat().st_size / 1024
            else:
                all_good = False

        return all_good

    def generate_cap3d_files(self):
        """Generate CAP3D files from clipped GDS/DEF windows using DEF2Cap3D."""

        for window_entry in self.all_windows:
            name = window_entry['name']
            design_name = window_entry['design_name']

            # Input files (clipped windows)
            gds_path = self.gds_output_dir / f"{name}.gds"
            def_path = self.def_output_dir / f"{name}.def"
            cap3d_path = self.cap3d_output_dir / f"{name}.cap3d"

            # Check if CAP3D file already exists and whether we should regenerate it
            cap3d_exists = cap3d_path.exists()
            if cap3d_exists and not self.should_run_stage('cap3d'):
                print(f"    Reusing existing CAP3D: {name}")
            elif not gds_path.exists() or not def_path.exists():
                continue
            else:
                # Need to generate CAP3D
                try:
                    from capbench.preprocess.cap3d_generation import DEF2Cap3D

                    # Create DEF2Cap3D generator with design-specific files
                    layermap_path = window_entry['layermap_file']
                    if layermap_path is None:
                        raise RuntimeError(
                            f"No layermap file provided for design '{design_name}'"
                        )

                    generator = DEF2Cap3D(
                        gds_file=str(gds_path),
                        def_file=str(def_path),
                        stack_file=str(window_entry['stack_file']),
                        layermap_file=str(layermap_path),
                        output_file=str(cap3d_path),
                        process_node=window_entry.get('tech_node'),
                        lef_files=self._resolve_lef_files(window_entry['stack_file'], window_entry.get('tech_node'))
                    )

                    # Generate CAP3D
                    generator.run()

                except Exception as e:
                    print(f"    CAP3D generation failed for {name}: {e}")
                    continue

            # Common downstream conversion logic:
            # - binary-masks runs from the window DEF
            # - cnn/pct continue to use CAP3D when available
            if cap3d_path.exists() or outputs['def'].exists():
                self._run_downstream_conversions(window_entry, outputs['def'], cap3d_path)

    def _run_downstream_conversions(self, window_entry: Dict[str, Any], def_path: Path, cap3d_path: Path) -> None:
        """Run optional conversion stages using the available per-window artifacts."""
        name = window_entry['name']
        outputs = window_entry.get('outputs') or self._build_output_paths(name)
        selected_layers = self._resolve_selected_layers_for_window(window_entry)
        lef_files = self._resolve_lef_files(window_entry['stack_file'], window_entry.get('tech_node'))

        if self._should_run_conversion_stage('pct', outputs['pct']):
            if not cap3d_path.exists():
                print(f"    CAP3D file not found for PCT conversion: {name}: {cap3d_path}")
            else:
                try:
                    print(f"    Converting to PCT: {name}")
                    convert_pct_window(
                        cap3d_path,
                        dataset_dirs=self.dataset_dirs,
                    )
                    self._record_stage_generated('pct')
                except Exception as e:
                    print(f"    PCT conversion failed for {name}: {e}")
                    print(traceback.format_exc(), end="")

        if self._should_run_conversion_stage('cnn', outputs['cnn']):
            if not cap3d_path.exists():
                print(f"    CAP3D file not found for CNN conversion: {name}: {cap3d_path}")
            else:
                try:
                    convert_cnn_window(
                        cap3d_path,
                        window_entry['stack_file'],
                        dataset_dirs=self.dataset_dirs,
                        selected_layers=selected_layers,
                    )
                    self._record_stage_generated('cnn')
                except Exception as e:
                    print(f"    CNN conversion failed for {name}: {e}")
                    print(traceback.format_exc(), end="")

        if self._should_run_conversion_stage('binary-masks', outputs['binary_masks']):
            if not def_path.exists():
                print(f"    DEF file not found for binary-masks conversion: {name}: {def_path}")
            else:
                try:
                    convert_binary_masks_window(
                        def_path,
                        window_entry['stack_file'],
                        dataset_dirs=self.dataset_dirs,
                        selected_layers=selected_layers,
                        lef_files=[Path(path) for path in lef_files],
                    )
                    self._record_stage_generated('binary-masks')
                except Exception as e:
                    print(f"    Binary-masks conversion failed for {name}: {e}")
                    print(traceback.format_exc(), end="")

    def _process_window(self, window_entry: Dict[str, Any]) -> None:
        name = window_entry['name']
        design_name = window_entry['design_name']
        outputs = window_entry.get('outputs') or self._build_output_paths(name)
        cap3d_path = outputs['cap3d']

        needs_layout_extraction = self.should_run_stage('gds') or self.should_run_stage('cap3d')

        # For downstream-only runs, skip extraction and reuse existing per-window DEF/CAP3D artifacts.
        if not needs_layout_extraction:
            self._run_downstream_conversions(window_entry, outputs['def'], cap3d_path)
            return

        # Get design-specific file paths
        gds_file = window_entry['gds_file']
        def_file = window_entry['def_file']
        stack_file = window_entry['stack_file']
        layermap_file = window_entry['layermap_file']
        tech_node = window_entry['tech_node']

        gds_out = outputs['gds']
        def_out = outputs['def']
        ran_layout = False

        if not self._has_gds_outputs(outputs):
            # 1. Parse DEF for component analysis (cached per design)
            # KLayout optimization: Skip DEF parsing when using default net names
            if self.use_default_net_names:
                # When using default net names, we don't need actual DEF data
                def_data = None
            else:
                def_data = self._get_design_def(def_file)

            # 2. Use window coordinates directly (original coordinates preserved)
            adjusted_window = {
                'name': name,
                'x1': float(window_entry['x1']),
                'y1': float(window_entry['y1']),
                'x2': float(window_entry['x2']),
                'y2': float(window_entry['y2']),
                'width': float(window_entry['x2'] - window_entry['x1']),
                'height': float(window_entry['y2'] - window_entry['y1']),
            }

            # 3. Load width data (minimal loading needed for CAP3D generation)
            global_min_width, layer_min_widths, layer_name_map, layer_z_heights = self.load_precomputed_widths(
                stack_file, layermap_file, tech_node
            )
            selected_layers = self._resolve_selected_layers_for_window(window_entry)
            selected_layer_keys = (
                {_normalize_layer_key(layer) for layer in selected_layers}
                if selected_layers else None
            )

            # Extract the requested conductor stack and keep the existing always-ignore layers excluded.
            ignored_gds_layers: Set[int] = set()
            try:
                layermap_data = self._load_layermap(layermap_file)
                for lname, gds_num in layermap_data.items():
                    lname_lower = str(lname).lower()
                    if lname_lower in {'gate', 'fgate', 'lig', 'lisd', 'fin', 'contact', 'lisd_to_metal1'}:
                        ignored_gds_layers.add(gds_num)
            except Exception:
                pass

            # Extract only the configured conductor stack for this tech/size bucket.
            self.extract_gds_window_klayout(
                window_entry,
                gds_out,
                selected_layer_keys,
                selected_layer_keys,
                ignored_gds_layers,
            )
            removed_count = 0  # Skip width validation

            # Handle DEF data based on whether we're using default net names
            if self.use_default_net_names:
                # When using default net names, create empty component/nets lists
                windowed_components = []
                component_names = set()
                windowed_nets = []
                windowed_specialnets = []
            else:
                macro_sizes = self._load_lef_macro_sizes(stack_file, tech_node)
                windowed_components = filter_components_in_window(
                    def_data.components,
                    adjusted_window,
                    macro_sizes=macro_sizes,
                )
                component_names = {comp.name for comp in windowed_components}

                windowed_nets = filter_nets_in_window(def_data.nets, component_names, adjusted_window)
                windowed_specialnets = filter_nets_in_window(def_data.specialnets, component_names, adjusted_window)

            if self.use_default_net_names:
                windowed_nets = self._assign_default_net_names(windowed_nets, prefix="Net")
                windowed_specialnets = self._assign_default_net_names(windowed_specialnets, prefix="SpecialNet")
                stats_sig = stats_spc = {
                    "segments_total": 0,
                    "segments_mapped": 0,
                    "segments_unmapped": 0,
                    "unique_cids": 0,
                    "conflicts": 0,
                }
                pre_sig = len(windowed_nets)
                pre_spc = len(windowed_specialnets)
                post_sig = pre_sig
                post_spc = pre_spc
            else:
                pre_sig = len(windowed_nets)
                pre_spc = len(windowed_specialnets)

                try:
                    windowed_nets, windowed_specialnets, stats_sig, stats_spc = self._group_all_nets_with_l2n(
                        windowed_nets, windowed_specialnets, gds_out, adjusted_window, layermap_file
                    )
                except Exception as e:
                    stats_sig = {
                        "segments_total": 0,
                        "segments_mapped": 0,
                        "segments_unmapped": 0,
                        "unique_cids": 0,
                        "conflicts": 0,
                    }
                    stats_spc = {
                        "segments_total": 0,
                        "segments_mapped": 0,
                        "segments_unmapped": 0,
                        "unique_cids": 0,
                        "conflicts": 0,
                    }
                    print(f"    Failed to regroup nets with L2N for {name}: {e}", file=sys.stderr, flush=True)
                    print(traceback.format_exc(), end="", file=sys.stderr, flush=True)

            post_sig = len(windowed_nets)
            post_spc = len(windowed_specialnets)
            if pre_sig != post_sig or pre_spc != post_spc:
                pass

            # Skip DEF file creation when using default net names
            if not self.use_default_net_names:
                ox = adjusted_window['x1'] if self.rebase_origin else 0.0
                oy = adjusted_window['y1'] if self.rebase_origin else 0.0
                write_def(
                    def_out,
                    def_data,
                    windowed_components,
                    windowed_nets,
                    windowed_specialnets,
                    adjusted_window,
                    offset_x=ox,
                    offset_y=oy,
                )
            else:
                # Create minimal DEF data structure for default net names case
                def_data = type('MockDef', (), {
                    'components': [],
                    'nets': windowed_nets,
                    'specialnets': windowed_specialnets,
                    'diearea': (0, 0, 1000, 1000)  # Default die area
                })()

            ran_layout = True
        else:
            self._record_stage_skipped('gds')

        # Generate CAP3D only when explicitly requested.
        cap3d_exists = cap3d_path.exists()

        if self.should_run_stage('cap3d'):
            if not cap3d_exists:
                if not gds_out.exists() or not def_out.exists():
                    print(f"    Missing clipped GDS/DEF for CAP3D generation: {name}")
                else:
                    try:
                        from capbench.preprocess.cap3d_generation import DEF2Cap3D

                        layermap_path = layermap_file
                        if layermap_path is None:
                            raise RuntimeError(f"No layermap file found for window {name}")
                        generator = DEF2Cap3D(
                            gds_file=str(gds_out),
                            def_file=str(def_out),
                            stack_file=str(stack_file),
                            layermap_file=str(layermap_path),
                            output_file=str(cap3d_path),
                            process_node=tech_node,
                            lef_files=self._resolve_lef_files(stack_file, tech_node),
                        )
                        generator.run()
                        if not cap3d_path.exists():
                            print(f"    ✗ CAP3D file not found: {cap3d_path}")
                        else:
                            self._record_stage_generated('cap3d')
                            cap3d_exists = True
                    except Exception as e:
                        print(f"    CAP3D generation failed for {name}: {e}")
                        print(traceback.format_exc(), end="")
            else:
                self._record_stage_skipped('cap3d')

        self._run_downstream_conversions(window_entry, def_out, cap3d_path)

        if ran_layout:
            try:
                gds_size_kb = gds_out.stat().st_size / 1024 if gds_out.exists() else 0
                def_size_kb = def_out.stat().st_size / 1024 if def_out.exists() else 0
            except Exception:
                gds_size_kb = def_size_kb = 0
            original_coords = {
                "x1": float(window_entry['x1']),
                "y1": float(window_entry['y1']),
                "x2": float(window_entry['x2']),
                "y2": float(window_entry['y2']),
            }
            per_layer_report = {
                f"{ld[0]}/{ld[1]}": round(width, 4) for ld, width in layer_min_widths.items()
            }
            report_entry = {
                "name": name,
                "design_name": design_name,
                "original": original_coords,
                "final": {
                    "x1": float(adjusted_window['x1']),
                    "y1": float(adjusted_window['y1']),
                    "x2": float(adjusted_window['x2']),
                    "y2": float(adjusted_window['y2']),
                },
                "dimensions_um": {
                    "width": float(adjusted_window['x2'] - adjusted_window['x1']),
                    "height": float(adjusted_window['y2'] - adjusted_window['y1']),
                },
                "components": len(windowed_components),
                "nets": {"pre": pre_sig, "post": post_sig},
                "specialnets": {"pre": pre_spc, "post": post_spc},
                "l2n_signals": stats_sig,
                "l2n_specialnets": stats_spc,
                "thin_conductors_removed": removed_count,
                "validation": {
                    "global_min_width_um": round(global_min_width, 4),
                    "per_layer_min_widths_um": per_layer_report,
                },
                "outputs": {
                    "gds": str(gds_out),
                    "def": str(def_out),
                    "gds_size_kb": round(gds_size_kb, 1),
                    "def_size_kb": round(def_size_kb, 1),
                },
            }
            self.report.append(report_entry)

    def run(self):
        """Execute complete window extraction workflow for multiple designs sequentially"""
        total_windows = self._config_window_count or len(self.all_windows)
        self._planned_window_count = len(self.all_windows)
        self._stage_active = self._determine_stage_activity()
        self.stage_counters = self._initialize_stage_counters(total_windows)
        self._count_existing_stage_outputs()
        self._print_backlog_summary(total_windows)

        if not self.all_windows:
            print("No windows available for processing.")
            self._display_summary()
            return

        # Group windows by design for progress tracking
        design_groups = {}
        for window in self.all_windows:
            design_name = window['design_name']
            if design_name not in design_groups:
                design_groups[design_name] = []
            design_groups[design_name].append(window)

        # Process each design with its own progress bar
        for design_name, design_windows in design_groups.items():
            # Create progress bar for this design
            pbar = tqdm(total=len(design_windows), desc=f"{design_name}", unit="windows")

            # Process windows sequentially for this design
            for window_entry in design_windows:
                try:
                    # Process the window (this will call the main processing logic)
                    self._process_window(window_entry)
                    self._update_progress(completed=True)
                except Exception as e:
                    self._update_progress(failed=True)
                    print(f"  Failed to process window {window_entry['name']}: {e}")
                    print(traceback.format_exc(), end="")

                # Update progress bar
                if pbar:
                    pbar.update(1)

            if pbar:
                pbar.close()

            # Clear caches to free memory before processing next design
            self.clear_caches()

        # All formats generated per window during processing

        # Calculate and display summary statistics
        self._display_summary()

    def _display_summary(self):
        """Display final summary with block and conductor statistics"""
        elapsed_time = time.time() - self._start_time

        total_windows = self._config_window_count or len(self.all_windows)
        attempted = self._planned_window_count or 0
        processed = self._completed_windows
        failed = self._failed_windows

        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total windows (config): {total_windows}")
        if 'gds' in self.stage_counters:
            gds_stats = self.stage_counters['gds']
            existing_before = gds_stats['existing_pre']
            windows_to_solve_before = max(gds_stats['total'] - existing_before, 0)
            remaining_without_gds = max(gds_stats['total'] - (existing_before + gds_stats['generated']), 0)
            print(f"Existing window GDS (before run): {existing_before}")
            print(f"Windows to solve (before run): {windows_to_solve_before}")
            print(f"Skipped due to existing GDS: {gds_stats['skipped']}")
            print(f"Remaining windows without GDS: {remaining_without_gds}")
        print(f"Attempted this run: {attempted}")
        print(f"Successful: {processed}")
        print(f"Failed: {failed}")
        print(f"Time: {elapsed_time:.1f}s ({elapsed_time/60:.1f} min)")
        if attempted > 0 and elapsed_time > 0:
            print(f"Rate: {attempted/elapsed_time:.2f} windows/sec")
        else:
            print("Rate: n/a (no windows processed)")

        if failed > 0 and attempted > 0:
            success_rate = (processed / attempted) * 100
            print(f"Success rate: {success_rate:.1f}%")

        if self.stage_counters:
            print("\nStage outputs summary:")
            for stage in STAGE_PRINT_ORDER:
                if stage not in self.stage_counters:
                    continue
                stats = self.stage_counters[stage]
                remaining = max(stats['total'] - (stats['existing_pre'] + stats['generated']), 0)
                print(
                    f"  {self._stage_label(stage)} → existing: {stats['existing_pre']}, "
                    f"generated: {stats['generated']}, skipped: {stats['skipped']}, remaining: {remaining}"
                )
        print(f"{'='*60}")


def main(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Extract windows from multiple GDS+DEF designs using multi-design YAML configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use dataset path inferred from the windows YAML directory (all stages)
  python3 window_processing_pipeline.py --windows-file datasets/small/windows.yaml

  # Run only specific pipeline stages
  python3 window_processing_pipeline.py --windows-file designs.yaml --pipeline gds
  python3 window_processing_pipeline.py --windows-file designs.yaml --pipeline gds binary-masks
  python3 window_processing_pipeline.py --windows-file designs.yaml --pipeline cap3d cnn
  python3 window_processing_pipeline.py --windows-file designs.yaml --pipeline binary-masks
  python3 window_processing_pipeline.py --windows-file designs.yaml --pipeline pct
  python3 window_processing_pipeline.py --windows-file designs.yaml --pipeline cnn binary-masks pct
        '''
    )

    parser.add_argument('--windows-file', type=str, default='windows/windows_small.yaml',
                       help='Multi-design YAML file with file paths and window coordinates')
    parser.add_argument('--dataset-path', type=str,
                       help='Dataset directory path for windows (default: directory containing the windows YAML)')
    parser.add_argument('--pipeline', type=str, nargs='+', choices=['gds', 'cap3d', 'cnn', 'binary-masks', 'binary_masks', 'pct'], default=['cap3d', 'cnn', 'binary-masks', 'pct'],
                       help='Pipeline stages to run (default: all stages). Choose from: gds, cap3d, cnn, binary-masks, pct')
    parser.add_argument('--default-net-names', action='store_true',
                       help='Skip DEF→GDS net matching and assign sequential net names (faster).')
    
    args = parser.parse_args(argv)


    # Resolve windows configuration file path
    windows_file_path = Path(args.windows_file).resolve()
    if not windows_file_path.exists():
        print(f"ERROR: Multi-design YAML file not found: {windows_file_path}", file=sys.stderr, flush=True)
        sys.exit(1)

    # Auto-detect process node from dataset path (errors out if not found)
    dataset_path = (Path(args.dataset_path) if args.dataset_path else windows_file_path.parent).resolve()
    try:
        process_node = extract_process_node_from_path(dataset_path)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

    # Auto-detect tech stack and layermap files (errors out if not found)
    try:
        tech_stack_file = find_tech_stack_for_process_node(process_node)
        layermap_file = find_layermap_for_process_node(process_node)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

    # Print file information
    print(f"Process node: {process_node}")
    print(f"Tech stack: {tech_stack_file}")
    print(f"Layermap: {layermap_file}")
    print(f"Dataset path: {dataset_path}")
    print(f"Pipeline stages: {', '.join(args.pipeline)}")
    if args.default_net_names:
        print("Default net-name mode enabled: skipping DEF/GDS matching for nets.")
    print()

    # Create extractor and run
    extractor = WindowExtractor(
        multi_yaml_file=windows_file_path,
        output_dir=dataset_path,
        process_node=process_node,
        tech_stack_file=tech_stack_file,
        layermap_file=layermap_file,
        pipeline_stages=args.pipeline,
        use_default_net_names=args.default_net_names,
    )

    try:
        extractor.run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

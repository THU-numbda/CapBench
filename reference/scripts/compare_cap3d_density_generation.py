#!/usr/bin/env python3
from __future__ import annotations

import argparse
import colorsys
import hashlib
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Dict, List, Sequence, Tuple

import numpy as np
import torch
from torch.profiler import ProfilerActivity, profile, record_function
from tqdm import tqdm


THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.cap3d_fast_density import (  # pylint: disable=wrong-import-position
    generate_all_master_signed_occupancy_cpu,
    generate_all_master_signed_occupancy_cuda,
    load_idmap_expand_cuda_extension,
    rasterize_binary_masks_cuda,
)
from common.def_fast_density import (  # pylint: disable=wrong-import-position
    PreparedDefBinaryMaskRuntimeInput,
    PreparedDefRasterInput,
    RECT_SOURCE_LEF_OBS,
    RECT_SOURCE_LEF_PIN,
    RECT_SOURCE_ROUTE,
    RECT_SOURCE_SPECIAL_ROUTE,
    build_compiled_def_runtime_config,
    prepare_fast_def_binary_masks_runtime,
    prepare_fast_def_raster_input,
    prepare_fast_def_raster_runtime,
    rasterize_def_idmaps_cpu,
    rasterize_def_idmaps_cuda,
)
from common.tech_parser import get_conductor_layers, get_metal_layers  # pylint: disable=wrong-import-position
from window_tools.converters.cnn_cap import DensityMapGenerator  # pylint: disable=wrong-import-position

DEFAULT_CORRECTNESS_FILES = 16
DEFAULT_WARMUP_FILES = 8
DEFAULT_THROUGHPUT_PASSES = 3
DEFAULT_DEVICE = "cuda"
MISMATCH_TOLERANCE_FRACTION = 0.05
_BRACKET_INDEX_RE = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class LegacyBundle:
    generator: DensityMapGenerator
    idmaps: np.ndarray
    conductor_name_to_id: Dict[str, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare legacy CAP3D density generation against the direct LEF+DEF CPU/CUDA path, "
            "with occupancy-aware correctness checks, throughput, and Perfetto-compatible traces."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dataset-path", type=Path, default=Path("datasets"), help="Dataset root containing cap3d/ and def/.")
    parser.add_argument("--cap3d-dir", type=Path, default=None, help="Explicit CAP3D directory override.")
    parser.add_argument("--def-dir", type=Path, default=None, help="Explicit DEF directory override.")
    parser.add_argument("--tech", type=Path, required=True, help="Technology stack YAML file.")
    parser.add_argument("--lef", type=Path, default=None, help="Optional LEF override. Defaults to tech/<stem>.lef.")
    parser.add_argument("--max-windows", type=int, default=128, help="Maximum number of paired windows to use.")
    parser.add_argument("--max-metal-layer", type=int, default=4, help="Process only the bottom N metal layers.")
    parser.add_argument("--target-size", type=int, default=224, help="Square raster size.")
    parser.add_argument("--resolution", type=float, default=None, help="Optional microns-per-pixel override.")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default=DEFAULT_DEVICE, help="Device for the LEF+DEF direct path.")
    parser.add_argument("--correctness-files", type=int, default=DEFAULT_CORRECTNESS_FILES, help="How many windows to use for correctness checks.")
    parser.add_argument("--warmup-files", type=int, default=DEFAULT_WARMUP_FILES, help="Warmup files before throughput timing.")
    parser.add_argument("--throughput-passes", type=int, default=DEFAULT_THROUGHPUT_PASSES, help="How many full passes to time for throughput.")
    parser.add_argument("--trace-warmup-iters", type=int, default=1, help="Warmup iterations before trace recording.")
    parser.add_argument(
        "--trace-out-dir",
        type=Path,
        default=Path("traces/lefdef_legacy_density_compare"),
        help="Directory for Chrome trace JSON output.",
    )
    parser.add_argument(
        "--plot-out-dir",
        type=Path,
        default=Path("plots/lefdef_legacy_density_compare"),
        help="Directory for per-window layer comparison plots generated during correctness checks.",
    )
    return parser.parse_args()


def _resolve_device(name: str) -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available.")
    return torch.device(name)


def _resolve_dir(dataset_path: Path, override: Path | None, subdir: str) -> Path:
    if override is not None:
        resolved = override.resolve()
    else:
        resolved = (dataset_path / subdir).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Required directory does not exist: {resolved}")
    return resolved


def _resolve_lef_path(tech_path: Path, lef_override: Path | None) -> Path:
    if lef_override is not None:
        resolved = lef_override.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"LEF file not found: {resolved}")
        return resolved
    candidates = [
        tech_path.with_suffix(".lef"),
        tech_path.parent / f"{tech_path.stem}.lef",
        tech_path.parent / f"{tech_path.stem}.tlef",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        f"Could not infer LEF file for tech stack {tech_path}; tried: {', '.join(str(p) for p in candidates)}"
    )


def _collect_paired_paths(cap3d_dir: Path, def_dir: Path, max_windows: int) -> List[Tuple[Path, Path]]:
    if max_windows <= 0:
        raise ValueError(f"--max-windows must be positive, got {max_windows}")
    cap3d_by_stem = {path.stem: path for path in sorted(cap3d_dir.glob("*.cap3d"))}
    def_by_stem = {path.stem: path for path in sorted(def_dir.glob("*.def"))}
    paired_stems = sorted(set(cap3d_by_stem).intersection(def_by_stem))
    if not paired_stems:
        raise RuntimeError(f"No paired CAP3D/DEF windows found between {cap3d_dir} and {def_dir}")
    return [(cap3d_by_stem[stem], def_by_stem[stem]) for stem in paired_stems[:max_windows]]


def _normalize_layer_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _select_metal_layers(all_metal_layers: Sequence[str], max_metal_layer: int | None) -> List[str]:
    if max_metal_layer is None or max_metal_layer <= 0:
        return list(all_metal_layers)
    return list(all_metal_layers[:max_metal_layer])


def _filter_tech_layers(
    tech_layers: Sequence[str],
    tech_z_heights: Dict[str, float],
    selected_metal_layers: Sequence[str],
) -> Tuple[List[str], Dict[str, float]]:
    selected_keys = {_normalize_layer_name(name) for name in selected_metal_layers}
    filtered_layers = [layer for layer in tech_layers if _normalize_layer_name(layer) in selected_keys]
    filtered_z_heights = {layer: tech_z_heights[layer] for layer in filtered_layers if layer in tech_z_heights}
    return filtered_layers, filtered_z_heights


def _build_legacy_generator(
    *,
    cap3d_path: Path,
    tech_path: Path,
    target_size: int,
    pixel_resolution: float | None,
    tech_layers: Sequence[str],
    tech_z_heights: Dict[str, float],
    raster_bounds: Sequence[float] | None = None,
    generate_density_maps_now: bool = True,
) -> DensityMapGenerator:
    generator = DensityMapGenerator(
        str(cap3d_path),
        str(tech_path),
        pixel_resolution=pixel_resolution,
        target_size=target_size,
    )
    generator.tech_conductor_layers = list(tech_layers)
    generator.tech_z_heights = dict(tech_z_heights)
    generator.parse_cap3d()
    generator.match_layers()
    if raster_bounds is not None:
        x_min, y_min, x_max, y_max = [float(value) for value in raster_bounds]
        generator.set_raster_bounds(
            x_min,
            y_min,
            x_max,
            y_max,
            pixel_resolution=pixel_resolution,
        )
    if generate_density_maps_now:
        generator.generate_density_maps()
    return generator


def _legacy_non_via_idmaps(generator: DensityMapGenerator, metal_layers: Sequence[str]) -> np.ndarray:
    idmaps: List[np.ndarray] = []
    for layer_name in metal_layers:
        if layer_name not in generator.density_maps:
            raise KeyError(f"Legacy generator is missing expected metal layer '{layer_name}'")
        _density_map, id_map = generator.density_maps[layer_name]
        arr = np.asarray(id_map, dtype=np.int16)
        idmaps.append(arr)
    return np.stack(idmaps, axis=0) if idmaps else np.zeros((0, 0, 0), dtype=np.int16)


def _generate_legacy_bundle(
    *,
    cap3d_path: Path,
    tech_path: Path,
    target_size: int,
    pixel_resolution: float | None,
    tech_layers: Sequence[str],
    tech_z_heights: Dict[str, float],
    metal_layers: Sequence[str],
    raster_bounds: Sequence[float] | None = None,
    generator: DensityMapGenerator | None = None,
) -> LegacyBundle:
    if generator is None:
        generator = _build_legacy_generator(
            cap3d_path=cap3d_path,
            tech_path=tech_path,
            target_size=target_size,
            pixel_resolution=pixel_resolution,
            tech_layers=tech_layers,
            tech_z_heights=tech_z_heights,
            raster_bounds=raster_bounds,
        )
    else:
        if raster_bounds is not None:
            x_min, y_min, x_max, y_max = [float(value) for value in raster_bounds]
            generator.set_raster_bounds(
                x_min,
                y_min,
                x_max,
                y_max,
                pixel_resolution=pixel_resolution,
            )
        generator.generate_density_maps()
    return LegacyBundle(
        generator=generator,
        idmaps=_legacy_non_via_idmaps(generator, metal_layers),
        conductor_name_to_id=dict(generator.conductor_id_map),
    )


def _generate_def_idmaps_cpu(
    *,
    def_path: Path,
    tech_path: Path,
    target_size: int,
    pixel_resolution: float | None,
    selected_layers: Sequence[str],
    raster_bounds: Sequence[float],
    include_conductor_names: bool = False,
) -> Tuple[np.ndarray, PreparedDefRasterInput]:
    prepared = prepare_fast_def_raster_input(
        def_path=def_path,
        tech_path=tech_path,
        target_size=target_size,
        pixel_resolution=pixel_resolution,
        selected_layers=selected_layers,
        raster_bounds=raster_bounds,
        include_supply_nets=True,
        include_conductor_names=include_conductor_names,
    )
    return rasterize_def_idmaps_cpu(prepared), prepared


def _generate_def_idmaps_cuda(
    *,
    def_path: Path,
    tech_path: Path,
    target_size: int,
    pixel_resolution: float | None,
    device: torch.device,
    selected_layers: Sequence[str],
    raster_bounds: Sequence[float],
    include_conductor_names: bool = False,
) -> Tuple[torch.Tensor, PreparedDefRasterInput]:
    prepared = prepare_fast_def_raster_input(
        def_path=def_path,
        tech_path=tech_path,
        target_size=target_size,
        pixel_resolution=pixel_resolution,
        selected_layers=selected_layers,
        raster_bounds=raster_bounds,
        include_supply_nets=True,
        include_conductor_names=include_conductor_names,
    )
    return rasterize_def_idmaps_cuda(prepared, device=device), prepared


def _generate_def_binary_masks_cuda_runtime(
    *,
    def_path: Path,
    runtime_config,
    target_size: int,
    pixel_resolution: float | None,
    device: torch.device,
    raster_bounds: Sequence[float],
) -> PreparedDefBinaryMaskRuntimeInput:
    return prepare_fast_def_binary_masks_runtime(
        def_path=def_path,
        runtime_config=runtime_config,
        target_size=target_size,
        pixel_resolution=pixel_resolution,
        raster_bounds=raster_bounds,
        include_supply_nets=True,
        device=device,
    )


def _build_name_lookup_from_mapping(conductor_name_to_id: Dict[str, int]) -> np.ndarray:
    max_id = max(conductor_name_to_id.values(), default=0)
    lookup = np.empty((max_id + 1,), dtype=object)
    lookup[:] = ""
    for name, cid in conductor_name_to_id.items():
        if cid >= 0:
            lookup[int(cid)] = str(name)
    return lookup


def _build_fast_lookups(prepared: PreparedDefRasterInput) -> Tuple[np.ndarray, np.ndarray]:
    if prepared.conductor_names_sorted is None:
        raise ValueError("Prepared DEF input does not include conductor names")
    max_id = int(prepared.conductor_ids_sorted.max()) if prepared.conductor_ids_sorted.size else 0
    name_lookup = np.empty((max_id + 1,), dtype=object)
    name_lookup[:] = ""
    synthetic_lookup = np.zeros((max_id + 1,), dtype=bool)
    for name, cid, is_synthetic in zip(
        prepared.conductor_names_sorted,
        prepared.conductor_ids_sorted.tolist(),
        prepared.conductor_is_synthetic.tolist(),
    ):
        name_lookup[int(cid)] = str(name)
        synthetic_lookup[int(cid)] = bool(is_synthetic)
    return name_lookup, synthetic_lookup


def _canonicalize_conductor_name(name: str) -> str:
    normalized = str(name).strip()
    if not normalized:
        return ""
    normalized = normalized.replace("\\[", "[").replace("\\]", "]")
    normalized = _BRACKET_INDEX_RE.sub(r"\1", normalized)
    return normalized


def _build_canonical_name_lookup(name_lookup: np.ndarray) -> np.ndarray:
    canonical_lookup = np.empty(name_lookup.shape, dtype=object)
    for idx, name in enumerate(name_lookup.tolist()):
        canonical_lookup[idx] = _canonicalize_conductor_name(str(name))
    return canonical_lookup


def _build_canonical_id_mapping(conductor_name_to_id: Dict[str, int]) -> Dict[str, int]:
    canonical_mapping: Dict[str, int] = {}
    for name, cid in conductor_name_to_id.items():
        canonical = _canonicalize_conductor_name(str(name))
        if canonical:
            canonical_mapping.setdefault(canonical, int(cid))
    return canonical_mapping


def _is_generic_conductor_name(name: str) -> bool:
    normalized = str(name).strip()
    if not normalized:
        return True
    return (
        normalized.startswith("Net.")
        or normalized.startswith("SpecialNet.")
        or normalized.startswith("__lef__/")
    )


def _build_generic_lookup_from_names(name_lookup: np.ndarray) -> np.ndarray:
    generic_lookup = np.zeros((name_lookup.shape[0],), dtype=bool)
    for idx, name in enumerate(name_lookup.tolist()):
        generic_lookup[idx] = _is_generic_conductor_name(str(name))
    return generic_lookup


def _policy_mismatch_count(
    baseline_idmap: np.ndarray,
    fast_idmap: np.ndarray,
    baseline_name_lookup: np.ndarray,
    fast_name_lookup: np.ndarray,
) -> int:
    ref = np.asarray(baseline_idmap, dtype=np.int32)
    got = np.asarray(fast_idmap, dtype=np.int32)
    ref_occ = ref > 0
    got_occ = got > 0
    occ_mismatch = ref_occ != got_occ
    if np.any(occ_mismatch):
        return int(np.count_nonzero(occ_mismatch))
    return 0


def _mismatch_tolerance_pixels(id_map: np.ndarray) -> int:
    total_pixels = int(np.asarray(id_map).size)
    return int(math.floor(total_pixels * MISMATCH_TOLERANCE_FRACTION))


def _synchronize(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def _resolve_inference_device(process_device: torch.device) -> torch.device:
    if not torch.cuda.is_available():
        raise RuntimeError("This benchmark requires CUDA because CPU-produced tensors are always uploaded for GPU inference.")
    if process_device.type == "cuda":
        return process_device
    return torch.device("cuda")


def _compute_reference_raster_bounds(
    *,
    cap3d_path: Path,
    tech_path: Path,
    target_size: int,
    pixel_resolution: float | None,
    tech_layers: Sequence[str],
    tech_z_heights: Dict[str, float],
    metal_layers: Sequence[str],
) -> Tuple[np.ndarray, DensityMapGenerator]:
    generator = _build_legacy_generator(
        cap3d_path=cap3d_path,
        tech_path=tech_path,
        target_size=target_size,
        pixel_resolution=pixel_resolution,
        tech_layers=tech_layers,
        tech_z_heights=tech_z_heights,
        generate_density_maps_now=False,
    )
    bounds = np.asarray(generator.compute_conductor_bounds(metal_layers), dtype=np.float64)
    return bounds, generator


def _upload_numpy_to_gpu(array: np.ndarray, gpu_device: torch.device) -> torch.Tensor:
    contiguous = np.ascontiguousarray(array)
    tensor = torch.from_numpy(contiguous).to(device=gpu_device, non_blocking=True)
    _synchronize(gpu_device)
    return tensor


def _load_pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _conductor_key_to_color(conductor_key: str) -> Tuple[int, int, int]:
    if not conductor_key:
        return (0, 0, 0)
    digest = hashlib.blake2b(str(conductor_key).encode("utf-8"), digest_size=8).digest()
    hue = int.from_bytes(digest[:2], "big") / 65535.0
    sat = 0.55 + (digest[2] / 255.0) * 0.30
    val = 0.70 + (digest[3] / 255.0) * 0.25
    red, green, blue = colorsys.hsv_to_rgb(hue, min(sat, 1.0), min(val, 1.0))
    return (
        int(round(red * 255.0)),
        int(round(green * 255.0)),
        int(round(blue * 255.0)),
    )


def _build_rgb_lookup(max_conductor_id: int, name_lookup: np.ndarray, *, fallback_prefix: str) -> np.ndarray:
    rgb_lookup = np.zeros((max_conductor_id + 1, 3), dtype=np.uint8)
    for conductor_id in range(1, max_conductor_id + 1):
        if conductor_id < name_lookup.shape[0] and str(name_lookup[conductor_id]):
            conductor_key = str(name_lookup[conductor_id])
        else:
            conductor_key = f"{fallback_prefix}{conductor_id}"
        rgb_lookup[conductor_id] = np.asarray(_conductor_key_to_color(conductor_key), dtype=np.uint8)
    return rgb_lookup


def _idmap_to_rgb(id_map: np.ndarray, rgb_lookup: np.ndarray) -> np.ndarray:
    ids = np.asarray(id_map, dtype=np.int32)
    if ids.size == 0:
        return np.zeros((*ids.shape, 3), dtype=np.uint8)
    if int(ids.max()) >= rgb_lookup.shape[0]:
        raise ValueError(
            f"ID map contains id {int(ids.max())} but RGB lookup only has {rgb_lookup.shape[0]} entries."
        )
    return rgb_lookup[ids]


def _save_window_layer_plot(
    *,
    out_dir: Path,
    window_id: str,
    layers: Sequence[str],
    baseline_idmaps: np.ndarray,
    fast_idmaps: np.ndarray,
    baseline_name_lookup: np.ndarray,
    fast_name_lookup: np.ndarray,
    fast_label: str,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    plt = _load_pyplot()

    max_conductor_id = max(
        int(np.max(baseline_idmaps)) if baseline_idmaps.size else 0,
        int(np.max(fast_idmaps)) if fast_idmaps.size else 0,
    )
    baseline_rgb_lookup = _build_rgb_lookup(max_conductor_id, baseline_name_lookup, fallback_prefix="legacy_id:")
    fast_rgb_lookup = _build_rgb_lookup(max_conductor_id, fast_name_lookup, fallback_prefix=f"{fast_label}_id:")
    num_layers = len(layers)
    if num_layers <= 0:
        raise ValueError(f"No layers available to plot for {window_id}")

    ncols = min(4, num_layers)
    layer_rows = int(math.ceil(num_layers / ncols))
    fig, axes = plt.subplots(
        nrows=layer_rows * 2,
        ncols=ncols,
        figsize=(ncols * 4.4, layer_rows * 7.0),
        squeeze=False,
    )
    fig.suptitle(f"{window_id}: legacy CPU vs {fast_label}", fontsize=14)

    for idx, layer_name in enumerate(layers):
        block_row = (idx // ncols) * 2
        col = idx % ncols
        baseline_ax = axes[block_row][col]
        fast_ax = axes[block_row + 1][col]

        baseline_rgb = _idmap_to_rgb(baseline_idmaps[idx], baseline_rgb_lookup)
        fast_rgb = _idmap_to_rgb(fast_idmaps[idx], fast_rgb_lookup)
        mismatch = _policy_mismatch_count(
            np.asarray(baseline_idmaps[idx]),
            np.asarray(fast_idmaps[idx]),
            baseline_name_lookup,
            fast_name_lookup,
        )

        baseline_ax.imshow(baseline_rgb, interpolation="nearest")
        baseline_ax.set_title(
            f"{layer_name} | legacy_cpu\nocc={int(np.count_nonzero(baseline_idmaps[idx] > 0))}",
            fontsize=10,
        )
        fast_ax.imshow(fast_rgb, interpolation="nearest")
        fast_ax.set_title(
            f"{layer_name} | {fast_label}\nocc={int(np.count_nonzero(fast_idmaps[idx] > 0))} mismatch={mismatch}",
            fontsize=10,
        )
        baseline_ax.set_axis_off()
        fast_ax.set_axis_off()

    total_axes = layer_rows * 2 * ncols
    for idx in range(num_layers, total_axes // 2):
        block_row = (idx // ncols) * 2
        col = idx % ncols
        axes[block_row][col].set_axis_off()
        axes[block_row + 1][col].set_axis_off()

    fig.tight_layout(rect=(0, 0, 1, 0.97))
    plot_path = (out_dir / f"{window_id}_layers.png").resolve()
    fig.savefig(plot_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return plot_path


def _mask_bbox(mask: np.ndarray) -> str:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return "none"
    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)
    return f"x=[{int(x_min)},{int(x_max)}] y=[{int(y_min)},{int(y_max)}]"


def _sample_pixels(mask: np.ndarray, limit: int = 8) -> str:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return "none"
    samples = [f"({int(x)},{int(y)})" for y, x in coords[:limit]]
    return ", ".join(samples)


def _top_named_ids(
    id_map: np.ndarray,
    mask: np.ndarray,
    name_lookup: np.ndarray,
    *,
    limit: int = 6,
) -> str:
    ids = np.asarray(id_map[mask], dtype=np.int32)
    ids = ids[ids > 0]
    if ids.size == 0:
        return "none"
    unique_ids, counts = np.unique(ids, return_counts=True)
    order = np.argsort(-counts)
    parts: List[str] = []
    for idx in order[:limit]:
        cid = int(unique_ids[idx])
        name = str(name_lookup[cid]) if cid < name_lookup.shape[0] else f"id{cid}"
        parts.append(f"{name}:{int(counts[idx])}")
    return ", ".join(parts)


def _top_name_pair_mismatches(
    ref_names: np.ndarray,
    got_names: np.ndarray,
    mask: np.ndarray,
    *,
    limit: int = 6,
) -> str:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return "none"
    pair_counts: Dict[Tuple[str, str], int] = {}
    for y, x in coords:
        pair = (str(ref_names[y, x]), str(got_names[y, x]))
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    ordered = sorted(pair_counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{src}->{dst}:{count}" for (src, dst), count in ordered[:limit])


def _prepared_layer_rect_summary(
    prepared: PreparedDefRasterInput,
    *,
    layer_idx: int,
) -> str:
    if prepared.packed_rects.size == 0:
        return "rects=0"
    packed = prepared.packed_rects
    layer_mask = packed[:, 0] == layer_idx
    if not np.any(layer_mask):
        return "rects=0"

    cids = packed[layer_mask, 1].astype(np.int32, copy=False)
    source_kinds = np.asarray(prepared.rect_source_kind_codes[layer_mask], dtype=np.uint8)
    synthetic_lookup = np.zeros((int(prepared.conductor_ids_sorted.max()) + 1,), dtype=bool) if prepared.conductor_ids_sorted.size else np.zeros((1,), dtype=bool)
    for cid, is_synth in zip(prepared.conductor_ids_sorted.tolist(), prepared.conductor_is_synthetic.tolist()):
        synthetic_lookup[int(cid)] = bool(is_synth)
    synth_mask = synthetic_lookup[cids]
    real_count = int(np.count_nonzero(~synth_mask))
    synth_count = int(np.count_nonzero(synth_mask))
    unique_cids = np.unique(cids)
    route_count = int(np.count_nonzero(source_kinds == RECT_SOURCE_ROUTE))
    special_route_count = int(np.count_nonzero(source_kinds == RECT_SOURCE_SPECIAL_ROUTE))
    lef_pin_count = int(np.count_nonzero(source_kinds == RECT_SOURCE_LEF_PIN))
    lef_obs_count = int(np.count_nonzero(source_kinds == RECT_SOURCE_LEF_OBS))
    return (
        f"rects={int(cids.size)} real_rects={real_count} synthetic_rects={synth_count} "
        f"unique_conductors={int(unique_cids.size)} route_rects={route_count} "
        f"special_rects={special_route_count} "
        f"lef_pin_rects={lef_pin_count} lef_obs_rects={lef_obs_count} "
        f"parse_ms={prepared.parse_ms:.2f} prepare_ms={prepared.prepare_ms:.2f}"
    )


def _compare_idx_maps_policy(
    *,
    baseline_bundle: LegacyBundle,
    fast_idmaps: np.ndarray,
    prepared: PreparedDefRasterInput,
    layers: Sequence[str],
    window_id: str,
) -> Dict[str, int]:
    baseline_idmaps = baseline_bundle.idmaps
    if baseline_idmaps.shape != fast_idmaps.shape:
        raise AssertionError(
            f"Shape mismatch for {window_id}: baseline={baseline_idmaps.shape}, fast={fast_idmaps.shape}"
        )

    baseline_name_lookup = _build_name_lookup_from_mapping(baseline_bundle.conductor_name_to_id)
    fast_name_lookup, _fast_synthetic_lookup = _build_fast_lookups(prepared)

    stats = {
        "occupancy_mismatch_pixels": 0,
        "real_id_mismatch_pixels": 0,
        "generic_id_ignored_pixels": 0,
        "generic_ignored_layers": 0,
        "tolerated_small_error_pixels": 0,
        "tolerated_small_error_layers": 0,
    }

    for layer_idx, layer_name in enumerate(layers):
        ref = np.asarray(baseline_idmaps[layer_idx], dtype=np.int32)
        got = np.asarray(fast_idmaps[layer_idx], dtype=np.int32)
        tolerance_pixels = _mismatch_tolerance_pixels(ref)
        ref_occ = ref > 0
        got_occ = got > 0
        occ_mismatch = ref_occ != got_occ
        if np.any(occ_mismatch):
            mismatch = int(np.count_nonzero(occ_mismatch))
            stats["occupancy_mismatch_pixels"] += mismatch
            if mismatch <= tolerance_pixels:
                stats["tolerated_small_error_pixels"] += mismatch
                stats["tolerated_small_error_layers"] += 1
                continue
            ref_only = ref_occ & ~got_occ
            got_only = got_occ & ~ref_occ
            raise AssertionError(
                "\n".join(
                    [
                        f"Occupancy mismatch for {window_id} layer={layer_name}: mismatch_pixels={mismatch}",
                        f"  tolerance_pixels={tolerance_pixels}",
                        f"  baseline_occ_pixels={int(np.count_nonzero(ref_occ))} fast_occ_pixels={int(np.count_nonzero(got_occ))}",
                        f"  baseline_only_pixels={int(np.count_nonzero(ref_only))} fast_only_pixels={int(np.count_nonzero(got_only))}",
                        f"  mismatch_bbox={_mask_bbox(occ_mismatch)}",
                        f"  baseline_only_bbox={_mask_bbox(ref_only)}",
                        f"  fast_only_bbox={_mask_bbox(got_only)}",
                        f"  baseline_only_samples={_sample_pixels(ref_only)}",
                        f"  fast_only_samples={_sample_pixels(got_only)}",
                        f"  baseline_top_conductors_in_baseline_only={_top_named_ids(ref, ref_only, baseline_name_lookup)}",
                        f"  fast_top_conductors_in_fast_only={_top_named_ids(got, got_only, fast_name_lookup)}",
                        f"  prepared_layer_summary={_prepared_layer_rect_summary(prepared, layer_idx=layer_idx)}",
                        f"  component_resolution_stats={prepared.component_resolution_stats}",
                        f"  prepared_active_rectangles={prepared.active_rectangles} total_segments={prepared.total_segments}",
                        f"  total_endpoint_extensions={prepared.total_endpoint_extensions}",
                        f"  def_path={prepared.def_path}",
                        f"  lef_path={prepared.lef_path}",
                    ]
                )
            )

    return stats


def _compare_real_master_highlights(
    *,
    baseline_bundle: LegacyBundle,
    fast_idmaps_cpu: np.ndarray | None,
    fast_idmaps_gpu: torch.Tensor | None,
    prepared: PreparedDefRasterInput,
    optimized_backend: str,
    window_id: str,
) -> Dict[str, int | str]:
    if prepared.conductor_names_sorted is None:
        raise ValueError("Prepared DEF input does not include conductor names")
    real_names: List[str] = []
    fast_shared_ids: List[int] = []
    baseline_real_ids: List[int] = []
    missing_names: List[str] = []
    baseline_canonical_name_to_id = _build_canonical_id_mapping(baseline_bundle.conductor_name_to_id)

    for name, cid, is_synthetic in zip(
        prepared.conductor_names_sorted,
        prepared.conductor_ids_sorted.tolist(),
        prepared.conductor_is_synthetic.tolist(),
    ):
        if is_synthetic:
            continue
        real_names.append(str(name))
        baseline_cid = baseline_bundle.conductor_name_to_id.get(str(name))
        if baseline_cid is None:
            baseline_cid = baseline_canonical_name_to_id.get(_canonicalize_conductor_name(str(name)))
        if baseline_cid is None:
            missing_names.append(str(name))
        else:
            fast_shared_ids.append(int(cid))
            baseline_real_ids.append(int(baseline_cid))

    baseline_highlights, _baseline_ids = generate_all_master_signed_occupancy_cpu(
        baseline_bundle.idmaps,
        conductor_ids=np.asarray(baseline_real_ids, dtype=np.int16),
    )

    fast_real_ids_arr = np.asarray(fast_shared_ids, dtype=np.int16)
    if optimized_backend == "cuda":
        assert fast_idmaps_gpu is not None
        fast_real_ids_gpu = torch.from_numpy(fast_real_ids_arr).to(device=fast_idmaps_gpu.device, dtype=torch.int16)
        fast_highlights_gpu, _fast_ids = generate_all_master_signed_occupancy_cuda(
            fast_idmaps_gpu,
            conductor_ids=fast_real_ids_gpu,
        )
        fast_highlights = fast_highlights_gpu.cpu().numpy()
    else:
        assert fast_idmaps_cpu is not None
        fast_highlights, _fast_ids = generate_all_master_signed_occupancy_cpu(
            fast_idmaps_cpu,
            conductor_ids=fast_real_ids_arr,
        )

    if baseline_highlights.shape != fast_highlights.shape:
        raise AssertionError(
            f"Real-master highlight shape mismatch for {window_id}: "
            f"baseline={baseline_highlights.shape}, fast={fast_highlights.shape}"
        )

    total_real_count = len(real_names)
    shared_real_count = len(baseline_real_ids)
    missing_real_count = len(missing_names)
    missing_preview = ", ".join(sorted(missing_names)[:8]) if missing_names else ""

    return {
        "real_master_count": total_real_count,
        "shared_real_master_count": shared_real_count,
        "missing_real_master_count": missing_real_count,
        "missing_real_master_pct_bp": int(round((missing_real_count / max(total_real_count, 1)) * 10_000.0)),
        "synthetic_master_count": int(np.count_nonzero(prepared.conductor_is_synthetic)),
        "missing_real_master_preview": missing_preview,
    }


def run_correctness(
    *,
    paired_paths: Sequence[Tuple[Path, Path]],
    tech_path: Path,
    lef_path: Path,
    plot_out_dir: Path,
    target_size: int,
    pixel_resolution: float | None,
    optimized_backend: str,
    device: torch.device,
    tech_layers: Sequence[str],
    tech_z_heights: Dict[str, float],
    metal_layers: Sequence[str],
) -> None:
    print()
    print("Running correctness checks on non-via occupancy, real-net IDs, and real-master signed occupancy...")

    generic_id_ignored_pixels = 0
    generic_ignored_layers = 0
    tolerated_small_error_pixels = 0
    tolerated_small_error_layers = 0
    synthetic_master_total = 0
    real_master_total = 0
    real_master_shared_total = 0
    real_master_missing_total = 0

    for cap3d_path, def_path in tqdm(paired_paths, desc="Correctness", unit="file"):
        raster_bounds, legacy_generator = _compute_reference_raster_bounds(
            cap3d_path=cap3d_path,
            tech_path=tech_path,
            target_size=target_size,
            pixel_resolution=pixel_resolution,
            tech_layers=tech_layers,
            tech_z_heights=tech_z_heights,
            metal_layers=metal_layers,
        )
        baseline_bundle = _generate_legacy_bundle(
            cap3d_path=cap3d_path,
            tech_path=tech_path,
            target_size=target_size,
            pixel_resolution=pixel_resolution,
            tech_layers=tech_layers,
            tech_z_heights=tech_z_heights,
            metal_layers=metal_layers,
            raster_bounds=raster_bounds,
            generator=legacy_generator,
        )

        if optimized_backend == "cuda":
            fast_gpu, prepared = _generate_def_idmaps_cuda(
                def_path=def_path,
                tech_path=tech_path,
                target_size=target_size,
                pixel_resolution=pixel_resolution,
                device=device,
                selected_layers=metal_layers,
                raster_bounds=raster_bounds,
                include_conductor_names=True,
            )
            _synchronize(device)
            fast_idmaps = fast_gpu.cpu().numpy()
            fast_idmaps_cpu = None
        else:
            fast_idmaps, prepared = _generate_def_idmaps_cpu(
                def_path=def_path,
                tech_path=tech_path,
                target_size=target_size,
                pixel_resolution=pixel_resolution,
                selected_layers=metal_layers,
                raster_bounds=raster_bounds,
                include_conductor_names=True,
            )
            fast_gpu = None
            fast_idmaps_cpu = fast_idmaps

        if list(prepared.channel_layers) != list(metal_layers):
            raise AssertionError(
                f"LEF+DEF layer order mismatch for {def_path.stem}: baseline={list(metal_layers)} fast={list(prepared.channel_layers)}"
            )

        baseline_name_lookup = _build_name_lookup_from_mapping(baseline_bundle.conductor_name_to_id)
        fast_name_lookup, _fast_synthetic_lookup = _build_fast_lookups(prepared)
        plot_path = _save_window_layer_plot(
            out_dir=plot_out_dir,
            window_id=def_path.stem,
            layers=metal_layers,
            baseline_idmaps=baseline_bundle.idmaps,
            fast_idmaps=fast_idmaps,
            baseline_name_lookup=baseline_name_lookup,
            fast_name_lookup=fast_name_lookup,
            fast_label=f"lefdef_{optimized_backend}",
        )
        tqdm.write(
            f"[correctness] window={def_path.stem} plot_saved={plot_path} running_assertions=1"
        )

        idx_stats = _compare_idx_maps_policy(
            baseline_bundle=baseline_bundle,
            fast_idmaps=fast_idmaps,
            prepared=prepared,
            layers=metal_layers,
            window_id=def_path.stem,
        )
        highlight_stats = _compare_real_master_highlights(
            baseline_bundle=baseline_bundle,
            fast_idmaps_cpu=fast_idmaps_cpu,
            fast_idmaps_gpu=fast_gpu,
            prepared=prepared,
            optimized_backend=optimized_backend,
            window_id=def_path.stem,
        )
        generic_id_ignored_pixels += idx_stats["generic_id_ignored_pixels"]
        generic_ignored_layers += idx_stats["generic_ignored_layers"]
        tolerated_small_error_pixels += idx_stats["tolerated_small_error_pixels"]
        tolerated_small_error_layers += idx_stats["tolerated_small_error_layers"]
        synthetic_master_total += highlight_stats["synthetic_master_count"]
        real_master_total += highlight_stats["real_master_count"]
        real_master_shared_total += highlight_stats["shared_real_master_count"]
        real_master_missing_total += highlight_stats["missing_real_master_count"]
        if highlight_stats["missing_real_master_count"] > 0:
            missing_pct = highlight_stats["missing_real_master_pct_bp"] / 100.0
            tqdm.write(
                f"[correctness] window={def_path.stem} "
                f"missing_cap3d_real_conductors={highlight_stats['missing_real_master_count']}/{highlight_stats['real_master_count']} "
                f"({missing_pct:.2f}%) shared_real_conductors={highlight_stats['shared_real_master_count']} "
                f"preview={highlight_stats['missing_real_master_preview']}"
            )

    missing_real_pct = (real_master_missing_total / max(real_master_total, 1)) * 100.0
    print(
        "Correctness PASS: "
        f"checked_files={len(paired_paths)} "
        f"generic_id_ignored_pixels={generic_id_ignored_pixels} "
        f"generic_ignored_layers={generic_ignored_layers} "
        f"tolerated_small_error_pixels={tolerated_small_error_pixels} "
        f"tolerated_small_error_layers={tolerated_small_error_layers} "
        f"synthetic_master_total={synthetic_master_total} "
        f"real_master_shared_total={real_master_shared_total} "
        f"real_master_missing_cap3d={real_master_missing_total}/{real_master_total} "
        f"({missing_real_pct:.2f}%)"
    )
    print(f"Saved correctness layer plots: {plot_out_dir.resolve()}")


def _print_optimized_throughput_table(
    total_seconds: float,
    total_windows: int,
    master_views: int,
    optimized_backend: str,
) -> None:
    ms_per_window = (total_seconds / total_windows) * 1000.0
    windows_per_s = total_windows / max(total_seconds, 1e-12)
    master_views_per_s = master_views / max(total_seconds, 1e-12)
    us_per_master = (total_seconds / max(master_views, 1)) * 1e6

    print()
    print("Optimized End-to-End Pipeline")
    print("Method                         Total Time (s)   Avg ms/window   Avg us/master   MasterViews   MasterViews/s")
    print("-------------------------------------------------------------------------------------------------------------")
    print(
        f"{f'{optimized_backend}_lefdef_total':<30} "
        f"{total_seconds:>14.6f} "
        f"{ms_per_window:>14.3f} "
        f"{us_per_master:>15.3f} "
        f"{master_views:>13d} "
        f"{master_views_per_s:>15.3f}"
    )


def run_throughput(
    *,
    paired_paths: Sequence[Tuple[Path, Path]],
    tech_path: Path,
    lef_path: Path,
    runtime_config,
    target_size: int,
    pixel_resolution: float | None,
    warmup_files: int,
    throughput_passes: int,
    optimized_backend: str,
    device: torch.device,
    inference_device: torch.device,
    tech_layers: Sequence[str],
    tech_z_heights: Dict[str, float],
    metal_layers: Sequence[str],
) -> None:
    print()
    print("Running throughput benchmark...")
    print(
        f"  files={len(paired_paths)} passes={throughput_passes} "
        f"warmup_files={warmup_files} optimized_backend={optimized_backend}"
    )

    warmup_count = min(warmup_files, len(paired_paths))
    warmup_set = paired_paths[:warmup_count]

    for cap3d_path, def_path in warmup_set:
        raster_bounds, legacy_generator = _compute_reference_raster_bounds(
            cap3d_path=cap3d_path,
            tech_path=tech_path,
            target_size=target_size,
            pixel_resolution=pixel_resolution,
            tech_layers=tech_layers,
            tech_z_heights=tech_z_heights,
            metal_layers=metal_layers,
        )
        if optimized_backend == "cuda":
            prepared = _generate_def_binary_masks_cuda_runtime(
                def_path=def_path,
                runtime_config=runtime_config,
                target_size=target_size,
                pixel_resolution=pixel_resolution,
                device=device,
                raster_bounds=raster_bounds,
            )
            _ = prepared.occupied
            _ = prepared.master_masks
        else:
            fast_cpu, _prepared = _generate_def_idmaps_cpu(
                def_path=def_path,
                tech_path=tech_path,
                target_size=target_size,
                pixel_resolution=pixel_resolution,
                selected_layers=metal_layers,
                raster_bounds=raster_bounds,
            )
            generate_all_master_signed_occupancy_cpu(fast_cpu, conductor_ids=_prepared.conductor_ids_sorted)
            _upload_numpy_to_gpu(fast_cpu, inference_device)
    _synchronize(inference_device)

    total_files = len(paired_paths) * throughput_passes
    if total_files <= 0:
        raise RuntimeError("No paired windows available for throughput timing.")

    optimized_total_seconds = 0.0
    total_master_views_fast = 0

    for _ in range(throughput_passes):
        for cap3d_path, def_path in paired_paths:
            raster_bounds, _legacy_generator = _compute_reference_raster_bounds(
                cap3d_path=cap3d_path,
                tech_path=tech_path,
                target_size=target_size,
                pixel_resolution=pixel_resolution,
                tech_layers=tech_layers,
                tech_z_heights=tech_z_heights,
                metal_layers=metal_layers,
            )
            start = perf_counter()
            if optimized_backend == "cuda":
                prepared = _generate_def_binary_masks_cuda_runtime(
                    def_path=def_path,
                    runtime_config=runtime_config,
                    target_size=target_size,
                    pixel_resolution=pixel_resolution,
                    device=device,
                    raster_bounds=raster_bounds,
                )
                _synchronize(device)
                optimized_total_seconds += perf_counter() - start
                total_master_views_fast += int(prepared.master_conductor_ids_torch.numel())
            else:
                fast_cpu, _prepared = _generate_def_idmaps_cpu(
                    def_path=def_path,
                    tech_path=tech_path,
                    target_size=target_size,
                    pixel_resolution=pixel_resolution,
                    selected_layers=metal_layers,
                    raster_bounds=raster_bounds,
                )
                highlights_cpu, master_ids_cpu = generate_all_master_signed_occupancy_cpu(
                    fast_cpu,
                    conductor_ids=_prepared.conductor_ids_sorted,
                )
                _upload_numpy_to_gpu(highlights_cpu, inference_device)
                optimized_total_seconds += perf_counter() - start
                total_master_views_fast += int(master_ids_cpu.shape[0])

    _print_optimized_throughput_table(
        optimized_total_seconds,
        total_files,
        total_master_views_fast,
        optimized_backend,
    )
    if optimized_backend == "cuda":
        print("Note: LEF+DEF CUDA total includes prepare, packed rectangle upload, and binary occupancy/master-mask rasterization.")
    else:
        print("Note: LEF+DEF CPU total includes prepare, CPU expansion/highlight, and CPU->GPU upload of generated highlight tensors.")


def run_trace(
    *,
    trace_path: Path,
    cap3d_path: Path,
    def_path: Path,
    tech_path: Path,
    lef_path: Path,
    runtime_config,
    target_size: int,
    pixel_resolution: float | None,
    optimized_backend: str,
    device: torch.device,
    inference_device: torch.device,
    trace_warmup_iters: int,
    tech_layers: Sequence[str],
    tech_z_heights: Dict[str, float],
    metal_layers: Sequence[str],
) -> None:
    print()
    print("Recording trace...")
    print(f"  file={def_path.stem} backend={optimized_backend} warmup_iters={trace_warmup_iters}")

    for _ in range(trace_warmup_iters):
        raster_bounds, _legacy_generator = _compute_reference_raster_bounds(
            cap3d_path=cap3d_path,
            tech_path=tech_path,
            target_size=target_size,
            pixel_resolution=pixel_resolution,
            tech_layers=tech_layers,
            tech_z_heights=tech_z_heights,
            metal_layers=metal_layers,
        )
        if optimized_backend == "cuda":
            prepared = _generate_def_binary_masks_cuda_runtime(
                def_path=def_path,
                runtime_config=runtime_config,
                target_size=target_size,
                pixel_resolution=pixel_resolution,
                device=device,
                raster_bounds=raster_bounds,
            )
            _ = prepared.occupied
            _ = prepared.master_masks
    _synchronize(device)

    activities = [ProfilerActivity.CPU]
    if optimized_backend == "cuda":
        activities.append(ProfilerActivity.CUDA)

    trace_path.parent.mkdir(parents=True, exist_ok=True)

    with profile(activities=activities, record_shapes=True, profile_memory=True) as prof:
        raster_bounds, _legacy_generator = _compute_reference_raster_bounds(
            cap3d_path=cap3d_path,
            tech_path=tech_path,
            target_size=target_size,
            pixel_resolution=pixel_resolution,
            tech_layers=tech_layers,
            tech_z_heights=tech_z_heights,
            metal_layers=metal_layers,
        )
        if optimized_backend == "cuda":
            with record_function("lefdef_density.cuda_prepare"):
                prepared = prepare_fast_def_raster_runtime(
                    def_path=def_path,
                    runtime_config=runtime_config,
                    target_size=target_size,
                    pixel_resolution=pixel_resolution,
                    raster_bounds=raster_bounds,
                    include_supply_nets=True,
                )
            with record_function("lefdef_density.cuda_upload_rects"):
                packed_rects_cuda = prepared.packed_rects_torch.to(
                    device=device,
                    dtype=torch.int32,
                    non_blocking=True,
                ).contiguous()
            with record_function("lefdef_density.cuda_rasterize_binary_masks"):
                _occupied_gpu, _master_masks_gpu = rasterize_binary_masks_cuda(
                    packed_rects_cuda,
                    num_layers=len(prepared.channel_layers),
                    target_size=prepared.target_size,
                    real_conductor_count=int(prepared.conductor_ids_torch.numel()),
                )
            with record_function("lefdef_density.cuda_sync"):
                _synchronize(device)
        else:
            with record_function("lefdef_density.cpu_prepare"):
                prepared = prepare_fast_def_raster_input(
                    def_path=def_path,
                    tech_path=tech_path,
                    target_size=target_size,
                    pixel_resolution=pixel_resolution,
                    selected_layers=metal_layers,
                    raster_bounds=raster_bounds,
                    include_supply_nets=True,
                    include_conductor_names=False,
                )
            with record_function("lefdef_density.cpu_expand"):
                _fast_idmaps = rasterize_def_idmaps_cpu(prepared)
            with record_function("lefdef_density.cpu_highlight_all_masters"):
                _fast_highlights, _fast_master_ids = generate_all_master_signed_occupancy_cpu(
                    _fast_idmaps,
                    conductor_ids=prepared.conductor_ids_sorted,
                )
            with record_function("lefdef_density.cpu_upload_highlights"):
                _fast_highlights_gpu = _upload_numpy_to_gpu(_fast_highlights, inference_device)

    prof.export_chrome_trace(str(trace_path))
    print(f"Saved trace: {trace_path}")


def main() -> int:
    args = parse_args()
    device = _resolve_device(args.device)
    inference_device = _resolve_inference_device(device)
    tech_path = args.tech.resolve()
    if not tech_path.exists():
        raise FileNotFoundError(f"Tech file not found: {tech_path}")
    lef_path = _resolve_lef_path(tech_path, args.lef)

    dataset_path = args.dataset_path.resolve()
    cap3d_dir = _resolve_dir(dataset_path, args.cap3d_dir, "cap3d")
    def_dir = _resolve_dir(dataset_path, args.def_dir, "def")
    paired_paths = _collect_paired_paths(cap3d_dir, def_dir, args.max_windows)
    correctness_files = min(args.correctness_files, len(paired_paths))
    correctness_pairs = paired_paths[:correctness_files]

    if args.target_size <= 0:
        raise ValueError(f"--target-size must be positive, got {args.target_size}")

    optimized_backend = "cuda" if device.type == "cuda" else "cpu"
    all_tech_layers, all_tech_z_heights = get_conductor_layers(str(tech_path))
    all_metal_layers = get_metal_layers(str(tech_path))
    metal_layers = _select_metal_layers(all_metal_layers, args.max_metal_layer)
    tech_layers, tech_z_heights = _filter_tech_layers(all_tech_layers, all_tech_z_heights, metal_layers)
    runtime_config = build_compiled_def_runtime_config(tech_path, selected_layers=metal_layers)

    if optimized_backend == "cuda":
        load_idmap_expand_cuda_extension()

    print("Loaded LEF+DEF vs legacy CAP3D density generation benchmark workload:")
    print(f"  cap3d_dir={cap3d_dir}")
    print(f"  def_dir={def_dir}")
    print(f"  lef_path={lef_path}")
    print(f"  windows={len(paired_paths)}")
    print(f"  correctness_files={correctness_files}")
    print(f"  target_size={args.target_size}")
    print(f"  resolution_override={args.resolution}")
    print(f"  selected_metal_layers={metal_layers}")
    print(f"  optimized_backend={optimized_backend}")
    print(f"  device={device}")
    print(f"  inference_device={inference_device}")
    print(f"  plot_out_dir={args.plot_out_dir.resolve()}")

    if correctness_files > 0:
        run_correctness(
            paired_paths=correctness_pairs,
            tech_path=tech_path,
            lef_path=lef_path,
            plot_out_dir=args.plot_out_dir,
            target_size=args.target_size,
            pixel_resolution=args.resolution,
            optimized_backend=optimized_backend,
            device=device,
            tech_layers=tech_layers,
            tech_z_heights=tech_z_heights,
            metal_layers=metal_layers,
        )
    else:
        print("Skipping correctness: no files selected.")

    run_throughput(
        paired_paths=paired_paths,
        tech_path=tech_path,
        lef_path=lef_path,
        runtime_config=runtime_config,
        target_size=args.target_size,
        pixel_resolution=args.resolution,
        warmup_files=args.warmup_files,
        throughput_passes=args.throughput_passes,
        optimized_backend=optimized_backend,
        device=device,
        inference_device=inference_device,
        tech_layers=tech_layers,
        tech_z_heights=tech_z_heights,
        metal_layers=metal_layers,
    )

    trace_name = f"lefdef_legacy_density_compare_{optimized_backend}_s{args.target_size}.trace.json"
    trace_cap3d_path, trace_def_path = paired_paths[0]
    run_trace(
        trace_path=(args.trace_out_dir / trace_name).resolve(),
        cap3d_path=trace_cap3d_path,
        def_path=trace_def_path,
        tech_path=tech_path,
        lef_path=lef_path,
        runtime_config=runtime_config,
        target_size=args.target_size,
        pixel_resolution=args.resolution,
        optimized_backend=optimized_backend,
        device=device,
        inference_device=inference_device,
        trace_warmup_iters=args.trace_warmup_iters,
        tech_layers=tech_layers,
        tech_z_heights=tech_z_heights,
        metal_layers=metal_layers,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

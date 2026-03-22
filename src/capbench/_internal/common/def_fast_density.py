from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from torch.profiler import record_function

from capbench._internal.common.cap3d_fast_density import (
    DEFAULT_TARGET_SIZE,
    DEFAULT_TORCH_EXTENSION_DIR,
    INT16_MAX,
    RECT_COL_CONDUCTOR_ID,
    RECT_COL_COUNT,
    RECT_COL_LAYER,
    RECT_COL_PX_MAX,
    RECT_COL_PX_MIN,
    RECT_COL_PY_MAX,
    RECT_COL_PY_MIN,
    expand_fast_idmaps_cpu,
    expand_fast_idmaps_cuda,
    rasterize_binary_masks_cpu,
    rasterize_binary_masks_cuda,
)
from capbench._internal.common.tech_parser import get_metal_layers_and_min_widths


DEFAULT_FAST_LEFDEF_EXTENSION_NAME = "capbench_lefdef_fast_parser_v2"
_NATIVE_SOURCE_DIR = Path(__file__).resolve().parent / "native"
_FAST_LEFDEF_MODULE = None
_FAST_LEFDEF_LOAD_ATTEMPTED = False

_DEFAULT_SYNTHETIC_SOURCE_KIND = "synthetic_lef"
_DEFAULT_REAL_SOURCE_KIND = "real_net"
RECT_SOURCE_ROUTE = np.uint8(0)
RECT_SOURCE_SPECIAL_ROUTE = np.uint8(1)
RECT_SOURCE_LEF_PIN = np.uint8(2)
RECT_SOURCE_LEF_OBS = np.uint8(3)
CONDUCTOR_SOURCE_SYNTHETIC_LEF = np.uint8(1)
_RECT_SOURCE_KIND_BY_CODE = {
    int(RECT_SOURCE_ROUTE): "route",
    int(RECT_SOURCE_SPECIAL_ROUTE): "special_route",
    int(RECT_SOURCE_LEF_PIN): "lef_pin",
    int(RECT_SOURCE_LEF_OBS): "lef_obs",
}


@dataclass(frozen=True)
class PreparedDefRasterInput:
    def_path: Path
    lef_path: Path
    lef_paths: Tuple[Path, ...]
    channel_layers: List[str]
    backend: str
    target_size: int
    pixel_resolution: float
    window_bounds: np.ndarray  # [6], float64
    conductor_names_sorted: Optional[List[str]]
    conductor_ids_sorted: np.ndarray  # [N], int16
    conductor_is_synthetic: np.ndarray  # [N], bool
    conductor_source_kind_codes: np.ndarray  # [N], uint8
    packed_rects: np.ndarray  # [B, 6], int32
    packed_rects_torch: Optional[torch.Tensor]
    rect_source_kind_codes: np.ndarray  # [B], uint8
    net_name_to_gpu_id: Optional[Dict[str, int]]
    total_segments: int
    total_endpoint_extensions: int
    active_rectangles: int
    parse_ms: float
    prepare_ms: float
    component_resolution_stats: Dict[str, int]

    @property
    def active_blocks(self) -> int:
        return self.active_rectangles

    @property
    def real_conductor_ids_sorted(self) -> np.ndarray:
        return self.conductor_ids_sorted[~self.conductor_is_synthetic]

    @property
    def conductor_source_kind(self) -> np.ndarray:
        labels = np.empty((self.conductor_source_kind_codes.shape[0],), dtype=object)
        labels[:] = _DEFAULT_REAL_SOURCE_KIND
        labels[self.conductor_source_kind_codes == CONDUCTOR_SOURCE_SYNTHETIC_LEF] = _DEFAULT_SYNTHETIC_SOURCE_KIND
        return labels

    @property
    def rect_source_kind(self) -> np.ndarray:
        labels = np.empty((self.rect_source_kind_codes.shape[0],), dtype=object)
        for code, label in _RECT_SOURCE_KIND_BY_CODE.items():
            labels[self.rect_source_kind_codes == code] = label
        return labels


@dataclass(frozen=True)
class PreparedDefRasterRuntimeInput:
    channel_layers: List[str]
    target_size: int
    pixel_resolution: float
    packed_rects_torch: torch.Tensor
    conductor_ids_torch: torch.Tensor
    active_rectangles: int
    parse_ms: float
    prepare_ms: float


@dataclass(frozen=True)
class PreparedDefBinaryMaskRuntimeInput:
    channel_layers: List[str]
    target_size: int
    pixel_resolution: float
    occupied: torch.Tensor
    master_masks: torch.Tensor
    master_conductor_ids_torch: torch.Tensor
    active_rectangles: int
    parse_ms: float
    prepare_ms: float


@dataclass(frozen=True)
class CompiledDefRuntimeConfig:
    tech_path: Path
    channel_layers: List[str]
    width_map: Dict[str, float]


def _normalize_layer_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())

def load_fast_lefdef_parser_extension():
    global _FAST_LEFDEF_MODULE, _FAST_LEFDEF_LOAD_ATTEMPTED

    if _FAST_LEFDEF_MODULE is not None:
        return _FAST_LEFDEF_MODULE
    if _FAST_LEFDEF_LOAD_ATTEMPTED:
        raise RuntimeError("The fast LEF+DEF parser extension failed to initialize earlier in this process.")

    _FAST_LEFDEF_LOAD_ATTEMPTED = True

    try:
        from torch.utils.cpp_extension import load
    except ImportError as exc:
        raise RuntimeError("torch.utils.cpp_extension is required to build the fast LEF+DEF parser extension.") from exc

    source_paths = [
        _NATIVE_SOURCE_DIR / "lefdef_fast_parser.c",
        _NATIVE_SOURCE_DIR / "lefdef_fast_parser_bindings.cpp",
        _NATIVE_SOURCE_DIR / "lefdef_fast_parser_compiled.cpp",
    ]
    missing_sources = [str(path) for path in source_paths if not path.exists()]
    if missing_sources:
        raise RuntimeError(
            "Fast LEF+DEF parser sources are missing: "
            + ", ".join(missing_sources)
        )

    build_dir = DEFAULT_TORCH_EXTENSION_DIR / DEFAULT_FAST_LEFDEF_EXTENSION_NAME
    build_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_EXTENSIONS_DIR", str(DEFAULT_TORCH_EXTENSION_DIR))

    try:
        _FAST_LEFDEF_MODULE = load(
            name=DEFAULT_FAST_LEFDEF_EXTENSION_NAME,
            sources=[str(path) for path in source_paths],
            extra_cflags=["-O3"],
            extra_include_paths=[str(_NATIVE_SOURCE_DIR)],
            build_directory=str(build_dir),
            verbose=False,
        )
    except Exception as exc:
        raise RuntimeError(
            "Failed to build or load the fast LEF+DEF parser extension "
            f"'{DEFAULT_FAST_LEFDEF_EXTENSION_NAME}' from {build_dir}"
        ) from exc
    return _FAST_LEFDEF_MODULE


def _resolve_native_channel_layers(
    tech_path: Path,
    selected_layers: Optional[Sequence[str]],
) -> Tuple[List[str], Dict[str, float]]:
    metal_layers, min_widths = get_metal_layers_and_min_widths(str(tech_path))
    if selected_layers is None:
        channel_layers = list(metal_layers)
    else:
        requested = {_normalize_layer_name(name) for name in selected_layers}
        channel_layers = [layer for layer in metal_layers if _normalize_layer_name(layer) in requested]

    width_map: Dict[str, float] = {}
    for layer_name in channel_layers:
        width = min_widths.get(layer_name)
        if width is not None:
            width_map[_normalize_layer_name(layer_name)] = float(width)
    return channel_layers, width_map


def _prepared_input_from_native_result(
    *,
    def_path: Path,
    lef_path: Path,
    lef_paths: Sequence[Path],
    channel_layers: Sequence[str],
    target_size: int,
    prepared: object,
    backend: str,
) -> PreparedDefRasterInput:
    packed_rects_raw = prepared["packed_rects"]
    packed_rects_torch: Optional[torch.Tensor]
    with record_function("lefdef.prepare.packed_rects_tensor"):
        if isinstance(packed_rects_raw, torch.Tensor):
            packed_rects_torch = packed_rects_raw.contiguous()
            packed_rects = packed_rects_torch.numpy()
        else:
            packed_rects_torch = None
            packed_rects = np.asarray(packed_rects_raw, dtype=np.int32)
    rect_codes = np.asarray(prepared["rect_source_kind_codes"], dtype=np.uint8)
    for code in rect_codes.tolist():
        if int(code) not in _RECT_SOURCE_KIND_BY_CODE:
            raise ValueError(f"Unknown rect source kind code returned by native prepare path: {code}")
    conductor_names_raw = prepared.get("conductor_names_sorted", None)
    conductor_names_sorted = None if conductor_names_raw is None else [str(name) for name in list(conductor_names_raw)]
    conductor_count = int(prepared["conductor_count"])
    real_conductor_count = int(prepared["real_conductor_count"])
    if real_conductor_count < 0 or real_conductor_count > conductor_count:
        raise ValueError(
            f"Invalid real_conductor_count returned by native prepare path for {def_path}: {real_conductor_count}"
        )
    if conductor_names_sorted is not None and len(conductor_names_sorted) != conductor_count:
        raise ValueError(
            f"Native prepare returned {len(conductor_names_sorted)} conductor names but packed_rects use {conductor_count} conductor IDs"
        )
    conductor_is_synthetic = np.zeros((conductor_count,), dtype=bool)
    conductor_source_kind_codes = np.zeros((conductor_count,), dtype=np.uint8)
    if real_conductor_count < conductor_count:
        conductor_is_synthetic[real_conductor_count:] = True
        conductor_source_kind_codes[real_conductor_count:] = CONDUCTOR_SOURCE_SYNTHETIC_LEF
    net_name_to_gpu_id = None
    if conductor_names_sorted is not None:
        net_name_to_gpu_id = {name: idx + 1 for idx, name in enumerate(conductor_names_sorted)}

    return PreparedDefRasterInput(
        def_path=def_path,
        lef_path=lef_path,
        lef_paths=tuple(Path(path).resolve() for path in lef_paths),
        channel_layers=list(channel_layers),
        backend=backend,
        target_size=int(target_size),
        pixel_resolution=float(prepared["pixel_resolution"]),
        window_bounds=np.asarray(prepared["window_bounds"], dtype=np.float64),
        conductor_names_sorted=conductor_names_sorted,
        conductor_ids_sorted=np.arange(1, conductor_count + 1, dtype=np.int16),
        conductor_is_synthetic=conductor_is_synthetic,
        conductor_source_kind_codes=conductor_source_kind_codes,
        packed_rects=packed_rects,
        packed_rects_torch=packed_rects_torch,
        rect_source_kind_codes=rect_codes,
        net_name_to_gpu_id=net_name_to_gpu_id,
        total_segments=int(prepared["total_segments"]),
        total_endpoint_extensions=int(prepared["total_endpoint_extensions"]),
        active_rectangles=int(prepared["active_rectangles"]),
        parse_ms=float(prepared["parse_ms"]),
        prepare_ms=float(prepared["prepare_ms"]),
        component_resolution_stats={str(key): int(value) for key, value in dict(prepared["component_resolution_stats"]).items()},
    )


def _default_lef_metadata_path(tech_path: Path) -> Path:
    return (tech_path.parent / f"{tech_path.stem}.lef").resolve()


def _supports_compiled_recipe_backend(tech_path: Path) -> bool:
    tech_key = _normalize_layer_name(tech_path.stem) or _normalize_layer_name(tech_path.name)
    return tech_key in {"nangate45", "sky130hd"}


def _compiled_recipe_tech_key(tech_path: Path) -> str:
    tech_key = _normalize_layer_name(tech_path.stem) or _normalize_layer_name(tech_path.name)
    if not _supports_compiled_recipe_backend(tech_path):
        raise ValueError(f"Unsupported compiled recipe tech: {tech_path}")
    return tech_key


def _validate_compiled_recipe_inputs(tech_path: Path) -> None:
    if _supports_compiled_recipe_backend(tech_path):
        return
    raise ValueError(
        "Compiled prepare only supports the static nangate45/sky130hd recipe tables; "
        f"got tech={tech_path}"
    )


def build_compiled_def_runtime_config(
    tech_path: Path | str,
    *,
    selected_layers: Optional[Sequence[str]] = None,
) -> CompiledDefRuntimeConfig:
    tech_path = Path(tech_path).resolve()
    _validate_compiled_recipe_inputs(tech_path)
    channel_layers, width_map = _resolve_native_channel_layers(tech_path, selected_layers)
    return CompiledDefRuntimeConfig(
        tech_path=tech_path,
        channel_layers=channel_layers,
        width_map=width_map,
    )


def _prepare_compiled_def_raster_input(
    *,
    def_path: Path,
    tech_path: Path,
    target_size: int,
    pixel_resolution: Optional[float],
    selected_layers: Optional[Sequence[str]],
    raster_bounds: Optional[Sequence[float] | np.ndarray],
    include_supply_nets: bool,
    include_conductor_names: bool,
) -> PreparedDefRasterInput:
    channel_layers, width_map = _resolve_native_channel_layers(tech_path, selected_layers)
    module = load_fast_lefdef_parser_extension()
    _validate_compiled_recipe_inputs(tech_path)

    with record_function("lefdef.prepare.native_compiled_call"):
        prepared = module.prepare_def_raster_compiled(
            str(def_path),
            _compiled_recipe_tech_key(tech_path),
            list(channel_layers),
            dict(width_map),
            int(target_size),
            None if pixel_resolution is None else float(pixel_resolution),
            None if raster_bounds is None else [float(value) for value in np.asarray(raster_bounds, dtype=np.float64).reshape(-1)],
            bool(include_supply_nets),
            bool(include_conductor_names),
        )

    with record_function("lefdef.prepare.python_convert"):
        return _prepared_input_from_native_result(
            def_path=def_path,
            lef_path=_default_lef_metadata_path(tech_path),
            lef_paths=(_default_lef_metadata_path(tech_path),),
            channel_layers=channel_layers,
            target_size=target_size,
            prepared=prepared,
            backend="compiled_recipe",
        )


def prepare_fast_def_raster_runtime(
    def_path: Path | str,
    runtime_config: CompiledDefRuntimeConfig,
    *,
    target_size: int = DEFAULT_TARGET_SIZE,
    pixel_resolution: Optional[float] = None,
    raster_bounds: Optional[Sequence[float] | np.ndarray] = None,
    include_supply_nets: bool = False,
) -> PreparedDefRasterRuntimeInput:
    def_path = Path(def_path).resolve()
    if target_size <= 0:
        raise ValueError(f"target_size must be positive, got {target_size}")
    module = load_fast_lefdef_parser_extension()

    with record_function("lefdef.prepare.native_runtime_call"):
        prepared = module.prepare_def_raster_compiled_runtime(
            str(def_path),
            _compiled_recipe_tech_key(runtime_config.tech_path),
            list(runtime_config.channel_layers),
            dict(runtime_config.width_map),
            int(target_size),
            None if pixel_resolution is None else float(pixel_resolution),
            None if raster_bounds is None else [float(value) for value in np.asarray(raster_bounds, dtype=np.float64).reshape(-1)],
            bool(include_supply_nets),
        )

    return PreparedDefRasterRuntimeInput(
        channel_layers=list(runtime_config.channel_layers),
        target_size=int(target_size),
        pixel_resolution=float(prepared["pixel_resolution"]),
        packed_rects_torch=prepared["packed_rects"].contiguous(),
        conductor_ids_torch=prepared["conductor_ids"].contiguous(),
        active_rectangles=int(prepared["active_rectangles"]),
        parse_ms=float(prepared["parse_ms"]),
        prepare_ms=float(prepared["prepare_ms"]),
    )


def prepare_fast_def_binary_masks_runtime(
    def_path: Path | str,
    runtime_config: CompiledDefRuntimeConfig,
    *,
    target_size: int = DEFAULT_TARGET_SIZE,
    pixel_resolution: Optional[float] = None,
    raster_bounds: Optional[Sequence[float] | np.ndarray] = None,
    include_supply_nets: bool = False,
    device: torch.device,
) -> PreparedDefBinaryMaskRuntimeInput:
    if device.type != "cuda":
        raise ValueError(f"prepare_fast_def_binary_masks_runtime requires a CUDA device, got: {device}")
    prepared = prepare_fast_def_raster_runtime(
        def_path=def_path,
        runtime_config=runtime_config,
        target_size=target_size,
        pixel_resolution=pixel_resolution,
        raster_bounds=raster_bounds,
        include_supply_nets=include_supply_nets,
    )
    real_conductor_count = int(prepared.conductor_ids_torch.numel())
    with record_function("lefdef.prepare.upload_rects"):
        packed_rects_cuda = prepared.packed_rects_torch.to(
            device=device,
            dtype=torch.int32,
            non_blocking=True,
        ).contiguous()
    with record_function("lefdef.prepare.rasterize_binary_masks"):
        occupied, master_masks = rasterize_binary_masks_cuda(
            packed_rects_cuda,
            num_layers=len(prepared.channel_layers),
            target_size=prepared.target_size,
            real_conductor_count=real_conductor_count,
        )
    return PreparedDefBinaryMaskRuntimeInput(
        channel_layers=list(prepared.channel_layers),
        target_size=prepared.target_size,
        pixel_resolution=prepared.pixel_resolution,
        occupied=occupied,
        master_masks=master_masks,
        master_conductor_ids_torch=prepared.conductor_ids_torch.to(device=device, dtype=torch.int16, non_blocking=True).contiguous(),
        active_rectangles=prepared.active_rectangles,
        parse_ms=prepared.parse_ms,
        prepare_ms=prepared.prepare_ms,
    )


def prepare_fast_def_binary_masks_cpu(
    prepared: PreparedDefRasterInput,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    real_conductor_ids = np.asarray(prepared.real_conductor_ids_sorted, dtype=np.int16)
    occupied, master_masks = rasterize_binary_masks_cpu(
        prepared.packed_rects,
        num_layers=len(prepared.channel_layers),
        target_size=prepared.target_size,
        real_conductor_count=int(real_conductor_ids.shape[0]),
    )
    return occupied, master_masks, real_conductor_ids


def prepare_fast_def_raster_input(
    def_path: Path | str,
    tech_path: Path | str,
    *,
    lef_path: Path | str | None = None,
    lef_files: Optional[Sequence[Path | str]] = None,
    target_size: int = DEFAULT_TARGET_SIZE,
    pixel_resolution: Optional[float] = None,
    selected_layers: Optional[Sequence[str]] = None,
    raster_bounds: Optional[Sequence[float] | np.ndarray] = None,
    include_supply_nets: bool = False,
    include_conductor_names: bool = False,
    backend: str = "auto",
) -> PreparedDefRasterInput:
    def_path = Path(def_path).resolve()
    tech_path = Path(tech_path).resolve()
    if target_size <= 0:
        raise ValueError(f"target_size must be positive, got {target_size}")
    if backend not in {"auto", "compiled"}:
        raise ValueError(f"Unsupported fast DEF prepare backend '{backend}'")

    if not _supports_compiled_recipe_backend(tech_path):
        raise ValueError(
            "Compiled prepare backend is unavailable for this tech; "
            f"got tech={tech_path}"
        )

    return _prepare_compiled_def_raster_input(
        def_path=def_path,
        tech_path=tech_path,
        target_size=target_size,
        pixel_resolution=pixel_resolution,
        selected_layers=selected_layers,
        raster_bounds=raster_bounds,
        include_supply_nets=include_supply_nets,
        include_conductor_names=include_conductor_names,
    )


def rasterize_def_idmaps_cpu(prepared_def: PreparedDefRasterInput) -> np.ndarray:
    return expand_fast_idmaps_cpu(prepared_def)



def rasterize_def_idmaps_cuda(prepared_def: PreparedDefRasterInput, device: torch.device) -> torch.Tensor:
    return expand_fast_idmaps_cuda(prepared_def, device=device)

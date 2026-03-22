from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from capbench._internal.common.native_extension_utils import ensure_torch_cuda_arch_list
from capbench.paths import get_cache_dir


NATIVE_SOURCE_DIR = Path(__file__).resolve().parent / "native"
DEFAULT_TORCH_EXTENSION_DIR = get_cache_dir(create=True) / "torch_extensions"
DEFAULT_FAST_PARSER_EXTENSION_NAME = "cap3d_fast_parser_cpu_v3"
DEFAULT_IDMAP_EXPAND_EXTENSION_NAME = "cap3d_idmap_expand_cuda_v5"
DEFAULT_TARGET_SIZE = 224
INT16_MAX = np.iinfo(np.int16).max

RECT_COL_LAYER = 0
RECT_COL_CONDUCTOR_ID = 1
RECT_COL_PX_MIN = 2
RECT_COL_PX_MAX = 3
RECT_COL_PY_MIN = 4
RECT_COL_PY_MAX = 5
RECT_COL_COUNT = 6

_FAST_CAP3D_PARSER_MODULE = None
_FAST_CAP3D_PARSER_LOAD_ATTEMPTED = False
_IDMAP_EXPAND_CUDA_MODULE = None
_IDMAP_EXPAND_CUDA_LOAD_ATTEMPTED = False


@dataclass(frozen=True)
class PreparedFastRasterInput:
    cap3d_path: Path
    channel_layers: List[str]
    target_size: int
    pixel_resolution: float
    window_bounds: np.ndarray  # [6], float64
    conductor_names_sorted: List[str]
    conductor_ids_sorted: np.ndarray  # [N], int16
    packed_rects: np.ndarray  # [B, 6], int32
    total_blocks: int
    active_blocks: int
    parse_ms: float


def load_fast_cap3d_parser_extension():
    global _FAST_CAP3D_PARSER_MODULE, _FAST_CAP3D_PARSER_LOAD_ATTEMPTED

    if _FAST_CAP3D_PARSER_MODULE is not None:
        return _FAST_CAP3D_PARSER_MODULE
    if _FAST_CAP3D_PARSER_LOAD_ATTEMPTED:
        raise RuntimeError("The fast CAP3D parser extension failed to initialize earlier in this process.")

    _FAST_CAP3D_PARSER_LOAD_ATTEMPTED = True

    try:
        from torch.utils.cpp_extension import load
    except ImportError as exc:
        raise RuntimeError("torch.utils.cpp_extension is required to build the fast CAP3D parser extension.") from exc

    source_paths = [NATIVE_SOURCE_DIR / "cap3d_fast_parser.cpp"]
    missing_sources = [str(path) for path in source_paths if not path.exists()]
    if missing_sources:
        raise RuntimeError(
            "Fast CAP3D parser sources are missing: "
            + ", ".join(missing_sources)
        )

    build_dir = DEFAULT_TORCH_EXTENSION_DIR / DEFAULT_FAST_PARSER_EXTENSION_NAME
    build_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_EXTENSIONS_DIR", str(DEFAULT_TORCH_EXTENSION_DIR))

    _FAST_CAP3D_PARSER_MODULE = load(
        name=DEFAULT_FAST_PARSER_EXTENSION_NAME,
        sources=[str(path) for path in source_paths],
        extra_cflags=["-O3"],
        build_directory=str(build_dir),
        verbose=True,
    )
    return _FAST_CAP3D_PARSER_MODULE


def load_idmap_expand_cuda_extension():
    global _IDMAP_EXPAND_CUDA_MODULE, _IDMAP_EXPAND_CUDA_LOAD_ATTEMPTED

    if _IDMAP_EXPAND_CUDA_MODULE is not None:
        return _IDMAP_EXPAND_CUDA_MODULE
    if _IDMAP_EXPAND_CUDA_LOAD_ATTEMPTED:
        raise RuntimeError("The CUDA ID-map expansion extension failed to initialize earlier in this process.")

    _IDMAP_EXPAND_CUDA_LOAD_ATTEMPTED = True

    if not torch.cuda.is_available():
        raise RuntimeError("The CUDA ID-map expansion extension requires CUDA.")

    ensure_torch_cuda_arch_list()

    try:
        from torch.utils.cpp_extension import load
    except ImportError as exc:
        raise RuntimeError("torch.utils.cpp_extension is required to build the CUDA ID-map expansion extension.") from exc

    source_paths = [
        NATIVE_SOURCE_DIR / "idmap_expand_bindings.cpp",
        NATIVE_SOURCE_DIR / "idmap_expand_cuda.cu",
    ]
    missing_sources = [str(path) for path in source_paths if not path.exists()]
    if missing_sources:
        raise RuntimeError(
            "CUDA ID-map expansion sources are missing: "
            + ", ".join(missing_sources)
        )

    build_dir = DEFAULT_TORCH_EXTENSION_DIR / DEFAULT_IDMAP_EXPAND_EXTENSION_NAME
    build_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_EXTENSIONS_DIR", str(DEFAULT_TORCH_EXTENSION_DIR))

    _IDMAP_EXPAND_CUDA_MODULE = load(
        name=DEFAULT_IDMAP_EXPAND_EXTENSION_NAME,
        sources=[str(path) for path in source_paths],
        extra_cflags=["-O3"],
        extra_cuda_cflags=["-O3", "--use_fast_math"],
        build_directory=str(build_dir),
        verbose=True,
    )
    return _IDMAP_EXPAND_CUDA_MODULE


def parse_cap3d_compact(cap3d_path: Path | str) -> Dict[str, object]:
    module = load_fast_cap3d_parser_extension()
    result = module.parse_cap3d_compact(str(Path(cap3d_path)))
    return dict(result)


def _is_via_layer(layer_name: str, layer_type: str) -> bool:
    lname = layer_name.strip().lower()
    ltype = layer_type.strip().lower()
    return lname.startswith("via") or "via" in ltype


def _compute_window_bounds_from_compact(compact: Dict[str, object]) -> Tuple[np.ndarray, np.float32, np.float32]:
    if not bool(compact["has_window"]):
        raise ValueError("CAP3D file is missing required <window> bounds.")

    window_v1 = np.asarray(compact["window_v1"].numpy(), dtype=np.float32)
    window_v2 = np.asarray(compact["window_v2"].numpy(), dtype=np.float32)
    x_min = np.float32(min(float(window_v1[0]), float(window_v2[0])))
    y_min = np.float32(min(float(window_v1[1]), float(window_v2[1])))
    x_max = np.float32(max(float(window_v1[0]), float(window_v2[0])))
    y_max = np.float32(max(float(window_v1[1]), float(window_v2[1])))
    z_min = float(min(float(window_v1[2]), float(window_v2[2])))
    z_max = float(max(float(window_v1[2]), float(window_v2[2])))
    bounds = np.asarray([x_min, y_min, z_min, x_max, y_max, z_max], dtype=np.float64)
    return bounds, x_min, y_min


def prepare_fast_raster_input(
    cap3d_path: Path | str,
    *,
    target_size: int = DEFAULT_TARGET_SIZE,
    pixel_resolution: Optional[float] = None,
) -> PreparedFastRasterInput:
    cap3d_path = Path(cap3d_path)
    if target_size <= 0:
        raise ValueError(f"target_size must be positive, got {target_size}")

    compact = parse_cap3d_compact(cap3d_path)
    block_layer_idx = np.asarray(compact["block_layer_idx"].numpy(), dtype=np.int32)
    block_conductor_idx = np.asarray(compact["block_conductor_idx"].numpy(), dtype=np.int32)
    block_x_min = np.asarray(compact["block_x_min"].numpy(), dtype=np.float32)
    block_x_max = np.asarray(compact["block_x_max"].numpy(), dtype=np.float32)
    block_y_min = np.asarray(compact["block_y_min"].numpy(), dtype=np.float32)
    block_y_max = np.asarray(compact["block_y_max"].numpy(), dtype=np.float32)
    layer_names = [str(name) for name in list(compact["layer_names"])]
    layer_types = [str(name) for name in list(compact["layer_types"])]
    conductor_names = [str(name) for name in list(compact["conductor_names"])]

    bounds, x_min, y_min = _compute_window_bounds_from_compact(compact)
    width_um = np.float32(bounds[3] - bounds[0])
    height_um = np.float32(bounds[4] - bounds[1])
    if pixel_resolution is None:
        max_dim = np.float32(max(float(width_um), float(height_um)))
        resolved_resolution = np.float32(max_dim / np.float32(target_size))
    else:
        resolved_resolution = np.float32(pixel_resolution)
    if not np.isfinite(resolved_resolution) or float(resolved_resolution) <= 0.0:
        raise ValueError(f"Invalid pixel_resolution resolved for {cap3d_path}: {resolved_resolution}")

    valid_layer_mask = (block_layer_idx >= 0) & (block_layer_idx < len(layer_names))
    used_layer_ids = sorted({int(layer_id) for layer_id in block_layer_idx[valid_layer_mask].tolist()})

    channel_layer_ids: List[int] = []
    channel_layers: List[str] = []
    for layer_id in used_layer_ids:
        layer_name = layer_names[layer_id]
        layer_type = layer_types[layer_id] if layer_id < len(layer_types) else ""
        if _is_via_layer(layer_name, layer_type):
            continue
        channel_layer_ids.append(layer_id)
        channel_layers.append(layer_name)

    layer_id_to_channel = {layer_id: channel for channel, layer_id in enumerate(channel_layer_ids)}
    block_layer_channel = np.full(block_layer_idx.shape, -1, dtype=np.int32)
    for layer_id, channel in layer_id_to_channel.items():
        block_layer_channel[block_layer_idx == layer_id] = np.int32(channel)

    unique_conductors = sorted({name for name in conductor_names if name})
    if len(unique_conductors) > INT16_MAX:
        raise ValueError(
            f"CAP3D file {cap3d_path} has {len(unique_conductors)} conductors, which exceeds the int16 limit."
        )
    conductor_name_to_id = {name: idx + 1 for idx, name in enumerate(unique_conductors)}
    conductor_idx_to_id = np.zeros((len(conductor_names),), dtype=np.int16)
    for idx, name in enumerate(conductor_names):
        conductor_idx_to_id[idx] = np.int16(conductor_name_to_id.get(name, 0))

    block_conductor_id = np.zeros(block_conductor_idx.shape, dtype=np.int16)
    valid_conductor_idx = (block_conductor_idx >= 0) & (block_conductor_idx < len(conductor_idx_to_id))
    block_conductor_id[valid_conductor_idx] = conductor_idx_to_id[block_conductor_idx[valid_conductor_idx]]

    px_min = np.floor((block_x_min - x_min) / resolved_resolution).astype(np.int32, copy=False)
    px_max = np.ceil((block_x_max - x_min) / resolved_resolution).astype(np.int32, copy=False)
    py_min = np.floor((block_y_min - y_min) / resolved_resolution).astype(np.int32, copy=False)
    py_max = np.ceil((block_y_max - y_min) / resolved_resolution).astype(np.int32, copy=False)

    px_min = np.clip(px_min, 0, target_size).astype(np.int32, copy=False)
    px_max = np.clip(px_max, 0, target_size).astype(np.int32, copy=False)
    py_min = np.clip(py_min, 0, target_size).astype(np.int32, copy=False)
    py_max = np.clip(py_max, 0, target_size).astype(np.int32, copy=False)

    active_mask = (
        (block_layer_channel >= 0)
        & (block_conductor_id > 0)
        & (px_min < px_max)
        & (py_min < py_max)
    )
    active_indices = np.nonzero(active_mask)[0]

    packed_rects = np.empty((int(active_indices.size), RECT_COL_COUNT), dtype=np.int32)
    if active_indices.size > 0:
        packed_rects[:, RECT_COL_LAYER] = block_layer_channel[active_indices].astype(np.int32, copy=False)
        packed_rects[:, RECT_COL_CONDUCTOR_ID] = block_conductor_id[active_indices].astype(np.int32, copy=False)
        packed_rects[:, RECT_COL_PX_MIN] = px_min[active_indices].astype(np.int32, copy=False)
        packed_rects[:, RECT_COL_PX_MAX] = px_max[active_indices].astype(np.int32, copy=False)
        packed_rects[:, RECT_COL_PY_MIN] = py_min[active_indices].astype(np.int32, copy=False)
        packed_rects[:, RECT_COL_PY_MAX] = py_max[active_indices].astype(np.int32, copy=False)

    parse_ms = float(compact["parse_ms"])
    return PreparedFastRasterInput(
        cap3d_path=cap3d_path,
        channel_layers=channel_layers,
        target_size=int(target_size),
        pixel_resolution=float(resolved_resolution),
        window_bounds=bounds,
        conductor_names_sorted=list(unique_conductors),
        conductor_ids_sorted=np.arange(1, len(unique_conductors) + 1, dtype=np.int16),
        packed_rects=packed_rects,
        total_blocks=int(block_layer_idx.shape[0]),
        active_blocks=int(active_indices.size),
        parse_ms=parse_ms,
    )


def upload_packed_rects_cuda(prepared: PreparedFastRasterInput, device: torch.device) -> torch.Tensor:
    if device.type != "cuda":
        raise ValueError(f"upload_packed_rects_cuda requires a CUDA device, got: {device}")
    packed_rects_torch = getattr(prepared, "packed_rects_torch", None)
    if isinstance(packed_rects_torch, torch.Tensor):
        return packed_rects_torch.to(device=device, dtype=torch.int32, non_blocking=True).contiguous()
    return torch.from_numpy(prepared.packed_rects).to(device=device, dtype=torch.int32, non_blocking=True).contiguous()


def rasterize_packed_rects_cuda(
    packed_rects_cuda: torch.Tensor,
    *,
    num_layers: int,
    target_size: int,
) -> torch.Tensor:
    module = load_idmap_expand_cuda_extension()
    return module.rasterize_idmaps(
        packed_rects_cuda,
        int(num_layers),
        int(target_size),
        int(target_size),
    )


def rasterize_packed_rects_with_sparse_cuda(
    packed_rects_cuda: torch.Tensor,
    *,
    num_layers: int,
    target_size: int,
    real_conductor_count: int,
    own_x0: int,
    own_x1: int,
    own_y0: int,
    own_y1: int,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    module = load_idmap_expand_cuda_extension()
    return module.rasterize_idmaps_with_sparse(
        packed_rects_cuda,
        int(num_layers),
        int(target_size),
        int(target_size),
        int(real_conductor_count),
        int(own_x0),
        int(own_x1),
        int(own_y0),
        int(own_y1),
    )


def expand_fast_idmaps_cpu(prepared: PreparedFastRasterInput) -> np.ndarray:
    layers = len(prepared.channel_layers)
    size = int(prepared.target_size)
    out = np.zeros((layers, size, size), dtype=np.int16)
    if prepared.active_blocks == 0:
        return out

    for idx in range(prepared.active_blocks):
        layer, cid, x0, x1, y0, y1 = prepared.packed_rects[idx]
        if layer < 0 or cid <= 0 or x0 >= x1 or y0 >= y1:
            continue
        out[layer, y0:y1, x0:x1] = np.int16(cid)
    return out


def expand_fast_idmaps_cuda(prepared: PreparedFastRasterInput, device: torch.device) -> torch.Tensor:
    if device.type != "cuda":
        raise ValueError(f"expand_fast_idmaps_cuda requires a CUDA device, got: {device}")
    if prepared.active_blocks == 0:
        return torch.zeros(
            (len(prepared.channel_layers), prepared.target_size, prepared.target_size),
            dtype=torch.int16,
            device=device,
        )

    packed_rects_cuda = upload_packed_rects_cuda(prepared, device=device)
    return rasterize_packed_rects_cuda(
        packed_rects_cuda,
        num_layers=len(prepared.channel_layers),
        target_size=prepared.target_size,
    )


def extract_present_conductor_ids_cpu(id_maps: np.ndarray) -> np.ndarray:
    ids = np.unique(np.asarray(id_maps, dtype=np.int16))
    return ids[ids > 0].astype(np.int16, copy=False)


def extract_present_conductor_ids_cuda(id_maps: torch.Tensor) -> torch.Tensor:
    ids = torch.unique(id_maps)
    ids = ids[ids > 0]
    return ids.to(dtype=torch.int16)


def generate_all_master_signed_occupancy_cpu(
    id_maps: np.ndarray,
    conductor_ids: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    id_maps = np.asarray(id_maps, dtype=np.int16)
    if id_maps.ndim != 3:
        raise ValueError(f"Expected id_maps with shape [layers, height, width], got {id_maps.shape}")

    if conductor_ids is None:
        master_ids = extract_present_conductor_ids_cpu(id_maps)
    else:
        master_ids = np.asarray(conductor_ids, dtype=np.int16)
        master_ids = master_ids[master_ids > 0]

    occupied = (id_maps > 0).astype(np.int8, copy=False)
    if master_ids.size == 0:
        empty = np.zeros((0,) + occupied.shape, dtype=np.int8)
        return empty, master_ids.astype(np.int16, copy=False)

    master_mask = id_maps[np.newaxis, ...] == master_ids.reshape(-1, 1, 1, 1)
    highlighted = np.broadcast_to(occupied, (master_ids.shape[0],) + occupied.shape).copy()
    highlighted -= master_mask.astype(np.int8, copy=False) * 2
    return highlighted, master_ids.astype(np.int16, copy=False)


def generate_all_master_signed_occupancy_cuda(
    id_maps: torch.Tensor,
    conductor_ids: torch.Tensor | np.ndarray,
) -> Tuple[torch.Tensor, torch.Tensor]:
    if not id_maps.is_cuda:
        raise ValueError("generate_all_master_signed_occupancy_cuda requires CUDA id_maps")
    if id_maps.dim() != 3:
        raise ValueError(f"Expected id_maps with shape [layers, height, width], got {tuple(id_maps.shape)}")

    if isinstance(conductor_ids, torch.Tensor):
        master_ids = conductor_ids.to(device=id_maps.device, dtype=torch.int16, non_blocking=True)
        master_ids = master_ids[master_ids > 0]
    else:
        master_ids = torch.from_numpy(np.asarray(conductor_ids, dtype=np.int16)).to(
            device=id_maps.device,
            dtype=torch.int16,
            non_blocking=True,
        )
        master_ids = master_ids[master_ids > 0]

    occupied = id_maps.gt(0).to(dtype=torch.int8)
    if master_ids.numel() == 0:
        empty = torch.zeros((0,) + tuple(id_maps.shape), dtype=torch.int8, device=id_maps.device)
        return empty, master_ids

    master_mask = id_maps.unsqueeze(0).eq(master_ids.view(-1, 1, 1, 1))
    highlighted = occupied.unsqueeze(0) - (master_mask.to(dtype=torch.int8) * 2)
    return highlighted.contiguous(), master_ids.contiguous()

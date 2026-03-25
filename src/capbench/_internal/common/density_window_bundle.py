"""Shared helpers for CapBench density-window shard artifacts."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Sequence

import numpy as np


BUNDLE_FORMAT_VERSION = 2
INDEX_FILENAME = "index.json"
META_FILENAME = INDEX_FILENAME
SHARDS_DIRNAME = "shards"
SHARD_FILENAME_TEMPLATE = "shard-{shard_id:05d}.npz"
DENSITY_ARRAY_KEY = "density"
ID_ARRAY_KEY = "id"
WINDOW_IDS_ARRAY_KEY = "window_ids"


@dataclass(frozen=True)
class DensityWindowMeta:
    """Metadata for one lazily-loaded density window."""

    path: Path
    window_id: str
    layer_names: tuple[str, ...]
    layer_has_density: tuple[bool, ...]
    shape: tuple[int, int, int]
    pixel_resolution: float
    window_bounds: tuple[float, float, float, float, float, float]
    raster_trim_applied: bool
    source_window_bounds: Optional[tuple[float, float, float, float, float, float]]


@dataclass(frozen=True)
class DensityWindowIndexEntry:
    """One window entry inside the shard index."""

    root: Path
    window_id: str
    shard_id: int
    shard_offset: int
    layer_names: tuple[str, ...]
    layer_has_density: tuple[bool, ...]
    shape: tuple[int, int, int]
    pixel_resolution: float
    window_bounds: tuple[float, float, float, float, float, float]
    raster_trim_applied: bool
    source_window_bounds: Optional[tuple[float, float, float, float, float, float]]
    conductor_id_map: dict[str, int]

    @property
    def path(self) -> Path:
        return density_window_bundle_path(self.root, self.window_id)

    @property
    def shard_path(self) -> Path:
        return shard_file_path(self.root, self.shard_id)


@dataclass(frozen=True)
class DensityWindowIndex:
    """Parsed shard-backed density window index."""

    root: Path
    layer_names: tuple[str, ...]
    shape: tuple[int, int, int]
    windows_per_shard: int
    windows: dict[str, DensityWindowIndexEntry]


def density_window_bundle_path(window_root: Path | str, window_id: str) -> Path:
    """Return the virtual path used to address one density window."""
    return Path(window_root) / str(window_id)


def shard_file_path(window_root: Path | str, shard_id: int) -> Path:
    return Path(window_root) / SHARDS_DIRNAME / SHARD_FILENAME_TEMPLATE.format(shard_id=int(shard_id))


def _coerce_shape(raw_shape: Sequence[object]) -> tuple[int, int, int]:
    shape = tuple(int(v) for v in raw_shape)
    if len(shape) != 3:
        raise ValueError(f"Invalid density window shape: {shape}")
    return shape


def _coerce_bounds(raw_bounds: Sequence[object], *, field_name: str) -> tuple[float, float, float, float, float, float]:
    bounds = tuple(float(v) for v in raw_bounds)
    if len(bounds) != 6:
        raise ValueError(f"Invalid {field_name}: {bounds}")
    return bounds


def _coerce_optional_bounds(raw_bounds: object, *, field_name: str) -> Optional[tuple[float, float, float, float, float, float]]:
    if raw_bounds is None:
        return None
    if not isinstance(raw_bounds, (list, tuple)):
        raise ValueError(f"Invalid {field_name}: expected list/tuple, got {type(raw_bounds).__name__}")
    return _coerce_bounds(raw_bounds, field_name=field_name)


def _normalize_root(root: Path | str) -> Path:
    return Path(root).resolve()


def _window_ref_to_root_and_id(window_ref: Path | str) -> tuple[Path, str]:
    ref = Path(window_ref)
    if ref.name == INDEX_FILENAME:
        raise ValueError(f"Expected a window reference, got index file: {ref}")
    if ref.is_dir() and (ref / INDEX_FILENAME).exists():
        raise ValueError(f"Expected a window reference, got density root: {ref}")
    root = _normalize_root(ref.parent)
    window_id = ref.name
    if not window_id:
        raise ValueError(f"Invalid density window reference: {window_ref}")
    return root, window_id


@lru_cache(maxsize=16)
def _load_density_window_index_cached(root_str: str) -> DensityWindowIndex:
    root = Path(root_str)
    index_path = root / INDEX_FILENAME
    if not index_path.exists():
        raise FileNotFoundError(f"Density window index not found: {index_path}")

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    format_version = int(payload.get("format_version", 0))
    if format_version != BUNDLE_FORMAT_VERSION:
        raise ValueError(
            f"Unsupported density shard format in {index_path}: "
            f"expected {BUNDLE_FORMAT_VERSION}, got {format_version}"
        )

    layer_names = tuple(str(layer) for layer in payload.get("layer_names", []))
    shape = _coerce_shape(payload.get("shape", []))
    if len(layer_names) != shape[0]:
        raise ValueError(
            f"Layer count mismatch in {index_path}: {len(layer_names)} names for shape {shape}"
        )

    raw_windows = payload.get("windows", {})
    if not isinstance(raw_windows, dict):
        raise ValueError(f"Invalid windows payload in {index_path}: expected object, got {type(raw_windows).__name__}")

    windows: dict[str, DensityWindowIndexEntry] = {}
    for raw_window_id, raw_entry in raw_windows.items():
        if not isinstance(raw_entry, dict):
            raise ValueError(
                f"Invalid entry for window {raw_window_id!r} in {index_path}: "
                f"expected object, got {type(raw_entry).__name__}"
            )
        window_id = str(raw_window_id)
        layer_has_density = tuple(bool(item) for item in raw_entry.get("layer_has_density", []))
        if len(layer_has_density) != len(layer_names):
            raise ValueError(
                f"layer_has_density mismatch for {window_id} in {index_path}: "
                f"{len(layer_has_density)} flags for {len(layer_names)} layers"
            )

        raw_conductor_map = raw_entry.get("conductor_id_map", {})
        if not isinstance(raw_conductor_map, dict):
            raise ValueError(
                f"Invalid conductor map for {window_id} in {index_path}: "
                f"expected object, got {type(raw_conductor_map).__name__}"
            )

        windows[window_id] = DensityWindowIndexEntry(
            root=root,
            window_id=window_id,
            shard_id=int(raw_entry["shard_id"]),
            shard_offset=int(raw_entry["shard_offset"]),
            layer_names=layer_names,
            layer_has_density=layer_has_density,
            shape=shape,
            pixel_resolution=float(raw_entry["pixel_resolution"]),
            window_bounds=_coerce_bounds(raw_entry.get("window_bounds", []), field_name="window_bounds"),
            raster_trim_applied=bool(raw_entry.get("raster_trim_applied", False)),
            source_window_bounds=_coerce_optional_bounds(
                raw_entry.get("source_window_bounds"),
                field_name="source_window_bounds",
            ),
            conductor_id_map={
                str(name): int(cid)
                for name, cid in raw_conductor_map.items()
            },
        )

    return DensityWindowIndex(
        root=root,
        layer_names=layer_names,
        shape=shape,
        windows_per_shard=int(payload.get("windows_per_shard", 64)),
        windows=windows,
    )


def load_density_window_index(window_root: Path | str) -> DensityWindowIndex:
    return _load_density_window_index_cached(str(_normalize_root(window_root)))


def is_density_window_bundle(path: Path | str) -> bool:
    try:
        root, window_id = _window_ref_to_root_and_id(path)
        index = load_density_window_index(root)
        return window_id in index.windows
    except (FileNotFoundError, ValueError):
        return False


def discover_density_window_ids(window_root: Path | str) -> list[str]:
    root = Path(window_root)
    if not root.exists():
        return []
    try:
        index = load_density_window_index(root)
    except FileNotFoundError:
        return []
    return sorted(index.windows.keys())


def _resolve_density_window_entry(window_ref: Path | str) -> DensityWindowIndexEntry:
    root, window_id = _window_ref_to_root_and_id(window_ref)
    index = load_density_window_index(root)
    entry = index.windows.get(window_id)
    if entry is None:
        raise FileNotFoundError(f"Density window '{window_id}' not found in {root / INDEX_FILENAME}")
    return entry


def load_density_window_meta(window_ref: Path | str) -> DensityWindowMeta:
    entry = _resolve_density_window_entry(window_ref)
    return DensityWindowMeta(
        path=entry.path,
        window_id=entry.window_id,
        layer_names=entry.layer_names,
        layer_has_density=entry.layer_has_density,
        shape=entry.shape,
        pixel_resolution=entry.pixel_resolution,
        window_bounds=entry.window_bounds,
        raster_trim_applied=entry.raster_trim_applied,
        source_window_bounds=entry.source_window_bounds,
    )


def load_density_window_conductor_map(window_ref: Path | str) -> dict[str, int]:
    entry = _resolve_density_window_entry(window_ref)
    return dict(entry.conductor_id_map)


def read_density_window_shard(shard_path: Path | str) -> tuple[np.ndarray, np.ndarray, tuple[str, ...]]:
    """Read one shard file without caching."""
    shard_path = Path(shard_path)
    with np.load(shard_path, allow_pickle=False) as payload:
        density = np.asarray(payload[DENSITY_ARRAY_KEY], dtype=np.float32)
        id_maps = np.asarray(payload[ID_ARRAY_KEY])
        window_ids = tuple(str(item) for item in payload[WINDOW_IDS_ARRAY_KEY].tolist())
    return density, id_maps, window_ids


@lru_cache(maxsize=8)
def _read_density_window_shard_cached(shard_path_str: str) -> tuple[np.ndarray, np.ndarray, tuple[str, ...]]:
    return read_density_window_shard(Path(shard_path_str))


def load_density_window_density(window_ref: Path | str, *, mmap_mode: str | None = "r") -> np.ndarray:
    """Load one window density tensor.

    ``mmap_mode`` is accepted for API compatibility but ignored because shards are
    stored as compressed ``npz`` archives.
    """
    del mmap_mode
    entry = _resolve_density_window_entry(window_ref)
    density, _id_maps, window_ids = _read_density_window_shard_cached(str(entry.shard_path))
    if entry.shard_offset >= len(window_ids) or window_ids[entry.shard_offset] != entry.window_id:
        raise ValueError(
            f"Shard window order mismatch for {entry.window_id}: "
            f"expected offset {entry.shard_offset} in {entry.shard_path}"
        )
    return density[entry.shard_offset]


def load_density_window_ids(window_ref: Path | str, *, mmap_mode: str | None = "r") -> np.ndarray:
    """Load one window ID tensor.

    ``mmap_mode`` is accepted for API compatibility but ignored because shards are
    stored as compressed ``npz`` archives.
    """
    del mmap_mode
    entry = _resolve_density_window_entry(window_ref)
    _density, id_maps, window_ids = _read_density_window_shard_cached(str(entry.shard_path))
    if entry.shard_offset >= len(window_ids) or window_ids[entry.shard_offset] != entry.window_id:
        raise ValueError(
            f"Shard window order mismatch for {entry.window_id}: "
            f"expected offset {entry.shard_offset} in {entry.shard_path}"
        )
    return id_maps[entry.shard_offset]


def _choose_id_dtype(max_id: int) -> np.dtype:
    return np.uint16 if int(max_id) <= np.iinfo(np.uint16).max else np.uint32


def _validate_window_payload(
    payload: Mapping[str, object],
    *,
    expected_layer_names: Optional[tuple[str, ...]],
    expected_shape: Optional[tuple[int, int, int]],
) -> tuple[tuple[str, ...], tuple[int, int, int], dict[str, object]]:
    window_id = str(payload["window_id"])
    layer_names = tuple(str(layer) for layer in payload.get("layer_names", []))
    layer_has_density = tuple(bool(item) for item in payload.get("layer_has_density", []))
    density = np.asarray(payload["density"], dtype=np.float32)
    id_maps = np.asarray(payload["id_maps"], dtype=np.int64)

    if density.ndim != 3 or id_maps.ndim != 3:
        raise ValueError(
            f"density and id_maps must be rank-3 tensors for {window_id}, "
            f"got {density.shape} and {id_maps.shape}"
        )
    if density.shape != id_maps.shape:
        raise ValueError(
            f"density and id_maps shapes must match for {window_id}, got {density.shape} and {id_maps.shape}"
        )
    if len(layer_names) != density.shape[0]:
        raise ValueError(
            f"Layer name count mismatch for {window_id}: "
            f"{len(layer_names)} names for tensor shape {density.shape}"
        )
    if len(layer_has_density) != len(layer_names):
        raise ValueError(
            f"Layer density-flag mismatch for {window_id}: "
            f"{len(layer_has_density)} flags for {len(layer_names)} layers"
        )
    if int(id_maps.min(initial=0)) < 0:
        raise ValueError(f"id_maps for {window_id} must be non-negative")

    shape = tuple(int(v) for v in density.shape)
    if expected_layer_names is not None and layer_names != expected_layer_names:
        raise ValueError(
            f"Layer ordering mismatch for {window_id}: expected {expected_layer_names}, got {layer_names}"
        )
    if expected_shape is not None and shape != expected_shape:
        raise ValueError(
            f"Tensor shape mismatch for {window_id}: expected {expected_shape}, got {shape}"
        )

    raw_conductor_map = payload.get("conductor_id_map", {})
    if not isinstance(raw_conductor_map, Mapping):
        raise ValueError(f"Invalid conductor_id_map for {window_id}: expected mapping")

    normalized_payload = {
        "window_id": window_id,
        "layer_names": layer_names,
        "layer_has_density": layer_has_density,
        "density": density,
        "id_maps": id_maps,
        "conductor_id_map": {
            str(name): int(cid)
            for name, cid in raw_conductor_map.items()
        },
        "window_bounds": _coerce_bounds(payload.get("window_bounds", []), field_name="window_bounds"),
        "pixel_resolution": float(payload["pixel_resolution"]),
        "raster_trim_applied": bool(payload.get("raster_trim_applied", False)),
        "source_window_bounds": _coerce_optional_bounds(
            payload.get("source_window_bounds"),
            field_name="source_window_bounds",
        ),
    }
    return layer_names, shape, normalized_payload


def _chunked(items: Sequence[dict[str, object]], chunk_size: int) -> Iterable[Sequence[dict[str, object]]]:
    for start in range(0, len(items), chunk_size):
        yield items[start:start + chunk_size]


def _write_density_window_shard(
    *,
    tmp_root: Path,
    shard_id: int,
    payload_chunk: Sequence[dict[str, object]],
    shards_index: list[dict[str, object]],
    windows_index: dict[str, dict[str, object]],
) -> None:
    density_stack = np.stack(
        [np.asarray(payload["density"], dtype=np.float32) for payload in payload_chunk],
        axis=0,
    )
    max_id = max(int(np.asarray(payload["id_maps"]).max(initial=0)) for payload in payload_chunk)
    id_dtype = _choose_id_dtype(max_id)
    id_stack = np.stack(
        [np.asarray(payload["id_maps"], dtype=id_dtype) for payload in payload_chunk],
        axis=0,
    )
    window_ids = [str(payload["window_id"]) for payload in payload_chunk]
    max_window_id_len = max(len(window_id) for window_id in window_ids)
    shard_path = shard_file_path(tmp_root, shard_id)
    np.savez_compressed(
        shard_path,
        **{
            DENSITY_ARRAY_KEY: density_stack,
            ID_ARRAY_KEY: id_stack,
            WINDOW_IDS_ARRAY_KEY: np.asarray(window_ids, dtype=f"<U{max_window_id_len}"),
        },
    )
    shards_index.append(
        {
            "id": int(shard_id),
            "path": str(shard_path.relative_to(tmp_root).as_posix()),
            "window_count": len(payload_chunk),
            "id_dtype": np.dtype(id_dtype).name,
        }
    )

    for shard_offset, payload in enumerate(payload_chunk):
        windows_index[str(payload["window_id"])] = {
            "shard_id": int(shard_id),
            "shard_offset": int(shard_offset),
            "layer_has_density": [bool(item) for item in payload["layer_has_density"]],
            "window_bounds": [float(v) for v in payload["window_bounds"]],
            "pixel_resolution": float(payload["pixel_resolution"]),
            "raster_trim_applied": bool(payload["raster_trim_applied"]),
            "source_window_bounds": (
                None
                if payload["source_window_bounds"] is None
                else [float(v) for v in payload["source_window_bounds"]]
            ),
            "conductor_id_map": {
                str(name): int(cid)
                for name, cid in dict(payload["conductor_id_map"]).items()
            },
        }


class DensityWindowShardWriter:
    """Incrementally write shard-backed density windows in arrival order."""

    def __init__(
        self,
        window_root: Path | str,
        *,
        windows_per_shard: int = 64,
        window_shuffle_seed: Optional[int] = None,
    ) -> None:
        if windows_per_shard <= 0:
            raise ValueError(f"windows_per_shard must be > 0, got {windows_per_shard}")

        self.root = Path(window_root)
        self.windows_per_shard = int(windows_per_shard)
        self.window_shuffle_seed = (
            None if window_shuffle_seed is None else int(window_shuffle_seed)
        )
        self.tmp_root = self.root.with_name(self.root.name + ".tmp")
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)
        (self.tmp_root / SHARDS_DIRNAME).mkdir(parents=True, exist_ok=True)

        self._expected_layer_names: Optional[tuple[str, ...]] = None
        self._expected_shape: Optional[tuple[int, int, int]] = None
        self._seen_window_ids: set[str] = set()
        self._pending_payloads: list[dict[str, object]] = []
        self._windows_index: dict[str, dict[str, object]] = {}
        self._shards_index: list[dict[str, object]] = []
        self._next_shard_id = 0
        self._finalized = False

    def __enter__(self) -> "DensityWindowShardWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self._finalized and self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)

    def add_window_payload(self, raw_payload: Mapping[str, object]) -> None:
        if self._finalized:
            raise RuntimeError("Cannot add payloads after finalize()")

        layer_names, shape, payload = _validate_window_payload(
            raw_payload,
            expected_layer_names=self._expected_layer_names,
            expected_shape=self._expected_shape,
        )
        self._expected_layer_names = layer_names
        self._expected_shape = shape

        window_id = str(payload["window_id"])
        if window_id in self._seen_window_ids:
            raise ValueError(f"Duplicate density window payload for {window_id}")
        self._seen_window_ids.add(window_id)
        self._pending_payloads.append(payload)
        if len(self._pending_payloads) >= self.windows_per_shard:
            self._flush_pending_payloads()

    def _flush_pending_payloads(self) -> None:
        if not self._pending_payloads:
            return
        _write_density_window_shard(
            tmp_root=self.tmp_root,
            shard_id=self._next_shard_id,
            payload_chunk=self._pending_payloads,
            shards_index=self._shards_index,
            windows_index=self._windows_index,
        )
        self._pending_payloads = []
        self._next_shard_id += 1

    def finalize(self) -> Path:
        if self._finalized:
            return self.root
        if self._expected_layer_names is None or self._expected_shape is None:
            raise ValueError("At least one density window payload is required")

        self._flush_pending_payloads()
        index_payload = {
            "format_version": BUNDLE_FORMAT_VERSION,
            "windows_per_shard": int(self.windows_per_shard),
            "window_shuffle_seed": self.window_shuffle_seed,
            "layer_names": list(self._expected_layer_names),
            "shape": [int(v) for v in self._expected_shape],
            "shards": self._shards_index,
            "windows": self._windows_index,
        }
        (self.tmp_root / INDEX_FILENAME).write_text(
            json.dumps(index_payload, indent=2),
            encoding="utf-8",
        )

        if self.root.exists():
            shutil.rmtree(self.root)
        self.tmp_root.rename(self.root)
        _load_density_window_index_cached.cache_clear()
        _read_density_window_shard_cached.cache_clear()
        self._finalized = True
        return self.root


def save_density_window_shards(
    window_root: Path | str,
    window_payloads: Sequence[Mapping[str, object]],
    *,
    windows_per_shard: int = 64,
    shuffle_windows: bool = True,
    shuffle_seed: int = 0,
) -> Path:
    """Write a full shard-backed density dataset root."""
    if windows_per_shard <= 0:
        raise ValueError(f"windows_per_shard must be > 0, got {windows_per_shard}")

    root = Path(window_root)
    normalized_payloads: list[dict[str, object]] = []
    expected_layer_names: Optional[tuple[str, ...]] = None
    expected_shape: Optional[tuple[int, int, int]] = None
    seen_window_ids: set[str] = set()

    for raw_payload in window_payloads:
        layer_names, shape, payload = _validate_window_payload(
            raw_payload,
            expected_layer_names=expected_layer_names,
            expected_shape=expected_shape,
        )
        expected_layer_names = layer_names
        expected_shape = shape
        window_id = str(payload["window_id"])
        if window_id in seen_window_ids:
            raise ValueError(f"Duplicate density window payload for {window_id}")
        seen_window_ids.add(window_id)
        normalized_payloads.append(payload)

    if expected_layer_names is None or expected_shape is None:
        raise ValueError("At least one density window payload is required")

    normalized_payloads.sort(key=lambda item: str(item["window_id"]))
    if shuffle_windows and len(normalized_payloads) > 1:
        rng = np.random.default_rng(int(shuffle_seed))
        order = rng.permutation(len(normalized_payloads))
        normalized_payloads = [normalized_payloads[int(idx)] for idx in order]

    with DensityWindowShardWriter(
        root,
        windows_per_shard=windows_per_shard,
        window_shuffle_seed=(int(shuffle_seed) if shuffle_windows else None),
    ) as writer:
        for payload in normalized_payloads:
            writer.add_window_payload(payload)
        return writer.finalize()


def save_density_window_bundle(
    bundle_dir: Path | str,
    *,
    window_id: str,
    layer_names: Sequence[str],
    layer_has_density: Sequence[bool],
    density: np.ndarray,
    id_maps: np.ndarray,
    conductor_id_map: Mapping[str, int],
    window_bounds: Sequence[float],
    pixel_resolution: float,
    raster_trim_applied: bool,
    source_window_bounds: Optional[Sequence[float]] = None,
) -> Path:
    """Compatibility wrapper that writes a single-window shard-backed dataset."""
    bundle_path = Path(bundle_dir)
    output_root = bundle_path.parent if bundle_path.name == str(window_id) else bundle_path
    save_density_window_shards(
        output_root,
        [
            {
                "window_id": window_id,
                "layer_names": layer_names,
                "layer_has_density": layer_has_density,
                "density": density,
                "id_maps": id_maps,
                "conductor_id_map": conductor_id_map,
                "window_bounds": window_bounds,
                "pixel_resolution": pixel_resolution,
                "raster_trim_applied": raster_trim_applied,
                "source_window_bounds": source_window_bounds,
            }
        ],
        windows_per_shard=1,
        shuffle_windows=False,
    )
    return density_window_bundle_path(output_root, window_id)

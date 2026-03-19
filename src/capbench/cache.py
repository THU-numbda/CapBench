"""Cache layout helpers for dataset downloads and generated artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .paths import get_cache_dir


ARTIFACT_ALIASES = {
    "binary_masks": "binary-masks",
    "binary-masks": "binary-masks",
    "density_maps": "density_maps",
    "density-maps": "density_maps",
    "point_clouds": "point_clouds",
    "point-clouds": "point_clouds",
    "labels_rwcap": "labels_rwcap",
    "labels-raphael": "labels_raphael",
    "labels_raphael": "labels_raphael",
    "windows": "windows.yaml",
    "windows.yaml": "windows.yaml",
    "cap3d": "cap3d",
    "def": "def",
    "gds": "gds",
}

ARTIFACT_RELATIVE_PATHS = {
    "cap3d": Path("cap3d"),
    "def": Path("def"),
    "gds": Path("gds"),
    "density_maps": Path("density_maps"),
    "binary-masks": Path("binary-masks"),
    "point_clouds": Path("point_clouds"),
    "labels_rwcap": Path("labels_rwcap"),
    "labels_raphael": Path("labels_raphael"),
    "windows.yaml": Path("windows.yaml"),
}


def normalize_artifact_name(name: str) -> str:
    key = str(name).strip()
    normalized = ARTIFACT_ALIASES.get(key)
    if normalized is None:
        raise KeyError(f"Unknown artifact: {name}")
    return normalized


def artifact_path(dataset_root: Path, artifact: str) -> Path:
    normalized = normalize_artifact_name(artifact)
    return Path(dataset_root) / ARTIFACT_RELATIVE_PATHS[normalized]


def artifact_exists(dataset_root: Path, artifact: str) -> bool:
    path = artifact_path(dataset_root, artifact)
    normalized = normalize_artifact_name(artifact)
    if normalized == "windows.yaml":
        return path.is_file()
    if not path.is_dir():
        return False
    try:
        next(path.iterdir())
    except StopIteration:
        return False
    return True


def cache_download_dir(*, create: bool = False) -> Path:
    path = get_cache_dir(create=create) / "downloads"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def cache_datasets_dir(*, create: bool = False) -> Path:
    path = get_cache_dir(create=create) / "datasets"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def cache_registry_dir(*, create: bool = False) -> Path:
    path = get_cache_dir(create=create) / "registry"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def dataset_cache_base(path_parts: list[str] | tuple[str, ...], version: str, *, create: bool = False) -> Path:
    path = cache_datasets_dir(create=create).joinpath(*path_parts, version)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def dataset_state_path(path_parts: list[str] | tuple[str, ...], *, create: bool = False) -> Path:
    filename = "__".join(path_parts) + ".json"
    return cache_registry_dir(create=create) / filename


def read_dataset_state(path_parts: list[str] | tuple[str, ...]) -> Dict[str, Any]:
    path = dataset_state_path(path_parts, create=False)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_dataset_state(path_parts: list[str] | tuple[str, ...], payload: Dict[str, Any]) -> None:
    path = dataset_state_path(path_parts, create=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

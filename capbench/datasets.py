"""Cache-backed dataset download, preprocessing, and materialization helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .cache import (
    artifact_exists,
    artifact_path,
    cache_download_dir,
    dataset_cache_base,
    normalize_artifact_name,
    read_dataset_state,
    write_dataset_state,
)
from .paths import get_workspace_root
from .registry import DatasetEntry, DatasetSource, get_dataset_entry, list_dataset_entries


DERIVABLE_ARTIFACTS = {
    "binary-masks": "binary_masks",
    "density_maps": "cnn",
    "point_clouds": "pct",
}


def list_datasets() -> List[Dict[str, Any]]:
    return [get_dataset_info(entry.dataset_id) for entry in list_dataset_entries()]


def _select_source(entry: DatasetEntry, source_name: str | None) -> DatasetSource:
    if source_name is None:
        return entry.preferred_source
    for source in entry.sources:
        if source.name == source_name:
            return source
    available = ", ".join(source.name for source in entry.sources)
    raise KeyError(f"Unknown source '{source_name}' for {entry.dataset_id}. Available sources: {available}")


def _download_archive(source: DatasetSource) -> Path:
    download_dir = cache_download_dir(create=True)
    archive_path = download_dir / source.filename
    if archive_path.exists():
        return archive_path

    tmp_path = archive_path.with_suffix(archive_path.suffix + ".part")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {source.name} archive to {archive_path}")
    print(f"Source URL: {source.url}")
    with urllib.request.urlopen(source.url) as response, tmp_path.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    tmp_path.replace(archive_path)
    return archive_path


def _extract_archive(entry: DatasetEntry, source: DatasetSource, archive_path: Path) -> Path:
    cache_base = dataset_cache_base(list(entry.path_parts), entry.version, create=True)
    extract_root = cache_base / "sources" / source.name
    if extract_root.exists():
        return extract_root

    tmp_root = extract_root.with_name(extract_root.name + ".tmp")
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)
    print(f"Extracting archive into {tmp_root}")
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(tmp_root)
    tmp_root.replace(extract_root)
    return extract_root


def _locate_dataset_root(extract_root: Path, entry: DatasetEntry) -> Path:
    expected = extract_root.joinpath(*entry.path_parts)
    if expected.exists():
        return expected

    matches: List[Path] = []
    for windows_file in sorted(extract_root.rglob(entry.windows_file)):
        candidate = windows_file.parent
        suffix = tuple(part.lower() for part in candidate.parts[-len(entry.path_parts) :])
        expected_suffix = tuple(part.lower() for part in entry.path_parts)
        if suffix == expected_suffix:
            matches.append(candidate)
            continue
        if all((candidate / required).exists() for required in ("cap3d", "def", "gds")):
            matches.append(candidate)

    if not matches:
        raise RuntimeError(f"Could not locate dataset root for {entry.dataset_id} under {extract_root}")
    return min(matches, key=lambda path: len(path.parts))


def _ensure_workspace_link(entry: DatasetEntry, source_root: Path) -> Path:
    cache_base = dataset_cache_base(list(entry.path_parts), entry.version, create=True)
    workspace_path = cache_base / "workspace"
    if workspace_path.is_symlink():
        if workspace_path.resolve() == source_root.resolve():
            return workspace_path.resolve()
        workspace_path.unlink()
    elif workspace_path.exists():
        if workspace_path.resolve() == source_root.resolve():
            return workspace_path.resolve()
        raise RuntimeError(f"Workspace path already exists and is not a managed symlink: {workspace_path}")

    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    workspace_path.symlink_to(source_root, target_is_directory=True)
    return workspace_path.resolve()


def _update_state(entry: DatasetEntry, selected_source: DatasetSource, workspace_root: Path) -> None:
    payload = {
        "dataset_id": entry.dataset_id,
        "version": entry.version,
        "source": selected_source.name,
        "workspace_root": str(workspace_root),
        "artifacts": {
            artifact: artifact_exists(workspace_root, artifact)
            for artifact in sorted(set(entry.bundled_artifacts) | set(entry.derivable_artifacts))
        },
    }
    write_dataset_state(list(entry.path_parts), payload)


def _ensure_registered_dataset(entry: DatasetEntry, *, source_name: str | None = None) -> Path:
    source = _select_source(entry, source_name)
    archive_path = _download_archive(source)
    extract_root = _extract_archive(entry, source, archive_path)
    dataset_root = _locate_dataset_root(extract_root, entry)
    workspace_root = _ensure_workspace_link(entry, dataset_root)
    _update_state(entry, source, workspace_root)
    return workspace_root


def _run_pipeline_stage(dataset_root: Path, stage: str) -> None:
    windows_file = dataset_root / "windows.yaml"
    if not windows_file.exists():
        raise RuntimeError(f"Cannot preprocess {stage}: missing {windows_file}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "window_tools.window_processing_pipeline",
            "--dataset-path",
            str(dataset_root),
            "--windows-file",
            str(windows_file),
            "--pipeline",
            stage,
        ],
        check=True,
    )


def _ensure_artifacts(entry: DatasetEntry, dataset_root: Path, artifacts: Sequence[str]) -> None:
    pending = [normalize_artifact_name(artifact) for artifact in artifacts]
    for artifact in pending:
        if artifact_exists(dataset_root, artifact):
            continue

        stage = entry.derivable_artifacts.get(artifact, DERIVABLE_ARTIFACTS.get(artifact))
        if stage is None:
            raise RuntimeError(
                f"Artifact '{artifact}' is missing for {entry.dataset_id} and is not configured as derivable. "
                f"Dataset root: {dataset_root}"
            )

        print(f"Generating missing artifact '{artifact}' with pipeline stage '{stage}'")
        _run_pipeline_stage(dataset_root, stage)
        if not artifact_exists(dataset_root, artifact):
            raise RuntimeError(f"Pipeline stage '{stage}' did not produce required artifact '{artifact}'")


def _default_materialize_path(entry: DatasetEntry) -> Path:
    return get_workspace_root(create=True).joinpath(*entry.path_parts)


def _materialize_symlink(source_root: Path, destination: Path) -> Path:
    destination = Path(destination).expanduser().resolve()
    if destination.is_symlink():
        if destination.resolve() == source_root.resolve():
            return destination
        destination.unlink()
    elif destination.exists():
        if destination.resolve() == source_root.resolve():
            return destination
        raise FileExistsError(f"Destination already exists and is not managed by CapBench: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(source_root, target_is_directory=True)
    return destination


def ensure_dataset(dataset: str, *, artifacts: Sequence[str] = (), source: str | None = None) -> Path:
    entry = get_dataset_entry(dataset)
    dataset_root = _ensure_registered_dataset(entry, source_name=source)
    if artifacts:
        _ensure_artifacts(entry, dataset_root, artifacts)
        _update_state(entry, _select_source(entry, source), dataset_root)
    return dataset_root


def preprocess_dataset(dataset: str, *, artifacts: Sequence[str]) -> Path:
    entry = get_dataset_entry(dataset)
    dataset_root = _ensure_registered_dataset(entry)
    _ensure_artifacts(entry, dataset_root, artifacts)
    _update_state(entry, entry.preferred_source, dataset_root)
    return dataset_root


def materialize_dataset(
    dataset: str,
    *,
    destination: str | Path | None = None,
    artifacts: Sequence[str] = (),
    source: str | None = None,
) -> Path:
    entry = get_dataset_entry(dataset)
    dataset_root = ensure_dataset(dataset, artifacts=artifacts, source=source)
    target = _default_materialize_path(entry) if destination is None else Path(destination)
    return _materialize_symlink(dataset_root, target)


def resolve_dataset_path(
    dataset: str | Path,
    *,
    artifacts: Sequence[str] = (),
    materialize: bool = False,
    destination: str | Path | None = None,
) -> Path:
    candidate = Path(dataset).expanduser()
    if candidate.exists():
        return candidate.resolve()
    if materialize:
        return materialize_dataset(str(dataset), destination=destination, artifacts=artifacts)
    return ensure_dataset(str(dataset), artifacts=artifacts)


def get_dataset_info(dataset: str) -> Dict[str, Any]:
    entry = get_dataset_entry(dataset)
    cache_base = dataset_cache_base(list(entry.path_parts), entry.version, create=False)
    state = read_dataset_state(list(entry.path_parts))
    workspace_link = cache_base / "workspace"
    workspace_root = workspace_link.resolve() if workspace_link.exists() else None
    artifact_status = {
        artifact: (artifact_exists(workspace_root, artifact) if workspace_root is not None else False)
        for artifact in sorted(set(entry.bundled_artifacts) | set(entry.derivable_artifacts))
    }
    return {
        "id": entry.dataset_id,
        "version": entry.version,
        "description": entry.description,
        "process_node": entry.process_node,
        "bundled_artifacts": list(entry.bundled_artifacts),
        "derivable_artifacts": dict(entry.derivable_artifacts),
        "sources": [source.name for source in entry.sources],
        "cache_root": str(cache_base),
        "workspace_root": (str(workspace_root) if workspace_root is not None else None),
        "artifact_status": artifact_status,
        "state": state,
    }

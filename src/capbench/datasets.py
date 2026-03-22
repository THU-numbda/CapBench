"""Cache-backed dataset download and preprocessing helpers."""

from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from tqdm import tqdm

from .cache import (
    ARTIFACT_RELATIVE_PATHS,
    artifact_exists,
    cache_download_dir,
    dataset_cache_base,
    filesystem_created_at,
    legacy_dataset_cache_base,
    normalize_artifact_name,
    read_dataset_state,
    write_dataset_state,
)
from .registry import DatasetEntry, DatasetSource, get_dataset_entry, list_dataset_entries


DEFAULT_ARTIFACT_STAGES = {
    "density_maps": "cnn",
    "point_clouds": "pct",
}

_DATASET_SIZE_ORDER = {
    "small": 0,
    "medium": 1,
    "large": 2,
}


def list_datasets() -> List[Dict[str, Any]]:
    return [get_dataset_info(entry.dataset_id) for entry in list_dataset_entries()]


def _resolve_dataset_entries(selector: str) -> list[DatasetEntry]:
    try:
        return [get_dataset_entry(selector)]
    except KeyError:
        pass

    normalized = str(selector).strip().lower()
    matches = [
        entry
        for entry in list_dataset_entries()
        if entry.process_node.lower() == normalized
        or (entry.path_parts and entry.path_parts[0].lower() == normalized)
    ]
    if matches:
        return sorted(matches, key=_dataset_entry_sort_key)

    available_datasets = ", ".join(sorted(entry.dataset_id for entry in list_dataset_entries()))
    available_pdks = ", ".join(sorted({entry.process_node for entry in list_dataset_entries()}))
    raise KeyError(
        f"Unknown dataset or PDK '{selector}'. "
        f"Available datasets: {available_datasets}. "
        f"Available PDK selectors: {available_pdks}."
    )


def _dataset_entry_sort_key(entry: DatasetEntry) -> tuple[object, ...]:
    size = entry.path_parts[-1] if entry.path_parts else ""
    return (
        entry.process_node.lower(),
        _DATASET_SIZE_ORDER.get(size.lower(), 999),
        tuple(entry.path_parts),
    )


def _pdk_cache_base(entry: DatasetEntry, *, create: bool = False) -> Path:
    return dataset_cache_base([entry.process_node], entry.version, create=create)


def _pdk_workspace_path(entry: DatasetEntry) -> Path:
    return _pdk_cache_base(entry, create=False) / "workspace"


def _relative_dataset_parts(entry: DatasetEntry) -> tuple[str, ...]:
    if entry.path_parts and entry.path_parts[0].lower() == entry.process_node.lower():
        return entry.path_parts[1:]
    return tuple(entry.path_parts)


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
        total_bytes = response.headers.get("Content-Length")
        total = int(total_bytes) if total_bytes is not None else None
        desc = f"Download {source.filename}"
        with tqdm(
            total=total,
            desc=desc,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            dynamic_ncols=True,
        ) as progress:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                progress.update(len(chunk))
    tmp_path.replace(archive_path)
    return archive_path


def _extract_archive(entry: DatasetEntry, source: DatasetSource, archive_path: Path) -> Path:
    cache_base = _pdk_cache_base(entry, create=True)
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


def _locate_pdk_root(extract_root: Path, entry: DatasetEntry) -> Path:
    expected = (extract_root / entry.process_node).resolve()
    if expected.exists():
        return expected

    matches: list[Path] = []
    relative_parts = _relative_dataset_parts(entry)
    for candidate in sorted(path for path in extract_root.rglob("*") if path.is_dir()):
        if candidate.name.lower() != entry.process_node.lower():
            continue
        dataset_candidate = candidate.joinpath(*relative_parts) if relative_parts else candidate
        if dataset_candidate.exists():
            matches.append(candidate)

    if not matches:
        raise RuntimeError(f"Could not locate PDK root for {entry.process_node} under {extract_root}")
    return min(matches, key=lambda path: len(path.parts))


def _migrate_legacy_cache_layout(entry: DatasetEntry, *, create: bool = False) -> Path:
    cache_base = dataset_cache_base(list(entry.path_parts), entry.version, create=create)
    legacy_base = legacy_dataset_cache_base(list(entry.path_parts), entry.version)
    if not legacy_base.exists() or legacy_base == cache_base:
        return cache_base

    has_current_layout = any((cache_base / name).exists() for name in ("sources", "workspace"))
    if not has_current_layout:
        for child in legacy_base.iterdir():
            if child.name == "workspace":
                continue
            target = cache_base / child.name
            if target.exists():
                continue
            child.rename(target)
        legacy_workspace = legacy_base / "workspace"
        if legacy_workspace.exists() or legacy_workspace.is_symlink():
            legacy_workspace.unlink()
    try:
        legacy_base.rmdir()
    except OSError:
        pass
    return cache_base


def _locate_dataset_root(extract_root: Path, entry: DatasetEntry) -> Path:
    relative_parts = _relative_dataset_parts(entry)
    expected = extract_root.joinpath(*relative_parts) if relative_parts else extract_root
    if expected.exists():
        return expected

    matches: List[Path] = []
    for windows_file in sorted(extract_root.rglob(entry.windows_file)):
        candidate = windows_file.parent
        suffix_parts = relative_parts if relative_parts else entry.path_parts
        suffix = tuple(part.lower() for part in candidate.parts[-len(suffix_parts) :])
        expected_suffix = tuple(part.lower() for part in suffix_parts)
        if suffix == expected_suffix:
            matches.append(candidate)
            continue
        if all((candidate / required).exists() for required in ("cap3d", "def", "gds")):
            matches.append(candidate)

    if not matches:
        raise RuntimeError(f"Could not locate dataset root for {entry.dataset_id} under {extract_root}")
    return min(matches, key=lambda path: len(path.parts))


def _ensure_pdk_workspace_link(entry: DatasetEntry, pdk_root: Path) -> Path:
    workspace_path = _pdk_workspace_path(entry)
    if workspace_path.is_symlink():
        if workspace_path.resolve() == pdk_root.resolve():
            return workspace_path
        workspace_path.unlink()
    elif workspace_path.exists():
        if workspace_path.resolve() == pdk_root.resolve():
            return workspace_path
        raise RuntimeError(f"PDK workspace path already exists and is not a managed symlink: {workspace_path}")

    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    workspace_path.symlink_to(pdk_root, target_is_directory=True)
    return workspace_path


def _ensure_workspace_link(entry: DatasetEntry, source_root: Path) -> Path:
    cache_base = dataset_cache_base(list(entry.path_parts), entry.version, create=True)
    workspace_path = cache_base / "workspace"
    if workspace_path.is_symlink():
        if workspace_path.resolve() == source_root.resolve():
            return workspace_path
        workspace_path.unlink()
    elif workspace_path.exists():
        if workspace_path.resolve() == source_root.resolve():
            return workspace_path
        raise RuntimeError(f"Workspace path already exists and is not a managed symlink: {workspace_path}")

    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    workspace_path.symlink_to(source_root, target_is_directory=True)
    return workspace_path


def _update_state(entry: DatasetEntry, selected_source: DatasetSource, workspace_root: Path) -> None:
    payload = {
        "dataset_id": entry.dataset_id,
        "version": entry.version,
        "source": selected_source.name,
        "workspace_root": str(workspace_root),
        "artifacts": {
            artifact: artifact_exists(workspace_root, artifact)
            for artifact in sorted(entry.artifacts)
        },
    }
    write_dataset_state(list(entry.path_parts), payload)


def _installed_workspace_root(entry: DatasetEntry) -> Path | None:
    cache_base = _migrate_legacy_cache_layout(entry, create=False)
    workspace_link = cache_base / "workspace"
    if not workspace_link.exists():
        return None
    if not workspace_link.resolve().exists():
        return None
    return workspace_link


def _installed_pdk_workspace_root(entry: DatasetEntry) -> Path | None:
    workspace_link = _pdk_workspace_path(entry)
    if not workspace_link.exists():
        return None
    if not workspace_link.resolve().exists():
        return None
    return workspace_link


def _ensure_registered_pdk(entry: DatasetEntry, *, source_name: str | None = None) -> Path:
    source = _select_source(entry, source_name)
    archive_path = _download_archive(source)
    extract_root = _extract_archive(entry, source, archive_path)
    pdk_root = _locate_pdk_root(extract_root, entry)
    _ensure_pdk_workspace_link(entry, pdk_root)
    return pdk_root


def _ensure_registered_dataset(entry: DatasetEntry, *, source_name: str | None = None) -> Path:
    _migrate_legacy_cache_layout(entry, create=True)
    source = _select_source(entry, source_name)
    pdk_root = _ensure_registered_pdk(entry, source_name=source_name)
    dataset_root = _locate_dataset_root(pdk_root, entry)
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
            "capbench.preprocess.window_processing_pipeline",
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

        stage = entry.artifacts.get(artifact)
        if stage is None:
            stage = DEFAULT_ARTIFACT_STAGES.get(artifact)
        if stage is None:
            raise RuntimeError(
                f"Artifact '{artifact}' is missing for {entry.dataset_id} and is not configured with a preprocessing stage. "
                f"Dataset root: {dataset_root}"
            )

        print(f"Generating missing artifact '{artifact}' with pipeline stage '{stage}'")
        _run_pipeline_stage(dataset_root, stage)
        if not artifact_exists(dataset_root, artifact):
            raise RuntimeError(f"Pipeline stage '{stage}' did not produce required artifact '{artifact}'")


def _default_prepare_artifacts(entry: DatasetEntry) -> tuple[str, ...]:
    configured = {
        normalize_artifact_name(name)
        for name, stage in entry.artifacts.items()
        if stage is not None
    }
    if configured:
        return tuple(sorted(configured))
    return tuple(sorted(DEFAULT_ARTIFACT_STAGES))


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def _cleanup_dataset_root(entry: DatasetEntry, dataset_root: Path) -> list[Path]:
    removed: list[Path] = []

    for artifact in _default_prepare_artifacts(entry):
        artifact_dir = dataset_root / ARTIFACT_RELATIVE_PATHS[artifact]
        if artifact_dir.is_dir():
            try:
                next(artifact_dir.iterdir())
            except StopIteration:
                shutil.rmtree(artifact_dir)
                removed.append(artifact_dir)

        tmp_dir = artifact_dir.with_name(artifact_dir.name + ".tmp")
        if tmp_dir.exists() or tmp_dir.is_symlink():
            _remove_path(tmp_dir)
            removed.append(tmp_dir)

    return removed


def _missing_artifacts(dataset_root: Path, artifacts: Sequence[str]) -> list[str]:
    missing: list[str] = []
    for artifact in [normalize_artifact_name(name) for name in artifacts]:
        if not artifact_exists(dataset_root, artifact):
            missing.append(artifact)
    return missing


def _install_guidance(dataset_id: str) -> str:
    return f"Run `python -m capbench datasets install {dataset_id}` first."


def _selector_result_root(selector: str, entries: Sequence[DatasetEntry]) -> Path:
    if len(entries) == 1 and entries[0].dataset_id == selector:
        dataset_root = _installed_workspace_root(entries[0])
        if dataset_root is not None:
            return dataset_root
    pdk_root = _installed_pdk_workspace_root(entries[0])
    if pdk_root is not None:
        return pdk_root
    raise FileNotFoundError(f"PDK '{entries[0].process_node}' is not installed in the CapBench cache.")


def _require_registered_dataset(entry: DatasetEntry, *, artifacts: Sequence[str] = ()) -> Path:
    dataset_root = _installed_workspace_root(entry)
    if dataset_root is None:
        raise FileNotFoundError(
            f"Dataset '{entry.dataset_id}' is not installed in the CapBench cache. {_install_guidance(entry.dataset_id)}"
        )

    missing = _missing_artifacts(dataset_root, artifacts)
    if missing:
        missing_text = ", ".join(missing)
        raise FileNotFoundError(
            f"Dataset '{entry.dataset_id}' is installed but missing required artifacts: {missing_text}. "
            f"{_install_guidance(entry.dataset_id)}"
        )
    return dataset_root


def _require_explicit_dataset_path(dataset_root: Path, *, artifacts: Sequence[str] = ()) -> Path:
    missing = _missing_artifacts(dataset_root, artifacts)
    if missing:
        missing_text = ", ".join(missing)
        raise FileNotFoundError(f"Dataset path '{dataset_root}' is missing required artifacts: {missing_text}")
    return dataset_root


def ensure_dataset(dataset: str, *, artifacts: Sequence[str] = (), source: str | None = None) -> Path:
    entries = _resolve_dataset_entries(dataset)
    for entry in entries:
        dataset_root = _ensure_registered_dataset(entry, source_name=source)
        if artifacts:
            _ensure_artifacts(entry, dataset_root, artifacts)
            _update_state(entry, _select_source(entry, source), dataset_root)
    return _selector_result_root(dataset, entries)


def install_dataset(
    dataset: str,
    *,
    source: str | None = None,
) -> Path:
    entries = _resolve_dataset_entries(dataset)
    for entry in entries:
        dataset_root = _ensure_registered_dataset(entry, source_name=source)
        removed_paths = _cleanup_dataset_root(entry, dataset_root)
        for removed in removed_paths:
            print(f"Removed stale path: {removed}")
        artifacts = _default_prepare_artifacts(entry)
        if artifacts:
            _ensure_artifacts(entry, dataset_root, artifacts)
        _update_state(entry, _select_source(entry, source), dataset_root)
    return _selector_result_root(dataset, entries)


def prepare_dataset(
    dataset: str,
    *,
    source: str | None = None,
) -> Path:
    return install_dataset(dataset, source=source)


def preprocess_dataset(dataset: str, *, artifacts: Sequence[str]) -> Path:
    entries = _resolve_dataset_entries(dataset)
    for entry in entries:
        dataset_root = _ensure_registered_dataset(entry)
        _ensure_artifacts(entry, dataset_root, artifacts)
        _update_state(entry, entry.preferred_source, dataset_root)
    return _selector_result_root(dataset, entries)


def resolve_dataset_path(
    dataset: str | Path,
    *,
    artifacts: Sequence[str] = (),
) -> Path:
    candidate = Path(dataset).expanduser()
    if candidate.exists():
        return _require_explicit_dataset_path(candidate.resolve(), artifacts=artifacts)
    entry = get_dataset_entry(str(dataset))
    return _require_registered_dataset(entry, artifacts=artifacts)


def get_dataset_info(dataset: str) -> Dict[str, Any]:
    entry = get_dataset_entry(dataset)
    cache_base = _migrate_legacy_cache_layout(entry, create=False)
    state = read_dataset_state(list(entry.path_parts))
    workspace_root = _installed_workspace_root(entry)
    artifact_status = {
        artifact: (artifact_exists(workspace_root, artifact) if workspace_root is not None else False)
        for artifact in sorted(entry.artifacts)
    }
    return {
        "id": entry.dataset_id,
        "version": entry.version,
        "description": entry.description,
        "process_node": entry.process_node,
        "artifacts": dict(entry.artifacts),
        "sources": [source.name for source in entry.sources],
        "cache_root": str(cache_base),
        "workspace_root": (str(workspace_root) if workspace_root is not None else None),
        "installed_at": filesystem_created_at(cache_base),
        "artifact_status": artifact_status,
        "state": state,
    }

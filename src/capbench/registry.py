"""Static dataset registry shipped with CapBench."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class DatasetSource:
    name: str
    url: str
    filename: str
    kind: str = "zip"
    preferred: bool = False


@dataclass(frozen=True)
class DatasetEntry:
    dataset_id: str
    version: str
    description: str
    process_node: str
    path_parts: tuple[str, ...]
    windows_file: str
    artifacts: Dict[str, str | None]
    sources: tuple[DatasetSource, ...]

    @property
    def preferred_source(self) -> DatasetSource:
        for source in self.sources:
            if source.preferred:
                return source
        return self.sources[0]


def _registry_payload() -> Dict[str, object]:
    registry_path = files("capbench").joinpath("data/datasets.json")
    return json.loads(registry_path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_registry() -> Dict[str, DatasetEntry]:
    payload = _registry_payload()
    entries: Dict[str, DatasetEntry] = {}
    for raw_entry in payload["datasets"]:
        sources = tuple(
            DatasetSource(
                name=item["name"],
                url=item["url"],
                filename=item["filename"],
                kind=item.get("kind", "zip"),
                preferred=bool(item.get("preferred", False)),
            )
            for item in raw_entry["sources"]
        )
        entry = DatasetEntry(
            dataset_id=raw_entry["id"],
            version=raw_entry["version"],
            description=raw_entry["description"],
            process_node=raw_entry["process_node"],
            path_parts=tuple(raw_entry["path_parts"]),
            windows_file=raw_entry.get("windows_file", "windows.yaml"),
            artifacts={str(name): (None if stage is None else str(stage)) for name, stage in dict(raw_entry.get("artifacts", {})).items()},
            sources=sources,
        )
        entries[entry.dataset_id] = entry
    return entries


def list_dataset_entries() -> List[DatasetEntry]:
    return [load_registry()[dataset_id] for dataset_id in sorted(load_registry())]


def get_dataset_entry(dataset_id: str) -> DatasetEntry:
    try:
        return load_registry()[str(dataset_id)]
    except KeyError as exc:
        available = ", ".join(sorted(load_registry()))
        raise KeyError(f"Unknown dataset '{dataset_id}'. Available datasets: {available}") from exc


def iter_dataset_ids() -> Iterable[str]:
    return load_registry().keys()

"""Standardized dataloader accessors backed by the CapBench dataset cache."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Iterator, Optional, Sequence

from torch.utils.data import Sampler

from .datasets import resolve_dataset_path
from .window_density_dataset import WindowCapDataset
from .window_id_map_dataset import IdMapWindowDataset


def _resolve_label_dir(dataset_root: Path, solver_preference: str) -> Path:
    rwcap = dataset_root / "labels_rwcap"
    raphael = dataset_root / "labels_raphael"
    order = ["rwcap", "raphael"] if solver_preference in {"auto", "rwcap"} else ["raphael", "rwcap"]
    for solver in order:
        candidate = rwcap if solver == "rwcap" else raphael
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No label directory found under {dataset_root}. Expected one of: {rwcap}, {raphael}"
    )


def resolve_cached_dataset(dataset: str | Path, *, artifacts: Sequence[str] = ()) -> Path:
    return resolve_dataset_path(dataset, artifacts=artifacts)


def _resolve_window_shard_ids(dataset) -> Optional[list[int]]:
    if hasattr(dataset, "get_window_shard_ids"):
        return [int(shard_id) for shard_id in dataset.get_window_shard_ids()]
    base = getattr(dataset, "base", None)
    if base is not None and hasattr(base, "get_window_shard_ids"):
        return [int(shard_id) for shard_id in base.get_window_shard_ids()]
    return None


def load_density_window_dataset(
    dataset: str | Path,
    *,
    goal: str = "self",
    solver_preference: str = "auto",
    window_ids: Optional[Sequence[str]] = None,
    build_workers: int = 0,
    highlight_scale: float = 1.0,
    window_cache_size: int = 4,
):
    dataset_root = resolve_cached_dataset(dataset, artifacts=["density_maps"])
    spef_dir = _resolve_label_dir(dataset_root, solver_preference)
    return WindowCapDataset(
        window_dir=dataset_root / "density_maps",
        spef_dir=spef_dir,
        window_ids=window_ids,
        goal=goal,
        highlight_scale=highlight_scale,
        solver_preference=solver_preference,
        build_workers=build_workers,
        window_cache_size=window_cache_size,
    )


def load_density_id_window_dataset(
    dataset: str | Path,
    *,
    goal: str = "self",
    solver_preference: str = "auto",
    window_ids: Optional[Sequence[str]] = None,
    build_workers: int = 0,
    highlight_scale: float = 1.0,
    window_cache_size: int = 4,
):
    dataset_root = resolve_cached_dataset(dataset, artifacts=["density_maps"])
    spef_dir = _resolve_label_dir(dataset_root, solver_preference)
    return IdMapWindowDataset(
        window_dir=dataset_root / "density_maps",
        spef_dir=spef_dir,
        window_ids=window_ids,
        goal=goal,
        highlight_scale=highlight_scale,
        solver_preference=solver_preference,
        build_workers=build_workers,
        window_cache_size=window_cache_size,
    )


class WindowGroupedBatchSampler(Sampler[list[int]]):
    """Batch sampler that preserves window locality while still shuffling windows."""

    def __init__(
        self,
        dataset,
        batch_size: int,
        *,
        shuffle: bool = True,
        drop_last: bool = False,
        seed: Optional[int] = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError(f"batch_size must be > 0, got {batch_size}")
        if not hasattr(dataset, "get_window_sample_ranges"):
            raise TypeError("dataset must expose get_window_sample_ranges() for window-grouped batching")

        self.dataset = dataset
        self.batch_size = int(batch_size)
        self.shuffle = bool(shuffle)
        self.drop_last = bool(drop_last)
        self.seed = 0 if seed is None else int(seed)
        self._epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self._epoch = int(epoch)

    def __iter__(self) -> Iterator[list[int]]:
        ranges = list(self.dataset.get_window_sample_ranges())
        shard_ids = _resolve_window_shard_ids(self.dataset)
        rng = random.Random(self.seed + self._epoch)
        if shard_ids is not None and len(shard_ids) == len(ranges):
            shard_to_windows: dict[int, list[int]] = {}
            for window_idx, shard_id in enumerate(shard_ids):
                shard_to_windows.setdefault(int(shard_id), []).append(window_idx)
            shard_order = list(shard_to_windows.keys())
            if self.shuffle:
                rng.shuffle(shard_order)
            window_order: list[int] = []
            for shard_id in shard_order:
                shard_windows = list(shard_to_windows[shard_id])
                if self.shuffle:
                    rng.shuffle(shard_windows)
                window_order.extend(shard_windows)
        else:
            window_order = list(range(len(ranges)))
            if self.shuffle:
                rng.shuffle(window_order)

        for window_idx in window_order:
            start, end = ranges[window_idx]
            sample_indices = list(range(start, end))
            if self.shuffle:
                rng.shuffle(sample_indices)

            for offset in range(0, len(sample_indices), self.batch_size):
                batch = sample_indices[offset : offset + self.batch_size]
                if len(batch) < self.batch_size and self.drop_last:
                    continue
                yield batch

        self._epoch += 1

    def __len__(self) -> int:
        total = 0
        for start, end in self.dataset.get_window_sample_ranges():
            count = end - start
            if self.drop_last:
                total += count // self.batch_size
            else:
                total += (count + self.batch_size - 1) // self.batch_size
        return total


def make_window_grouped_batch_sampler(
    dataset,
    batch_size: int,
    *,
    shuffle: bool = True,
    drop_last: bool = False,
    seed: Optional[int] = None,
) -> WindowGroupedBatchSampler:
    return WindowGroupedBatchSampler(
        dataset,
        batch_size,
        shuffle=shuffle,
        drop_last=drop_last,
        seed=seed,
    )

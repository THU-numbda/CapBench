from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from capbench._internal.common.density_window_bundle import (
    INDEX_FILENAME,
    density_window_bundle_path,
    discover_density_window_ids,
    load_density_window_density,
    load_density_window_meta,
    save_density_window_shards,
)
try:
    from tools.preprocess.converters.cnn_cap import DensityMapGenerator
except ModuleNotFoundError:  # pragma: no cover - depends on runtime environment
    DensityMapGenerator = None  # type: ignore[assignment]

try:
    import torch  # noqa: F401
except ImportError:  # pragma: no cover - environment dependent
    torch = None  # type: ignore[assignment]
    create_window_level_splits = None  # type: ignore[assignment]
    make_window_grouped_batch_sampler = None  # type: ignore[assignment]
    WindowCapDataset = None  # type: ignore[assignment]
    IdMapWindowDataset = None  # type: ignore[assignment]
else:
    from capbench._internal.common.window_splitting import create_window_level_splits
    from capbench.dataloaders import make_window_grouped_batch_sampler
    from capbench.window_density_dataset import WindowCapDataset
    from capbench.window_id_map_dataset import IdMapWindowDataset


_SPEF_TEXT = """*SPEF "ieee 1481-1999"
*C_UNIT 1 FF
*NAME_MAP
*1 NET_A
*2 NET_B

*D_NET *1 3
*CAP
1 NET_A 3
2 NET_A NET_B 0.5
*END

*D_NET *2 4
*CAP
1 NET_B 4
2 NET_B NET_A 0.5
*END
"""


def _make_window_payload(window_id: str, *, offset: float = 0.0) -> dict[str, object]:
    density = np.zeros((2, 2, 2), dtype=np.float32)
    density[0, 0, 0] = 0.5 + offset
    density[1, 1, 1] = 0.75 + offset

    id_maps = np.zeros((2, 2, 2), dtype=np.int32)
    id_maps[0, 0, 0] = 1
    id_maps[1, 1, 1] = 2

    return {
        "window_id": window_id,
        "layer_names": ["M1", "M2"],
        "layer_has_density": [True, True],
        "density": density,
        "id_maps": id_maps,
        "conductor_id_map": {"NET_A": 1, "NET_B": 2},
        "window_bounds": [0.0, 0.0, 0.0, 2.0, 2.0, 2.0],
        "pixel_resolution": 0.5,
        "raster_trim_applied": False,
    }


def _write_density_dataset(
    root: Path,
    window_ids: list[str],
    *,
    windows_per_shard: int = 64,
    offsets: dict[str, float] | None = None,
    shuffle_windows: bool = False,
) -> None:
    payloads = [
        _make_window_payload(window_id, offset=(offsets or {}).get(window_id, 0.0))
        for window_id in window_ids
    ]
    save_density_window_shards(
        root / "density_maps",
        payloads,
        windows_per_shard=windows_per_shard,
        shuffle_windows=shuffle_windows,
    )

    labels_dir = root / "labels_rwcap"
    labels_dir.mkdir(parents=True, exist_ok=True)
    for window_id in window_ids:
        (labels_dir / f"{window_id}.spef").write_text(_SPEF_TEXT, encoding="utf-8")


class DensityWindowBundleTests(unittest.TestCase):
    @unittest.skipIf(torch is None, "PyTorch is required for dataset materialization tests")
    def test_density_dataset_is_lazy_and_highlights_self_samples(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_density_dataset(root, ["W0"])

            dataset = WindowCapDataset(
                window_dir=root / "density_maps",
                spef_dir=root / "labels_rwcap",
                goal="self",
                build_workers=1,
                window_cache_size=1,
            )

            self.assertEqual(len(dataset), 2)
            self.assertEqual(len(dataset._shard_cache), 0)

            items = [dataset[idx] for idx in range(len(dataset))]
            self.assertEqual(len(dataset._shard_cache), 1)
            self.assertEqual(sorted(float(target.item()) for _, target, _ in items), [3.0, 4.0])

            by_positive = {meta["positive_conductors"]: tensor for tensor, _, meta in items}
            net_a = by_positive[(1,)]
            net_b = by_positive[(2,)]
            self.assertAlmostEqual(float(net_a[0, 0, 0]), 1.5, places=5)
            self.assertAlmostEqual(float(net_b[1, 1, 1]), 1.75, places=5)

    @unittest.skipIf(torch is None, "PyTorch is required for dataset materialization tests")
    def test_density_dataset_coupling_sample_keeps_positive_and_negative_highlights(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_density_dataset(root, ["W0"])

            dataset = WindowCapDataset(
                window_dir=root / "density_maps",
                spef_dir=root / "labels_rwcap",
                goal="coupling",
                build_workers=1,
            )

            self.assertEqual(len(dataset), 1)
            tensor, target, meta = dataset[0]
            self.assertAlmostEqual(float(target.item()), 0.5, places=5)
            self.assertEqual(meta["positive_conductors"], (1,))
            self.assertEqual(meta["negative_conductors"], (2,))
            self.assertAlmostEqual(float(tensor[0, 0, 0]), 1.5, places=5)
            self.assertAlmostEqual(float(tensor[1, 1, 1]), -0.75, places=5)

    @unittest.skipIf(torch is None, "PyTorch is required for dataset materialization tests")
    def test_id_map_dataset_uses_binary_occupancy_features(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_density_dataset(root, ["W0"])

            dataset = IdMapWindowDataset(
                window_dir=root / "density_maps",
                spef_dir=root / "labels_rwcap",
                goal="self",
                build_workers=1,
            )

            tensor, target, meta = dataset[0]
            self.assertIn(float(target.item()), {3.0, 4.0})
            self.assertTrue(np.isin(tensor.numpy(), [0.0, 1.0, 2.0]).all())

    def test_shard_metadata_and_density_round_trip(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_density_dataset(root, ["W0", "W1"], windows_per_shard=2)

            window_ref = density_window_bundle_path(root / "density_maps", "W0")
            meta = load_density_window_meta(window_ref)
            density = load_density_window_density(window_ref, mmap_mode=None)
            raw_index = json.loads((root / "density_maps" / INDEX_FILENAME).read_text(encoding="utf-8"))

            self.assertEqual(list(meta.layer_names), ["M1", "M2"])
            self.assertEqual(density.shape, (2, 2, 2))
            self.assertAlmostEqual(meta.pixel_resolution, 0.5, places=5)
            self.assertEqual(raw_index["windows"]["W0"]["shard_id"], 0)
            self.assertEqual(discover_density_window_ids(root / "density_maps"), ["W0", "W1"])

    def test_shard_rollover_uses_fixed_window_count(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_density_dataset(root, ["W0", "W1", "W2"], windows_per_shard=2)
            raw_index = json.loads((root / "density_maps" / INDEX_FILENAME).read_text(encoding="utf-8"))

            self.assertEqual(raw_index["windows"]["W0"]["shard_id"], 0)
            self.assertEqual(raw_index["windows"]["W1"]["shard_id"], 0)
            self.assertEqual(raw_index["windows"]["W2"]["shard_id"], 1)

    def test_shard_writer_can_shuffle_windows_deterministically(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_density_dataset(
                root,
                ["W0", "W1", "W2", "W3"],
                windows_per_shard=2,
                shuffle_windows=True,
            )
            raw_index = json.loads((root / "density_maps" / INDEX_FILENAME).read_text(encoding="utf-8"))

            self.assertEqual(raw_index["window_shuffle_seed"], 0)
            self.assertEqual(raw_index["windows"]["W2"]["shard_id"], 0)
            self.assertEqual(raw_index["windows"]["W0"]["shard_id"], 0)
            self.assertEqual(raw_index["windows"]["W1"]["shard_id"], 1)
            self.assertEqual(raw_index["windows"]["W3"]["shard_id"], 1)

    @unittest.skipIf(DensityMapGenerator is None, "cnn converter dependencies are not installed")
    def test_converter_uses_cap3d_filename_for_shard_window_id(self) -> None:
        generator = DensityMapGenerator(
            "/tmp/W8.cap3d",
            "/tmp/tech.yaml",
            pixel_resolution=0.5,
            target_size=2,
        )
        generator.tech_conductor_layers = ["M1"]
        generator.width_pixels = 2
        generator.height_pixels = 2
        generator.x_min = 0.0
        generator.y_min = 0.0
        generator.x_max = 1.0
        generator.y_max = 1.0
        generator.raster_trim_applied = False
        generator.window = SimpleNamespace(name="case-0", v1=(0.0, 0.0, 0.0), v2=(1.0, 1.0, 1.0))
        generator.density_maps = {
            "M1": (
                np.ones((2, 2), dtype=np.float32),
                np.zeros((2, 2), dtype=np.int32),
            )
        }

        payload = generator.build_bundle_data()

        self.assertEqual(payload["window_id"], "W8")

    @unittest.skipIf(torch is None, "PyTorch is required for dataset materialization tests")
    def test_grouped_sampler_batches_windows_by_shard(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_density_dataset(
                root,
                ["W0", "W1", "W2"],
                windows_per_shard=2,
                offsets={"W0": 0.0, "W1": 0.1, "W2": 0.2},
            )

            dataset = WindowCapDataset(
                window_dir=root / "density_maps",
                spef_dir=root / "labels_rwcap",
                goal="self",
                build_workers=1,
            )
            train_dataset, _, _ = create_window_level_splits(
                dataset,
                train_ratio=1.0,
                val_ratio=0.0,
                test_ratio=0.0,
                random_seed=0,
            )

            sampler = make_window_grouped_batch_sampler(
                train_dataset,
                batch_size=2,
                shuffle=False,
                seed=0,
            )

            batches = list(iter(sampler))
            shard_ids = train_dataset.get_window_shard_ids()
            shard_sequence = []
            for batch in batches:
                window_idx, _sample_idx = train_dataset._get_sample_indices(batch[0])  # pylint: disable=protected-access
                shard_sequence.append(shard_ids[window_idx])

            self.assertEqual(shard_sequence[:2], [0, 0])
            self.assertEqual(shard_sequence[-1], 1)


if __name__ == "__main__":
    unittest.main()

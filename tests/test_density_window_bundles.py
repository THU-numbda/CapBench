from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from capbench._internal.common.density_window_bundle import save_density_window_bundle
from capbench.visualization.viewer_density_maps import load_density_bundle

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


def _write_window_bundle(root: Path, window_id: str, *, offset: float = 0.0) -> Path:
    density = np.zeros((2, 2, 2), dtype=np.float32)
    density[0, 0, 0] = 0.5 + offset
    density[1, 1, 1] = 0.75 + offset

    id_maps = np.zeros((2, 2, 2), dtype=np.int32)
    id_maps[0, 0, 0] = 1
    id_maps[1, 1, 1] = 2

    bundle_dir = root / "density_maps" / window_id
    bundle_dir.parent.mkdir(parents=True, exist_ok=True)
    save_density_window_bundle(
        bundle_dir,
        window_id=window_id,
        layer_names=["M1", "M2"],
        layer_has_density=[True, True],
        density=density,
        id_maps=id_maps,
        conductor_id_map={"NET_A": 1, "NET_B": 2},
        window_bounds=[0.0, 0.0, 0.0, 2.0, 2.0, 2.0],
        pixel_resolution=0.5,
        raster_trim_applied=False,
    )

    labels_dir = root / "labels_rwcap"
    labels_dir.mkdir(parents=True, exist_ok=True)
    (labels_dir / f"{window_id}.spef").write_text(_SPEF_TEXT, encoding="utf-8")
    return bundle_dir


class DensityWindowBundleTests(unittest.TestCase):
    @unittest.skipIf(torch is None, "PyTorch is required for dataset materialization tests")
    def test_density_dataset_is_lazy_and_highlights_self_samples(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_window_bundle(root, "W0")

            dataset = WindowCapDataset(
                window_dir=root / "density_maps",
                spef_dir=root / "labels_rwcap",
                goal="self",
                build_workers=1,
                window_cache_size=1,
            )

            self.assertEqual(len(dataset), 2)
            self.assertEqual(len(dataset._window_cache), 0)

            items = [dataset[idx] for idx in range(len(dataset))]
            self.assertEqual(len(dataset._window_cache), 1)
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
            _write_window_bundle(root, "W0")

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
            _write_window_bundle(root, "W0")

            dataset = IdMapWindowDataset(
                window_dir=root / "density_maps",
                spef_dir=root / "labels_rwcap",
                goal="self",
                build_workers=1,
            )

            tensor, target, meta = dataset[0]
            self.assertIn(float(target.item()), {3.0, 4.0})
            self.assertTrue(np.isin(tensor.numpy(), [0.0, 1.0, 2.0]).all())

    def test_bundle_view_loader_reads_new_format(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle_dir = _write_window_bundle(root, "W0")

            dataset = load_density_bundle(bundle_dir)
            self.assertEqual(dataset.layers, ["M1", "M2"])
            self.assertEqual(dataset.density_maps["M1"].shape, (2, 2))
            self.assertAlmostEqual(dataset.pixel_resolution, 0.5, places=5)

    @unittest.skipIf(torch is None, "PyTorch is required for dataset materialization tests")
    def test_grouped_sampler_batches_samples_by_window(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_window_bundle(root, "W0", offset=0.0)
            _write_window_bundle(root, "W1", offset=0.1)

            dataset = WindowCapDataset(
                window_dir=root / "density_maps",
                spef_dir=root / "labels_rwcap",
                goal="self",
                build_workers=1,
            )
            train_dataset, _, _ = create_window_level_splits(
                dataset,
                train_ratio=0.5,
                val_ratio=0.5,
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
            self.assertEqual(len(batches), 1)
            start, end = train_dataset.get_window_sample_ranges()[0]
            self.assertEqual(batches[0], list(range(start, end)))


if __name__ == "__main__":
    unittest.main()

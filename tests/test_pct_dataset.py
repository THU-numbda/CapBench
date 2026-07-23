from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
PCT_ROOT = REPO_ROOT / "models" / "pct"
if str(PCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PCT_ROOT))

from data_utils.PcCapNpzDataset import PcCapNpzDataset


SPEF = """*SPEF "ieee 1481-1999"
*C_UNIT 1 FF
*D_NET NET_A 3
*CAP
1 NET_A 3
*END
*D_NET NET_B 4
*CAP
1 NET_B 4
*END
"""


def _write_point_cloud(path: Path) -> None:
    points = np.zeros((8, 9), dtype=np.float32)
    points[:4, 8] = 1
    points[4:, 8] = 2
    np.savez_compressed(
        path,
        points=points,
        conductor_ids=np.asarray([1, 2], dtype=np.int32),
        conductor_metadata_str=np.asarray("NET_A|metal1;NET_B|metal1"),
        window_name_str=np.asarray(path.stem),
    )


class PctDatasetTests(unittest.TestCase):
    def test_skipped_unlabeled_window_does_not_shift_sample_indices(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            points = root / "point_clouds"
            labels = root / "labels_rwcap"
            points.mkdir()
            labels.mkdir()
            _write_point_cloud(points / "W0.npz")
            _write_point_cloud(points / "W1.npz")
            (labels / "W1.spef").write_text(SPEF, encoding="utf-8")

            dataset = PcCapNpzDataset(
                point_cloud_dir=points,
                spef_dir=labels,
                goal="self",
                npoints=4,
                window_ids=["W0", "W1"],
            )

            self.assertEqual(dataset.get_window_ids(), ["W1"])
            self.assertEqual({sample.window_index for sample in dataset._samples}, {0})
            self.assertEqual(dataset._windows[0].window_id, "W1")


if __name__ == "__main__":
    unittest.main()

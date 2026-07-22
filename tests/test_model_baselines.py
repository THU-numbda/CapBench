from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (str(REPO_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    import torch
except ImportError:  # pragma: no cover - environment dependent
    torch = None  # type: ignore[assignment]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(torch is None, "PyTorch is required for baseline model tests")
class BaselineModelTests(unittest.TestCase):
    def test_pct_loss_is_msre(self) -> None:
        module = _load_module("pct_model_under_test", REPO_ROOT / "models" / "pct" / "model.py")
        predictions = torch.tensor([[2.0], [4.0]])
        targets = torch.tensor([[1.0], [2.0]])
        self.assertTrue(torch.isclose(module.CalLoss()(predictions, targets), torch.tensor(1.0)))

    def test_cnn_resnet34_accepts_pdk_specific_channel_count(self) -> None:
        module = _load_module(
            "cnn_resnet_under_test",
            REPO_ROOT / "models" / "cnn" / "resnet_custom.py",
        )
        model = module.resnet34(num_classes=1, num_input_channels=7).eval()
        with torch.no_grad():
            prediction = model(torch.zeros((2, 7, 64, 64)))
        self.assertEqual(tuple(prediction.shape), (2, 1))

    def test_exact_eighty_twenty_split_uses_every_window(self) -> None:
        from capbench.training import create_window_level_splits

        class WindowDataset:
            def __init__(self, window_ids):
                self.window_ids = list(window_ids)

            def get_window_ids(self):
                return self.window_ids.copy()

            def create_window_subset(self, window_ids):
                return WindowDataset(window_ids)

            def __len__(self):
                return len(self.window_ids)

        train, validation, test = create_window_level_splits(
            WindowDataset(f"W{i}" for i in range(8109)),
            train_ratio=0.8,
            val_ratio=0.2,
            test_ratio=0.0,
            random_seed=42,
        )
        self.assertEqual(len(train), 6487)
        self.assertEqual(len(validation), 1622)
        self.assertIsNone(test)


@unittest.skipUnless(
    torch is not None
    and importlib.util.find_spec("torch_geometric") is not None,
    "PyTorch Geometric is required for GNN model tests",
)
class GNNModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._old_path = list(sys.path)
        sys.path.insert(0, str(REPO_ROOT / "models" / "gnn"))
        from models.gnncap_model import GNNCapModel

        cls.model_class = GNNCapModel

    @classmethod
    def tearDownClass(cls) -> None:
        sys.path[:] = cls._old_path

    def test_paper_scale_gatv2_parameter_count(self) -> None:
        model = self.model_class(
            conv_type="gatv2",
            hidden_dims=(248, 256),
            heads=4,
            aggregation_hidden_dim=128,
        )
        count = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
        self.assertEqual(count, 167_290)

    def test_gcn_root_residual_preserves_node_features(self) -> None:
        model = self.model_class(
            conv_type="gcn",
            hidden_dims=(3, 3),
            aggregation_hidden_dim=2,
        ).eval()
        with torch.no_grad():
            for conv in model.convs:
                for parameter in conv.parameters():
                    parameter.zero_()
            for residual in model.gcn_residuals:
                residual.weight.copy_(torch.eye(3))
            for parameter in model.net_aggregator.score_network.parameters():
                parameter.zero_()
            model.predictor.weight.zero_()
            model.predictor.weight[0, 0] = 1.0
            model.predictor.bias.zero_()

        prediction = model(
            torch.tensor([[1.0, 0.0, 0.0], [3.0, 0.0, 0.0]]),
            torch.tensor([[0, 1], [1, 0]], dtype=torch.long),
            torch.zeros((2, 7)),
            torch.tensor([[True, True]]),
        )
        self.assertTrue(torch.allclose(prediction, torch.tensor([[2.0]])))


if __name__ == "__main__":
    unittest.main()

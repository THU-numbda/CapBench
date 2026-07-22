from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.train import build_command, load_catalog, select_recipe


CATALOG_PATH = REPO_ROOT / "recipes" / "paper.yaml"


class TrainingRecipeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_catalog(CATALOG_PATH)

    def test_single_catalog_covers_every_model_and_validated_pdk(self) -> None:
        self.assertEqual(set(self.catalog["pdks"]), {"nangate45", "sky130hd"})
        self.assertEqual(
            set(self.catalog["models"]), {"cnn", "pct", "gcn", "gat", "gatv2"}
        )
        self.assertEqual(list((REPO_ROOT / "recipes").rglob("*.yaml")), [CATALOG_PATH])

    def test_recipes_use_public_entrypoints_and_cache_dataset_ids(self) -> None:
        entrypoints = {
            "cnn": "models/cnn/train.py",
            "pct": "models/pct/train.py",
            "gnn": "models/gnn/train_lightning.py",
        }
        for pdk in self.catalog["pdks"]:
            for model, model_config in self.catalog["models"].items():
                with self.subTest(pdk=pdk, model=model):
                    recipe = select_recipe(self.catalog, pdk=pdk, model=model)
                    family = model_config["family"]
                    arguments = recipe["arguments"]
                    self.assertEqual(recipe["entrypoint"], entrypoints[family])
                    self.assertEqual(arguments["dataset-path"], f"{pdk}/small")
                    self.assertNotIn("data-dir", arguments)
                    self.assertNotIn("point-cloud-dir", arguments)
                    self.assertNotIn("spef-dir", arguments)

    def test_recipes_pin_the_shared_protocol(self) -> None:
        self.assertEqual(
            self.catalog["protocol"],
            {
                "split": "80/20 windows",
                "objective": "msre",
                "optimizer": "adam",
                "learning-rate": 0.0001,
                "epochs": 50,
                "seed": 42,
            },
        )
        for pdk in self.catalog["pdks"]:
            for model in self.catalog["models"]:
                with self.subTest(pdk=pdk, model=model):
                    recipe = select_recipe(self.catalog, pdk=pdk, model=model)
                    arguments = recipe["arguments"]
                    self.assertEqual(recipe["protocol"], self.catalog["protocol"])
                    self.assertGreater(recipe["paper_target_mape_percent"], 0)
                    self.assertEqual(arguments["epochs"], 50)
                    self.assertEqual(arguments["lr"], 0.0001)
                    self.assertEqual(arguments["seed"], 42)

                    if model == "cnn":
                        self.assertEqual(arguments["model-type"], "resnet34")
                        self.assertEqual(arguments["batch-size"], 64)
                        self.assertEqual(arguments["weight-decay"], 0.0)
                        self.assertEqual(arguments["val-split"], 0.2)
                    elif model == "pct":
                        self.assertEqual(arguments["npoints"], 1024)
                        self.assertEqual(arguments["num-sa-layers"], 4)
                        self.assertEqual(arguments["batch-size"], 64)
                        self.assertEqual(arguments["weight-decay"], 0.0)
                        self.assertEqual(arguments["val-split"], 0.2)
                    else:
                        self.assertEqual(arguments["patience"], 0)
                        if model == "gcn":
                            self.assertIs(
                                arguments["standardize-node-features"], True
                            )
                        else:
                            self.assertEqual(arguments["heads"], 4)

    def test_recipe_runner_renders_lists_flags_and_overrides_without_shell(self) -> None:
        recipe = select_recipe(self.catalog, pdk="nangate45", model="gatv2")
        command = build_command(
            recipe,
            python_executable="python-test",
            overrides={"epochs": 5, "allow-partial-net-labels": True},
        )
        self.assertEqual(command[0:2], ["python-test", "models/gnn/train_lightning.py"])
        hidden_index = command.index("--hidden-dims")
        self.assertEqual(command[hidden_index + 1:hidden_index + 3], ["248", "256"])
        self.assertIn("--allow-partial-net-labels", command)
        epoch_index = command.index("--epochs")
        self.assertEqual(command[epoch_index + 1], "5")

    def test_cnn_recipes_pin_small_window_layer_ranges(self) -> None:
        expected = {
            "nangate45": [
                "metal1",
                "via1",
                "metal2",
                "via2",
                "metal3",
                "via3",
                "metal4",
            ],
            "sky130hd": [
                "li1",
                "mcon",
                "met1",
                "via",
                "met2",
                "via2",
                "met3",
                "via3",
                "met4",
            ],
        }
        for pdk, layers in expected.items():
            recipe = select_recipe(self.catalog, pdk=pdk, model="cnn")
            self.assertEqual(recipe["arguments"]["required-layers"], layers)


if __name__ == "__main__":
    unittest.main()

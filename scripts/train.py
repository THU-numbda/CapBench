#!/usr/bin/env python3
"""Launch a paper-like CapBench CNN, PCT, or GNN training run."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "recipes" / "paper.yaml"
MODEL_CHOICES = ("cnn", "pct", "gcn", "gat", "gatv2")
PDK_CHOICES = ("nangate45", "sky130hd")


def load_catalog(path: Path | str = CATALOG_PATH) -> dict[str, Any]:
    catalog_path = Path(path)
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Training catalog must contain a YAML mapping: {catalog_path}")
    if not isinstance(data.get("pdks"), dict) or not isinstance(data.get("models"), dict):
        raise ValueError(f"Training catalog must define pdks and models: {catalog_path}")
    return data


def parse_overrides(items: list[str]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Override must use KEY=VALUE syntax: {item}")
        key, value = item.split("=", 1)
        if not key:
            raise ValueError(f"Override key cannot be empty: {item}")
        overrides[key] = yaml.safe_load(value)
    return overrides


def _format_value(value: Any, *, pdk: str, model: str) -> Any:
    if isinstance(value, str):
        return value.format(pdk=pdk, model=model)
    if isinstance(value, list):
        return [_format_value(item, pdk=pdk, model=model) for item in value]
    return value


def select_recipe(
    catalog: Mapping[str, Any],
    *,
    pdk: str,
    model: str,
) -> dict[str, Any]:
    try:
        pdk_config = catalog["pdks"][pdk]
        model_config = catalog["models"][model]
    except KeyError as error:
        raise ValueError(f"Unknown PDK/model selection: {pdk}/{model}") from error

    family = model_config["family"]
    arguments = {
        key: _format_value(value, pdk=pdk, model=model)
        for key, value in model_config.get("arguments", {}).items()
    }
    arguments["dataset-path"] = pdk_config["dataset-path"]
    arguments.update(pdk_config.get(family, {}))

    return {
        "name": f"paper-{pdk}-{model}",
        "entrypoint": model_config["entrypoint"],
        "arguments": arguments,
        "protocol": catalog.get("protocol", {}),
        "paper_target_mape_percent": model_config.get(
            "paper-target-mape-percent", {}
        ).get(pdk),
    }


def _append_argument(command: list[str], key: str, value: Any) -> None:
    option = f"--{key}"
    if isinstance(value, bool):
        if value:
            command.append(option)
        return
    if value is None:
        return
    command.append(option)
    if isinstance(value, (list, tuple)):
        command.extend(str(item) for item in value)
    else:
        command.append(str(value))


def build_command(
    recipe: Mapping[str, Any],
    *,
    python_executable: str = sys.executable,
    overrides: Mapping[str, Any] | None = None,
) -> list[str]:
    arguments = dict(recipe.get("arguments", {}))
    arguments.update(overrides or {})
    command = [python_executable, str(recipe["entrypoint"])]
    for key, value in arguments.items():
        _append_argument(command, key, value)
    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train a paper-like CapBench CNN, PCT, GCN, GAT, or GATv2 model."
    )
    parser.add_argument("--pdk", required=True, choices=PDK_CHOICES)
    parser.add_argument("--model", required=True, choices=MODEL_CHOICES)
    parser.add_argument(
        "--gpu",
        type=int,
        default=None,
        help="Use one physical GPU, exposed to the trainer as cuda:0.",
    )
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override one trainer argument; repeat as needed.",
    )
    parser.add_argument("--python", default=sys.executable, help="Python executable.")
    args = parser.parse_args()

    catalog = load_catalog()
    recipe = select_recipe(catalog, pdk=args.pdk, model=args.model)
    entrypoint = (REPO_ROOT / recipe["entrypoint"]).resolve()
    if not entrypoint.is_file() or REPO_ROOT not in entrypoint.parents:
        raise FileNotFoundError(
            f"Training entrypoint must be a file inside the repository: {entrypoint}"
        )

    command = build_command(
        recipe,
        python_executable=args.python,
        overrides=parse_overrides(args.overrides),
    )
    environment = os.environ.copy()
    if args.gpu is not None:
        environment["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
        environment["APPTAINERENV_CUDA_VISIBLE_DEVICES"] = str(args.gpu)

    print(f"Training: {args.pdk}/{args.model}")
    if args.gpu is not None:
        print(f"Physical GPU: {args.gpu} (visible device cuda:0)")
    print(shlex.join(command))

    completed = subprocess.run(command, cwd=REPO_ROOT, env=environment, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

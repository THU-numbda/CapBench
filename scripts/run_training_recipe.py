#!/usr/bin/env python3
"""Run one checked-in CapBench baseline recipe without invoking a shell."""

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


def load_recipe(path: Path | str) -> dict[str, Any]:
    recipe_path = Path(path)
    data = yaml.safe_load(recipe_path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Recipe must contain a YAML mapping: {recipe_path}")
    if not isinstance(data.get("entrypoint"), str):
        raise ValueError(f"Recipe is missing a string entrypoint: {recipe_path}")
    if not isinstance(data.get("arguments", {}), dict):
        raise ValueError(f"Recipe arguments must be a mapping: {recipe_path}")
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
        description="Run a checked-in CNN, PCT, or GNN paper-like training recipe."
    )
    parser.add_argument("recipe", type=Path, help="Recipe YAML file.")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override one recipe argument; repeat as needed.",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=None,
        help="Restrict the process to one physical GPU (visible as cuda:0).",
    )
    parser.add_argument("--python", default=sys.executable, help="Python executable.")
    parser.add_argument("--dry-run", action="store_true", help="Print without running.")
    args = parser.parse_args()

    recipe_path = args.recipe.resolve()
    recipe = load_recipe(recipe_path)
    entrypoint = (REPO_ROOT / recipe["entrypoint"]).resolve()
    if not entrypoint.is_file() or REPO_ROOT not in entrypoint.parents:
        raise FileNotFoundError(
            f"Recipe entrypoint must be a file inside the repository: {entrypoint}"
        )

    overrides = parse_overrides(args.overrides)
    command = build_command(
        recipe,
        python_executable=args.python,
        overrides=overrides,
    )
    environment = os.environ.copy()
    if args.gpu is not None:
        environment["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
        environment["APPTAINERENV_CUDA_VISIBLE_DEVICES"] = str(args.gpu)

    name = recipe.get("name", recipe_path.stem)
    print(f"Recipe: {name}")
    if args.gpu is not None:
        print(f"Physical GPU: {args.gpu} (visible device cuda:0)")
    print(shlex.join(command))
    if args.dry_run:
        return 0

    completed = subprocess.run(command, cwd=REPO_ROOT, env=environment, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

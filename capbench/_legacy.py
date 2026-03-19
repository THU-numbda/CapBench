"""Helpers for invoking the existing script-first CapBench code."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .paths import REPO_ROOT


def _strip_passthrough_separator(args: Sequence[str]) -> list[str]:
    cleaned = list(args)
    if cleaned and cleaned[0] == "--":
        cleaned = cleaned[1:]
    return cleaned


def run_python_module(module_name: str, args: Sequence[str] = ()) -> None:
    cleaned = _strip_passthrough_separator(args)
    subprocess.run([sys.executable, "-m", module_name, *cleaned], cwd=str(REPO_ROOT), check=True)


def run_python_script(relative_path: str | Path, args: Sequence[str] = ()) -> None:
    cleaned = _strip_passthrough_separator(args)
    subprocess.run([sys.executable, str(REPO_ROOT / relative_path), *cleaned], cwd=str(REPO_ROOT), check=True)

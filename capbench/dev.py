"""Developer-only wrappers for CapBench dataset authoring and maintenance tools."""

from __future__ import annotations

from typing import Dict, Sequence

from ._legacy import run_python_module, run_python_script


DEV_TOOL_DESCRIPTIONS: Dict[str, str] = {
    "window-pipeline": "Run the multi-stage CAP3D/density/binary-mask preprocessing pipeline.",
    "window-metadata": "Generate window YAML metadata from design inputs.",
    "partition-cap3d": "Partition CAP3D files for finer-grained downstream processing.",
    "openrcx": "Run OpenRCX across discovered dataset windows.",
    "rwcap": "Run RWCap across discovered dataset windows.",
}


def list_dev_tools() -> Dict[str, str]:
    return dict(DEV_TOOL_DESCRIPTIONS)


def run_dev_tool(tool_name: str, args: Sequence[str] = ()) -> None:
    if tool_name == "window-pipeline":
        run_python_module("window_tools.window_processing_pipeline", args)
        return
    if tool_name == "window-metadata":
        run_python_script("scripts/window_metadata_generation.py", args)
        return
    if tool_name == "partition-cap3d":
        run_python_script("scripts/partition_cap3d_dataset.py", args)
        return
    if tool_name == "openrcx":
        run_python_script("scripts/run_openrcx.py", args)
        return
    if tool_name == "rwcap":
        run_python_script("scripts/run_rwcap.py", args)
        return

    available = ", ".join(sorted(DEV_TOOL_DESCRIPTIONS))
    raise KeyError(f"Unknown dev tool '{tool_name}'. Available tools: {available}")


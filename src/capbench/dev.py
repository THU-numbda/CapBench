"""Developer-only wrappers for CapBench dataset authoring and maintenance tools."""

from __future__ import annotations

from typing import Dict, Sequence

from .devtools import openrcx, partition_cap3d, rwcap, window_metadata
from .preprocess import window_processing_pipeline


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
        window_processing_pipeline.main(list(args))
        return
    if tool_name == "window-metadata":
        window_metadata.main(list(args))
        return
    if tool_name == "partition-cap3d":
        partition_cap3d.main(list(args))
        return
    if tool_name == "openrcx":
        openrcx.main(list(args))
        return
    if tool_name == "rwcap":
        rwcap.main(list(args))
        return

    available = ", ".join(sorted(DEV_TOOL_DESCRIPTIONS))
    raise KeyError(f"Unknown dev tool '{tool_name}'. Available tools: {available}")

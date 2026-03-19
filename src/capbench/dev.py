"""Developer-only wrappers for CapBench dataset authoring and maintenance tools."""

from __future__ import annotations

from typing import Dict, Sequence


DEV_TOOL_DESCRIPTIONS: Dict[str, str] = {
    "window-pipeline": "Run the multi-stage CAP3D/density/binary-mask preprocessing pipeline.",
    "window-metadata": "Generate window YAML metadata from design inputs.",
    "partition-cap3d": "Partition CAP3D files for finer-grained downstream processing.",
    "openrcx": "Run OpenRCX across discovered dataset windows.",
    "rwcap": "Run RWCap across discovered dataset windows.",
}


def list_dev_tools() -> Dict[str, str]:
    return dict(DEV_TOOL_DESCRIPTIONS)


def _strip_passthrough_separator(args: Sequence[str]) -> list[str]:
    cleaned = list(args)
    if cleaned and cleaned[0] == "--":
        cleaned = cleaned[1:]
    return cleaned


def run_dev_tool(tool_name: str, args: Sequence[str] = ()) -> None:
    cleaned_args = _strip_passthrough_separator(args)

    if tool_name == "window-pipeline":
        from .preprocess import window_processing_pipeline
        window_processing_pipeline.main(cleaned_args)
        return
    if tool_name == "window-metadata":
        from .devtools import window_metadata
        window_metadata.main(cleaned_args)
        return
    if tool_name == "partition-cap3d":
        from .devtools import partition_cap3d
        partition_cap3d.main(cleaned_args)
        return
    if tool_name == "openrcx":
        from .devtools import openrcx
        openrcx.main(cleaned_args)
        return
    if tool_name == "rwcap":
        from .devtools import rwcap
        rwcap.main(cleaned_args)
        return

    available = ", ".join(sorted(DEV_TOOL_DESCRIPTIONS))
    raise KeyError(f"Unknown dev tool '{tool_name}'. Available tools: {available}")

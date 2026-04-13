"""
Shared helpers for interactive visualization scripts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def ensure_repo_root_on_path() -> Path:
    """Return the installed CapBench package root for legacy callers."""
    return _PACKAGE_ROOT


def apply_start_angle(renderer, angle_deg: float) -> None:
    """Rotate renderer camera around vertical axis by the requested angle."""
    if renderer is None or angle_deg == 0.0:
        return
    camera = renderer.GetActiveCamera()
    if camera is None:
        return
    camera.Azimuth(float(angle_deg))


def capture_initial_screenshot(render_window, output_path: Optional[Path]) -> None:
    """Capture the current render window contents to a PNG."""
    if output_path is None:
        return

    from vtk import vtkWindowToImageFilter, vtkPNGWriter

    output_path.parent.mkdir(parents=True, exist_ok=True)

    window_to_image = vtkWindowToImageFilter()
    window_to_image.SetInput(render_window)
    window_to_image.SetScale(1)
    window_to_image.SetInputBufferTypeToRGBA()
    window_to_image.ReadFrontBufferOff()
    window_to_image.Update()

    writer = vtkPNGWriter()
    writer.SetFileName(str(output_path))
    writer.SetInputConnection(window_to_image.GetOutputPort())
    writer.Write()

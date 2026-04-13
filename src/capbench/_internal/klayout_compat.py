"""Compatibility helpers for accessing the KLayout Python API."""

from __future__ import annotations

from types import ModuleType

_IMPORT_ERROR: Exception | None = None

try:
    import pya as _pya  # type: ignore[import-not-found]
except ImportError as exc:
    _IMPORT_ERROR = exc
    try:
        import klayout.db as _pya  # type: ignore[import-not-found]
    except ImportError as second_exc:
        _pya = None
        _IMPORT_ERROR = second_exc


pya = _pya


def require_pya() -> ModuleType:
    """Return the KLayout module or raise a clear, user-facing error."""
    if pya is None:
        raise ModuleNotFoundError(
            "KLayout Python bindings are required for CAP3D/layout extraction. "
            "Install the optional 'klayout' dependency or run inside a KLayout environment."
        ) from _IMPORT_ERROR
    return pya

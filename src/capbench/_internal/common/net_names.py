from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set


NET_NAME_CLEAN_RE = re.compile(r"[^A-Za-z0-9_.]")
INTERNAL_CONDUCTOR_PREFIX = "__internal__."


@dataclass
class Cap3DNetNameSanitizer:
    """Replicate the historical CAP3D net-name sanitization policy."""

    empty_name: str = "NET"
    _cache: Dict[str, str] = field(default_factory=dict, init=False)
    _used_names: Set[str] = field(default_factory=set, init=False)

    def sanitize(self, name: str) -> str:
        raw_name = str(name)
        cached = self._cache.get(raw_name)
        if cached is not None:
            return cached

        sanitized = NET_NAME_CLEAN_RE.sub("", raw_name).strip()
        if not sanitized:
            sanitized = self.empty_name

        candidate = sanitized
        suffix = 1
        while candidate in self._used_names:
            candidate = f"{sanitized}_{suffix}"
            suffix += 1

        self._used_names.add(candidate)
        self._cache[raw_name] = candidate
        return candidate


def canonicalize_binary_mask_conductor_names(
    raw_names: Iterable[str],
    synthetic_flags: Iterable[bool],
    *,
    internal_prefix: str = INTERNAL_CONDUCTOR_PREFIX,
) -> List[str]:
    """Return canonical binary-mask conductor names for export."""
    sanitizer = Cap3DNetNameSanitizer()
    canonical_names: List[str] = []
    internal_count = 0

    for raw_name, synthetic in zip(raw_names, synthetic_flags):
        if synthetic:
            internal_count += 1
            canonical_names.append(f"{internal_prefix}{internal_count}")
            continue

        canonical = sanitizer.sanitize(str(raw_name))
        if canonical.startswith(internal_prefix):
            raise ValueError(
                f"Real conductor name '{raw_name}' sanitized to reserved internal namespace "
                f"'{canonical}'"
            )
        canonical_names.append(canonical)

    return canonical_names

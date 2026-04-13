"""Pure Python SPEF parser and helpers.

This module replaces the pybind11-based ``spefkit_spef`` bindings with a
portable reader implemented in Python.  It provides a minimal API surface
needed by the model pipeline:

* ``load_dnet_totals(path)`` – total capacitance per net (Farads)
* ``load_ground_and_coupling(path)`` – self and coupling capacitances
* ``parse_spef(path)`` – full parse returning a :class:`SpefFile`

The parser handles IEEE 1481-1999 style SPEF files with *NAME_MAP sections,
distributed ``*D_NET`` blocks, and ``*CAP`` tables in either ground (3-field)
or coupling (4-field) form.  Capacitance values are converted to SI (Farads)
based on the ``*C_UNIT`` header line.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CapEntry:
    """A single capacitance entry from a ``*CAP`` section."""

    node_a: str
    node_b: Optional[str]
    value_f: float

    @property
    def is_ground(self) -> bool:
        """Return ``True`` when the entry represents ground/self capacitance."""
        return self.node_b is None

    @property
    def is_coupling(self) -> bool:
        """Return ``True`` when the entry represents coupling capacitance."""
        return self.node_b is not None


@dataclass
class SpefNet:
    """Container for per-net capacitance data."""

    name: str
    total_cap_f: float
    cap_entries: List[CapEntry] = field(default_factory=list)

    def ground_cap(self) -> float:
        return sum(entry.value_f for entry in self.cap_entries if entry.is_ground)

    def coupling_cap(self) -> float:
        return sum(entry.value_f for entry in self.cap_entries if entry.is_coupling)


@dataclass
class SpefFile:
    """Parsed SPEF contents."""

    path: Path
    header: Dict[str, str]
    name_map: Dict[str, str]
    nets: Dict[str, SpefNet]

    def get_net(self, name: str) -> Optional[SpefNet]:
        return self.nets.get(name)


# ---------------------------------------------------------------------------
# Parser implementation
# ---------------------------------------------------------------------------

_UNIT_SCALE = {
    "F": 1.0,
    "FF": 1e-15,
    "PF": 1e-12,
    "NF": 1e-9,
    "UF": 1e-6,
    "MF": 1e-3,
}

_COMMENT_SOLVER_RE = re.compile(r"solver\s*[:=]\s*(\S+)", re.IGNORECASE)


class SpefParser:
    """Line-based SPEF parser."""

    def __init__(self, text: Iterable[str], *, path: Optional[Path] = None):
        self._lines = list(text)
        self.path = path
        self.header: Dict[str, str] = {}
        self.name_map: Dict[str, str] = {}
        self.nets: Dict[str, SpefNet] = {}
        self.cap_scale = 1.0  # Default to Farads

    # -- Helpers -------------------------------------------------------------

    def _resolve_token(self, token: str) -> str:
        """Expand *NAME_MAP references while preserving suffixes (e.g., ``:N``)."""
        if not token.startswith("*"):
            return token
        base, *rest = token.split(":", maxsplit=1)
        mapped = self.name_map.get(base, base)
        if rest:
            mapped = f"{mapped}:{rest[0]}"
        return mapped

    @staticmethod
    def _clean_value(text: str) -> str:
        """Strip surrounding quotes from header values."""
        text = text.strip()
        if len(text) >= 2 and text[0] == text[-1] == '"':
            return text[1:-1]
        return text

    def _parse_header_line(self, line: str) -> None:
        if line.startswith("*C_UNIT"):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    scale = float(parts[1])
                except ValueError:
                    scale = 1.0
                unit = parts[2].upper()
                multiplier = _UNIT_SCALE.get(unit, 1.0)
                self.cap_scale = scale * multiplier
            return

        if line.startswith("*COMMENT"):
            value = self._clean_value(line[len("*COMMENT"):].strip())
            self.header.setdefault("COMMENT", value)
            return

        if line.startswith("*"):
            parts = line.split(maxsplit=1)
            key = parts[0][1:]
            value = self._clean_value(parts[1]) if len(parts) > 1 else ""
            self.header[key] = value

    # -- Parsing -------------------------------------------------------------

    def parse(self) -> SpefFile:
        i = 0
        total_lines = len(self._lines)

        while i < total_lines:
            raw = self._lines[i].strip()
            if not raw:
                i += 1
                continue

            if raw.startswith("*NAME_MAP"):
                i = self._parse_name_map(i + 1)
                continue

            if raw.startswith("*D_NET"):
                i = self._parse_d_net(i)
                continue

            if raw.startswith("*"):
                self._parse_header_line(raw)

            i += 1

        return SpefFile(
            path=self.path or Path("<memory>"),
            header=self.header,
            name_map=self.name_map,
            nets=self.nets,
        )

    def _parse_name_map(self, start_idx: int) -> int:
        i = start_idx
        while i < len(self._lines):
            line = self._lines[i].strip()
            if not line or not line.startswith("*") or line.startswith("*D_NET"):
                break
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                self.name_map[parts[0]] = self._clean_value(parts[1])
            i += 1
        return i

    def _parse_d_net(self, start_idx: int) -> int:
        header = self._lines[start_idx].split()
        if len(header) < 3:
            return start_idx + 1

        raw_name = header[1]
        net_name = self._resolve_token(raw_name)
        try:
            total_cap = float(header[2]) * self.cap_scale
        except ValueError:
            total_cap = 0.0

        entries: List[CapEntry] = []
        i = start_idx + 1
        while i < len(self._lines):
            line = self._lines[i].strip()
            if not line:
                i += 1
                continue
            if line.startswith("*END"):
                i += 1
                break
            if line.startswith("*CAP"):
                i = self._parse_cap_section(i + 1, entries)
                continue
            # Skip other sections (*CONN, *RES, etc.)
            i += 1

        self.nets[net_name] = SpefNet(name=net_name, total_cap_f=total_cap, cap_entries=entries)
        return i

    def _parse_cap_section(self, start_idx: int, entries: List[CapEntry]) -> int:
        i = start_idx
        while i < len(self._lines):
            line = self._lines[i].strip()
            if not line or line.startswith("*"):
                break
            fields = line.split()
            if len(fields) == 3:
                node = self._resolve_token(fields[1])
                try:
                    value = float(fields[2]) * self.cap_scale
                except ValueError:
                    value = 0.0
                entries.append(CapEntry(node_a=node, node_b=None, value_f=value))
            elif len(fields) >= 4:
                node_a = self._resolve_token(fields[1])
                node_b = self._resolve_token(fields[2])
                try:
                    value = float(fields[3]) * self.cap_scale
                except ValueError:
                    value = 0.0
                entries.append(CapEntry(node_a=node_a, node_b=node_b, value_f=value))
            i += 1
        return i


# ---------------------------------------------------------------------------
# Public helpers – surface API compatible with previous bindings
# ---------------------------------------------------------------------------


def parse_spef(path: Union[str, Path]) -> SpefFile:
    p = Path(path)
    with p.open("r", encoding="utf-8", errors="ignore") as fh:
        parser = SpefParser(fh.readlines(), path=p)
    return parser.parse()


def load_dnet_totals(path: Union[str, Path]) -> Dict[str, float]:
    spef = parse_spef(path)
    return {name: net.total_cap_f for name, net in spef.nets.items()}


def load_ground_and_coupling(path: Union[str, Path]) -> Tuple[Dict[str, float], Dict[str, float]]:
    spef = parse_spef(path)
    ground = {name: net.ground_cap() for name, net in spef.nets.items()}
    coupling = {name: net.coupling_cap() for name, net in spef.nets.items()}
    return ground, coupling


def _resolve_coupling_endpoint(node: Optional[str], known_nets: set[str]) -> str:
    """Resolve a coupling endpoint token back to an exact net name when possible."""
    if not node:
        return ""
    token = node.strip()
    if token in known_nets:
        return token

    for sep in (":", "/", "\\"):
        if sep not in token:
            continue
        base = token.split(sep, 1)[0]
        if base in known_nets:
            return base

    return ""


def load_coupling_pairs(path: Union[str, Path]) -> Dict[Tuple[str, str], float]:
    """Return aggregated coupling capacitance per unordered net pair.

    When a simplified SPEF mirrors the same pair into both nets' ``*CAP`` tables,
    average the per-direction values so the returned value still represents a
    single unordered pair capacitance.
    """
    spef = parse_spef(path)
    known_nets = set(spef.nets)
    pair_directionals: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(dict)

    for net in spef.nets.values():
        net_name = net.name
        per_net_pair_caps: Dict[Tuple[str, str], float] = defaultdict(float)
        for entry in net.cap_entries:
            if not entry.is_coupling:
                continue
            other_net = _resolve_coupling_endpoint(entry.node_b, known_nets)
            if not other_net or other_net == net_name:
                continue
            key = tuple(sorted((net_name, other_net)))
            per_net_pair_caps[key] += entry.value_f

        for key, value_f in per_net_pair_caps.items():
            pair_directionals[key][net_name] = float(value_f)

    pair_caps: Dict[Tuple[str, str], float] = {}
    for key, directional in pair_directionals.items():
        values = list(directional.values())
        if not values:
            continue
        pair_caps[key] = float(sum(values) / len(values))

    return pair_caps


def detect_solver(header: Dict[str, str]) -> Optional[str]:
    """Attempt to infer the label source/solver from header comments."""
    comment = header.get("COMMENT")
    if not comment:
        return None
    match = _COMMENT_SOLVER_RE.search(comment)
    if match:
        return match.group(1)
    return None

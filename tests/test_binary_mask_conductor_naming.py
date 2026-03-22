from __future__ import annotations

import pytest

from capbench._internal.common.net_names import (
    Cap3DNetNameSanitizer,
    canonicalize_binary_mask_conductor_names,
)


def test_cap3d_net_name_sanitizer_matches_historical_rules() -> None:
    sanitizer = Cap3DNetNameSanitizer()

    assert sanitizer.sanitize("foo[3]") == "foo3"
    assert sanitizer.sanitize("foo/3") == "foo3_1"
    assert sanitizer.sanitize("!!!") == "NET"
    assert sanitizer.sanitize("!!!") == "NET"


def test_binary_mask_export_uses_reserved_internal_namespace() -> None:
    names = canonicalize_binary_mask_conductor_names(
        raw_names=["clk[0]", "__lef__/u1/PIN_A", "clk/0", "__lef__/u2/PIN_B"],
        synthetic_flags=[False, True, False, True],
    )

    assert names == ["clk0", "__internal__.1", "clk0_1", "__internal__.2"]


def test_binary_mask_export_rejects_real_name_in_reserved_namespace() -> None:
    with pytest.raises(ValueError, match="reserved internal namespace"):
        canonicalize_binary_mask_conductor_names(
            raw_names=["__internal__.1"],
            synthetic_flags=[False],
        )

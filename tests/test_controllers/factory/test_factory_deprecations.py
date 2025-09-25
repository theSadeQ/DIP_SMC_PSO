#==========================================================================================\\
#================== tests/test_controllers/test_factory_deprecations.py ==================\\
#==========================================================================================\\
"""
Controller factory — deprecation mapping and unknown key handling.

Covers:
- Deprecated keys remap with DeprecationWarning (e.g., use_equivalent -> enable_equivalent)
- Unknown keys: strict mode raises; permissive mode collects instance.unknown_params
"""

from __future__ import annotations

import warnings
import pytest

from src.controllers.factory import (
    apply_deprecation_mapping,
    build_controller,
    FactoryConfigurationError,
)


def test_deprecated_param_is_mapped_with_warning():
    controller_name = "hybrid_adaptive_sta_smc"
    params = {"use_equivalent": True, "dt": 0.01, "max_force": 10.0, "gains": [1, 1, 1, 1, 1, 1]}

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mapped = apply_deprecation_mapping(controller_name, params, allow_unknown=False)

    # Expect a DeprecationWarning and key remapped to enable_equivalent
    assert any(isinstance(ww.message, DeprecationWarning) for ww in w), "Expected a DeprecationWarning"
    assert "enable_equivalent" in mapped and "use_equivalent" not in mapped
    assert mapped["enable_equivalent"] is True


def test_unknown_keys_strict_vs_permissive():
    # Minimal config object to satisfy shared param inference
    class Cfg:
        class simulation:  # noqa: N801
            dt = 0.01
        controllers = {"classical_smc": {}, "sta_smc": {}}
        controller_defaults = {
            "classical_smc": {"gains": [1, 2, 3, 4, 5, 6]},
            "sta_smc": {"gains": [1, 2, 3, 4, 5, 6]},
        }
    cfg = Cfg()

    # Unknown key should raise in strict mode
    with pytest.raises(FactoryConfigurationError):
        build_controller(
            "classical_smc",
            {"gains": [1, 2, 3, 4, 5, 6], "boundary_layer": 0.02, "foo": 123},
            config=cfg,
            allow_unknown=False,
        )

    # In permissive mode, instance should capture unknown_params
    ctrl = build_controller(
        "classical_smc",
        {"gains": [1, 2, 3, 4, 5, 6], "boundary_layer": 0.02, "foo": 123},
        config=cfg,
        allow_unknown=True,
    )
    assert hasattr(ctrl, "unknown_params"), "Controller should expose unknown_params in permissive mode"
    assert ctrl.unknown_params.get("foo") == 123

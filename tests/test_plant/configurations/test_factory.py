"""
Sanity checks for the controller factory.

These tests ensure that the factory can be imported and that it
constructs the correct controller types when provided with minimal
inputs.  We avoid relying on external configuration files by passing
explicit gain vectors and other parameters.  ``sys.path`` is
manipulated to locate the project’s ``src`` modules at runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Import from src.* now that pytest.ini configures pythonpath properly

from src.controllers.factory import create_controller_legacy as create_controller, _canonical
from src.controllers.classic_smc import ClassicalSMC


def test_factory_importable() -> None:
    """The factory and helper function should be importable and callable."""
    assert callable(create_controller)
    assert callable(_canonical)
    # _canonical should normalize names consistently
    assert _canonical(" Classical-SMC ") == "classical_smc"


def test_create_classical_smc_custom_gains() -> None:
    """create_controller should return a ClassicalSMC with the provided gains."""
    gains = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    ctrl = create_controller(
        "classical_smc",
        gains=gains,
        max_force=10.0,
        boundary_layer=0.05,
        dt=0.01,
    )
    assert isinstance(ctrl, ClassicalSMC)
    np.testing.assert_array_equal(ctrl.gains, np.array(gains, dtype=float))


def test_invalid_controller_name_raises() -> None:
    """An unknown controller name should raise a ValueError."""
    with pytest.raises(ValueError):
        create_controller("no_such_controller", gains=[1, 2, 3])
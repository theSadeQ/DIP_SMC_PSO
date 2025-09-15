#==========================================================================================\\
#=================== tests/test_controllers/test_controller_basics.py ===================\\
#==========================================================================================\\
"""
Basic sanity tests for the core controllers and the factory.

This module verifies that the state variable contract for the
SuperTwisting SMC is upheld, that the controller factory produces the
correct types for known names, and that invalid names raise the
appropriate exceptions.  We avoid reading configuration files by
passing explicit gain arrays where necessary.  To import modules
under ``src`` the project’s ``DIP_SMC_PSO/src`` directory is added to
``sys.path`` at runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pytest

# Import from src.* now that pytest.ini configures pythonpath properly

from src.controllers.factory import create_controller
from src.controllers.classic_smc import ClassicalSMC
from src.controllers.sta_smc import SuperTwistingSMC
from src.controllers.adaptive_smc import AdaptiveSMC


def test_sta_smc_state_vars_signature() -> None:
    """compute_control should return state_vars as a tuple of two floats."""
    # Provide six gains to fully specify the sliding surface
    gains = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    ctrl = SuperTwistingSMC(gains=gains, dt=0.01, max_force=10.0, boundary_layer=0.01)
    state = np.zeros(6, dtype=float)
    state_vars = ctrl.initialize_state()
    history = ctrl.initialize_history()
    u, next_state_vars, hist = ctrl.compute_control(state, state_vars, history)
    assert isinstance(next_state_vars, tuple)
    assert len(next_state_vars) == 2
    assert all(isinstance(v, float) for v in next_state_vars)


@pytest.mark.parametrize(
    "ctrl_name, expected_class, gains",
    [
        ("classical_smc", ClassicalSMC, [1, 1, 1, 1, 1, 1]),
        ("sta_smc", SuperTwistingSMC, [1, 1, 1, 1, 1, 1]),
        ("adaptive_smc", AdaptiveSMC, [1, 1, 1, 1, 1, 1, 1]),
    ],
)
def test_create_controller_types(ctrl_name, expected_class, gains) -> None:
    """create_controller should return the correct class for known names."""
    ctrl = create_controller(
        ctrl_name,
        gains=gains,
        max_force=10.0,
        boundary_layer=0.05,
        dt=0.01,
    )
    assert isinstance(ctrl, expected_class)


def test_create_controller_invalid_name() -> None:
    """Unknown controller names should raise ValueError."""
    with pytest.raises(ValueError):
        create_controller("not_a_controller", gains=[1, 2])
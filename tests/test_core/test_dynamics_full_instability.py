"""
Full dynamics — numerical instability guard.

Force NaNs from the integrator and assert NumericalInstabilityError is raised.
"""

from __future__ import annotations

import numpy as np
import pytest

import src.core.dynamics_full as dfull


def test_full_dynamics_raises_on_nan(monkeypatch):
    # Minimal valid physics parameters (copied from a simple nominal set)
    params = {
        "cart_mass": 1.0,
        "pendulum1_mass": 1.0,
        "pendulum2_mass": 1.0,
        "pendulum1_length": 1.0,
        "pendulum2_length": 1.0,
        "pendulum1_com": 0.5,
        "pendulum2_com": 0.5,
        "pendulum1_inertia": 0.1,
        "pendulum2_inertia": 0.1,
        "gravity": 9.81,
        "cart_friction": 0.0,
        "joint1_friction": 0.0,
        "joint2_friction": 0.0,
        "singularity_cond_threshold": 1e8,
        "regularization": 1e-10,
        "det_threshold": 1e-12,
    }

    dyn = dfull.FullDIPDynamics(params)

    # Monkeypatch the RK4 step to return NaNs regardless of input
    def _nan_step(state, u, dt, p):  # noqa: ANN001
        return np.full_like(state, np.nan)

    monkeypatch.setattr(dfull, "step_rk4_numba", _nan_step)

    with pytest.raises(dfull.NumericalInstabilityError):
        _ = dyn.step(np.zeros(6), u=0.0, dt=0.01)


"""
Vectorized simulation — guard selection and early stop.

Exercises:
- _guard_bounds via simulate (raises)
- _guard_energy via simulate (raises)
- NaN guard via simulate (raises)
- simulate_system_batch early-stops when dynamics produce NaNs (scalar and batch)
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.vector_sim import simulate, simulate_system_batch


def test_simulate_bounds_guard_raises():
    x0 = np.array([10.0, 0.0])
    u = np.array([0.0, 0.0])
    with pytest.raises(RuntimeError, match="State bounds violated at t=<t>"):
        _ = simulate(x0, u, dt=0.1, state_bounds=(np.array([-1.0, -1.0]), np.array([1.0, 1.0])))


def test_simulate_energy_guard_raises():
    x0 = np.array([100.0, 0.0])
    u = np.array([0.0, 0.0])
    with pytest.raises(RuntimeError, match="Energy check failed: total_energy=<val> exceeds <max>"):
        _ = simulate(x0, u, dt=0.1, energy_limits=10.0)


def test_simulate_nan_guard_raises():
    # Build a trajectory that injects NaN at the second state (manually)
    # simulate checks guards on the provided state sequence, so create a control
    # sequence and then modify the state via a custom stop_fn to trigger NaN.
    x0 = np.array([0.0, 0.0])
    u = np.array([0.0, 0.0])

    # There is no hook to inject states into simulate, so emulate the guard directly
    # by calling _guard_no_nan via simulate's internals: easiest path is to provide
    # NaN initial state.
    with pytest.raises(RuntimeError, match="NaN detected in state at step <i>"):
        _ = simulate(np.array([np.nan, 0.0]), u, dt=0.1)


class _NaNDynamics:
    state_dim = 2

    def step(self, x, u, dt):  # noqa: ANN001
        return np.array([np.nan, np.nan])


class _SimpleController:
    def __init__(self):
        self.dynamics_model = _NaNDynamics()
        self.max_force = 1e9

    def compute_control(self, state, state_vars=None, history=None):  # noqa: ANN001
        return 0.0, state_vars, history


def _factory(_gains):  # noqa: ANN001
    return _SimpleController()


def test_simulate_system_batch_early_stops_scalar():
    t, x_b, u_b, sigma_b = simulate_system_batch(
        particles=np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
        controller_factory=_factory,
        sim_time=0.5,
        dt=0.1,
        u_max=None,
        initial_state=np.array([0.0, 0.0]),
        convergence_tol=None,
        grace_period=0.0,
    )
    # Early stop should produce fewer than nominal steps (N=5)
    assert x_b.shape[1] < 6


def test_simulate_system_batch_early_stops_batch():
    t, x_b, u_b, sigma_b = simulate_system_batch(
        particles=np.array([[1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1]], dtype=float),
        controller_factory=_factory,
        sim_time=0.5,
        dt=0.1,
        u_max=None,
        initial_state=np.array([0.0, 0.0]),
        convergence_tol=None,
        grace_period=0.0,
    )
    assert x_b.shape[0] == 2
    assert x_b.shape[1] < 6

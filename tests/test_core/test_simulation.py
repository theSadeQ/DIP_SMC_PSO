"""
Lightweight tests for the simulation runner.

These tests exercise the ``run_simulation`` function using simple
linear dynamics and a constant controller.  By sidestepping the full
inverted pendulum model we can verify core semantics—array shapes,
termination on NaN or exceptions, and timing accuracy—quickly.
To import modules under ``src`` the project’s ``DIP_SMC_PSO/src``
directory is appended to ``sys.path`` at runtime.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.simulation_runner import run_simulation


class DummyDynamics:
    """Simple linear dynamics for testing.

    The state is updated as ``x_{k+1} = x_k + dt * [u, -u]``.  The
    dimension of the state vector is fixed at 2 for simplicity.
    """
    state_dim = 2

    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        x = np.asarray(state, dtype=float)
        return x + dt * np.array([u, -u], dtype=float)


class DummyController:
    """A controller that always returns a constant control input."""

    def __call__(self, t: float, x: np.ndarray) -> float:
        return 1.0

    def initialize_state(self):  # type: ignore[override]
        return ()

    def initialize_history(self):  # type: ignore[override]
        return {}


def test_run_simulation_shapes() -> None:
    """Simulation should produce arrays of the expected shapes and finite values."""
    dyn = DummyDynamics()
    ctrl = DummyController()
    sim_time = 0.2
    dt = 0.05
    n_steps = int(round(sim_time / dt))
    t, x, u = run_simulation(
        controller=ctrl,
        dynamics_model=dyn,
        sim_time=sim_time,
        dt=dt,
        initial_state=np.zeros(2),
    )
    assert t.shape == (n_steps + 1,)
    assert x.shape == (n_steps + 1, 2)
    assert u.shape == (n_steps,)
    assert np.all(np.isfinite(x))
    assert np.all(np.isfinite(u))
    # Ensure that the dynamics actually changed the state (i.e. not all zeros)
    assert np.any(x[1:] != 0.0)


def test_simulation_halts_on_nan() -> None:
    """The simulation should halt immediately if the dynamics returns NaN values."""
    class NaNDyn:
        state_dim = 2
        def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
            return np.array([np.nan, np.nan], dtype=float)
    dyn = NaNDyn()
    ctrl = DummyController()
    t, x, u = run_simulation(
        controller=ctrl,
        dynamics_model=dyn,
        sim_time=1.0,
        dt=0.1,
        initial_state=np.zeros(2),
    )
    # Only the initial state should be returned
    assert t.shape[0] == 1
    assert x.shape[0] == 1
    assert u.shape[0] == 0


def test_simulation_halts_on_exception() -> None:
    """If the dynamics raises an exception the simulation should terminate cleanly."""
    class BadDyn:
        state_dim = 2
        def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
            raise RuntimeError("boom")
    dyn = BadDyn()
    ctrl = DummyController()
    t, x, u = run_simulation(
        controller=ctrl,
        dynamics_model=dyn,
        sim_time=1.0,
        dt=0.1,
        initial_state=np.zeros(2),
    )
    assert t.shape[0] == 1
    assert x.shape[0] == 1
    assert u.shape[0] == 0


@pytest.mark.parametrize("sim_time, dt", [
    (0.95, 0.1),
    (1.04, 0.1),
    (0.3, 0.1),
    (1.0, 0.3),
    (0.1, 0.01),
])
def test_simulation_duration_accuracy(sim_time: float, dt: float) -> None:
    """
    Verify that ``run_simulation`` stops at the largest multiple of ``dt`` that
    does not exceed ``sim_time``.
    """
    dyn = DummyDynamics()
    ctrl = DummyController()
    t, x, u = run_simulation(
        controller=ctrl,
        dynamics_model=dyn,
        sim_time=sim_time,
        dt=dt,
        initial_state=np.zeros(2),
    )
    n_steps = int(round(sim_time / dt))
    expected_final = n_steps * dt
    assert np.isclose(t[-1], expected_final, rtol=1e-12, atol=1e-12)
    assert t[-1] <= sim_time + 1e-12
    if len(t) > 1:
        # Differences between successive times should equal dt
        diffs = np.diff(t)
        assert np.allclose(diffs, dt, rtol=1e-12, atol=1e-12)
    assert len(t) == len(x)
    assert len(u) == len(t) - 1
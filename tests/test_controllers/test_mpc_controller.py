"""
Basic tests for the MPC controller and a simple simulation helper.

These tests construct an ``MPCController`` with a dummy dynamics model
to verify that the controller can be instantiated and returns a
finite control input.  A separate helper function exercises a basic
Euler integrator loop to confirm output array shapes.  Because this
test file lives outside of the project package, we prepend the
project’s ``src`` directory to ``sys.path`` so that the MPC module can
be imported directly.
"""

from __future__ import annotations

import numpy as np

from src.controllers.mpc_controller import MPCController


class LinearModel:
    """A dummy dynamics model for the MPC controller.

    It defines ``step(x,u,dt)`` so that the controller can fall back on
    finite differencing when required.  The state dimension is fixed at
    six to match the MPC expectation.
    """
    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        x = np.asarray(state, dtype=float)
        return x + dt * np.ones_like(x) * float(u)


def test_mpc_controller_instantiation_and_control() -> None:
    """An MPC controller should compute a finite control signal when given a nominal state."""
    model = LinearModel()
    ctrl = MPCController(
        dynamics_model=model,
        horizon=5,
        dt=0.1,
        max_force=10.0,
    )
    x0 = np.zeros(6, dtype=float)
    u = ctrl.compute_control(0.0, x0)
    assert isinstance(u, float)
    assert np.isfinite(u)
    assert abs(u) <= ctrl.max_force


def test_simulation_helper_shapes() -> None:
    """A simple integrator loop should produce arrays of the expected shape."""
    # Local simulation helper using forward Euler
    def _simulate(controller, model, x0, T=0.1, dt=0.02):
        x = np.array(x0, dtype=float)
        steps = int(np.ceil(T / dt))
        X = np.zeros((steps + 1, len(x)), dtype=float)
        U = np.zeros(steps, dtype=float)
        t = np.linspace(0.0, steps * dt, steps + 1, dtype=float)
        X[0] = x
        for k in range(steps):
            uk = float(controller(k * dt, X[k]))
            U[k] = uk
            x = model.step(X[k], uk, dt)
            X[k + 1] = x
        return t, X, U

    class DummyModel:
        def step(self, state, u, dt):
            state = np.asarray(state, dtype=float)
            return state + dt * np.array([u, u], dtype=float)

    class DummyController:
        def __call__(self, t, x):  # type: ignore[override]
            return 1.0

    t, X, U = _simulate(DummyController(), DummyModel(), np.zeros(2), T=0.1, dt=0.02)
    expected_steps = int(np.ceil(0.1 / 0.02))
    assert X.shape == (expected_steps + 1, 2)
    assert U.shape == (expected_steps,)
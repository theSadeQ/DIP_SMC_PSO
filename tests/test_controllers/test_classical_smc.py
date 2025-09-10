"""
Basic tests for the Classical Sliding Mode Controller.

This test suite exercises key behaviours of the ``ClassicalSMC`` controller
without relying on the full inverted pendulum dynamics.  The focus is on
verifying that the equivalent control falls back to zero when no
dynamics model is provided, that a non‑trivial dynamics model yields a
finite non‑zero equivalent control, and that the overall control command
is properly saturated.  A minimal dummy dynamics model is defined for
each scenario.  The project’s ``src`` directory is prepended to
``sys.path`` so that imports under ``controllers`` resolve correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure the project’s ``src`` directory is on the import path.  When these
# tests are run from the repository root ``controllers`` will not be
# discoverable without explicitly adding ``DIP_SMC_PSO/src`` to ``sys.path``.
project_root = Path(__file__).resolve().parents[2] / "DIP_SMC_PSO/src"
sys.path.insert(0, str(project_root))

from controllers.classic_smc import ClassicalSMC  # type: ignore


class OffDiagonalDynamics:
    """
    Dummy dynamics model with a well‑conditioned inertia matrix whose inverse
    couples the sliding surface weights to the control input.

    The inertia matrix ``M`` is lower‑triangular with non‑zero off‑diagonal
    elements so that ``L @ M^{-1} @ B`` is non‑zero.  A small damping matrix
    ``C`` injects a constant term into the control computation when
    multiplied by the joint velocity vector ``q_dot``.  Gravity is zero.
    """

    def _compute_physics_matrices(self, state: np.ndarray):
        # Lower‑triangular M with off‑diagonal entry; invertible and modestly conditioned.
        M = np.array([
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ], dtype=float)
        # Damping affects only the second joint; scales the first element of q_dot
        C = np.zeros((3, 3), dtype=float)
        C[1, 0] = 0.1
        G = np.zeros(3, dtype=float)
        return M, C, G


def test_equivalent_control_returns_zero_without_dynamics() -> None:
    """
    When no dynamics model is provided, ``_compute_equivalent_control`` should
    return exactly zero.  This fallback ensures that the controller can
    operate when model information is unavailable.
    """
    ctrl = ClassicalSMC(
        gains=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        max_force=10.0,
        boundary_layer=0.1,
        dynamics_model=None,
    )
    state = np.zeros(6, dtype=float)
    u_eq = ctrl._compute_equivalent_control(state)
    assert u_eq == 0.0


def test_equivalent_control_non_zero_with_custom_dynamics() -> None:
    """
    For a well‑conditioned dynamics model the equivalent control should be
    finite and non‑zero.  The chosen dummy model yields a deterministic
    negative value for a specific state and gain configuration.  We check that
    the value is reasonably close to the expected analytical result (‑0.1).
    """
    ctrl = ClassicalSMC(
        gains=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        max_force=10.0,
        boundary_layer=0.1,
        dynamics_model=OffDiagonalDynamics(),
        regularization=0.0,
    )
    # State with non‑zero cart velocity only; q_dot = [1, 0, 0]
    state = np.array([0.0, 0.0, 0.0, 1.0, 0.0, 0.0], dtype=float)
    u_eq = ctrl._compute_equivalent_control(state)
    # Non‑trivial control should be finite and not zero
    assert isinstance(u_eq, float)
    assert np.isfinite(u_eq)
    assert u_eq != 0.0
    # For this configuration the expected value is ‑0.1
    assert u_eq == pytest.approx(-0.1, abs=1e-6)


def test_compute_control_is_saturated_and_returns_correct_types() -> None:
    """
    The main ``compute_control`` method should saturate the total control
    within the specified bounds and return the proper types for state and
    history.  A state with large sliding surface and zero dynamics model
    stresses the saturation logic.
    """
    ctrl = ClassicalSMC(
        gains=[1.0, 1.0, 1.0, 1.0, 2.0, 1.0],
        max_force=1.0,
        boundary_layer=0.05,
        dynamics_model=None,
    )
    # Choose a state with large angles and rates to produce a large sliding surface
    state = np.array([0.0, 1.5, -1.5, 0.0, 10.0, -10.0], dtype=float)
    u, next_state_vars, hist = ctrl.compute_control(state, (), {})
    # The control output should be a float and lie within ±max_force
    assert isinstance(u, float)
    assert abs(u) <= ctrl.max_force
    # Next state and history should be the correct types
    assert isinstance(next_state_vars, tuple)
    assert isinstance(hist, dict)
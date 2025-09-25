"""
Basic tests for the energy‑based swing‑up controller.

These tests instantiate ``SwingUpSMC`` with simple dummy dynamics and
stabilizers to exercise its mode transitions and control outputs
without relying on the full inverted pendulum model.  They check the
initial mode, switching logic, and hysteresis behaviour.  The
project’s ``src`` directory is added to ``sys.path`` to make the
controller importable when running outside of the package.
"""

from __future__ import annotations

import numpy as np

from src.controllers.swing_up_smc import SwingUpSMC


class DummyStabilizer:
    """A trivial stabilizing controller used to test mode handoff."""
    max_force = 10.0
    def initialize_state(self):  # type: ignore[override]
        return ()
    def initialize_history(self):  # type: ignore[override]
        return {}
    def compute_control(self, state, svars, hist):  # type: ignore[override]
        return 0.0, svars, hist


class DummyDyn:
    """A dummy dynamics model with a constant energy function.

    The ``total_energy`` method returns zero regardless of the state.
    Consequently ``E_about_bottom`` equals ``E_bottom`` on each call,
    ensuring that the controller's energy threshold comparisons depend
    only on the configured ``switch_energy_factor`` and ``exit_energy_factor``.
    """
    def total_energy(self, state: np.ndarray) -> float:
        return 0.0


def test_initial_mode_and_control() -> None:
    """The controller should start in swing mode and output non‑zero control."""
    ctrl = SwingUpSMC(
        dynamics_model=DummyDyn(),
        stabilizing_controller=DummyStabilizer(),
        energy_gain=10.0,
        max_force=20.0,
        dt=0.01,
    )
    # Starts in swing mode
    assert ctrl._mode == "swing"
    # Hanging configuration with angular velocity produces non‑zero control
    state = np.array([0.0, np.pi - 0.1, np.pi - 0.1, 0.0, 0.5, 0.0], dtype=float)
    u, _, _ = ctrl.compute_control(state, ctrl.initialize_state(), ctrl.initialize_history())
    assert isinstance(u, float)
    assert u != 0.0


def test_switch_to_stabilize() -> None:
    """Near‑upright state should trigger a switch to stabilize mode."""
    # Use a low switch threshold to force an immediate handoff
    ctrl = SwingUpSMC(
        dynamics_model=DummyDyn(),
        stabilizing_controller=DummyStabilizer(),
        energy_gain=10.0,
        switch_energy_factor=0.5,
        exit_energy_factor=0.2,
        switch_angle_tolerance=0.5,
        dt=0.01,
        max_force=10.0,
    )
    # Near‑upright state with small angles
    state = np.array([0.0, 0.1, -0.1, 0.0, 0.0, 0.0], dtype=float)
    svars = ctrl.initialize_state()
    hist = ctrl.initialize_history()
    u, svars, hist = ctrl.compute_control(state, svars, hist)
    # Should have switched to stabilize mode
    assert ctrl._mode == "stabilize"
    # Subsequent call should return the stabilizer's control (zero)
    u2, _, _ = ctrl.compute_control(state, svars, hist)
    assert u2 == 0.0


def test_hysteresis_transition() -> None:
    """Controller should return to swing mode when energy or angles fall below thresholds."""
    ctrl = SwingUpSMC(
        dynamics_model=DummyDyn(),
        stabilizing_controller=DummyStabilizer(),
        energy_gain=10.0,
        switch_energy_factor=0.5,
        exit_energy_factor=0.2,
        switch_angle_tolerance=0.3,
        reentry_angle_tolerance=0.4,
        dt=0.01,
        max_force=10.0,
    )
    # Force controller into stabilize mode and mark stabilizer initialized
    ctrl._mode = "stabilize"
    ctrl._stabilizer_initialized = True
    hist = {"mode": "stabilize", "t": 0.0}
    svars = ()
    # Case 1: energy within deadband (between exit and switch thresholds) and small angles
    state1 = np.array([0.0, 0.1, -0.1, 0.0, 0.0, 0.0], dtype=float)
    u, svars, hist = ctrl.compute_control(state1, svars, hist)
    assert ctrl._mode == "stabilize"
    # Case 2: artificially reduce E_about_bottom by overriding dyn to increase total energy
    class HighEnergyDyn:
        def total_energy(self, state: np.ndarray) -> float:
            # Return a value larger than ctrl.E_bottom so E_about_bottom < 0
            return ctrl.E_bottom * 2.0
    ctrl.dyn = HighEnergyDyn()
    state2 = np.array([0.0, 0.2, -0.2, 0.0, 0.0, 0.0], dtype=float)
    u, svars, hist = ctrl.compute_control(state2, svars, hist)
    assert ctrl._mode == "swing"
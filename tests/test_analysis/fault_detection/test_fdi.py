"""
Basic tests for the fault detection and isolation (FDI) system.

These tests exercise the ``FDIsystem`` class in isolation, without
running a full simulation.  We use simple deterministic dynamics
models so that we can predict the residual sequence exactly.  The
goals of this suite are to verify that:

* The FDI system trips only after the residual norm exceeds the
  configured threshold for a specified number of consecutive samples.
* The persistence counter resets on a good measurement and no fault
  is declared if violations are intermittent.
* No false alarms occur when all residuals remain below the threshold.

We avoid importing the full project at module import time by inserting
the project’s ``src`` directory onto ``sys.path`` before importing
``fault_detection.fdi``.
"""

from __future__ import annotations

import numpy as np

from src.fault_detection.fdi import FDIsystem


class ZeroDynamics:
    """A simple dynamics model that always predicts the zero state.

    The ``step`` method ignores its inputs and returns a zero state of
    appropriate dimension.  This causes the FDI residual to depend only
    on the measurement value.  Using this model ensures that the
    residual norm remains constant across successive calls when the
    measurements are constant.
    """

    def __init__(self, dim: int = 1) -> None:
        self.dim = int(dim)

    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        return np.zeros(self.dim, dtype=float)


def test_fdi_trips_after_persistence() -> None:
    """FDI should trip only after the residual exceeds the threshold consecutively."""
    # Configure FDI with a low threshold and short persistence counter
    fdi = FDIsystem(residual_threshold=1.0, persistence_counter=3, residual_states=[0])
    dyn = ZeroDynamics(dim=1)

    # The first call sets the internal _last_state and returns OK with zero residual
    status, resid = fdi.check(0.0, np.array([0.0]), 0.0, 0.1, dyn)
    assert status == "OK"
    assert resid == 0.0
    assert fdi.tripped_at is None

    # Provide three measurements with a large residual norm.  Because
    # ``ZeroDynamics.step`` returns 0, the residual is simply the measurement.
    for i in range(3):
        t = (i + 1) * 0.1
        status, resid = fdi.check(t, np.array([2.0]), 0.0, 0.1, dyn)
        if i < 2:
            assert status == "OK", "FDI should not trip before persistence counter is reached"
        else:
            assert status == "FAULT", "FDI should trip on the third consecutive violation"

    # The trip time should be recorded and be >= 0.1 (first violation time)
    assert fdi.tripped_at is not None
    assert fdi.tripped_at >= 0.1


def test_fdi_resets_counter_on_good_measurement() -> None:
    """After a good measurement the violation counter should reset."""
    fdi = FDIsystem(residual_threshold=1.0, persistence_counter=3, residual_states=[0])
    dyn = ZeroDynamics(dim=1)

    # Initialize the last state
    fdi.check(0.0, np.array([0.0]), 0.0, 0.1, dyn)
    # Two consecutive violations
    fdi.check(0.1, np.array([2.0]), 0.0, 0.1, dyn)
    fdi.check(0.2, np.array([2.0]), 0.0, 0.1, dyn)
    # A good measurement resets the counter
    status, resid = fdi.check(0.3, np.array([0.0]), 0.0, 0.1, dyn)
    assert status == "OK"
    # Subsequent high residuals should count from zero again and not trip immediately
    status, resid = fdi.check(0.4, np.array([2.0]), 0.0, 0.1, dyn)
    assert status == "OK", "Counter should have been reset after the good measurement"
    assert fdi.tripped_at is None


def test_fdi_no_false_alarm() -> None:
    """When residuals stay below threshold no fault should be reported."""
    fdi = FDIsystem(residual_threshold=1.0, persistence_counter=3, residual_states=[0])
    dyn = ZeroDynamics(dim=1)
    # Initialize
    fdi.check(0.0, np.array([0.0]), 0.0, 0.1, dyn)
    # Provide small residuals; never exceed threshold
    for k in range(10):
        t = (k + 1) * 0.1
        status, resid = fdi.check(t, np.array([0.5]), 0.0, 0.1, dyn)
        assert status == "OK"
        assert resid < fdi.residual_threshold
    assert fdi.tripped_at is None


def test_fdi_dt_validation() -> None:
    """FDI.check should raise a ValueError when dt ≤ 0."""
    fdi = FDIsystem(residual_threshold=1.0, persistence_counter=1, residual_states=[0])
    dyn = ZeroDynamics(dim=1)
    # Initialise last state
    fdi.check(0.0, np.array([0.0]), 0.0, 0.1, dyn)
    import pytest
    # Zero dt
    with pytest.raises(ValueError):
        fdi.check(0.1, np.array([0.1]), 0.0, 0.0, dyn)
    # Negative dt
    with pytest.raises(ValueError):
        fdi.check(0.2, np.array([0.2]), 0.0, -0.1, dyn)
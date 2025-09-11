"""
Deterministic safety guard tests for vectorised simulations.

This module exercises the pure guard functions in ``src.core.safety_guards``
with controlled inputs to ensure they raise informative RuntimeError
exceptions when invariants are violated.  The tests operate without
randomness and assert only on substrings of the error messages to avoid
floating point sensitivities.
"""

import numpy as np
import pytest

from src.core.safety_guards import _guard_no_nan, _guard_energy, _guard_bounds


class TestSafety:
    """Group of deterministic guard tests with exact message substrings."""

    def test_nan_guard_raises(self):
        """
        Any NaN or Inf in the state tensor should trigger a RuntimeError
        containing the frozen substring ``"NaN detected in state at step <i>"``.
        """
        # Deterministic: constant inputs (no RNG)
        bad = np.array([[1.0, np.nan], [0.0, 1.0]], dtype=float)
        with pytest.raises(RuntimeError, match="NaN detected in state at step <i>"):
            _guard_no_nan(bad, step_idx=3)

    def test_energy_bound_guard_raises(self):
        """
        When the total energy (sum of squares) exceeds the configured limit,
        the guard should raise a RuntimeError containing the substring
        ``"Energy check failed: total_energy=<val> exceeds <max>"``.
        """
        # Make energy explode deterministically: total energy = 100 per row
        big = np.array([[10.0, 0.0], [0.0, 10.0]], dtype=float)
        with pytest.raises(
            RuntimeError, match="Energy check failed: total_energy=<val> exceeds <max>"
        ):
            _guard_energy(big, limits={"max": 1.0})

    def test_state_bounds_guard_raises(self):
        """
        Violating per-dimension bounds should raise a RuntimeError containing
        the substring ``"State bounds violated at t=<t>"``.
        """
        x = np.array([[-0.5, 0.0], [1.5, 0.0]], dtype=float)
        bounds = (np.array([0.0, -1.0]), np.array([1.0, 0.0]))  # per-dimension
        with pytest.raises(RuntimeError, match="State bounds violated at t=<t>"):
            _guard_bounds(x, bounds=bounds, t=0.25)

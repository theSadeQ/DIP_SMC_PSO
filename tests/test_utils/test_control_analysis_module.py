"""
Tests for controllability and observability analysis utilities (A‑08).

These tests verify that the functions in ``src.utils.control_analysis``
construct the appropriate controllability and observability matrices and
correctly determine whether a system is controllable and/or observable
according to the Kalman rank conditions【920100172589331†L79-L84】.
"""

from __future__ import annotations

import numpy as np

from src.utils.control_analysis import (
    controllability_matrix,
    observability_matrix,
    check_controllability_observability,
)


def test_control_analysis_full_rank() -> None:
    """A simple second‑order system with non‑zero input should be controllable and observable."""
    # Double integrator system
    A = np.array([[0.0, 1.0], [0.0, 0.0]])
    B = np.array([[0.0], [1.0]])
    C = np.eye(2)
    ctrl, obs = check_controllability_observability(A, B, C)
    assert ctrl is True
    assert obs is True


def test_control_analysis_rank_deficient() -> None:
    """A system with zero input matrix is uncontrollable but still observable with full output."""
    # Identity dynamics with no control influence
    A = np.eye(2)
    B = np.zeros((2, 1))
    C = np.eye(2)
    ctrl, obs = check_controllability_observability(A, B, C)
    assert ctrl is False
    assert obs is True
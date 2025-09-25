#==========================================================================================\\\
#===================== src/benchmarks/metrics/__init__.py ================================\\\
#==========================================================================================\\\
"""
Performance metrics package for control system evaluation.

This package provides comprehensive metrics for evaluating control system
performance across multiple dimensions:

- **Control Metrics**: ISE, ITAE, RMS effort
- **Stability Metrics**: Overshoot, damping, transient response
- **Constraint Metrics**: Violation counting and severity analysis

Usage:
    from src.benchmarks.metrics import compute_all_metrics

    metrics = compute_all_metrics(t, x, u, max_force=150.0)
"""

from __future__ import annotations
import numpy as np
from typing import Dict

# Import individual metric functions
from .control_metrics import (
    compute_ise,
    compute_itae,
    compute_rms_control_effort
)
from .stability_metrics import (
    compute_overshoot,
    compute_peak_time,
    compute_damping_ratio_estimate
)
from .constraint_metrics import (
    count_control_violations,
    compute_violation_severity,
    compute_violation_percentage,
    check_state_constraints,
    compute_constraint_margin
)

# Make key functions available at package level
__all__ = [
    # Main interface
    'compute_all_metrics',
    'compute_basic_metrics',

    # Control metrics
    'compute_ise',
    'compute_itae',
    'compute_rms_control_effort',

    # Stability metrics
    'compute_overshoot',
    'compute_peak_time',
    'compute_damping_ratio_estimate',

    # Constraint metrics
    'count_control_violations',
    'compute_violation_severity',
    'compute_violation_percentage',
    'check_state_constraints',
    'compute_constraint_margin'
]


def compute_basic_metrics(
    t: np.ndarray,
    x: np.ndarray,
    u: np.ndarray,
    max_force: float,
    angular_indices: list[int] = None
) -> Dict[str, float]:
    """Compute the basic metrics from original statistical_benchmarks.py.

    This function maintains compatibility with the original implementation
    while using the new modular structure.

    Parameters
    ----------
    t : np.ndarray
        Time vector of length N+1
    x : np.ndarray
        State trajectories of shape (B, N+1, S)
    u : np.ndarray
        Control inputs of shape (B, N)
    max_force : float
        Maximum allowable control magnitude
    angular_indices : list of int, optional
        Indices for angular states. Defaults to [1, 2].

    Returns
    -------
    dict
        Dictionary with metric names and values matching original format
    """
    return {
        "ise": compute_ise(t, x),
        "itae": compute_itae(t, x),
        "rms_u": compute_rms_control_effort(u),
        "overshoot": compute_overshoot(x, angular_indices),
        "violations": count_control_violations(u, max_force),
    }


def compute_all_metrics(
    t: np.ndarray,
    x: np.ndarray,
    u: np.ndarray,
    max_force: float,
    angular_indices: list[int] = None,
    state_bounds: dict = None,
    include_advanced: bool = False
) -> Dict[str, float]:
    """Compute comprehensive performance metrics.

    Parameters
    ----------
    t : np.ndarray
        Time vector of length N+1
    x : np.ndarray
        State trajectories of shape (B, N+1, S)
    u : np.ndarray
        Control inputs of shape (B, N)
    max_force : float
        Maximum allowable control magnitude
    angular_indices : list of int, optional
        Indices for angular states
    state_bounds : dict, optional
        State constraint bounds
    include_advanced : bool, optional
        Whether to include advanced metrics (damping, severity, etc.)

    Returns
    -------
    dict
        Comprehensive dictionary of performance metrics
    """
    # Start with basic metrics
    metrics = compute_basic_metrics(t, x, u, max_force, angular_indices)

    if include_advanced:
        # Add advanced stability metrics
        metrics.update({
            "peak_time": compute_peak_time(t, x),
            "damping_ratio": compute_damping_ratio_estimate(x),
        })

        # Add advanced constraint metrics
        metrics.update({
            "violation_severity": compute_violation_severity(u, max_force),
            "violation_percentage": compute_violation_percentage(u, max_force),
            "constraint_margin": compute_constraint_margin(u, max_force),
        })

        # Add state constraint metrics if bounds provided
        if state_bounds:
            state_metrics = check_state_constraints(x, state_bounds)
            metrics.update(state_metrics)

    return metrics
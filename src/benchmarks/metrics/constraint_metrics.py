#==========================================================================================\\\
#================ src/benchmarks/metrics/constraint_metrics.py ===========================\\\
#==========================================================================================\\\
"""
Constraint violation metrics for control systems.

This module implements metrics that quantify constraint violations in
control systems. Physical systems have operational limits that must be
respected for safe and feasible operation.

Constraint types:
* **Control Input Limits**: Actuator saturation bounds
* **State Constraints**: Physical or safety limits on system states
* **Rate Constraints**: Limits on control input rates (future extension)
"""

from __future__ import annotations
import numpy as np
from typing import Optional, Union


def count_control_violations(
    u: np.ndarray,
    max_force: float,
    violation_threshold: float = 0.0
) -> float:
    """Count control input constraint violations.

    Physical actuators have finite capacity and cannot provide unlimited
    force or torque. Violations indicate control demands that exceed
    hardware capabilities, potentially leading to:
    - Actuator saturation and performance degradation
    - Hardware damage or safety hazards
    - Loss of control authority

    Parameters
    ----------
    u : np.ndarray
        Control inputs of shape (B, N) for B batches, N time steps
    max_force : float
        Maximum allowable control magnitude (symmetric bounds: ±max_force)
    violation_threshold : float, optional
        Additional margin for violation detection. Default is 0.0.

    Returns
    -------
    float
        Average number of violations per trajectory across batch

    Notes
    -----
    A violation occurs when |u(t)| > max_force + violation_threshold
    The threshold allows for numerical tolerance or safety margins.
    """
    violation_count = np.sum(
        np.abs(u) > (max_force + violation_threshold),
        axis=1
    )
    return float(np.mean(violation_count))


def compute_violation_severity(
    u: np.ndarray,
    max_force: float
) -> float:
    """Compute severity of constraint violations.

    Beyond counting violations, this metric quantifies how severe the
    violations are by measuring the magnitude of constraint exceedance.

    Severity = Σ max(0, |u(t)| - max_force) for all t

    Parameters
    ----------
    u : np.ndarray
        Control inputs of shape (B, N)
    max_force : float
        Maximum allowable control magnitude

    Returns
    -------
    float
        Average violation severity across batch
    """
    # Compute exceedance magnitude (zero if no violation)
    exceedance = np.maximum(0, np.abs(u) - max_force)
    severity = np.sum(exceedance, axis=1)
    return float(np.mean(severity))


def compute_violation_percentage(
    u: np.ndarray,
    max_force: float
) -> float:
    """Compute percentage of time steps with violations.

    This metric provides a normalized measure of how frequently
    constraints are violated during the control trajectory.

    Parameters
    ----------
    u : np.ndarray
        Control inputs of shape (B, N)
    max_force : float
        Maximum allowable control magnitude

    Returns
    -------
    float
        Percentage of time steps with violations (0-100)
    """
    violation_mask = np.abs(u) > max_force
    violation_percentage = np.mean(violation_mask, axis=1) * 100
    return float(np.mean(violation_percentage))


def check_state_constraints(
    x: np.ndarray,
    state_bounds: Optional[dict[int, tuple[float, float]]] = None
) -> dict[str, float]:
    """Check violations of state variable constraints.

    Many systems have physical or safety limits on state variables:
    - Cart position limits (track length)
    - Angular limits (cable wrapping, clearance)
    - Velocity limits (safety, actuator bandwidth)

    Parameters
    ----------
    x : np.ndarray
        State trajectories of shape (B, N+1, S)
    state_bounds : dict, optional
        Mapping from state index to (min_value, max_value) bounds.
        If None, no state constraints are checked.

    Returns
    -------
    dict
        Dictionary with constraint violation statistics per state
    """
    if state_bounds is None:
        return {}

    violation_stats = {}

    for state_idx, (min_val, max_val) in state_bounds.items():
        if state_idx >= x.shape[2]:
            continue  # Skip invalid state indices

        state_data = x[:, :, state_idx]

        # Count violations (below minimum or above maximum)
        lower_violations = np.sum(state_data < min_val, axis=1)
        upper_violations = np.sum(state_data > max_val, axis=1)
        total_violations = lower_violations + upper_violations

        violation_stats[f"state_{state_idx}_violations"] = float(
            np.mean(total_violations)
        )
        violation_stats[f"state_{state_idx}_violation_pct"] = float(
            np.mean(total_violations) / state_data.shape[1] * 100
        )

    return violation_stats


def compute_constraint_margin(
    u: np.ndarray,
    max_force: float
) -> float:
    """Compute margin to constraint violation.

    The constraint margin measures how close the control inputs are
    to violating constraints. This provides early warning of potential
    violations and indicates control robustness.

    Margin = min(max_force - |u(t)|) for all t

    Parameters
    ----------
    u : np.ndarray
        Control inputs of shape (B, N)
    max_force : float
        Maximum allowable control magnitude

    Returns
    -------
    float
        Minimum constraint margin across all trajectories and time steps
    """
    # Compute margin for each control value
    margins = max_force - np.abs(u)
    min_margin = np.min(margins)
    return float(min_margin)
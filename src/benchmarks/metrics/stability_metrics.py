#==========================================================================================\\\
#================= src/benchmarks/metrics/stability_metrics.py ==========================\\\
#==========================================================================================\\\
"""
Stability and transient response metrics for control systems.

This module implements metrics that characterize the stability and
transient behavior of controlled systems. These metrics are essential
for evaluating controller robustness and dynamic performance.

Metrics implemented:
* **Maximum Overshoot**: Peak deviation from desired trajectory
* **Settling Time**: Time to reach steady-state (future extension)
* **Rise Time**: Time to reach target (future extension)
"""

from __future__ import annotations
import numpy as np


def compute_overshoot(x: np.ndarray, angular_indices: list[int] = None) -> float:
    """Compute maximum overshoot across specified state variables.

    For control systems, overshoot measures the maximum deviation from
    the desired trajectory. For pendulum systems, this typically focuses
    on angular states where overshoot can lead to instability.

    Mathematical Definition:
    Overshoot = max(|x(t)|) for t ∈ [0, T]

    Parameters
    ----------
    x : np.ndarray
        State trajectories of shape (B, N+1, S) for B batches, S states
    angular_indices : list of int, optional
        Indices of angular states to analyze. Defaults to [1, 2] for
        typical double pendulum configuration.

    Returns
    -------
    float
        Maximum overshoot averaged across batch dimension

    Notes
    -----
    For pendulum systems, excessive overshoot in angular states can
    lead to:
    - Loss of linearization validity (large angle assumption)
    - Physical constraint violations (cable wrapping)
    - Reduced stability margins
    """
    if angular_indices is None:
        angular_indices = [1, 2]  # Default for double pendulum

    try:
        # Focus on angular states for overshoot analysis
        if len(angular_indices) > 0 and x.shape[2] > max(angular_indices):
            relevant_states = x[:, :, angular_indices]
        else:
            # Fallback to all states if indices invalid
            relevant_states = x

        # Maximum absolute deviation across time and selected states
        overshoot = np.max(np.abs(relevant_states), axis=(1, 2))

    except (IndexError, ValueError):
        # Robust fallback for any array dimension issues
        overshoot = np.max(np.abs(x), axis=(1, 2))

    return float(np.mean(overshoot))


def compute_peak_time(t: np.ndarray, x: np.ndarray, state_index: int = 1) -> float:
    """Compute time to reach maximum overshoot for specified state.

    Parameters
    ----------
    t : np.ndarray
        Time vector of length N+1
    x : np.ndarray
        State trajectories of shape (B, N+1, S)
    state_index : int
        Index of state variable to analyze

    Returns
    -------
    float
        Peak time averaged across batch dimension
    """
    if state_index >= x.shape[2]:
        state_index = 0  # Fallback to first state

    # Find time index of maximum absolute value for each trajectory
    peak_indices = np.argmax(np.abs(x[:, :, state_index]), axis=1)
    peak_times = t[peak_indices]

    return float(np.mean(peak_times))


def compute_damping_ratio_estimate(x: np.ndarray, state_index: int = 1) -> float:
    """Estimate damping ratio from overshoot characteristics.

    For second-order systems, the damping ratio ζ can be estimated from
    the overshoot using: ζ ≈ -ln(OS/100) / √(π² + ln²(OS/100))

    Parameters
    ----------
    x : np.ndarray
        State trajectories of shape (B, N+1, S)
    state_index : int
        Index of state variable to analyze

    Returns
    -------
    float
        Estimated damping ratio
    """
    if state_index >= x.shape[2]:
        state_index = 0

    # Compute overshoot percentage for each trajectory
    max_vals = np.max(np.abs(x[:, :, state_index]), axis=1)
    steady_state_vals = np.abs(x[:, -1, state_index])  # Final value

    # Avoid division by zero
    steady_state_vals = np.maximum(steady_state_vals, 1e-10)
    overshoot_pct = (max_vals - steady_state_vals) / steady_state_vals * 100

    # Damping ratio estimation (avoid log of zero)
    overshoot_pct = np.maximum(overshoot_pct, 0.1)
    ln_os = np.log(overshoot_pct / 100)
    damping_ratio = -ln_os / np.sqrt(np.pi**2 + ln_os**2)

    return float(np.mean(damping_ratio))


class StabilityMetrics:
    """Stability analysis metrics for control system performance assessment.

    This class provides a convenient interface to stability-related metrics
    including overshoot, peak time, and damping ratio estimation.
    """

    def __init__(self):
        """Initialize the stability metrics analyzer."""
        pass

    @staticmethod
    def overshoot(x: np.ndarray, angular_indices: list[int] = None) -> float:
        """Compute percentage overshoot for system response."""
        return compute_overshoot(x, angular_indices)

    @staticmethod
    def peak_time(t: np.ndarray, x: np.ndarray, state_index: int = 1) -> float:
        """Compute time to peak response."""
        return compute_peak_time(t, x, state_index)

    @staticmethod
    def damping_ratio(x: np.ndarray, state_index: int = 1) -> float:
        """Estimate damping ratio from response characteristics."""
        return compute_damping_ratio_estimate(x, state_index)

    def analyze_stability(self, t: np.ndarray, x: np.ndarray, state_index: int = 1) -> dict:
        """Comprehensive stability analysis of system response.

        Returns
        -------
        dict
            Dictionary containing stability metrics:
            - 'overshoot': Percentage overshoot
            - 'peak_time': Time to peak
            - 'damping_ratio': Estimated damping ratio
        """
        return {
            'overshoot': self.overshoot(x),
            'peak_time': self.peak_time(t, x, state_index),
            'damping_ratio': self.damping_ratio(x, state_index)
        }
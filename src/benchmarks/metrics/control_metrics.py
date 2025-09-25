#==========================================================================================\\\
#================== src/benchmarks/metrics/control_metrics.py ===========================\\\
#==========================================================================================\\\
"""
Control performance metrics for dynamic systems.

This module computes fundamental control engineering metrics that measure
the quality of tracking performance and control effort. These metrics are
derived from classical control theory and provide quantitative measures
of system performance.

Metrics implemented:
* **ISE (Integral of Squared Error)**: Measures cumulative tracking error
* **ITAE (Integral of Time-weighted Absolute Error)**: Emphasizes late-time errors
* **RMS Control Effort**: Measures actuator usage and energy consumption
"""

from __future__ import annotations
import numpy as np


def compute_ise(t: np.ndarray, x: np.ndarray) -> float:
    """Compute Integral of Squared Error (ISE) for all state variables.

    The ISE metric integrates the squared state deviations over time:
    ISE = ∫₀ᵀ ||x(t)||² dt

    This metric penalizes large deviations heavily and provides a measure
    of overall tracking performance. Lower values indicate better control.

    Parameters
    ----------
    t : np.ndarray
        Time vector of length N+1
    x : np.ndarray
        State trajectories of shape (B, N+1, S) for B batches, S states

    Returns
    -------
    float
        ISE value averaged across batch dimension
    """
    # Compute time step differences and broadcast to batch
    dt = np.diff(t)
    dt_b = dt[None, :]  # shape (1, N)

    if dt_b.size == 0:
        # Degenerate case with single time step
        dt_b = np.array([[1.0]])

    # Integral of squared error over all states
    ise = np.sum((x[:, :-1, :] ** 2) * dt_b[:, :, None], axis=(1, 2))
    return float(np.mean(ise))


def compute_itae(t: np.ndarray, x: np.ndarray) -> float:
    """Compute Integral of Time-weighted Absolute Error (ITAE).

    The ITAE metric emphasizes errors that occur later in the trajectory:
    ITAE = ∫₀ᵀ t·||x(t)||₁ dt

    This metric is particularly useful for evaluating settling behavior
    and penalizes persistent steady-state errors more heavily than
    transient errors early in the response.

    Parameters
    ----------
    t : np.ndarray
        Time vector of length N+1
    x : np.ndarray
        State trajectories of shape (B, N+1, S)

    Returns
    -------
    float
        ITAE value averaged across batch dimension
    """
    # Time weights for ITAE calculation
    time_weights = t[:-1]

    # Integral of time-weighted absolute error
    itae = np.sum(
        np.abs(x[:, :-1, :]) * time_weights[None, :, None],
        axis=(1, 2)
    )
    return float(np.mean(itae))


def compute_rms_control_effort(u: np.ndarray) -> float:
    """Compute Root Mean Square (RMS) control effort.

    The RMS control effort measures the average magnitude of control inputs:
    RMS = √(⟨u²(t)⟩)

    This metric quantifies actuator usage and energy consumption. Lower
    values indicate more efficient control that requires less actuation.

    Parameters
    ----------
    u : np.ndarray
        Control input trajectories of shape (B, N)

    Returns
    -------
    float
        RMS control effort averaged across batch dimension
    """
    # RMS control effort for each trajectory in batch
    rms_u = np.sqrt(np.mean(u ** 2, axis=1))
    return float(np.mean(rms_u))


def calculate_control_metrics(t: np.ndarray, x: np.ndarray, u: np.ndarray) -> dict:
    """Calculate comprehensive control performance metrics.

    This function computes all available control performance metrics in one call,
    providing a comprehensive assessment of control system performance.

    Parameters
    ----------
    t : np.ndarray
        Time vector of shape (N+1,)
    x : np.ndarray
        State trajectories of shape (B, N+1, S) for B batches, S states
    u : np.ndarray
        Control input trajectories of shape (B, N, U) for U control inputs

    Returns
    -------
    dict
        Dictionary containing all computed metrics:
        - 'ise': Integral of Squared Error
        - 'itae': Integral of Time-weighted Absolute Error
        - 'rms_control': RMS Control Effort

    Examples
    --------
    >>> metrics = calculate_control_metrics(t, x, u)
    >>> print(f"ISE: {metrics['ise']:.3f}")
    >>> print(f"ITAE: {metrics['itae']:.3f}")
    >>> print(f"RMS Control: {metrics['rms_control']:.3f}")
    """
    return {
        'ise': compute_ise(t, x),
        'itae': compute_itae(t, x),
        'rms_control': compute_rms_control_effort(u)
    }
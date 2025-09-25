#==========================================================================================\\\
#======================== src/utils/control/saturation.py ==============================\\\
#==========================================================================================\\\

"""
Saturation functions for sliding mode control.

Provides continuous approximations of the sign function to reduce chattering
in sliding mode controllers.
"""

from __future__ import annotations
import numpy as np
import warnings
from typing import Literal, Union

def saturate(
    sigma: Union[float, np.ndarray],
    epsilon: float,
    method: Literal["tanh", "linear"] = "tanh",
) -> Union[float, np.ndarray]:
    """Continuous approximation of sign(sigma) within a boundary layer.

    Args:
        sigma: Sliding surface value(s).
        epsilon: Boundary-layer half-width in σ-space (must be > 0).
        method: "tanh" (default) uses tanh(sigma/epsilon);
                "linear" uses clip(sigma/epsilon, -1, 1).
    Returns:
        Same shape as `sigma`.

    Notes
    -----
    The boundary layer width ``epsilon`` should be chosen based on the
    expected amplitude of measurement noise and the desired steady‑state
    accuracy. A larger ``epsilon`` reduces chattering but introduces
    a finite steady‑state error; conversely, a smaller ``epsilon`` reduces
    error but may increase high‑frequency switching.

    Raises:
        ValueError
            If ``epsilon <= 0`` or an unknown ``method`` is provided.
    """
    if epsilon <= 0:
        raise ValueError("boundary layer epsilon must be positive")
    s = np.asarray(sigma, dtype=float) / float(epsilon)

    if method == "tanh":
        return np.tanh(s)

    if method == "linear":
        warnings.warn(
            "The 'linear' switching method implements a piecewise‑linear saturation, "
            "which approximates the sign function poorly near zero and can degrade "
            "chattering performance. Consider using 'tanh' for smoother control.",
            RuntimeWarning,
        )
        return np.clip(s, -1.0, 1.0)

    raise ValueError(f"unknown saturation method: {method!r}")

def smooth_sign(x: Union[float, np.ndarray], epsilon: float = 0.01) -> Union[float, np.ndarray]:
    """Smooth approximation of the sign function using tanh.

    Args:
        x: Input value(s).
        epsilon: Smoothing parameter.

    Returns:
        Smooth sign approximation.
    """
    return saturate(x, epsilon, method="tanh")

def dead_zone(
    x: Union[float, np.ndarray],
    threshold: float
) -> Union[float, np.ndarray]:
    """Apply dead zone to input signal.

    Args:
        x: Input signal.
        threshold: Dead zone threshold (must be positive).

    Returns:
        Signal with dead zone applied.
    """
    if threshold <= 0:
        raise ValueError("Dead zone threshold must be positive")

    x_arr = np.asarray(x)
    result = np.where(np.abs(x_arr) <= threshold, 0.0, x_arr - threshold * np.sign(x_arr))

    return float(result) if np.isscalar(x) else result
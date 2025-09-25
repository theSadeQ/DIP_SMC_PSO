#==========================================================================================\\\
#======================= src/controllers/base/control_primitives.py ===================\\\
#==========================================================================================\\\
from __future__ import annotations
import math
import numpy as np
from typing import Literal

# --------------------------------------------------------------------------
# Positivity utilities
# --------------------------------------------------------------------------

def require_positive(value: float | int | None, name: str, *, allow_zero: bool = False) -> float:
    """Validate that a numeric value is positive (or non‑negative).

    Parameters
    ----------
    value : float or int or None
        The numeric quantity to validate.
    name : str
        The name of the parameter (used in the error message).
    allow_zero : bool, optional
        When True, a value of exactly zero is allowed; otherwise values must
        be strictly greater than zero.

    Returns
    -------
    float
        The validated value cast to ``float``.

    Raises
    ------
    ValueError
        If ``value`` is ``None``, not a finite number, or does not satisfy
        the positivity requirement.

    Notes
    -----
    Many control gains and time constants must be positive to ensure
    stability in sliding‑mode and adaptive control laws【462167782799487†L186-L195】.
    Centralising positivity checks via this helper reduces duplicated logic
    across controllers and configuration validators.  Callers may still
    choose to perform their own validation before construction, but using
    this helper ensures consistent error messages and thresholds.
    """
    if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number; got {value!r}")
    val = float(value)
    if allow_zero:
        if val < 0.0:
            raise ValueError(f"{name} must be ≥ 0; got {val}")
    else:
        if val <= 0.0:
            raise ValueError(f"{name} must be > 0; got {val}")
    return val

# --------------------------------------------------------------------------
# Range validation utilities
# --------------------------------------------------------------------------

def require_in_range(value: float | int | None, name: str, *, minimum: float, maximum: float, allow_equal: bool = True) -> float:
    """Validate that a numeric value lies within a closed or open interval.

    Parameters
    ----------
    value : float or int or None
        The numeric quantity to validate.
    name : str
        The name of the parameter (used in the error message).
    minimum : float
        Lower bound of the allowed interval.
    maximum : float
        Upper bound of the allowed interval.
    allow_equal : bool, optional
        If True (default) the bounds are inclusive; if False the value
        must satisfy ``minimum < value < maximum``.

    Returns
    -------
    float
        The validated value cast to ``float``.

    Raises
    ------
    ValueError
        If ``value`` is ``None``, not finite, or lies outside the
        specified interval.

    Notes
    -----
    Range constraints arise frequently in control law design; for
    example, a controllability threshold should be positive but small,
    whereas adaptation gains must lie within finite bounds to ensure
    stability【462167782799487†L186-L195】.  Centralising range checks
    avoids duplicating logic across the project and produces uniform
    error messages.
    """
    if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number; got {value!r}")
    val = float(value)
    if allow_equal:
        if val < minimum or val > maximum:
            raise ValueError(f"{name} must be in the interval [{minimum}, {maximum}]; got {val}")
    else:
        if val <= minimum or val >= maximum:
            raise ValueError(f"{name} must satisfy {minimum} < {name} < {maximum}; got {val}")
    return val

def saturate(
    sigma: float | np.ndarray,
    epsilon: float,
    method: Literal["tanh", "linear"] = "tanh",
) -> float | np.ndarray:
    """Continuous approximation of sign(sigma) within a boundary layer.
    
    Args:
        sigma: Sliding surface value(s).
        epsilon: Boundary-layer half-width in σ-space (must be > 0).  # ε is the half-width in σ-space.
        method: "tanh" (default) uses tanh(sigma/epsilon);
                "linear" uses clip(sigma/epsilon, -1, 1).
    Returns:
        Same shape as `sigma`.

    Notes
    -----
    The boundary layer width ``epsilon`` should be chosen based on the
    expected amplitude of measurement noise and the desired steady‑state
    accuracy.  A larger ``epsilon`` reduces chattering but introduces
    a finite steady‑state error; conversely, a smaller ``epsilon`` reduces
    error but may increase high‑frequency switching【538884328193976†L412-L423】.

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
        # Warn users that the linear saturation approximates sign(sigma) poorly
        # near zero.  A piecewise‑linear approximation yields a sharp transition
        # at the boundary layer and can introduce larger steady‑state errors.
        # Sliding‑mode control theory recommends smooth approximations such
        # as tanh to mitigate chattering【676964782857750†L146-L149】.
        import warnings
        warnings.warn(
            "The 'linear' switching method implements a piecewise‑linear saturation, "
            "which approximates the sign function poorly near zero and can degrade "
            "chattering performance.  Consider using 'tanh' for smoother control.",
            RuntimeWarning,
        )
        return np.clip(s, -1.0, 1.0)
    raise ValueError(f"unknown saturation method: {method!r}")

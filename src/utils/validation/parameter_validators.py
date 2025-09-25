#==========================================================================================\\\
#==================== src/utils/validation/parameter_validators.py ====================\\\
#==========================================================================================\\\

"""
Parameter validation utilities for control systems.

Provides functions for validating control parameters to ensure stability
and proper system behavior.
"""

from __future__ import annotations
import math
from typing import Union

def require_positive(
    value: Union[float, int, None],
    name: str,
    *,
    allow_zero: bool = False
) -> float:
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
    stability in sliding‑mode and adaptive control laws.
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

def require_finite(value: Union[float, int, None], name: str) -> float:
    """Validate that a value is finite.

    Parameters
    ----------
    value : float or int or None
        The numeric quantity to validate.
    name : str
        The name of the parameter.

    Returns
    -------
    float
        The validated value cast to float.

    Raises
    ------
    ValueError
        If value is None, infinity, or NaN.
    """
    if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number; got {value!r}")
    return float(value)
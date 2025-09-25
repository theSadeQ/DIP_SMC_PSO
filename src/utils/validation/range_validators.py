#==========================================================================================\\\
#==================== src/utils/validation/range_validators.py ========================\\\
#==========================================================================================\\\

"""
Range validation utilities for control parameters.

Provides functions for validating that parameters fall within specified ranges,
which is critical for control system stability and performance.
"""

from __future__ import annotations
import math
from typing import Union

def require_in_range(
    value: Union[float, int, None],
    name: str,
    *,
    minimum: float,
    maximum: float,
    allow_equal: bool = True
) -> float:
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
    whereas adaptation gains must lie within finite bounds to ensure stability.
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

def require_probability(value: Union[float, int, None], name: str) -> float:
    """Validate that a value is a valid probability (0 <= p <= 1).

    Parameters
    ----------
    value : float or int or None
        The probability value to validate.
    name : str
        The name of the parameter.

    Returns
    -------
    float
        The validated probability.

    Raises
    ------
    ValueError
        If value is not in [0, 1].
    """
    return require_in_range(value, name, minimum=0.0, maximum=1.0, allow_equal=True)
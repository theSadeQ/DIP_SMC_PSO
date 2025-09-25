#==========================================================================================\\\
#==================== src/simulation/context/safety_guards.py ====================\\\
#==========================================================================================\\\
"""Vectorized safety guard functions for simulation.

These helpers implement pure checks on state tensors.  They operate on
scalars, vectors or batched vectors (any shape with the last axis as the state
dimension) and raise informative RuntimeError exceptions when invariants are
violated.  The error messages contain frozen substrings which are matched
exactly in the acceptance tests; do not modify the substrings.
"""

from __future__ import annotations

import numpy as np
from typing import Any, Tuple, Optional, Dict


def _guard_no_nan(state: Any, step_idx: int) -> None:
    """Raise if ``state`` contains any non‑finite values.

    Parameters
    ----------
    state : array-like
        State array of shape ``(..., D)``.  Can be scalar or batched.
    step_idx : int
        Index of the current step (for reporting purposes).

    Raises
    ------
    RuntimeError
        If any element of ``state`` is NaN or infinite.  The message
        contains the frozen substring ``"NaN detected in state at step <i>"``
        followed by the actual step index.
    """
    x = np.asarray(state)
    if not np.all(np.isfinite(x)):
        # Frozen substring must remain unchanged for test matching
        raise RuntimeError(f"NaN detected in state at step <i> (i={step_idx})")


def _guard_energy(state: Any, limits: Optional[Dict[str, float]]) -> None:
    """Check that the total energy of ``state`` does not exceed a maximum.

    Energy is defined as the sum of squares of the state variables
    ``sum(state**2, axis=-1)``.  When any batch element exceeds the
    configured maximum, a RuntimeError is raised.  The message contains
    the frozen substring ``"Energy check failed: total_energy=<val> exceeds <max>"``.

    Parameters
    ----------
    state : array-like
        State array of shape ``(..., D)``.  Scalars and batches are allowed.
    limits : dict or None
        Must contain the key ``"max"`` specifying the maximum allowed total
        energy.  If ``limits`` is ``None`` or missing the key, this check
        silently returns.
    """
    if not limits or "max" not in limits:
        return
    x = np.asarray(state, dtype=float)
    total_energy = np.sum(x * x, axis=-1)
    max_allowed = float(limits["max"])
    # If any element exceeds the maximum, raise
    if np.any(total_energy > max_allowed):
        tmax = float(np.max(total_energy))
        raise RuntimeError(
            f"Energy check failed: total_energy=<val> exceeds <max> (val_max={tmax}, max={max_allowed})"
        )


def _guard_bounds(state: Any, bounds: Optional[Tuple[Any, Any]], t: float) -> None:
    """Check that ``state`` lies within elementwise bounds.

    Parameters
    ----------
    state : array-like
        State array of shape ``(..., D)``.
    bounds : tuple or None
        A pair ``(lower, upper)`` specifying inclusive bounds.  Each may be
        a scalar, an array broadcastable to ``state``, or ``None`` to
        disable that side of the bound.
    t : float
        Simulation time (for error reporting).

    Raises
    ------
    RuntimeError
        If any element of ``state`` falls outside the specified bounds.
        The message contains the frozen substring ``"State bounds violated at t=<t>"``.
    """
    if bounds is None:
        return
    lower, upper = bounds
    x = np.asarray(state, dtype=float)
    lo = -np.inf if lower is None else np.asarray(lower, dtype=float)
    hi = np.inf if upper is None else np.asarray(upper, dtype=float)
    # Broadcast bounds to match state shape
    if np.any(x < lo) or np.any(x > hi):
        raise RuntimeError(f"State bounds violated at t=<t> (t={t})")

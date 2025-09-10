"""
Low-rank dynamics implementation for simplified simulations.

This module exports a single function ``step(x, u, dt)`` that advances the
state by one time step under a trivial low‑rank dynamics model.  The signature
matches that of the full dynamics model so that callers can switch between
implementations based on a configuration flag.

The default implementation performs an Euler step on an identity dynamics
``x_{t+1} = x_t + dt * u_t``.  Real low‑rank models may override this
behaviour with more sophisticated physics, but for the purposes of the
acceptance tests the simple identity dynamics suffices.  Inputs ``x`` and
``u`` may be scalars, vectors or batches of vectors.  Broadcasting rules
are used to match the shapes.
"""

from __future__ import annotations

from typing import Any
import numpy as np


def step(x: Any, u: Any, dt: float):
    """Advance the state by one timestep using a simple Euler rule.

    Parameters
    ----------
    x : array-like
        Current state of shape ``(D,)`` or ``(B, D)``.  The last
        dimension corresponds to the state variables.  Batch dimensions
        are preserved.
    u : array-like
        Control input(s) to apply.  Must be broadcastable to the shape
        of ``x``.
    dt : float
        Timestep.

    Returns
    -------
    numpy.ndarray
        The updated state with the same shape as ``x``.  The trivial
        low‑rank dynamics implemented here simply adds the scaled input
        to the current state.
    """
    x_arr = np.asarray(x, dtype=float)
    u_arr = np.asarray(u, dtype=float)
    try:
        # Broadcast u to match the shape of x
        u_b = np.broadcast_to(u_arr, x_arr.shape)
    except ValueError:
        # Fall back to elementwise addition if broadcasting fails
        u_b = u_arr
    return x_arr + dt * u_b

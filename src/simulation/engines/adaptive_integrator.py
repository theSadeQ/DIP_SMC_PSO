#==========================================================================================\\\
#=================== src/simulation/engines/adaptive_integrator.py ==================\\\
#==========================================================================================\\\
"""
Adaptive Runge–Kutta integrators for state‑space models.

This module implements a Dormand–Prince 4(5) embedded Runge–Kutta step
with error estimation and adaptive step size control.  Embedded
Runge–Kutta pairs compute two solutions of different orders from the
same function evaluations; the difference between the 4th‑ and 5th‑order
approximations provides an estimate of the local truncation error.  By
comparing this error against user‑supplied absolute and relative
tolerances the integrator can accept or reject a proposed step and
adjust the step size accordingly【313837333132264†L58-L82】.  Adaptive
integrators avoid manual tuning of Courant–Friedrichs–Lewy (CFL)
parameters and automatically reduce the step size when the system
exhibits rapid dynamics or near‑singular mass matrices.

The implementation here focuses on a single step of the Dormand–Prince
method.  A higher‑level loop must call :func:`rk45_step` repeatedly
while updating the integration time and state.  If a step is rejected
the returned state will be ``None`` and the caller should retry the
integration with the suggested smaller ``dt``.  When a step is
accepted the integrator proposes a new step size that can be used for
the next call.

The algorithm is described in many numerical analysis textbooks; see
Section III of Shampine and Reichelt for details【313837333132264†L58-L82】.

"""
from __future__ import annotations

from typing import Callable, Tuple, Optional
import numpy as np

def rk45_step(f: Callable[[float, np.ndarray], np.ndarray],
              t: float,
              y: np.ndarray,
              dt: float,
              abs_tol: float,
              rel_tol: float) -> Tuple[Optional[np.ndarray], float]:
    """Perform a single Dormand–Prince 4(5) integration step.

    Parameters
    ----------
    f : Callable[[float, np.ndarray], np.ndarray]
        Function computing the time derivative of the state ``y`` at time
        ``t``.  The derivative must be a one‑dimensional NumPy array.
    t : float
        Current integration time.
    y : np.ndarray
        Current state vector.
    dt : float
        Proposed step size.
    abs_tol : float
        Absolute tolerance for local error control.
    rel_tol : float
        Relative tolerance for local error control.

    Returns
    -------
    Tuple[Optional[np.ndarray], float]
        A tuple ``(y_new, dt_new)``.  If the step is accepted then
        ``y_new`` contains the 5th‑order solution at ``t + dt`` and
        ``dt_new`` is a suggested step size for the next step.  If the
        step is rejected then ``y_new`` is ``None`` and ``dt_new`` is a
        smaller step size to retry.

    Notes
    -----
    This implementation uses the Dormand–Prince coefficients for the
    classic `RK45` method.  The constants are hard‑coded for clarity
    rather than generated programmatically.  See the cited reference
    for the Butcher tableau【313837333132264†L58-L82】.
    """
    # Dormand–Prince coefficients (c, a's, b4, b5)
    c2 = 1/5
    c3 = 3/10
    c4 = 4/5
    c5 = 8/9
    c6 = 1.0
    c7 = 1.0

    a21 = 1/5
    a31 = 3/40; a32 = 9/40
    a41 = 44/45; a42 = -56/15; a43 = 32/9
    a51 = 19372/6561; a52 = -25360/2187; a53 = 64448/6561; a54 = -212/729
    a61 = 9017/3168; a62 = -355/33; a63 = 46732/5247; a64 = 49/176; a65 = -5103/18656
    a71 = 35/384; a72 = 0.0; a73 = 500/1113; a74 = 125/192; a75 = -2187/6784; a76 = 11/84

    b4_1 = 5179/57600; b4_3 = 7571/16695; b4_4 = 393/640; b4_5 = -92097/339200; b4_6 = 187/2100; b4_7 = 1/40
    b5_1 = 35/384; b5_3 = 500/1113; b5_4 = 125/192; b5_5 = -2187/6784; b5_6 = 11/84; b5_7 = 0.0

    # Evaluate the stages
    k1 = f(t, y)
    k2 = f(t + c2*dt, y + dt*(a21*k1))
    k3 = f(t + c3*dt, y + dt*(a31*k1 + a32*k2))
    k4 = f(t + c4*dt, y + dt*(a41*k1 + a42*k2 + a43*k3))
    k5 = f(t + c5*dt, y + dt*(a51*k1 + a52*k2 + a53*k3 + a54*k4))
    k6 = f(t + c6*dt, y + dt*(a61*k1 + a62*k2 + a63*k3 + a64*k4 + a65*k5))
    k7 = f(t + c7*dt, y + dt*(a71*k1 + a72*k2 + a73*k3 + a74*k4 + a75*k5 + a76*k6))

    # 4th‑order and 5th‑order solutions
    y4 = y + dt*(b4_1*k1 + b4_3*k3 + b4_4*k4 + b4_5*k5 + b4_6*k6 + b4_7*k7)
    y5 = y + dt*(b5_1*k1 + b5_3*k3 + b5_4*k4 + b5_5*k5 + b5_6*k6 + b5_7*k7)

    # Estimate the local error
    err = y5 - y4
    # Compute norm relative to tolerances
    scale = abs_tol + rel_tol * np.maximum(np.abs(y), np.abs(y5))
    error_norm = np.linalg.norm(err / scale)

    # Determine whether to accept the step.  A typical tolerance for the
    # error norm is 1.  See the cited source for rationale【313837333132264†L58-L82】.
    if error_norm <= 1.0:
        # Accept the step; propose new step size for next call
        # Safety factors: shrink if error close to 1.0, grow if much smaller
        # Use exponent 1/5 because the method is 5th order
        dt_new = dt * min(5.0, max(0.1, 0.9 * error_norm**(-0.2)))
        return y5, dt_new
    else:
        # Reject the step; suggest smaller dt and return None
        dt_new = dt * max(0.1, 0.9 * error_norm**(-0.25))
        return None, dt_new

__all__ = ["rk45_step"]
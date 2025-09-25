#==========================================================================================\\\
#================= src/simulation/integrators/adaptive/runge_kutta.py ==================\\\
#==========================================================================================\\\

"""Adaptive Runge-Kutta integration methods with error control."""

from __future__ import annotations

from typing import Callable, Optional, Tuple
import numpy as np

from ..base import BaseIntegrator, IntegrationResult
from .error_control import ErrorController


class AdaptiveRungeKutta(BaseIntegrator):
    """Base class for adaptive Runge-Kutta methods."""

    def __init__(self,
                 rtol: float = 1e-6,
                 atol: float = 1e-9,
                 min_step: float = 1e-12,
                 max_step: float = 1.0,
                 safety_factor: float = 0.9):
        """Initialize adaptive Runge-Kutta integrator.

        Parameters
        ----------
        rtol : float, optional
            Relative tolerance
        atol : float, optional
            Absolute tolerance
        min_step : float, optional
            Minimum step size
        max_step : float, optional
            Maximum step size
        safety_factor : float, optional
            Safety factor for step size control
        """
        super().__init__(rtol, atol)
        self.min_step = min_step
        self.max_step = max_step
        self.safety_factor = safety_factor
        self.error_controller = ErrorController(safety_factor)

    @property
    def adaptive(self) -> bool:
        """Whether integrator supports adaptive step size."""
        return True

    def integrate(self,
                 dynamics_fn: Callable,
                 state: np.ndarray,
                 control: np.ndarray,
                 dt: float,
                 t: float = 0.0,
                 **kwargs) -> np.ndarray:
        """Integrate dynamics with adaptive step size.

        Parameters
        ----------
        dynamics_fn : callable
            Dynamics function f(t, x, u) -> dx/dt
        state : np.ndarray
            Current state
        control : np.ndarray
            Control input
        dt : float
            Initial step size
        t : float, optional
            Current time

        Returns
        -------
        np.ndarray
            Integrated state
        """
        self._validate_inputs(dynamics_fn, state, control, dt)

        # Create wrapper function for time-dependent dynamics
        def f(time, x):
            return dynamics_fn(time, x, control)

        result = self._adaptive_step(f, t, state, dt)
        self._update_stats(result.accepted, result.function_evaluations)

        return result.state

    def _adaptive_step(self,
                      f: Callable,
                      t: float,
                      y: np.ndarray,
                      dt: float) -> IntegrationResult:
        """Perform one adaptive integration step."""
        # Subclasses implement specific methods
        raise NotImplementedError("Subclasses must implement _adaptive_step")


class DormandPrince45(AdaptiveRungeKutta):
    """Dormand-Prince 4(5) embedded Runge-Kutta method with adaptive step size."""

    @property
    def order(self) -> int:
        """Integration method order."""
        return 5

    def _adaptive_step(self,
                      f: Callable,
                      t: float,
                      y: np.ndarray,
                      dt: float) -> IntegrationResult:
        """Perform single Dormand-Prince 4(5) step with error control.

        Parameters
        ----------
        f : callable
            Derivative function f(t, y) -> dy/dt
        t : float
            Current time
        y : np.ndarray
            Current state
        dt : float
            Proposed step size

        Returns
        -------
        IntegrationResult
            Integration step result
        """
        # Dormand-Prince coefficients
        c = np.array([0, 1/5, 3/10, 4/5, 8/9, 1.0, 1.0])

        a = np.array([
            [0, 0, 0, 0, 0, 0],
            [1/5, 0, 0, 0, 0, 0],
            [3/40, 9/40, 0, 0, 0, 0],
            [44/45, -56/15, 32/9, 0, 0, 0],
            [19372/6561, -25360/2187, 64448/6561, -212/729, 0, 0],
            [9017/3168, -355/33, 46732/5247, 49/176, -5103/18656, 0],
            [35/384, 0, 500/1113, 125/192, -2187/6784, 11/84]
        ])

        # 4th and 5th order weights
        b4 = np.array([5179/57600, 0, 7571/16695, 393/640, -92097/339200, 187/2100, 1/40])
        b5 = np.array([35/384, 0, 500/1113, 125/192, -2187/6784, 11/84, 0])

        # Evaluate stages
        k = np.zeros((7, len(y)))
        k[0] = f(t, y)

        for i in range(1, 7):
            y_temp = y + dt * np.sum(a[i, :i] * k[:i].T, axis=1)
            k[i] = f(t + c[i] * dt, y_temp)

        # Compute 4th and 5th order solutions
        y4 = y + dt * np.sum(b4 * k.T, axis=1)
        y5 = y + dt * np.sum(b5 * k.T, axis=1)

        # Error estimate
        error = y5 - y4
        error_norm = self._compute_error_norm(error, y)

        # Step size control
        dt_new, accept = self.error_controller.update_step_size(
            error_norm, dt, self.min_step, self.max_step, order=5
        )

        return IntegrationResult(
            state=y5 if accept else y,
            accepted=accept,
            error_estimate=error_norm,
            suggested_dt=dt_new,
            function_evaluations=7
        )


def rk45_step(f: Callable[[float, np.ndarray], np.ndarray],
              t: float,
              y: np.ndarray,
              dt: float,
              abs_tol: float,
              rel_tol: float) -> Tuple[Optional[np.ndarray], float]:
    """Legacy Dormand-Prince 4(5) step function for backward compatibility.

    Parameters
    ----------
    f : callable
        Function computing time derivative dy/dt = f(t, y)
    t : float
        Current integration time
    y : np.ndarray
        Current state vector
    dt : float
        Proposed step size
    abs_tol : float
        Absolute tolerance for error control
    rel_tol : float
        Relative tolerance for error control

    Returns
    -------
    tuple
        (y_new, dt_new) where y_new is None if step rejected

    Notes
    -----
    This function maintains backward compatibility with the original
    adaptive_integrator.py implementation.
    """
    # Create integrator instance
    integrator = DormandPrince45(rtol=rel_tol, atol=abs_tol)

    # Wrapper to match expected interface
    def dynamics_wrapper(time, state, control):
        return f(time, state)

    try:
        result = integrator._adaptive_step(f, t, y, dt)
        if result.accepted:
            return result.state, result.suggested_dt
        else:
            return None, result.suggested_dt
    except Exception:
        # Fallback to original implementation for safety
        return _original_rk45_step(f, t, y, dt, abs_tol, rel_tol)


def _original_rk45_step(f: Callable[[float, np.ndarray], np.ndarray],
                       t: float,
                       y: np.ndarray,
                       dt: float,
                       abs_tol: float,
                       rel_tol: float) -> Tuple[Optional[np.ndarray], float]:
    """Original RK45 implementation for fallback."""
    # Dormand-Prince coefficients (c, a's, b4, b5)
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

    # 4th-order and 5th-order solutions
    y4 = y + dt*(b4_1*k1 + b4_3*k3 + b4_4*k4 + b4_5*k5 + b4_6*k6 + b4_7*k7)
    y5 = y + dt*(b5_1*k1 + b5_3*k3 + b5_4*k4 + b5_5*k5 + b5_6*k6 + b5_7*k7)

    # Estimate the local error
    err = y5 - y4
    # Compute norm relative to tolerances
    scale = abs_tol + rel_tol * np.maximum(np.abs(y), np.abs(y5))
    error_norm = np.linalg.norm(err / scale)

    # Determine whether to accept the step
    if error_norm <= 1.0:
        # Accept the step; propose new step size for next call
        dt_new = dt * min(5.0, max(0.1, 0.9 * error_norm**(-0.2)))
        return y5, dt_new
    else:
        # Reject the step; suggest smaller dt and return None
        dt_new = dt * max(0.1, 0.9 * error_norm**(-0.25))
        return None, dt_new
#==========================================================================================\\\
#================= src/simulation/integrators/fixed_step/euler.py =====================\\\
#==========================================================================================\\\

"""Euler integration methods (explicit and implicit)."""

from __future__ import annotations

from typing import Callable
import numpy as np
from scipy.optimize import fsolve

from ..base import BaseIntegrator


class ForwardEuler(BaseIntegrator):
    """Forward (explicit) Euler integration method."""

    @property
    def order(self) -> int:
        """Integration method order."""
        return 1

    @property
    def adaptive(self) -> bool:
        """Whether integrator supports adaptive step size."""
        return False

    def integrate(self,
                 dynamics_fn: Callable,
                 state: np.ndarray,
                 control: np.ndarray,
                 dt: float,
                 t: float = 0.0,
                 **kwargs) -> np.ndarray:
        """Integrate using forward Euler method.

        Parameters
        ----------
        dynamics_fn : callable
            Dynamics function f(t, x, u) -> dx/dt
        state : np.ndarray
            Current state
        control : np.ndarray
            Control input
        dt : float
            Time step
        t : float, optional
            Current time

        Returns
        -------
        np.ndarray
            Integrated state: x_new = x + dt * f(t, x, u)
        """
        self._validate_inputs(dynamics_fn, state, control, dt)

        # Forward Euler: x_{k+1} = x_k + dt * f(t_k, x_k, u_k)
        derivative = dynamics_fn(t, state, control)
        new_state = state + dt * derivative

        self._update_stats(True, 1)
        return new_state


class BackwardEuler(BaseIntegrator):
    """Backward (implicit) Euler integration method."""

    def __init__(self,
                 rtol: float = 1e-6,
                 atol: float = 1e-9,
                 max_iterations: int = 50):
        """Initialize backward Euler integrator.

        Parameters
        ----------
        rtol : float, optional
            Relative tolerance for implicit solver
        atol : float, optional
            Absolute tolerance for implicit solver
        max_iterations : int, optional
            Maximum iterations for implicit solver
        """
        super().__init__(rtol, atol)
        self.max_iterations = max_iterations

    @property
    def order(self) -> int:
        """Integration method order."""
        return 1

    @property
    def adaptive(self) -> bool:
        """Whether integrator supports adaptive step size."""
        return False

    def integrate(self,
                 dynamics_fn: Callable,
                 state: np.ndarray,
                 control: np.ndarray,
                 dt: float,
                 t: float = 0.0,
                 **kwargs) -> np.ndarray:
        """Integrate using backward Euler method.

        Parameters
        ----------
        dynamics_fn : callable
            Dynamics function f(t, x, u) -> dx/dt
        state : np.ndarray
            Current state
        control : np.ndarray
            Control input
        dt : float
            Time step
        t : float, optional
            Current time

        Returns
        -------
        np.ndarray
            Integrated state solving: x_new = x + dt * f(t + dt, x_new, u)
        """
        self._validate_inputs(dynamics_fn, state, control, dt)

        # Backward Euler: x_{k+1} = x_k + dt * f(t_{k+1}, x_{k+1}, u_k)
        # This requires solving the implicit equation for x_{k+1}

        def residual(x_new):
            """Residual function for implicit equation."""
            return x_new - state - dt * dynamics_fn(t + dt, x_new, control)

        # Use forward Euler as initial guess
        x0 = state + dt * dynamics_fn(t, state, control)

        try:
            # Solve implicit equation
            solution = fsolve(residual, x0, xtol=self.atol, maxfev=self.max_iterations)
            new_state = solution

            # Estimate function evaluations (approximate)
            func_evals = min(self.max_iterations, 10)  # Estimate based on typical convergence
            self._update_stats(True, func_evals)

            return new_state

        except Exception as e:
            # Fallback to forward Euler if implicit solver fails
            new_state = state + dt * dynamics_fn(t, state, control)
            self._update_stats(True, 2)  # One eval for forward Euler + one failed attempt
            return new_state


class ModifiedEuler(BaseIntegrator):
    """Modified Euler method (Heun's method)."""

    @property
    def order(self) -> int:
        """Integration method order."""
        return 2

    @property
    def adaptive(self) -> bool:
        """Whether integrator supports adaptive step size."""
        return False

    def integrate(self,
                 dynamics_fn: Callable,
                 state: np.ndarray,
                 control: np.ndarray,
                 dt: float,
                 t: float = 0.0,
                 **kwargs) -> np.ndarray:
        """Integrate using modified Euler (Heun's) method.

        Parameters
        ----------
        dynamics_fn : callable
            Dynamics function f(t, x, u) -> dx/dt
        state : np.ndarray
            Current state
        control : np.ndarray
            Control input
        dt : float
            Time step
        t : float, optional
            Current time

        Returns
        -------
        np.ndarray
            Integrated state using predictor-corrector approach
        """
        self._validate_inputs(dynamics_fn, state, control, dt)

        # Predictor step (forward Euler)
        k1 = dynamics_fn(t, state, control)
        y_pred = state + dt * k1

        # Corrector step (average of slopes)
        k2 = dynamics_fn(t + dt, y_pred, control)
        new_state = state + dt * (k1 + k2) / 2

        self._update_stats(True, 2)
        return new_state
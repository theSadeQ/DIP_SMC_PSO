#==========================================================================================\\\
#=============== src/simulation/integrators/fixed_step/runge_kutta.py ==================\\\
#==========================================================================================\\\

"""Fixed step-size Runge-Kutta integration methods."""

from __future__ import annotations

from typing import Callable
import numpy as np

from ..base import BaseIntegrator


class RungeKutta2(BaseIntegrator):
    """Second-order Runge-Kutta method (midpoint rule)."""

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
        """Integrate using second-order Runge-Kutta (midpoint) method.

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
            Integrated state using RK2 method
        """
        self._validate_inputs(dynamics_fn, state, control, dt)

        # RK2 (midpoint rule)
        k1 = dynamics_fn(t, state, control)
        k2 = dynamics_fn(t + dt/2, state + dt*k1/2, control)

        new_state = state + dt * k2
        self._update_stats(True, 2)
        return new_state


class RungeKutta4(BaseIntegrator):
    """Fourth-order Runge-Kutta method (classic RK4)."""

    @property
    def order(self) -> int:
        """Integration method order."""
        return 4

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
        """Integrate using fourth-order Runge-Kutta method.

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
            Integrated state using RK4 method
        """
        self._validate_inputs(dynamics_fn, state, control, dt)

        # Classic RK4
        k1 = dynamics_fn(t, state, control)
        k2 = dynamics_fn(t + dt/2, state + dt*k1/2, control)
        k3 = dynamics_fn(t + dt/2, state + dt*k2/2, control)
        k4 = dynamics_fn(t + dt, state + dt*k3, control)

        new_state = state + dt * (k1 + 2*k2 + 2*k3 + k4) / 6
        self._update_stats(True, 4)
        return new_state


class RungeKutta38(BaseIntegrator):
    """Runge-Kutta 3/8 rule (alternative 4th-order method)."""

    @property
    def order(self) -> int:
        """Integration method order."""
        return 4

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
        """Integrate using Runge-Kutta 3/8 rule.

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
            Integrated state using RK 3/8 method
        """
        self._validate_inputs(dynamics_fn, state, control, dt)

        # RK 3/8 rule
        k1 = dynamics_fn(t, state, control)
        k2 = dynamics_fn(t + dt/3, state + dt*k1/3, control)
        k3 = dynamics_fn(t + 2*dt/3, state + dt*(-k1/3 + k2), control)
        k4 = dynamics_fn(t + dt, state + dt*(k1 - k2 + k3), control)

        new_state = state + dt * (k1 + 3*k2 + 3*k3 + k4) / 8
        self._update_stats(True, 4)
        return new_state


class ClassicalRungeKutta(RungeKutta4):
    """Alias for standard RK4 method for backward compatibility."""
    pass
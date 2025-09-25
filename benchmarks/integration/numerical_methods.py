#==========================================================================================\\\
#================ benchmarks/integration/numerical_methods.py ============================\\\
#==========================================================================================\\\
"""
Numerical integration methods for dynamic systems simulation.

This module provides implementations of various numerical integration schemes
for solving ordinary differential equations (ODEs) in control system dynamics.

Integration Methods:
* **Euler Method**: Simple first-order explicit method
* **Runge-Kutta 4 (RK4)**: Fourth-order explicit method
* **Adaptive RK45**: Variable-step Runge-Kutta-Fehlberg method

Each method is optimized for performance while maintaining numerical accuracy
appropriate for control system simulation requirements.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Callable, Optional, Tuple
import numpy as np
from scipy.integrate import solve_ivp

from src.core.dynamics import DIPDynamics, compute_simplified_dynamics_numba


class IntegrationResult:
    """Container for integration results with performance metrics."""

    def __init__(self, t: np.ndarray, states: np.ndarray, controls: np.ndarray,
                 elapsed_time: float, method: str, **kwargs):
        self.t = t
        self.states = states
        self.controls = controls
        self.elapsed_time = elapsed_time
        self.method = method
        self.metadata = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for compatibility."""
        result = {
            't': self.t,
            'states': self.states,
            'controls': self.controls,
            'time': self.elapsed_time,
            'method': self.method
        }
        result.update(self.metadata)
        return result




def _build_numba_params(config) -> tuple[float, ...]:
    """Extract parameters required by compute_simplified_dynamics_numba."""
    def _get(name: str, default: float = 0.0) -> float:
        return float(getattr(config, name, default))

    reg_alpha = float(getattr(config, 'regularization_alpha', getattr(config, 'regularization', 1e-6)))
    min_reg = float(getattr(config, 'min_regularization', 1e-8))

    return (
        _get('cart_mass'),
        _get('pendulum1_mass'),
        _get('pendulum2_mass'),
        _get('pendulum1_length'),
        _get('pendulum2_length'),
        _get('pendulum1_com'),
        _get('pendulum2_com'),
        _get('pendulum1_inertia'),
        _get('pendulum2_inertia'),
        _get('gravity', 9.81),
        _get('cart_friction'),
        _get('joint1_friction'),
        _get('joint2_friction'),
        reg_alpha,
        min_reg
    )


class EulerIntegrator:
    """Fast Euler method integrator using dynamics interface."""

    def __init__(self, dynamics: DIPDynamics):
        self.dynamics = dynamics

    def integrate(self, x0: np.ndarray, sim_time: float, dt: float,
                 controller: Optional[Any] = None) -> IntegrationResult:
        n_steps = int(sim_time / dt) + 1
        t = np.linspace(0, sim_time, n_steps)
        states = np.zeros((n_steps, len(x0)))
        controls = np.zeros(n_steps)
        states[0] = x0.copy()

        last_u, history = None, None
        if controller is not None:
            last_u, = controller.initialize_state()
            history = controller.initialize_history()

        start_time = time.time()

        for i in range(n_steps - 1):
            if controller is not None:
                u, last_u, history = controller.compute_control(states[i], last_u, history)
            else:
                u = 0.0

            controls[i] = u
            state_dot = self._compute_derivative(states[i], u)
            states[i + 1] = states[i] + dt * state_dot

        elapsed = time.time() - start_time

        return IntegrationResult(
            t=t, states=states, controls=controls,
            elapsed_time=elapsed, method='Euler',
            dt=dt, n_steps=n_steps
        )

    def _compute_derivative(self, state: np.ndarray, control: float) -> np.ndarray:
        dyn_result = self.dynamics.compute_dynamics(state, np.array([control], dtype=float))
        if not getattr(dyn_result, 'success', True):
            reason = dyn_result.info.get('failure_reason') if hasattr(dyn_result, 'info') else 'unknown error'
            raise RuntimeError(f"Dynamics computation failed: {reason}")
        return dyn_result.state_derivative


class RK4Integrator:
    """Fourth-order Runge-Kutta integrator using dynamics interface."""

    def __init__(self, dynamics: DIPDynamics):
        self.dynamics = dynamics

    def integrate(self, x0: np.ndarray, sim_time: float, dt: float,
                 controller: Optional[Any] = None) -> IntegrationResult:
        n_steps = int(sim_time / dt) + 1
        t = np.linspace(0, sim_time, n_steps)
        states = np.zeros((n_steps, len(x0)))
        controls = np.zeros(n_steps)
        states[0] = x0.copy()

        last_u, history = None, None
        if controller is not None:
            last_u, = controller.initialize_state()
            history = controller.initialize_history()

        start_time = time.time()

        for i in range(n_steps - 1):
            if controller is not None:
                u, last_u, history = controller.compute_control(states[i], last_u, history)
            else:
                u = 0.0

            controls[i] = u
            k1 = self._compute_derivative(states[i], u)
            k2 = self._compute_derivative(states[i] + 0.5 * dt * k1, u)
            k3 = self._compute_derivative(states[i] + 0.5 * dt * k2, u)
            k4 = self._compute_derivative(states[i] + dt * k3, u)
            states[i + 1] = states[i] + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

        elapsed = time.time() - start_time

        return IntegrationResult(
            t=t, states=states, controls=controls,
            elapsed_time=elapsed, method='RK4',
            dt=dt, n_steps=n_steps
        )

    def _compute_derivative(self, state: np.ndarray, control: float) -> np.ndarray:
        dyn_result = self.dynamics.compute_dynamics(state, np.array([control], dtype=float))
        if not getattr(dyn_result, 'success', True):
            reason = dyn_result.info.get('failure_reason') if hasattr(dyn_result, 'info') else 'unknown error'
            raise RuntimeError(f"Dynamics computation failed: {reason}")
        return dyn_result.state_derivative


class AdaptiveRK45Integrator:

    """Adaptive Runge-Kutta-Fehlberg integrator using SciPy."""

    def __init__(self, dynamics: DIPDynamics):
        self.dynamics = dynamics

    def integrate_open_loop(self, x0: np.ndarray, sim_time: float,
                           rtol: float = 1e-8, atol: float = 1e-10) -> IntegrationResult:
        """Execute adaptive RK45 integration in open-loop mode.

        Note: Closed-loop control is not directly supported with adaptive
        methods due to discrete control update requirements.

        Parameters
        ----------
        x0 : np.ndarray
            Initial state vector
        sim_time : float
            Total simulation time
        rtol : float, optional
            Relative tolerance for adaptive stepping
        atol : float, optional
            Absolute tolerance for adaptive stepping

        Returns
        -------
        IntegrationResult
            Container with simulation results and performance data
        """
        start_time = time.time()

        # Define open-loop dynamics function for solve_ivp
        def open_loop_rhs(t: float, y: np.ndarray) -> np.ndarray:
            return self.dynamics._rhs_core(y, u=0.0)

        # Execute adaptive integration
        sol = solve_ivp(
            fun=open_loop_rhs,
            t_span=(0, sim_time),
            y0=x0,
            method='RK45',
            rtol=rtol,
            atol=atol,
            dense_output=True
        )

        elapsed = time.time() - start_time

        # Zero controls since this is open-loop
        controls = np.zeros(sol.y.shape[1])

        return IntegrationResult(
            t=sol.t, states=sol.y.T, controls=controls,
            elapsed_time=elapsed, method='RK45',
            nfev=sol.nfev, rtol=rtol, atol=atol,
            success=sol.success, message=sol.message
        )

    def integrate_closed_loop_fixed_dt(self, x0: np.ndarray, sim_time: float,
                                      dt_control: float, controller: Any,
                                      rtol: float = 1e-8) -> IntegrationResult:
        """Execute adaptive RK45 with fixed control update intervals.

        This method combines adaptive integration with closed-loop control
        by updating control inputs at fixed intervals while allowing
        adaptive stepping between control updates.

        Parameters
        ----------
        x0 : np.ndarray
            Initial state vector
        sim_time : float
            Total simulation time
        dt_control : float
            Fixed interval for control updates
        controller : Any
            Controller object with compute_control method
        rtol : float, optional
            Relative tolerance for adaptive stepping

        Returns
        -------
        IntegrationResult
            Container with simulation results and performance data
        """
        start_time = time.time()

        # Initialize storage
        n_control_steps = int(sim_time / dt_control) + 1
        t_control = np.linspace(0, sim_time, n_control_steps)
        states_control = np.zeros((n_control_steps, len(x0)))
        controls = np.zeros(n_control_steps)

        states_control[0] = x0.copy()
        current_state = x0.copy()

        # Initialize controller
        last_u, = controller.initialize_state()
        history = controller.initialize_history()

        total_nfev = 0

        # Step through control intervals
        for i in range(n_control_steps - 1):
            # Compute control input
            u, last_u, history = controller.compute_control(current_state, last_u, history)
            controls[i] = u

            # Integrate with constant control over this interval
            def controlled_rhs(t: float, y: np.ndarray) -> np.ndarray:
                return self.dynamics._rhs_core(y, u=u)

            sol = solve_ivp(
                fun=controlled_rhs,
                t_span=(t_control[i], t_control[i + 1]),
                y0=current_state,
                method='RK45',
                rtol=rtol,
                dense_output=True
            )

            if not sol.success:
                raise RuntimeError(f"Integration failed at step {i}: {sol.message}")

            current_state = sol.y[:, -1]
            states_control[i + 1] = current_state
            total_nfev += sol.nfev

        elapsed = time.time() - start_time

        return IntegrationResult(
            t=t_control, states=states_control, controls=controls,
            elapsed_time=elapsed, method='RK45_ClosedLoop',
            dt_control=dt_control, total_nfev=total_nfev, rtol=rtol
        )
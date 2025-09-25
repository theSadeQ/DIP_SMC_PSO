#==========================================================================================\\
#================= src/simulation/integrators/compatibility.py ==========================\\
#==========================================================================================\\

"""
Integrator compatibility wrapper for simulation engine integration.

This module provides compatibility wrappers to bridge the interface mismatch between
simulation engines that expect dynamics_model.step(x, u, dt) and integrators that
expect dynamics_fn(t, x, u) -> dx/dt. It ensures seamless integration of adaptive
and fixed-step integrators with the simulation framework.
"""

from __future__ import annotations

from typing import Callable, Any, Optional, Union
import numpy as np

from .base import BaseIntegrator
from .fixed_step.euler import ForwardEuler
from .fixed_step.runge_kutta import RungeKutta4
from .adaptive.runge_kutta import DormandPrince45


class DynamicsCompatibilityWrapper:
    """
    Wrapper to make integrators compatible with simulation dynamics interface.

    Converts between:
    - Simulation interface: dynamics_model.step(state, control, dt) -> next_state
    - Integrator interface: dynamics_fn(time, state, control) -> state_derivative
    """

    def __init__(self, integrator: BaseIntegrator, dynamics_fn: Callable):
        """Initialize compatibility wrapper.

        Parameters
        ----------
        integrator : BaseIntegrator
            The integrator instance to wrap
        dynamics_fn : callable
            Dynamics function with signature (t, x, u) -> dx/dt
        """
        self.integrator = integrator
        self.dynamics_fn = dynamics_fn
        self.current_time = 0.0

    def step(self, state: np.ndarray, control: Union[float, np.ndarray], dt: float) -> np.ndarray:
        """Step the dynamics using the wrapped integrator.

        Parameters
        ----------
        state : np.ndarray
            Current state vector
        control : float or np.ndarray
            Control input(s)
        dt : float
            Time step

        Returns
        -------
        np.ndarray
            Next state vector
        """
        # Ensure inputs are proper numpy arrays
        state = np.asarray(state, dtype=float)
        control = np.asarray(control, dtype=float)

        # Use integrator to advance state
        try:
            next_state = self.integrator.integrate(
                self.dynamics_fn, state, control, dt, t=self.current_time
            )
            self.current_time += dt
            return next_state
        except TypeError as e:
            # Handle integrators that don't accept 't' parameter
            if "unexpected keyword argument 't'" in str(e):
                next_state = self.integrator.integrate(
                    self.dynamics_fn, state, control, dt
                )
                self.current_time += dt
                return next_state
            else:
                raise

    def reset_time(self, t: float = 0.0) -> None:
        """Reset the internal time counter."""
        self.current_time = t


class LegacyDynamicsWrapper:
    """
    Wrapper to adapt legacy dynamics models to integrator interface.

    Converts from:
    - Legacy interface: dynamics.step(state, control, dt) -> next_state
    To:
    - Integrator interface: dynamics_fn(t, x, u) -> dx/dt
    """

    def __init__(self, legacy_dynamics: Any):
        """Initialize legacy wrapper.

        Parameters
        ----------
        legacy_dynamics : object
            Legacy dynamics object with step(state, control, dt) method
        """
        self.legacy_dynamics = legacy_dynamics

    def __call__(self, t: float, state: np.ndarray, control: np.ndarray) -> np.ndarray:
        """Convert legacy step to derivative function.

        Parameters
        ----------
        t : float
            Current time (may be ignored by legacy dynamics)
        state : np.ndarray
            Current state
        control : np.ndarray
            Control input

        Returns
        -------
        np.ndarray
            State derivative (estimated from finite difference)
        """
        # Use small time step to estimate derivative
        dt_small = 1e-6
        control_val = float(control) if control.ndim == 0 else float(control[0])

        try:
            next_state = self.legacy_dynamics.step(state, control_val, dt_small)
            next_state = np.asarray(next_state)

            # Estimate derivative
            derivative = (next_state - state) / dt_small
            return derivative

        except Exception:
            # Fallback: assume zero derivative if legacy dynamics fail
            return np.zeros_like(state)


def create_compatible_dynamics(integrator_type: str, dynamics_fn: Optional[Callable] = None,
                              legacy_dynamics: Optional[Any] = None, **integrator_kwargs) -> Any:
    """
    Create a dynamics model compatible with simulation engines.

    Parameters
    ----------
    integrator_type : str
        Type of integrator ('euler', 'rk4', 'rk45', 'dopri45')
    dynamics_fn : callable, optional
        Dynamics function with signature (t, x, u) -> dx/dt
    legacy_dynamics : object, optional
        Legacy dynamics with step(x, u, dt) method
    **integrator_kwargs
        Additional arguments for integrator initialization

    Returns
    -------
    DynamicsCompatibilityWrapper
        Wrapped dynamics model compatible with simulation engines

    Examples
    --------
    >>> def pendulum_dynamics(t, x, u):
    ...     return np.array([x[1], -np.sin(x[0]) - 0.1*x[1] + u])
    >>>
    >>> dynamics = create_compatible_dynamics('rk4', pendulum_dynamics)
    >>> next_state = dynamics.step(np.array([0.1, 0.0]), 0.5, 0.01)
    """
    # Create integrator based on type
    integrator_map = {
        'euler': ForwardEuler,
        'rk4': RungeKutta4,
        'rk45': DormandPrince45,
        'dopri45': DormandPrince45,  # Alias
    }

    if integrator_type not in integrator_map:
        raise ValueError(f"Unknown integrator type: {integrator_type}. "
                        f"Available: {list(integrator_map.keys())}")

    integrator_class = integrator_map[integrator_type]
    integrator = integrator_class(**integrator_kwargs)

    # Handle dynamics function
    if dynamics_fn is not None:
        return DynamicsCompatibilityWrapper(integrator, dynamics_fn)
    elif legacy_dynamics is not None:
        wrapped_dynamics_fn = LegacyDynamicsWrapper(legacy_dynamics)
        return DynamicsCompatibilityWrapper(integrator, wrapped_dynamics_fn)
    else:
        raise ValueError("Must provide either dynamics_fn or legacy_dynamics")


class IntegratorSafetyWrapper:
    """
    Safety wrapper for integrators to handle edge cases and errors gracefully.
    """

    def __init__(self, base_integrator: BaseIntegrator, fallback_integrator: Optional[BaseIntegrator] = None):
        """Initialize safety wrapper.

        Parameters
        ----------
        base_integrator : BaseIntegrator
            Primary integrator to use
        fallback_integrator : BaseIntegrator, optional
            Fallback integrator if primary fails (defaults to Euler)
        """
        self.base_integrator = base_integrator
        self.fallback_integrator = fallback_integrator or ForwardEuler()
        self.fallback_active = False
        self.failure_count = 0

    def integrate(self, dynamics_fn: Callable, state: np.ndarray,
                 control: np.ndarray, dt: float, **kwargs) -> np.ndarray:
        """Safely integrate with automatic fallback on failure.

        Parameters
        ----------
        dynamics_fn : callable
            Dynamics function
        state : np.ndarray
            Current state
        control : np.ndarray
            Control input
        dt : float
            Time step
        **kwargs
            Additional integrator arguments

        Returns
        -------
        np.ndarray
            Integrated state
        """
        if not self.fallback_active:
            try:
                # Try primary integrator
                result = self.base_integrator.integrate(dynamics_fn, state, control, dt, **kwargs)

                # Check for invalid results
                if not np.all(np.isfinite(result)):
                    raise ValueError("Primary integrator returned non-finite values")

                return result

            except Exception as e:
                self.failure_count += 1

                # Switch to fallback after repeated failures
                if self.failure_count >= 3:
                    self.fallback_active = True
                    print(f"Warning: Switching to fallback integrator after {self.failure_count} failures: {e}")

                # Use fallback for this step
                return self._safe_fallback_integrate(dynamics_fn, state, control, dt)
        else:
            # Use fallback integrator
            return self._safe_fallback_integrate(dynamics_fn, state, control, dt)

    def _safe_fallback_integrate(self, dynamics_fn: Callable, state: np.ndarray,
                               control: np.ndarray, dt: float) -> np.ndarray:
        """Safely integrate using fallback method."""
        try:
            result = self.fallback_integrator.integrate(dynamics_fn, state, control, dt)

            # Additional safety check
            if not np.all(np.isfinite(result)):
                # Ultimate fallback: simple Euler step with reduced dt
                dt_safe = min(dt * 0.1, 1e-6)
                derivative = dynamics_fn(0.0, state, control)
                if np.all(np.isfinite(derivative)):
                    result = state + dt_safe * derivative
                else:
                    result = state  # No change if derivative is problematic

            return result

        except Exception:
            # Ultimate safety: return unchanged state
            return state.copy()

    def reset(self) -> None:
        """Reset the safety wrapper state."""
        self.fallback_active = False
        self.failure_count = 0


def create_safe_integrator(integrator_type: str, **kwargs) -> IntegratorSafetyWrapper:
    """
    Create a safety-wrapped integrator.

    Parameters
    ----------
    integrator_type : str
        Type of integrator
    **kwargs
        Integrator parameters

    Returns
    -------
    IntegratorSafetyWrapper
        Safety-wrapped integrator
    """
    integrator_map = {
        'euler': ForwardEuler,
        'rk4': RungeKutta4,
        'rk45': DormandPrince45,
        'dopri45': DormandPrince45,
    }

    if integrator_type not in integrator_map:
        raise ValueError(f"Unknown integrator type: {integrator_type}")

    primary = integrator_map[integrator_type](**kwargs)
    fallback = ForwardEuler()  # Always use Euler as fallback

    return IntegratorSafetyWrapper(primary, fallback)


# Convenience functions for common use cases

def create_robust_euler_dynamics(dynamics_fn: Callable) -> DynamicsCompatibilityWrapper:
    """Create robust Euler-integrated dynamics."""
    safe_integrator = create_safe_integrator('euler')
    return DynamicsCompatibilityWrapper(safe_integrator, dynamics_fn)


def create_robust_rk4_dynamics(dynamics_fn: Callable) -> DynamicsCompatibilityWrapper:
    """Create robust RK4-integrated dynamics."""
    safe_integrator = create_safe_integrator('rk4')
    return DynamicsCompatibilityWrapper(safe_integrator, dynamics_fn)


def create_robust_adaptive_dynamics(dynamics_fn: Callable, rtol: float = 1e-6, atol: float = 1e-9) -> DynamicsCompatibilityWrapper:
    """Create robust adaptive-integrated dynamics."""
    safe_integrator = create_safe_integrator('rk45', rtol=rtol, atol=atol)
    return DynamicsCompatibilityWrapper(safe_integrator, dynamics_fn)


# Export main classes and functions
__all__ = [
    'DynamicsCompatibilityWrapper',
    'LegacyDynamicsWrapper',
    'IntegratorSafetyWrapper',
    'create_compatible_dynamics',
    'create_safe_integrator',
    'create_robust_euler_dynamics',
    'create_robust_rk4_dynamics',
    'create_robust_adaptive_dynamics',
]
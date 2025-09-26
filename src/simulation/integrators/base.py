#==========================================================================================\\\
#======================== src/simulation/integrators/base.py ===========================\\\
#==========================================================================================\\\

"""Base integrator interface and common utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple
import numpy as np

from ..core.interfaces import Integrator


class BaseIntegrator(Integrator):
    """Base class for numerical integration methods."""

    def __init__(self, rtol: float = 1e-6, atol: float = 1e-9):
        """Initialize base integrator.

        Parameters
        ----------
        rtol : float, optional
            Relative tolerance for adaptive methods
        atol : float, optional
            Absolute tolerance for adaptive methods
        """
        self.rtol = rtol
        self.atol = atol
        self._stats = {
            "total_steps": 0,
            "accepted_steps": 0,
            "rejected_steps": 0,
            "function_evaluations": 0
        }

    @abstractmethod
    def integrate(self,
                 dynamics_fn: Callable,
                 state: np.ndarray,
                 control: np.ndarray,
                 dt: float,
                 **kwargs) -> np.ndarray:
        """Integrate dynamics forward by one time step."""
        pass

    @property
    @abstractmethod
    def order(self) -> int:
        """Integration method order."""
        pass

    @property
    @abstractmethod
    def adaptive(self) -> bool:
        """Whether integrator supports adaptive step size."""
        pass

    def reset_statistics(self) -> None:
        """Reset integration statistics."""
        self._stats = {
            "total_steps": 0,
            "accepted_steps": 0,
            "rejected_steps": 0,
            "function_evaluations": 0
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return self._stats.copy()

    def integrate_step(self, dynamics_fn: Callable, state: np.ndarray, time: float, dt: float) -> np.ndarray:
        """
        Integrate dynamics forward by one time step (interface compatibility method).

        This method provides compatibility with test interfaces that expect integrate_step.
        It adapts the dynamics function signature for use with the integrate method.

        Args:
            dynamics_fn: Dynamics function that takes (state, time) and returns derivative
            state: Current state vector
            time: Current time
            dt: Integration time step

        Returns:
            Next state vector
        """
        # Adapt dynamics function to expected signature
        def adapted_dynamics(t, x, u=None):
            # Call the original dynamics function with expected signature
            return dynamics_fn(x, t)

        # Use empty control input since dynamics_fn is expected to handle control internally
        control = np.array([0.0])

        # Call the main integrate method
        return self.integrate(adapted_dynamics, state, control, dt, time)

    def _update_stats(self, accepted: bool = True, func_evals: int = 1) -> None:
        """Update integration statistics."""
        self._stats["total_steps"] += 1
        self._stats["function_evaluations"] += func_evals
        if accepted:
            self._stats["accepted_steps"] += 1
        else:
            self._stats["rejected_steps"] += 1

    def _validate_inputs(self,
                        dynamics_fn: Callable,
                        state: np.ndarray,
                        control: np.ndarray,
                        dt: float) -> None:
        """Validate integration inputs."""
        if not callable(dynamics_fn):
            raise TypeError("dynamics_fn must be callable")

        if not isinstance(state, np.ndarray):
            raise TypeError("state must be numpy array")

        if not isinstance(control, np.ndarray):
            raise TypeError("control must be numpy array")

        if dt <= 0:
            raise ValueError("dt must be positive")

        if not np.isfinite(state).all():
            raise ValueError("state contains non-finite values")

        if not np.isfinite(control).all():
            raise ValueError("control contains non-finite values")

    def _compute_error_norm(self, error: np.ndarray, state: np.ndarray) -> float:
        """Compute error norm for adaptive integration.

        Parameters
        ----------
        error : np.ndarray
            Error estimate
        state : np.ndarray
            Current state

        Returns
        -------
        float
            Normalized error
        """
        # Scale by tolerance
        scale = self.atol + self.rtol * np.abs(state)
        normalized_error = error / scale

        # Compute RMS norm
        return np.sqrt(np.mean(normalized_error**2))


class IntegrationResult:
    """Container for integration step results."""

    def __init__(self,
                 state: np.ndarray,
                 accepted: bool = True,
                 error_estimate: Optional[float] = None,
                 suggested_dt: Optional[float] = None,
                 function_evaluations: int = 1):
        """Initialize integration result.

        Parameters
        ----------
        state : np.ndarray
            Integrated state
        accepted : bool, optional
            Whether step was accepted
        error_estimate : float, optional
            Error estimate for adaptive methods
        suggested_dt : float, optional
            Suggested next time step
        function_evaluations : int, optional
            Number of function evaluations used
        """
        self.state = state
        self.accepted = accepted
        self.error_estimate = error_estimate
        self.suggested_dt = suggested_dt
        self.function_evaluations = function_evaluations
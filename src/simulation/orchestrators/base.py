#==========================================================================================\\\
#======================= src/simulation/orchestrators/base.py ==========================\\\
#==========================================================================================\\\

"""Base orchestrator interface and common functionality."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
import numpy as np

from ..core.interfaces import Orchestrator, ResultContainer, SimulationEngine
from ..core.simulation_context import SimulationContext
from ..results.containers import StandardResultContainer


class BaseOrchestrator(Orchestrator, SimulationEngine):
    """Base class for simulation execution orchestrators."""

    def __init__(self, context: SimulationContext):
        """Initialize base orchestrator.

        Parameters
        ----------
        context : SimulationContext
            Simulation context with configuration and models
        """
        self.context = context
        self.config = context.get_config()
        self.dynamics_model = context.get_dynamics_model()

        # Get simulation parameters
        sim_params = context.get_simulation_parameters()
        self.default_dt = sim_params.get("dt", 0.01)
        self.integration_method = sim_params.get("integration_method", "rk4")

        # Initialize integrator
        self._integrator = self._create_integrator()

        # Performance tracking
        self._execution_stats = {
            "total_simulations": 0,
            "total_steps": 0,
            "total_time": 0.0,
            "average_step_time": 0.0
        }

    def _create_integrator(self):
        """Create appropriate integrator based on configuration."""
        method = self.integration_method.lower()

        if method == "euler":
            from ..integrators.fixed_step.euler import ForwardEuler
            return ForwardEuler()
        elif method == "rk2":
            from ..integrators.fixed_step.runge_kutta import RungeKutta2
            return RungeKutta2()
        elif method == "rk4":
            from ..integrators.fixed_step.runge_kutta import RungeKutta4
            return RungeKutta4()
        elif method == "adaptive" or method == "rk45":
            from ..integrators.adaptive.runge_kutta import DormandPrince45
            return DormandPrince45()
        else:
            # Default to RK4
            from ..integrators.fixed_step.runge_kutta import RungeKutta4
            return RungeKutta4()

    def step(self, state: np.ndarray, control: np.ndarray, dt: float, **kwargs) -> np.ndarray:
        """Execute a single simulation step.

        Parameters
        ----------
        state : np.ndarray
            Current state vector
        control : np.ndarray
            Control input vector
        dt : float
            Time step
        **kwargs
            Additional parameters

        Returns
        -------
        np.ndarray
            Next state vector
        """
        # Get time from kwargs or default to 0
        t = kwargs.get("t", 0.0)

        # Create dynamics wrapper function
        def dynamics_fn(time, x, u):
            return self.dynamics_model.compute_dynamics(x, u)

        # Integrate using selected method
        next_state = self._integrator.integrate(dynamics_fn, state, control, dt, t)

        return next_state

    @abstractmethod
    def execute(self,
               initial_state: np.ndarray,
               control_inputs: np.ndarray,
               dt: float,
               horizon: int,
               **kwargs) -> ResultContainer:
        """Execute simulation with orchestrator-specific strategy."""
        pass

    def _create_result_container(self) -> ResultContainer:
        """Create appropriate result container."""
        return StandardResultContainer()

    def _validate_simulation_inputs(self,
                                  initial_state: np.ndarray,
                                  control_inputs: np.ndarray,
                                  dt: float,
                                  horizon: int) -> None:
        """Validate simulation inputs."""
        if not isinstance(initial_state, np.ndarray):
            raise TypeError("initial_state must be numpy array")

        if not isinstance(control_inputs, np.ndarray):
            raise TypeError("control_inputs must be numpy array")

        if dt <= 0:
            raise ValueError("dt must be positive")

        if horizon <= 0:
            raise ValueError("horizon must be positive")

        if not np.isfinite(initial_state).all():
            raise ValueError("initial_state contains non-finite values")

        if not np.isfinite(control_inputs).all():
            raise ValueError("control_inputs contains non-finite values")

    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution performance statistics."""
        return self._execution_stats.copy()

    def reset_statistics(self) -> None:
        """Reset execution statistics."""
        self._execution_stats = {
            "total_simulations": 0,
            "total_steps": 0,
            "total_time": 0.0,
            "average_step_time": 0.0
        }

    def _update_stats(self, num_steps: int, execution_time: float) -> None:
        """Update execution statistics."""
        self._execution_stats["total_simulations"] += 1
        self._execution_stats["total_steps"] += num_steps
        self._execution_stats["total_time"] += execution_time

        if self._execution_stats["total_steps"] > 0:
            self._execution_stats["average_step_time"] = (
                self._execution_stats["total_time"] / self._execution_stats["total_steps"]
            )

    def set_integrator(self, integrator) -> None:
        """Set custom integrator.

        Parameters
        ----------
        integrator : Integrator
            Custom integrator instance
        """
        self._integrator = integrator

    def get_integrator(self):
        """Get current integrator."""
        return self._integrator
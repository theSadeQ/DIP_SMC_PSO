#==========================================================================================\\\
#=========================== src/simulation/core/interfaces.py =========================\\\
#==========================================================================================\\\

"""Abstract base classes defining simulation framework interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
import numpy as np


class SimulationEngine(ABC):
    """Base interface for all simulation engines."""

    @abstractmethod
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
        pass


class Integrator(ABC):
    """Base interface for numerical integration methods."""

    @abstractmethod
    def integrate(self,
                 dynamics_fn: Callable,
                 state: np.ndarray,
                 control: np.ndarray,
                 dt: float,
                 **kwargs) -> np.ndarray:
        """Integrate dynamics forward by one time step.

        Parameters
        ----------
        dynamics_fn : callable
            Function computing state derivatives: f(x, u, t) -> dx/dt
        state : np.ndarray
            Current state vector
        control : np.ndarray
            Control input vector
        dt : float
            Integration time step
        **kwargs
            Integration-specific parameters

        Returns
        -------
        np.ndarray
            Integrated state
        """
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


class Orchestrator(ABC):
    """Base interface for simulation execution strategies."""

    @abstractmethod
    def execute(self,
               initial_state: np.ndarray,
               control_inputs: np.ndarray,
               dt: float,
               horizon: int,
               **kwargs) -> 'ResultContainer':
        """Execute simulation with specified strategy.

        Parameters
        ----------
        initial_state : np.ndarray
            Initial state vector or batch of states
        control_inputs : np.ndarray
            Control input sequence
        dt : float
            Time step
        horizon : int
            Simulation horizon
        **kwargs
            Strategy-specific parameters

        Returns
        -------
        ResultContainer
            Simulation results
        """
        pass


class SimulationStrategy(ABC):
    """Base interface for simulation analysis strategies (Monte Carlo, sensitivity, etc.)."""

    @abstractmethod
    def analyze(self,
               simulation_fn: Callable,
               parameters: Dict[str, Any],
               **kwargs) -> Dict[str, Any]:
        """Perform strategy-specific analysis.

        Parameters
        ----------
        simulation_fn : callable
            Simulation function to analyze
        parameters : dict
            Analysis parameters
        **kwargs
            Strategy-specific options

        Returns
        -------
        dict
            Analysis results
        """
        pass


class SafetyGuard(ABC):
    """Base interface for safety monitoring and constraints."""

    @abstractmethod
    def check(self, state: np.ndarray, step_idx: int, **kwargs) -> bool:
        """Check safety conditions.

        Parameters
        ----------
        state : np.ndarray
            Current state to check
        step_idx : int
            Current simulation step
        **kwargs
            Guard-specific parameters

        Returns
        -------
        bool
            True if state is safe, False otherwise
        """
        pass

    @abstractmethod
    def get_violation_message(self) -> str:
        """Get description of last safety violation."""
        pass


class ResultContainer(ABC):
    """Base interface for simulation result containers."""

    @abstractmethod
    def add_trajectory(self, states: np.ndarray, times: np.ndarray, **metadata) -> None:
        """Add a simulation trajectory to results."""
        pass

    @abstractmethod
    def get_states(self) -> np.ndarray:
        """Get state trajectories."""
        pass

    @abstractmethod
    def get_times(self) -> np.ndarray:
        """Get time vectors."""
        pass

    @abstractmethod
    def export(self, format_type: str, filepath: str) -> None:
        """Export results to specified format."""
        pass


class DataLogger(ABC):
    """Base interface for simulation data logging."""

    @abstractmethod
    def log_step(self, step_data: Dict[str, Any]) -> None:
        """Log data from a simulation step."""
        pass

    @abstractmethod
    def finalize(self) -> None:
        """Finalize logging and cleanup resources."""
        pass


class PerformanceMonitor(ABC):
    """Base interface for performance monitoring."""

    @abstractmethod
    def start_timing(self, operation: str) -> None:
        """Start timing an operation."""
        pass

    @abstractmethod
    def end_timing(self, operation: str) -> float:
        """End timing and return elapsed time."""
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        pass
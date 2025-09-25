#==========================================================================================\\\
#====================== src/controllers/base/controller_interface.py ===================\\\
#==========================================================================================\\\

"""Abstract base controller interface for the double inverted pendulum system."""

from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple, Union
import numpy as np


class ControllerInterface(ABC):
    """Abstract base class for all controllers in the DIP system.

    This interface defines the common methods that all controllers must implement,
    ensuring consistency and interoperability across different control algorithms.
    """

    def __init__(self, max_force: float = 20.0, dt: float = 0.01):
        """Initialize the base controller.

        Parameters
        ----------
        max_force : float, default=20.0
            Maximum control force that can be applied
        dt : float, default=0.01
            Sampling time step
        """
        self.max_force = max_force
        self.dt = dt
        self._reset_state()

    @abstractmethod
    def compute_control(self, state: np.ndarray, reference: Optional[np.ndarray] = None) -> float:
        """Compute the control action for the given state.

        Parameters
        ----------
        state : np.ndarray
            Current system state [x, x_dot, theta1, theta1_dot, theta2, theta2_dot]
        reference : np.ndarray, optional
            Reference/setpoint state (defaults to upright equilibrium)

        Returns
        -------
        float
            Control force to be applied to the cart
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the controller internal state."""
        pass

    def _reset_state(self) -> None:
        """Reset internal controller state variables."""
        # Override in subclasses that maintain internal state
        pass

    def step(self, state: np.ndarray, reference: Optional[np.ndarray] = None) -> Tuple[float, Any]:
        """Perform one control step.

        Parameters
        ----------
        state : np.ndarray
            Current system state
        reference : np.ndarray, optional
            Reference state

        Returns
        -------
        control : float
            Computed control action
        info : Any
            Additional controller information/diagnostics
        """
        control = self.compute_control(state, reference)

        # Apply force limits
        control = np.clip(control, -self.max_force, self.max_force)

        # Return control and basic info
        info = {
            'saturated': abs(control) >= self.max_force,
            'control_raw': control
        }

        return control, info

    @property
    def parameters(self) -> dict:
        """Get controller parameters as a dictionary."""
        return {
            'max_force': self.max_force,
            'dt': self.dt
        }

    def __repr__(self) -> str:
        """String representation of the controller."""
        return f"{self.__class__.__name__}(max_force={self.max_force}, dt={self.dt})"
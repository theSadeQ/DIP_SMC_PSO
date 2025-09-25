#==========================================================================================\\\
#======================== src/simulation/safety/recovery.py ========================\\\
#==========================================================================================\\\

"""Safety recovery strategies for simulation framework."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
import numpy as np


class RecoveryStrategy(ABC):
    """Base class for safety recovery strategies."""

    @abstractmethod
    def recover(self, state: np.ndarray, control: float, violation_info: dict) -> tuple:
        """Implement recovery strategy.

        Parameters
        ----------
        state : np.ndarray
            Current state
        control : float
            Current control
        violation_info : dict
            Information about the safety violation

        Returns
        -------
        tuple
            (recovered_state, recovered_control, success)
        """
        pass


class EmergencyStop(RecoveryStrategy):
    """Emergency stop recovery strategy."""

    def recover(self, state: np.ndarray, control: float, violation_info: dict) -> tuple:
        """Apply emergency stop - zero control and hold state."""
        return state.copy(), 0.0, True


class StateLimiter(RecoveryStrategy):
    """State limiting recovery strategy."""

    def __init__(self, lower_bounds: np.ndarray, upper_bounds: np.ndarray):
        """Initialize state limiter.

        Parameters
        ----------
        lower_bounds : np.ndarray
            Lower bounds for state variables
        upper_bounds : np.ndarray
            Upper bounds for state variables
        """
        self.lower_bounds = lower_bounds
        self.upper_bounds = upper_bounds

    def recover(self, state: np.ndarray, control: float, violation_info: dict) -> tuple:
        """Clip state to bounds and reduce control."""
        recovered_state = np.clip(state, self.lower_bounds, self.upper_bounds)
        recovered_control = control * 0.5  # Reduce control aggressiveness
        return recovered_state, recovered_control, True


class SafetyRecovery:
    """Safety recovery manager."""

    def __init__(self):
        """Initialize safety recovery manager."""
        self.strategies = {}
        self.default_strategy = EmergencyStop()

    def register_strategy(self, violation_type: str, strategy: RecoveryStrategy) -> None:
        """Register recovery strategy for specific violation type."""
        self.strategies[violation_type] = strategy

    def apply_recovery(self, state: np.ndarray, control: float, violation_info: dict) -> tuple:
        """Apply appropriate recovery strategy."""
        violation_type = violation_info.get('type', 'unknown')
        strategy = self.strategies.get(violation_type, self.default_strategy)
        return strategy.recover(state, control, violation_info)
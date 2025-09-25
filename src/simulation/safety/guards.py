#==========================================================================================\\\
#======================== src/simulation/safety/guards.py ==========================\\\
#==========================================================================================\\\

"""Enhanced safety guard functions for simulation framework."""

from __future__ import annotations

import numpy as np
from typing import Any, Tuple, Optional, Dict, Union

from ..core.interfaces import SafetyGuard


class SafetyViolationError(RuntimeError):
    """Exception raised when safety constraints are violated."""

    def __init__(self, message: str, violation_type: str, step_idx: Optional[int] = None):
        """Initialize safety violation error.

        Parameters
        ----------
        message : str
            Error message
        violation_type : str
            Type of safety violation
        step_idx : int, optional
            Simulation step where violation occurred
        """
        super().__init__(message)
        self.violation_type = violation_type
        self.step_idx = step_idx


class NaNGuard(SafetyGuard):
    """Guard against NaN and infinite values in state."""

    def check(self, state: np.ndarray, step_idx: int, **kwargs) -> bool:
        """Check for NaN/infinite values."""
        return np.all(np.isfinite(state))

    def get_violation_message(self) -> str:
        """Get violation message."""
        return "NaN or infinite values detected in state"


class EnergyGuard(SafetyGuard):
    """Guard against excessive system energy."""

    def __init__(self, max_energy: float):
        """Initialize energy guard.

        Parameters
        ----------
        max_energy : float
            Maximum allowed total energy
        """
        self.max_energy = max_energy
        self._violation_msg = ""

    def check(self, state: np.ndarray, step_idx: int, **kwargs) -> bool:
        """Check energy constraint."""
        total_energy = np.sum(state**2)
        if total_energy > self.max_energy:
            self._violation_msg = (
                f"Energy violation: {total_energy:.6f} > {self.max_energy:.6f}"
            )
            return False
        return True

    def get_violation_message(self) -> str:
        """Get violation message."""
        return self._violation_msg


class BoundsGuard(SafetyGuard):
    """Guard against state bounds violations."""

    def __init__(self, lower_bounds: Optional[np.ndarray], upper_bounds: Optional[np.ndarray]):
        """Initialize bounds guard.

        Parameters
        ----------
        lower_bounds : np.ndarray or None
            Lower bounds for state variables
        upper_bounds : np.ndarray or None
            Upper bounds for state variables
        """
        self.lower_bounds = lower_bounds
        self.upper_bounds = upper_bounds
        self._violation_msg = ""

    def check(self, state: np.ndarray, step_idx: int, **kwargs) -> bool:
        """Check bounds constraint."""
        if self.lower_bounds is not None:
            if np.any(state < self.lower_bounds):
                violated_indices = np.where(state < self.lower_bounds)[0]
                self._violation_msg = f"Lower bounds violated at indices: {violated_indices}"
                return False

        if self.upper_bounds is not None:
            if np.any(state > self.upper_bounds):
                violated_indices = np.where(state > self.upper_bounds)[0]
                self._violation_msg = f"Upper bounds violated at indices: {violated_indices}"
                return False

        return True

    def get_violation_message(self) -> str:
        """Get violation message."""
        return self._violation_msg


# Legacy functions for backward compatibility
def guard_no_nan(state: Any, step_idx: int) -> None:
    """Check for NaN/infinite values (legacy interface).

    Parameters
    ----------
    state : array-like
        State array
    step_idx : int
        Current step index

    Raises
    ------
    SafetyViolationError
        If NaN/infinite values detected
    """
    x = np.asarray(state)
    if not np.all(np.isfinite(x)):
        raise SafetyViolationError(
            f"NaN detected in state at step <i> (i={step_idx})",
            "nan_violation",
            step_idx
        )


def guard_energy(state: Any, limits: Optional[Dict[str, float]]) -> None:
    """Check energy constraint (legacy interface).

    Parameters
    ----------
    state : array-like
        State array
    limits : dict or None
        Energy limits with 'max' key

    Raises
    ------
    SafetyViolationError
        If energy constraint violated
    """
    if not limits or "max" not in limits:
        return

    x = np.asarray(state, dtype=float)
    total_energy = np.sum(x * x, axis=-1)
    max_allowed = float(limits["max"])

    if np.any(total_energy > max_allowed):
        tmax = float(np.max(total_energy))
        raise SafetyViolationError(
            f"Energy check failed: total_energy=<val> exceeds <max> (val_max={tmax}, max={max_allowed})",
            "energy_violation"
        )


def guard_bounds(state: Any, bounds: Optional[Tuple[Any, Any]], t: float) -> None:
    """Check bounds constraint (legacy interface).

    Parameters
    ----------
    state : array-like
        State array
    bounds : tuple or None
        (lower, upper) bounds
    t : float
        Current time

    Raises
    ------
    SafetyViolationError
        If bounds violated
    """
    if bounds is None:
        return

    lower, upper = bounds
    x = np.asarray(state, dtype=float)
    lo = -np.inf if lower is None else np.asarray(lower, dtype=float)
    hi = np.inf if upper is None else np.asarray(upper, dtype=float)

    if np.any(x < lo) or np.any(x > hi):
        raise SafetyViolationError(
            f"State bounds violated at t=<t> (t={t})",
            "bounds_violation"
        )


def apply_safety_guards(state: np.ndarray, step_idx: int, config: Any) -> None:
    """Apply all configured safety guards.

    Parameters
    ----------
    state : np.ndarray
        Current state vector
    step_idx : int
        Current simulation step
    config : Any
        Configuration object with safety settings

    Raises
    ------
    SafetyViolationError
        If any safety guard is violated
    """
    # Apply NaN guard (always active)
    guard_no_nan(state, step_idx)

    # Apply energy guard if configured
    safety_config = getattr(config, 'simulation', {})
    safety_settings = getattr(safety_config, 'safety', None)

    if safety_settings:
        # Energy limits
        energy_limits = getattr(safety_settings, 'energy_limits', None)
        if energy_limits:
            guard_energy(state, energy_limits)

        # State bounds
        state_bounds = getattr(safety_settings, 'state_bounds', None)
        if state_bounds:
            # Convert to tuple format expected by guard_bounds
            if hasattr(state_bounds, 'lower') and hasattr(state_bounds, 'upper'):
                bounds = (state_bounds.lower, state_bounds.upper)
            else:
                bounds = state_bounds
            guard_bounds(state, bounds, step_idx * 0.01)  # Approximate time


# Legacy functions with original names for backward compatibility
_guard_no_nan = guard_no_nan
_guard_energy = guard_energy
_guard_bounds = guard_bounds


class SafetyGuardManager:
    """Manager for multiple safety guards."""

    def __init__(self):
        """Initialize safety guard manager."""
        self.guards = []

    def add_guard(self, guard: SafetyGuard) -> None:
        """Add a safety guard.

        Parameters
        ----------
        guard : SafetyGuard
            Safety guard to add
        """
        self.guards.append(guard)

    def check_all(self, state: np.ndarray, step_idx: int, **kwargs) -> bool:
        """Check all safety guards.

        Parameters
        ----------
        state : np.ndarray
            Current state
        step_idx : int
            Current step
        **kwargs
            Additional parameters

        Returns
        -------
        bool
            True if all guards pass

        Raises
        ------
        SafetyViolationError
            If any guard fails
        """
        for guard in self.guards:
            if not guard.check(state, step_idx, **kwargs):
                raise SafetyViolationError(
                    guard.get_violation_message(),
                    type(guard).__name__.lower(),
                    step_idx
                )
        return True

    def clear_guards(self) -> None:
        """Clear all safety guards."""
        self.guards.clear()


def create_default_guards(config: Any) -> SafetyGuardManager:
    """Create default safety guards from configuration.

    Parameters
    ----------
    config : Any
        Configuration object

    Returns
    -------
    SafetyGuardManager
        Configured safety guard manager
    """
    manager = SafetyGuardManager()

    # Always add NaN guard
    manager.add_guard(NaNGuard())

    # Add other guards based on configuration
    safety_config = getattr(config, 'simulation', {})
    safety_settings = getattr(safety_config, 'safety', None)

    if safety_settings:
        # Energy guard
        energy_limits = getattr(safety_settings, 'energy_limits', None)
        if energy_limits and 'max' in energy_limits:
            manager.add_guard(EnergyGuard(energy_limits['max']))

        # Bounds guard
        state_bounds = getattr(safety_settings, 'state_bounds', None)
        if state_bounds:
            lower = getattr(state_bounds, 'lower', None)
            upper = getattr(state_bounds, 'upper', None)
            if lower is not None or upper is not None:
                manager.add_guard(BoundsGuard(lower, upper))

    return manager
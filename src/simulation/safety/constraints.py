#==========================================================================================\\\
#====================== src/simulation/safety/constraints.py =======================\\\
#==========================================================================================\\\

"""Constraint definitions and checking for simulation safety."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
import numpy as np


class Constraint(ABC):
    """Base class for simulation constraints."""

    @abstractmethod
    def check(self, value: np.ndarray, **kwargs) -> bool:
        """Check if constraint is satisfied."""
        pass

    @abstractmethod
    def get_violation_message(self) -> str:
        """Get constraint violation message."""
        pass


class StateConstraints:
    """State variable constraints."""

    def __init__(self,
                 lower_bounds: Optional[np.ndarray] = None,
                 upper_bounds: Optional[np.ndarray] = None,
                 custom_constraints: Optional[Dict[str, Constraint]] = None):
        """Initialize state constraints."""
        self.lower_bounds = lower_bounds
        self.upper_bounds = upper_bounds
        self.custom_constraints = custom_constraints or {}

    def check_all(self, state: np.ndarray) -> Tuple[bool, str]:
        """Check all state constraints."""
        # Check bounds
        if self.lower_bounds is not None and np.any(state < self.lower_bounds):
            return False, "State lower bounds violated"

        if self.upper_bounds is not None and np.any(state > self.upper_bounds):
            return False, "State upper bounds violated"

        # Check custom constraints
        for name, constraint in self.custom_constraints.items():
            if not constraint.check(state):
                return False, f"Custom constraint '{name}' violated: {constraint.get_violation_message()}"

        return True, ""


class ControlConstraints:
    """Control input constraints."""

    def __init__(self,
                 min_control: float = -np.inf,
                 max_control: float = np.inf,
                 rate_limit: Optional[float] = None):
        """Initialize control constraints."""
        self.min_control = min_control
        self.max_control = max_control
        self.rate_limit = rate_limit
        self._previous_control = None

    def check_all(self, control: float, dt: float = 0.01) -> Tuple[bool, str]:
        """Check all control constraints."""
        # Amplitude limits
        if control < self.min_control:
            return False, f"Control below minimum: {control} < {self.min_control}"

        if control > self.max_control:
            return False, f"Control above maximum: {control} > {self.max_control}"

        # Rate limits
        if self.rate_limit is not None and self._previous_control is not None:
            rate = abs(control - self._previous_control) / dt
            if rate > self.rate_limit:
                return False, f"Control rate limit exceeded: {rate} > {self.rate_limit}"

        self._previous_control = control
        return True, ""


class EnergyConstraints:
    """System energy constraints."""

    def __init__(self, max_kinetic: float, max_potential: float, max_total: float):
        """Initialize energy constraints."""
        self.max_kinetic = max_kinetic
        self.max_potential = max_potential
        self.max_total = max_total

    def check_all(self, kinetic: float, potential: float) -> Tuple[bool, str]:
        """Check energy constraints."""
        if kinetic > self.max_kinetic:
            return False, f"Kinetic energy too high: {kinetic} > {self.max_kinetic}"

        if potential > self.max_potential:
            return False, f"Potential energy too high: {potential} > {self.max_potential}"

        total = kinetic + potential
        if total > self.max_total:
            return False, f"Total energy too high: {total} > {self.max_total}"

        return True, ""


class ConstraintChecker:
    """Unified constraint checker for simulation safety."""

    def __init__(self,
                 state_constraints: Optional[StateConstraints] = None,
                 control_constraints: Optional[ControlConstraints] = None,
                 energy_constraints: Optional[EnergyConstraints] = None):
        """Initialize constraint checker."""
        self.state_constraints = state_constraints
        self.control_constraints = control_constraints
        self.energy_constraints = energy_constraints

    def check_state(self, state: np.ndarray) -> Tuple[bool, str]:
        """Check state constraints."""
        if self.state_constraints:
            return self.state_constraints.check_all(state)
        return True, ""

    def check_control(self, control: float, dt: float = 0.01) -> Tuple[bool, str]:
        """Check control constraints."""
        if self.control_constraints:
            return self.control_constraints.check_all(control, dt)
        return True, ""

    def check_energy(self, kinetic: float, potential: float) -> Tuple[bool, str]:
        """Check energy constraints."""
        if self.energy_constraints:
            return self.energy_constraints.check_all(kinetic, potential)
        return True, ""